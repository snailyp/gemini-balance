"""
Files API 路由
"""
from typing import Optional
from fastapi import APIRouter, Request, Query, Depends, Header, HTTPException
from fastapi.responses import JSONResponse

from app.config.config import settings
from app.domain.file_models import (
    FileMetadata, 
    ListFilesResponse, 
    DeleteFileResponse
)
from app.log.logger import get_files_logger
from app.core.security import SecurityService
from app.service.files.files_service import get_files_service
from app.service.files.file_upload_handler import get_upload_handler

logger = get_files_logger()

router = APIRouter()
security_service = SecurityService()


@router.post("/upload/v1beta/files")
async def upload_file_init(
    request: Request,
    auth_token: str = Depends(security_service.verify_key_or_goog_api_key),
    x_goog_upload_protocol: Optional[str] = Header(None),
    x_goog_upload_command: Optional[str] = Header(None),
    x_goog_upload_header_content_length: Optional[str] = Header(None),
    x_goog_upload_header_content_type: Optional[str] = Header(None),
):
    """初始化文件上传"""
    logger.debug(f"Upload file request: {request.method=}, {request.url=}, {auth_token=}, {x_goog_upload_protocol=}, {x_goog_upload_command=}, {x_goog_upload_header_content_length=}, {x_goog_upload_header_content_type=}")
    
    # 檢查是否是實際的上傳請求（有 upload_id）
    if request.query_params.get("upload_id") and x_goog_upload_command in ["upload", "upload, finalize"]:
        logger.debug("This is an upload request, not initialization. Redirecting to handle_upload.")
        return await handle_upload(
            upload_path="v1beta/files",
            request=request,
            key=request.query_params.get("key"),
            auth_token=auth_token
        )
    
    try:
        # 使用认证 token 作为 user_token
        user_token = auth_token
        # 获取请求体
        body = await request.body()
        
        # 构建请求主机 URL
        request_host = f"{request.url.scheme}://{request.url.netloc}"
        logger.info(f"Request host: {request_host}")
        
        # 准备请求头
        headers = {
            "x-goog-upload-protocol": x_goog_upload_protocol or "resumable",
            "x-goog-upload-command": x_goog_upload_command or "start",
        }
        
        if x_goog_upload_header_content_length:
            headers["x-goog-upload-header-content-length"] = x_goog_upload_header_content_length
        if x_goog_upload_header_content_type:
            headers["x-goog-upload-header-content-type"] = x_goog_upload_header_content_type
        
        # 调用服务
        files_service = await get_files_service()
        response_data, response_headers = await files_service.initialize_upload(
            headers=headers,
            body=body,
            user_token=user_token,
            request_host=request_host  # 傳遞請求主機
        )

        logger.info(f"Upload initialization response: {response_data}")
        logger.info(f"Upload initialization response headers: {response_headers}")
        
        logger.info(f"Upload initialization response headers: {response_data}")
        # 返回响应
        return JSONResponse(
            content=response_data,
            headers=response_headers
        )
        
    except HTTPException as e:
        logger.error(f"Upload initialization failed: {e.detail}")
        return JSONResponse(
            content={"error": {"message": e.detail}},
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected error in upload initialization: {str(e)}")
        return JSONResponse(
            content={"error": {"message": "Internal server error"}},
            status_code=500
        )


@router.get("/v1beta/files")
async def list_files(
    page_size: int = Query(10, ge=1, le=100, description="每页大小", alias="pageSize"),
    page_token: Optional[str] = Query(None, description="分页标记", alias="pageToken"),
    auth_token: str = Depends(security_service.verify_key_or_goog_api_key)
) -> ListFilesResponse:
    """列出文件"""
    logger.debug(f"List files: {page_size=}, {page_token=}, {auth_token=}")
    try:
        # 使用认证 token 作为 user_token（如果启用用户隔离）
        user_token = auth_token if settings.FILES_USER_ISOLATION_ENABLED else None
        # 调用服务
        files_service = await get_files_service()
        return await files_service.list_files(
            page_size=page_size,
            page_token=page_token,
            user_token=user_token
        )
        
    except HTTPException as e:
        logger.error(f"List files failed: {e.detail}")
        return JSONResponse(
            content={"error": {"message": e.detail}},
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected error in list files: {str(e)}")
        return JSONResponse(
            content={"error": {"message": "Internal server error"}},
            status_code=500
        )


@router.get("/v1beta/files/{file_id:path}")
async def get_file(
    file_id: str,
    auth_token: str = Depends(security_service.verify_key_or_goog_api_key)
) -> FileMetadata:
    """获取文件信息"""
    logger.debug(f"Get file request: {file_id=}, {auth_token=}")
    try:
        # 使用认证 token 作为 user_token
        user_token = auth_token
        # 调用服务
        files_service = await get_files_service()
        return await files_service.get_file(f"files/{file_id}", user_token)
        
    except HTTPException as e:
        logger.error(f"Get file failed: {e.detail}")
        return JSONResponse(
            content={"error": {"message": e.detail}},
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected error in get file: {str(e)}")
        return JSONResponse(
            content={"error": {"message": "Internal server error"}},
            status_code=500
        )


@router.delete("/v1beta/files/{file_id:path}")
async def delete_file(
    file_id: str,
    auth_token: str = Depends(security_service.verify_key_or_goog_api_key)
) -> DeleteFileResponse:
    """删除文件"""
    logger.info(f"Delete file: {file_id=}, {auth_token=}")
    try:
        # 使用认证 token 作为 user_token
        user_token = auth_token
        # 调用服务
        files_service = await get_files_service()
        success = await files_service.delete_file(f"files/{file_id}", user_token)
        
        return DeleteFileResponse(
            success=success,
            message="File deleted successfully" if success else "Failed to delete file"
        )
        
    except HTTPException as e:
        logger.error(f"Delete file failed: {e.detail}")
        return JSONResponse(
            content={"error": {"message": e.detail}},
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected error in delete file: {str(e)}")
        return JSONResponse(
            content={"error": {"message": "Internal server error"}},
            status_code=500
        )


# 处理上传请求的通配符路由
@router.api_route("/upload/{upload_path:path}", methods=["GET", "POST", "PUT"])
async def handle_upload(
    upload_path: str,
    request: Request,
    key: Optional[str] = Query(None),  # 從查詢參數獲取 key
    auth_token: str = Depends(security_service.verify_key_or_goog_api_key)
):
    """处理文件上传请求"""
    try:
        logger.info(f"Handling upload request: {request.method} {upload_path}, key={key}")
        
        # 從查詢參數獲取 upload_id
        upload_id = request.query_params.get("upload_id")
        if not upload_id:
            raise HTTPException(status_code=400, detail="Missing upload_id")
        
        # 從 session 獲取真實的 API key
        files_service = await get_files_service()
        session_info = await files_service.get_upload_session(upload_id)
        if not session_info:
            logger.error(f"No session found for upload_id: {upload_id}")
            raise HTTPException(status_code=404, detail="Upload session not found")
        
        real_api_key = session_info["api_key"]
        original_upload_url = session_info["upload_url"]
        
        # 使用真實的 API key 構建完整的 Google 上傳 URL
        # 保留原始 URL 的所有參數，但使用真實的 API key
        upload_url = original_upload_url
        logger.info(f"Using real API key for upload: {real_api_key[:8]}...{real_api_key[-4:]}")
        
        # 代理上传请求
        upload_handler = get_upload_handler()
        return await upload_handler.proxy_upload_request(
            request=request,
            upload_url=upload_url,
            files_service=files_service
        )
        
    except HTTPException as e:
        logger.error(f"Upload handling failed: {e.detail}")
        return JSONResponse(
            content={"error": {"message": e.detail}},
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected error in upload handling: {str(e)}")
        return JSONResponse(
            content={"error": {"message": "Internal server error"}},
            status_code=500
        )


# 为兼容性添加 /gemini 前缀的路由
@router.post("/gemini/upload/v1beta/files")
async def gemini_upload_file_init(
    request: Request,
    auth_token: str = Depends(security_service.verify_key_or_goog_api_key),
    x_goog_upload_protocol: Optional[str] = Header(None),
    x_goog_upload_command: Optional[str] = Header(None),
    x_goog_upload_header_content_length: Optional[str] = Header(None),
    x_goog_upload_header_content_type: Optional[str] = Header(None),
):
    """初始化文件上传（Gemini 前缀）"""
    return await upload_file_init(
        request,
        auth_token,
        x_goog_upload_protocol,
        x_goog_upload_command,
        x_goog_upload_header_content_length,
        x_goog_upload_header_content_type
    )


@router.get("/gemini/v1beta/files")
async def gemini_list_files(
    page_size: int = Query(10, ge=1, le=100, alias="pageSize"),
    page_token: Optional[str] = Query(None, alias="pageToken"),
    auth_token: str = Depends(security_service.verify_key_or_goog_api_key)
) -> ListFilesResponse:
    """列出文件（Gemini 前缀）"""
    return await list_files(page_size, page_token, auth_token)


@router.get("/gemini/v1beta/files/{file_id:path}")
async def gemini_get_file(
    file_id: str,
    auth_token: str = Depends(security_service.verify_key_or_goog_api_key)
) -> FileMetadata:
    """获取文件信息（Gemini 前缀）"""
    return await get_file(file_id, auth_token)


@router.delete("/gemini/v1beta/files/{file_id:path}")
async def gemini_delete_file(
    file_id: str,
    auth_token: str = Depends(security_service.verify_key_or_goog_api_key)
) -> DeleteFileResponse:
    """删除文件（Gemini 前缀）"""
    return await delete_file(file_id, auth_token)