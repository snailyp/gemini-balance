# Gemini Balance - Gemini API 代理和负载均衡器

<p align="center">
  <a href="https://trendshift.io/repositories/13692" target="_blank">
    <img src="https://trendshift.io/api/badge/repositories/13692" alt="snailyp%2Fgemini-balance | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/>
  </a>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.9%2B-blue.svg" alt="Python"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.100%2B-green.svg" alt="FastAPI"></a>
  <a href="https://www.uvicorn.org/"><img src="https://img.shields.io/badge/Uvicorn-running-purple.svg" alt="Uvicorn"></a>
  <a href="https://t.me/+soaHax5lyI0wZDVl"><img src="https://img.shields.io/badge/Telegram-Group-blue.svg?logo=telegram" alt="Telegram Group"></a>
</p>

> ⚠️ **重要声明**: 本项目采用 [CC BY-NC 4.0](LICENSE) 协议，**禁止任何形式的商业倒卖服务**。
> 本人从未在任何平台售卖服务，如遇售卖，均为倒卖行为，请勿上当受骗。

---

## 📖 项目简介

**Gemini Balance** 是一个基于 Python FastAPI 构建的应用程序，旨在提供 Google Gemini API 的代理和负载均衡功能。它允许您管理多个 Gemini API Key，并通过简单的配置实现 Key 的轮询、认证、模型过滤和状态监控。此外，项目还集成了图像生成和多种图床上传功能，并支持 OpenAI API 格式的代理。

<details>
<summary>📂 查看项目结构</summary>

```plaintext
app/
├── config/       # 配置管理
├── core/         # 核心应用逻辑 (FastAPI 实例创建, 中间件等)
├── database/     # 数据库模型和连接
├── domain/       # 业务领域对象
├── exception/    # 自定义异常
├── handler/      # 请求处理器
├── log/          # 日志配置
├── main.py       # 应用入口
├── middleware/   # FastAPI 中间件
├── router/       # API 路由 (Gemini, OpenAI, 状态页等)
├── scheduler/    # 定时任务 (如 Key 状态检查)
├── service/      # 业务逻辑服务 (聊天, Key 管理, 统计等)
├── static/       # 静态文件 (CSS, JS)
├── templates/    # HTML 模板 (如 Key 状态页)
└── utils/        # 工具函数
```
</details>

---

## ✨ 功能亮点

*   **多 Key 负载均衡**: 支持配置多个 Gemini API Key (`API_KEYS`)，自动按顺序轮询使用，提高可用性和并发能力。
*   **可视化配置即时生效**: 通过管理后台修改配置后，无需重启服务即可生效。
    ![配置面板](files/image4.png)
*   **双协议 API 兼容**: 同时支持 Gemini 和 OpenAI 格式的 CHAT API 请求转发。
    *   OpenAI Base URL: `http://localhost:8000(/hf)/v1`
    *   Gemini Base URL: `http://localhost:8000(/gemini)/v1beta`
*   **图文对话与修图**: 通过 `IMAGE_MODELS` 配置支持图文对话和修图功能的模型，调用时使用 `配置模型-image` 模型名。
    ![对话生图](files/image6.png)
    ![修改图片](files/image7.png)
*   **联网搜索**: 通过 `SEARCH_MODELS` 配置支持联网搜索的模型，调用时使用 `配置模型-search` 模型名。
    ![联网搜索](files/image8.png)
*   **Key 状态监控**: 提供 `/keys_status` 页面（需要认证），实时查看各 Key 的状态和使用情况。
    ![监控面板](files/image.png)
*   **详细日志记录**: 提供详细的错误日志，方便排查问题。
    ![调用详情](files/image1.png)
    ![日志列表](files/image2.png)
    ![日志详情](files/image3.png)
*   **灵活的密钥添加**: 支持通过正则表达式 `gemini_key` 批量添加密钥，并自动去重。
    ![添加密钥](files/image5.png)
*   **失败重试与自动禁用**: 自动处理 API 请求失败，进行重试 (`MAX_RETRIES`)，并在 Key 失效次数过多时自动禁用 (`MAX_FAILURES`)，定时检查恢复 (`CHECK_INTERVAL_HOURS`)。
*   **全面的 API 兼容**:
    *   **Embeddings 接口**: 完美适配 OpenAI 格式的 `embeddings` 接口。
    *   **画图接口**: 将 `imagen-3.0-generate-002` 模型接口改造为 OpenAI 画图接口格式。
*   **模型列表自动维护**: 自动获取并同步 Gemini 和 OpenAI 的最新模型列表，兼容 New API。
*   **代理支持**: 支持配置 HTTP/SOCKS5 代理 (`PROXIES`)，方便在特殊网络环境下使用。
*   **Docker 支持**: 提供 AMD 和 ARM 架构的 Docker 镜像，方便快速部署。
    *   镜像地址: `ghcr.io/snailyp/gemini-balance:latest`

---

## 🚀 快速开始

### 方式一：使用 Docker Compose (推荐)

这是最推荐的部署方式，可以一键启动应用和数据库。

1.  **下载 `docker-compose.yml`**:
    从项目仓库获取 `docker-compose.yml` 文件。
2.  **准备 `.env` 文件**:
    从 `.env.example` 复制一份并重命名为 `.env`，然后根据需求修改配置。特别注意，`DATABASE_TYPE` 应设置为 `mysql`，并填写 `MYSQL_*` 相关配置。
3.  **启动服务**:
    在 `docker-compose.yml` 和 `.env` 文件所在的目录下，运行以下命令：
    ```bash
    docker-compose up -d
    ```
    该命令会以后台模式启动 `gemini-balance` 应用和 `mysql` 数据库。

### 方式二：使用 Docker 命令

1.  **拉取镜像**:
    ```bash
    docker pull ghcr.io/snailyp/gemini-balance:latest
    ```
2.  **准备 `.env` 文件**:
    从 `.env.example` 复制一份并重命名为 `.env`，然后根据需求修改配置。
3.  **运行容器**:
    ```bash
    docker run -d -p 8000:8000 --name gemini-balance \
    -v ./data:/app/data \
    --env-file .env \
    ghcr.io/snailyp/gemini-balance:latest
    ```
    *   `-d`: 后台运行。
    *   `-p 8000:8000`: 将容器的 8000 端口映射到主机。
    *   `-v ./data:/app/data`: 挂载数据卷以持久化 SQLite 数据和日志。
    *   `--env-file .env`: 加载环境变量配置文件。

### 方式三：本地运行 (适用于开发)

1.  **克隆仓库并安装依赖**:
    ```bash
    git clone https://github.com/snailyp/gemini-balance.git
    cd gemini-balance
    pip install -r requirements.txt
    ```
2.  **配置环境变量**:
    从 `.env.example` 复制一份并重命名为 `.env`，然后根据需求修改配置。
3.  **启动应用**:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    应用启动后，访问 `http://localhost:8000`。

---

## ⚙️ API 端点

### Gemini API 格式 (`/gemini/v1beta`)

此端点将请求直接转发到官方 Gemini API 格式的端点，不包含高级功能。

*   `GET /models`: 列出可用的 Gemini 模型。
*   `POST /models/{model_name}:generateContent`: 生成内容。
*   `POST /models/{model_name}:streamGenerateContent`: 流式生成内容。

### OpenAI API 格式

#### 兼容 huggingface (HF) 格式

如果您需要使用高级功能（例如假流式输出），请使用此端点。

*   `GET /hf/v1/models`: 列出模型。
*   `POST /hf/v1/chat/completions`: 聊天补全。
*   `POST /hf/v1/embeddings`: 创建文本嵌入。
*   `POST /hf/v1/images/generations`: 生成图像。

#### 标准 OpenAI 格式

此端点直接转发至官方的 OpenAI 兼容 API 格式端点，不包含高级功能。

*   `GET /openai/v1/models`: 列出模型。
*   `POST /openai/v1/chat/completions`: 聊天补全 (推荐，速度更快，防截断)。
*   `POST /openai/v1/embeddings`: 创建文本嵌入。
*   `POST /openai/v1/images/generations`: 生成图像。

---

<details>
<summary>📋 查看完整配置项列表</summary>

| 配置项 | 说明 | 默认值 |
| :--- | :--- | :--- |
| **数据库配置** | | |
| `DATABASE_TYPE` | 数据库类型: `mysql` 或 `sqlite` | `mysql` |
| `SQLITE_DATABASE` | 当使用 `sqlite` 时必填，SQLite 数据库文件路径 | `default_db` |
| `MYSQL_HOST` | 当使用 `mysql` 时必填，MySQL 数据库主机地址 | `localhost` |
| `MYSQL_SOCKET` | 可选，MySQL 数据库 socket 地址 | `/var/run/mysqld/mysqld.sock` |
| `MYSQL_PORT` | 当使用 `mysql` 时必填，MySQL 数据库端口 | `3306` |
| `MYSQL_USER` | 当使用 `mysql` 时必填，MySQL 数据库用户名 | `your_db_user` |
| `MYSQL_PASSWORD` | 当使用 `mysql` 时必填，MySQL 数据库密码 | `your_db_password` |
| `MYSQL_DATABASE` | 当使用 `mysql` 时必填，MySQL 数据库名称 | `defaultdb` |
| **API 相关配置** | | |
| `API_KEYS` | **必填**, Gemini API 密钥列表，用于负载均衡 | `[]` |
| `ALLOWED_TOKENS` | **必填**, 允许访问的 Token 列表 | `[]` |
| `AUTH_TOKEN` | 超级管理员 Token，不填则使用 `ALLOWED_TOKENS` 的第一个 | `sk-123456` |
| `TEST_MODEL` | 用于测试密钥可用性的模型 | `gemini-1.5-flash` |
| `IMAGE_MODELS` | 支持绘图功能的模型列表 | `["gemini-2.0-flash-exp"]` |
| `SEARCH_MODELS` | 支持搜索功能的模型列表 | `["gemini-2.0-flash-exp"]` |
| `FILTERED_MODELS` | 被禁用的模型列表 | `[]` |
| `TOOLS_CODE_EXECUTION_ENABLED` | 是否启用代码执行工具 | `false` |
| `SHOW_SEARCH_LINK` | 是否在响应中显示搜索结果链接 | `true` |
| `SHOW_THINKING_PROCESS` | 是否显示模型思考过程 | `true` |
| `THINKING_MODELS` | 支持思考功能的模型列表 | `[]` |
| `THINKING_BUDGET_MAP` | 思考功能预算映射 (模型名:预算值) | `{}` |
| `URL_NORMALIZATION_ENABLED` | 是否启用智能路由映射功能 | `false` |
| `URL_CONTEXT_ENABLED` | 是否启用URL上下文理解功能 | `false` |
| `URL_CONTEXT_MODELS` | 支持URL上下文理解功能的模型列表 | `[]` |
| `BASE_URL` | Gemini API 基础 URL | `https://generativelanguage.googleapis.com/v1beta` |
| `MAX_FAILURES` | 单个 Key 允许的最大失败次数 | `3` |
| `MAX_RETRIES` | API 请求失败时的最大重试次数 | `3` |
| `CHECK_INTERVAL_HOURS` | 禁用 Key 恢复检查间隔 (小时) | `1` |
| `TIMEZONE` | 应用程序使用的时区 | `Asia/Shanghai` |
| `TIME_OUT` | 请求超时时间 (秒) | `300` |
| `PROXIES` | 代理服务器列表 (例如 `http://user:pass@host:port`) | `[]` |
| **日志与安全** | | |
| `LOG_LEVEL` | 日志级别: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `AUTO_DELETE_ERROR_LOGS_ENABLED` | 是否自动删除错误日志 | `true` |
| `AUTO_DELETE_ERROR_LOGS_DAYS` | 错误日志保留天数 | `7` |
| `AUTO_DELETE_REQUEST_LOGS_ENABLED`| 是否自动删除请求日志 | `false` |
| `AUTO_DELETE_REQUEST_LOGS_DAYS` | 请求日志保留天数 | `30` |
| `SAFETY_SETTINGS` | 内容安全阈值 (JSON 字符串) | `[{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"}, ...]` |
| **TTS 相关** | | |
| `TTS_MODEL` | TTS 模型名称 | `gemini-2.5-flash-preview-tts` |
| `TTS_VOICE_NAME` | TTS 语音名称 | `Zephyr` |
| `TTS_SPEED` | TTS 语速 | `normal` |
| **图像生成相关** | | |
| `PAID_KEY` | 付费版API Key，用于图片生成等高级功能 | `your-paid-api-key` |
| `CREATE_IMAGE_MODEL` | 图片生成模型 | `imagen-3.0-generate-002` |
| `UPLOAD_PROVIDER` | 图片上传提供商: `smms`, `picgo`, `cloudflare_imgbed` | `smms` |
| `SMMS_SECRET_TOKEN` | SM.MS图床的API Token | `your-smms-token` |
| `PICGO_API_KEY` | [PicoGo](https://www.picgo.net/)图床的API Key | `your-picogo-apikey` |
| `CLOUDFLARE_IMGBED_URL` | [CloudFlare](https://github.com/MarSeventh/CloudFlare-ImgBed) 图床上传地址 | `https://xxxxxxx.pages.dev/upload` |
| `CLOUDFLARE_IMGBED_AUTH_CODE`| CloudFlare图床的鉴权key | `your-cloudflare-imgber-auth-code` |
| `CLOUDFLARE_IMGBED_UPLOAD_FOLDER`| CloudFlare图床的上传文件夹路径 | `""` |
| **流式优化器相关** | | |
| `STREAM_OPTIMIZER_ENABLED` | 是否启用流式输出优化 | `false` |
| `STREAM_MIN_DELAY` | 流式输出最小延迟 | `0.016` |
| `STREAM_MAX_DELAY` | 流式输出最大延迟 | `0.024` |
| `STREAM_SHORT_TEXT_THRESHOLD`| 短文本阈值 | `10` |
| `STREAM_LONG_TEXT_THRESHOLD` | 长文本阈值 | `50` |
| `STREAM_CHUNK_SIZE` | 流式输出块大小 | `5` |
| **伪流式 (Fake Stream) 相关** | | |
| `FAKE_STREAM_ENABLED` | 是否启用伪流式传输 | `false` |
| `FAKE_STREAM_EMPTY_DATA_INTERVAL_SECONDS` | 伪流式传输时发送心跳空数据的间隔秒数 | `5` |

</details>

---

## 🤝 贡献

欢迎通过提交 Pull Request 或 Issue 来为项目做出贡献。

[![Contributors](https://contrib.rocks/image?repo=snailyp/gemini-balance)](https://github.com/snailyp/gemini-balance/graphs/contributors)

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=snailyp/gemini-balance&type=Date)](https://star-history.com/#snailyp/gemini-balance&Date)

## 🎉 特别鸣谢

*   [PicGo](https://www.picgo.net/)
*   [SM.MS](https://smms.app/)
*   [CloudFlare-ImgBed](https://github.com/MarSeventh/CloudFlare-ImgBed)

## 💖 友情项目

*   **[OneLine](https://github.com/chengtx809/OneLine)** by [chengtx809](https://github.com/chengtx809) - AI 驱动的热点事件时间轴生成工具。

## 🎁 项目支持

如果你觉得这个项目对你有帮助，可以考虑通过 [爱发电](https://afdian.com/a/snaily) 支持我。

## 许可证

本项目采用 [CC BY-NC 4.0](LICENSE)（署名-非商业性使用）协议。


## 赞助商

特别感谢 [DigitalOcean](https://m.do.co/c/b249dd7f3b4c) 为本项目提供稳定可靠的云基础设施支持。

<a href="https://m.do.co/c/b249dd7f3b4c">
  <img src="files/dataocean.svg" alt="DigitalOcean Logo" width="200"/>
</a>

本项目的 CDN 加速和安全防护由 [Tencent EdgeOne](https://edgeone.ai/?from=github) 赞助。

<a href="https://edgeone.ai/?from=github">
  <img src="https://edgeone.ai/media/34fe3a45-492d-4ea4-ae5d-ea1087ca7b4b.png" alt="EdgeOne Logo" width="200"/>
</a>
