
import datetime
import json
import re
import time
from typing import Any, AsyncGenerator, Dict, Union

from app.config.config import settings
from app.database.services import error_log_service, request_log_service
from app.domain.openai_models import ChatRequest, ImageGenerationRequest
from app.service.client.api_client import OpenaiApiClient
from app.service.key.key_manager import KeyManager
from app.log.logger import get_openai_compatible_logger

logger = get_openai_compatible_logger()

class OpenAICompatiableService:

    def __init__(self, base_url: str, key_manager: KeyManager = None):
        self.key_manager = key_manager
        self.base_url = base_url
        self.api_client = OpenaiApiClient(base_url, settings.TIME_OUT)
        
    async def get_models(self, api_key: str) -> Dict[str, Any]:
        return await self.api_client.get_models(api_key)

    async def create_chat_completion(
        self,
        request: ChatRequest,
        api_key: str,
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """创建聊天完成"""
        request_dict = request.model_dump()
        # 移除值为null的
        request_dict = {k: v for k, v in request_dict.items() if v is not None}
        del request_dict["top_k"] # 删除top_k参数，目前不支持该参数
        if request.stream:
            return self._handle_stream_completion(request.model, request_dict, api_key)
        return await self._handle_normal_completion(request.model, request_dict, api_key)

    async def generate_images(
        self,
        request: ImageGenerationRequest,
    ) -> Dict[str, Any]:
        """生成图片"""
        request_dict = request.model_dump()
        # 移除值为null的
        request_dict = {k: v for k, v in request_dict.items() if v is not None}
        api_key = settings.PAID_KEY
        return await self.api_client.generate_images(request_dict, api_key)

    async def create_embeddings(
        self,
        input_text: str,
        model: str,
        api_key: str,
    ) -> Dict[str, Any]:
        """创建嵌入"""
        return await self.api_client.create_embeddings(input_text, model, api_key)

    async def _handle_normal_completion(
        self, model: str, request: dict, api_key: str
    ) -> Dict[str, Any]:
        """处理普通聊天完成"""
        start_time = time.perf_counter()
        request_datetime = datetime.datetime.now()
        is_success = False
        status_code = None
        response = None
        try:
            response = await self.api_client.generate_content(request, api_key)
            is_success = True
            status_code = 200
            return response
        except Exception as e:
            is_success = False
            error_log_msg = str(e)
            logger.error(f"Normal API call failed with error: {error_log_msg}")
            match = re.search(r"status code (\d+)", error_log_msg)
            if match:
                status_code = int(match.group(1))
            else:
                status_code = 500

            await error_log_service.add_log(
                gemini_key=api_key,
                model_name=model,
                error_type="openai-compatiable-non-stream",
                error_log=error_log_msg,
                error_code=status_code,
                request_msg=request,
            )
            raise e
        finally:
            end_time = time.perf_counter()
            latency_ms = int((end_time - start_time) * 1000)
            await request_log_service.add_log(
                model_name=model,
                api_key=api_key,
                is_success=is_success,
                status_code=status_code,
                latency_ms=latency_ms,
                request_time=request_datetime,
            )

    async def _handle_stream_completion(
        self, model: str, payload: dict, api_key: str
    ) -> AsyncGenerator[str, None]:
        """处理流式聊天完成，添加重试逻辑"""
        retries = 0
        max_retries = settings.MAX_RETRIES
        is_success = False
        status_code = None
        final_api_key = api_key

        while retries < max_retries:
            start_time = time.perf_counter()
            request_datetime = datetime.datetime.now()
            current_attempt_key = api_key
            final_api_key = current_attempt_key
            try:
                async for line in self.api_client.stream_generate_content(
                    payload, current_attempt_key
                ):
                    if line.startswith("data:"):
                        # print(line)
                        yield line + "\n\n"
                logger.info("Streaming completed successfully")
                is_success = True
                status_code = 200
                break
            except Exception as e:
                retries += 1
                is_success = False
                error_log_msg = str(e)
                logger.warning(
                    f"Streaming API call failed with error: {error_log_msg}. Attempt {retries} of {max_retries}"
                )
                match = re.search(r"status code (\d+)", error_log_msg)
                if match:
                    status_code = int(match.group(1))
                else:
                    status_code = 500

                await error_log_service.add_log(
                    gemini_key=current_attempt_key,
                    model_name=model,
                    error_type="openai-compatiable-stream",
                    error_log=error_log_msg,
                    error_code=status_code,
                    request_msg=payload,
                )

                if self.key_manager:
                    api_key = await self.key_manager.handle_api_failure(
                        current_attempt_key, retries
                    )
                    if api_key:
                        logger.info(f"Switched to new API key: {api_key}")
                    else:
                        logger.error(
                            f"No valid API key available after {retries} retries."
                        )
                        break 
                else:
                    logger.error("KeyManager not available for retry logic.")
                    break 

                if retries >= max_retries:
                    logger.error(f"Max retries ({max_retries}) reached for streaming.")
                    break
            finally:
                end_time = time.perf_counter()
                latency_ms = int((end_time - start_time) * 1000)
                await request_log_service.add_log(
                    model_name=model,
                    api_key=final_api_key,
                    is_success=is_success,
                    status_code=status_code,
                    latency_ms=latency_ms,
                    request_time=request_datetime,
                )
                if not is_success and retries >= max_retries:
                    yield f"data: {json.dumps({'error': 'Streaming failed after retries'})}\n\n"
                    yield "data: [DONE]\n\n"
                    
    
