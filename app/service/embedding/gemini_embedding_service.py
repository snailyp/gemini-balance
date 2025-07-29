# app/service/embedding/gemini_embedding_service.py

import datetime
import re
import time
from typing import Any, Dict

from app.config.config import settings
from app.database.services import add_error_log, add_request_log
from app.domain.gemini_models import GeminiBatchEmbedRequest, GeminiEmbedRequest
from app.log.logger import get_gemini_embedding_logger
from app.service.client.api_client import GeminiApiClient
from app.service.key.key_manager import KeyManager

logger = get_gemini_embedding_logger()


def _build_embed_payload(request: GeminiEmbedRequest) -> Dict[str, Any]:
    """构建嵌入请求payload"""
    payload = {"content": request.content.model_dump()}

    if request.taskType:
        payload["taskType"] = request.taskType
    if request.title:
        payload["title"] = request.title
    if request.outputDimensionality:
        payload["outputDimensionality"] = request.outputDimensionality

    return payload


def _build_batch_embed_payload(
    request: GeminiBatchEmbedRequest, model: str
) -> Dict[str, Any]:
    """构建批量嵌入请求payload"""
    requests = []
    for embed_request in request.requests:
        embed_payload = _build_embed_payload(embed_request)
        embed_payload["model"] = (
            f"models/{model}"  # Gemini API要求每个请求包含model字段
        )
        requests.append(embed_payload)

    return {"requests": requests}


class GeminiEmbeddingService:
    """Gemini嵌入服务"""

    def __init__(self, base_url: str, key_manager: KeyManager):
        self.api_client = GeminiApiClient(base_url, settings.TIME_OUT)
        self.key_manager = key_manager

    async def embed_content(
        self, model: str, request: GeminiEmbedRequest, api_key: str
    ) -> Dict[str, Any]:
        """生成单一嵌入内容"""
        payload = _build_embed_payload(request)
        start_time = time.perf_counter()
        request_datetime = datetime.datetime.now()
        is_success = False
        status_code = None
        response = None

        try:
            response = await self.api_client.embed_content(payload, model, api_key)
            is_success = True
            status_code = 200
            return response
        except Exception as e:
            is_success = False
            error_log_msg = str(e)
            logger.error(f"Single embedding API call failed: {error_log_msg}")
            match = re.search(r"status code (\d+)", error_log_msg)
            if match:
                status_code = int(match.group(1))
            else:
                status_code = 500

            await add_error_log(
                gemini_key=api_key,
                model_name=model,
                error_type="gemini-embed-single",
                error_log=error_log_msg,
                error_code=status_code,
                request_msg=payload,
            )
            raise e
        finally:
            end_time = time.perf_counter()
            latency_ms = int((end_time - start_time) * 1000)
            await add_request_log(
                model_name=model,
                api_key=api_key,
                is_success=is_success,
                status_code=status_code,
                latency_ms=latency_ms,
                request_time=request_datetime,
            )

    async def batch_embed_contents(
        self, model: str, request: GeminiBatchEmbedRequest, api_key: str
    ) -> Dict[str, Any]:
        """生成批量嵌入内容"""
        payload = _build_batch_embed_payload(request, model)
        start_time = time.perf_counter()
        request_datetime = datetime.datetime.now()
        is_success = False
        status_code = None
        response = None

        try:
            response = await self.api_client.batch_embed_contents(
                payload, model, api_key
            )
            is_success = True
            status_code = 200
            return response
        except Exception as e:
            is_success = False
            error_log_msg = str(e)
            logger.error(f"Batch embedding API call failed: {error_log_msg}")
            match = re.search(r"status code (\d+)", error_log_msg)
            if match:
                status_code = int(match.group(1))
            else:
                status_code = 500

            await add_error_log(
                gemini_key=api_key,
                model_name=model,
                error_type="gemini-embed-batch",
                error_log=error_log_msg,
                error_code=status_code,
                request_msg=payload,
            )
            raise e
        finally:
            end_time = time.perf_counter()
            latency_ms = int((end_time - start_time) * 1000)
            await add_request_log(
                model_name=model,
                api_key=api_key,
                is_success=is_success,
                status_code=status_code,
                latency_ms=latency_ms,
                request_time=request_datetime,
            )
