import time
from app.models import Product

CACHE_TTL = 6 * 3600  # 6 hours

_cache: dict[str, dict] = {}


def get_cached(source: str) -> list[Product] | None:
    entry = _cache.get(source)
    if entry and (time.time() - entry["timestamp"]) < CACHE_TTL:
        return entry["data"]
    return None


def set_cached(source: str, data: list[Product]) -> None:
    _cache[source] = {"data": data, "timestamp": time.time()}
