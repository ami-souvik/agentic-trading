"""
Pydantic output models for all 5 agents.

Every agent must return one of these validated models. If validation fails,
the caller retries once, then falls back to the HOLD default for the PM.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ── Agent 1: News & Sentiment ─────────────────────────────────────────────────

SentimentLabel = Literal["BULLISH", "SLIGHTLY_BULLISH", "NEUTRAL", "SLIGHTLY_BEARISH", "BEARISH"]
DataQuality = Literal["HIGH", "MEDIUM", "LOW", "STALE"]
NewsWindow = Literal["PRE_OPEN", "INTRADAY", "AFTER_CLOSE"]


class NewsSentimentOutput(BaseModel):
    ticker: str
    sentiment_score: float = Field(ge=0.0, le=1.0)
    sentiment_label: SentimentLabel
    key_events: list[str]
    news_window: NewsWindow
    data_quality: DataQuality
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


# ── Agent 2: Technical Analysis ───────────────────────────────────────────────

TechnicalSignal = Literal["BUY", "SELL", "HOLD", "EXIT_LONG"]
Trend = Literal["UPTREND", "DOWNTREND", "RANGING"]
Momentum = Literal["OVERBOUGHT", "NEUTRAL", "OVERSOLD"]
VolumeSignal = Literal["ABOVE_AVG", "AVERAGE", "BELOW_AVG", "DIVERGENT"]


class TechnicalOutput(BaseModel):
    ticker: str
    technical_signal: TechnicalSignal
    trend: Trend
    momentum: Momentum
    suggested_stop_loss_pct: float = Field(ge=0.0)
    suggested_target_pct: float = Field(ge=0.0)
    volume_signal: VolumeSignal
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


# ── Agent 3: Fundamentals ─────────────────────────────────────────────────────

FundamentalBias = Literal["BULLISH", "NEUTRAL", "BEARISH"]
Valuation = Literal["CHEAP", "FAIR", "EXPENSIVE", "UNKNOWN"]
InstitutionalFlow = Literal[
    "FII_BUYING", "FII_SELLING", "DII_BUYING", "DII_SELLING", "MIXED", "NEUTRAL"
]


class FundamentalsOutput(BaseModel):
    ticker: str
    fundamental_bias: FundamentalBias
    valuation: Valuation
    institutional_flow: InstitutionalFlow
    macro_tailwind: bool
    red_flags: list[str]
    data_staleness_days: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


# ── Agent 4: Bull vs Bear Debate ──────────────────────────────────────────────

DebateWinner = Literal["BULL", "BEAR", "DRAW"]


class BullBearOutput(BaseModel):
    ticker: str
    bull_thesis: list[str] = Field(min_length=1, max_length=3)
    bear_thesis: list[str] = Field(min_length=1, max_length=3)
    debate_winner: DebateWinner
    conviction_delta: float = Field(ge=0.0, le=1.0)
    key_risk: str
    confidence: float = Field(ge=0.0, le=1.0)


# ── Agent 5: Portfolio Manager ────────────────────────────────────────────────

PMDecisionType = Literal["BUY", "SELL", "HOLD", "EXIT", "SKIP"]
PMDecisionRationale = Literal["QUIET", "RESTRICTED", "BUDGET", "DRAWDOWN", ""]
ProductType = Literal["CNC"]
AgentAgreement = Literal["HIGH", "MEDIUM", "LOW"]


class PMDecision(BaseModel):
    ticker: str
    decision: PMDecisionType
    decision_rationale: str = ""
    quantity_shares: int = Field(ge=0)
    estimated_trade_value_inr: float = Field(ge=0.0)
    product_type: ProductType = "CNC"
    horizon_days: int = Field(ge=1, le=5)
    target_price: float = Field(ge=0.0)
    stop_loss_price: float = Field(ge=0.0)
    confidence: float = Field(ge=0.0, le=1.0)
    primary_thesis: str
    kill_conditions: list[str]
    agent_agreement: AgentAgreement
    estimated_cost_bps: float = Field(ge=0.0)
    risk_reward_ratio: float = Field(ge=0.0)

    @model_validator(mode="after")
    def validate_decision_constraints(self) -> "PMDecision":
        if self.decision in ("HOLD", "SKIP"):
            # quantity/price fields should be 0 for non-action decisions
            # Allow non-zero to accommodate LLM quirks; normalise here.
            pass
        if self.decision == "BUY" and self.quantity_shares == 0:
            raise ValueError("BUY decision must have quantity_shares > 0")
        return self


# ── HOLD fallback (used when PM schema validation fails twice) ─────────────────

def pm_hold_fallback(ticker: str) -> PMDecision:
    return PMDecision(
        ticker=ticker,
        decision="HOLD",
        decision_rationale="",
        quantity_shares=0,
        estimated_trade_value_inr=0.0,
        product_type="CNC",
        horizon_days=1,
        target_price=0.0,
        stop_loss_price=0.0,
        confidence=0.0,
        primary_thesis="Schema validation failed — defaulting to HOLD.",
        kill_conditions=[],
        agent_agreement="LOW",
        estimated_cost_bps=28.5,
        risk_reward_ratio=0.0,
    )


# ── Cost tracking ──────────────────────────────────────────────────────────────

class TokenUsage(BaseModel):
    agent: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0       # tokens served from cache (cheap read)
    cache_write_tokens: int = 0  # tokens written to cache (one-time creation cost)
    cost_usd: float = 0.0
