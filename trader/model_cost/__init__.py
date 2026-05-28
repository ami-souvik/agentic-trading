"""
trader.model_cost — LLM cost tracking backed by the LiteLLM pricing registry.

Public API (designed for future extraction into a standalone package):

    from trader.model_cost import compute_cost, cost_summary, get_model_pricing, ModelPricing

    # Simple — just the dollar amount
    usd = compute_cost("claude-haiku-4-5", input_tokens=4000, output_tokens=500,
                       cache_read_tokens=3200)

    # Detailed breakdown dict for logging / DynamoDB
    detail = cost_summary("gemini-2.5-flash", input_tokens=2000, output_tokens=300)

    # Inspect model metadata
    pricing = get_model_pricing("claude-sonnet-4-6")
    print(pricing.input_cost_per_million)   # USD per 1M input tokens
    print(pricing.supports_prompt_caching)  # True for Anthropic / Gemini

Pricing data is sourced from:
    https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json

Refreshed once per day; falls back to a bundled snapshot when offline.
"""
from trader.model_cost.calculator import compute_cost, cost_summary
from trader.model_cost.registry import ModelPricing, get_model_pricing, MODEL_ALIASES
from trader.model_cost.fetcher import fetch_pricing_data, LITELLM_PRICING_URL

__all__ = [
    # Core public API
    "compute_cost",
    "cost_summary",
    "get_model_pricing",
    "ModelPricing",
    # Advanced / admin
    "MODEL_ALIASES",
    "fetch_pricing_data",
    "LITELLM_PRICING_URL",
]
