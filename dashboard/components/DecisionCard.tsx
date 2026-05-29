"use client";
import { useState } from "react";
import { DecisionResponse, AgentDecisionDetail, decisionColor, formatINR } from "@/lib/api";
import clsx from "clsx";
import { ChevronDown, ChevronRight } from "lucide-react";

const AGENT_LABELS: Record<string, string> = {
  NewsSentiment: "News & Sentiment",
  Technical:     "Technical",
  Fundamentals:  "Fundamentals",
  BullBear:      "Bull vs Bear",
  PortfolioManager: "Portfolio Manager",
};

function ConfidenceBadge({ value }: { value: number | null }) {
  if (value === null) return null;
  const pct = Math.round(value * 100);
  const color =
    pct >= 70 ? "text-bull" : pct >= 50 ? "text-gold" : "text-bear";
  return (
    <span className={clsx("font-mono text-xs", color)}>{pct}%</span>
  );
}

function AgentPane({ agent }: { agent: AgentDecisionDetail }) {
  const label = AGENT_LABELS[agent.agent] ?? agent.agent;

  return (
    <div className="bg-bg rounded-lg p-3 space-y-2 text-xs">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-subtle uppercase tracking-wide text-[10px]">
          {label}
        </span>
        <div className="flex items-center gap-2">
          {agent.model && (
            <span className="text-subtle font-mono text-[10px]">{agent.model}</span>
          )}
          <ConfidenceBadge value={agent.confidence ?? null} />
        </div>
      </div>

      {/* News */}
      {agent.sentiment_label && (
        <div>
          <span className="text-subtle">Sentiment: </span>
          <span
            className={clsx(
              "font-semibold",
              agent.sentiment_label?.includes("BULLISH") ? "text-bull" : "text-bear"
            )}
          >
            {agent.sentiment_label}
          </span>
        </div>
      )}
      {agent.key_events?.length > 0 && (
        <ul className="space-y-0.5">
          {agent.key_events.map((e, i) => (
            <li key={i} className="text-subtle flex gap-1.5">
              <span className="text-accent mt-0.5">·</span>
              {e}
            </li>
          ))}
        </ul>
      )}

      {/* Technical */}
      {agent.technical_signal && (
        <div className="flex flex-wrap gap-2">
          <span className="text-subtle">Signal: </span>
          <span
            className={clsx(
              "font-semibold",
              agent.technical_signal === "BUY" ? "text-bull" : "text-bear"
            )}
          >
            {agent.technical_signal}
          </span>
          {agent.trend && (
            <span className="text-subtle">· Trend: <span className="text-text">{agent.trend}</span></span>
          )}
          {agent.momentum && (
            <span className="text-subtle">· Momentum: <span className="text-text">{agent.momentum}</span></span>
          )}
        </div>
      )}

      {/* Fundamentals */}
      {agent.fundamental_bias && (
        <div>
          <span className="text-subtle">Bias: </span>
          <span
            className={clsx(
              "font-semibold",
              agent.fundamental_bias === "BULLISH" ? "text-bull" : "text-bear"
            )}
          >
            {agent.fundamental_bias}
          </span>
          {agent.institutional_flow && (
            <span className="text-subtle ml-2">· {agent.institutional_flow}</span>
          )}
        </div>
      )}
      {agent.red_flags?.length > 0 && (
        <div className="text-bear">⚠ {agent.red_flags.join(", ")}</div>
      )}

      {/* Bull/Bear debate */}
      {agent.bull_thesis?.length > 0 && (
        <div className="grid grid-cols-2 gap-2 mt-1">
          <div>
            <div className="text-bull text-[10px] font-semibold mb-1">BULL</div>
            <ul className="space-y-0.5">
              {agent.bull_thesis.map((t, i) => (
                <li key={i} className="text-subtle flex gap-1.5">
                  <span className="text-bull mt-0.5">▲</span>{t}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="text-bear text-[10px] font-semibold mb-1">BEAR</div>
            <ul className="space-y-0.5">
              {agent.bear_thesis?.map((t, i) => (
                <li key={i} className="text-subtle flex gap-1.5">
                  <span className="text-bear mt-0.5">▼</span>{t}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
      {agent.debate_winner && (
        <div className="text-subtle">
          Winner: <span
            className={agent.debate_winner === "BULL" ? "text-bull font-semibold" : "text-bear font-semibold"}
          >
            {agent.debate_winner}
          </span>
          {agent.key_risk && <span className="ml-2">· Risk: {agent.key_risk}</span>}
        </div>
      )}

      {/* PM primary thesis */}
      {agent.primary_thesis && (
        <p className="text-subtle italic">&ldquo;{agent.primary_thesis}&rdquo;</p>
      )}

      {/* Reasoning */}
      {agent.reasoning && !agent.primary_thesis && (
        <p className="text-subtle italic">&ldquo;{agent.reasoning}&rdquo;</p>
      )}

      {/* Token cost */}
      {agent.cost_usd !== null && agent.cost_usd !== undefined && (
        <div className="text-[10px] text-muted font-mono">
          ${agent.cost_usd.toFixed(5)} · {agent.input_tokens}↑ {agent.output_tokens}↓ tokens
          {agent.schema_valid === false && (
            <span className="ml-2 text-bear">⚠ schema error</span>
          )}
        </div>
      )}
    </div>
  );
}

interface Props {
  decision: DecisionResponse;
}

export function DecisionCard({ decision }: Props) {
  const [open, setOpen] = useState(false);
  const { pm_decision, skip_reason } = decision;

  return (
    <div className="rounded-xl border border-border bg-surface overflow-hidden">
      {/* Header row — always visible */}
      <button
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-border/20 transition-colors"
        onClick={() => setOpen((o) => !o)}
      >
        {open ? (
          <ChevronDown size={14} className="text-subtle shrink-0" />
        ) : (
          <ChevronRight size={14} className="text-subtle shrink-0" />
        )}

        {/* Ticker + decision badge */}
        <span className="font-mono font-semibold text-text w-28">{decision.ticker}</span>
        <span
          className={clsx(
            "px-2 py-0.5 rounded text-xs font-semibold",
            decisionColor(pm_decision)
          )}
        >
          {pm_decision ?? "—"}
        </span>

        {/* Confidence */}
        {decision.pm_confidence !== null && (
          <ConfidenceBadge value={decision.pm_confidence} />
        )}

        {/* Quick summary pills */}
        <div className="flex gap-2 ml-2 flex-wrap">
          {decision.news_sentiment && (
            <span
              className={clsx(
                "px-1.5 py-0.5 rounded text-[10px]",
                decision.news_sentiment.includes("BULLISH")
                  ? "bg-bull/10 text-bull"
                  : "bg-bear/10 text-bear"
              )}
            >
              📰 {decision.news_sentiment}
            </span>
          )}
          {decision.technical_signal && (
            <span
              className={clsx(
                "px-1.5 py-0.5 rounded text-[10px]",
                decision.technical_signal === "BUY"
                  ? "bg-bull/10 text-bull"
                  : "bg-bear/10 text-bear"
              )}
            >
              📈 {decision.technical_signal}
            </span>
          )}
          {decision.debate_winner && (
            <span
              className={clsx(
                "px-1.5 py-0.5 rounded text-[10px]",
                decision.debate_winner === "BULL"
                  ? "bg-bull/10 text-bull"
                  : decision.debate_winner === "BEAR"
                  ? "bg-bear/10 text-bear"
                  : "bg-muted/10 text-subtle"
              )}
            >
              ⚔️ {decision.debate_winner}
            </span>
          )}
        </div>

        {/* Actual fill */}
        {decision.actual_fill && (
          <span className="ml-auto text-xs text-subtle font-mono">
            {decision.actual_fill.side} {decision.actual_fill.qty} @{" "}
            ₹{decision.actual_fill.fill_price.toLocaleString("en-IN")}
          </span>
        )}

        {/* Skip reason */}
        {pm_decision === "SKIP" && skip_reason && (
          <span className="ml-auto text-xs text-muted">{skip_reason}</span>
        )}

        {/* R:R ratio */}
        {decision.risk_reward_ratio !== null && decision.risk_reward_ratio !== undefined && (
          <span className="text-xs text-subtle ml-auto">
            R:R {decision.risk_reward_ratio.toFixed(1)}x
          </span>
        )}
      </button>

      {/* Expanded detail — all 5 agent panes */}
      {open && (
        <div className="px-4 pb-4 grid gap-2">
          {decision.agents.map((agent) => (
            <AgentPane key={agent.agent} agent={agent} />
          ))}

          {/* PM thesis */}
          {decision.pm_reasoning && (
            <div className="bg-accent/5 border border-accent/20 rounded-lg p-3 text-xs">
              <span className="text-accent font-semibold">PM Thesis: </span>
              <span className="text-subtle">{decision.pm_reasoning}</span>
            </div>
          )}

          {/* Fill details */}
          {decision.actual_fill && (
            <div className="bg-border/20 rounded-lg p-3 text-xs font-mono text-subtle">
              Fill: {decision.actual_fill.side} {decision.actual_fill.qty} shares @{" "}
              ₹{decision.actual_fill.fill_price.toLocaleString("en-IN")} |{" "}
              Value: {formatINR(decision.actual_fill.trade_value_inr)} |{" "}
              Cost: ₹{decision.actual_fill.simulated_cost_inr.toFixed(2)}{" "}
              ({decision.actual_fill.simulated_cost_bps.toFixed(1)} bps)
            </div>
          )}
        </div>
      )}
    </div>
  );
}
