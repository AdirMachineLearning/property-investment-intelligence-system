"""Tool guardrail: every tool call an agent makes goes through `ToolGuard.execute`.

In order, it checks:
1. allow-list: each agent may call only its own tools;
2. budget: calls per agent and per turn are capped (README: bounded tool calls);
3. schema: the arguments must match the tool's JSON input schema;
4. policy: tool-specific rules (roi_calculator only with numbers the USER supplied);
5. de-duplication: an identical call in the same turn returns the earlier evidence;
6. time limit: a slow tool returns `tool_failure` instead of hanging the chat;
7. it never raises: any error comes back to the model as data.

Every result is registered in the evidence store and returned with its reference (E1, E2, ...)
for the agent to cite. Long results are trimmed so they fit in the model's context.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field

from jsonschema import Draft202012Validator

from agents.evidence import EvidenceStore, numbers_in_text
from agents.tools.base import ToolSpec
from agents.tools.roi import USER_SUPPLIED

_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tool")


@dataclass
class TurnState:
    """Everything one user turn shares: evidence, budgets, the trace and the user's words."""
    store: EvidenceStore
    user_text: str = ""                                  # this message + earlier user messages
    tool_calls: int = 0
    calls_by_agent: dict = field(default_factory=dict)
    cache: dict = field(default_factory=dict)            # (tool, args json) -> ref
    events: list = field(default_factory=list)
    on_event: object = None                              # callback for live progress in the UI
    usage: dict = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0, "llm_calls": 0})

    def emit(self, kind: str, agent: str, **detail) -> dict:
        ev = {"t": round(time.time(), 3), "type": kind, "agent": agent, **detail}
        self.events.append(ev)
        if callable(self.on_event):
            try:
                self.on_event(ev)
            except Exception:
                pass
        return ev

    def user_numbers(self) -> set[float]:
        return set(numbers_in_text(self.user_text))


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(0.5, 0.005 * abs(b))


class ToolGuard:
    def __init__(self, registry: dict[str, ToolSpec], config):
        self.registry = registry
        self.config = config
        self._validators = {n: Draft202012Validator(s.schema["input_schema"])
                            for n, s in registry.items() if not s.server_tool}

    # ------------------------------------------------------------------ policy
    def _policy(self, name: str, args: dict, state: TurnState) -> str | None:
        if name == "roi_calculator":
            user_nums = state.user_numbers()
            for k in USER_SUPPLIED:
                v = args.get(k)
                if v in (None, 0):
                    continue
                if not any(_close(float(v), u) or _close(float(v), u * 1000) or _close(float(v), u * 1e6)
                           for u in user_nums):
                    return (f"{k}={v} was not supplied by the user. The data has no purchase "
                            "prices or costs; ask the user for them instead of assuming.")
            rev = args.get("annual_revenue")
            if rev is not None:
                ok = (any(_close(float(rev), u) for u in user_nums)
                      or any(_close(float(rev), e) for e in state.store.all_numbers()))
                if not ok:
                    return (f"annual_revenue={rev} matches neither the user's numbers nor any tool "
                            "result of this turn; take it from rank_opportunities")
        return None

    # ------------------------------------------------------------------ execution
    def execute(self, agent: str, allowed: set[str], name: str, args: dict,
                state: TurnState) -> tuple[dict, str | None]:
        """Returns (payload for the model, evidence ref or None)."""
        args = args if isinstance(args, dict) else {}

        def refuse(status: str, reason: str, guard: str):
            state.emit("guardrail", agent, guard=guard, tool=name, reason=reason)
            return {"tool": name, "status": status, "status_reason": reason}, None

        if name not in self.registry or name not in allowed:
            return refuse("invalid_input", f"tool {name!r} is not available to {agent}; "
                          f"use one of {sorted(allowed)}", "allow_list")
        used = state.calls_by_agent.get(agent, 0)
        if used >= self.config.max_tool_calls_per_agent or state.tool_calls >= self.config.max_tool_calls_per_turn:
            return refuse("budget_exhausted", "tool-call budget reached: answer with the evidence "
                          "you have and state what is missing", "budget")
        errors = sorted(self._validators[name].iter_errors(args), key=lambda e: list(e.path))
        if errors:
            msg = "; ".join(f"{'/'.join(map(str, e.path)) or 'input'}: {e.message}" for e in errors[:3])
            return refuse("invalid_input", f"arguments do not match the schema: {msg}", "schema")
        reason = self._policy(name, args, state)
        if reason:
            return refuse("refused_by_policy", reason, "policy")

        key = (name, json.dumps(args, sort_keys=True, default=str))
        if key in state.cache:
            ref = state.cache[key]
            state.emit("tool_cached", agent, tool=name, ref=ref)
            return self._payload(state.store.get(ref).result, ref), ref

        state.tool_calls += 1
        state.calls_by_agent[agent] = used + 1
        state.emit("tool_call", agent, tool=name, args=args)
        t0 = time.time()
        try:
            fut = _POOL.submit(self.registry[name].handler, args)
            result = fut.result(timeout=self.config.tool_timeout_s)
        except FutureTimeout:
            result = {"tool": name, "status": "tool_failure",
                      "status_reason": f"timed out after {self.config.tool_timeout_s:.0f}s"}
        except Exception as e:                           # the tools should not raise; be safe
            result = {"tool": name, "status": "tool_failure", "status_reason": f"{type(e).__name__}: {e}"}
        if not isinstance(result, dict):
            result = {"tool": name, "status": "tool_failure", "status_reason": "tool returned no record"}
        rec = state.store.register(name, agent, args, result, external=self.registry[name].external)
        state.cache[key] = rec.ref
        state.emit("tool_result", agent, tool=name, ref=rec.ref, status=result.get("status"),
                   evidence_id=result.get("evidence_id"), ms=int(1000 * (time.time() - t0)))
        return self._payload(result, rec.ref), rec.ref

    def _payload(self, result: dict, ref: str) -> dict:
        out = {"ref": ref, **result}
        text = json.dumps(out, ensure_ascii=False, default=str)
        if len(text) <= self.config.max_tool_result_chars:
            return out
        out = dict(out)
        out.pop("assumptions", None)
        for key in ("results", "cities"):
            while isinstance(out.get(key), list) and len(out[key]) > 1 and \
                    len(json.dumps(out, ensure_ascii=False, default=str)) > self.config.max_tool_result_chars:
                out[key] = out[key][: max(1, len(out[key]) * 2 // 3)]
                out["truncated"] = True
        return out
