"""The evidence store: every tool answer the agents receive, with a short reference to cite.

Each tool result is registered once per turn and gets a short reference (E1, E2, ...) that the
agents cite in their answers, e.g. "about EUR 22,344 per year [E2]". The store keeps:

* the tool, the arguments, the agent that called it and the full result;
* the tool's own `evidence_id` (e.g. "opp:amsterdam:20261028_1012:breakdown:..."), so a brief
  can be traced to the exact table, model and snapshot;
* every number in the result (also numbers inside text such as `statement` and `formula`),
  which the output guardrail uses to check that each number in the answer comes from a tool.

`log_path` appends one JSON line per result; the groundedness harness (README criterion 7)
reads the same file.
"""
from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

NUMBER_RE = re.compile(r"(?<![\w.])[-−]?\d[\d,]*(?:\.\d+)?")


def parse_number(text: str) -> float | None:
    t = text.replace("−", "-").replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def numbers_in_text(text: str) -> list[float]:
    out = []
    for m in NUMBER_RE.finditer(str(text)):
        v = parse_number(m.group(0))
        if v is not None:
            out.append(v)
    return out


def flatten_numbers(obj, keys_to_skip=("evidence_id", "table_version", "model_version",
                                       "split_version", "tool_use_id")) -> set[float]:
    """Every number in a JSON-like object, including numbers written inside strings."""
    found: set[float] = set()

    def walk(x, key=None):
        if key in keys_to_skip:
            return
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            found.add(float(x))
        elif isinstance(x, str):
            found.update(numbers_in_text(x))
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(v, k)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v, key)

    walk(obj)
    return found


@dataclass
class EvidenceRecord:
    ref: str
    tool: str
    agent: str
    args: dict
    result: dict
    evidence_id: str | None
    status: str | None
    numbers: set[float] = field(default_factory=set)
    created: float = field(default_factory=time.time)
    external: bool = False          # web content: context only, never used in the score

    def summary(self) -> dict:
        return {"ref": self.ref, "tool": self.tool, "agent": self.agent, "args": self.args,
                "status": self.status, "evidence_id": self.evidence_id, "external": self.external}


class EvidenceStore:
    def __init__(self, log_path: Path | None = None, turn_id: str | None = None):
        self.records: dict[str, EvidenceRecord] = {}
        self.log_path = Path(log_path) if log_path else None
        self.turn_id = turn_id or time.strftime("%Y%m%d_%H%M%S")
        self._lock = threading.Lock()

    def register(self, tool: str, agent: str, args: dict, result: dict,
                 external: bool = False) -> EvidenceRecord:
        with self._lock:
            ref = f"E{len(self.records) + 1}"
            rec = EvidenceRecord(ref=ref, tool=tool, agent=agent, args=dict(args or {}),
                                 result=result, evidence_id=result.get("evidence_id"),
                                 status=result.get("status"), numbers=flatten_numbers(result),
                                 external=external)
            self.records[ref] = rec
        if self.log_path is not None:
            try:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"turn_id": self.turn_id, "ref": ref, "tool": tool,
                                        "agent": agent, "request": args, "response": result},
                                       ensure_ascii=False, default=str) + "\n")
            except OSError:
                pass                    # the log is best-effort; the answer must not fail
        return rec

    def get(self, ref: str) -> EvidenceRecord | None:
        return self.records.get(ref)

    def all_numbers(self, refs=None) -> set[float]:
        recs = self.records.values() if refs is None else [self.records[r] for r in refs if r in self.records]
        out: set[float] = set()
        for r in recs:
            out |= r.numbers
        return out

    def used_tool(self, tool: str) -> bool:
        return any(r.tool == tool and r.status == "ok" for r in self.records.values())

    def __len__(self):
        return len(self.records)
