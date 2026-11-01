"""Versioned prompts. Each file starts with `version: X.Y` and `---`; the version is recorded
in the trace of every answer, so a change in behaviour can be traced to a prompt change."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=None)
def load(name: str) -> tuple[str, str]:
    """(text, version) of agents/prompts/<name>.md."""
    raw = (DIR / f"{name}.md").read_text(encoding="utf-8")
    head, _, body = raw.partition("\n---\n")
    version = head.replace("version:", "").strip() if head.startswith("version:") else "0"
    return body.strip(), version


def system_prompt(name: str, with_common: bool = True) -> tuple[str, str]:
    body, v = load(name)
    if not with_common:
        return body, v
    common, cv = load("_common")
    return f"{body}\n\n{common}", f"{name}-{v}+common-{cv}"
