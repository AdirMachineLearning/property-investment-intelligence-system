"""Ask the agents from the terminal (no UI).

    python -m agents.cli "מהן ההזדמנויות המובילות באמסטרדם?"
    python -m agents.cli            # interactive: type questions, empty line to quit
"""
from __future__ import annotations

import sys
import warnings

from agents.orchestrator import Orchestrator


def show(r) -> None:
    print("\n" + r.answer + "\n")
    v = r.verification or {}
    tools = [e["tool"] for e in r.events if e["type"] == "tool_call"]
    g = v.get("groundedness")
    grounded = "-" if g is None else f"{g:.0%}"
    print(f"[{r.mode} | {r.agent} | tools: {', '.join(tools) or '-'} | "
          f"numbers {v.get('claims', 0)}, grounded {grounded} | "
          f"{r.elapsed_s}s | {r.usage['llm_calls']} model calls]")
    for ev in r.evidence:
        print(f"  {ev['ref']}: {ev['tool']} {ev['status']} {ev['evidence_id']}")


def main() -> None:
    warnings.simplefilter("ignore")
    orch = Orchestrator()
    if orch.llm is None:
        print("(no ANTHROPIC_API_KEY: answering in fallback mode, the opportunity table only)")
    history = []
    questions = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else None
    while True:
        q = questions.pop(0) if questions else (None if questions is not None else input("? ").strip())
        if not q:
            break
        r = orch.handle(q, history)
        show(r)
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": r.answer}]


if __name__ == "__main__":
    main()
