# agents/prompts

Versioned system prompts (`version: X.Y` header). `_common.md` holds the score definition and
the rules the output guardrail enforces, shared by every specialist. Each answer's trace records
the prompt versions used. Listing descriptions and reviews are untrusted data.

Change a prompt → bump its version, rerun `python -m agents.harness`, and compare.
