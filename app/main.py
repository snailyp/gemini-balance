from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logger import get_main_logger

from app.api import openai_routes
import uvicorn

from app.middleware.request_logging_middleware import RequestLoggingMiddleware

# 配置日志
logger = get_main_logger()

app = FastAPI()

# 添加请求日志中间件
# app.add_middleware(RequestLoggingMiddleware)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议配置具体的域名
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 明确指定允许的HTTP方法
    allow_headers=["*"],  # 生产环境建议配置具体的请求头
    expose_headers=["*"],  # 允许前端访问的响应头
    max_age=600,  # 预检请求缓存时间(秒)
)

# 包含所有路由
app.include_router(openai_routes.router)

@app.get("/health")
@app.get("/")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
