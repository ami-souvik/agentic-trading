"""
FII/DII daily flow data for the Indian equity market.

Primary source: nselib capital_market module.
Falls back to a zero-value placeholder on failure so the pipeline can continue —
the Portfolio Manager agent will note the data_staleness context accordingly.
"""
from __future__ import annotations

import logging
from datetime import date
from .cache import Cache

logger = logging.getLogger(__name__)

_CACHE_TTL = 23 * 3600  # 23 hours — same day re-use
C = Cache(_CACHE_TTL)

_EMPTY_FLOWS = {
    "fii_net_buy_cr": 0.0,
    "dii_net_buy_cr": 0.0,
    "date": "",
    "source": "unavailable",
}


def _try_nselib(trade_date: date) -> dict | None:
    """
    Attempt to fetch FII/DII data via nselib.

    fii_dii_trading_activity lives in capital_market_data.py but is NOT
    re-exported from capital_market/__init__.py, so we import from the
    submodule directly.  The function takes no arguments — it always fetches
    today's live data from NSE.  Values are already in ₹ crore.
    """
    try:
        from nselib.capital_market.capital_market_data import (  # type: ignore
            fii_dii_trading_activity,
        )

        df = fii_dii_trading_activity()  # no date args — live data only

        if df is None or df.empty:
            return None

        logger.debug("FII/DII nselib columns: %s", df.columns.tolist())

        # Normalise column names for matching
        df.columns = [str(c).strip() for c in df.columns]
        col_lower = {c.lower().replace(" ", "_"): c for c in df.columns}

        fii_net = dii_net = 0.0

        # Layout A: flat columns like netFII / NET_FII / netDII / NET_DII
        for key, orig in col_lower.items():
            try:
                val = float(df[orig].iloc[-1] or 0)
            except Exception:
                continue
            if "fii" in key and "net" in key:
                fii_net = val
            elif "dii" in key and "net" in key:
                dii_net = val

        # Layout B: rows keyed by category column (FII/FPI | DII) with netValue
        if fii_net == 0.0 and dii_net == 0.0 and "category" in col_lower:
            cat_col = col_lower["category"]
            net_col = next(
                (col_lower[k] for k in col_lower if "net" in k and "value" in k), None
            )
            if net_col:
                for _, row in df.iterrows():
                    cat = str(row[cat_col]).upper()
                    net = float(row.get(net_col) or 0)
                    if "FII" in cat:
                        fii_net = net
                    elif "DII" in cat:
                        dii_net = net

        # NSE API already returns values in ₹ crore — no unit conversion needed
        return {
            "fii_net_buy_cr": round(fii_net, 2),
            "dii_net_buy_cr": round(dii_net, 2),
            "date": trade_date.isoformat(),
            "source": "nselib",
        }
    except Exception as e:
        logger.warning("nselib FII/DII fetch failed for %s: %s", trade_date, e)
        return None


def _try_nse_direct(trade_date: date) -> dict | None:
    """
    Attempt to fetch FII/DII data from NSE's public JSON endpoint.
    """
    import httpx
    try:
        url = "https://www.nseindia.com/api/fiidiiTradeReact"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/",
        }
        with httpx.Client(follow_redirects=True, timeout=20.0, headers=headers) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()

        if not data:
            return None

        # API returns a list; find the row matching trade_date
        date_str_formats = [
            trade_date.strftime("%d-%b-%Y").upper(),
            trade_date.strftime("%d-%m-%Y"),
        ]

        for row in data:
            row_date = str(row.get("date", row.get("Date", ""))).strip()
            if row_date in date_str_formats:
                fii_net = float(row.get("netFII", row.get("FII_NET", 0)) or 0)
                dii_net = float(row.get("netDII", row.get("DII_NET", 0)) or 0)
                return {
                    "fii_net_buy_cr": round(fii_net, 2),
                    "dii_net_buy_cr": round(dii_net, 2),
                    "date": trade_date.isoformat(),
                    "source": "nse_api",
                }

        # If exact date not found, use latest row as approximation
        if data:
            row = data[0]
            fii_net = float(row.get("netFII", row.get("FII_NET", 0)) or 0)
            dii_net = float(row.get("netDII", row.get("DII_NET", 0)) or 0)
            return {
                "fii_net_buy_cr": round(fii_net, 2),
                "dii_net_buy_cr": round(dii_net, 2),
                "date": trade_date.isoformat(),
                "source": "nse_api_latest",
            }
    except Exception as e:
        logger.warning("NSE direct FII/DII fetch failed for %s: %s", trade_date, e)

    return None


def fetch_fii_dii_flows(trade_date: date) -> dict:
    """
    Return FII/DII net buy/sell data for the given trading date.

    Result keys:
      fii_net_buy_cr (float): FII net buy in ₹ crore (negative = net sell)
      dii_net_buy_cr (float): DII net buy in ₹ crore
      date (str): ISO date string
      source (str): data source identifier

    Falls back to zeros if all sources fail — the caller should lower confidence.
    """
    cache_key = f"fii_dii:{trade_date.isoformat()}"
    cached = C._get(cache_key)
    if cached is not None:
        logger.debug("FII/DII cache hit for %s", trade_date)
        return cached

    result = _try_nselib(trade_date)
    if result is None:
        result = _try_nse_direct(trade_date)
    if result is None:
        logger.warning("All FII/DII sources failed for %s; using zero placeholder", trade_date)
        result = {**_EMPTY_FLOWS, "date": trade_date.isoformat()}

    C._set(cache_key, result)
    logger.info("FII/DII for %s: FII ₹%.0f cr, DII ₹%.0f cr (source: %s)",
                trade_date, result["fii_net_buy_cr"], result["dii_net_buy_cr"], result["source"])
    return result
