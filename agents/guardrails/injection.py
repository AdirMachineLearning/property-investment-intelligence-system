"""Prompt-injection detection, shared by the input guardrail (the user's message) and the
review tool (untrusted listing and review text).

Pattern-based on purpose: it is deterministic, explainable in the presentation and testable.
It catches the common forms in English and Hebrew; the second line of defence is structural:
untrusted text is returned inside tool results marked `untrusted`, and the system prompts tell
the agents that text inside tool results is data, never instructions.
"""
from __future__ import annotations

import re

INJECTION_PATTERNS = [
    # English
    r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|prompts|rules)",
    r"disregard (all |any |the )?(previous|prior|above|your) (instructions|rules|guidelines)",
    r"forget (all |your |the )?(previous |prior )?(instructions|rules)",
    r"you are now (a|an|the) ",
    r"(reveal|print|show|repeat) (your |the )?(system|hidden) (prompt|instructions)",
    r"\bsystem prompt\b",
    r"\bjailbreak\b|\bDAN mode\b|developer mode",
    r"act as (if you|an? unrestricted)",
    r"new instructions?:",
    r"</?(system|assistant|tool_result|instructions)>",
    # Hebrew
    r"התעלם (מכל |מ)?(ה)?הוראות",
    r"שכח (את )?(כל )?(ה)?הוראות",
    r"(הצג|חשוף|הדפס) (את )?(ה)?(פרומפט|הנחיות) (ה)?(מערכת|הסודיות)",
    r"הוראות חדשות:",
    r"אתה עכשיו (סוכן|מודל|בוט) ",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def find_injection(text: str) -> str | None:
    """The first matching pattern's text, or None."""
    for rx in _COMPILED:
        m = rx.search(str(text or ""))
        if m:
            return m.group(0)
    return None


def scan_untrusted_text(text: str, max_chars: int = 300) -> tuple[str, bool]:
    """Truncate untrusted text and quarantine it if it carries instructions.
    Returns (safe_text, was_quarantined)."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if find_injection(text):
        return "[quarantined by guardrail: this text contained instructions aimed at the assistant]", True
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + " …"
    return text, False
