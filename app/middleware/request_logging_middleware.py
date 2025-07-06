import json
import time
import datetime

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.log.logger import get_request_logger
from app.database.models import RequestLog
from app.database.connection import database

logger = get_request_logger()


# 添加中间件类
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 尝试获取API Key
        api_key = request.headers.get("authorization") or request.headers.get("x-api-key")
        if api_key and api_key.startswith("Bearer "):
            api_key = api_key.split(" ")[1]

        model_name = None
        request_body_str = None

        # 获取并记录请求体，同时尝试解析model_name
        try:
            body = await request.body()
            if body:
                request_body_str = body.decode()
                try:
                    formatted_body = json.loads(request_body_str)
                    logger.info(
                        f"Formatted request body:\n{json.dumps(formatted_body, indent=2, ensure_ascii=False)}"
                    )
                    # 尝试从请求体中提取model_name
                    model_name = formatted_body.get("model")
                except json.JSONDecodeError:
                    logger.error("Request body is not valid JSON.")
        except Exception as e:
            logger.error(f"Error reading request body: {str(e)}")

        # 重置请求的接收器，以便后续处理器可以继续读取请求体
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive

        response = await call_next(request)

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        status_code = response.status_code
        is_success = 200 <= status_code < 300

        # 记录请求日志到数据库
        try:
            await database.execute(
                RequestLog.__table__.insert().values(
                    request_time=datetime.datetime.now(),
                    model_name=model_name,
                    api_key=api_key,
                    is_success=is_success,
                    status_code=status_code,
                    latency_ms=latency_ms,
                )
            )
        except Exception as e:
            logger.error(f"Failed to log request to database: {str(e)}")

        return response
