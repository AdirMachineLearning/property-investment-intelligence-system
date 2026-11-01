"""Input guardrail: runs on the user's message before any language model sees it.

Blocks: empty or oversized messages, and messages that try to override the assistant's
instructions (prompt injection). Off-topic requests are not blocked here; the router answers
them politely, so the user is told what the system can do.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from agents.guardrails.injection import find_injection

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass
class InputCheck:
    allowed: bool
    text: str
    reason: str | None = None
    flags: list[str] = field(default_factory=list)
    message_he: str | None = None          # what the user sees when blocked


def check_input(message: str, max_chars: int = 2000) -> InputCheck:
    text = CONTROL_CHARS.sub("", str(message or "")).strip()
    if not text:
        return InputCheck(False, text, "empty", ["empty"], "לא התקבלה שאלה. נסה לנסח שאלה על הזדמנויות השקעה.")
    if len(text) > max_chars:
        return InputCheck(False, text[:max_chars], "too_long", ["too_long"],
                          f"ההודעה ארוכה מדי ({len(text):,} תווים, המקסימום {max_chars:,}). קצר אותה ונסה שוב.")
    hit = find_injection(text)
    if hit:
        return InputCheck(False, text, f"prompt_injection: {hit!r}", ["prompt_injection"],
                          "ההודעה נחסמה: היא מנסה לשנות את ההוראות של המערכת. "
                          "אפשר לשאול על הזדמנויות, מחירים, שכונות ונתונים.")
    return InputCheck(True, text)
