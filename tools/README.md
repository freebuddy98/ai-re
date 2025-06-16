# 工具目录 (Tools Directory)

本目录包含用于 AI-RE 系统开发和测试的各种工具。

## 🎯 新功能亮点

### 1. 基于时间戳的Redis流key管理
- **问题解决**: 避免不同时间段的事件混合存储
- **优雅方案**: 使用 `ai-re:<时间戳>:事件类型` 格式的流key
- **便于调试**: 每个开发会话有独立的事件流
- **便于重放**: 可以轻松切换和管理不同的测试会话

### 2. 紧凑对话历史显示
- **用户友好**: 每次输入后自动显示最近5轮对话
- **调试方便**: 快速查看对话上下文，无需滚动
- **格式简洁**: 使用图标和缩略文本提高可读性

## 🛠️ 工具列表

### Mock DPSS 服务 (Mock DPSS Service)

`mock_dpss_service.py` - 用于测试和开发的 DPSS 服务仿真程序

**核心功能:**
- 完全兼容的 REST API，模拟真实 DPSS 服务
- 可编辑的 YAML 数据文件，支持热重载
- 多种预置测试场景（空上下文、丰富对话、电商开发等）
- 动态数据管理，支持通过 API 更新上下文
- 严格遵循 `dialogue_context.yml` schema

**快速启动:**

```bash
# 使用启动脚本（推荐）
./tools/start_mock_dpss.sh

# 或直接运行
python tools/mock_dpss_service.py --port 8080

# 自定义配置
./tools/start_mock_dpss.sh --host 0.0.0.0 --port 8080 --reload
```

**API 接口:**
- `GET /api/v1/dpss/context` - 获取对话上下文
- `GET /health` - 健康检查
- `GET /data` - 查看所有模拟数据
- `POST /data/reload` - 重新加载数据文件
- `PUT /data/channel/{channel_id}` - 更新特定频道数据

**测试验证:**

```bash
# 运行完整测试套件
python tools/test_mock_dpss.py

# 测试特定接口
curl "http://localhost:8080/api/v1/dpss/context?channel_id=channel456&limit=3"
```

**数据管理:**
- 数据文件: `tools/mock_dpss_data.yml`
- 预置场景: `channel123`(空), `channel456`(丰富), `ecommerce_dev`(电商), `default`(默认)
- 支持实时编辑和热重载

### 会话管理器 (Session Manager)

`session_manager.py` - 管理基于时间戳的Redis流会话

**核心功能:**
- 初始化新会话并自动生成时间戳前缀
- 切换到已有会话
- 查看和清理旧会话数据
- 实时监控Redis流状态

**使用方法:**

```bash
# 初始化新会话
python tools/session_manager.py init --description "功能测试会话"

# 查看当前会话
python tools/session_manager.py current

# 列出所有会话
python tools/session_manager.py list

# 切换到指定会话
python tools/session_manager.py switch 20240605143022

# 查看Redis流状态
python tools/session_manager.py streams

# 清理旧会话 (保留最近3个)
python tools/session_manager.py clean --keep 3 --execute
```

### 交互式对话仿真器 (Interactive Dialogue Simulator)

`interactive_dialogue_simulator.py` - 交互式、向导式的 Python 脚本，用于仿真客户与需求分析师之间的多轮对话。

**新增功能:**
- ✨ 每次输入后自动显示最近5轮对话 (紧凑格式)
- ✨ 自动使用基于时间戳的Redis流key
- ✨ 自动检测和修复Redis连接 (Docker容器 ↔ localhost)

**功能特性:**
1. **多轮对话仿真**: 支持客户和需求分析师角色之间的对话切换
2. **对话历史管理**: 可以加载已有对话或开始新对话
3. **事件总线集成**: 客户消息自动发送为 `user_message_raw` 事件
4. **环境检测**: 自动检测并启动 Redis 服务器（支持 Docker）
5. **对话保存**: 可以保存对话历史供后续继续
6. **智能显示**: 紧凑显示最近对话，便于调试

**使用方法:**

#### 基本运行

```bash
# 从项目根目录运行
python tools/interactive_dialogue_simulator.py
```

#### 环境要求

脚本会自动检测和处理以下环境：

1. **Redis 服务器**：
   - 首先检查本地 Redis (localhost:6379)
   - 然后检查 Docker 中的 Redis 容器
   - 如果都不存在，尝试自动启动 Redis Docker 容器

2. **事件总线配置**：
   - 需要 `config/config.yml` 配置文件
   - 需要事件总线框架库

#### 操作流程

1. **启动脚本**: 运行脚本后首先进行环境检测
2. **选择对话模式**:
   - 选择 "1" 开始新对话
   - 选择 "2" 继续已有对话
3. **对话循环**:
   - 每轮选择说话身份（客户或需求分析师）
   - 输入对话内容
   - 客户消息会自动发送到事件总线
   - **新**: 自动显示最近5轮对话的紧凑视图
4. **特殊命令**:
   - `quit` - 结束对话
   - `history` - 查看完整对话历史
   - `save` - 保存当前对话

#### 新增的紧凑对话显示

每次输入消息后，会自动显示类似这样的紧凑格式：

```
📝 最近 5 轮对话:
--------------------------------------------------
 4. 🤖 分析师: 明白了。您期望支持多少并发用户？
 5. 👤 客户: 预计最多1000个并发用户
 6. 🤖 分析师: 好的。关于用户注册，您希望支持哪些注册方式？
 7. 👤 客户: 支持邮箱注册和手机号注册两种方式
 8. 🤖 分析师: 那么关于安全性，您有什么特殊要求吗？

📊 当前对话包含 8 条消息
```

## 📁 对话存储

对话文件存储在 `tools/conversations/` 目录下：
- 格式: JSON
- 包含: 会话ID、频道ID、消息历史、时间戳等
- 示例文件: `example_login_system.json`

## 🔧 配置文件

### Redis流前缀配置

主配置文件 `config/config.yml` 中的 `event_bus.stream_prefix` 会被会话管理器自动更新:

```yaml
event_bus:
  stream_prefix: "ai-re:20240605143022"  # 自动生成的时间戳前缀
  redis:
    host: "${REDIS_HOST:-127.0.0.1}"
    port: "${REDIS_PORT:-6379}"
    # ...
```

### 会话跟踪文件

`tools/sessions.yml` - 跟踪所有会话的元数据:

```yaml
current_session: "20240605143022"
sessions:
  - timestamp: "20240605143022"
    created_at: "2024-06-05T14:30:22.123456"
    description: "功能测试会话"
    prefix: "ai-re:20240605143022"
    base_prefix: "ai-re"
```

## 🎮 快速开始示例

### 场景1: 开始新的开发会话

```bash
# 1. 初始化新会话
python tools/session_manager.py init --description "用户登录功能开发"

# 2. 启动对话仿真器
python tools/interactive_dialogue_simulator.py

# 3. 进行对话测试
# (选择客户身份，输入需求...)
# (每次输入后会自动显示最近5轮对话)

# 4. 查看Redis流状态
python tools/session_manager.py streams
```

### 场景2: 继续已有会话

```bash
# 1. 查看可用会话
python tools/session_manager.py list

# 2. 切换到指定会话
python tools/session_manager.py switch 20240605143022

# 3. 继续对话仿真
python tools/interactive_dialogue_simulator.py
# (选择"继续已有对话")
```

### 场景3: 清理旧数据

```bash
# 1. 查看当前Redis流
python tools/session_manager.py streams

# 2. 预览清理操作 (dry-run)
python tools/session_manager.py clean --keep 3

# 3. 执行清理
python tools/session_manager.py clean --keep 3 --execute
```

## 🧪 测试工具

`test_new_features.py` - 测试新功能的演示脚本:

```bash
python tools/test_new_features.py
```

测试内容:
- 紧凑对话历史显示功能
- 基于时间戳的Redis流key功能
- Redis连接和事件发送

## ⚠️ 注意事项

1. **Redis连接**: 工具会自动处理Docker容器和本地Redis的连接差异
2. **环境变量**: 确保 `.env` 文件中的Redis配置正确
3. **会话管理**: 建议定期清理旧会话以节省Redis存储空间
4. **对话保存**: 重要对话记得及时保存，避免意外丢失

## 🚀 高级用法

### 自定义Redis连接

如果使用非标准Redis配置，可以临时修改环境变量：

```bash
export REDIS_HOST=custom-redis-host
export REDIS_PORT=6380
python tools/session_manager.py streams
```

### 批量会话管理

结合shell脚本可以实现批量操作：

```bash
# 批量创建测试会话
for desc in "登录测试" "注册测试" "密码重置测试"; do
    python tools/session_manager.py init --description "$desc"
    sleep 1
done
```

### 集成到CI/CD

会话管理器可以集成到自动化测试流程中：

```bash
# 在测试开始前创建独立会话
TEST_SESSION=$(python tools/session_manager.py init --description "CI测试-$(date +%Y%m%d-%H%M%S)" | grep "initialized:" | cut -d: -f2 | tr -d ' ')

# 运行测试...

# 测试完成后清理
python tools/session_manager.py clean --keep 1 --execute
``` 