# Mock DPSS Service

Mock DPSS 服务是一个用于测试和开发的仿真程序，模拟真实的 DPSS 服务 API，返回符合 `config/dialogue_context.yml` schema 的对话上下文数据。

## 功能特性

- **完全兼容的 API**：实现与真实 DPSS 服务相同的 REST API 接口
- **可编辑的数据**：通过 YAML 文件管理模拟数据，支持热重载
- **多种上下文场景**：预置了空上下文、丰富对话历史、电商开发等多种场景
- **动态数据管理**：支持通过 API 动态更新特定频道的上下文数据
- **完整的 Schema 支持**：严格遵循 `dialogue_context.yml` 中定义的数据结构

## 快速开始

### 1. 安装依赖

```bash
# 确保安装了必要的依赖
pip install fastapi uvicorn pyyaml
```

### 2. 启动服务

```bash
# 使用默认配置启动（端口 8080）
python tools/mock_dpss_service.py

# 自定义端口和主机
python tools/mock_dpss_service.py --host 0.0.0.0 --port 8080

# 启用开发模式（自动重载）
python tools/mock_dpss_service.py --reload

# 使用自定义数据文件
python tools/mock_dpss_service.py --data-file custom_data.yml
```

### 3. 验证服务

```bash
# 健康检查
curl http://localhost:8080/health

# 获取服务信息
curl http://localhost:8080/

# 测试上下文 API
curl "http://localhost:8080/api/v1/dpss/context?channel_id=channel456&limit=5"
```

## API 接口

### 核心接口

#### `GET /api/v1/dpss/context`

获取指定频道的对话上下文数据。

**参数：**
- `channel_id` (必需): 频道 ID
- `limit` (可选): 最大历史记录数量，默认为 5

**响应：**
返回符合 `dialogue_context.yml` schema 的 JSON 数据。

**示例：**
```bash
curl "http://localhost:8080/api/v1/dpss/context?channel_id=ecommerce_dev&limit=3"
```

### 管理接口

#### `GET /health`
健康检查接口

#### `GET /data`
获取当前所有模拟数据（调试用）

#### `POST /data/reload`
重新加载数据文件

#### `PUT /data/channel/{channel_id}`
更新特定频道的上下文数据

**示例：**
```bash
curl -X PUT "http://localhost:8080/data/channel/test_channel" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "test_channel",
    "recent_history": [
      {
        "turn_id": "test_001",
        "speaker_type": "user",
        "user_id_if_user": "test_user",
        "utterance_text": "测试消息",
        "timestamp_utc": "2025-06-05T12:00:00Z"
      }
    ],
    "current_focus_reis_summary": [],
    "active_questions": []
  }'
```

## 数据管理

### 数据文件结构

模拟数据存储在 `tools/mock_dpss_data.yml` 文件中，结构如下：

```yaml
dialogue_contexts:
  channel_id_1:
    channel_id: "channel_id_1"
    retrieval_timestamp_utc: "2025-06-05T10:29:00Z"
    recent_history: [...]
    current_focus_reis_summary: [...]
    active_questions: [...]
  
  channel_id_2:
    # 另一个频道的数据
    
  default:
    # 默认上下文（当请求的频道不存在时使用）
```

### 预置场景

服务预置了以下测试场景：

1. **`channel123`** - 空上下文场景
   - 适用于测试新对话开始的情况

2. **`channel456`** - 丰富对话历史场景
   - 包含多轮对话历史
   - 多个焦点 REI
   - 活跃的待回答问题

3. **`ecommerce_dev`** - 电商系统开发场景
   - B2C/B2B 电商平台讨论
   - 包含目标、角色、非功能需求等多种 REI 类型

4. **`default`** - 默认场景
   - 当请求不存在的频道时返回

### 编辑数据

你可以通过以下方式修改模拟数据：

1. **直接编辑文件**：修改 `tools/mock_dpss_data.yml`，然后调用重载接口
2. **API 更新**：使用 PUT 接口动态更新特定频道数据
3. **程序重启**：重启服务会重新加载文件数据

## 与 NLU 服务集成

### 配置 NLU 服务

在 `config/config.yml` 中配置 DPSS 服务地址：

```yaml
nlu_service:
  dpss:
    base_url: "http://localhost:8080"  # Mock DPSS 服务地址
    context_endpoint: "/api/v1/dpss/context"
    timeout: 30
```

### 测试集成

1. 启动 Mock DPSS 服务：
```bash
python tools/mock_dpss_service.py
```

2. 启动 NLU 服务进行测试：
```bash
cd nlu-service
python -m nlu_service.main
```

3. 发送测试消息验证集成效果

## 开发和调试

### 日志输出

服务会输出详细的请求日志，包括：
- 接收到的请求参数
- 返回的上下文数据
- 错误信息

### 数据验证

服务会自动验证返回的数据是否符合 schema 要求，确保与真实 DPSS 服务的兼容性。

### 扩展功能

你可以根据需要扩展 Mock 服务：

1. 添加新的 API 端点
2. 实现更复杂的数据逻辑
3. 添加数据持久化功能
4. 集成更多测试场景

## 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 使用不同端口
   python tools/mock_dpss_service.py --port 8081
   ```

2. **数据文件格式错误**
   ```bash
   # 检查 YAML 语法
   python -c "import yaml; yaml.safe_load(open('tools/mock_dpss_data.yml'))"
   ```

3. **依赖缺失**
   ```bash
   pip install fastapi uvicorn pyyaml
   ```

### 调试技巧

- 使用 `GET /data` 接口查看当前加载的数据
- 检查服务日志输出
- 使用 `--reload` 参数启用开发模式
- 通过 `POST /data/reload` 重新加载数据而无需重启服务 