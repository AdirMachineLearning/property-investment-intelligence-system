"""All agent settings in one place. Every value can be overridden by an environment variable
(or a .env file at the repository root), so the lecturer never has to edit code."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

try:                                    # optional: read ANTHROPIC_API_KEY etc. from .env
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:                     # python-dotenv is optional
    pass


def _env(name: str, default):
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    return type(default)(v) if not isinstance(default, Path) else Path(v)


@dataclass
class AgentConfig:
    # where the data, models and reports live (the team's bundle, or a demo repository)
    data_root: Path = field(default_factory=lambda: _env("PIIS_DATA_ROOT", REPO_ROOT))
    # language models: a strong one for the specialists, a fast one for routing and revision
    agent_model: str = field(default_factory=lambda: _env("PIIS_AGENT_MODEL", "claude-sonnet-5-5"))
    router_model: str = field(default_factory=lambda: _env("PIIS_ROUTER_MODEL", "claude-haiku-5-5"))
    max_tokens: int = 2500
    # budgets (tool guardrails)
    max_tool_calls_per_agent: int = field(default_factory=lambda: _env("PIIS_MAX_TOOL_CALLS", 10))
    max_tool_calls_per_turn: int = 24
    max_llm_rounds_per_agent: int = 10
    tool_timeout_s: float = 30.0
    max_tool_result_chars: int = 14_000
    web_search_max_uses: int = 3
    # input guardrail
    max_input_chars: int = 2_000
    # conversation memory passed to the specialists (user/assistant text only)
    history_turns: int = 6
    # evidence log for the groundedness harness (README criterion 7)
    evidence_log: Path | None = field(
        default_factory=lambda: _env("PIIS_EVIDENCE_LOG", REPO_ROOT / "evaluation" / "agent_evidence.jsonl"))

    @property
    def api_key_present(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
