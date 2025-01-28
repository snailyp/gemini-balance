FROM python:3.9-slim

# 创建非root用户
RUN useradd -m -u 1000 user
WORKDIR /app

# 安装依赖
COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 复制应用代码
COPY --chown=user ./app /app/app

# 切换到非root用户
USER user

# 设置环境变量
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    LOG_DIR=/home/user/logs \
    PORT=7860

# 暴露端口
EXPOSE 7860

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
