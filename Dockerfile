FROM python:3.10-slim

WORKDIR /app

# 复制所需文件到容器中
COPY ./requirements.txt /app
COPY ./VERSION /app
COPY ./bulk_verify_keys.py /app

RUN pip install --no-cache-dir -r requirements.txt
COPY ./import_keys.py /app
COPY ./allkeys.txt /app
COPY ./app /app/app
COPY ./tests /app/tests
RUN find ./app -type f -print0 | sort -z | xargs -0 sha1sum | sha1sum > /tmp/app_checksum
ENV API_KEYS='["your_api_key_1"]'
ENV ALLOWED_TOKENS='["your_token_1"]'
ENV BASE_URL=https://generativelanguage.googleapis.com/v1beta
ENV TOOLS_CODE_EXECUTION_ENABLED=false
ENV IMAGE_MODELS='["gemini-2.0-flash-exp"]'
ENV SEARCH_MODELS='["gemini-2.0-flash-exp","gemini-2.0-pro-exp"]'

# Expose port
EXPOSE 6000

# Set the Python path
ENV PYTHONPATH=/app

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "6000", "--no-access-log"]
