import time
from collections import deque

from fastapi import HTTPException, Request, status


class TokenBucketLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.buckets: dict[str, deque[float]] = {}

    def check(self, key: str) -> None:
        now = time.time()
        window_start = now - self.window_seconds
        bucket = self.buckets.setdefault(key, deque())
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )
        bucket.append(now)


def rate_limit_middleware(limiter: TokenBucketLimiter):
    async def middleware(request: Request, call_next):
        token = request.headers.get("authorization", "")
        key_parts = [request.client.host if request.client else "unknown"]
        if token:
            key_parts.append(token[-8:])  # cheap token-based differentiation
        key = ":".join(key_parts)
        limiter.check(key)
        return await call_next(request)

    return middleware
