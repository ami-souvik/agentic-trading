# Suggested 4-Week Build Plan

## Week 1 — Data & Plumbing
**Goal:** Ingest, store, and visualize EOD data + news for 15 chosen Nifty stocks.

**D1–D2:** Pick the 15 tickers (suggested: 10 mega-caps RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, HINDUNILVR, ITC, LT, AXISBANK, KOTAKBANK + 5 high-news names BHARTIARTL, MARUTI, BAJFINANCE, ASIANPAINT, ADANIENT). Terraform AWS skeleton, DynamoDB tables, Secrets Manager, S3 archive bucket.

**D3–D4:** Implement ingestion/ with jugaad-data EOD pull + bhavcopy archival + NSE/BSE RSS + Moneycontrol/ET RSS + Reddit API. Dedupe with cosine similarity.

**D5–D7:** Build paper-trading ledger with realistic 28-bps delivery / 11-bps intraday cost model; wire up Nifty 50 TRI as benchmark.

**Acceptance:** One command runs end-to-end ingestion for one day; you can pull yesterday's OHLC + ≥10 news items per ticker; cost model verified against published Zerodha calculator for 3 test trades.

## Week 2 — Agents & Decisions
**Goal:** All 5 agents return validated JSON for all 15 stocks.

**D8–D10:** Build News/Sentiment, Technical, Fundamentals agents. Gemini 2.5 Flash for News + Technical; Claude Haiku 4.5 for Fundamentals.

**D11–D12:** Bull/Bear debate (single LLM, two personas, 2 rounds max).

**D13–D14:** Portfolio Manager with strict JSON schema + self-consistency (3 samples). Claude Sonnet 4.6 or Haiku 4.5 depending on early cost data.

**Acceptance:** ≥98% schema-valid outputs across a 3-day dry run; total daily LLM cost <$0.40; LangGraph state checkpointed for replay.

## Week 3 — Dashboard, Benchmarks, Risk
**Goal:** End-to-end loop with monitoring.

**D15–D17:** Next.js dashboard — NAV vs Nifty 50 chart, decision log with debate viewer, per-stock confidence heatmap, cost breakdown.

**D18–D19:** Implement all 5 benchmarks (Nifty 50 TRI, equal-weight, momentum, mean-reversion, buy-and-hold) in metrics/.

**D20–D21:** Wire circuit breakers (drawdown, position size, sector, ASM/GSM, schema-error rate). CloudWatch alarms + SNS notifications.

**Acceptance:** Dashboard loads <2s; benchmarks recompute nightly; a manually-injected ASM ticker triggers an EXIT signal in next run.

## Week 4 — The 30-Day Run + Analysis
**Goal:** 21 trading days of paper trading with full logging, then a written post-mortem.

**D22–D42:** Run daily at 17:00 IST (after market close, news settled). Daily 15-min review of decision log; weekly check of all metrics.

**D43–D45:** Post-mortem. Compute final Sharpe / Sortino / drawdown vs each benchmark. Per-agent hit rate. Agreement-vs-outcome heatmap. Cost-as-pct-of-gross-return. Identify top 2 lessons for v2.

**Acceptance** — what "success" actually means:

≥95% of trading days the full pipeline ran without manual intervention.
≥97% schema-valid outputs from all agents.
Total spend ≤ ₹2,000.
A written post-mortem identifying ≥3 prompt-engineering improvements to ship in v2.
A labeled dataset of 21 × 15 × 5 ≈ 1,575 (decision, prompt, outcome) tuples ready for analysis.

Returns vs the Nifty 50 are not in the success criteria. If you happen to beat the benchmark, that's a hypothesis worth testing on a longer window — never proof.