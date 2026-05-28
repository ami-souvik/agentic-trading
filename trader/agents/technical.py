"""
Agent 2: Technical Analyst
Model: gemini-2.5-flash
"""
from __future__ import annotations

import json
import logging

from trader.agents.base import BaseAgent
from trader.agents.models import TechnicalOutput, TokenUsage

logger = logging.getLogger(__name__)


class TechnicalAgent(BaseAgent):
    name = "technical"
    model = "gemini-2.5-flash"

    def run(
        self,
        ticker: str,
        company_name: str,
        indicators: dict,
        last_5d_ohlcv: list[dict],
        current_position: dict,
    ) -> tuple[TechnicalOutput | None, TokenUsage, bool]:
        """
        Returns (output, token_usage, schema_valid).
        """
        user_message = self._agent_prompt.format(
            ticker=ticker,
            company_name=company_name,
            indicators=json.dumps(indicators, default=str),
            last_5d_ohlcv=json.dumps(last_5d_ohlcv, default=str),
            current_position=json.dumps(current_position, default=str),
        )

        def call_fn():
            return self._call_gemini(user_message)

        def parse_fn(text: str) -> TechnicalOutput:
            return self._parse_output(text, TechnicalOutput)

        return self._call_with_retry(call_fn, parse_fn)
