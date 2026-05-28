"""
Agent 1: News & Sentiment Analyst
Model: gemini-2.5-flash
"""
from __future__ import annotations

import json
import logging

from trader.agents.base import BaseAgent
from trader.agents.models import NewsSentimentOutput, TokenUsage

logger = logging.getLogger(__name__)


class NewsSentimentAgent(BaseAgent):
    name = "news_sentiment"
    model = "gemini-2.5-flash"

    def run(
        self,
        ticker: str,
        company_name: str,
        sector: str,
        news_articles: list[dict],
        corporate_announcements: list[dict],
        close_price: float,
        pct_1d: float,
        news_window_tag: str,
    ) -> tuple[NewsSentimentOutput | None, TokenUsage, bool]:
        """
        Returns (output, token_usage, schema_valid).
        schema_valid=False means both attempts failed; caller should treat as NEUTRAL.
        """
        user_message = self._agent_prompt.format(
            ticker=ticker,
            company_name=company_name,
            sector=sector,
            news_articles=json.dumps(news_articles, default=str),
            corporate_announcements=json.dumps(corporate_announcements, default=str),
            close_price=close_price,
            pct_1d=pct_1d,
            news_window_tag=news_window_tag,
        )

        def call_fn():
            return self._call_gemini(user_message)

        def parse_fn(text: str) -> NewsSentimentOutput:
            return self._parse_output(text, NewsSentimentOutput)

        return self._call_with_retry(call_fn, parse_fn)
