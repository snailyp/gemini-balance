import uvicorn
from dotenv import load_dotenv

# 在导入应用程序配置之前加载 .env 文件到环境变量
load_dotenv()

from app.core.application import create_app
from app.log.logger import get_main_logger

app = create_app()

if __name__ == "__main__":
    logger = get_main_logger()
    logger.info("Starting application server...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
