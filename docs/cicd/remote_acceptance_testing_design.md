# Remote CI/CD Acceptance Testing Design

## Overview

This document outlines the technical design for implementing remote acceptance testing in CI/CD pipelines, focusing on container image generation and functional testing for the AI-RE project.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Developer     │    │   Git Repository│    │  Remote CI/CD   │
│   Workstation   │───▶│   (GitHub/     │───▶│   Server        │
│                 │    │    GitLab)      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                               ┌─────────────────────────────────────┐
                               │         CI/CD Pipeline             │
                               │                                     │
                               │  ┌─────────────┐ ┌─────────────┐   │
                               │  │   Build     │ │   Test      │   │
                               │  │   Images    │ │   Suite     │   │
                               │  └─────────────┘ └─────────────┘   │
                               │                                     │
                               │  ┌─────────────┐ ┌─────────────┐   │
                               │  │   Deploy    │ │   Report    │   │
                               │  │   & Test    │ │   Results   │   │
                               │  └─────────────┘ └─────────────┘   │
                               └─────────────────────────────────────┘
                                                       │
                                                       ▼
                               ┌─────────────────────────────────────┐
                               │     Container Registry             │
                               │   (Docker Hub / ECR / GCR)         │
                               └─────────────────────────────────────┘
```

## 1. CI/CD Platform Options

### Option A: GitHub Actions (Recommended)
**Advantages:**
- Native integration with GitHub repositories
- Rich ecosystem of actions and workflows
- Built-in secrets management
- Matrix builds for multi-environment testing
- Good container support

**Implementation:**
```yaml
# .github/workflows/acceptance-tests.yml
name: Remote Acceptance Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        environment: [staging, production]
        
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Build container images
        run: |
          docker build -t ai-re/input-service:${{ github.sha }} \
            -f services/input-service/Dockerfile .
          docker build -t ai-re/test-runner:${{ github.sha }} \
            -f docker/test-runner/Dockerfile .
            
      - name: Run acceptance tests
        run: |
          docker-compose -f docker/acceptance-test-compose.yml up \
            --abort-on-container-exit --exit-code-from test-runner
            
      - name: Publish test results
        uses: dorny/test-reporter@v1
        if: always()
        with:
          name: 'Acceptance Tests (${{ matrix.environment }})'
          path: 'test-results/acceptance-*.xml'
          reporter: jest-junit
```

### Option B: GitLab CI/CD
**Advantages:**
- Integrated container registry
- Powerful pipeline features
- Good Kubernetes integration
- Built-in monitoring and observability

### Option C: Jenkins
**Advantages:**
- Highly customizable
- Rich plugin ecosystem
- Self-hosted option
- Advanced pipeline scripting

## 2. Container Image Strategy

### 2.1 Multi-Stage Build Strategy

```dockerfile
# docker/Dockerfile.acceptance-test
# Multi-stage build for optimized test images

# Stage 1: Base runtime image
FROM python:3.10-slim as base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Application image
FROM base as app
COPY . .
RUN pip install -e .

# Stage 3: Test image
FROM app as test
COPY tests/requirements.txt tests/
RUN pip install --no-cache-dir -r tests/requirements.txt
COPY tests/ tests/
COPY scripts/ scripts/

# Stage 4: Acceptance test runner
FROM test as acceptance-test
ENV PYTHONPATH=/app
ENV TEST_ENVIRONMENT=ci
ENV SKIP_UNIT_TESTS=true
ENV SKIP_INTEGRATION_TESTS=true
CMD ["python", "-m", "pytest", "tests/acceptance/", "-v", "--junitxml=/app/test-results/acceptance.xml"]
```

### 2.2 Test Environment Composition

```yaml
# docker/acceptance-test-compose.yml
version: '3.8'

services:
  redis:
    image: redis:6.2-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  loki:
    image: grafana/loki:2.8.0
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:3100/ready || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  input-service:
    build:
      context: .
      dockerfile: services/input-service/Dockerfile
      target: production
    ports:
      - "8001:8001"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - LOKI_URL=http://loki:3100/loki/api/v1/push
      - LOKI_ENABLED=true
    depends_on:
      redis:
        condition: service_healthy
      loki:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 10s
      timeout: 5s
      retries: 10

  test-runner:
    build:
      context: .
      dockerfile: docker/Dockerfile.acceptance-test
      target: acceptance-test
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - SERVICE_URL=http://input-service:8001
      - LOKI_URL=http://loki:3100/loki/api/v1/push
      - TEST_ENVIRONMENT=ci
      - CI=true
    volumes:
      - ./test-results:/app/test-results
    depends_on:
      input-service:
        condition: service_healthy
    command: >
      sh -c "
        echo 'Starting acceptance tests...' &&
        python -m pytest tests/acceptance/ -v 
          --junitxml=/app/test-results/acceptance.xml 
          --html=/app/test-results/acceptance.html 
          --self-contained-html 
          --tb=short
      "

  # Performance monitoring container
  monitoring:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./docker/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

volumes:
  test-results:
```

## 3. Test Execution Strategy

### 3.1 Test Categories and Execution Order

```bash
#!/bin/bash
# scripts/run_ci_acceptance_tests.sh

set -e

echo "=== AI-RE Remote Acceptance Testing ==="

# Test execution phases
PHASES=(
    "orchestration:A001,A002,A003"
    "performance:A007"
    "persistence:A004,A005"
    "monitoring:A008,A009"
    "lifecycle:A006,A010"
)

# Execute tests in phases
for phase in "${PHASES[@]}"; do
    phase_name=$(echo $phase | cut -d: -f1)
    test_ids=$(echo $phase | cut -d: -f2)
    
    echo "--- Phase: $phase_name ---"
    echo "Tests: $test_ids"
    
    # Run specific acceptance tests
    docker-compose -f docker/acceptance-test-compose.yml \
        run --rm test-runner \
        python -m pytest tests/acceptance/ \
        -k "$(echo $test_ids | tr ',' ' or ')" \
        -v --tb=short \
        --junitxml=/app/test-results/acceptance-${phase_name}.xml
        
    if [ $? -ne 0 ]; then
        echo "❌ Phase $phase_name failed"
        exit 1
    fi
    
    echo "✅ Phase $phase_name completed successfully"
done

echo "🎉 All acceptance tests completed successfully!"
```

### 3.2 Parallel Test Execution

```yaml
# .github/workflows/parallel-acceptance-tests.yml
name: Parallel Acceptance Tests

on:
  push:
    branches: [main]

jobs:
  build-images:
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.build.outputs.tag }}
    steps:
      - uses: actions/checkout@v4
      - name: Build and push images
        id: build
        run: |
          TAG=${{ github.sha }}
          echo "tag=$TAG" >> $GITHUB_OUTPUT
          docker build -t ghcr.io/${{ github.repository }}/ai-re:$TAG .
          docker push ghcr.io/${{ github.repository }}/ai-re:$TAG

  acceptance-tests:
    needs: build-images
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        test-suite:
          - orchestration
          - performance
          - persistence
          - monitoring
          - lifecycle
    steps:
      - uses: actions/checkout@v4
      - name: Run ${{ matrix.test-suite }} tests
        run: |
          docker-compose -f docker/acceptance-test-compose.yml \
            run --rm test-runner \
            ./scripts/run_container_acceptance_tests.sh --${{ matrix.test-suite }}
      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results-${{ matrix.test-suite }}
          path: test-results/
```

## 4. Environment Management

### 4.1 Environment-Specific Configurations

```yaml
# config/environments/ci.yml
environment: ci

# Override Redis connection for CI
event_bus:
  redis:
    host: "redis"
    port: 6379
    db: 0
    password: ""

# CI-specific logging
logging:
  level: "DEBUG"
  enable_loki: true
  loki_url: "http://loki:3100/loki/api/v1/push"

# Performance testing limits for CI
performance:
  max_concurrent_requests: 50
  test_duration: 30
  acceptable_response_time: 1000ms
  
# Test data configuration
test_data:
  cleanup_after_test: true
  use_persistent_volumes: false
```

### 4.2 Secrets Management

```yaml
# GitHub Secrets Configuration
secrets:
  DOCKER_REGISTRY_TOKEN: "ghp_xxxxxxxxxxxxxxxxxxxx"
  REDIS_PASSWORD: "secure_redis_password"
  MONITORING_TOKEN: "monitoring_access_token"
  SLACK_WEBHOOK_URL: "https://hooks.slack.com/services/..."
  
# In workflow
env:
  DOCKER_REGISTRY_TOKEN: ${{ secrets.DOCKER_REGISTRY_TOKEN }}
  REDIS_PASSWORD: ${{ secrets.REDIS_PASSWORD }}
```

## 5. Monitoring and Observability

### 5.1 Test Metrics Collection

```python
# tests/acceptance/utils/metrics_collector.py
import time
import psutil
import requests
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class TestMetrics:
    test_name: str
    duration: float
    memory_usage: float
    cpu_usage: float
    network_io: Dict[str, int]
    success_rate: float
    error_count: int

class MetricsCollector:
    def __init__(self):
        self.metrics: List[TestMetrics] = []
        
    def collect_system_metrics(self) -> Dict[str, float]:
        """Collect system resource metrics"""
        return {
            'memory_percent': psutil.virtual_memory().percent,
            'cpu_percent': psutil.cpu_percent(interval=1),
            'disk_usage': psutil.disk_usage('/').percent,
        }
        
    def collect_application_metrics(self, service_url: str) -> Dict[str, float]:
        """Collect application-specific metrics"""
        try:
            health_response = requests.get(f"{service_url}/health", timeout=5)
            metrics_response = requests.get(f"{service_url}/metrics", timeout=5)
            
            return {
                'response_time': health_response.elapsed.total_seconds(),
                'status_code': health_response.status_code,
                'active_connections': self._parse_connection_count(metrics_response.text)
            }
        except Exception as e:
            return {'error': str(e)}
            
    def export_to_prometheus(self, metrics: Dict[str, float]):
        """Export metrics to Prometheus format"""
        with open('/tmp/test_metrics.prom', 'w') as f:
            for key, value in metrics.items():
                f.write(f'ai_re_test_{key} {value}\n')
```

### 5.2 Alerting and Notifications

```yaml
# .github/workflows/acceptance-tests-with-notifications.yml
jobs:
  notify-start:
    runs-on: ubuntu-latest
    steps:
      - name: Notify test start
        uses: 8398a7/action-slack@v3
        with:
          status: custom
          custom_payload: |
            {
              "text": "🔄 Acceptance tests started",
              "attachments": [{
                "color": "warning",
                "fields": [{
                  "title": "Branch",
                  "value": "${{ github.ref_name }}",
                  "short": true
                }, {
                  "title": "Commit",
                  "value": "${{ github.sha }}",
                  "short": true
                }]
              }]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}

  acceptance-tests:
    needs: notify-start
    # ... test execution ...
    
  notify-results:
    needs: acceptance-tests
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Notify test results
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          fields: repo,message,commit,author,action,eventName,ref,workflow
          custom_payload: |
            {
              "text": "${{ job.status == 'success' && '✅ Acceptance tests passed' || '❌ Acceptance tests failed' }}",
              "attachments": [{
                "color": "${{ job.status == 'success' && 'good' || 'danger' }}",
                "fields": [{
                  "title": "Test Results",
                  "value": "View detailed results in GitHub Actions",
                  "short": false
                }]
              }]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

## 6. Performance Testing Integration

### 6.1 Load Testing in CI

```python
# tests/acceptance/performance/load_test_ci.py
import asyncio
import aiohttp
import time
from typing import List, Dict

class CILoadTester:
    def __init__(self, base_url: str, max_concurrent: int = 50):
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        
    async def run_load_test(self, duration: int = 30) -> Dict[str, float]:
        """Run load test suitable for CI environment"""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        start_time = time.time()
        results = []
        
        async def make_request(session: aiohttp.ClientSession):
            async with semaphore:
                start = time.time()
                try:
                    async with session.post(
                        f"{self.base_url}/api/v1/webhook/mattermost",
                        json=self._generate_test_payload()
                    ) as response:
                        duration = time.time() - start
                        results.append({
                            'status': response.status,
                            'duration': duration,
                            'success': response.status == 200
                        })
                except Exception as e:
                    results.append({
                        'status': 0,
                        'duration': time.time() - start,
                        'success': False,
                        'error': str(e)
                    })
        
        # Run requests for specified duration
        async with aiohttp.ClientSession() as session:
            tasks = []
            while time.time() - start_time < duration:
                task = asyncio.create_task(make_request(session))
                tasks.append(task)
                await asyncio.sleep(0.1)  # 10 RPS rate limit for CI
            
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return self._analyze_results(results)
        
    def _analyze_results(self, results: List[Dict]) -> Dict[str, float]:
        """Analyze load test results"""
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r['success'])
        
        response_times = [r['duration'] for r in results]
        response_times.sort()
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'success_rate': (successful_requests / total_requests) * 100,
            'avg_response_time': sum(response_times) / len(response_times),
            'p95_response_time': response_times[int(len(response_times) * 0.95)],
            'p99_response_time': response_times[int(len(response_times) * 0.99)],
        }
```

## 7. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Set up basic CI/CD pipeline
- [ ] Create container build strategy
- [ ] Implement basic acceptance test execution
- [ ] Set up test result reporting

### Phase 2: Enhancement (Week 3-4)
- [ ] Add parallel test execution
- [ ] Implement monitoring and metrics collection
- [ ] Set up notifications and alerting
- [ ] Add performance testing integration

### Phase 3: Advanced Features (Week 5-6)
- [ ] Implement blue-green deployment testing
- [ ] Add security scanning integration
- [ ] Set up canary deployment testing
- [ ] Optimize for cost and performance

### Phase 4: Production Readiness (Week 7-8)
- [ ] Full documentation and runbooks
- [ ] Disaster recovery procedures
- [ ] Performance tuning and optimization
- [ ] Team training and handover

## Conclusion

This comprehensive design provides a robust, scalable, and cost-effective solution for remote acceptance testing in CI/CD pipelines. The architecture supports:

- **Scalability**: Parallel test execution and matrix builds
- **Reliability**: Comprehensive monitoring and alerting
- **Security**: Integrated security scanning and testing
- **Cost-effectiveness**: Resource optimization and caching
- **Maintainability**: Clear documentation and modular design

The implementation follows industry best practices and provides a solid foundation for continuous integration and deployment of the AI-RE system. 