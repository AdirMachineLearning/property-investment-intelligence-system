"""ROI calculator: the only place where money in and money out meet.

The data has no purchase prices or operating costs (README, Guardrails), so the system never
estimates a return on its own. This tool computes one ONLY from numbers the user supplied in
the conversation. The tool guardrail (agents/guardrails/tool_guard.py) checks that provenance:
`purchase_price` and `annual_operating_costs` must appear in the user's own messages, and
`annual_revenue` must come from the user or from a tool result of this turn.
"""
from __future__ import annotations

from agents.tools.base import ToolSpec

USER_SUPPLIED = ("purchase_price", "annual_operating_costs", "annual_financing_costs")


def roi_calculator_tool() -> ToolSpec:
    schema = {
        "name": "roi_calculator",
        "description": (
            "Arithmetic only. Computes gross and net rental yield and simple payback years from "
            "a purchase price and annual costs THAT THE USER SUPPLIED, and an annual revenue "
            "from the user or from rank_opportunities (prefer the conservative score). Never "
            "invent a purchase price or costs: if the user did not give them, do not call this "
            "tool, ask for them. The result is a simple illustration before tax, vacancy beyond "
            "the stated occupancy, and regulation, not financial advice."),
        "input_schema": {"type": "object", "properties": {
            "purchase_price": {"type": "number", "exclusiveMinimum": 0},
            "annual_revenue": {"type": "number", "minimum": 0},
            "annual_operating_costs": {"type": "number", "minimum": 0},
            "annual_financing_costs": {"type": "number", "minimum": 0},
            "currency": {"type": "string"},
            "revenue_source": {"type": "string",
                               "description": "Where annual_revenue comes from, e.g. 'user' or an evidence reference like 'E2'."}},
            "required": ["purchase_price", "annual_revenue", "annual_operating_costs", "currency"]},
    }

    def handler(a: dict) -> dict:
        price = float(a["purchase_price"])
        rev = float(a["annual_revenue"])
        costs = float(a["annual_operating_costs"]) + float(a.get("annual_financing_costs") or 0)
        net = rev - costs
        out = {"tool": "roi_calculator", "status": "ok", "status_reason": None,
               "currency": a["currency"], "inputs": {k: a.get(k) for k in schema["input_schema"]["properties"]},
               "gross_yield_pct": round(100 * rev / price, 2),
               "net_operating_income": round(net, 0),
               "net_yield_pct": round(100 * net / price, 2),
               "payback_years": round(price / net, 1) if net > 0 else None,
               "guardrail": ("Illustration from user-supplied inputs only; before tax, regulation "
                             "(e.g. limits on short-term rental nights) and financing details. "
                             "Not financial advice and not a buy recommendation."),
               "evidence_id": f"roi:{int(price)}:{int(rev)}:{int(costs)}"}
        if net <= 0:
            out["note"] = "costs are equal to or above revenue: no payback"
        return out

    return ToolSpec("roi_calculator", schema, handler)
