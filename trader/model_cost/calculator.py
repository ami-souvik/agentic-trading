"""
compute_cost() — the single public function callers use.

Supports two call patterns:

Pattern A — Anthropic with prompt caching:
    cost = compute_cost(
        model="claude-haiku-4-5",
        input_tokens=4000,
        output_tokens=500,
        cache_read_tokens=3200,   # tokens served from cache (cheap)
        cache_write_tokens=800,   # tokens written to cache (slightly more expensive)
    )

Pattern B — Standard (no caching):
    cost = compute_cost("gemini-2.5-flash", input_tokens=2000, output_tokens=300)

The function never raises — unknown models return $0.00 with a log warning
so a bad model name never crashes the trading pipeline.
"""
from __future__ import annotations

import logging

from trader.model_cost.registry import ModelPricing, get_model_pricing

logger = logging.getLogger(__name__)


def compute_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    """
    Compute USD cost for one LLM call.

    Args:
        model:              Model name (our internal alias or LiteLLM canonical key).
        input_tokens:       Total prompt tokens sent (including any cached portion).
        output_tokens:      Completion tokens generated.
        cache_read_tokens:  Tokens served from the prompt cache (Anthropic / Gemini).
                            These are billed at the cheaper cache_read rate.
        cache_write_tokens: Tokens being written into the cache for the first time.
                            Billed at cache_creation rate (usually slightly above base).

    Returns:
        Cost in USD as a float, rounded to 8 decimal places.

    Cost formula:
        non_cached_input  = input_tokens - cache_read_tokens - cache_write_tokens
        cost = (non_cached_input  × input_cost_per_token)
             + (cache_write_tokens × cache_creation_input_token_cost)
             + (cache_read_tokens  × cache_read_input_token_cost)
             + (output_tokens      × output_cost_per_token)
    """
    pricing: ModelPricing = get_model_pricing(model)

    # Guard: don't allow negative counts
    cache_read_tokens = max(0, cache_read_tokens)
    cache_write_tokens = max(0, cache_write_tokens)
    input_tokens = max(0, input_tokens)
    output_tokens = max(0, output_tokens)

    non_cached_input = max(0, input_tokens - cache_read_tokens - cache_write_tokens)

    cost = (
        non_cached_input     * pricing.input_cost_per_token
        + cache_write_tokens * pricing.cache_creation_input_token_cost
        + cache_read_tokens  * pricing.cache_read_input_token_cost
        + output_tokens      * pricing.output_cost_per_token
    )

    return round(cost, 8)


def cost_summary(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> dict:
    """
    Like compute_cost() but returns a detailed breakdown dict — useful for
    logging to CloudWatch or the DynamoDB DECISION item.

    Returns:
        {
          "model": str,
          "provider": str,
          "input_tokens": int,
          "output_tokens": int,
          "cache_read_tokens": int,
          "cache_write_tokens": int,
          "non_cached_input_tokens": int,
          "cost_usd": float,
          "cost_breakdown": {
              "input_usd": float,
              "cache_write_usd": float,
              "cache_read_usd": float,
              "output_usd": float,
          },
          "rates_per_million": {
              "input": float,
              "output": float,
              "cache_write": float,
              "cache_read": float,
          }
        }
    """
    pricing = get_model_pricing(model)

    cache_read_tokens = max(0, cache_read_tokens)
    cache_write_tokens = max(0, cache_write_tokens)
    input_tokens = max(0, input_tokens)
    output_tokens = max(0, output_tokens)
    non_cached = max(0, input_tokens - cache_read_tokens - cache_write_tokens)

    input_usd       = round(non_cached          * pricing.input_cost_per_token,             8)
    cache_write_usd = round(cache_write_tokens  * pricing.cache_creation_input_token_cost,  8)
    cache_read_usd  = round(cache_read_tokens   * pricing.cache_read_input_token_cost,      8)
    output_usd      = round(output_tokens       * pricing.output_cost_per_token,            8)

    return {
        "model": pricing.model,
        "provider": pricing.litellm_provider,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_write_tokens": cache_write_tokens,
        "non_cached_input_tokens": non_cached,
        "cost_usd": round(input_usd + cache_write_usd + cache_read_usd + output_usd, 8),
        "cost_breakdown": {
            "input_usd": input_usd,
            "cache_write_usd": cache_write_usd,
            "cache_read_usd": cache_read_usd,
            "output_usd": output_usd,
        },
        "rates_per_million": {
            "input":       pricing.input_cost_per_million,
            "output":      pricing.output_cost_per_million,
            "cache_write": pricing.cache_write_cost_per_million,
            "cache_read":  pricing.cache_read_cost_per_million,
        },
    }
