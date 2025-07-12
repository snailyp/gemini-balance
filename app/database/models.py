"""
数据库模型模块
"""
import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, BigInteger, Enum
import enum

from app.database.connection import Base


class Settings(Base):
    """
    设置表，对应.env中的配置项
    """
    __tablename__ = "t_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False, unique=True, comment="配置项键名")
    value = Column(Text, nullable=True, comment="配置项值")
    description = Column(String(255), nullable=True, comment="配置项描述")
    created_at = Column(DateTime, default=datetime.datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment="更新时间")
    
    def __repr__(self):
        return f"<Settings(key='{self.key}', value='{self.value}')>"


class ErrorLog(Base):
    """
    错误日志表
    """
    __tablename__ = "t_error_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    gemini_key = Column(String(100), nullable=True, comment="Gemini API密钥")
    model_name = Column(String(100), nullable=True, comment="模型名称")
    error_type = Column(String(50), nullable=True, comment="错误类型")
    error_log = Column(Text, nullable=True, comment="错误日志")
    error_code = Column(Integer, nullable=True, comment="错误代码")
    request_msg = Column(JSON, nullable=True, comment="请求消息")
    request_time = Column(DateTime, default=datetime.datetime.now, comment="请求时间")
    
    def __repr__(self):
        return f"<ErrorLog(id='{self.id}', gemini_key='{self.gemini_key}')>"


class RequestLog(Base):
    """
    API 请求日志表
    """

    __tablename__ = "t_request_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_time = Column(DateTime, default=datetime.datetime.now, comment="请求时间")
    model_name = Column(String(100), nullable=True, comment="模型名称")
    api_key = Column(String(100), nullable=True, comment="使用的API密钥")
    is_success = Column(Boolean, nullable=False, comment="请求是否成功")
    status_code = Column(Integer, nullable=True, comment="API响应状态码")
    latency_ms = Column(Integer, nullable=True, comment="请求耗时(毫秒)")

    def __repr__(self):
        return f"<RequestLog(id='{self.id}', key='{self.api_key[:4]}...', success='{self.is_success}')>"


class FileState(enum.Enum):
    """文件状态枚举"""
    PROCESSING = "PROCESSING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"


class FileRecord(Base):
    """
    文件记录表，用于存储上传到 Gemini 的文件信息
    """
    __tablename__ = "t_file_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 文件基本信息
    name = Column(String(255), unique=True, nullable=False, comment="文件名称，格式: files/{file_id}")
    display_name = Column(String(255), nullable=True, comment="用户上传时的原始文件名")
    mime_type = Column(String(100), nullable=False, comment="MIME 类型")
    size_bytes = Column(BigInteger, nullable=False, comment="文件大小（字节）")
    sha256_hash = Column(String(255), nullable=True, comment="文件的 SHA256 哈希值")
    
    # 状态信息
    state = Column(Enum(FileState), nullable=False, default=FileState.PROCESSING, comment="文件状态")
    
    # 时间戳
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    update_time = Column(DateTime, nullable=False, comment="更新时间")
    expiration_time = Column(DateTime, nullable=False, comment="过期时间")
    
    # API 相关
    uri = Column(String(500), nullable=False, comment="文件访问 URI")
    api_key = Column(String(100), nullable=False, comment="上传时使用的 API Key")
    upload_url = Column(Text, nullable=True, comment="临时上传 URL（用于分块上传）")
    
    # 额外信息
    user_token = Column(String(100), nullable=True, comment="上传用户的 token")
    upload_completed = Column(DateTime, nullable=True, comment="上传完成时间")
    
    def __repr__(self):
        return f"<FileRecord(name='{self.name}', state='{self.state.value if self.state else 'None'}', api_key='{self.api_key[:8]}...')>"
    
    def to_dict(self):
        """转换为字典格式，用于 API 响应"""
        return {
            "name": self.name,
            "displayName": self.display_name,
            "mimeType": self.mime_type,
            "sizeBytes": str(self.size_bytes),
            "createTime": self.create_time.isoformat() + "Z",
            "updateTime": self.update_time.isoformat() + "Z",
            "expirationTime": self.expiration_time.isoformat() + "Z",
            "sha256Hash": self.sha256_hash,
            "uri": self.uri,
            "state": self.state.value if self.state else "PROCESSING"
        }
    
    def is_expired(self):
        """检查文件是否已过期"""
        # 确保比较时都是 timezone-aware
        expiration_time = self.expiration_time
        if expiration_time.tzinfo is None:
            expiration_time = expiration_time.replace(tzinfo=datetime.timezone.utc)
        return datetime.datetime.now(datetime.timezone.utc) > expiration_time
