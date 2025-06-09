# AI-RE 项目测试组织结构文档

## 概述

本文档描述了 AI-RE 项目的测试架构、组织结构和最佳实践。我们采用测试金字塔模型，确保高质量的代码覆盖率和快速的反馈循环。

## 测试架构

### 测试金字塔

```
    /\
   /  \     E2E Tests (端到端测试)
  /    \    - 完整工作流验证
 /      \   - 真实环境模拟
/________\  - 用户体验验证
\        /  
 \      /   Integration Tests (集成测试)
  \    /    - 组件间集成验证
   \  /     - 外部依赖测试
    \/      - 接口兼容性测试
   ___
  /   \     Unit Tests (单元测试)
 /     \    - 快速反馈
/_______\   - 高覆盖率
            - 独立测试
```

## 目录结构

```
ai-re/
├── tests/                          # 根级测试目录
│   ├── unit/                       # 单元测试（预留，当前在各模块内）
│   ├── integration/                # 集成测试
│   │   ├── test_redis_integration.py      # Redis 集成测试
│   │   ├── test_input_service_integration.py # 输入服务集成测试
│   │   └── test_system_configuration.py   # 系统配置集成测试
│   ├── e2e/                        # 端到端测试
│   │   ├── test_api_workflow.py           # API 工作流测试
│   │   ├── test_service_health.py         # 服务健康检查测试
│   │   └── test_input_service_e2e.py      # 输入服务 E2E 测试
│   ├── fixtures/                   # 共享测试数据
│   ├── conftest.py                 # pytest 配置
│   └── requirements.txt            # 测试依赖
├── libs/                           # 共享库
│   └── event_bus_framework/
│       └── tests/
│           └── unit/               # 框架单元测试
└── services/                       # 服务
    └── input-service/
        └── tests/
            └── unit/               # 服务单元测试
```

## 测试类型详细说明

### 1. 单元测试 (Unit Tests)

**位置**: 每个模块的 `tests/unit/` 目录下  
**目标**: 测试单个函数、类或方法的行为  
**特点**:
- 执行速度快 (< 100ms per test)
- 无外部依赖
- 高代码覆盖率 (目标 >90%)
- 使用 mock 对象模拟依赖

**命名规范**:
- 文件: `test_<module_name>.py`
- 类: `Test<ClassName>`
- 方法: `test_<specific_behavior>`

### 2. 集成测试 (Integration Tests)

**位置**: `tests/integration/`  
**目标**: 测试组件之间的交互和集成  
**特点**:
- 使用真实的外部服务 (Redis, Loki)
- 测试数据持久化和网络通信
- 验证配置和环境设置

**测试用例**:
- Redis 连接和数据操作
- 事件总线发布/订阅
- 服务间通信
- 配置加载和验证

### 3. 端到端测试 (E2E Tests)

**位置**: `tests/e2e/`  
**目标**: 验证完整的用户工作流和业务场景  
**特点**:
- 模拟真实用户操作
- 测试完整的数据流
- 验证性能和可用性

**测试场景**:
- Webhook 处理完整流程
- API 端点功能验证
- 错误处理和恢复
- 负载和压力测试

## 测试配置

### 环境变量

```bash
# 测试控制
SKIP_INTEGRATION_TESTS=false    # 跳过集成测试
SKIP_E2E_TESTS=false           # 跳过 E2E 测试

# Redis 配置
REDIS_TEST_HOST=localhost       # 测试 Redis 主机
REDIS_TEST_PORT=6379           # 测试 Redis 端口

# 服务配置
SERVICE_URL=http://localhost:8000  # 测试服务 URL
LOG_LEVEL=DEBUG                    # 测试日志级别
```

### pytest 配置

**pyproject.toml**:
```toml
[tool.pytest.ini_options]
testpaths = ["tests", "libs", "services"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
    "--disable-warnings",
    "--color=yes"
]
markers = [
    "unit: 单元测试",
    "integration: 集成测试", 
    "e2e: 端到端测试",
    "slow: 运行时间较长的测试",
    "redis: 需要 Redis 的测试"
]
```

## 测试执行策略

### 开发阶段

```bash
# 快速单元测试
make test-unit

# 完整测试套件
make test

# 特定类型测试
pytest -m unit          # 仅单元测试
pytest -m integration   # 仅集成测试
pytest -m e2e           # 仅 E2E 测试
```

### CI/CD 管道

```yaml
# .github/workflows/test.yml
test_strategy:
  - stage: unit_tests
    parallel: true
    fast_fail: true
  
  - stage: integration_tests  
    depends_on: unit_tests
    services: [redis, loki]
    
  - stage: e2e_tests
    depends_on: integration_tests
    full_environment: true
```

## 测试数据管理

### Fixtures

**共享 fixtures** (`tests/conftest.py`):
```python
@pytest.fixture
def redis_client():
    """Redis 客户端 fixture"""
    
@pytest.fixture  
def mock_event_bus():
    """模拟事件总线 fixture"""
    
@pytest.fixture
def sample_webhook_data():
    """示例 webhook 数据 fixture"""
```

### 测试数据隔离

- 使用唯一的测试前缀
- 自动清理测试数据
- 避免测试间相互影响

## 最佳实践

### 1. 测试编写原则

- **AAA 模式**: Arrange, Act, Assert
- **单一职责**: 每个测试只验证一个行为
- **独立性**: 测试之间不应有依赖关系
- **确定性**: 测试结果应该可重复

### 2. 命名约定

```python
def test_service_should_publish_event_when_valid_webhook_received():
    """测试服务在收到有效 webhook 时应该发布事件"""
    # Arrange
    webhook_data = create_valid_webhook()
    
    # Act
    result = service.process_webhook(webhook_data)
    
    # Assert  
    assert result.success is True
    assert_event_published()
```

### 3. Mock 使用指南

- **单元测试**: 大量使用 mock 隔离依赖
- **集成测试**: 尽量使用真实服务
- **E2E 测试**: 避免使用 mock

### 4. 异步测试

```python
@pytest.mark.asyncio
async def test_async_webhook_handler():
    """异步 webhook 处理测试"""
    # 使用 pytest-asyncio 处理异步测试
```

## 性能基准

### 测试执行时间目标

- 单元测试: < 5 分钟 (全部)
- 集成测试: < 10 分钟
- E2E 测试: < 15 分钟

### 覆盖率目标

- 单元测试覆盖率: >90%
- 集成测试覆盖率: >70%
- 整体覆盖率: >85%

## 故障排查

### 常见问题

1. **Redis 连接失败**
   - 检查 REDIS_TEST_HOST 环境变量
   - 确认 Redis 服务运行状态

2. **测试间数据污染**
   - 使用唯一的测试前缀
   - 确保测试清理逻辑执行

3. **异步测试不稳定**
   - 适当增加等待时间
   - 使用确定性的同步点

### 调试技巧

```bash
# 详细输出
pytest -v -s

# 失败时进入调试器
pytest --pdb

# 运行特定测试
pytest tests/integration/test_redis_integration.py::TestRedisIntegration::test_connection
```

## 总结

本测试组织结构确保了:
- **快速反馈**: 单元测试提供即时反馈
- **可靠集成**: 集成测试验证组件协作
- **完整验证**: E2E 测试确保用户体验
- **易于维护**: 清晰的结构和最佳实践 