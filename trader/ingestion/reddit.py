"""
Reddit sentiment ingestion: r/IndianStockMarket and r/IndianStreetBets.

Requires REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET env vars.
Returns empty list gracefully when credentials are missing or PRAW is unavailable.
This module is a read-only data source — no posting or voting.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

_CACHE_TTL = 3600  # 1 hour
_SUBREDDITS = ["IndianStockMarket", "IndianStreetBets"]
_POST_LIMIT = 50  # Posts to scan per subreddit


def _redis():
    try:
        import redis as redis_lib
        from trader.config.settings import get_settings
        client = redis_lib.from_url(get_settings().redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def _cache_get(key: str) -> list | None:
    r = _redis()
    if r is None:
        return None
    try:
        raw = r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _cache_set(key: str, value: list) -> None:
    r = _redis()
    if r is None:
        return
    try:
        r.setex(key, _CACHE_TTL, json.dumps(value, default=str))
    except Exception:
        pass


def _get_praw():
    """Return an authenticated praw.Reddit instance or None."""
    try:
        import praw
        from trader.config.settings import get_settings
        settings = get_settings()

        if not settings.reddit_client_id or not settings.reddit_client_secret:
            logger.debug("Reddit credentials not configured; skipping Reddit ingestion")
            return None

        return praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
            read_only=True,
        )
    except Exception as e:
        logger.warning("Failed to initialise PRAW: %s", e)
        return None


def fetch_reddit_mentions(ticker: str, hours_back: int = 24) -> list[dict]:
    """
    Return Reddit posts mentioning `ticker` from the last `hours_back` hours.

    Each post dict: {title, url, subreddit, score, created_at, flair}
    Returns empty list when credentials are missing or Reddit is unreachable.
    """
    cache_key = f"reddit:{ticker}:{hours_back}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    reddit = _get_praw()
    if reddit is None:
        return []

    from trader.config.tickers import TICKER_MAP
    ticker_obj = TICKER_MAP.get(ticker)
    search_terms = [ticker]
    if ticker_obj:
        search_terms.append(ticker_obj.name.split()[0])  # First word of company name

    cutoff_ts = (datetime.now(tz=timezone.utc) - timedelta(hours=hours_back)).timestamp()
    results = []

    for sub_name in _SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            for term in search_terms:
                for post in subreddit.search(term, sort="new", limit=_POST_LIMIT):
                    if post.created_utc < cutoff_ts:
                        continue
                    results.append({
                        "title":      post.title,
                        "url":        f"https://reddit.com{post.permalink}",
                        "subreddit":  sub_name,
                        "score":      post.score,
                        "created_at": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
                        "flair":      post.link_flair_text or "",
                    })
        except Exception as e:
            logger.warning("Reddit fetch failed for r/%s, term '%s': %s", sub_name, term, e)

    # Deduplicate by URL
    seen: set[str] = set()
    deduped = []
    for post in results:
        if post["url"] not in seen:
            seen.add(post["url"])
            deduped.append(post)

    deduped.sort(key=lambda p: p["created_at"], reverse=True)
    _cache_set(cache_key, deduped)
    return deduped
