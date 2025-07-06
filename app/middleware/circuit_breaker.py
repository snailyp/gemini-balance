from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from app.config.config import settings
from app.database.redis_conn import get_redis_pool
from app.exception.exceptions import ServiceUnavailableError

class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        redis = await get_redis_pool()
        
        # Only apply to Gemini API routes
        if "/gemini/" in request.url.path:
            breaker_key = "global_breaker_tripped"
            failure_key = "global_gemini_failures_minute"

            # Check if the circuit is open
            if await redis.exists(breaker_key):
                raise ServiceUnavailableError("Global circuit breaker is open due to high upstream failure rate.")

            # Check failure rate
            current_failures = await redis.get(failure_key)
            if current_failures and int(current_failures) > settings.GLOBAL_FAILURE_THRESHOLD:
                # Trip the circuit breaker
                await redis.set(breaker_key, 1, ex=settings.GLOBAL_COOLDOWN_SECONDS)
                raise ServiceUnavailableError("Global circuit breaker has been tripped.")

        response = await call_next(request)
        return response
