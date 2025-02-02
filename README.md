# 🚀 FastAPI OpenAI 代理服务

## 📝 项目简介

这是一个基于 FastAPI 框架开发的 OpenAI API 代理服务。主要提供多 API Key 轮询、认证鉴权、流式响应等功能。

## ✨ 主要特性

- 🔄 多 API Key 轮询支持
- 🔐 Bearer Token 认证
- 📡 支持流式响应
- 🌐 CORS 跨域支持
- 📊 健康检查接口

## 🛠️ 技术栈

- FastAPI
- Python 3.9+
- Pydantic
- Docker
- httpx
- uvicorn

## 🚀 快速开始

### 环境要求

- Python 3.9+
- Docker (可选)

### 📦 安装依赖

```bash
pip install -r requirements.txt
```

### ⚙️ 配置文件

创建 `.env` 文件并配置以下参数:

```env
# API密钥列表，支持统一的代理地址配置
# 方式一：简单配置（使用默认代理地址）
API_KEYS='["your-api-key-1","your-api-key-2"]'

# 方式二：简单字符串列表
API_KEYS='["sk-xxx1","sk-xxx2"]'

# 统一的代理地址配置（可选，默认为 https://api.openai.com/v1）
BASE_URL="https://your-proxy-domain.com/v1"

# 允许的访问令牌列表
ALLOWED_TOKENS='["your-access-token-1","your-access-token-2"]'

# 可用模型列表（可选，默认包含gpt-4-turbo-preview等模型）
AVAILABLE_MODELS='["gpt-4-turbo-preview","gpt-4","gpt-3.5-turbo","text-embedding-3-small"]'
```

注意：
1. 环境变量中的 JSON 字符串必须使用单引号包裹
2. 列表类型的配置必须是有效的 JSON 格式
3. 所有配置项都支持通过环境变量传入

### 🐳 Docker 部署

你可以选择以下任一方式部署：

#### 方式一：使用预构建镜像

```bash
# 拉取最新版本镜像
docker pull ghcr.io/[your-username]/[repo-name]:latest

# 运行容器（简单配置）
docker run -d \
  -p 8000:8000 \
  -e API_KEYS='["your-api-key-1","your-api-key-2"]' \
  -e ALLOWED_TOKENS='["your-token-1","your-token-2"]' \
  ghcr.io/[your-username]/[repo-name]:latest

# 运行容器（高级配置）
docker run -d \
  -p 8000:8000 \
  -e API_KEYS='["your-api-key-1","your-api-key-2"]' \
  -e BASE_URL="https://your-proxy-domain.com/v1" \
  -e ALLOWED_TOKENS='["your-token-1","your-token-2"]' \
  -e AVAILABLE_MODELS='["gpt-4-turbo-preview","gpt-3.5-turbo"]' \
  ghcr.io/[your-username]/[repo-name]:latest
```

#### 方式二：本地构建

```bash
# 构建镜像
docker build -t openai-proxy .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -e API_KEYS='["your-api-key-1","your-api-key-2"]' \
  -e BASE_URL="https://your-proxy-domain.com/v1" \
  -e ALLOWED_TOKENS='["your-token-1","your-token-2"]' \
  openai-proxy
```

## 🔌 API 接口

### 获取模型列表

```http
GET /v1/models
Authorization: Bearer your-token
```

### 聊天完成

```http
POST /v1/chat/completions
Authorization: Bearer your-token

{
    "messages": [...],
    "model": "gpt-4-turbo-preview",
    "temperature": 0.7,
    "stream": false
}
```

### 获取 Embedding

```http
POST /v1/embeddings
Authorization: Bearer your-token

{
    "input": "Your text here",
    "model": "text-embedding-3-small"
}
```

### 健康检查

```http
GET /health
```

## 📚 代码结构

```plaintext
.
├── app/
│   ├── api/
│   │   ├── routes.py          # API路由
│   │   └── dependencies.py    # 依赖注入
│   ├── core/
│   │   ├── config.py         # 配置管理
│   │   └── security.py       # 安全认证
│   ├── services/
│   │   ├── chat_service.py   # 聊天服务
│   │   ├── key_manager.py    # Key管理
│   │   └── model_service.py  # 模型服务
│   ├── schemas/
│   │   └── request_model.py  # 请求模型
│   └── main.py              # 主程序入口
├── Dockerfile              # Docker配置
└── requirements.txt       # 项目依赖
```

## 🔒 安全特性

- API Key 轮询机制
- Bearer Token 认证
- 请求日志记录
- 失败重试机制
- Key 有效性检查

## 📝 注意事项

- 请确保妥善保管 API Keys 和访问令牌
- 建议在生产环境中使用环境变量配置敏感信息
- 默认服务端口为 8000
- API Key 失败重试次数默认为 10 次
- 可以通过环境变量 AVAILABLE_MODELS 配置可用的模型列表
- 可以通过环境变量 BASE_URL 配置统一的代理地址，默认使用 OpenAI 官方地址
- Docker 镜像支持 AMD64 和 ARM64 架构
- 每次推送到主分支或创建新的标签时会自动构建并发布 Docker 镜像

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## �� 许可证

MIT License
