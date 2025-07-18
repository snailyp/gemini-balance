"""
文件管理服务
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from httpx import AsyncClient
import asyncio

from app.config.config import settings
from app.database import services as db_services
from app.database.models import FileState
from app.domain.file_models import FileMetadata, ListFilesResponse
from fastapi import HTTPException
from app.log.logger import get_files_logger
from app.service.client.api_client import GeminiApiClient
from app.service.key.key_manager import get_key_manager_instance

logger = get_files_logger()

# 全局上傳會話存儲
_upload_sessions: Dict[str, Dict[str, Any]] = {}
_upload_sessions_lock = asyncio.Lock()


class FilesService:
    """文件管理服务类"""
    
    def __init__(self):
        self.api_client = GeminiApiClient(base_url=settings.BASE_URL)
        self.key_manager = None
    
    async def _get_key_manager(self):
        """获取 KeyManager 实例"""
        if not self.key_manager:
            self.key_manager = await get_key_manager_instance(
                settings.API_KEYS, 
                settings.VERTEX_API_KEYS
            )
        return self.key_manager
    
    async def initialize_upload(
        self, 
        headers: Dict[str, str], 
        body: Optional[bytes],
        user_token: str,
        request_host: str = None  # 添加請求主機參數
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        初始化文件上传
        
        Args:
            headers: 请求头
            body: 请求体
            user_token: 用户令牌
            
        Returns:
            Tuple[Dict[str, Any], Dict[str, str]]: (响应体, 响应头)
        """
        try:
            # 获取可用的 API key
            key_manager = await self._get_key_manager()
            api_key = await key_manager.get_next_key()
            
            if not api_key:
                raise HTTPException(status_code=503, detail="No available API keys")
            
            # 转发请求到真实的 Gemini API
            async with AsyncClient() as client:
                # 准备请求头
                forward_headers = {
                    "X-Goog-Upload-Protocol": headers.get("x-goog-upload-protocol", "resumable"),
                    "X-Goog-Upload-Command": headers.get("x-goog-upload-command", "start"),
                    "Content-Type": headers.get("content-type", "application/json"),
                }
                
                # 添加其他必要的头
                if "x-goog-upload-header-content-length" in headers:
                    forward_headers["X-Goog-Upload-Header-Content-Length"] = headers["x-goog-upload-header-content-length"]
                if "x-goog-upload-header-content-type" in headers:
                    forward_headers["X-Goog-Upload-Header-Content-Type"] = headers["x-goog-upload-header-content-type"]
                
                # 发送请求
                response = await client.post(
                    "https://generativelanguage.googleapis.com/upload/v1beta/files",
                    headers=forward_headers,
                    content=body,
                    params={"key": api_key}
                )
                
                if response.status_code != 200:
                    logger.error(f"Upload initialization failed: {response.status_code} - {response.text}")
                    raise HTTPException(status_code=response.status_code, detail="Upload initialization failed")
                
                # 获取上传 URL
                upload_url = response.headers.get("x-goog-upload-url")
                if not upload_url:
                    raise HTTPException(status_code=500, detail="No upload URL in response")
                
                logger.info(f"Original upload URL from Google: {upload_url}")
                    
                
                # 儲存上傳資訊到 headers 中，供後續使用
                # 不在這裡創建數據庫記錄，等到上傳完成後再創建
                logger.info(f"Upload initialized with API key: {api_key[:8]}...{api_key[-4:]}")
                
                # 解析响应 - 初始化响应可能是空的
                response_data = {}
                
                # 從請求體中解析文件信息（如果有）
                display_name = ""
                if body:
                    try:
                        request_data = json.loads(body)
                        display_name = request_data.get("displayName", "")
                    except Exception:
                        pass
                # 從 upload URL 中提取 upload_id
                import urllib.parse
                parsed_url = urllib.parse.urlparse(upload_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                upload_id = query_params.get('upload_id', [None])[0]
                
                if upload_id:
                    # 儲存上傳會話信息，使用 upload_id 作為 key
                    async with _upload_sessions_lock:
                        _upload_sessions[upload_id] = {
                            "api_key": api_key,
                            "user_token": user_token,
                            "display_name": display_name,
                            "mime_type": headers.get("x-goog-upload-header-content-type", "application/octet-stream"),
                            "size_bytes": int(headers.get("x-goog-upload-header-content-length", "0")),
                            "created_at": datetime.now(timezone.utc),
                            "upload_url": upload_url
                        }
                        logger.info(f"Stored upload session for upload_id={upload_id}: api_key={api_key[:8]}...{api_key[-4:]}")
                        logger.debug(f"Total active sessions: {len(_upload_sessions)}")
                else:
                    logger.warning(f"No upload_id found in upload URL: {upload_url}")
                
                # 定期清理過期的會話（超過1小時）
                asyncio.create_task(self._cleanup_expired_sessions())
                
                # 替換 Google 的 URL 為我們的代理 URL
                proxy_upload_url = upload_url
                if request_host:
                    # 原始: https://generativelanguage.googleapis.com/upload/v1beta/files?key=AIzaSyDc...&upload_id=xxx&upload_protocol=resumable
                    # 替換為: http://request-host/upload/v1beta/files?key=sk-123456&upload_id=xxx&upload_protocol=resumable
                    
                    # 先替換域名
                    proxy_upload_url = upload_url.replace(
                        "https://generativelanguage.googleapis.com",
                        request_host.rstrip('/')
                    )
                    
                    # 再替換 key 參數
                    import re
                    # 匹配 key=xxx 參數
                    key_pattern = r'(\?|&)key=([^&]+)'
                    match = re.search(key_pattern, proxy_upload_url)
                    if match:
                        # 替換為我們的 token
                        proxy_upload_url = proxy_upload_url.replace(
                            f"{match.group(1)}key={match.group(2)}",
                            f"{match.group(1)}key={user_token}"
                        )
                    
                    logger.info(f"Replaced upload URL: {upload_url} -> {proxy_upload_url}")
                
                return response_data, {
                    "X-Goog-Upload-URL": proxy_upload_url,
                    "X-Goog-Upload-Status": "active"
                }
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to initialize upload: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    async def _cleanup_expired_sessions(self):
        """清理過期的上傳會話"""
        try:
            async with _upload_sessions_lock:
                now = datetime.now(timezone.utc)
                expired_keys = []
                for key, session in _upload_sessions.items():
                    if now - session["created_at"] > timedelta(hours=1):
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del _upload_sessions[key]
                    
                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired upload sessions")
        except Exception as e:
            logger.error(f"Error cleaning up upload sessions: {str(e)}")
    
    async def get_upload_session(self, key: str) -> Optional[Dict[str, Any]]:
        """獲取上傳會話信息（支持 upload_id 或完整 URL）"""
        async with _upload_sessions_lock:
            # 先嘗試直接查找
            session = _upload_sessions.get(key)
            if session:
                logger.debug(f"Found session by direct key {key}")
                return session
            
            # 如果是 URL，嘗試提取 upload_id
            if key.startswith("http"):
                import urllib.parse
                parsed_url = urllib.parse.urlparse(key)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                upload_id = query_params.get('upload_id', [None])[0]
                if upload_id:
                    session = _upload_sessions.get(upload_id)
                    if session:
                        logger.debug(f"Found session by upload_id {upload_id} from URL")
                        return session
            
            logger.debug(f"No session found for key: {key}")
            return None
    
    async def get_file(self, file_name: str, user_token: str) -> FileMetadata:
        """
        获取文件信息
        
        Args:
            file_name: 文件名称 (格式: files/{file_id})
            user_token: 用户令牌
            
        Returns:
            FileMetadata: 文件元数据
        """
        try:
            # 查询文件记录
            file_record = await db_services.get_file_record_by_name(file_name)
            
            if not file_record:
                raise HTTPException(status_code=404, detail="File not found")
            
            # 检查是否过期
            expiration_time = datetime.fromisoformat(str(file_record["expiration_time"]))
            # 如果是 naive datetime，假设为 UTC
            if expiration_time.tzinfo is None:
                expiration_time = expiration_time.replace(tzinfo=timezone.utc)
            if expiration_time <= datetime.now(timezone.utc):
                raise HTTPException(status_code=404, detail="File has expired")
            
            # 使用原始 API key 获取文件信息
            api_key = file_record["api_key"]
            
            async with AsyncClient() as client:
                response = await client.get(
                    f"{settings.BASE_URL}/{file_name}",
                    params={"key": api_key}
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to get file: {response.status_code} - {response.text}")
                    raise HTTPException(status_code=response.status_code, detail="Failed to get file")
                
                file_data = response.json()
                
                # 檢查並更新文件狀態
                google_state = file_data.get("state", "PROCESSING")
                if google_state != file_record.get("state", "").value if file_record.get("state") else None:
                    logger.info(f"File state changed from {file_record.get('state')} to {google_state}")
                    # 更新數據庫中的狀態
                    if google_state == "ACTIVE":
                        await db_services.update_file_record_state(
                            file_name=file_name,
                            state=FileState.ACTIVE,
                            update_time=datetime.now(timezone.utc)
                        )
                    elif google_state == "FAILED":
                        await db_services.update_file_record_state(
                            file_name=file_name,
                            state=FileState.FAILED,
                            update_time=datetime.now(timezone.utc)
                        )
                
                # 构建响应
                return FileMetadata(
                    name=file_data["name"],
                    displayName=file_data.get("displayName"),
                    mimeType=file_data["mimeType"],
                    sizeBytes=str(file_data["sizeBytes"]),
                    createTime=file_data["createTime"],
                    updateTime=file_data["updateTime"],
                    expirationTime=file_data["expirationTime"],
                    sha256Hash=file_data.get("sha256Hash"),
                    uri=file_data["uri"],
                    state=google_state
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get file {file_name}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    async def list_files(
        self, 
        page_size: int = 10,
        page_token: Optional[str] = None,
        user_token: Optional[str] = None
    ) -> ListFilesResponse:
        """
        列出文件
        
        Args:
            page_size: 每页大小
            page_token: 分页标记
            user_token: 用户令牌（可选，如果提供则只返回该用户的文件）
            
        Returns:
            ListFilesResponse: 文件列表响应
        """
        try:
            logger.debug(f"list_files called with page_size={page_size}, page_token={page_token}")
            
            # 从数据库获取文件列表
            files, next_page_token = await db_services.list_file_records(
                user_token=user_token,
                page_size=page_size,
                page_token=page_token
            )
            
            logger.debug(f"Database returned {len(files)} files, next_page_token={next_page_token}")
            
            # 转换为响应格式
            file_list = []
            for file_record in files:
                file_list.append(FileMetadata(
                    name=file_record["name"],
                    displayName=file_record.get("display_name"),
                    mimeType=file_record["mime_type"],
                    sizeBytes=str(file_record["size_bytes"]),
                    createTime=file_record["create_time"].isoformat() + "Z",
                    updateTime=file_record["update_time"].isoformat() + "Z",
                    expirationTime=file_record["expiration_time"].isoformat() + "Z",
                    sha256Hash=file_record.get("sha256_hash"),
                    uri=file_record["uri"],
                    state=file_record["state"].value if file_record.get("state") else "ACTIVE"
                ))
            
            response = ListFilesResponse(
                files=file_list,
                nextPageToken=next_page_token
            )
            
            logger.debug(f"Returning response with {len(response.files)} files, nextPageToken={response.nextPageToken}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to list files: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    async def delete_file(self, file_name: str, user_token: str) -> bool:
        """
        删除文件
        
        Args:
            file_name: 文件名称
            user_token: 用户令牌
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 查询文件记录
            file_record = await db_services.get_file_record_by_name(file_name)
            
            if not file_record:
                raise HTTPException(status_code=404, detail="File not found")
            
            # 使用原始 API key 删除文件
            api_key = file_record["api_key"]
            
            async with AsyncClient() as client:
                response = await client.delete(
                    f"{settings.BASE_URL}/{file_name}",
                    params={"key": api_key}
                )
                
                if response.status_code not in [200, 204]:
                    logger.error(f"Failed to delete file: {response.status_code} - {response.text}")
                    # 如果 API 删除失败，但文件已过期，仍然删除数据库记录
                    expiration_time = datetime.fromisoformat(str(file_record["expiration_time"]))
                    if expiration_time.tzinfo is None:
                        expiration_time = expiration_time.replace(tzinfo=timezone.utc)
                    if expiration_time <= datetime.now(timezone.utc):
                        await db_services.delete_file_record(file_name)
                        return True
                    raise HTTPException(status_code=response.status_code, detail="Failed to delete file")
            
            # 删除数据库记录
            await db_services.delete_file_record(file_name)
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete file {file_name}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    async def check_file_state(self, file_name: str, api_key: str) -> str:
        """
        檢查並更新文件狀態
        
        Args:
            file_name: 文件名稱
            api_key: API密鑰
            
        Returns:
            str: 當前狀態
        """
        try:
            async with AsyncClient() as client:
                response = await client.get(
                    f"{settings.BASE_URL}/{file_name}",
                    params={"key": api_key}
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to check file state: {response.status_code}")
                    return "UNKNOWN"
                
                file_data = response.json()
                google_state = file_data.get("state", "PROCESSING")
                
                # 更新數據庫狀態
                if google_state == "ACTIVE":
                    await db_services.update_file_record_state(
                        file_name=file_name,
                        state=FileState.ACTIVE,
                        update_time=datetime.now(timezone.utc)
                    )
                elif google_state == "FAILED":
                    await db_services.update_file_record_state(
                        file_name=file_name,
                        state=FileState.FAILED,
                        update_time=datetime.now(timezone.utc)
                    )
                
                return google_state
                
        except Exception as e:
            logger.error(f"Failed to check file state: {str(e)}")
            return "UNKNOWN"
    
    async def cleanup_expired_files(self) -> int:
        """
        清理过期文件
        
        Returns:
            int: 清理的文件数量
        """
        try:
            # 获取过期文件
            expired_files = await db_services.delete_expired_file_records()
            
            if not expired_files:
                return 0
            
            # 尝试从 Gemini API 删除文件
            for file_record in expired_files:
                try:
                    api_key = file_record["api_key"]
                    file_name = file_record["name"]
                    
                    async with AsyncClient() as client:
                        await client.delete(
                            f"{settings.BASE_URL}/{file_name}",
                            params={"key": api_key}
                        )
                except Exception as e:
                    # 记录错误但继续处理其他文件
                    logger.error(f"Failed to delete file {file_record['name']} from API: {str(e)}")
            
            return len(expired_files)
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired files: {str(e)}")
            return 0


# 单例实例
_files_service_instance: Optional[FilesService] = None


async def get_files_service() -> FilesService:
    """获取文件服务单例实例"""
    global _files_service_instance
    if _files_service_instance is None:
        _files_service_instance = FilesService()
    return _files_service_instance