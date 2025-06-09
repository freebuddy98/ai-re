# Input Service - 外部接口文档

## 概述

Input Service 是 AI-RE 系统的统一外部消息入口服务，负责接收来自各种外部平台（如 Mattermost、Slack 等）的消息，并将其标准化后通过事件总线发布到系统内部。

## 版本信息

- **版本**: 0.1.0
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **端口**: 8000 (默认)

## REST API 接口

### 1. Webhook 接口

#### Mattermost Outgoing Webhook

接收来自 Mattermost 的 Outgoing Webhook 消息。

**端点**: `POST /api/v1/webhook/mattermost`

**请求头**:
```
Content-Type: application/json
```

**请求体结构**:
```json
{
  "token": "webhook-token",
  "team_id": "team-identifier",
  "team_domain": "team-domain-name",
  "channel_id": "channel-identifier",
  "channel_name": "channel-name",
  "timestamp": 1677123456000,
  "user_id": "user-identifier",
  "user_name": "username",
  "post_id": "post-identifier",
  "text": "用户消息内容",
  "trigger_word": "触发词",
  "file_ids": "文件ID列表",
  "create_at": 1677123456000
}
```

**请求字段说明**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `token` | string | 是 | Webhook验证令牌 |
| `team_id` | string | 是 | 团队标识符 |
| `team_domain` | string | 否 | 团队域名 |
| `channel_id` | string | 是 | 频道标识符 |
| `channel_name` | string | 否 | 频道名称 |
| `timestamp` | integer | 否 | 消息时间戳（毫秒） |
| `user_id` | string | 是 | 用户标识符 |
| `user_name` | string | 否 | 用户名 |
| `post_id` | string | 否 | 帖子标识符 |
| `text` | string | 是 | 消息文本内容 |
| `trigger_word` | string | 否 | 触发词 |
| `file_ids` | string | 否 | 附件文件ID |
| `create_at` | integer | 否 | 创建时间戳（毫秒） |

**响应格式**:

成功响应 (200 OK):
```json
{
  "status": "success",
  "message": "Webhook processed successfully"
}
```

忽略响应 (200 OK) - 空消息时:
```json
{
  "status": "ignored",
  "reason": "empty_message"
}
```

错误响应 (200 OK) - 处理失败时:
```json
{
  "status": "error",
  "message": "Failed to process webhook"
}
```

**示例请求**:
```bash
curl -X POST http://localhost:8000/api/v1/webhook/mattermost \
  -H "Content-Type: application/json" \
  -d '{
    "token": "abc123",
    "team_id": "team_001",
    "channel_id": "channel_general",
    "channel_name": "general",
    "user_id": "user_123",
    "user_name": "john_doe",
    "text": "Hello, AI assistant!",
    "post_id": "post_456"
  }'
```

### 2. 健康检查接口

检查服务健康状态。

**端点**: `GET /health`

**响应格式**:
```json
{
  "status": "ok",
  "service": "input-service",
  "version": "0.1.0",
  "timestamp": "2023-12-01T10:30:00Z"
}
```

**示例请求**:
```bash
curl http://localhost:8000/health
```

### 3. Loki 状态接口

检查 Loki 日志系统连接状态。

**端点**: `GET /loki-status`

**响应格式**:
```json
{
  "loki_enabled": true,
  "loki_url": "http://loki:3100/loki/api/v1/push",
  "status": "connected|disconnected",
  "last_check": "2023-12-01T10:30:00Z"
}
```

**示例请求**:
```bash
curl http://localhost:8000/loki-status
```

## 事件输出

### 发布的事件类型

服务处理外部消息后，会发布以下标准化事件到事件总线：

#### 用户原始消息事件

**主题**: `user_message_raw`

**事件结构**:
```json
{
  "meta": {
    "event_id": "uuid-string",
    "source": "mattermost",
    "timestamp": 1677123456000
  },
  "user_id": "user123",
  "username": "john_doe",
  "platform": "mattermost",
  "channel_id": "channel456",
  "content": {
    "text": "Hello, AI assistant!",
    "attachments": null
  },
  "raw_data": {
    "original_webhook_payload": "完整的原始webhook数据"
  }
}
```

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `meta.event_id` | string | 事件唯一标识符 |
| `meta.source` | string | 消息来源平台 |
| `meta.timestamp` | integer | 事件时间戳（毫秒） |
| `user_id` | string | 用户标识符 |
| `username` | string | 用户名（可选） |
| `platform` | string | 来源平台名称 |
| `channel_id` | string | 频道标识符 |
| `content.text` | string | 处理后的消息文本 |
| `content.attachments` | array | 附件列表（当前为null） |
| `raw_data` | object | 原始webhook数据 |

## 配置接口

### 服务配置

服务通过配置文件 `config/config.yml` 进行配置：

```yaml
input_service:
  service_name: "input-service"
  app_title: "AI-RE 输入服务"
  app_description: "AI-RE 助手系统的统一外部消息入口"
  app_version: "0.1.0"
  
  # API配置
  api:
    host: "0.0.0.0"
    port: 8000
    docs_url: "/docs"
    redoc_url: "/redoc"
    openapi_url: "/openapi.json"
  
  # API路径配置
  api_paths:
    mattermost_webhook: "/api/v1/webhook/mattermost"
    health: "/health"
    loki_status: "/loki-status"
  
  # 主题配置
  topics:
    publish:
      - "user_message_raw"
    subscribe:
      - "system_status"
```

### 环境变量

支持以下环境变量配置：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `CONFIG_PATH` | `/app/config/config.yml` | 配置文件路径 |
| `SERVICE_NAME` | `input-service` | 服务名称 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `REDIS_HOST` | `redis` | Redis服务器地址 |
| `REDIS_PORT` | `6379` | Redis服务器端口 |

## 错误处理

### 错误类型

1. **验证错误**: 请求数据格式不正确
2. **处理错误**: 内部处理失败
3. **发布错误**: 事件发布到总线失败
4. **连接错误**: Redis连接失败

### 错误响应格式

所有错误都以200状态码返回，包含错误信息：

```json
{
  "status": "error",
  "message": "错误描述",
  "details": {
    "error_code": "ERROR_001",
    "timestamp": "2023-12-01T10:30:00Z"
  }
}
```

### 错误处理策略

- **空消息**: 直接忽略，返回ignored状态
- **格式错误**: 记录错误日志，返回error状态
- **发布失败**: 记录错误日志，返回error状态
- **系统异常**: 记录异常堆栈，返回error状态

## 监控与日志

### 日志记录

服务记录以下类型的日志：

1. **请求日志**: 记录所有webhook请求
2. **处理日志**: 记录消息处理过程
3. **错误日志**: 记录所有错误和异常
4. **性能日志**: 记录处理时间等性能指标

### 监控指标

- **请求计数**: 总请求数和成功/失败计数
- **处理延迟**: 消息处理时间
- **事件发布**: 发布成功/失败计数
- **健康状态**: 服务和依赖组件状态

### 日志格式

```json
{
  "timestamp": "2023-12-01T10:30:00Z",
  "level": "INFO",
  "service": "input-service",
  "message": "收到 Mattermost 消息",
  "context": {
    "user_id": "user123",
    "channel_id": "channel456",
    "text_length": 25
  }
}
```

## 安全考虑

### 输入验证

- 验证webhook token（如果配置）
- 检查请求数据格式和大小
- 过滤危险字符和内容

### 访问控制

- IP白名单（如果需要）
- 请求频率限制
- Token验证机制

### 数据保护

- 敏感数据脱敏
- 审计日志记录
- 安全传输（HTTPS）

## 部署配置

### Docker 部署

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "-m", "input_service", "--config", "/app/config/config.yml"]
```

### Docker Compose

```yaml
services:
  input-service:
    build: ./services/input-service
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - LOG_LEVEL=INFO
    depends_on:
      - redis
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
```

### Kubernetes 部署

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: input-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: input-service
  template:
    metadata:
      labels:
        app: input-service
    spec:
      containers:
      - name: input-service
        image: ai-re/input-service:0.1.0
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_HOST
          value: "redis-service"
        - name: LOG_LEVEL
          value: "INFO"
```

## 集成示例

### Mattermost 集成

1. 在 Mattermost 中创建 Outgoing Webhook
2. 设置 Callback URL: `http://your-server:8000/api/v1/webhook/mattermost`
3. 配置触发词或频道
4. 服务将自动处理消息并发布到事件总线

### 客户端SDK示例

```python
import requests

class InputServiceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def send_webhook(self, webhook_data: dict) -> dict:
        response = requests.post(
            f"{self.base_url}/api/v1/webhook/mattermost",
            json=webhook_data
        )
        return response.json()
    
    def health_check(self) -> dict:
        response = requests.get(f"{self.base_url}/health")
        return response.json()

# 使用示例
client = InputServiceClient("http://localhost:8000")
result = client.send_webhook({
    "token": "abc123",
    "user_id": "user123",
    "channel_id": "channel456",
    "text": "Hello, AI!"
})
```

## 故障排除

### 常见问题

1. **连接Redis失败**: 检查Redis服务状态和网络连接
2. **配置文件未找到**: 确认CONFIG_PATH环境变量设置
3. **事件发布失败**: 检查Redis Streams配置和权限
4. **webhook不响应**: 检查URL配置和防火墙设置

### 调试方法

1. **启用DEBUG日志**: 设置LOG_LEVEL=DEBUG
2. **检查健康接口**: 访问/health端点
3. **查看日志文件**: 检查应用日志和错误信息
4. **测试Redis连接**: 使用redis-cli验证连接

## 版本兼容性

- **Python**: 3.8+
- **FastAPI**: 0.100+
- **Redis**: 5.0+
- **Mattermost**: 5.0+

## 变更日志

### v0.1.0 (2023-12-01)
- 初始版本发布
- Mattermost webhook支持
- 基础健康检查接口
- 事件总线集成
- Docker容器支持 