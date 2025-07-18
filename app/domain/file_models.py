"""
Files API 相关的领域模型
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class FileUploadConfig(BaseModel):
    """文件上传配置"""
    mime_type: Optional[str] = Field(None, description="MIME 类型")
    display_name: Optional[str] = Field(None, description="显示名称，最多40个字符")


class CreateFileRequest(BaseModel):
    """创建文件请求（用于初始化上传）"""
    file: Optional[Dict[str, Any]] = Field(None, description="文件元数据")
    

class FileMetadata(BaseModel):
    """文件元数据响应"""
    name: str = Field(..., description="文件名称，格式: files/{file_id}")
    displayName: Optional[str] = Field(None, description="显示名称")
    mimeType: str = Field(..., description="MIME 类型")
    sizeBytes: str = Field(..., description="文件大小（字节）")
    createTime: str = Field(..., description="创建时间 (RFC3339)")
    updateTime: str = Field(..., description="更新时间 (RFC3339)")
    expirationTime: str = Field(..., description="过期时间 (RFC3339)")
    sha256Hash: Optional[str] = Field(None, description="SHA256 哈希值")
    uri: str = Field(..., description="文件访问 URI")
    state: str = Field(..., description="文件状态")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }


class ListFilesRequest(BaseModel):
    """列出文件请求参数"""
    pageSize: Optional[int] = Field(10, ge=1, le=100, description="每页大小")
    pageToken: Optional[str] = Field(None, description="分页标记")


class ListFilesResponse(BaseModel):
    """列出文件响应"""
    files: List[FileMetadata] = Field(default_factory=list, description="文件列表")
    nextPageToken: Optional[str] = Field(None, description="下一页标记")


class UploadInitResponse(BaseModel):
    """上传初始化响应（内部使用）"""
    file_metadata: FileMetadata
    upload_url: str


class FileKeyMapping(BaseModel):
    """文件与 API Key 的映射关系（内部使用）"""
    file_name: str
    api_key: str
    user_token: str
    created_at: datetime
    expires_at: datetime


class DeleteFileResponse(BaseModel):
    """删除文件响应"""
    success: bool = Field(..., description="是否删除成功")
    message: Optional[str] = Field(None, description="消息")