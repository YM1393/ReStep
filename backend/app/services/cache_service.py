"""
Redis caching service with graceful fallback.

If REDIS_URL is not set or Redis is unavailable, all cache operations
return None / succeed silently so the application works without Redis.
"""

import os
import json
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

_redis_client = None
_redis_available = False


def _init_redis():
    """Lazily initialise the Redis connection."""
    global _redis_client, _redis_available
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return
    try:
        import redis
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        _redis_client.ping()
        _redis_available = True
        logger.info("Redis cache connected: %s", redis_url)
    except Exception as e:
        _redis_client = None
        _redis_available = False
        logger.warning("Redis unavailable, caching disabled: %s", e)


# Initialise on module load
_init_redis()


class CacheService:
    """Simple Redis cache wrapper with JSON serialisation."""

    # Key prefixes for different data types
    PREFIX_PATIENTS = "cache:patients"
    PREFIX_DASHBOARD = "cache:dashboard"
    PREFIX_NORMATIVE = "cache:normative"
    PREFIX_TESTS = "cache:tests"

    @staticmethod
    def get(key: str) -> Optional[Any]:
        """Retrieve a cached value. Returns None on miss or if Redis is down."""
        if not _redis_available:
            return None
        try:
            raw = _redis_client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.debug("Cache get error for %s: %s", key, e)
            return None

    @staticmethod
    def set(key: str, value: Any, ttl: int = 60) -> bool:
        """Store a value in cache with TTL (seconds). Returns True on success."""
        if not _redis_available:
            return False
        try:
            raw = json.dumps(value, ensure_ascii=False, default=str)
            _redis_client.setex(key, ttl, raw)
            return True
        except Exception as e:
            logger.debug("Cache set error for %s: %s", key, e)
            return False

    @staticmethod
    def delete(key: str) -> bool:
        """Delete a specific key. Returns True if deleted."""
        if not _redis_available:
            return False
        try:
            return _redis_client.delete(key) > 0
        except Exception as e:
            logger.debug("Cache delete error for %s: %s", key, e)
            return False

    @staticmethod
    def clear_pattern(pattern: str) -> int:
        """Delete all keys matching a glob pattern. Returns count deleted."""
        if not _redis_available:
            return 0
        try:
            count = 0
            cursor = 0
            while True:
                cursor, keys = _redis_client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    count += _redis_client.delete(*keys)
                if cursor == 0:
                    break
            return count
        except Exception as e:
            logger.debug("Cache clear_pattern error for %s: %s", pattern, e)
            return 0

    # ---------------------------------------------------------------
    # Convenience helpers for specific data types
    # ---------------------------------------------------------------

    @staticmethod
    def get_patient_list(limit: int) -> Optional[list]:
        return CacheService.get(f"{CacheService.PREFIX_PATIENTS}:list:{limit}")

    @staticmethod
    def set_patient_list(limit: int, data: list):
        CacheService.set(f"{CacheService.PREFIX_PATIENTS}:list:{limit}", data, ttl=60)

    @staticmethod
    def get_dashboard_stats() -> Optional[dict]:
        return CacheService.get(f"{CacheService.PREFIX_DASHBOARD}:stats")

    @staticmethod
    def set_dashboard_stats(data: dict):
        CacheService.set(f"{CacheService.PREFIX_DASHBOARD}:stats", data, ttl=300)

    @staticmethod
    def get_normative(age: int, gender: str) -> Optional[dict]:
        return CacheService.get(f"{CacheService.PREFIX_NORMATIVE}:{age}:{gender}")

    @staticmethod
    def set_normative(age: int, gender: str, data: dict):
        CacheService.set(f"{CacheService.PREFIX_NORMATIVE}:{age}:{gender}", data, ttl=3600)

    @staticmethod
    def get_patient_tests(patient_id: str, test_type: Optional[str] = None) -> Optional[list]:
        key = f"{CacheService.PREFIX_TESTS}:patient:{patient_id}:{test_type or 'ALL'}"
        return CacheService.get(key)

    @staticmethod
    def set_patient_tests(patient_id: str, data: list, test_type: Optional[str] = None):
        key = f"{CacheService.PREFIX_TESTS}:patient:{patient_id}:{test_type or 'ALL'}"
        CacheService.set(key, data, ttl=120)

    # ---------------------------------------------------------------
    # Invalidation helpers (called on writes)
    # ---------------------------------------------------------------

    @staticmethod
    def invalidate_patients():
        """Clear all patient list caches."""
        CacheService.clear_pattern(f"{CacheService.PREFIX_PATIENTS}:*")

    @staticmethod
    def invalidate_dashboard():
        """Clear dashboard stats cache."""
        CacheService.clear_pattern(f"{CacheService.PREFIX_DASHBOARD}:*")

    @staticmethod
    def invalidate_tests(patient_id: Optional[str] = None):
        """Clear test result caches, optionally scoped to a patient."""
        if patient_id:
            CacheService.clear_pattern(f"{CacheService.PREFIX_TESTS}:patient:{patient_id}:*")
        else:
            CacheService.clear_pattern(f"{CacheService.PREFIX_TESTS}:*")

    @staticmethod
    def invalidate_all():
        """Nuclear option - clear everything."""
        CacheService.clear_pattern("cache:*")


# Module-level singleton
cache = CacheService()
