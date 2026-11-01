# agents/tools

Read-only tools. Each returns a fixed record with a `status` (ok, insufficient_evidence,
not_found, invalid_input, unavailable) and an `evidence_id`, and never raises.

- `model_tools.py`: `rank_opportunities` and `predict_listing_price`, the team's tools from `src/models`.
- `data_tools.py`: `data_availability`, `neighbourhood_stats` (descriptive, any city), `review_signals` (sanitised guest reviews).
- `roi.py`: `roi_calculator`, only from the user's own purchase price and costs.
- `__init__.py`: the registry, and `web_search` (Anthropic server tool, external context).
- `base.py`: `ToolSpec` and `ToolContext`, which loads the data once and reports what is missing.

Catalogue and contracts: [docs/agents.md](../../docs/agents.md#the-tools).
