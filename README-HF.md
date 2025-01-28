# OpenAI API 代理服务

这是一个基于 FastAPI 开发的 OpenAI API 代理服务，支持多 API Key 轮询、认证鉴权、流式响应等功能。

## 🚀 功能特点

- 多 API Key 轮询
- Bearer Token 认证
- 流式响应支持
- 跨域支持
- 健康检查
- 支持自定义代理地址

## 🔧 环境变量配置

在 Hugging Face Space 的 Settings -> Repository Secrets 中配置以下环境变量：

```bash
# API密钥列表（必需）
API_KEYS='["your-api-key-1","your-api-key-2"]'

# 访问令牌列表（必需）
ALLOWED_TOKENS='["your-token-1","your-token-2"]'

# 可用模型列表（可选）
AVAILABLE_MODELS='["gpt-4-turbo-preview","gpt-3.5-turbo"]'
```

## 📚 API 文档

启动服务后访问 `/docs` 或 `/redoc` 查看完整的 API 文档。

### 基本接口

1. 聊天完成
```http
POST /v1/chat/completions
Authorization: Bearer your-token

{
    "messages": [...],
    "model": "gpt-4-turbo-preview",
    "temperature": 0.7
}
```

2. Embedding
```http
POST /v1/embeddings
Authorization: Bearer your-token

{
    "input": "Your text here",
    "model": "text-embedding-3-small"
}
```

## 🔒 安全说明

- 所有请求都需要通过 Bearer Token 认证
- API Key 轮询机制确保负载均衡
- 失败自动重试和切换机制
- 支持配置独立的代理地址

## 📝 使用说明

1. Fork 这个 Space
2. 在 Settings 中配置环境变量
3. 等待自动部署完成
4. 使用配置的 Token 访问 API

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## �� 许可证

MIT License 