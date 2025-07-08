"""
配置路由模块
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.core.security import verify_auth_token
from app.log.logger import Logger, get_config_routes_logger
from app.service.config.config_service import ConfigService
from app.service.key.key_manager import get_key_manager_instance

router = APIRouter(prefix="/api/config", tags=["config"])

logger = get_config_routes_logger()


@router.get("", response_model=Dict[str, Any])
async def get_config(request: Request):
    auth_token = request.cookies.get("auth_token")
    if not auth_token or not verify_auth_token(auth_token):
        logger.warning("Unauthorized access attempt to config page")
        return RedirectResponse(url="/", status_code=302)
    return await ConfigService.get_config()


@router.put("", response_model=Dict[str, Any])
async def update_config(config_data: Dict[str, Any], request: Request):
    auth_token = request.cookies.get("auth_token")
    if not auth_token or not verify_auth_token(auth_token):
        logger.warning("Unauthorized access attempt to config page")
        return RedirectResponse(url="/", status_code=302)
    try:
        result = await ConfigService.update_config(config_data)
        # 配置更新成功后，立即更新所有 logger 的级别
        Logger.update_log_levels(config_data["LOG_LEVEL"])
        logger.info("Log levels updated after configuration change.")
        return result
    except Exception as e:
        logger.error(f"Error updating config or log levels: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset", response_model=Dict[str, Any])
async def reset_config(request: Request):
    auth_token = request.cookies.get("auth_token")
    if not auth_token or not verify_auth_token(auth_token):
        logger.warning("Unauthorized access attempt to config page")
        return RedirectResponse(url="/", status_code=302)
    try:
        return await ConfigService.reset_config()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class DeleteKeysRequest(BaseModel):
    keys: List[str] = Field(..., description="List of API keys to delete")


@router.delete("/keys/{key_to_delete}", response_model=Dict[str, Any])
async def delete_single_key(key_to_delete: str, request: Request):
    auth_token = request.cookies.get("auth_token")
    if not auth_token or not verify_auth_token(auth_token):
        logger.warning(f"Unauthorized attempt to delete key: {key_to_delete}")
        return RedirectResponse(url="/", status_code=302)
    try:
        logger.info(f"Attempting to delete key: {key_to_delete}")
        result = await ConfigService.delete_key(key_to_delete)
        if not result.get("success"):
            raise HTTPException(
                status_code=(
                    404 if "not found" in result.get("message", "").lower() else 400
                ),
                detail=result.get("message"),
            )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting key '{key_to_delete}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting key: {str(e)}")


@router.post("/keys/delete-selected", response_model=Dict[str, Any])
async def delete_selected_keys_route(
    delete_request: DeleteKeysRequest, request: Request
):
    auth_token = request.cookies.get("auth_token")
    if not auth_token or not verify_auth_token(auth_token):
        logger.warning("Unauthorized attempt to bulk delete keys")
        return RedirectResponse(url="/", status_code=302)

    if not delete_request.keys:
        logger.warning("Attempt to bulk delete keys with an empty list.")
        raise HTTPException(status_code=400, detail="No keys provided for deletion.")

    try:
        logger.info(f"Attempting to bulk delete {len(delete_request.keys)} keys.")
        result = await ConfigService.delete_selected_keys(delete_request.keys)
        if not result.get("success") and result.get("deleted_count", 0) == 0:
            raise HTTPException(
                status_code=400, detail=result.get("message", "Failed to delete keys.")
            )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error bulk deleting keys: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error bulk deleting keys: {str(e)}"
        )


@router.get("/ui/models")
async def get_ui_models(request: Request):
    auth_token_cookie = request.cookies.get("auth_token")
    if not auth_token_cookie or not verify_auth_token(auth_token_cookie):
        logger.warning("Unauthorized access attempt to /api/config/ui/models")
        raise HTTPException(status_code=403, detail="Not authenticated")

    try:
        models = await ConfigService.fetch_ui_models()
        return models
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in /ui/models endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while fetching UI models: {str(e)}",
        )


@router.get("/keys/status", response_model=Dict[str, Any])
async def get_keys_status(request: Request):
    """
    获取所有 key 的状态，包括有效、无效和冷却中。
    """
    auth_token = request.cookies.get("auth_token")
    if not auth_token or not verify_auth_token(auth_token):
        logger.warning("Unauthorized access attempt to keys status page")
        raise HTTPException(status_code=403, detail="Not authenticated")

    try:
        # 获取 KeyManager 单例
        key_manager = await get_key_manager_instance()
        
        # 获取 Gemini keys 的状态
        gemini_keys_status = await key_manager.get_keys_by_status()
        
        # 为了保持接口一致性，也获取 Vertex keys 的状态
        vertex_keys_status = await key_manager.get_vertex_keys_by_status()

        return {
            "gemini_keys": gemini_keys_status,
            "vertex_keys": vertex_keys_status,
        }
    except Exception as e:
        logger.error(f"Error fetching key statuses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while fetching key statuses: {str(e)}")
