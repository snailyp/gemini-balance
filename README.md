[Read this document in Chinese](README_ZH.md)

# Gemini Balance - Gemini API Proxy and Load Balancer

<p align="center">
  <a href="https://trendshift.io/repositories/13692" target="_blank">
    <img src="https://trendshift.io/api/badge/repositories/13692" alt="snailyp%2Fgemini-balance | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/>
  </a>
</p>

> ⚠️ This project is licensed under the CC BY-NC 4.0 (Attribution-NonCommercial) license. Any form of commercial resale service is prohibited. See the LICENSE file for details.

> I have never sold this service on any platform. If you encounter someone selling this service, they are definitely a reseller. Please be careful not to be deceived.

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Uvicorn](https://img.shields.io/badge/Uvicorn-running-purple.svg)](https://www.uvicorn.org/)
[![Telegram Group](https://img.shields.io/badge/Telegram-Group-blue.svg?logo=telegram)](https://t.me/+soaHax5lyI0wZDVl)

> Telegram Group: <https://t.me/+soaHax5lyI0wZDVl>

## Project Introduction

Gemini Balance is an application built with Python FastAPI, designed to provide proxy and load balancing functions for the Google Gemini API. It allows you to manage multiple Gemini API Keys and implement key rotation, authentication, model filtering, and status monitoring through simple configuration. Additionally, the project integrates image generation and multiple image hosting upload functions, and supports proxying in the OpenAI API format.

**Project Structure:**

```plaintext
app/
├── config/       # Configuration management
├── core/         # Core application logic (FastAPI instance creation, middleware, etc.)
├── database/     # Database models and connections
├── domain/       # Business domain objects (optional)
├── exception/    # Custom exceptions
├── handler/      # Request handlers (optional, or handled in router)
├── log/          # Logging configuration
├── main.py       # Application entry point
├── middleware/   # FastAPI middleware
├── router/       # API routes (Gemini, OpenAI, status page, etc.)
├── scheduler/    # Scheduled tasks (e.g., Key status check)
├── service/      # Business logic services (chat, Key management, statistics, etc.)
├── static/       # Static files (CSS, JS)
├── templates/    # HTML templates (e.g., Key status page)
├── utils/        # Utility functions
```

## ✨ Feature Highlights

* **Multi-Key Load Balancing**: Supports configuring multiple Gemini API Keys (`API_KEYS`) for automatic sequential polling, improving availability and concurrency.
* **Visual Configuration Takes Effect Immediately**: Configurations modified through the admin backend take effect without restarting the service. Remember to click save for changes to apply.
    ![Configuration Panel](files/image4.png)
* **Dual Protocol API Compatibility**: Supports forwarding CHAT API requests in both Gemini and OpenAI formats.

    ```plaintext
    openai baseurl `http://localhost:8000(/hf)/v1`
    gemini baseurl `http://localhost:8000(/gemini)/v1beta`
    ```

* **Supports Image-Text Chat and Image Modification**: `IMAGE_MODELS` configures which models can perform image-text chat and image editing. When actually calling, use the `configured_model-image` model name to use this feature.
    ![Chat with Image Generation](files/image6.png)
    ![Modify Image](files/image7.png)
* **Supports Web Search**: Supports web search. `SEARCH_MODELS` configures which models can perform web searches. When actually calling, use the `configured_model-search` model name to use this feature.
    ![Web Search](files/image8.png)
* **Key Status Monitoring**: Provides a `/keys_status` page (requires authentication) to view the status and usage of each Key in real-time.
    ![Monitoring Panel](files/image.png)
* **Detailed Logging**: Provides detailed error logs for easy troubleshooting.
    ![Call Details](files/image1.png)
    ![Log List](files/image2.png)
    ![Log Details](files/image3.png)
* **Support for Custom Gemini Proxy**: Supports custom Gemini proxies, such as those built on Deno or Cloudflare.
* **OpenAI Image Generation API Compatibility**: Adapts the `imagen-3.0-generate-002` model interface to be compatible with the OpenAI image generation API, supporting client calls.
* **Flexible Key Addition**: Flexible way to add keys using regex matching for `gemini_key`, with key deduplication.
    ![Add Key](files/image5.png)
* **OpenAI Format Embeddings API Compatibility**: Perfectly adapts to the OpenAI format `embeddings` interface, usable for local document vectorization.
* **Streamlined Response Optimization**: Optional stream output optimizer (`STREAM_OPTIMIZER_ENABLED`) to improve the experience of long-text stream responses.
* **Failure Retry and Key Management**: Automatically handles API request failures, retries (`MAX_RETRIES`), automatically disables Keys after too many failures (`MAX_FAILURES`), and periodically checks for recovery (`CHECK_INTERVAL_HOURS`).
* **Docker Support**: Supports AMD and ARM architecture Docker deployments. You can also build your own Docker image.
    > Image address: docker pull ghcr.io/snailyp/gemini-balance:latest
* **Automatic Model List Maintenance**: Supports fetching OpenAI and Gemini model lists, perfectly compatible with NewAPI's automatic model list fetching, no manual entry required.
* **Support for Removing Unused Models**: Too many default models are provided, many of which are not used. You can filter them out using `FILTERED_MODELS`.
* **Proxy Support**: Supports configuring HTTP/SOCKS5 proxy servers (`PROXIES`) for accessing the Gemini API, convenient for use in special network environments. Supports batch adding proxies.

## 🚀 Quick Start

### Build Docker Yourself (Recommended)

#### a) Build with Dockerfile

1. **Build Image**:

    ```bash
    docker build -t gemini-balance .
    ```

2. **Run Container**:

    ```bash
    docker run -d -p 8000:8000 --env-file .env gemini-balance
    ```

    * `-d`: Run in detached mode.
    * `-p 8000:8000`: Map port 8000 of the container to port 8000 of the host.
    * `--env-file .env`: Use the `.env` file to set environment variables.

    > Note: If using an SQLite database, you need to mount a data volume to persist
>
    > ```bash
    > docker run -d -p 8000:8000 --env-file .env -v /path/to/data:/app/data gemini-balance
    > ```
>
    > Where `/path/to/data` is the data storage path on the host, and `/app/data` is the data directory inside the container.

#### b) Deploy with an Existing Docker Image

1. **Pull Image**:

    ```bash
    docker pull ghcr.io/snailyp/gemini-balance:latest
    ```

2. **Run Container**:

    ```bash
    docker run -d -p 8000:8000 --env-file .env ghcr.io/snailyp/gemini-balance:latest
    ```

    * `-d`: Run in detached mode.
    * `-p 8000:8000`: Map port 8000 of the container to port 8000 of the host (adjust as needed).
    * `--env-file .env`: Use the `.env` file to set environment variables (ensure the `.env` file exists in the directory where the command is executed).

    > Note: If using an SQLite database, you need to mount a data volume to persist
>
    > ```bash
    > docker run -d -p 8000:8000 --env-file .env -v /path/to/data:/app/data ghcr.io/snailyp/gemini-balance:latest
    > ```
>
    > Where `/path/to/data` is the data storage path on the host, and `/app/data` is the data directory inside the container.

### Run Locally (Suitable for Development and Testing)

If you want to run the source code directly locally for development or testing, follow these steps:

1. **Ensure Prerequisites are Met**:
    * Clone the repository locally.
    * Install Python 3.9 or higher.
    * Create and configure the `.env` file in the project root directory (refer to the "Configure Environment Variables" section above).
    * Install project dependencies:

        ```bash
        pip install -r requirements.txt
        ```

2. **Start Application**:
    Run the following command in the project root directory:

    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

    * `app.main:app`: Specifies the location of the FastAPI application instance (the `app` object in the `main.py` file within the `app` module).
    * `--host 0.0.0.0`: Makes the application accessible from any IP address on the local network.
    * `--port 8000`: Specifies the port number the application listens on (you can change this as needed).
    * `--reload`: Enables automatic reloading. When you modify the code, the service will automatically restart, which is very suitable for development environments (remove this option in production environments).

3. **Access Application**:
    After the application starts, you can access `http://localhost:8000` (or the host and port you specified) through a browser or API tool.

### Complete Configuration List

| Configuration Item             | Description                                                                 | Default Value                                                                                                                                                                                                                            |
| :----------------------------- | :-------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Database Configuration**     |                                                                             |                                                                                                                                                                                                                                          |
| `DATABASE_TYPE`                | Optional, database type, supports `mysql` or `sqlite`                       | `mysql`                                                                                                                                                                                                                                  |
| `SQLITE_DATABASE`              | Optional, required when using `sqlite`, SQLite database file path           | `default_db`                                                                                                                                                                                                                             |
| `MYSQL_HOST`                   | Required when using `mysql`, MySQL database host address                    | `localhost`                                                                                                                                                                                                                              |
| `MYSQL_SOCKET`                 | Optional, MySQL database socket address                                     | `/var/run/mysqld/mysqld.sock`                                                                                                                                                                                                            |
| `MYSQL_PORT`                   | Required when using `mysql`, MySQL database port                            | `3306`                                                                                                                                                                                                                                   |
| `MYSQL_USER`                   | Required when using `mysql`, MySQL database username                        | `your_db_user`                                                                                                                                                                                                                           |
| `MYSQL_PASSWORD`               | Required when using `mysql`, MySQL database password                        | `your_db_password`                                                                                                                                                                                                                       |
| `MYSQL_DATABASE`               | Required when using `mysql`, MySQL database name                            | `defaultdb`                                                                                                                                                                                                                              |
| **API Related Configuration**  |                                                                             |                                                                                                                                                                                                                                          |
| `API_KEYS`                     | Required, list of Gemini API keys for load balancing                        | `["your-gemini-api-key-1", "your-gemini-api-key-2"]`                                                                                                                                                                                     |
| `ALLOWED_TOKENS`               | Required, list of tokens allowed to access                                  | `["your-access-token-1", "your-access-token-2"]`                                                                                                                                                                                         |
| `AUTH_TOKEN`                   | Optional, super admin token with all permissions, defaults to the first of `ALLOWED_TOKENS` if not set | `sk-123456`                                                                                                                                                                                                              |
| `TEST_MODEL`                   | Optional, model name used to test if a key is usable                        | `gemini-1.5-flash`                                                                                                                                                                                                                       |
| `IMAGE_MODELS`                 | Optional, list of models that support drawing functions                     | `["gemini-2.0-flash-exp"]`                                                                                                                                                                                                               |
| `SEARCH_MODELS`                | Optional, list of models that support search functions                      | `["gemini-2.0-flash-exp"]`                                                                                                                                                                                                               |
| `FILTERED_MODELS`              | Optional, list of disabled models                                           | `["gemini-1.0-pro-vision-latest", ...]`                                                                                                                                                                                                  |
| `TOOLS_CODE_EXECUTION_ENABLED` | Optional, whether to enable the code execution tool                         | `false`                                                                                                                                                                                                                                  |
| `SHOW_SEARCH_LINK`             | Optional, whether to display search result links in the response            | `true`                                                                                                                                                                                                                                   |
| `SHOW_THINKING_PROCESS`        | Optional, whether to display the model's thinking process                   | `true`                                                                                                                                                                                                                                   |
| `THINKING_MODELS`              | Optional, list of models that support thinking functions                    | `[]`                                                                                                                                                                                                                                     |
| `THINKING_BUDGET_MAP`          | Optional, thinking function budget mapping (model_name:budget_value)        | `{}`                                                                                                                                                                                                                                     |
| `URL_NORMALIZATION_ENABLED`    | Optional, whether to enable intelligent URL routing mapping                 | `false`                                                                                                                                                                                                                                  |
| `BASE_URL`                     | Optional, Gemini API base URL, no modification needed by default            | `https://generativelanguage.googleapis.com/v1beta`                                                                                                                                                                                       |
| `MAX_FAILURES`                 | Optional, number of times a single key is allowed to fail                   | `3`                                                                                                                                                                                                                                      |
| `MAX_RETRIES`                  | Optional, maximum number of retries for failed API requests                 | `3`                                                                                                                                                                                                                                      |
| `CHECK_INTERVAL_HOURS`         | Optional, time interval (hours) to check if a disabled Key has recovered    | `1`                                                                                                                                                                                                                                      |
| `TIMEZONE`                     | Optional, timezone used by the application                                  | `Asia/Shanghai`                                                                                                                                                                                                                          |
| `TIME_OUT`                     | Optional, request timeout (seconds)                                         | `300`                                                                                                                                                                                                                                    |
| `PROXIES`                      | Optional, list of proxy servers (e.g., `http://user:pass@host:port`, `socks5://host:port`) | `[]`                                                                                                                                                                                                                                     |
| `LOG_LEVEL`                    | Optional, log level, e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL          | `INFO`                                                                                                                                                                                                                                   |
| `AUTO_DELETE_ERROR_LOGS_ENABLED` | Optional, whether to enable automatic deletion of error logs              | `true`                                                                                                                                                                                                                                   |
| `AUTO_DELETE_ERROR_LOGS_DAYS`  | Optional, automatically delete error logs older than this many days (e.g., 1, 7, 30) | `7`                                                                                                                                                                                                                                      |
| `AUTO_DELETE_REQUEST_LOGS_ENABLED`| Optional, whether to enable automatic deletion of request logs             | `false`                                                                                                                                                                                                                                  |
| `AUTO_DELETE_REQUEST_LOGS_DAYS` | Optional, automatically delete request logs older than this many days (e.g., 1, 7, 30) | `30`                                                                                                                                                                                                                                     |
| `SAFETY_SETTINGS`              | Optional, safety settings (JSON string format), used to configure content safety thresholds. Example values may need adjustment based on actual model support. | `[{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"}, {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"}, {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"}, {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"}, {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"}]` |
| **TTS Related**                |                                                                             |                                                                                                                                                                                                                                          |
| `TTS_MODEL`                    | Optional, TTS model name                                                    | `gemini-2.5-flash-preview-tts`                                                                                                                                                                                                           |
| `TTS_VOICE_NAME`               | Optional, TTS voice name                                                    | `Zephyr`                                                                                                                                                                                                                                 |
| `TTS_SPEED`                    | Optional, TTS speed                                                         | `normal`                                                                                                                                                                                                                                 |
| **Image Generation Related**   |                                                                             |                                                                                                                                                                                                                                          |
| `PAID_KEY`                     | Optional, paid API Key for advanced features like image generation          | `your-paid-api-key`                                                                                                                                                                                                                        |
| `CREATE_IMAGE_MODEL`           | Optional, image generation model                                            | `imagen-3.0-generate-002`                                                                                                                                                                                                                  |
| `UPLOAD_PROVIDER`              | Optional, image upload provider: `smms`, `picgo`, `cloudflare_imgbed`       | `smms`                                                                                                                                                                                                                                   |
| `SMMS_SECRET_TOKEN`            | Optional, API Token for SM.MS image hosting                                 | `your-smms-token`                                                                                                                                                                                                                          |
| `PICGO_API_KEY`                | Optional, API Key for [PicoGo](https://www.picgo.net/) image hosting        | `your-picogo-apikey`                                                                                                                                                                                                                         |
| `CLOUDFLARE_IMGBED_URL`        | Optional, [CloudFlare](https://github.com/MarSeventh/CloudFlare-ImgBed) image hosting upload address | `https://xxxxxxx.pages.dev/upload`                                                                                                                                                                                           |
| `CLOUDFLARE_IMGBED_AUTH_CODE`  | Optional, authentication key for CloudFlare image hosting                   | `your-cloudflare-imgber-auth-code`                                                                                                                                                                                                           |
| `CLOUDFLARE_IMGBED_UPLOAD_FOLDER` | Optional, upload folder path for CloudFlare image hosting               | `""`                                                                                                                                                                                                                                          |
| **Stream Optimizer Related**   |                                                                             |                                                                                                                                                                                                                                          |
| `STREAM_OPTIMIZER_ENABLED`     | Optional, whether to enable stream output optimization                      | `false`                                                                                                                                                                                                                                  |
| `STREAM_MIN_DELAY`             | Optional, minimum delay for stream output                                   | `0.016`                                                                                                                                                                                                                                  |
| `STREAM_MAX_DELAY`             | Optional, maximum delay for stream output                                   | `0.024`                                                                                                                                                                                                                                  |
| `STREAM_SHORT_TEXT_THRESHOLD`  | Optional, short text threshold                                              | `10`                                                                                                                                                                                                                                     |
| `STREAM_LONG_TEXT_THRESHOLD`   | Optional, long text threshold                                               | `50`                                                                                                                                                                                                                                     |
| `STREAM_CHUNK_SIZE`            | Optional, stream output chunk size                                          | `5`                                                                                                                                                                                                                                      |
| **Fake Stream Related**        |                                                                             |                                                                                                                                                                                                                                          |
| `FAKE_STREAM_ENABLED`          | Optional, whether to enable fake streaming for models or scenarios that don't support streaming | `false`                                                                                                                                                                                                                                  |
| `FAKE_STREAM_EMPTY_DATA_INTERVAL_SECONDS` | Optional, interval in seconds for sending heartbeat empty data during fake streaming | `5`                                                                                                                                                                                                                                      |

## ⚙️ API Endpoints

The following are the main API endpoints provided by the service:

### Gemini API Related (`(/gemini)/v1beta`)

* `GET /models`: List available Gemini models.
* `POST /models/{model_name}:generateContent`: Generate content using the specified Gemini model.
* `POST /models/{model_name}:streamGenerateContent`: Stream content generation using the specified Gemini model.

### OpenAI API Related

* `GET (/hf)/v1/models`: List available models (uses Gemini format underneath).
* `POST (/hf)/v1/chat/completions`: Perform chat completion (uses Gemini format underneath, supports streaming).
* `POST (/hf)/v1/embeddings`: Create text embeddings (uses Gemini format underneath).
* `POST (/hf)/v1/images/generations`: Generate images (uses Gemini format underneath).
* `GET /openai/v1/models`: List available models (uses OpenAI format underneath).
* `POST /openai/v1/chat/completions`: Perform chat completion (uses OpenAI format underneath, supports streaming, can prevent truncation, and is faster).
* `POST /openai/v1/embeddings`: Create text embeddings (uses OpenAI format underneath).
* `POST /openai/v1/images/generations`: Generate images (uses OpenAI format underneath).

## 🤝 Contributing

Pull Requests or Issues are welcome.

## 🎉 Special Thanks

Special thanks to the following projects and platforms for providing image hosting services for this project:

* [PicGo](https://www.picgo.net/)
* [SM.MS](https://smms.app/)
* [CloudFlare-ImgBed](https://github.com/MarSeventh/CloudFlare-ImgBed) open source project

## 🙏 Thanks to Contributors

Thanks to all developers who contributed to this project!

[![Contributors](https://contrib.rocks/image?repo=snailyp/gemini-balance)](https://github.com/snailyp/gemini-balance/graphs/contributors)

## Thanks to Our Supporters

A special shout-out to DigitalOcean for providing the rock-solid and dependable cloud infrastructure that keeps this project humming!
[![DigitalOcean Logo](files/dataocean.svg)](https://m.do.co/c/b249dd7f3b4c)

CDN acceleration and security protection for this project are sponsored by Tencent EdgeOne.
[![EdgeOne Logo](https://edgeone.ai/media/34fe3a45-492d-4ea4-ae5d-ea1087ca7b4b.png)](https://edgeone.ai/?from=github)

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=snailyp/gemini-balance&type=Date)](https://star-history.com/#snailyp/gemini-balance&Date)

## 💖 Friendly Projects

* **[OneLine](https://github.com/chengtx809/OneLine)** by [chengtx809](https://github.com/chengtx809) - OneLine: AI-driven hot event timeline generation tool

## 🎁 Project Support

If you find this project helpful, consider supporting me via [Afdian](https://afdian.com/a/snaily).

## License

This project is licensed under the CC BY-NC 4.0 (Attribution-NonCommercial) license. Any form of commercial resale service is prohibited. See the LICENSE file for details.
