from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.config.config import settings
from app.core.security import SecurityService
from app.domain.openai_models import (
    ChatRequest,
    EmbeddingRequest,
    ImageGenerationRequest,
)
from app.handler.retry_handler import RetryHandler
from app.handler.error_handler import handle_route_errors
from app.log.logger import get_openai_compatible_logger
from app.service.key.key_manager import KeyManager, get_key_manager_instance
from app.service.openai_compatiable.openai_compatiable_service import OpenAICompatiableService
from app.utils.helpers import redact_key_for_logging


router = APIRouter()
logger = get_openai_compatible_logger()

security_service = SecurityService()

async def get_key_manager():
    return await get_key_manager_instance()


async def get_next_working_key_wrapper(
    key_manager: KeyManager = Depends(get_key_manager),
):
    return await key_manager.get_next_working_key()


async def get_openai_service(key_manager: KeyManager = Depends(get_key_manager)):
    """获取OpenAI聊天服务实例"""
    return OpenAICompatiableService(settings.BASE_URL, key_manager)


@router.get("/openai/v1/models")
async def list_models(
    _=Depends(security_service.verify_authorization),
    key_manager: KeyManager = Depends(get_key_manager),
    openai_service: OpenAICompatiableService = Depends(get_openai_service),
):
    """获取可用模型列表。"""
    operation_name = "list_models"
    async with handle_route_errors(logger, operation_name):
        logger.info("Handling models list request")
        api_key = await key_manager.get_random_valid_key()
        logger.info(f"Using API key: {redact_key_for_logging(api_key)}")
        response = await openai_service.get_models(api_key)
        # 成功时锁定当前密钥
        await key_manager.lock_current_key(api_key)
        return response


@router.post("/openai/v1/chat/completions")
@RetryHandler(key_arg="api_key")
async def chat_completion(
    request: ChatRequest,
    _=Depends(security_service.verify_authorization),
    api_key: str = Depends(get_next_working_key_wrapper),
    key_manager: KeyManager = Depends(get_key_manager),
    openai_service: OpenAICompatiableService = Depends(get_openai_service),
):
    """处理聊天补全请求，支持流式响应和特定模型切换。"""
    operation_name = "chat_completion"
    is_image_chat = request.model == f"{settings.CREATE_IMAGE_MODEL}-chat"
    current_api_key = api_key
    if is_image_chat:
        current_api_key = await key_manager.get_paid_key()

    async with handle_route_errors(logger, operation_name):
        logger.info(f"Handling chat completion request for model: {request.model}")
        logger.debug(f"Request: \n{request.model_dump_json(indent=2)}")
        logger.info(f"Using API key: {redact_key_for_logging(current_api_key)}")

        if is_image_chat:
            response = await openai_service.create_image_chat_completion(request, current_api_key)
            return response
        else:
            response = await openai_service.create_chat_completion(request, current_api_key)
            if request.stream:
                return StreamingResponse(response, media_type="text/event-stream")
            return response


@router.post("/openai/v1/images/generations")
async def generate_image(
    request: ImageGenerationRequest,
    _=Depends(security_service.verify_authorization),
    openai_service: OpenAICompatiableService = Depends(get_openai_service),
):
    """处理图像生成请求。"""
    operation_name = "generate_image"
    async with handle_route_errors(logger, operation_name):
        logger.info(f"Handling image generation request for prompt: {request.prompt}")
        request.model = settings.CREATE_IMAGE_MODEL
        return await openai_service.generate_images(request)


@router.post("/openai/v1/embeddings")
async def embedding(
    request: EmbeddingRequest,
    _=Depends(security_service.verify_authorization),
    key_manager: KeyManager = Depends(get_key_manager),
    openai_service: OpenAICompatiableService = Depends(get_openai_service),
):
    """处理文本嵌入请求。"""
    operation_name = "embedding"
    async with handle_route_errors(logger, operation_name):
        logger.info(f"Handling embedding request for model: {request.model}")
        api_key = await key_manager.get_next_working_key()
        logger.info(f"Using API key: {redact_key_for_logging(api_key)}")
        response = await openai_service.create_embeddings(
            input_text=request.input, model=request.model, api_key=api_key
        )
        # 成功时锁定当前密钥
        await key_manager.lock_current_key(api_key)
        return response
