from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse

from app.config.config import settings
from app.core.security import SecurityService
from app.domain.claude_models import ClaudeChatRequest
from app.handler.error_handler import handle_route_errors
from app.log.logger import get_claude_compatible_logger
from app.service.chat.gemini_chat_service import GeminiChatService
from app.service.key.key_manager import KeyManager, get_key_manager_instance
from app.service.claude_compatiable.claude_compatiable_service import (
    ClaudeCompatibleService,
)

router = APIRouter()
logger = get_claude_compatible_logger()

security_service = SecurityService()


async def get_key_manager():
    return await get_key_manager_instance()


# Centralized service instances
async def get_gemini_chat_service(key_manager: KeyManager = Depends(get_key_manager)):
    return GeminiChatService(base_url=settings.BASE_URL, key_manager=key_manager)


async def get_claude_service(
    gemini_service: GeminiChatService = Depends(get_gemini_chat_service),
):
    """获取Claude-to-Gemini适配器服务实例"""
    return ClaudeCompatibleService(gemini_service)


@router.post("/v1/messages")
async def claude_chat_completion(
    req: Request,
    request: ClaudeChatRequest,
    _=Depends(security_service.verify_authorization),
    key_manager: KeyManager = Depends(get_key_manager),
    claude_service: ClaudeCompatibleService = Depends(get_claude_service),
):
    """处理Claude格式的聊天补全请求，并将其转换为Gemini API调用。"""
    operation_name = "claude_chat_completion"
    try:
        async with handle_route_errors(logger, operation_name):
            # We need a Gemini key to call the Gemini API
            api_key = await key_manager.get_next_working_key()
            if not api_key:
                raise HTTPException(
                    status_code=500, detail="No valid Gemini API key available."
                )

            logger.info(
                f"Handling Claude-compatible chat completion request for model: {request.model}"
            )
            logger.debug(
                f"Incoming Claude Request from {req.client.host}: \n{request.model_dump_json(indent=2)}"
            )
            logger.info(f"Using Gemini API key: {api_key[:5]}...{api_key[-4:]}")

            response = await claude_service.create_chat_completion(request, api_key)

            if request.stream:
                return StreamingResponse(response, media_type="text/event-stream")
            return JSONResponse(content=response)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in claude_chat_completion: {e}",
            exc_info=True,
        )
        raise
