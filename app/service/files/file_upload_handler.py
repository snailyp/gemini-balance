"""
文件上传处理器
处理 Google 的可恢复上传协议
"""
from typing import Optional
from datetime import datetime, timezone, timedelta

from httpx import AsyncClient
from fastapi import Request, Response, HTTPException

from app.config.config import settings
from app.database import services as db_services
from app.database.models import FileState
from app.log.logger import get_files_logger

logger = get_files_logger()


class FileUploadHandler:
    """处理文件分块上传"""
    
    def __init__(self):
        self.chunk_size = 8 * 1024 * 1024  # 8MB
    
    async def handle_upload_chunk(
        self,
        upload_url: str,
        request: Request,
        files_service=None  # 添加 files_service 參數
    ) -> Response:
        """
        处理上传分块
        
        Args:
            upload_url: 上传 URL
            request: FastAPI 请求对象
            files_service: 文件服務實例
            
        Returns:
            Response: 响应对象
        """
        try:
            # 获取请求头
            headers = {}
            
            # 复制必要的上传头
            upload_headers = [
                "x-goog-upload-command",
                "x-goog-upload-offset",
                "content-type",
                "content-length"
            ]
            
            for header in upload_headers:
                if header in request.headers:
                    # 转换为正确的格式
                    key = "-".join(word.capitalize() for word in header.split("-"))
                    headers[key] = request.headers[header]
            
            # 读取请求体
            body = await request.body()
            
            # 检查是否是最后一块
            is_final = "finalize" in headers.get("X-Goog-Upload-Command", "")
            logger.debug(f"Upload command: {headers.get('X-Goog-Upload-Command', '')}, is_final: {is_final}")
            
            # 转发到真实的上传 URL
            async with AsyncClient() as client:
                response = await client.post(
                    upload_url,
                    headers=headers,
                    content=body,
                    timeout=300.0  # 5分钟超时
                )
                
                if response.status_code not in [200, 201, 308]:
                    logger.error(f"Upload chunk failed: {response.status_code} - {response.text}")
                    raise HTTPException(status_code=response.status_code, detail="Upload failed")

                # 如果是最后一块，更新文件状态
                if is_final and response.status_code in [200, 201]:
                    logger.debug(f"Upload finalized with status {response.status_code}")
                    try:
                        # 解析響應獲取文件信息
                        response_data = response.json()
                        logger.debug(f"Upload complete response data: {response_data}")
                        file_data = response_data.get("file", {})
                        
                        # 獲取真實的文件名
                        real_file_name = file_data.get("name")
                        logger.debug(f"Upload response: {response_data}")
                        if real_file_name and files_service:
                            logger.info(f"Upload completed, file name: {real_file_name}")
                            
                            # 從會話中獲取信息
                            session_info = await files_service.get_upload_session(upload_url)
                            logger.debug(f"Retrieved session info for {upload_url}: {session_info}")
                            if session_info:
                                # 創建文件記錄
                                now = datetime.now(timezone.utc)
                                expiration_time = now + timedelta(hours=48)
                                
                                # 處理過期時間格式（Google 可能返回納秒級精度）
                                expiration_time_str = file_data.get("expirationTime", expiration_time.isoformat() + "Z")
                                # 處理納秒格式：2025-07-11T02:02:52.531916141Z -> 2025-07-11T02:02:52.531916Z
                                if expiration_time_str.endswith("Z"):
                                    # 移除 Z
                                    expiration_time_str = expiration_time_str[:-1]
                                    # 如果有納秒（超過6位小數），截斷到微秒
                                    if "." in expiration_time_str:
                                        date_part, frac_part = expiration_time_str.rsplit(".", 1)
                                        if len(frac_part) > 6:
                                            frac_part = frac_part[:6]
                                        expiration_time_str = f"{date_part}.{frac_part}"
                                    # 添加時區
                                    expiration_time_str += "+00:00"
                                
                                # 獲取文件狀態（Google 可能返回 PROCESSING）
                                file_state = file_data.get("state", "PROCESSING")
                                logger.debug(f"File state from Google: {file_state}")
                                
                                # 將字符串狀態轉換為枚舉
                                if file_state == "ACTIVE":
                                    state_enum = FileState.ACTIVE
                                elif file_state == "PROCESSING":
                                    state_enum = FileState.PROCESSING
                                elif file_state == "FAILED":
                                    state_enum = FileState.FAILED
                                else:
                                    logger.warning(f"Unknown file state: {file_state}, defaulting to PROCESSING")
                                    state_enum = FileState.PROCESSING
                                
                                await db_services.create_file_record(
                                    name=real_file_name,
                                    mime_type=file_data.get("mimeType", session_info["mime_type"]),
                                    size_bytes=int(file_data.get("sizeBytes", session_info["size_bytes"])),
                                    api_key=session_info["api_key"],
                                    uri=file_data.get("uri", f"{settings.BASE_URL}/{real_file_name}"),
                                    create_time=now,
                                    update_time=now,
                                    expiration_time=datetime.fromisoformat(expiration_time_str),
                                    state=state_enum,
                                    display_name=file_data.get("displayName", session_info.get("display_name", "")),
                                    sha256_hash=file_data.get("sha256Hash"),
                                    user_token=session_info["user_token"]
                                )
                                logger.info(f"Created file record: name={real_file_name}, api_key={session_info['api_key'][:8]}...{session_info['api_key'][-4:]}")
                            else:
                                logger.warning(f"No upload session found for URL: {upload_url}")
                        else:
                            logger.warning(f"Missing real_file_name or files_service: real_file_name={real_file_name}, files_service={files_service}")

                        # 返回完整的文件信息
                        return Response(
                            content=response.content,
                            status_code=response.status_code,
                            headers=dict(response.headers)
                        )
                    except Exception as e:
                        logger.error(f"Failed to create file record: {str(e)}", exc_info=True)
                else:
                    logger.debug(f"Upload chunk processed: is_final={is_final}, status={response.status_code}")
                
                # 返回响应
                response_headers = dict(response.headers)
                
                # 确保包含必要的头
                if response.status_code == 308:  # Resume Incomplete
                    if "x-goog-upload-status" not in response_headers:
                        response_headers["x-goog-upload-status"] = "active"
                
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=response_headers
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to handle upload chunk: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    async def proxy_upload_request(
        self,
        request: Request,
        upload_url: str,
        files_service=None
    ) -> Response:
        """
        代理上传请求
        
        Args:
            request: FastAPI 请求对象
            upload_url: 目标上传 URL
            files_service: 文件服務實例
            
        Returns:
            Response: 代理响应
        """
        logger.debug(f"Proxy upload request: {request.method}, {upload_url}")
        try:
            # 如果是 GET 请求，返回上传状态
            if request.method == "GET":
                return await self._get_upload_status(upload_url)
            
            # 处理 POST/PUT 请求
            return await self.handle_upload_chunk(upload_url, request, files_service)
            
        except Exception as e:
            logger.error(f"Failed to proxy upload request: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    async def _get_upload_status(self, upload_url: str) -> Response:
        """
        获取上传状态
        
        Args:
            upload_url: 上传 URL
            
        Returns:
            Response: 状态响应
        """
        try:
            async with AsyncClient() as client:
                response = await client.get(upload_url)
                
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
        except Exception as e:
            logger.error(f"Failed to get upload status: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# 单例实例
_upload_handler_instance: Optional[FileUploadHandler] = None


def get_upload_handler() -> FileUploadHandler:
    """获取上传处理器单例实例"""
    global _upload_handler_instance
    if _upload_handler_instance is None:
        _upload_handler_instance = FileUploadHandler()
    return _upload_handler_instance