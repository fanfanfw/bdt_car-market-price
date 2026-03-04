"""
Simple rate limiting helpers.

This is intentionally lightweight (no third-party dependency) and uses Django's cache.
For multi-instance deployments, configure a shared cache backend (e.g., Redis) so limits
are enforced consistently across workers/hosts.
"""

from __future__ import annotations

import hashlib
import time
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

from .utils import get_client_ip


def _get_api_key(request) -> str | None:
    # Mirror existing integration auth header name.
    provided_api_key = request.headers.get("X-API-Key") or request.META.get("HTTP_X_API_KEY")
    if not provided_api_key:
        return None
    return str(provided_api_key)


def _is_valid_api_key(request) -> bool:
    configured_api_keys = getattr(settings, "API_KEYS", None) or []
    if not configured_api_keys:
        return False
    provided = _get_api_key(request)
    if not provided:
        return False
    return provided in configured_api_keys


def _key_id(api_key: str) -> str:
    # Do not store raw API keys in cache keys.
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]


def rate_limit_by_api_key_or_ip(
    *,
    scope: str,
    anon_limit: int,
    auth_limit: int,
    window_seconds: int,
    reject_invalid_api_key_header: bool = False,
    invalid_key_status: int = 401,
    invalid_key_limit: int | None = None,
):
    """
    Rate limit per fixed window.

    - Anonymous: bucketed by client IP
    - Authenticated: bucketed by API key (if valid)

    Returns HTTP 429 with Retry-After when exceeded.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            now = int(time.time())
            bucket = now // max(int(window_seconds), 1)

            configured_api_keys = getattr(settings, "API_KEYS", None) or []
            provided_api_key = _get_api_key(request)

            # If a key header is present but invalid, optionally reject it.
            # This prevents key-guessing while still allowing the UI to call anonymously.
            if (
                reject_invalid_api_key_header
                and provided_api_key is not None
                and configured_api_keys
                and provided_api_key not in configured_api_keys
            ):
                if invalid_key_limit is not None:
                    ip = get_client_ip(request) or "unknown"
                    invalid_subject = f"invalid:ip:{ip}"
                    invalid_cache_key = f"rl:{scope}:{invalid_subject}:{bucket}"
                    ttl = max(int(window_seconds), 1) + 1
                    try:
                        invalid_count = cache.incr(invalid_cache_key)
                    except ValueError:
                        cache.add(invalid_cache_key, 1, timeout=ttl)
                        invalid_count = 1
                    if invalid_count > int(invalid_key_limit):
                        retry_after = max(int(window_seconds) - (now % int(window_seconds)), 1)
                        resp = JsonResponse(
                            {
                                "error": "Too many requests",
                                "scope": scope,
                                "retry_after_seconds": retry_after,
                            },
                            status=429,
                        )
                        resp["Retry-After"] = str(retry_after)
                        return resp

                return JsonResponse({"error": "Invalid API key"}, status=int(invalid_key_status))

            if provided_api_key is not None and configured_api_keys and provided_api_key in configured_api_keys:
                api_key = _get_api_key(request) or ""
                subject = f"key:{_key_id(api_key)}"
                limit = int(auth_limit)
            else:
                subject = f"ip:{get_client_ip(request) or 'unknown'}"
                limit = int(anon_limit)

            cache_key = f"rl:{scope}:{subject}:{bucket}"
            ttl = max(int(window_seconds), 1) + 1

            try:
                count = cache.incr(cache_key)
            except ValueError:
                # Key did not exist in cache.
                cache.add(cache_key, 1, timeout=ttl)
                count = 1

            if count > limit:
                retry_after = max(int(window_seconds) - (now % int(window_seconds)), 1)
                resp = JsonResponse(
                    {
                        "error": "Too many requests",
                        "scope": scope,
                        "retry_after_seconds": retry_after,
                    },
                    status=429,
                )
                resp["Retry-After"] = str(retry_after)
                return resp

            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
