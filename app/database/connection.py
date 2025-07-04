"""
数据库连接池模块
"""
from pathlib import Path
from urllib.parse import quote_plus
from databases import Database
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base

from app.config.config import settings
from app.log.logger import get_database_logger

logger = get_database_logger()

# 数据库URL
if settings.DATABASE_TYPE == "sqlite":
    # 确保 data 目录存在
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / settings.SQLITE_DATABASE
    DATABASE_URL = f"sqlite:///{db_path}"
elif settings.DATABASE_TYPE == "mysql":
    if settings.MYSQL_SOCKET:
        DATABASE_URL = f"mysql+pymysql://{settings.MYSQL_USER}:{quote_plus(settings.MYSQL_PASSWORD)}@/{settings.MYSQL_DATABASE}?unix_socket={settings.MYSQL_SOCKET}"
    else:
        DATABASE_URL = f"mysql+pymysql://{settings.MYSQL_USER}:{quote_plus(settings.MYSQL_PASSWORD)}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
else:
    raise ValueError("Unsupported database type. Please set DATABASE_TYPE to 'sqlite' or 'mysql'.")

# 创建数据库引擎
# pool_pre_ping=True: 在从连接池获取连接前执行简单的 "ping" 测试，确保连接有效
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 创建元数据对象
metadata = MetaData()

# 创建基类
Base = declarative_base(metadata=metadata)

# 创建数据库连接池，并配置连接池参数，在sqlite中不使用连接池
# min_size/max_size: 连接池的最小/最大连接数
# pool_recycle=3600: 连接在池中允许存在的最大秒数（生命周期）。
#                    设置为 3600 秒（1小时），确保在 MySQL 默认的 wait_timeout (通常8小时) 或其他网络超时之前回收连接。
#                    如果遇到连接失效问题，可以尝试调低此值，使其小于实际的 wait_timeout 或网络超时时间。
# databases 库会自动处理连接失效后的重连尝试。
if settings.DATABASE_TYPE == "sqlite":
    database = Database(DATABASE_URL)
else:
    database = Database(DATABASE_URL, min_size=5, max_size=20, pool_recycle=1800)

async def connect_to_db():
    """
    连接到数据库
    """
    try:
        await database.connect()
        logger.info(f"Connected to {settings.DATABASE_TYPE}")
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        raise


async def disconnect_from_db():
    """
    断开数据库连接
    """
    try:
        await database.disconnect()
        logger.info(f"Disconnected from {settings.DATABASE_TYPE}")
    except Exception as e:
        logger.error(f"Failed to disconnect from database: {str(e)}")
