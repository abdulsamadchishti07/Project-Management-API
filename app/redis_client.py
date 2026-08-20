from fastapi import HTTPException, Request, status
from typing import Optional, Any

import json
import logging

import redis
from .config import settings



logger = logging.getLogger(__name__)

# Initialize Redis client with graceful fallback
try:
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
except Exception as e:
    logger.warning(f"Could not connect to Redis: {e}")
    redis_client = None


def get_cached_json(key: str) -> Optional[Any]:
    """Retrieves and deserializes JSON from Redis cache."""
    if not redis_client:
        return None
    try:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"Redis cache read error on '{key}': {e}")
    return None


def set_cached_json(key: str, data: Any, expire_seconds: int = 180):
    """Serializes and stores data in Redis cache with an expiration time."""
    if not redis_client:
        return
    try:
        serialized = json.dumps(data, default=str)
        redis_client.setex(key, expire_seconds, serialized)
    except Exception as e:
        logger.warning(f"Redis cache write error on '{key}': {e}")


def delete_cache_pattern(pattern: str):
    """
    Non-blocking cache invalidation using SCAN instead of KEYS.
    Safe for production on large Redis keyspaces.
    """
    if not redis_client:
        return
    try:
        cursor = "0"
        while cursor != 0:
            cursor, keys = redis_client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                redis_client.delete(*keys)
    except Exception as e:
        logger.warning(f"Redis cache invalidation error for '{pattern}': {e}")


class RateLimiter:
    """
    FastAPI Dependency for Rate Limiting.
    Extracts client IP with X-Forwarded-For support for reverse proxies and Docker containers.
    """

    def __init__(self, times: int, seconds: int, key_prefix: str = "rate_limit"):
        self.times = times
        self.seconds = seconds
        self.key_prefix = key_prefix

    def __call__(self, request: Request):
        if not redis_client:
            return  # Gracefully pass if Redis is offline

        # Support X-Forwarded-For behind reverse proxies / Docker load balancers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "unknown"

        endpoint = request.url.path
        key = f"{self.key_prefix}:{endpoint}:{client_ip}"

        try:
            current_requests = redis_client.incr(key)
            if current_requests == 1:
                redis_client.expire(key, self.seconds)

            if current_requests > self.times:
                ttl = redis_client.ttl(key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Limit is {self.times} per {self.seconds}s. Please retry in {ttl}s."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Rate limiting check encountered an issue: {e}")
