# agents/guardrails

Deterministic code, tested in `tests/test_agents.py`:

- `input_guard.py`: blocks prompt injection (English and Hebrew patterns), empty and oversized messages.
- `tool_guard.py`: per-agent allow-list, JSON-schema validation, call budgets, de-duplication, time limit, and policy (`roi_calculator` only with the user's numbers). Registers every result as evidence.
- `injection.py`: shared injection detection; quarantines instructions found in review text.
- `output_guard.py`: every number in an answer must match a tool result of the turn and be cited; cited references must exist; no buy instructions, guarantees or ROI without the calculator.

Never infer bookings from unavailable dates or ROI from nightly prices.
