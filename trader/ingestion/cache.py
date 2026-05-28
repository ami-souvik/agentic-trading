from __future__ import annotations

from typing import Any
import pickle


class Cache:
    def __init__(self, ttl: int = 60*60*24):
        self.ttl = ttl
        self.redis = self._redis()

    def _redis(self):
        try:
            import redis as redis_lib
            from trader.config.settings import get_settings
            client = redis_lib.from_url(get_settings().redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception:
            return None

    def _get(self, key: str) -> Any | None:
        if self.redis is None:
            return None
        try:
            raw = self.redis.get(key)
            return pickle.loads(raw) if raw else None
        except Exception:
            return None


    def _set(self, key: str, value: Any) -> None:
        if self.redis is None:
            return
        try:
            self.redis.setex(key, self.ttl, pickle.dumps(value))
        except Exception:
            pass