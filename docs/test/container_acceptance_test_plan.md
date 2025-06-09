# 容器化验收测试计划 (Container-Based Acceptance Test Plan)

## 概述 (Overview)

本文档定义了AI-RE系统的容器化验收测试计划，确保系统在Docker容器环境中的正确运行、服务间通信、容器编排、网络连接、数据持久化等关键功能。

## 测试目标 (Test Objectives)

1. **容器启动与健康检查**: 验证所有服务容器能正确启动并通过健康检查
2. **服务间通信**: 验证容器间网络通信和服务发现
3. **数据持久化**: 验证数据卷挂载和数据持久化功能
4. **环境配置**: 验证环境变量和配置文件在容器中的正确应用
5. **负载均衡与故障恢复**: 验证容器的自动重启和故障恢复能力
6. **端口映射**: 验证端口暴露和外部访问
7. **日志收集**: 验证Loki日志收集和管理
8. **性能表现**: 验证容器化环境下的性能指标

## 测试环境 (Test Environment)

- **Docker版本**: 20.10+
- **Docker Compose版本**: 2.0+
- **测试网络**: `ai-re-network` (bridge driver)
- **服务端口映射**:
  - Input Service: 8000:8000
  - Redis: 6379:6379
  - Loki: 3100:3100

## 容器服务架构 (Container Service Architecture)

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Input Service  │    │      Redis      │    │      Loki       │
│   (port 8000)  │◄──►│   (port 6379)   │    │   (port 3100)   │
│                 │    │                 │    │                 │
│  - Webhook API  │    │  - Event Store  │    │  - Log Storage  │
│  - Health Check │    │  - Stream Data  │    │  - Log Query    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 验收测试用例 (Acceptance Test Cases)

### A001: 容器编排启动测试 (Container Orchestration Startup Test)

**测试目标**: 验证所有容器服务能够按正确顺序启动并达到健康状态

**测试步骤**:
1. 执行 `docker-compose up -d`
2. 等待所有服务启动
3. 检查容器状态
4. 验证健康检查

**验收标准**:
- 所有容器状态为 `running`
- 所有健康检查通过 (`healthy`)
- Redis容器在5s内响应ping
- Input Service在30s内通过健康检查
- Loki容器成功启动

**测试数据**: 无

**预期结果**: 
```bash
CONTAINER         STATUS              HEALTH
input-service     Up X seconds        healthy
redis             Up X seconds        healthy  
loki              Up X seconds        
```

---

### A002: 服务间网络通信测试 (Inter-Service Network Communication Test)

**测试目标**: 验证容器间网络通信正常工作

**测试步骤**:
1. 从Input Service容器内连接Redis
2. 从Input Service容器内连接Loki
3. 验证网络域名解析
4. 测试端口连通性

**验收标准**:
- Input Service能连接到 `redis:6379`
- Input Service能连接到 `loki:3100`
- DNS解析正常工作
- 网络延迟 < 10ms

**测试数据**: 
- Redis主机: `redis`
- Loki主机: `loki`

**预期结果**: 网络连接成功，服务发现正常

---

### A003: API端点容器访问测试 (API Endpoint Container Access Test)

**测试目标**: 验证外部可以通过映射端口访问容器化服务

**测试步骤**:
1. 从宿主机访问 `http://localhost:8000/health`
2. 从宿主机访问 `http://localhost:8000/loki-status`
3. 发送webhook请求到 `http://localhost:8000/api/v1/webhook/mattermost`
4. 验证响应内容和状态码

**验收标准**:
- 健康检查端点返回200状态码
- Loki状态端点返回200状态码
- Webhook端点能接受和处理请求
- 响应时间 < 2s

**测试数据**:
```json
{
  "token": "test-token",
  "team_id": "team123",
  "channel_id": "channel456",
  "user_id": "user789",
  "user_name": "testuser",
  "text": "Container test message"
}
```

**预期结果**: 所有API端点正常响应

---

### A004: 数据持久化验证测试 (Data Persistence Verification Test)

**测试目标**: 验证数据卷正确挂载并实现数据持久化

**测试步骤**:
1. 发送消息到webhook并存储到Redis
2. 停止并删除containers
3. 重新启动容器
4. 验证数据是否持久化

**验收标准**:
- Redis数据在容器重启后保持
- 日志数据正确挂载到宿主机
- 配置文件正确映射到容器
- 数据卷状态正常

**测试数据**:
- 测试消息数据
- 配置文件路径验证

**预期结果**: 数据持久化成功，重启后数据完整

---

### A005: 环境变量配置验证测试 (Environment Variable Configuration Test)

**测试目标**: 验证环境变量在容器中正确设置和应用

**测试步骤**:
1. 检查Input Service容器内环境变量
2. 验证Redis连接配置
3. 验证Loki连接配置
4. 验证配置文件路径

**验收标准**:
- `REDIS_HOST=redis`
- `CONFIG_PATH=/app/config/config.yml`
- `LOKI_URL=http://loki:3100/loki/api/v1/push`
- `LOKI_ENABLED=true`
- `SERVICE_NAME=input-service`

**测试数据**: 环境变量预期值

**预期结果**: 所有环境变量正确设置并被应用程序使用

---

### A006: 容器健康检查与自动恢复测试 (Container Health Check and Auto-Recovery Test)

**测试目标**: 验证容器健康检查机制和自动重启功能

**测试步骤**:
1. 模拟Input Service健康检查失败
2. 观察容器重启行为
3. 验证Redis健康检查机制
4. 测试依赖关系和启动顺序

**验收标准**:
- 健康检查失败时容器自动重启
- Redis健康检查间隔5s
- Input Service健康检查间隔10s
- 依赖服务启动顺序正确

**测试数据**: 健康检查失败模拟

**预期结果**: 自动恢复机制正常工作

---

### A007: 负载处理容器性能测试 (Load Handling Container Performance Test)

**测试目标**: 验证容器化环境下的并发处理能力

**测试步骤**:
1. 并发发送100个webhook请求
2. 监控容器资源使用
3. 检查响应时间分布
4. 验证错误率

**验收标准**:
- 成功处理率 > 95%
- 平均响应时间 < 500ms
- P99响应时间 < 2s
- 内存使用 < 512MB
- CPU使用 < 80%

**测试数据**: 100个并发webhook请求

**预期结果**: 性能指标满足要求

---

### A008: 日志收集与管理测试 (Log Collection and Management Test)

**测试目标**: 验证Loki日志收集和查询功能

**测试步骤**:
1. 发送webhook请求生成日志
2. 验证日志发送到Loki
3. 查询Loki中的日志
4. 验证日志格式和内容

**验收标准**:
- 日志成功发送到Loki
- 日志格式正确 (JSON)
- 日志包含必要字段 (timestamp, level, message, service)
- 日志查询响应 < 1s

**测试数据**: Webhook请求生成的日志

**预期结果**: 日志收集和查询正常工作

---

### A009: 容器网络隔离测试 (Container Network Isolation Test)

**测试目标**: 验证容器网络隔离和安全性

**测试步骤**:
1. 验证容器只能访问允许的服务
2. 测试网络策略
3. 验证端口访问限制
4. 检查网络配置

**验收标准**:
- 容器间通信限制在ai-re-network内
- 外部只能访问映射的端口
- 内部服务端口不对外暴露
- 网络配置符合安全要求

**测试数据**: 网络访问测试

**预期结果**: 网络隔离正确实施

---

### A010: 容器完整生命周期测试 (Container Complete Lifecycle Test)

**测试目标**: 验证容器的完整生命周期管理

**测试步骤**:
1. 启动所有容器服务
2. 运行完整的业务流程
3. 优雅停止服务
4. 清理容器和资源
5. 重新部署验证

**验收标准**:
- 启动过程无错误
- 业务流程正常运行
- 优雅关闭无数据丢失
- 资源清理完全
- 重新部署成功

**测试数据**: 完整业务流程数据

**预期结果**: 完整生命周期管理正常

---

## 测试执行策略 (Test Execution Strategy)

### 自动化测试执行

```bash
# 1. 准备环境
./scripts/setup_container_test_env.sh

# 2. 运行验收测试
./scripts/run_container_acceptance_tests.sh

# 3. 清理环境
./scripts/cleanup_container_test_env.sh
```

### 测试数据管理

- 使用Docker卷进行测试数据隔离
- 测试间数据清理策略
- 测试数据模板和工厂

### 测试报告

- 容器状态报告
- 性能指标报告
- 日志分析报告
- 资源使用报告

## 故障排查指南 (Troubleshooting Guide)

### 常见问题

1. **容器启动失败**
   - 检查Docker和Docker Compose版本
   - 验证端口占用情况
   - 检查镜像构建是否成功

2. **网络连接问题**
   - 验证网络配置
   - 检查DNS解析
   - 确认防火墙设置

3. **数据持久化问题**
   - 检查卷挂载配置
   - 验证文件权限
   - 确认存储空间

4. **性能问题**
   - 监控资源使用
   - 检查网络延迟
   - 分析日志错误

### 监控指标

- 容器CPU使用率
- 容器内存使用率
- 网络I/O
- 磁盘I/O
- 响应时间
- 错误率

## 验收标准总结 (Acceptance Criteria Summary)

### 必须满足的条件 (Must-Have Criteria)

1. ✅ 所有容器成功启动并通过健康检查
2. ✅ API端点在容器环境中正常工作
3. ✅ 服务间通信无问题
4. ✅ 数据持久化功能正常
5. ✅ 环境配置正确应用
6. ✅ 日志收集和查询正常
7. ✅ 性能指标满足要求
8. ✅ 容器生命周期管理正常

### 建议满足的条件 (Should-Have Criteria)

1. 🔶 自动扩缩容能力
2. 🔶 监控和告警集成
3. 🔶 备份和恢复策略
4. 🔶 安全扫描通过

### 可选满足的条件 (Could-Have Criteria)

1. 🔷 多环境部署支持
2. 🔷 CI/CD流水线集成
3. 🔷 蓝绿部署支持
4. 🔷 服务网格集成

---

**文档版本**: v1.0  
**最后更新**: 2025-06-09  
**负责人**: AI-RE团队 