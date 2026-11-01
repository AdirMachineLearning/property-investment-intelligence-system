"""The two model tools from src/models (Idan's hand-off), wrapped for the agents.

The wrappers add nothing to the numbers: they forward the call to the team's code and turn a
missing file into an `unavailable` answer. The descriptions are the team's own TOOL_SCHEMA
texts, so the model sees the same guardrails the tool enforces.
"""
from __future__ import annotations

from agents.tools.base import ToolContext, ToolSpec, unavailable


def rank_opportunities_tool(ctx: ToolContext) -> ToolSpec:
    from src.models.opportunity_tool import TOOL_SCHEMA

    def handler(args: dict) -> dict:
        tool = ctx.opportunity_tool()
        if tool is None:
            return unavailable("rank_opportunities",
                               "no opportunity table loaded: " + ctx.errors.get("opportunities", "unknown"))
        return tool.handle_tool_call(args)

    return ToolSpec("rank_opportunities", dict(TOOL_SCHEMA), handler)


def predict_listing_price_tool(ctx: ToolContext) -> ToolSpec:
    from src.models.predict import TOOL_SCHEMA

    def handler(args: dict) -> dict:
        service = ctx.prediction_service()
        if service is None:
            return unavailable("predict_listing_price",
                               "no price model loaded: " + ctx.errors.get("predictions", "unknown"))
        out = service.handle_tool_call(args)
        out.setdefault("tool", "predict_listing_price")
        return out

    return ToolSpec("predict_listing_price", dict(TOOL_SCHEMA), handler)
