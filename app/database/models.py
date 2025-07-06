"""
数据库模型模块
"""
import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy.dialects.mysql import LONGTEXT

from app.database.connection import Base


class Settings(Base):
    """
    设置表，对应.env中的配置项
    """
    __tablename__ = "t_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False, unique=True, comment="配置项键名")
    value = Column(LONGTEXT, nullable=True, comment="配置项值")
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
    error_log = Column(LONGTEXT, nullable=True, comment="错误日志")
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


class Stats(Base):
    """
    统计信息表
    """
    __tablename__ = "t_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True, comment="统计日期")
    total_requests = Column(Integer, default=0, comment="总请求数")
    successful_requests = Column(Integer, default=0, comment="成功请求数")
    failed_requests = Column(Integer, default=0, comment="失败请求数")
    average_latency = Column(Integer, default=0, comment="平均延迟")
    
    def __repr__(self):
        return f"<Stats(date='{self.date}', total_requests='{self.total_requests}')>"


class APIKey(Base):
    """
    API密钥表
    """
    __tablename__ = "t_api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key_value = Column(LONGTEXT, nullable=False, unique=True, index=True, comment="API密钥值")
    service = Column(String(50), nullable=False, default="gemini", comment="所属服务 (e.g., 'gemini', 'openai')")
    status = Column(String(20), nullable=False, default="active", comment="密钥状态 ('active', 'banned', 'limited')")
    failure_count = Column(Integer, default=0, comment="失败次数")
    banned_at = Column(DateTime, nullable=True, comment="封禁时间")
    created_at = Column(DateTime, default=datetime.datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<APIKey(service='{self.service}', key_value='{self.key_value[:4]}...', status='{self.status}')>"
