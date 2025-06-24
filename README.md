# Coze 批量推理和 WAV 拼接服务

这是一个用于 Coze 平台的批量文本转语音 (TTS) 推理和 WAV 音频文件拼接服务。它旨在处理大量文本输入，生成语音，并将生成的 WAV 文件进行拼接。

## 功能

-   **批量 TTS 推理**: 高效地将大量文本转换为语音。
-   **WAV 音频拼接**: 将多个生成的 WAV 音频文件拼接成一个。
-   **Coze 平台集成**: 作为 Coze 服务的后端，提供语音生成和处理能力。
-   支持通过 API 进行交互。
-   使用 Docker 进行容器化部署。

## 安装

### 前提条件

-   Docker 和 Docker Compose (如果使用 Docker 部署)
-   Python 3.8+ (如果直接运行 Python 应用)

### 使用 Docker 部署

1.  克隆仓库：
    ```bash
    git clone https://github.com/your-username/coze-tts-service.git
    cd coze-tts-service
    ```
2.  构建并运行 Docker 容器：
    ```bash
    docker-compose up --build
    ```
    服务将在 `http://localhost:5000` (或您配置的端口) 上运行。

### 直接运行 Python 应用

1.  克隆仓库：
    ```bash
    git clone https://github.com/your-username/coze-tts-service.git
    cd coze-tts-service
    ```
2.  创建并激活虚拟环境：
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
3.  安装依赖：
    ```bash
    pip install -r requirements.txt
    ```
4.  运行应用程序：
    ```bash
    python app.py
    ```
    服务将在 `http://localhost:5000` (或您配置的端口) 上运行。

## 使用

-   通过 API 调用服务，进行批量文本转语音推理和 WAV 拼接操作。
-   参考 `openapi.json` 文件了解详细的 API 端点和请求/响应格式。
-   生成的音频文件将保存在 `output/` 目录中。

## API 文档

API 文档可以通过访问 `/docs` 或 `/redoc` (如果 `app.py` 配置了 FastAPI 或 Flask-RESTX) 来查看，或者直接参考 `openapi.json` 文件。

## 文件结构

```
.
├── app.py                  # 主应用程序文件 (Coze 服务接口)
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 构建文件
├── docker-compose.yml      # Docker Compose 配置
├── openapi.json            # OpenAPI 规范文件
├── tts_client.py           # TTS 客户端逻辑 (可能包含推理和拼接功能)
├── .gitignore              # Git 忽略文件
├── output/                 # 生成的音频输出目录
│   └── combined_tts.mp3
└── uploads/                # 上传文件目录 (如果需要上传输入文件)
```

## 许可证

[选择一个许可证，例如 MIT 或 Apache 2.0]