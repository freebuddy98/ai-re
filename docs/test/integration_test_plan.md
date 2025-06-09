# 集成测试计划文档

## 概述

本文档描述了 AI-RE 系统的集成测试策略、测试用例和执行计划。集成测试主要验证各组件之间的接口和交互，确保系统各部分能够正确协同工作。

## 测试目标

### 主要目标
1. **接口兼容性验证**: 确保各组件间接口规范一致
2. **数据流完整性**: 验证数据在组件间正确传递
3. **错误处理机制**: 测试异常情况下的系统行为
4. **性能基准验证**: 确保集成后性能满足要求
5. **配置兼容性**: 验证不同配置下的系统行为

### 测试范围
- Event Bus Framework 与 Redis 的集成
- Input Service 与 Event Bus Framework 的集成
- 配置系统的集成测试
- 日志系统的集成测试
- 外部依赖的集成测试

## 测试环境

### 环境配置
```yaml
测试环境规格:
  - Redis: 6.0+
  - Python: 3.10
  - 操作系统: Linux/Ubuntu 20.04+
  - 内存: 最少 2GB
  - CPU: 最少 2 核心
```

### 依赖服务
```yaml
services:
  redis:
    image: redis:6.2-alpine
    ports:
      - "6379:6379"
  
  loki:
    image: grafana/loki:2.8.0
    ports:
      - "3100:3100"
    
  test-runner:
    build: .
    environment:
      - REDIS_HOST=redis
      - LOKI_URL=http://loki:3100/loki/api/v1/push
    depends_on:
      - redis
      - loki
```

## 测试分类

### 1. Redis 集成测试

#### 测试目的
验证 Event Bus Framework 与 Redis Streams 的集成功能。

#### 测试用例

##### INT-001: Redis 连接测试
- **描述**: 验证与 Redis 服务器的基本连接
- **前置条件**: Redis 服务器运行在指定端口
- **测试步骤**:
  1. 创建 Redis 客户端连接
  2. 执行 PING 命令
  3. 验证连接状态
- **预期结果**: 连接成功，PING 返回 PONG
- **失败条件**: 连接超时或认证失败

##### INT-002: 流创建和删除测试
- **描述**: 验证 Redis Streams 的创建和删除功能
- **测试步骤**:
  1. 创建新的流
  2. 添加消息到流
  3. 验证流存在
  4. 删除流
  5. 验证流已删除
- **预期结果**: 流操作成功执行

##### INT-003: 消费者组管理测试
- **描述**: 验证消费者组的创建和管理
- **测试步骤**:
  1. 创建消费者组
  2. 添加消费者到组
  3. 验证组状态
  4. 删除消费者组
- **预期结果**: 消费者组操作正常

##### INT-004: 消息发布和订阅测试
- **描述**: 验证基本的发布/订阅功能
- **测试步骤**:
  1. 创建发布者和订阅者
  2. 发布测试消息
  3. 订阅者接收消息
  4. 验证消息内容完整性
- **预期结果**: 消息正确传递，无数据丢失

##### INT-005: 连接池测试
- **描述**: 验证 Redis 连接池的正确性
- **测试步骤**:
  1. 配置连接池参数
  2. 并发创建多个连接
  3. 执行并发操作
  4. 监控连接数量
- **预期结果**: 连接池正常工作，无连接泄漏

### 2. Event Bus Framework 集成测试

#### 测试目的
验证事件总线框架的核心功能和性能。

#### 测试用例

##### INT-101: 事件发布集成测试
- **描述**: 验证事件发布功能的完整性
- **测试步骤**:
  1. 初始化事件总线
  2. 创建测试事件
  3. 发布事件到指定主题
  4. 验证发布结果
- **预期结果**: 事件成功发布，返回消息ID

##### INT-102: 事件订阅集成测试
- **描述**: 验证事件订阅功能
- **测试步骤**:
  1. 创建订阅者
  2. 订阅指定主题
  3. 发布测试事件
  4. 验证接收到的事件
- **预期结果**: 正确接收并解析事件

##### INT-103: 多主题发布订阅测试
- **描述**: 验证多主题场景下的功能
- **测试步骤**:
  1. 创建多个主题
  2. 创建多个发布者和订阅者
  3. 交叉发布和订阅
  4. 验证消息路由正确性
- **预期结果**: 消息正确路由到对应订阅者

##### INT-104: 事件序列化集成测试
- **描述**: 验证事件序列化和反序列化
- **测试步骤**:
  1. 创建复杂事件对象
  2. 序列化事件
  3. 发布序列化数据
  4. 订阅并反序列化
  5. 验证数据完整性
- **预期结果**: 数据序列化/反序列化正确

##### INT-105: 错误处理集成测试
- **描述**: 验证异常情况下的错误处理
- **测试步骤**:
  1. 模拟 Redis 连接失败
  2. 发布事件
  3. 验证错误处理机制
  4. 恢复连接
  5. 验证自动重连
- **预期结果**: 错误正确处理，支持自动恢复

### 3. Input Service 集成测试

#### 测试目的
验证输入服务与事件总线的集成，以及外部接口的正确性。

#### 测试用例

##### INT-201: Webhook 处理集成测试
- **描述**: 验证 Webhook 请求的端到端处理
- **测试步骤**:
  1. 启动输入服务
  2. 发送 Mattermost Webhook 请求
  3. 验证事件总线接收到事件
  4. 检查事件格式和内容
- **预期结果**: Webhook 正确转换为事件并发布

##### INT-202: 消息验证集成测试
- **描述**: 验证输入消息的验证机制
- **测试步骤**:
  1. 发送有效的 Webhook 请求
  2. 发送无效的 Webhook 请求
  3. 发送空消息请求
  4. 验证处理结果
- **预期结果**: 有效消息处理，无效消息被拒绝

##### INT-203: 错误响应集成测试
- **描述**: 验证错误情况下的响应机制
- **测试步骤**:
  1. 模拟事件总线故障
  2. 发送 Webhook 请求
  3. 验证错误响应
  4. 恢复事件总线
  5. 验证正常处理恢复
- **预期结果**: 错误情况下返回正确的错误响应

##### INT-204: 配置加载集成测试
- **描述**: 验证服务配置的正确加载
- **测试步骤**:
  1. 修改配置文件
  2. 重启服务
  3. 验证配置生效
  4. 测试配置相关功能
- **预期结果**: 配置正确加载并生效

##### INT-205: 健康检查集成测试
- **描述**: 验证健康检查接口的完整性
- **测试步骤**:
  1. 启动所有依赖服务
  2. 调用健康检查接口
  3. 停止部分依赖服务
  4. 再次调用健康检查
- **预期结果**: 健康状态准确反映系统状态

### 4. 配置系统集成测试

#### 测试目的
验证配置系统在各种环境下的正确性。

#### 测试用例

##### INT-301: 环境变量替换测试
- **描述**: 验证配置中的环境变量替换功能
- **测试步骤**:
  1. 设置环境变量
  2. 加载配置文件
  3. 验证变量替换结果
  4. 测试默认值机制
- **预期结果**: 环境变量正确替换，默认值生效

##### INT-302: 配置文件优先级测试
- **描述**: 验证多个配置文件的加载优先级
- **测试步骤**:
  1. 创建多个配置文件
  2. 设置不同的配置路径
  3. 加载配置
  4. 验证优先级规则
- **预期结果**: 配置按预期优先级加载

##### INT-303: 配置验证集成测试
- **描述**: 验证配置数据的验证机制
- **测试步骤**:
  1. 创建有效配置
  2. 创建无效配置
  3. 加载配置
  4. 验证验证结果
- **预期结果**: 有效配置通过，无效配置被拒绝

### 5. 日志系统集成测试

#### 测试目的
验证日志系统的集成功能和外部日志服务的连接。

#### 测试用例

##### INT-401: 日志输出集成测试
- **描述**: 验证日志的正确输出
- **测试步骤**:
  1. 配置日志系统
  2. 输出不同级别的日志
  3. 验证控制台输出
  4. 验证文件输出
- **预期结果**: 日志正确输出到各个目标

##### INT-402: Loki 集成测试
- **描述**: 验证与 Loki 日志服务的集成
- **前置条件**: Loki 服务正常运行
- **测试步骤**:
  1. 配置 Loki 连接
  2. 发送测试日志
  3. 查询 Loki 中的日志
  4. 验证日志格式和内容
- **预期结果**: 日志正确发送到 Loki

##### INT-403: 日志格式化集成测试
- **描述**: 验证不同格式的日志输出
- **测试步骤**:
  1. 配置 JSON 格式
  2. 配置文本格式
  3. 输出测试日志
  4. 验证格式正确性
- **预期结果**: 日志格式符合配置要求

## 测试数据

### 测试数据集

#### Webhook 测试数据
```json
{
  "valid_webhook": {
    "token": "test-token-123",
    "team_id": "team_001",
    "channel_id": "channel_general",
    "user_id": "user_123",
    "text": "Hello, AI assistant!",
    "post_id": "post_456"
  },
  "invalid_webhook": {
    "token": "",
    "team_id": null,
    "text": ""
  },
  "large_message": {
    "token": "test-token",
    "user_id": "user_123",
    "text": "很长的消息内容..." // 10KB+ 文本
  }
}
```

#### 事件测试数据
```json
{
  "input_event": {
    "event_type": "input",
    "source_service": "test-service",
    "user_id": "test_user",
    "content": "Test message",
    "platform": "test_platform"
  },
  "complex_event": {
    "event_type": "input",
    "source_service": "test-service",
    "user_id": "test_user",
    "content": "Test message",
    "attachments": [
      {
        "type": "image",
        "url": "http://example.com/image.png"
      }
    ],
    "metadata": {
      "custom_field": "custom_value"
    }
  }
}
```

## 测试执行

### 自动化测试

#### 测试命令
```bash
# 运行所有集成测试
python -m pytest tests/integration/ -v

# 运行特定分类的测试
python -m pytest tests/integration/test_redis_integration.py -v
python -m pytest tests/integration/test_event_bus_integration.py -v
python -m pytest tests/integration/test_input_service_integration.py -v

# 运行带覆盖率的测试
python -m pytest tests/integration/ --cov=event_bus_framework --cov=input_service

# 并行执行测试
python -m pytest tests/integration/ -n auto
```

#### CI/CD 集成
```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:6.2-alpine
        ports:
          - 6379:6379
      
      loki:
        image: grafana/loki:2.8.0
        ports:
          - 3100:3100
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run integration tests
      run: |
        python -m pytest tests/integration/ -v --cov
      env:
        REDIS_HOST: localhost
        REDIS_PORT: 6379
        LOKI_URL: http://localhost:3100/loki/api/v1/push
```

### 手动测试

#### 测试清单
- [ ] Redis 连接测试
- [ ] 事件发布测试  
- [ ] 事件订阅测试
- [ ] Webhook 处理测试
- [ ] 错误处理测试
- [ ] 配置加载测试
- [ ] 日志输出测试
- [ ] 性能基准测试

#### 测试报告模板
```markdown
## 集成测试执行报告

### 测试信息
- 执行日期: YYYY-MM-DD
- 测试版本: v0.1.0
- 测试环境: development/staging/production
- 执行人员: [姓名]

### 测试结果汇总
- 总用例数: X
- 通过用例: X
- 失败用例: X
- 跳过用例: X
- 通过率: X%

### 失败用例详情
[记录失败的测试用例和原因]

### 性能指标
- 事件发布延迟: X ms
- 事件订阅延迟: X ms
- Webhook 响应时间: X ms
- 系统吞吐量: X events/sec

### 问题和建议
[记录发现的问题和改进建议]
```

## 性能基准

### 性能指标

#### 吞吐量指标
- **事件发布速率**: > 1000 events/sec
- **事件订阅速率**: > 1000 events/sec
- **Webhook 处理速率**: > 100 requests/sec

#### 延迟指标
- **事件发布延迟**: < 10ms (P99)
- **端到端延迟**: < 100ms (P99)
- **Webhook 响应时间**: < 200ms (P99)

#### 资源使用
- **内存使用**: < 512MB (正常负载)
- **CPU 使用**: < 50% (正常负载)
- **网络带宽**: < 100Mbps

### 性能测试

#### 负载测试
```python
# 性能测试示例
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

async def performance_test():
    # 并发发布测试
    event_count = 10000
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = []
        for i in range(event_count):
            future = executor.submit(publish_test_event, i)
            futures.append(future)
        
        # 等待所有任务完成
        for future in futures:
            future.result()
    
    end_time = time.time()
    duration = end_time - start_time
    throughput = event_count / duration
    
    print(f"发布 {event_count} 事件耗时: {duration:.2f}s")
    print(f"吞吐量: {throughput:.2f} events/sec")
```

## 测试维护

### 测试用例维护
- **定期更新**: 每月检查和更新测试用例
- **版本管理**: 测试用例与代码版本同步
- **文档更新**: 及时更新测试文档

### 测试环境维护
- **环境监控**: 监控测试环境的健康状态
- **数据清理**: 定期清理测试数据
- **环境重置**: 支持快速重置测试环境

### 测试工具升级
- **工具更新**: 定期更新测试工具和框架
- **最佳实践**: 采用最新的测试最佳实践
- **自动化改进**: 持续改进自动化测试流程

## 故障排除

### 常见问题

#### Redis 连接问题
- **现象**: 连接超时或拒绝连接
- **原因**: Redis 服务未启动或网络问题
- **解决**: 检查 Redis 服务状态和网络配置

#### 事件丢失问题
- **现象**: 发布的事件未被订阅者接收
- **原因**: 消费者组配置错误或网络延迟
- **解决**: 检查消费者组配置和网络状况

#### 性能问题
- **现象**: 测试执行时间过长
- **原因**: 资源不足或配置不当
- **解决**: 增加资源或优化配置

### 调试技巧
1. **启用详细日志**: 设置 DEBUG 级别日志
2. **使用监控工具**: 监控系统资源使用
3. **分步调试**: 逐步执行测试用例
4. **环境对比**: 对比不同环境的行为差异

## 总结

集成测试是确保 AI-RE 系统各组件正确协同工作的关键环节。通过系统性的集成测试，我们可以：

1. **提前发现问题**: 在生产环境之前发现集成问题
2. **验证功能完整性**: 确保所有功能在集成环境下正常工作
3. **建立信心**: 为系统部署提供信心保障
4. **持续改进**: 通过测试结果持续优化系统

建议定期执行集成测试，并根据系统演进不断完善测试用例和测试流程。 