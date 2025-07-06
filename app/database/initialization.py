"""
数据库初始化模块
"""
from dotenv import dotenv_values

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.database.connection import engine, Base
from app.database.models import Settings
from app.log.logger import get_database_logger
from app.database.services import api_key_service

logger = get_database_logger()


def create_tables():
    """
    创建数据库表
    """
    logger.info("Attempting to create database tables...")
    try:
        # 创建所有表
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        raise


def import_env_to_settings():
    """
    将.env文件中的配置项导入到t_settings表中
    """
    try:
        # 获取.env文件中的所有配置项
        env_values = dotenv_values(".env")
        
        # 获取检查器
        inspector = inspect(engine)
        
         # 检查t_settings表是否存在
        if "t_settings" in inspector.get_table_names():
            # 使用Session进行数据库操作
            with Session(engine) as session:
                # 获取所有现有的配置项
                current_settings = {setting.key: setting for setting in session.query(Settings).all()}
                
                # 遍历所有配置项
                for key, value in env_values.items():
                    # 检查配置项是否已存在
                    if key not in current_settings:
                        # 插入配置项
                        new_setting = Settings(key=key, value=value)
                        session.add(new_setting)
                        logger.info(f"Inserted setting: {key}")
                
                # 提交事务
                session.commit()
                
        logger.info("Environment variables imported to settings table successfully")
    except Exception as e:
        logger.error(f"Failed to import environment variables to settings table: {str(e)}")
        raise


async def initialize_database():
    """
    初始化数据库
    """
    try:
        # 创建表
        create_tables()

        # 导入环境变量
        import_env_to_settings()
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise