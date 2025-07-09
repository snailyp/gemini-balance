# Gemini Balance - Gemini API 代理和负载均衡器

<p align="center">
  <a href="https://trendshift.io/repositories/13692" target="_blank">
    <img src="https://trendshift.io/api/badge/repositories/13692" alt="snailyp%2Fgemini-balance | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/>
  </a>
</p>

> ⚠️ 本项目采用 CC BY-NC 4.0（署名-非商业性使用）协议，禁止任何形式的商业倒卖服务，详见 LICENSE 文件。

> 本人从未在各个平台售卖服务，如有遇到售卖此服务者，那一定是倒卖狗，大家切记不要上当受骗。

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Uvicorn](https://img.shields.io/badge/Uvicorn-running-purple.svg)](https://www.uvicorn.org/)
[![Telegram Group](https://img.shields.io/badge/Telegram-Group-blue.svg?logo=telegram)](https://t.me/+soaHax5lyI0wZDVl)
> 交流群：https://t.me/+soaHax5lyI0wZDVl

## 项目简介

Gemini Balance 是一个基于 Python FastAPI 构建的应用程序，旨在提供 Google Gemini API 的代理和负载均衡功能。它允许您管理多个 Gemini API Key，并通过简单的配置实现 Key 的轮询、认证、模型过滤和状态监控。此外，项目还集成了图像生成和多种图床上传功能，并支持 OpenAI API 格式的代理。

**项目结构:**

```plaintext
app/
├── config/       # 配置管理
├── core/         # 核心应用逻辑 (FastAPI 实例创建, 中间件等)
├── database/     # 数据库模型和连接
├── domain/       # 业务领域对象 (可选)
├── exception/    # 自定义异常
├── handler/      # 请求处理器 (可选, 或在 router 中处理)
├── log/          # 日志配置
├── main.py       # 应用入口
├── middleware/   # FastAPI 中间件
├── router/       # API 路由 (Gemini, OpenAI, 状态页等)
├── scheduler/    # 定时任务 (如 Key 状态检查)
├── service/      # 业务逻辑服务 (聊天, Key 管理, 统计等)
├── static/       # 静态文件 (CSS, JS)
├── templates/    # HTML 模板 (如 Key 状态页)
├── utils/        # 工具函数
```

## ✨ 功能亮点

* **多 Key 负载均衡**: 支持配置多个 Gemini API Key (`API_KEYS`)，自动按顺序轮询使用，提高可用性和并发能力。
* **可视化配置即时生效**: 通过管理后台修改配置后，无需重启服务即可生效，切记要点击保存才会生效。
![配置面板](files/image4.png)
* **双协议API 兼容**: 同时支持 Gemini 和 OpenAI 格式的 CHAT API 请求转发。

    ```palintext
    openai baseurl `http://localhost:8000(/hf)/v1`
    gemini baseurl `http://localhost:8000(/gemini)/v1beta`
    ```

* **支持图文对话和修改图片**: `IMAGE_MODELS`配置哪个模型可以图文对话和修图的功能，实际调用的时候，用 `配置模型-image`这个模型名对话使用该功能。
![对话生图](files/image6.png)
![修改图片](files/image7.png)
* **支持联网搜索**: 支持联网搜索，`SEARCH_MODELS`配置哪些模型可以联网搜索，实际调用的时候，用 `配置模型-search`这个模型名对话使用该功能
![联网搜索](files/image8.png)
* **Key 状态监控**: 提供 `/keys_status` 页面（需要认证），实时查看各 Key 的状态和使用情况。
![监控面板](files/image.png)
* **详细的日志记录**: 提供详细的错误日志，方便排查。
![调用详情](files/image1.png)
![日志列表](files/image2.png)
![日志详情](files/image3.png)
* **支持自定义gemini代理**: 支持自定义gemini代理，比如自行在deno或者cloudflare上搭建gemini代理
* **openai画图接口兼容**: 将`imagen-3.0-generate-002`模型接口改造成openai画图接口，支持客户端调用。
* **灵活的添加密钥方式**: 灵活的添加密钥方式，采用正则匹配`gemini_key`,密钥去重
![添加密钥](files/image5.png)
* **兼容openai格式embeddings接口**：完美适配openai格式的`embeddings`接口，可用于本地文档向量化。
* **流式响应优化**: 可选的流式输出优化器 (`STREAM_OPTIMIZER_ENABLED`)，改善长文本流式响应的体验。
* **失败重试与 Key 管理**: 自动处理 API 请求失败，进行重试 (`MAX_RETRIES`)，并在 Key 失效次数过多时自动禁用 (`MAX_FAILURES`)，定时检查恢复 (`CHECK_INTERVAL_HOURS`)。
* **Docker 支持**: 支持AMD，ARM架构的docker部署，也可自行构建docker镜像。
    >镜像地址: docker pull ghcr.io/snailyp/gemini-balance:latest
* **模型列表自动维护**: 支持openai和gemini模型列表获取，与newapi自动获取模型列表完美兼容，无需手动填写。
* **支持移除不使用的模型**: 默认提供的模型太多，很多用不上，可以通过`FILTERED_MODELS`过滤掉。
* **代理支持**: 支持配置 HTTP/SOCKS5 代理服务器 (`PROXIES`)，用于访问 Gemini API，方便在特殊网络环境下使用。支持批量添加代理。

## 🚀 快速开始

### 自行构建 Docker (推荐)

#### a) dockerfile构建

1. **构建镜像**:

    ```bash
    docker build -t gemini-balance .
    ```

2. **运行容器**:

    ```bash
    docker run -d -p 8000:8000 --env-file .env gemini-balance
    ```

    * `-d`: 后台运行。
    * `-p 8000:8000`: 将容器的 8000 端口映射到主机的 8000 端口。
    * `--env-file .env`: 使用 `.env` 文件设置环境变量。

    > 注意：如果使用 SQLite 数据库，需要挂载数据卷以持久化数据：
    > ```bash
    > docker run -d -p 8000:8000 --env-file .env -v /path/to/data:/app/data gemini-balance
    > ```
    > 其中 `/path/to/data` 是主机上的数据存储路径，`/app/data` 是容器内的数据目录。

#### b) 用现有的docker镜像部署

1. **拉取镜像**:

   ```bash
   docker pull ghcr.io/snailyp/gemini-balance:latest
   ```

2. **运行容器**:

   ```bash
   docker run -d -p 8000:8000 --env-file .env ghcr.io/snailyp/gemini-balance:latest
   ```

   * `-d`: 后台运行。
   * `-p 8000:8000`: 将容器的 8000 端口映射到主机的 8000 端口 (根据需要调整)。
   * `--env-file .env`: 使用 `.env` 文件设置环境变量 (确保 `.env` 文件存在于执行命令的目录)。

    > 注意：如果使用 SQLite 数据库，需要挂载数据卷以持久化数据：
    > ```bash
    > docker run -d -p 8000:8000 --env-file .env -v /path/to/data:/app/data ghcr.io/snailyp/gemini-balance:latest
    > ```
    > 其中 `/path/to/data` 是主机上的数据存储路径，`/app/data` 是容器内的数据目录。

### 本地运行 (适用于开发和测试)

如果您想在本地直接运行源代码进行开发或测试，请按照以下步骤操作：

1. **确保已完成准备工作**:
    * 克隆仓库到本地。
    * 安装 Python 3.9 或更高版本。
    * 在项目根目录下创建并配置好 `.env` 文件 (参考前面的"配置环境变量"部分)。
    * 安装项目依赖：

        ```bash
        pip install -r requirements.txt
        ```

2. **启动应用**:
    在项目根目录下运行以下命令：

    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

    * `app.main:app`: 指定 FastAPI 应用实例的位置 (`app` 模块中的 `main.py` 文件里的 `app` 对象)。
    * `--host 0.0.0.0`: 使应用可以从本地网络中的任何 IP 地址访问。
    * `--port 8000`: 指定应用监听的端口号 (您可以根据需要修改)。
    * `--reload`: 启用自动重载功能。当您修改代码时，服务会自动重启，非常适合开发环境 (生产环境请移除此选项)。

3. **访问应用**:
    应用启动后，您可以通过浏览器或 API 工具访问 `http://localhost:8000` (或您指定的主机和端口)。

### 完整配置项列表

| 配置项                       | 说明                                                     | 默认值                             |
| :--------------------------- | :------------------------------------------------------- | :---------------------------------------------------- |
| **数据库配置**               |                                                          |                                                       |
| `DATABASE_TYPE`              | 可选，数据库类型，支持 `mysql` 或 `sqlite`               | `mysql`                                              |
| `SQLITE_DATABASE`            | 可选，当使用 `sqlite` 时必填，SQLite 数据库文件路径 | `default_db`                                         |
| `MYSQL_HOST`                 | 当使用 `mysql` 时必填，MySQL 数据库主机地址    | `localhost`                                          |
| `MYSQL_SOCKET`               | 可选，MySQL 数据库 socket 地址                          | `/var/run/mysqld/mysqld.sock`                        |
| `MYSQL_PORT`                 | 当使用 `mysql` 时必填，MySQL 数据库端口        | `3306`                                               |
| `MYSQL_USER`                 | 当使用 `mysql` 时必填，MySQL 数据库用户名      | `your_db_user`                                       |
| `MYSQL_PASSWORD`             | 当使用 `mysql` 时必填，MySQL 数据库密码        | `your_db_password`                                   |
| `MYSQL_DATABASE`             | 当使用 `mysql` 时必填，MySQL 数据库名称        | `defaultdb`                                          |
| **API 相关配置**             |                                                          |                                                       |
| `API_KEYS`                   | 必填，Gemini API 密钥列表，用于负载均衡                        | `["your-gemini-api-key-1", "your-gemini-api-key-2"]`  |
| `ALLOWED_TOKENS`             | 必填，允许访问的 Token 列表                                    | `["your-access-token-1", "your-access-token-2"]`      |
| `AUTH_TOKEN`                 | 可选，超级管理员token，具有所有权限，不填默认使用 ALLOWED_TOKENS 的第一个 | `sk-123456`                                                  |
| `TEST_MODEL`                 | 可选，用于测试密钥是否可用的模型名                             | `gemini-1.5-flash`                                    |
| `IMAGE_MODELS`               | 可选，支持绘图功能的模型列表                                   | `["gemini-2.0-flash-exp"]`                            |
| `SEARCH_MODELS`              | 可选，支持搜索功能的模型列表                                   | `["gemini-2.0-flash-exp"]`                            |
| `FILTERED_MODELS`            | 可选，被禁用的模型列表                                         | `["gemini-1.0-pro-vision-latest", ...]`               |
| `TOOLS_CODE_EXECUTION_ENABLED` | 可选，是否启用代码执行工具                                     | `false`                                               |
| `SHOW_SEARCH_LINK`           | 可选，是否在响应中显示搜索结果链接                             | `true`                                                |
| `SHOW_THINKING_PROCESS`      | 可选，是否显示模型思考过程                                     | `true`                                                |
| `THINKING_MODELS`            | 可选，支持思考功能的模型列表                                   | `[]`                                                  |
| `THINKING_BUDGET_MAP`        | 可选，思考功能预算映射 (模型名:预算值)                         | `{}`                                                  |
| `URL_NORMALIZATION_ENABLED`  | 可选，是否启用智能路由映射功能                                 | `false`                                               |
| `BASE_URL`                   | 可选，Gemini API 基础 URL，默认无需修改                        | `https://generativelanguage.googleapis.com/v1beta`    |
| `MAX_FAILURES`               | 可选，允许单个key失败的次数                                    | `3`                                                   |
| `MAX_RETRIES`                | 可选，API 请求失败时的最大重试次数                             | `3`                                                   |
| `CHECK_INTERVAL_HOURS`       | 可选，检查禁用 Key 是否恢复的时间间隔 (小时)                   | `1`                                                   |
| `TIMEZONE`                   | 可选，应用程序使用的时区                                       | `Asia/Shanghai`                                       |
| `TIME_OUT`                   | 可选，请求超时时间 (秒)                                        | `300`                                                 |
| `PROXIES`                    | 可选，代理服务器列表 (例如 `http://user:pass@host:port`, `socks5://host:port`) | `[]`                                                  |
| `LOG_LEVEL`                  | 可选，日志级别，例如 DEBUG, INFO, WARNING, ERROR, CRITICAL     | `INFO`                                                |
| `AUTO_DELETE_ERROR_LOGS_ENABLED` | 可选，是否开启自动删除错误日志                                 | `true`                                                |
| `AUTO_DELETE_ERROR_LOGS_DAYS`  | 可选，自动删除多少天前的错误日志 (例如 1, 7, 30)             | `7`                                                   |
| `AUTO_DELETE_REQUEST_LOGS_ENABLED`| 可选，是否开启自动删除请求日志                               | `false`                                               |
| `AUTO_DELETE_REQUEST_LOGS_DAYS` | 可选，自动删除多少天前的请求日志 (例如 1, 7, 30)           | `30`                                                  |
| `SAFETY_SETTINGS`            | 可选，安全设置 (JSON 字符串格式)，用于配置内容安全阈值。示例值可能需要根据实际模型支持情况调整。 | `[{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"}, {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"}, {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"}, {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"}, {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"}]` |
| **TTS 相关**                 |                                                          |                                                       |
| `TTS_MODEL`                  | 可选，TTS 模型名称                                           | `gemini-2.5-flash-preview-tts`                        |
| `TTS_VOICE_NAME`             | 可选，TTS 语音名称                                           | `Zephyr`                                              |
| `TTS_SPEED`                  | 可选，TTS 语速                                               | `normal`                                              |
| **图像生成相关**             |                                                          |                                                       |
| `PAID_KEY`                   | 可选，付费版API Key，用于图片生成等高级功能                    | `your-paid-api-key`                                   |
| `CREATE_IMAGE_MODEL`         | 可选，图片生成模型                                             | `imagen-3.0-generate-002`                             |
| `UPLOAD_PROVIDER`            | 可选，图片上传提供商: `smms`, `picgo`, `cloudflare_imgbed`     | `smms`                                                |
| `SMMS_SECRET_TOKEN`          | 可选，SM.MS图床的API Token                                     | `your-smms-token`                                     |
| `PICGO_API_KEY`              | 可选，[PicoGo](https://www.picgo.net/)图床的API Key                                      | `your-picogo-apikey`                                  |
| `CLOUDFLARE_IMGBED_URL`      | 可选，[CloudFlare](https://github.com/MarSeventh/CloudFlare-ImgBed) 图床上传地址                                  | `https://xxxxxxx.pages.dev/upload`                    |
| `CLOUDFLARE_IMGBED_AUTH_CODE`| 可选，CloudFlare图床的鉴权key                                  | `your-cloudflare-imgber-auth-code`                    |
| `CLOUDFLARE_IMGBED_UPLOAD_FOLDER`| 可选，CloudFlare图床的上传文件夹路径                        | `""`                                                  |
| **流式优化器相关**           |                                                          |                                                       |
| `STREAM_OPTIMIZER_ENABLED`   | 可选，是否启用流式输出优化                                     | `false`                                               |
| `STREAM_MIN_DELAY`           | 可选，流式输出最小延迟                                         | `0.016`                                               |
| `STREAM_MAX_DELAY`           | 可选，流式输出最大延迟                                         | `0.024`                                               |
| `STREAM_SHORT_TEXT_THRESHOLD`| 可选，短文本阈值                                               | `10`                                                  |
| `STREAM_LONG_TEXT_THRESHOLD` | 可选，长文本阈值                                               | `50`                                                  |
| `STREAM_CHUNK_SIZE`          | 可选，流式输出块大小                                           | `5`                                                   |
| **伪流式 (Fake Stream) 相关** |                                                          |                                                       |
| `FAKE_STREAM_ENABLED`        | 可选，是否启用伪流式传输，用于不支持流式的模型或场景           | `false`                                               |
| `FAKE_STREAM_EMPTY_DATA_INTERVAL_SECONDS` | 可选，伪流式传输时发送心跳空数据的间隔秒数                   | `5`                                                   |

## ⚙️ API 端点

以下是服务提供的主要 API 端点：

### Gemini API 相关 (`(/gemini)/v1beta`)

* `GET /models`: 列出可用的 Gemini 模型。
* `POST /models/{model_name}:generateContent`: 使用指定的 Gemini 模型生成内容。
* `POST /models/{model_name}:streamGenerateContent`: 使用指定的 Gemini 模型流式生成内容。

### OpenAI API 相关

* `GET (/hf)/v1/models`: 列出可用的模型 (底层用的gemini格式)。
* `POST (/hf)/v1/chat/completions`: 进行聊天补全 (底层用的gemini格式, 支持流式传输)。
* `POST (/hf)/v1/embeddings`: 创建文本嵌入 (底层用的gemini格式)。
* `POST (/hf)/v1/images/generations`: 生成图像 (底层用的gemini格式)。
* `GET /openai/v1/models`: 列出可用的模型 (底层用的openai格式)。
* `POST /openai/v1/chat/completions`: 进行聊天补全 (底层用的openai格式, 支持流式传输, 可防止截断，速度也快)。
* `POST /openai/v1/embeddings`: 创建文本嵌入 (底层用的openai格式)。
* `POST /openai/v1/images/generations`: 生成图像 (底层用的openai格式)。

## 🤝 贡献

欢迎提交 Pull Request 或 Issue。

## 🎉 特别鸣谢

特别鸣谢以下项目和平台为本项目提供图床服务:

* [PicGo](https://www.picgo.net/)
* [SM.MS](https://smms.app/)
* [CloudFlare-ImgBed](https://github.com/MarSeventh/CloudFlare-ImgBed) 开源项目

## 🙏 感谢贡献者

感谢所有为本项目做出贡献的开发者！

[![Contributors](https://contrib.rocks/image?repo=snailyp/gemini-balance)](https://github.com/snailyp/gemini-balance/graphs/contributors)

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=snailyp/gemini-balance&type=Date)](https://star-history.com/#snailyp/gemini-balance&Date)

## 💖 友情项目

* **[OneLine](https://github.com/chengtx809/OneLine)** by [chengtx809](https://github.com/chengtx809) - OneLine一线：AI驱动的热点事件时间轴生成工具

## 🎁 项目支持

如果你觉得这个项目对你有帮助，可以考虑通过 [爱发电](https://afdian.com/a/snaily) 支持我。

## 许可证

本项目采用 CC BY-NC 4.0（署名-非商业性使用）协议，禁止任何形式的商业倒卖服务，详见 LICENSE 文件。
