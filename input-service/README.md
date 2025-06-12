# Input Service

AI-RE 助手系统的统一外部消息入口。

## 功能

- 接收 Mattermost Webhook 消息
- 处理并标准化消息格式
- 将消息发布到事件总线

## 安装

```bash
pip install -e .
```

## 使用

```bash
python -m input_service.main
```

## 功能特点

- 提供 HTTP/S 端点，接收来自 Mattermost 的实时 Webhook 消息
- 对接收到的消息进行基础的验证和解析
- 对消息文本进行初步的预处理
- 将提取并处理后的信息构造成标准的 `RawMessage` 格式
- 通过事件总线框架 (`IEventBus`) 将消息发布出去，供后续服务消费

## 安装

### 从源码安装

```bash
# 克隆项目
git clone <repository-url>
cd ai-re

# 安装输入服务
pip install -e ./input_service
```

### 依赖

- Python 3.8+
- FastAPI
- Uvicorn
- 事件总线框架 (Event Bus Framework)

## 使用方法

### 启动服务

```bash
# 使用默认配置启动
input-service

# 或者指定参数
input-service --host 0.0.0.0 --port 8080 --redis-url redis://localhost:6379/0 --topic raw_message
```

### 命令行参数

- `--host`: 服务监听的主机地址 (默认: 0.0.0.0)
- `--port`: 服务监听的端口 (默认: 8000)
- `--redis-url`: Redis 连接 URL (默认: redis://localhost:6379/0)
- `--topic`: 默认的消息发布主题 (默认: raw_message)
- `--debug`: 启用调试模式

## API 端点

### Mattermost Webhook

- **URL**: `/api/v1/mattermost/webhook`
- **方法**: POST
- **描述**: 接收并处理来自 Mattermost 的 Webhook 推送消息

### 健康检查

- **URL**: `/health`
- **方法**: GET
- **描述**: 服务健康状态检查

## 开发

### 运行测试

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest input_service/tests
```

## 项目结构

```
input_service/
├── src/
│   └── input_service/
│       ├── __init__.py
│       ├── app.py           # FastAPI 应用创建
│       ├── main.py          # 服务入口点
│       ├── service.py       # 消息处理服务
│       └── webhook_handler.py # Webhook 处理器
├── tests/
│   └── test_webhook_handler.py
├── setup.py
└── README.md
```

## 贡献

欢迎贡献代码和提出问题！请参阅项目的贡献指南。 