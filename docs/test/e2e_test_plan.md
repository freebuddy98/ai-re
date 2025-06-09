# 端到端测试计划文档

## 概述

端到端（E2E）测试计划定义了 AI-RE 系统的全链路测试策略，从外部用户接口到内部事件处理的完整工作流程验证。E2E 测试确保系统在真实环境中能够按预期工作，为用户提供完整的功能验证。

## 测试目标

### 核心目标
1. **完整工作流验证**: 验证从输入到输出的完整业务流程
2. **用户体验测试**: 从用户角度验证系统功能和性能
3. **系统集成验证**: 确保所有组件在真实环境中协同工作
4. **业务场景覆盖**: 覆盖核心业务场景和边界情况
5. **生产环境模拟**: 在接近生产的环境中验证系统行为

### 测试范围
- 外部接口到内部事件处理的完整链路
- 多服务协同的业务流程
- 异常情况下的系统恢复能力
- 系统在负载下的表现
- 数据一致性和完整性

## 测试环境

### 环境要求
```yaml
生产环境模拟:
  架构: 微服务架构
  容器: Docker + Docker Compose
  存储: Redis Cluster
  日志: Loki + Grafana
  监控: Prometheus + Grafana
  网络: 独立网络命名空间
```

### 服务部署
```yaml
version: '3.8'
services:
  # Redis 集群
  redis:
    image: redis:6.2-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  # Input Service
  input-service:
    build: ./services/input-service
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - LOG_LEVEL=INFO
      - LOKI_URL=http://loki:3100/loki/api/v1/push
    depends_on:
      - redis
      - loki
    restart: unless-stopped

  # 日志服务
  loki:
    image: grafana/loki:2.8.0
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - loki_data:/loki

volumes:
  redis_data:
  loki_data:
```

## 测试场景

### 1. 基础功能场景

#### E2E-001: Mattermost Webhook 完整流程
**目标**: 验证从 Mattermost webhook 到事件发布的完整流程

**测试步骤**:
1. **环境准备**
   - 启动所有服务
   - 验证服务健康状态
   - 清空 Redis 数据

2. **Webhook 发送**
   ```bash
   curl -X POST http://localhost:8000/api/v1/webhook/mattermost \
     -H "Content-Type: application/json" \
     -d '{
       "token": "test-webhook-token",
       "team_id": "team_001",
       "channel_id": "general",
       "user_id": "john_doe",
       "user_name": "John Doe",
       "text": "Hello AI assistant, how are you?",
       "post_id": "post_123456",
       "timestamp": 1677123456000
     }'
   ```

3. **响应验证**
   - 验证 HTTP 200 响应
   - 验证响应体格式
   - 检查响应时间 < 200ms

4. **事件验证**
   - 连接 Redis 检查事件流
   - 验证事件数据格式
   - 确认事件时间戳正确

5. **日志验证**
   - 检查应用日志记录
   - 验证 Loki 日志聚合
   - 确认无错误日志

**预期结果**:
- Webhook 请求成功处理
- 事件正确发布到 `user_message_raw` 流
- 日志完整记录处理过程
- 系统性能指标正常

#### E2E-002: 空消息处理流程
**目标**: 验证空消息的正确处理

**测试步骤**:
1. 发送空消息 webhook
2. 验证返回 "ignored" 状态
3. 确认无事件发布到事件流
4. 检查日志记录处理决策

#### E2E-003: 无效数据处理流程
**目标**: 验证无效数据的错误处理

**测试步骤**:
1. 发送格式错误的 webhook
2. 验证错误响应
3. 确认错误日志记录
4. 验证系统稳定性

### 2. 负载测试场景

#### E2E-101: 并发请求处理
**目标**: 验证系统在并发负载下的表现

**测试配置**:
```yaml
负载参数:
  并发用户: 50
  请求总数: 1000
  持续时间: 60秒
  请求间隔: 随机 1-5秒
```

**性能指标**:
- 成功率 > 99%
- 平均响应时间 < 500ms
- P99 响应时间 < 1000ms
- 无内存泄漏
- 无连接超时

#### E2E-102: 长时间运行稳定性测试
**目标**: 验证系统长时间运行的稳定性

**测试配置**:
```yaml
稳定性测试:
  运行时间: 24小时
  请求频率: 10 requests/minute
  监控指标: CPU, Memory, Network, Disk
  告警阈值:
    CPU: > 80%
    Memory: > 1GB
    响应时间: > 1000ms
```

### 3. 故障恢复场景

#### E2E-201: Redis 服务中断恢复测试
**目标**: 验证 Redis 服务中断后的系统恢复能力

**测试步骤**:
1. **正常运行阶段**
   - 发送正常 webhook 请求
   - 验证系统正常工作

2. **故障模拟阶段**
   - 停止 Redis 服务
   - 发送 webhook 请求
   - 验证错误响应和日志

3. **服务恢复阶段**
   - 重启 Redis 服务
   - 发送 webhook 请求
   - 验证系统自动恢复

4. **数据一致性验证**
   - 检查事件数据完整性
   - 验证无数据丢失

#### E2E-202: 服务重启恢复测试
**目标**: 验证输入服务重启后的恢复能力

**测试步骤**:
1. 正常运行并发送请求
2. 重启输入服务
3. 立即发送请求验证恢复
4. 检查日志和数据一致性

### 4. 安全测试场景

#### E2E-301: 输入验证安全测试
**目标**: 验证系统对恶意输入的防护

**测试用例**:
```json
{
  "sql_injection": {
    "text": "'; DROP TABLE users; --"
  },
  "xss_attempt": {
    "text": "<script>alert('XSS')</script>"
  },
  "large_payload": {
    "text": "A" * 1000000
  },
  "special_characters": {
    "text": "测试中文 🚀 Special chars: !@#$%^&*()"
  }
}
```

#### E2E-302: 限流和防护测试
**目标**: 验证系统的限流和防护机制

**测试步骤**:
1. 快速连续发送大量请求
2. 验证限流机制生效
3. 检查系统稳定性
4. 验证正常请求不受影响

## 测试自动化

### 测试框架
```python
# e2e_test_framework.py
import pytest
import requests
import redis
import time
import docker
from typing import Dict, Any

class E2ETestFramework:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.docker_client = docker.from_env()
    
    def setup_environment(self):
        """设置测试环境"""
        # 启动服务
        self.docker_client.containers.run(
            "docker-compose",
            "up -d",
            remove=True
        )
        
        # 等待服务就绪
        self.wait_for_services()
    
    def cleanup_environment(self):
        """清理测试环境"""
        # 清理数据
        self.redis_client.flushall()
        
        # 停止服务
        self.docker_client.containers.run(
            "docker-compose",
            "down",
            remove=True
        )
    
    def wait_for_services(self, timeout=60):
        """等待服务启动"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 检查输入服务
                health_response = requests.get(f"{self.base_url}/health")
                if health_response.status_code == 200:
                    # 检查 Redis
                    self.redis_client.ping()
                    return True
            except:
                time.sleep(2)
        
        raise TimeoutError("Services failed to start within timeout")
    
    def send_webhook(self, data: Dict[str, Any]) -> requests.Response:
        """发送 webhook 请求"""
        return requests.post(
            f"{self.base_url}/api/v1/webhook/mattermost",
            json=data,
            timeout=10
        )
    
    def verify_event_published(self, stream_name: str, timeout: int = 10) -> bool:
        """验证事件是否发布到流"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = self.redis_client.xread({stream_name: '0'}, count=1)
                if result:
                    return True
            except:
                pass
            time.sleep(0.5)
        return False

# 测试用例示例
@pytest.fixture
def e2e_framework():
    framework = E2ETestFramework()
    framework.setup_environment()
    yield framework
    framework.cleanup_environment()

def test_basic_webhook_flow(e2e_framework):
    """测试基础 webhook 流程"""
    # 准备测试数据
    webhook_data = {
        "token": "test-token",
        "team_id": "team_001",
        "channel_id": "general",
        "user_id": "test_user",
        "text": "Hello, AI assistant!",
        "post_id": "post_123"
    }
    
    # 发送请求
    response = e2e_framework.send_webhook(webhook_data)
    
    # 验证响应
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # 验证事件发布
    assert e2e_framework.verify_event_published("ai-re:user_message_raw")
```

### CI/CD 集成
```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest requests redis docker
    
    - name: Start services
      run: |
        docker-compose -f docker-compose.e2e.yml up -d
        sleep 30  # 等待服务启动
    
    - name: Run E2E tests
      run: |
        python -m pytest tests/e2e/ -v --tb=short
      env:
        SERVICE_URL: http://localhost:8000
        REDIS_HOST: localhost
    
    - name: Cleanup
      if: always()
      run: |
        docker-compose -f docker-compose.e2e.yml down -v
```

## 性能基准和监控

### 性能基准定义
```yaml
性能基准:
  响应时间:
    webhook_处理: 
      平均: < 200ms
      P95: < 500ms
      P99: < 1000ms
    
  吞吐量:
    并发请求: > 100 req/sec
    事件发布: > 1000 events/sec
  
  资源使用:
    内存: < 512MB
    CPU: < 50%
    磁盘IO: < 100MB/s
  
  可用性:
    正常运行时间: > 99.9%
    错误率: < 0.1%
```

### 监控仪表板
```json
{
  "dashboard": {
    "title": "E2E Test Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          "rate(webhook_requests_total[5m])"
        ]
      },
      {
        "title": "Response Time",
        "type": "graph", 
        "targets": [
          "histogram_quantile(0.95, webhook_response_time_histogram)"
        ]
      },
      {
        "title": "Error Rate",
        "type": "stat",
        "targets": [
          "rate(webhook_errors_total[5m])"
        ]
      }
    ]
  }
}
```

## 测试数据管理

### 测试数据生成
```python
# test_data_generator.py
import json
import random
import time
from faker import Faker

fake = Faker(['en_US', 'zh_CN'])

class TestDataGenerator:
    @staticmethod
    def generate_webhook_data(count: int = 1) -> list:
        """生成测试 webhook 数据"""
        data = []
        for i in range(count):
            webhook = {
                "token": f"test-token-{i}",
                "team_id": f"team_{random.randint(1, 10)}",
                "channel_id": fake.word(),
                "user_id": fake.user_name(),
                "user_name": fake.name(),
                "text": fake.text(max_nb_chars=200),
                "post_id": f"post_{int(time.time())}_{i}",
                "timestamp": int(time.time() * 1000)
            }
            data.append(webhook)
        return data
```

## 最佳实践

### 测试设计原则
1. **独立性**: 每个测试用例独立，不依赖其他测试
2. **幂等性**: 测试可以重复执行，结果一致
3. **完整性**: 覆盖完整的业务流程
4. **现实性**: 模拟真实的使用场景
5. **可维护性**: 测试代码易于理解和维护

### 环境管理
1. **容器化**: 使用 Docker 确保环境一致性
2. **版本控制**: 测试环境配置版本化管理
3. **快速重置**: 支持快速清理和重置
4. **数据隔离**: 测试数据与生产数据隔离
5. **资源监控**: 监控测试环境资源使用

### 故障排查
1. **详细日志**: 记录详细的测试执行日志
2. **断点调试**: 支持测试用例断点调试
3. **环境快照**: 保存失败时的环境状态
4. **分层诊断**: 从网络、服务、数据层面诊断
5. **自动重试**: 对临时性故障自动重试

## 总结

端到端测试是验证 AI-RE 系统整体功能和性能的重要手段。通过全面的 E2E 测试：

1. **保证质量**: 确保系统在真实环境中正确工作
2. **提升信心**: 为产品发布提供质量保证
3. **发现问题**: 及早发现集成和配置问题
4. **优化性能**: 通过性能测试优化系统表现
5. **持续改进**: 建立持续的质量反馈循环

建议将 E2E 测试纳入 CI/CD 流程，定期执行，并根据业务发展持续完善测试用例和测试环境。 