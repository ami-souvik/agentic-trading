"""
Tests for trader/model_cost — LiteLLM-backed pricing registry.

All tests use the fallback snapshot so no network connection is needed.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from trader.model_cost.fetcher import _FALLBACK_SNAPSHOT, fetch_pricing_data
from trader.model_cost.registry import ModelPricing, get_model_pricing, MODEL_ALIASES
from trader.model_cost.calculator import compute_cost, cost_summary
from trader.model_cost import compute_cost as public_compute_cost  # public API smoke-test


# ── Helpers ──────────────────────────────────────────────────────────────────

def _use_fallback():
    """Force the registry to use only the fallback snapshot (no network, no disk cache)."""
    from trader.model_cost import fetcher
    fetcher._LOADED_DATA.clear()
    fetcher._LOADED_DATA.update(_FALLBACK_SNAPSHOT)


# ── ModelPricing dataclass ────────────────────────────────────────────────────

class TestModelPricingDataclass:
    def test_per_million_properties(self):
        pricing = ModelPricing(
            model="test",
            input_cost_per_token=1e-06,
            output_cost_per_token=5e-06,
            cache_read_input_token_cost=1e-07,
            cache_creation_input_token_cost=1.25e-06,
        )
        assert pricing.input_cost_per_million == pytest.approx(1.0)
        assert pricing.output_cost_per_million == pytest.approx(5.0)
        assert pricing.cache_read_cost_per_million == pytest.approx(0.1)
        assert pricing.cache_write_cost_per_million == pytest.approx(1.25)

    def test_supports_prompt_caching_true(self):
        pricing = ModelPricing(model="test", cache_read_input_token_cost=1e-07)
        assert pricing.supports_prompt_caching is True

    def test_supports_prompt_caching_false(self):
        pricing = ModelPricing(model="test", cache_read_input_token_cost=0.0)
        assert pricing.supports_prompt_caching is False

    def test_str_representation(self):
        pricing = ModelPricing(
            model="claude-haiku-4-5",
            input_cost_per_token=1e-06,
            output_cost_per_token=5e-06,
            cache_read_input_token_cost=1e-07,
        )
        s = str(pricing)
        assert "claude-haiku-4-5" in s
        assert "in=$1.000/M" in s


# ── Registry lookup ───────────────────────────────────────────────────────────

class TestGetModelPricing:
    def setup_method(self):
        _use_fallback()

    def test_claude_haiku_exact_match(self):
        pricing = get_model_pricing("claude-haiku-4-5")
        assert pricing.input_cost_per_million == pytest.approx(1.0)
        assert pricing.output_cost_per_million == pytest.approx(5.0)
        assert pricing.cache_read_cost_per_million == pytest.approx(0.1)
        assert pricing.cache_write_cost_per_million == pytest.approx(1.25)
        assert pricing.litellm_provider == "anthropic"

    def test_claude_sonnet_exact_match(self):
        pricing = get_model_pricing("claude-sonnet-4-6")
        assert pricing.input_cost_per_million == pytest.approx(3.0)
        assert pricing.output_cost_per_million == pytest.approx(15.0)
        assert pricing.cache_read_cost_per_million == pytest.approx(0.3)

    def test_gemini_alias_resolution(self):
        """'gemini-2.5-flash' must resolve via MODEL_ALIASES to 'gemini/gemini-2.5-flash'."""
        assert "gemini-2.5-flash" in MODEL_ALIASES
        pricing = get_model_pricing("gemini-2.5-flash")
        assert pricing.model == "gemini/gemini-2.5-flash"
        assert pricing.input_cost_per_million == pytest.approx(0.30)
        assert pricing.output_cost_per_million == pytest.approx(2.50)

    def test_gemini_canonical_name(self):
        """Direct use of canonical LiteLLM name also works."""
        pricing = get_model_pricing("gemini/gemini-2.5-flash")
        assert pricing.input_cost_per_million == pytest.approx(0.30)

    def test_unknown_model_returns_zero_sentinel(self):
        """Unknown model must not raise — returns zero-cost sentinel."""
        pricing = get_model_pricing("some-totally-unknown-model-xyz")
        assert pricing.cost_usd_for(1000, 100) == 0.0 if hasattr(pricing, "cost_usd_for") else True
        assert pricing.input_cost_per_token == 0.0
        assert pricing.output_cost_per_token == 0.0

    def test_haiku_supports_prompt_caching(self):
        pricing = get_model_pricing("claude-haiku-4-5")
        assert pricing.supports_prompt_caching is True

    def test_context_window(self):
        pricing = get_model_pricing("claude-haiku-4-5")
        assert pricing.max_input_tokens == 200_000
        assert pricing.max_output_tokens == 64_000


# ── compute_cost() ────────────────────────────────────────────────────────────

class TestComputeCost:
    def setup_method(self):
        _use_fallback()

    def test_haiku_no_caching(self):
        """1000 input + 100 output, no cache → $0.001 + $0.0005 = $0.0005"""
        # in: 1000 × $1/M = $0.001; out: 100 × $5/M = $0.0005
        cost = compute_cost("claude-haiku-4-5", input_tokens=1000, output_tokens=100)
        expected = 1000 * 1e-06 + 100 * 5e-06
        assert cost == pytest.approx(expected, rel=1e-4)

    def test_haiku_with_cache_read(self):
        """3000 cached + 1000 non-cached input + 200 output."""
        cost = compute_cost(
            "claude-haiku-4-5",
            input_tokens=4000,
            output_tokens=200,
            cache_read_tokens=3000,
        )
        # non_cached=1000, cache_read=3000, output=200
        expected = (
            1000 * 1e-06    # non-cached input
            + 3000 * 1e-07  # cache read
            + 200 * 5e-06   # output
        )
        assert cost == pytest.approx(expected, rel=1e-4)

    def test_haiku_cache_read_cheaper_than_no_cache(self):
        """Reading from cache should be cheaper than the same tokens uncached."""
        cost_no_cache = compute_cost("claude-haiku-4-5", input_tokens=4000, output_tokens=200)
        cost_cached   = compute_cost("claude-haiku-4-5", input_tokens=4000, output_tokens=200,
                                     cache_read_tokens=3000)
        assert cost_cached < cost_no_cache

    def test_haiku_cache_write(self):
        """Tokens written to cache should be billed at cache_creation rate (1.25/M)."""
        cost = compute_cost(
            "claude-haiku-4-5",
            input_tokens=1000,
            output_tokens=0,
            cache_write_tokens=1000,
        )
        # All 1000 input are cache_write; no non-cached input, no output
        expected = 1000 * 1.25e-06
        assert cost == pytest.approx(expected, rel=1e-4)

    def test_sonnet_pricing(self):
        cost = compute_cost("claude-sonnet-4-6", input_tokens=1000, output_tokens=100)
        expected = 1000 * 3e-06 + 100 * 1.5e-05
        assert cost == pytest.approx(expected, rel=1e-4)

    def test_gemini_alias(self):
        cost = compute_cost("gemini-2.5-flash", input_tokens=2000, output_tokens=300)
        expected = 2000 * 3e-07 + 300 * 2.5e-06
        assert cost == pytest.approx(expected, rel=1e-4)

    def test_zero_tokens(self):
        assert compute_cost("claude-haiku-4-5", input_tokens=0, output_tokens=0) == 0.0

    def test_negative_tokens_clamped_to_zero(self):
        cost = compute_cost("claude-haiku-4-5", input_tokens=-100, output_tokens=-50)
        assert cost == 0.0

    def test_unknown_model_returns_zero(self):
        cost = compute_cost("does-not-exist", input_tokens=1000, output_tokens=100)
        assert cost == 0.0

    def test_public_api_alias(self):
        """Importing from trader.model_cost should work identically."""
        cost = public_compute_cost("claude-haiku-4-5", input_tokens=1000, output_tokens=100)
        assert cost > 0.0


# ── cost_summary() ────────────────────────────────────────────────────────────

class TestCostSummary:
    def setup_method(self):
        _use_fallback()

    def test_summary_structure(self):
        result = cost_summary("claude-haiku-4-5", input_tokens=4000, output_tokens=200,
                              cache_read_tokens=3000, cache_write_tokens=500)
        assert "model" in result
        assert "provider" in result
        assert "cost_usd" in result
        assert "cost_breakdown" in result
        assert "rates_per_million" in result

    def test_breakdown_sums_to_total(self):
        result = cost_summary("claude-haiku-4-5", input_tokens=4000, output_tokens=200,
                              cache_read_tokens=3000)
        bd = result["cost_breakdown"]
        total_from_parts = bd["input_usd"] + bd["cache_write_usd"] + bd["cache_read_usd"] + bd["output_usd"]
        assert total_from_parts == pytest.approx(result["cost_usd"], rel=1e-6)

    def test_rates_per_million_haiku(self):
        result = cost_summary("claude-haiku-4-5", input_tokens=100, output_tokens=10)
        rates = result["rates_per_million"]
        assert rates["input"] == pytest.approx(1.0)
        assert rates["output"] == pytest.approx(5.0)
        assert rates["cache_read"] == pytest.approx(0.1)
        assert rates["cache_write"] == pytest.approx(1.25)

    def test_non_cached_input_count(self):
        result = cost_summary("claude-haiku-4-5", input_tokens=5000, output_tokens=100,
                              cache_read_tokens=3000, cache_write_tokens=1000)
        # non_cached = 5000 - 3000 - 1000 = 1000
        assert result["non_cached_input_tokens"] == 1000

    def test_gemini_rates(self):
        result = cost_summary("gemini-2.5-flash", input_tokens=1000, output_tokens=100)
        rates = result["rates_per_million"]
        assert rates["input"] == pytest.approx(0.30)
        assert rates["output"] == pytest.approx(2.50)


# ── Fetcher cache behaviour ───────────────────────────────────────────────────

class TestFetcher:
    def test_fallback_snapshot_has_required_models(self):
        """The bundled snapshot must cover all 3 models we use in production."""
        assert "claude-haiku-4-5" in _FALLBACK_SNAPSHOT
        assert "claude-sonnet-4-6" in _FALLBACK_SNAPSHOT
        assert "gemini/gemini-2.5-flash" in _FALLBACK_SNAPSHOT

    def test_fallback_fields_are_floats(self):
        for model, entry in _FALLBACK_SNAPSHOT.items():
            for field in ("input_cost_per_token", "output_cost_per_token"):
                assert isinstance(entry[field], float), f"{model}.{field} must be float"

    def test_network_failure_uses_fallback(self, tmp_path):
        """If the network is down and no cache exists, fallback snapshot is used."""
        from trader.model_cost import fetcher

        saved = dict(fetcher._LOADED_DATA)
        fetcher._LOADED_DATA.clear()
        original_cache = fetcher.CACHE_PATH
        fetcher.CACHE_PATH = tmp_path / "no_such_file.json"  # cache doesn't exist

        with patch("trader.model_cost.fetcher.urlopen", side_effect=OSError("offline")):
            data = fetch_pricing_data(force_refresh=True)

        assert "claude-haiku-4-5" in data

        # Restore
        fetcher.CACHE_PATH = original_cache
        fetcher._LOADED_DATA.clear()
        fetcher._LOADED_DATA.update(saved)

    def test_cache_written_on_successful_fetch(self, tmp_path):
        """A successful fetch should write the cache file to disk."""
        from trader.model_cost import fetcher

        saved = dict(fetcher._LOADED_DATA)
        fetcher._LOADED_DATA.clear()
        original_cache = fetcher.CACHE_PATH
        fetcher.CACHE_PATH = tmp_path / "pricing_cache.json"

        fake_json = json.dumps({"test-model": {"input_cost_per_token": 1e-06}})

        class FakeResponse:
            def read(self): return fake_json.encode()
            def __enter__(self): return self
            def __exit__(self, *a): pass

        with patch("trader.model_cost.fetcher.urlopen", return_value=FakeResponse()):
            data = fetch_pricing_data(force_refresh=True)

        assert fetcher.CACHE_PATH.exists()
        cached = json.loads(fetcher.CACHE_PATH.read_text())
        assert "test-model" in cached

        # Restore
        fetcher.CACHE_PATH = original_cache
        fetcher._LOADED_DATA.clear()
        fetcher._LOADED_DATA.update(saved)
