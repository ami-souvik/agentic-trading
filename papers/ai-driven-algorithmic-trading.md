# Building a Lean, AI-Driven Algorithmic Trading MVP for Indian Equities (NSE/BSE)

**TL;DR**
- **Build it, but expect process learning — not alpha.** A multi-agent LLM swing-trading MVP for Nifty large-caps is *technically* feasible under ₹2,000/month using **Zerodha Kite Connect Personal (free trading API) + jugaad-data/nselib (free EOD data) + Gemini 2.5 Flash / DeepSeek V3.2 for analyst agents + Claude Haiku 4.5 for the final Portfolio Manager**. Total LLM spend for once-daily decisions on 15 stocks comes to roughly **$5–$15/month** with prompt caching.
- **Tax-adjust your expectations.** Indian retail round-trip costs (STT + exchange fees + GST + stamp duty + DP charges) run roughly **25.5 bps for delivery and 10.6 bps for intraday** on a ₹50,000 trade — i.e., 2.5× the 10 bps used in Kirtac & Germano (2024) for delivery. Their Sharpe 3.05 / 355% gain is essentially impossible to replicate in retail Indian conditions; the StockBench benchmark (Chen, Yao et al., Tsinghua, arXiv 2510.02209v1, Oct 2025) confirms that **even GPT-5 only barely beat buy-and-hold (0.3% vs 0.4% over 82 trading days on the top-20 DJIA, Mar 3–Jun 30 2025)**.
- **The realistic success criterion is infrastructure and prompt-engineering insight, not returns.** Treat the 30-day paper trade as a *calibration run* against five baselines (Nifty 50 TRI, equal-weighted basket, 5-day momentum, mean-reversion, buy-and-hold). With ~21 trading days the 95% CI on a measured Sharpe of 1.0 spans roughly −1.5 to +3.5; you cannot statistically prove an edge, only that the pipeline works.

---

## 1. Indian Broker & Market Data API Landscape (2025–2026)

### 1.1 Headline regulatory shift you must understand first

SEBI's circular **SEBI/HO/MIRSD/MIRSD-PoD/P/2025/0000013 (4 Feb 2025) "Safer participation of retail investors in Algorithmic trading"**, followed by **NSE/INVG/67858 (5 May 2025)** implementation standards, came into force with a final compliance deadline extended from 1 Aug 2025 to **1 Oct 2025** (SEBI sep-2025 extension circular). Key operational rules for a personal algo dev:

- **OPS (orders-per-second) threshold of 10** per exchange per client. **Below 10 OPS → no algo registration needed**. Above 10 OPS → mandatory algo registration with the broker, who in turn registers it with the exchange. A once-daily decision engine on 15 stocks is trivially below this.
- **Static IP whitelisting is mandatory** for API-driven order placement (only for the *order-placing* IP — not for data-only consumption). Family sharing of the static IP is allowed only with 2FA-verified consent across self/spouse/dependent children/parents.
- **White-box vs. black-box classification**: a personal-use, self-built system on your own money is effectively *white-box for personal use*; you don't need Research Analyst (RA) registration. **The moment you offer signals/copy-trade to anyone else, you cross into black-box / RA territory and need broker empanelment plus SEBI RA registration.**
- Each algo order routed via API must carry an exchange-assigned **unique Algo ID** (broker auto-handled).

### 1.2 Broker API comparison (personal use, Q2 2026 status)

| Broker | API monthly cost | Historical data | Live stream | Sandbox | Notes |
|---|---|---|---|---|---|
| **Zerodha Kite Connect — Personal** | **₹0** (free since Mar 2025) | ❌ Not included | ❌ No live quotes | No | Trading + account-mgmt only. Pair with jugaad-data for data. |
| **Zerodha Kite Connect — Standard** | **₹500/mo** (cut from ₹2,000 in Jun 2025 after the SEBI circular per Z-Connect post) | ✅ 10y NSE/BSE intraday (bundled since 8 Feb 2025) | ✅ WebSocket, 3,000 instruments | No | API key-level cap: 10 req/sec; 200 orders/min RMS limit; 2,000 MIS + 2,000 CO/day. |
| **Upstox** | **Free APIs** (₹10/order via API until 31 Mar 2026 per developer announcement; standard ₹20 after) | ✅ Historical candles 1m–monthly | ✅ WebSocket v3 (TBT), 100 instruments/conn (non-WS endpoints 25 req/s, 250/min) | ✅ Sandbox | OAuth2; Python/Node SDKs solid. |
| **Dhan (DhanHQ)** | **Trading API free; Data API ₹499+GST/mo OR free if ≥25 trades in last 30d** (per Chittorgarh) | ✅ Historical OHLC | ✅ WebSocket, up to 5 conns × 5,000 instruments | ✅ Sandbox mode | 10 req/s order, 5 req/s data, 100k data req/day. Cleanest dev experience for Indian API. |
| **Fyers** | **Free API + free data** | ✅ Historical + quotes | ✅ WebSocket | ✅ Sandbox | Strong dev docs; brokerage normal ₹20/order. |
| **Angel One SmartAPI** | **Free** | ✅ Historical | ✅ SmartStream WebSocket | Limited | Mass-market lead-magnet positioning. |
| **Alice Blue ANT API** | **Free** | ✅ | ✅ | Partial | Solid for cost-conscious devs. |
| **5paisa** | Free | Limited | ✅ | No | Less actively maintained. |
| **ICICI Direct Breeze** | Free | ✅ | ✅ | No | Requires ICICI bank+demat account. |

### 1.3 Free/cheap data alternatives

- **jugaad-data** (`jugaad-py/jugaad-data`) — actively maintained, uses **new** NSE site, supports bhavcopy, `stock_df` EOD historical, `NSELive()` for live quotes, caching built in. **Recommended primary for the MVP.**
- **nselib** (`pypi/nselib`) — broad coverage: indices, FII/DII, derivatives, AMFI archives. Use for Nifty 50 index history (your benchmark) and FII flow.
- **nsepython** (`pypi/nsepython`) — still maintained.
- **nsepy** — explicitly **deprecated** by its author (relies on the old NSE site).
- **nsetools v2.0+** — works on new NSE site; good for ad-hoc quotes.
- **yfinance** with `.NS` suffix — convenient cross-checking; adjusted closes are reliable for Nifty 50 names, but corporate-action handling occasionally lags NSE bhavcopy.
- **NSE/BSE direct** — RSS feeds at `nseindia.com/static/rss-feed` for corporate announcements, press releases, circulars; BSE has the `bse` Python wrapper (`pypi/bse`, `BennyThadikaran/BseIndiaApi`) for corporate actions, gainers/losers.

### 1.4 MVP recommendation

**Primary stack:** **Zerodha Kite Connect Personal (free) + jugaad-data + nselib for EOD OHLC, bhavcopy, and Nifty index history**. If you later want intraday tick data, upgrade Kite to ₹500/mo *or* switch to Dhan (free Data API once you cross 25 trades/month, ₹499 otherwise). **Avoid paying ₹2,000+/month — that pricing is obsolete post-Jun 2025.**

For a once-daily decision system that paper-trades for one month, **you need zero paid data**: bhavcopy at T+0 close + the official NSE corporate-announcement RSS + Moneycontrol / Economic Times RSS = ₹0/month.

---

## 2. Indian Market News & Sentiment Sources

### 2.1 Free or near-free news

| Source | Access mode | Notes |
|---|---|---|
| **NSE corporate announcements** | RSS at `nseindia.com/static/rss-feed`; JSON via reverse-engineered new NSE site (jugaad-data exposes parts) | Authoritative; required for results, board meetings, dividends. |
| **BSE announcements** | `BseIndiaApi` Python wrapper; partial RSS | Use for non-NSE listings (unlikely in Nifty 50). |
| **Moneycontrol** | RSS feeds (`moneycontrol.com/news`), site is scrape-friendly with rate-limiting | India's most-cited business outlet; closest to consensus retail sentiment. |
| **Economic Times Markets** | RSS at `economictimes.indiatimes.com` | Strong fundamentals/macro coverage. |
| **Livemint, Business Standard, NDTV Profit, Reuters India** | RSS available; some scraping | Layer for redundancy. |
| **NewsAPI.org / NewsData.io / GNews** | Free tier ~100 req/day | Multi-outlet keyword search; commercial use restricted on free tier. |
| **Finnhub** | Free tier covers India tickers (limited) | English summaries; used by StockBench. |
| **stockinsights.ai** | Paid; offers AI-tagged BSE/NSE announcements feed | Optional if you later outsource the announcement-summarization layer. |

### 2.2 Social sentiment

- **Twitter/X**: API Basic tier is $200/month (10k posts/month read) — **out of budget**. Skip for the MVP.
- **StockTwits India**: present but thin; less Indian retail volume than Twitter/Telegram.
- **Reddit** `r/IndianStockMarket`, `r/IndianStreetBets`, `r/IndiaInvestments`: free Reddit API (60 req/min OAuth); good signal-of-noise. **Include this.**
- **Telegram channels**: Telethon/Telegram API is free; useful but noisy — flag-only signal.

### 2.3 Sector-specific

- Banking: RBI press releases (RSS), credit-growth weekly data, MPC minutes.
- IT: NASSCOM commentary; USD/INR (RBI reference rate via `nselib`).
- FMCG: management commentary in quarterly results.
- Energy: PPAC daily price notification (PSU OMCs), Brent via investing.com RSS.

### 2.4 Legality of scraping in India

There is no specific Indian statute prohibiting scraping of publicly available pages for personal/non-commercial use, but the Indian Copyright Act 1957 protects article text. Safer pattern: **store URLs + headlines + timestamps + your derived sentiment scores, not full article bodies, and never redistribute.** Respect robots.txt and rate-limits. For a personal AWS-hosted system this is low-risk; publishing or selling signals materially changes the risk.

---

## 3. SEBI Regulations & Compliance for Personal Algo Trading

### 3.1 What the Feb 2025 framework actually requires of you

1. **Below 10 OPS → no separate algo registration.** A once-daily decision engine is trivially under this.
2. **Static IP whitelist** for *order-placing* IPs (one primary + one backup). Running on AWS, you must use an Elastic IP. **Lambda/Fargate ephemeral IPs will not work for order placement.** Data-only consumption from your AWS resources typically does *not* require static IP — check your broker's policy.
3. **Unique Algo ID** is assigned by the exchange via the broker to every API order. Auto-handled by the broker SDK.
4. **2FA** for the broker login is mandatory.
5. **No advice to others** — the moment you let a friend mirror your trades or publish signals, you become an "algo provider" and need broker empanelment + SEBI Research Analyst registration if your algo is black-box.

### 3.2 Paper trading regulation

**Paper trading is not regulated by SEBI** — it's just record-keeping. The regulated activities begin when you (a) place a real order through a broker API, (b) advise others, or (c) charge for signals. Your one-month paper run can be entirely simulated on your laptop/AWS with no broker static IP, no Algo ID, and no compliance touchpoints.

### 3.3 Taxation (so you're not surprised on Day 31 of real trading)

Per Income Tax India and the Finance Act 2024 (effective 23 July 2024):

| Trade type | Holding | Tax treatment | Rate |
|---|---|---|---|
| **Equity intraday** | Same day | **Speculative business income** (Sec 43(5)) | **Income-tax slab rates** |
| **Equity delivery ≤12 months** | Short-term | **STCG under Sec 111A** (if STT paid) | **20% flat** (raised from 15% on 23 Jul 2024) |
| **Equity delivery >12 months** | Long-term | **LTCG under Sec 112A** | **12.5%** above ₹1.25 lakh annual exemption |
| **Frequent positional/F&O** | n/a | Can be reclassified as **non-speculative business income** | Slab rates; allows expense deductions |

Your hybrid model (intraday OR up to 5 days): intraday round-trips → speculative business income at slab rates; 2–5 day swings → STCG at 20% (since holding <12 months and STT paid). STT itself is not income-tax deductible for capital-gains computation, but brokerage, exchange fees, GST, and stamp duty are deductible when reporting as business income. **ITR-3 is the form**. Maintain a daily P&L ledger and trade book from day 1.

---

## 4. Indian Transaction Cost Modelling (the most important section for honest paper-trading)

### 4.1 Cost components (NSE equity, 2025–2026)

| Component | Equity Delivery (CNC) | Equity Intraday (MIS) | Who collects |
|---|---|---|---|
| **Brokerage** (Zerodha/Dhan/Upstox flat) | ₹0 (delivery) / **min(₹20, 0.03%)** intraday | min(₹20, 0.03%) | Broker |
| **STT** | **0.1% on buy + 0.1% on sell** | **0.025% on sell only** | Government |
| **NSE transaction charge** | 0.00297% | 0.00297% | Exchange |
| **BSE transaction charge** | 0.00375% (group A/B) | 0.00375% | Exchange |
| **GST** | **18% on (brokerage + transaction + SEBI fee)** | 18% on (brokerage + txn + SEBI) | Government |
| **SEBI turnover fee** | ₹10 per crore (0.0001%) | ₹10 per crore | SEBI |
| **Stamp duty** (uniform since 1 Jul 2020 per Indian Stamp Act amendment) | **0.015% on buy side only** | **0.003% on buy side only** | State (via Centre) |
| **DP charges** | **₹15.93/scrip on sell** (NSDL/CDSL + Zerodha DP) | ₹0 | Depository + DP |

### 4.2 Worked example: ₹50,000 trade, ~Reliance, on Zerodha

**Delivery (CNC) scenario, buy ₹50,000 on Day 1, sell ₹50,500 on Day 2:**

| Charge | Buy | Sell | Total (₹) |
|---|---|---|---|
| Brokerage | 0 | 0 | **0** |
| STT (0.1% each side) | 50.00 | 50.50 | **100.50** |
| NSE txn (0.00297%) | 1.49 | 1.50 | **2.99** |
| GST (18% on brokerage + txn + SEBI) | 0.27 | 0.27 | **0.54** |
| SEBI (₹10/cr) | 0.005 | 0.005 | **0.01** |
| Stamp duty (0.015% buy) | 7.50 | 0 | **7.50** |
| DP charges | 0 | 15.93 | **15.93** |
| **Total round-trip cost** | | | **₹127.47** |
| **As % of buy value** | | | **0.255% ≈ 25.5 bps** |

**Intraday (MIS) scenario, ₹50,000 buy and sell same day:**

| Charge | Buy | Sell | Total (₹) |
|---|---|---|---|
| Brokerage (₹20 cap, 0.03%) | 15.00 | 15.15 | **30.15** |
| STT (0.025% on sell) | 0 | 12.50 | **12.50** |
| NSE txn (0.00297%) | 1.49 | 1.50 | **2.99** |
| GST | 2.97 | 3.00 | **5.97** |
| SEBI | 0.005 | 0.005 | **0.01** |
| Stamp duty (0.003% buy) | 1.50 | 0 | **1.50** |
| **Total round-trip cost** | | | **₹53.12** |
| **As % of buy value** | | | **0.106% ≈ 10.6 bps** |

### 4.3 Comparison to Kirtac & Germano (2024) 10 bps assumption

Kirtac & Germano used **10 bps round-trip cost** for their long-short U.S. strategy that produced **Sharpe 3.05 / 355% gain Aug 2021 – Jul 2023** (Finance Research Letters 62:105227). Mapping to India:

- **Intraday**: ~10.6 bps — almost identical to their assumption. Cost-comparable *if* you can replicate their signal in intraday.
- **Delivery (T+1)**: ~25.5 bps — **2.55× their assumption.** Sharpe degrades faster than gross return because losing trades become more frequent net.
- The **DP charge of ₹15.93 per scrip per sell day is *fixed*** — a ₹10,000 delivery trade pays 16 bps on DP alone. Position sizes >₹50,000 materially lower the cost percentage.

### 4.4 Slippage & impact cost

For Nifty 50 names with daily volumes ₹500 Cr+, slippage on a retail-sized ₹50,000 order is typically <2 bps at open/close auction and <5 bps intraday. NSE publishes "Impact Cost" for Nifty 50 constituents — most sit at <0.05% for a ₹1 lakh order. For mid/small-caps this can jump to 20–100 bps and the strategy is untradeable at scale.

**Realistic numbers to bake into your paper-trade simulator: 28–32 bps round-trip delivery, 15–18 bps intraday (large-cap), conservatively.**

---

## 5. Multi-Agent LLM Architecture for Trading

### 5.1 TradingAgents (Xiao, Sun, Luo, Wang — arXiv 2412.20138, rev. Jun 2025, v7)

Open-source at `TauricResearch/TradingAgents`, built on LangGraph; v0.2.0 released Feb 2026 with multi-provider LLM support. Agent topology:

1. **Analyst Team (4 in parallel)**: Fundamental, Sentiment, News, Technical — each gathers a different data stream.
2. **Research Team**: Bull Researcher and Bear Researcher *debate* (multi-turn LLM-vs-LLM dialogue) the analyst outputs.
3. **Trader Agent**: synthesizes the debate + analyst memos into a draft decision.
4. **Risk Management Team**: Aggressive / Conservative / Neutral perspectives feed back.
5. **Final Trader**: outputs the executable order.

**Reported performance (the paper itself flags as anomalously high):** TradingAgents beat five rule-based baselines by **6–26% cumulative return** over a 3-month backtest on tech stocks; Sharpe ratios **exceeded 5–8**, which the authors explicitly call out as likely "statistical anomalies" due to "few pullbacks in TradingAgents during that period" — they note that Sharpe >3 already qualifies as "excellent" and the highest result "exceeds our expected empirical range." Treat these results as upper-bound, not as a target.

For a lean MVP, **replicate the *roles* but collapse the parallelism**: a 5-agent sequential pipeline (News-Sentiment → Technical → Fundamentals → Bull-vs-Bear debate as a single dual-role prompt → Portfolio Manager) is sufficient. Running the full debate-rounds × 4 analysts × 3 risk personas can 10× your token spend.

### 5.2 StockBench (Chen, Yao et al., Tsinghua, arXiv 2510.02209v1, Oct 2025)

**The most important paper for calibrating your expectations.** The authors built a contamination-free benchmark on the **top 20 DJIA stocks, March 3 – June 30 2025 (82 trading days)**, starting each agent with $100,000 cash and zero holdings, with a deliberately *minimal single-agent 4-step daily workflow* (portfolio overview → in-depth stock analysis → JSON decision → execution validation). Context window 32,768 tokens; news capped at top-5 articles per stock from prior 48 hours (Finnhub).

**Headline results (Table 2, §3.2):**

| Model | Return % | Max DD % | Sortino | Rank |
|---|---|---|---|---|
| **Kimi-K2** | 1.9 | −11.8 | **0.0420** | **1** |
| **Qwen3-235B-Instruct** | 2.4 | **−11.2** | 0.0299 | **2** |
| GLM-4.5 | 2.3 | −13.7 | 0.0295 | 3 |
| Qwen3-235B-Thinking | 2.5 | −14.9 | 0.0309 | 4 |
| OpenAI-O3 | 1.9 | −13.2 | 0.0267 | 5 |
| Claude-4-Sonnet | 2.2 | −14.2 | 0.0245 | 7 |
| DeepSeek-V3.1 | 1.1 | −14.1 | 0.0210 | 8 |
| **GPT-5** | **0.3** | −13.1 | 0.0132 | 9 |
| DeepSeek-V3 | 0.2 | −14.1 | 0.0144 | 11 |
| **Passive Buy-and-Hold** | **0.4** | **−15.2** | **0.0155** | **12** |
| GPT-OSS-120B | −0.9 | −14.0 | 0.0156 | 13 |
| GPT-OSS-20B | −2.8 | −14.4 | −0.0069 | 14 |

**Critical findings for your MVP:**

- **GPT-5 barely beat baseline (0.3% vs 0.4% return)**. Frontier model ≠ alpha.
- **11 of 13 LLMs beat buy-and-hold on composite rank — mostly by *reducing drawdown***, not by generating return. *"Most tested models outperform the passive buy-and-hold baseline, which achieves a modest 0.4% return"* (§3.2). **LLM trading agents look more useful as risk-management overlays than as alpha generators.**
- **Failure modes (§4.2):** Two dominant errors — (1) arithmetic/sizing errors; (2) schema/JSON errors. **Thinking models reduce arithmetic but inflate schema errors**: Qwen3-235B-Thinking 14.5% schema-error rate vs Instruct 5.6%; DeepSeek-V3.1-Thinking 5.2% vs V3-Instruct 0.4%. *"Reasoning models tend to overthink and produce more complex outputs, which can lead to deviations from the expected format."* **You will spend more time on output validation than on prompt-engineering.**
- **Scalability (§4.1):** Performance degrades as universe grows. Kimi-K2 went from −4.6% (5 stocks) → +3.2% (10) → +1.9% (20) → −0.5% (30). **15 stocks is the sweet spot — your chosen universe size is well-justified.**
- **Data ablation (§4.3, Table 4):** Kimi-K2 full = 1.9%; without news = 1.4%; without news AND fundamentals = 0.6%. **News contributes ~0.5pp; fundamentals contribute ~0.8pp.** Both matter; smaller open models (GPT-OSS-120B) extract no value from news at all — only fundamentals.
- **Regime sensitivity (§4.4):** In a downturn (Jan–Apr 2025) **all LLM agents underperformed the passive baseline**; in an upturn most beat it. *"LLM agents may struggle to navigate bearish markets."* **Build a circuit-breaker for sustained drawdowns.**
- **Reproducibility caveat (Appendix D):** Variance ×10⁻⁴ ranges from DeepSeek-V3 = 0.074 to GPT-OSS-120B = 10.19. Kimi-K2 (the winner) variance = 1.866 — **even the #1 result is not reliably reproducible across seeds.**
- **Data-contamination caveat (Appendix C):** GPT-5 could "accurately predict the stock trend of AAPL in 2021" from training memorization. **Use a post-knowledge-cutoff evaluation window** — anything before late 2024 is suspect.
- **Authors' ethical statement:** *"StockBench is not intended to offer, or serve as the basis for, any financial advice, trading recommendation, or commercial activity. Any trading strategy tested on StockBench carries inherent market risk; past performance recorded in the benchmark does not guarantee future returns."*

### 5.3 Kirtac & Germano (2024) — Finance Research Letters 62:105227 / arXiv 2412.19245

965,375 U.S. financial news articles 2010–2023, evaluating OPT (GPT-3-based), BERT, FinBERT, Loughran-McDonald. **OPT achieved 74.4% accuracy** in predicting next-day return sign, **Sharpe 3.05 with 10 bps round-trip costs**, **355% cumulative Aug 2021 – Jul 2023**. Execution timing rules (directly portable to IST):

- **News before 06:00**: enter at the open *the same day*, exit at the close *same day*.
- **News 06:00–16:00**: enter at the close *same day*, exit at the close of *the next trading day*.
- **News after 16:00**: enter at the open of the *next* trading day, exit at the close of *that next trading day*.

For India (NSE pre-open 09:00–09:15, normal session 09:15–15:30): map "before 06:00" → news before 09:00 IST; "06:00–16:00" → news during session + early evening to ~21:00 IST; "after 16:00" → news after 21:00 IST.

**Why Sharpe 3.05 will not reproduce for you:** (a) U.S. universe with English Refinitiv-clean ticker mapping; (b) full long-short with shorting (Indian shorting in cash market is intraday-only); (c) ~3,000 stocks vs your 15; (d) 13 years of data smooths idiosyncratic events; (e) Indian delivery costs are 25.5 bps vs their 10 bps; (f) top-quintile minus bottom-quintile portfolios need cross-section a 15-stock universe lacks. **Realistic ceiling: Sharpe 0.5–1.0; realistic baseline: ~0.**

### 5.4 Other 2024–2026 multi-agent trading papers worth knowing

- **FinMem** (Yu et al., Nov 2023, arXiv 2311.13743) — single-agent with 3-layer memory (Profile / Memory / Decision); layered short/medium/long memory with decay. Useful interpretability pattern.
- **FinAgent** (Zhang et al., Feb 2024, arXiv 2402.18485) — multimodal (chart images + tabular + audio earnings calls); tool-augmented; beats DRL baselines.
- **FinRobot** (Yang et al., May 2024, arXiv 2405.14767) — tri-CoT (Data-CoT → Concept-CoT → Thesis-CoT) sequential workflow simulating a human equity analyst.
- **FINCON** (Yu et al., NeurIPS 2024) — multi-agent synthesis with "conceptual verbal reinforcement"; criticizes FinMem/FinAgent as too noisy/indecisive.
- **Trading-R1** (Xiao et al., 2025, arXiv 2509.11420) — RL fine-tuning for trading reasoning.
- **FinDPO** (Iacovides et al., Jul 2025, arXiv 2507.18417) — Direct Preference Optimization for finance sentiment; claims better OOS generalization than SFT.
- **Event-Aware Sentiment Factors** (Wang & Wei, ICML 2025, arXiv 2508.07408) — LLM-assigned multi-label event categories from tweets; some labels have ICs >0.05 but **also negative-alpha categories** — reminder that "sentiment" ≠ "signal".

### 5.5 Cost-efficient model assignment for your 5-agent pipeline

| Agent | Model | Rationale | Approx. cost/decision/stock |
|---|---|---|---|
| **News/Sentiment Analyst** | Gemini 2.5 Flash | Cheapest with 1M context; ingests many articles | $0.0005 |
| **Technical Analyst** | DeepSeek V3.2 (standard $0.14/$0.28 per 1M tokens at cache-miss; $0.014/M with cache hit) or Gemini 2.5 Flash | Mostly numeric, structured | $0.0003 |
| **Fundamentals Analyst** | Claude Haiku 4.5 | Better quantitative-narrative summarization | $0.001 |
| **Bull vs Bear debate** | Claude Haiku 4.5 (both roles in one prompt) | Quality of argument matters | $0.002 |
| **Portfolio Manager (final)** | Claude Sonnet 4.6 OR GPT-5.4 mini | This is the decision; stronger model warranted | $0.005 |

**Per-day, 15 stocks: ≈ $0.13. Per-month (21 trading days): ≈ $2.70 — well under budget.** Add a 3× buffer for retries/longer prompts → **~$8–$10/month** for LLMs.

### 5.6 Prompt engineering patterns for finance

1. **Structured JSON outputs** with explicit schema and example. Enforce with `response_format` (Anthropic tool use; OpenAI structured outputs; Gemini schema). **Single most impactful reliability lever** per StockBench §4.2.
2. **Role conditioning** — "You are the bear researcher arguing why this stock will fall over the next 5 days" — significantly improves debate quality.
3. **Chain-of-thought + explicit confidence** — ask for `reasoning` + `confidence_0_to_1`. Track calibration over time.
4. **Few-shot with 2–3 historical examples** of correctly-formatted outputs reduces schema errors ~5–10%.
5. **Self-consistency for the final PM** — sample 3 PM outputs at temperature 0.3, take majority decision. Cheap reliability win.
6. **Prompt caching** — Anthropic's official docs (`platform.claude.com/docs/en/build-with-claude/prompt-caching`): *"Cache read tokens are 0.1 times the base input tokens price"* — exactly **90% discount** on cache reads; cache writes cost 1.25× standard input for a 5-minute TTL; break-even after just two cache reads. Cache the system prompt + market-rules + ticker descriptions. **This alone can cut 70–90% of input-token cost** when the same boilerplate runs across 15 stocks.

---

## 6. Lean-Budget LLM Strategy (under ~$25/month)

### 6.1 Token budget estimate

Per stock per day:
- News input: ~2,000 tokens × 5 articles = ~10,000 tokens, ~80% cached → ~2,000 fresh.
- Technical/fundamentals: ~1,500 fresh.
- Bull/bear debate: ~3,000 output, ~2,000 input each side.
- PM final: ~3,000 input + 800 output.

Per-stock-per-day: ~12,000 input + ~5,000 output (Gemini Flash/Haiku-blended) ≈ **$0.008 raw, ~$0.003 with 70% caching**.
Per day, 15 stocks: ~$0.05–$0.13. Per month (21 trading days): **~$1–$3 baseline; budget $10 with buffer**.

### 6.2 Pricing snapshot (Q1 2026, per 1M tokens)

| Model | Input | Output | Notes |
|---|---|---|---|
| **Gemini 2.5 Flash** | $0.30 | $2.50 | 1M context; batch + cache discounts |
| **Gemini 2.5 Flash-Lite** | $0.10 | $0.40 | Even cheaper; slight quality drop |
| **DeepSeek V3.2 (standard)** | $0.14 | $0.28 | Cheapest competitive; cache-hit input falls to $0.014/M. (V3.2-Exp variant is $0.27/$0.41 on OpenRouter; V3.2-Speciale $0.40/$1.20.) Higher latency, lower API uptime. |
| **GPT-5.4 mini / GPT-4.1 Mini** | $0.40–$0.75 | $1.60–$4.50 | Strong instruction-following |
| **Claude Haiku 4.5** | $1.00 | $5.00 | 200K context; 90% cache-read discount, 50% batch discount |
| **Claude Sonnet 4.6** | $3.00 | $15.00 | Use only for the final PM if you escalate |
| **GPT-5.4 / GPT-5.5** | $2.50–$5.00 | $14–$30 | Frontier; per StockBench, no alpha translation |

### 6.3 Caching & retrieval strategies

- **Anthropic prompt caching (90% off cache reads, exact)** — cache the system prompt, decision-rules doc (market hours, cost model, risk policy), and per-ticker static metadata (sector, market cap, beta, last 4 quarter summaries). Single biggest cost lever.
- **Embedding-based news dedup** — `text-embedding-3-small` ($0.02/1M) or Gemini text-embedding; cosine similarity >0.92 → dedupe before LLM.
- **Summarize-then-decide** — run Flash/Haiku to compress 20 articles → 1 paragraph per stock; pass only summaries to the PM.
- **Skip-trading on quiet days** — if no news in 24h and no >2% intraday move, skip the full agent pipeline for that stock and inherit prior position. ~50% cost saving on average.

---

## 7. MVP Architecture Blueprint (mapped to user stack)

### 7.1 System diagram (logical)

```
                       EventBridge (cron: 17:00 IST Mon-Fri)
                                    │
                                    ▼
   ┌──────────────────────────── ECS Fargate task ──────────────────────────────┐
   │  1. Data Ingestion (Python)                                                │
   │     - jugaad-data: EOD bhavcopy + per-stock OHLC                           │
   │     - nselib: index history (Nifty 50 TRI proxy), FII/DII                  │
   │     - NSE/BSE RSS: corporate announcements                                 │
   │     - Moneycontrol/ET RSS + Reddit API: news + sentiment raw               │
   │     ▼                                                                      │
   │  2. Storage layer                                                          │
   │     - DynamoDB: ticker, signals, trades, positions, daily NAV              │
   │     - Redis (Upstash free tier or in-container): hot quote cache,          │
   │       deduped news, prompt cache keys                                      │
   │     - S3: raw bhavcopy archives, news snapshots, decision logs (jsonl)     │
   │     ▼                                                                      │
   │  3. Multi-Agent Orchestration (FastAPI + LangGraph 1.2.x)                  │
   │     - News-Sentiment → Technical → Fundamentals → Bull/Bear → PM           │
   │     - SQS only if agents fan out (skip for MVP)                            │
   │     - Secrets Manager: LLM + broker API keys                               │
   │     ▼                                                                      │
   │  4. Paper-trading ledger                                                   │
   │     - DynamoDB writes: simulated fills, P&L, position changes              │
   │     - CloudWatch logs: every prompt/output/decision                        │
   └────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
       Next.js dashboard (Vercel free tier) — GraphQL/REST → FastAPI
```

### 7.2 AWS deployment shape

| Component | Service | Free-tier coverage |
|---|---|---|
| Scheduled run | **EventBridge** (cron) | Free for default bus events |
| Compute | **ECS Fargate** (single task, ~5 min/day) | ~$0.04/run = ~$1.20/month |
| Storage | **DynamoDB on-demand** | 25 GB free, 25 WCU/RCU; usage <1 GB |
| Hot cache | **Upstash Redis free tier** or in-container | $0 |
| Object archive | **S3 Standard** | 5 GB free first 12 months |
| Logging | **CloudWatch Logs** | 5 GB ingest free |
| Secrets | **Secrets Manager** | $0.40/secret/month — 2 secrets = ~$0.80 |
| Static IP for broker (only when live) | **Elastic IP on t4g.nano** ($3/mo) or NAT Gateway+EIP | Free EIP while attached to running instance |

**Estimated AWS bill for the paper-trading month: $3–$8.** Combined with LLMs (~$8–$10), total ~$15/month — comfortably under ₹2,000.

### 7.3 Framework choice: LangGraph

Use **LangGraph 1.2.x** (1.0 released 22 October 2025; current as of May 2026 is 1.2.1 per `langchain-ai/langgraph` releases). Rationale:
- TradingAgents reference implementation is already in LangGraph — direct adaptability.
- Best state-persistence and checkpointing for replay/debugging.
- Token overhead lower than CrewAI or AutoGen in production benchmarks.
- Native Python — fits your FastAPI backend.
- Optional swap-out to your AgentTree library for any single node.

Skip CrewAI for now (role-DSL adds tokens) and AutoGen (harder to make deterministic — and you want determinism for audit/replay).

### 7.4 Terraform IaC outline

```hcl
# infra/main.tf — sketch only
resource "aws_dynamodb_table" "positions" { /* PK ticker, SK date */ }
resource "aws_dynamodb_table" "decisions" { /* PK date, SK ticker#agent */ }
resource "aws_dynamodb_table" "trades"    { /* PK date, SK trade_id */ }
resource "aws_dynamodb_table" "nav_daily" { /* PK date */ }
resource "aws_s3_bucket"      "archive"   { }
resource "aws_secretsmanager_secret" "llm_keys" { }
resource "aws_secretsmanager_secret" "broker_keys" { }
resource "aws_ecs_cluster"    "trader"    { }
resource "aws_ecs_task_definition" "daily_run" { /* 1 vCPU, 2 GB; python -m trader.daily */ }
resource "aws_cloudwatch_event_rule" "weekday_close" {
  schedule_expression = "cron(30 10 ? * MON-FRI *)"   # 16:00 IST = 10:30 UTC
}
resource "aws_cloudwatch_event_target" "run_task" { /* invokes ECS task */ }
```

### 7.5 DynamoDB schemas

```python
# positions
{ "PK": "TICKER#RELIANCE",
  "SK": "2026-05-26",
  "qty": 100, "avg_price": 2840.50,
  "entry_date": "2026-05-24", "strategy": "swing", "hold_max_days": 5 }

# decisions  (one row per agent per stock per day)
{ "PK": "DATE#2026-05-26",
  "SK": "TICKER#RELIANCE#AGENT#PortfolioManager",
  "decision": "HOLD",
  "confidence": 0.62,
  "reasoning": "...",
  "input_tokens": 4321, "output_tokens": 612,
  "model": "claude-haiku-4.5",
  "agent_outputs_ref": "s3://.../2026-05-26/RELIANCE/agents.jsonl" }

# trades (paper-trade fills)
{ "PK": "DATE#2026-05-26",
  "SK": "TRADE#0001",
  "ticker": "RELIANCE", "side": "BUY", "qty": 20, "fill_price": 2840.50,
  "simulated_cost_bps": 28, "ledger_after": 50000.00 }

# nav_daily
{ "PK": "DATE#2026-05-26",
  "nav": 1015000.00, "cash": 250000.00, "equity_value": 765000.00,
  "daily_return_pct": 0.42, "drawdown_pct": -1.1, "nifty50_close": 24210.55 }
```

### 7.6 Folder layout

```
trader/
  ├── ingestion/      # jugaad, nselib, rss scrapers, dedup
  ├── agents/
  │     ├── news.py
  │     ├── technical.py
  │     ├── fundamentals.py
  │     ├── bull_bear.py
  │     └── portfolio_manager.py
  ├── orchestration/  # LangGraph graph definition
  ├── ledger/         # paper-trading engine, cost model, slippage
  ├── metrics/        # Sharpe, Sortino, drawdown, attribution
  ├── api/            # FastAPI app for the dashboard
  ├── prompts/        # versioned prompts as .md files
  └── tests/

dashboard-next/        # Next.js, Tailwind, ApexCharts
infra/                 # Terraform
```

### 7.7 Example: Kite Connect call (when you go live)

```python
from kiteconnect import KiteConnect
kc = KiteConnect(api_key=API_KEY)
kc.set_access_token(ACCESS_TOKEN)
order_id = kc.place_order(
    variety=kc.VARIETY_REGULAR,
    exchange=kc.EXCHANGE_NSE,
    tradingsymbol="RELIANCE",
    transaction_type=kc.TRANSACTION_TYPE_BUY,
    quantity=20,
    product=kc.PRODUCT_CNC,     # or PRODUCT_MIS for intraday
    order_type=kc.ORDER_TYPE_LIMIT,
    price=2840.50,
    tag="agent_v1_swing")        # 20-char tag for attribution
```

### 7.8 Example: Portfolio Manager prompt (skeleton)

```text
SYSTEM (cached):
You are the Portfolio Manager for a personal Indian-equity trading account.
Universe: 15 large-cap NSE stocks. Rules:
- Max 15% of NAV per position. - Max 5 open positions. - Reject any ticker on the NSE ASM, GSM, or T2T list.
- Hold up to 5 trading days. - Honor circuit limits and IST market hours (09:15-15:30).
- Account for ~28 bps round-trip cost (delivery) when scoring conviction.

USER (per stock, per day):
TICKER: {ticker}
PRICE_CONTEXT: {last_5d_ohlc}
TECHNICAL_AGENT: {technical_memo}
FUNDAMENTALS_AGENT: {fundamentals_memo}
NEWS_SENTIMENT_AGENT: {news_memo, top_3_headlines}
BULL_RESEARCHER: {bull_memo}
BEAR_RESEARCHER: {bear_memo}
CURRENT_POSITION: {qty, entry_price, days_held}

Output strict JSON:
{
 "decision": "BUY" | "SELL" | "HOLD" | "EXIT",
 "target_qty_pct_of_nav": 0.0-0.15,
 "horizon_days": 1-5,
 "confidence": 0.0-1.0,
 "primary_thesis": "<=2 sentences",
 "kill_conditions": ["e.g. close below 50DMA", "negative result surprise"]
}
```

---

## 8. 30-Day Paper-Trading Evaluation Framework

### 8.1 Metrics to track daily

| Metric | Definition | Why it matters |
|---|---|---|
| **Cumulative return** | (NAV_T − NAV_0) / NAV_0 | Headline number |
| **Daily P&L distribution** | mean, stdev, skew | Tail visibility |
| **Sharpe (annualized)** | √252 × mean_daily / stdev_daily | Risk-adjusted; **21 obs gives huge std error** |
| **Sortino (annualized)** | √252 × mean_daily / downside_stdev | Better tail-aware |
| **Max drawdown** | min(cum P&L − running max) | Real-money killer |
| **Win rate** | wins / total trades | Texture |
| **Avg win / Avg loss** | | If skewed positive, low win-rate is fine |
| **Profit factor** | sum(wins) / abs(sum(losses)) | >1.5 is decent |
| **Hold-time distribution** | histogram of days_held | Confirms swing vs. intraday mix |
| **Per-agent hit rate** | for each agent's directional call, % aligned with realized 5-day return | Tells you which agent to trust |
| **Inter-agent agreement** | Cohen's kappa pairwise | High agreement = redundant agents; useful debate signal |
| **Cost-as-pct-of-gross-return** | total simulated costs / gross P&L | If >50%, you're churning |

### 8.2 Benchmarks

1. **Nifty 50 Total Return Index** (closest market beta).
2. **Equal-weighted basket** of your 15 chosen stocks (controls stock-selection vs. timing).
3. **5-day momentum baseline**: each Monday, buy top 5 by trailing 5-day return; hold for the week.
4. **Mean-reversion baseline**: buy bottom 5 by trailing 5-day return.
5. **Buy-and-hold** (most important per StockBench).

### 8.3 Honest statistical-significance caveats

With ~21 trading days, **you cannot statistically distinguish skill from luck.** To claim a true Sharpe ≥ 1.0 at 5% significance against a Sharpe-0 null requires ≥ ~1-year sample. With 21 obs, the 95% CI on a measured Sharpe of 1.0 spans roughly **−1.5 to +3.5**. **The one-month run is a *systems test*, not a strategy validation.** Conclusions you *can* draw:
- Whether the pipeline ran end-to-end every trading day.
- Whether agent outputs were schema-valid (target ≥98%).
- Whether agent disagreement correlated with outcome variance.
- Whether your cost model and benchmark calculations are correct.

**Extend to 6 months minimum before considering real money.**

### 8.4 Logging architecture

For every decision, store in S3 + DynamoDB:
- Date, ticker, agent role, model, model version.
- **Full prompt** (post-templating) and **full output** (raw text + parsed JSON).
- Input/output token counts and cost.
- Realized 1-day, 3-day, 5-day forward returns (filled in over the next week).
- Whether the trade was simulated as executed; simulated cost in bps.

This corpus is **the only durable asset of the MVP** — even if returns are random, you'll have a labeled prompt/response/outcome dataset for prompt iteration and later fine-tuning.

### 8.5 Circuit breakers / kill-switches

| Condition | Action |
|---|---|
| Portfolio drawdown ≥ 10% from peak | Pause new entries; only exits allowed |
| Single position >15% of NAV | Block any further BUY on that ticker |
| Sector concentration >40% of NAV | Block BUYs in over-weighted sector |
| Ticker added to NSE ASM / GSM / T2T list | Force EXIT |
| LLM schema-error rate >5% in last 5 runs | Pause pipeline; alert via SNS |
| Daily LLM cost >$1 | Investigate (typically a stuck loop) |
| News older than 48h | Down-weight in news agent |

---

## 9. Risks, Pitfalls, and Honest Limitations

1. **Look-ahead bias from LLM training data.** Per StockBench Appendix C, GPT-5 can reproduce 2021 AAPL trajectories from memory. Any backtest before late 2024 is suspect. **Mitigation**: paper-trade only on forward, post-cutoff dates. Do not use LLM-driven backtests as validation. (See arXiv 2601.13770 "Look-Ahead-Bench" for a formal benchmark.)
2. **Survivorship bias.** Today's Nifty 50 is by definition the survivors. A multi-year backtest on today's Nifty 50 ignores deletions (e.g., Vedanta, ZEEL). For 1-month forward paper trading this is moot; **never claim multi-year backtest results without point-in-time index membership.**
3. **Why Sharpe 3.05 will not reproduce for you**: smaller universe (15 vs ~3,000), no delivery shorting in India, 25.5 bps Indian costs vs 10 bps US assumed, English-only news pipelines miss Hindi/regional context driving Indian retail, RSS-scraped news vs Refinitiv-curated. **Realistic ceiling: Sharpe 0.5–1.0; realistic baseline: ~0.**
4. **Intraday paper-trading overstates real returns**. No real fills, slippage, liquidity rejection, margin calls, or exchange throttling. **Mitigation**: use closing-auction prices not LTPs; add 5 bps slippage intraday, 2 bps delivery; randomly reject 5% of intended fills.
5. **Indian-specific friction**:
   - **Circuit limits** 5/10/20%. Your order at the day's circuit price *will not fill*. Simulate this.
   - **ASM / GSM / T2T**: stocks added with 1-day notice; margin jumps to 100%; T2T disallows intraday netting. Check daily lists; exit positions if your holding enters Stage 1+.
   - **NSE holidays + Muhurat trading**: pull holiday calendar from NSE; do not run on declared holidays.
   - **T+1 settlement** for most equities since Jan 2023; full T+0 in beta. Funds may not be redeployable for 1 day after a sell.
   - **STT increase on F&O announced in Union Budget FY2024-25 (Finance Minister Nirmala Sitharaman, 23 July 2024, effective 1 October 2024):** STT on futures sales raised from 0.0125% to 0.02% of traded price; STT on options sales raised from 0.0625% to 0.1% of premium. *"Options will now attract 0.1 per cent STT, while the same for futures will stand at 0.02 per cent"* (Business Standard, 23 Jul 2024). Irrelevant to your equity-only MVP but watch the next budget.
   - **Currency-specific**: USD/INR moves can drive IT-sector returns more than company news.
6. **Multi-agent pipelines can be theatre.** TradingAgents shows debate helps; FINCON criticizes single-agent FinMem as too indecisive; StockBench deliberately uses single-agent design and concludes minimal workflow is best to avoid biasing toward one model. **Verdict**: ship a 5-agent pipeline because it gives you better attribution data, not because there's strong evidence it outperforms a well-prompted single agent.
7. **Frontier model ≠ alpha.** Per StockBench Table 2: GPT-5 final return 0.3%; passive buy-and-hold 0.4%. Kimi-K2 (an open MoE model) ranked #1 by composite score. **Spending on Sonnet 4.6 or GPT-5.5 for the PM buys schema adherence, not expected return.**
8. **Honest expected outcome of this MVP**: a working, observable, version-controlled multi-agent pipeline producing auditable daily decisions on 15 NSE stocks under ₹2,000/month; ~21 days of decision logs as a labeled dataset; clear evidence of which agent contributes signal and which is noise; a calibrated transaction-cost model; **no statistically significant alpha**. Anyone selling you a different expectation is selling something.

---

## 10. Suggested 4-Week Build Plan

### Week 1 — Data & Plumbing
**Goal:** Ingest, store, and visualize EOD data + news for 15 chosen Nifty stocks.

- **D1–D2**: Pick the 15 tickers (suggested: 10 mega-caps RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, HINDUNILVR, ITC, LT, AXISBANK, KOTAKBANK + 5 high-news names BHARTIARTL, MARUTI, BAJFINANCE, ASIANPAINT, ADANIENT). Terraform AWS skeleton, DynamoDB tables, Secrets Manager, S3 archive bucket.
- **D3–D4**: Implement `ingestion/` with jugaad-data EOD pull + bhavcopy archival + NSE/BSE RSS + Moneycontrol/ET RSS + Reddit API. Dedupe with cosine similarity.
- **D5–D7**: Build paper-trading ledger with realistic 28-bps delivery / 11-bps intraday cost model; wire up Nifty 50 TRI as benchmark.

**Acceptance**: One command runs end-to-end ingestion for one day; you can pull yesterday's OHLC + ≥10 news items per ticker; cost model verified against published Zerodha calculator for 3 test trades.

### Week 2 — Agents & Decisions
**Goal:** All 5 agents return validated JSON for all 15 stocks.

- **D8–D10**: Build News/Sentiment, Technical, Fundamentals agents. Gemini 2.5 Flash for News + Technical; Claude Haiku 4.5 for Fundamentals.
- **D11–D12**: Bull/Bear debate (single LLM, two personas, 2 rounds max).
- **D13–D14**: Portfolio Manager with strict JSON schema + self-consistency (3 samples). Claude Sonnet 4.6 or Haiku 4.5 depending on early cost data.

**Acceptance**: ≥98% schema-valid outputs across a 3-day dry run; total daily LLM cost <$0.40; LangGraph state checkpointed for replay.

### Week 3 — Dashboard, Benchmarks, Risk
**Goal:** End-to-end loop with monitoring.

- **D15–D17**: Next.js dashboard — NAV vs Nifty 50 chart, decision log with debate viewer, per-stock confidence heatmap, cost breakdown.
- **D18–D19**: Implement all 5 benchmarks (Nifty 50 TRI, equal-weight, momentum, mean-reversion, buy-and-hold) in `metrics/`.
- **D20–D21**: Wire circuit breakers (drawdown, position size, sector, ASM/GSM, schema-error rate). CloudWatch alarms + SNS notifications.

**Acceptance**: Dashboard loads <2s; benchmarks recompute nightly; a manually-injected ASM ticker triggers an EXIT signal in next run.

### Week 4 — The 30-Day Run + Analysis
**Goal:** 21 trading days of paper trading with full logging, then a written post-mortem.

- **D22–D42**: Run daily at 17:00 IST (after market close, news settled). Daily 15-min review of decision log; weekly check of all metrics.
- **D43–D45**: Post-mortem. Compute final Sharpe / Sortino / drawdown vs each benchmark. Per-agent hit rate. Agreement-vs-outcome heatmap. Cost-as-pct-of-gross-return. Identify top 2 lessons for v2.

**Acceptance — what "success" actually means**:
1. ≥95% of trading days the full pipeline ran without manual intervention.
2. ≥97% schema-valid outputs from all agents.
3. Total spend ≤ ₹2,000.
4. A written post-mortem identifying ≥3 prompt-engineering improvements to ship in v2.
5. A labeled dataset of 21 × 15 × 5 ≈ 1,575 (decision, prompt, outcome) tuples ready for analysis.

**Returns vs the Nifty 50 are not in the success criteria.** If you happen to beat the benchmark, that's a hypothesis worth testing on a longer window — never proof.

---

## Recommendations (decision-ready)

1. **Start now with: Zerodha Kite Connect Personal (free) + jugaad-data + nselib + LangGraph 1.2.x + Claude Haiku 4.5 (PM) + Gemini 2.5 Flash (analysts) + Next.js on Vercel free tier + AWS Fargate cron.** Expected monthly burn: ₹800–₹1,300.

2. **Cap your universe at 15 names** — per StockBench §4.1, performance degrades sharply at 20+ stocks; 5–15 is the sweet spot.

3. **Build the cost simulator first.** Use 28 bps round-trip delivery and 11 bps intraday. Validate against Zerodha's published calculator on 5 worked trades. If your cost model is wrong, every downstream metric is wrong.

4. **Cache aggressively (Anthropic 90% cache-read discount, exact).** Single most impactful LLM-cost lever — typically 4–8× cheaper than naive prompting.

5. **Treat the 30-day result as systems calibration, not strategy validation.** If you intend to evaluate alpha, extend the paper trade to **6 months minimum** before sizing real money. Even then, realistic Sharpe is 0.0–1.0, not 3.0.

6. **Escalation criteria to graduate to real money**: 6 months of forward paper trading; Sharpe ≥ 0.7 vs Nifty 50 TRI; max drawdown ≤ 12%; schema-validity ≥ 99%; cost-as-pct-of-gross-return ≤ 35%. If any one of these isn't met, do not deploy capital.

7. **De-escalation triggers in live trading**: 5% live drawdown in first 2 weeks → switch back to paper; any execution slippage >2× simulated → recalibrate cost model and re-paper-trade.

8. **What NOT to do**: don't pay for Twitter/X API; don't use frontier models for analyst roles; don't run order placement on Lambda (no static IP); don't believe any backtest before Nov 2024; don't add F&O until equities work; don't share signals (it changes your regulatory status).

---

## Caveats

- **LLM pricing moves fast**: the Q1 2026 numbers cited above (Haiku 4.5 at $1/$5; Gemini 2.5 Flash at $0.30/$2.50; GPT-5.4 mini at $0.75/$4.50; DeepSeek V3.2 standard at $0.14/$0.28) are likely to drop further by mid-2026; recheck before locking model choices.
- **DeepSeek pricing varies by variant**: the figures above are for V3.2 standard (cache-miss); V3.2-Exp is $0.27/$0.41, V3.2-Speciale is $0.40/$1.20.
- **SEBI implementation is still being refined**: the Oct 2025 NSE operational guidelines may tighten further. Re-read your broker's algo-trading policy page before going live.
- **All performance numbers from Kirtac & Germano (2024) are on U.S. equities** (Refinitiv news + CRSP price data). No published replication exists for Indian markets as of May 2026.
- **StockBench (arXiv 2510.02209v1) was published October 2025 with a March–June 2025 evaluation window** and uses DJIA, not Nifty. Its findings about "most LLM agents barely beat buy-and-hold" are the most generalizable insight.
- **TradingAgents' reported Sharpe ratios of 5–8** are flagged by the authors themselves as likely statistical anomalies — do not target these as expected performance.
- **One trading month ≈ 21 observations** is not enough to claim alpha. Do not extrapolate.
- **The library landscape (LangGraph, jugaad-data, nselib, broker APIs) is maintained by small teams or individuals.** Pin versions in `requirements.txt`/`package.json` and budget a half-day per quarter for dependency-rot maintenance.
- **Tax filings**: paper trading produces no tax liability, but the moment you go live, every intraday trade is speculative business income reportable in ITR-3. Engage a CA familiar with active-trader tax filings before going live.