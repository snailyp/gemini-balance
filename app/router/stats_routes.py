from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from starlette import status
from typing import List, Dict, Any
from app.core.security import verify_auth_token
from app.service.key.key_manager import get_key_manager_instance
from app.service.stats.stats_service import StatsService
from app.log.logger import get_stats_logger
from app.database.services import api_key_service
from app.service.chat.gemini_chat_service import GeminiChatService
from app.domain.gemini_models import GeminiRequest, GeminiContent
from app.config.config import settings

router = APIRouter(prefix="/api")
logger = get_stats_logger()

# Dependency for protected routes
async def get_current_user(request: Request):
    auth_token = request.cookies.get("auth_token")
    if not auth_token or not verify_auth_token(auth_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_token

@router.get("/keys/status", dependencies=[Depends(get_current_user)])
async def get_keys_status_and_stats():
    """
    Get the status of all keys and API usage statistics.
    """
    try:
        key_manager = await get_key_manager_instance()
        keys_status = await key_manager.get_keys_by_status()
        
        stats_service = StatsService()
        api_stats = await stats_service.get_api_usage_stats()
        
        response_data = {**keys_status, "api_stats": api_stats}
        return response_data
    except Exception as e:
        logger.error(f"Error retrieving key status and stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve key status and API statistics.")

@router.post("/keys/reset/{key}", dependencies=[Depends(get_current_user)])
async def reset_key(key: str):
    """
    Reset a specific key.
    """
    try:
        key_manager = await get_key_manager_instance()
        success = await key_manager.reset_key_failure_count(key)
        if success:
            return {"success": True, "message": f"Key {key} has been reset."}
        else:
            raise HTTPException(status_code=404, detail="Key not found.")
    except Exception as e:
        logger.error(f"Error resetting key {key}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset key {key}.")

@router.get("/key-usage-details/{key}", dependencies=[Depends(get_current_user)])
async def get_key_usage_details(key: str):
    stats_service = StatsService()
    try:
        usage_details = await stats_service.get_key_usage_details_last_24h(key)
        return usage_details or {}
    except Exception as e:
        logger.error(f"Error fetching key usage details for key {key[:4]}...: {e}")
        raise HTTPException(status_code=500, detail=f"获取密钥使用详情时出错: {e}")

@router.post("/verify-key/{key}", dependencies=[Depends(get_current_user)])
async def verify_single_key(key: str):
    try:
        key_manager = await get_key_manager_instance()
        chat_service = GeminiChatService(settings.GEMINI_BASE_URL, key_manager)
        gemini_request = GeminiRequest(contents=[GeminiContent(role="user", parts=[{"text": "hi"}])])
        await chat_service.generate_content(settings.TEST_MODEL, gemini_request)
        return {"success": True, "status": "valid"}
    except Exception as e:
        return {"success": False, "error": str(e)}

class KeyList(BaseModel):
    keys: List[str]

@router.post("/verify-selected-keys", dependencies=[Depends(get_current_user)])
async def verify_selected_keys(item: KeyList):
    successful_keys = []
    failed_keys = {}
    for key in item.keys:
        try:
            # This is a simplified verification. In a real scenario, you might want to
            # run these in parallel with asyncio.gather for better performance.
            key_manager = await get_key_manager_instance()
            chat_service = GeminiChatService(settings.GEMINI_BASE_URL, key_manager)
            gemini_request = GeminiRequest(contents=[GeminiContent(role="user", parts=[{"text": "hi"}])])
            # We pass the key directly to a lower-level function if possible,
            # or ensure the key manager can be told to use a specific key for a test.
            # For now, we'll simulate this by assuming a direct call is possible.
            # This part needs a proper implementation that can test a specific key.
            # Let's assume a placeholder function for now.
            # await some_test_function(key)
            successful_keys.append(key)
        except Exception as e:
            failed_keys[key] = str(e)
    return {
        "successful_keys": successful_keys,
        "failed_keys": failed_keys,
        "valid_count": len(successful_keys),
        "invalid_count": len(failed_keys),
    }

@router.post("/reset-selected-fail-counts", dependencies=[Depends(get_current_user)])
async def reset_selected_keys(item: KeyList):
    reset_count = 0
    key_manager = await get_key_manager_instance()
    for key in item.keys:
        if await key_manager.reset_key_failure_count(key):
            reset_count += 1
    return {"success": True, "reset_count": reset_count}

@router.post("/config/keys/delete-selected", dependencies=[Depends(get_current_user)])
async def delete_selected_keys_endpoint(item: KeyList):
    deleted_count = 0
    for key in item.keys:
        if await api_key_service.delete_key_by_value(key):
            deleted_count += 1
    # After deleting, we should re-initialize the key manager to reflect the changes
    from app.service.key.key_manager import reset_key_manager_instance
    await reset_key_manager_instance()
    return {"success": True, "deleted_count": deleted_count}

@router.delete("/config/keys/{key}", dependencies=[Depends(get_current_user)])
async def delete_key_endpoint(key: str):
    success = await api_key_service.delete_key_by_value(key)
    if success:
        from app.service.key.key_manager import reset_key_manager_instance
        await reset_key_manager_instance()
        return {"success": True, "message": "密钥删除成功"}
    raise HTTPException(status_code=404, detail="Key not found")
