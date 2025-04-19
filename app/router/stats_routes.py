from fastapi import APIRouter, Depends, HTTPException, Request
from starlette import status
from app.core.security import verify_auth_token
from app.service.stats_service import StatsService
from app.log.logger import get_stats_logger # 使用路由日志记录器

logger = get_stats_logger()


# 认证检查的辅助函数
async def verify_token(request: Request):
    auth_token = request.cookies.get("auth_token")
    if not auth_token or not verify_auth_token(auth_token):
        logger.warning("Unauthorized access attempt to scheduler API")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

router = APIRouter(
    prefix="/api",
    tags=["stats"],
    dependencies=[Depends(verify_token)] # Assuming API routes need authentication
)

stats_service = StatsService()

@router.get("/key-usage-details/{key}",
            summary="获取指定密钥最近24小时的模型调用次数",
            description="根据提供的 API 密钥，返回过去24小时内每个模型被调用的次数统计。")
async def get_key_usage_details(key: str):
    """
    Retrieves the model usage count for a specific API key within the last 24 hours.

    Args:
        key: The API key to get usage details for.

    Returns:
        A dictionary with model names as keys and their call counts as values.
        Example: {"gemini-pro": 10, "gemini-1.5-pro-latest": 5}

    Raises:
        HTTPException: If an error occurs during data retrieval.
    """
    try:
        usage_details = await stats_service.get_key_usage_details_last_24h(key)
        if usage_details is None:
            # Handle case where key might be valid but has no recent usage,
            # or if the service layer explicitly returns None for other reasons.
            # Returning an empty dict is usually fine for the frontend.
            return {}
        return usage_details
    except Exception as e:
        # Log the exception details here if needed
        print(f"Error fetching key usage details for key {key[:4]}...: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取密钥使用详情时出错: {e}"
        )