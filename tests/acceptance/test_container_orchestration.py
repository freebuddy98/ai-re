"""
容器编排验收测试 (Container Orchestration Acceptance Tests)

测试Docker Compose服务编排、容器启动顺序、健康检查等关键功能。
"""
import time
import docker
import pytest
import subprocess
import requests
from typing import Dict, List
import json
import os

@pytest.fixture(scope="class")
def docker_client():
    """Docker客户端"""
    return docker.from_env()

@pytest.fixture(scope="class")
def compose_project_name():
    """Docker Compose项目名称"""
    return "ai-re-test"

class TestContainerOrchestration:
    """容器编排验收测试类"""
    
    def test_a001_container_startup_and_health_checks(self, docker_client, compose_project_name):
        """A001: 容器编排启动测试 - 验证所有容器能够按正确顺序启动并达到健康状态"""
        
        # 清理现有容器
        self._cleanup_containers(compose_project_name)
        
        # 启动Docker Compose服务
        result = subprocess.run([
            "docker", "compose", "-p", compose_project_name, "up", "-d"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 0, f"Docker Compose启动失败: {result.stderr}"
        
        # 等待服务启动
        time.sleep(10)
        
        # 验证容器状态
        containers = self._get_project_containers(docker_client, compose_project_name)
        
        # 验证所有期望的容器都在运行
        expected_services = ["redis", "loki", "input-service"]
        running_services = [c.name.split('_')[-1] for c in containers if c.status == "running"]
        
        for service in expected_services:
            assert any(service in name for name in running_services), f"服务 {service} 未运行"
        
        # 等待健康检查
        self._wait_for_health_checks(docker_client, compose_project_name, timeout=60)
        
        # 验证健康检查状态
        for container in containers:
            if "input-service" in container.name:
                # Input Service应该有健康检查
                container.reload()
                health = container.attrs.get("State", {}).get("Health", {})
                assert health.get("Status") == "healthy", f"Input Service健康检查失败: {health}"
            elif "redis" in container.name:
                # Redis应该有健康检查
                container.reload()
                health = container.attrs.get("State", {}).get("Health", {})
                assert health.get("Status") == "healthy", f"Redis健康检查失败: {health}"
    
    def test_a002_inter_service_network_communication(self, docker_client, compose_project_name):
        """A002: 服务间网络通信测试 - 验证容器间网络通信正常工作"""
        
        # 获取Input Service容器
        input_service_container = self._get_container_by_service(
            docker_client, compose_project_name, "input-service"
        )
        assert input_service_container, "Input Service容器未找到"
        
        # 测试Redis连接
        redis_test_cmd = ["python", "-c", 
                         "import redis; r=redis.Redis(host='redis', port=6379); print(r.ping())"]
        
        exec_result = input_service_container.exec_run(redis_test_cmd)
        assert exec_result.exit_code == 0, f"Redis连接测试失败: {exec_result.output.decode()}"
        assert b"True" in exec_result.output, "Redis ping测试失败"
        
        # 测试Loki连接 (简单的TCP连接测试)
        loki_test_cmd = ["python", "-c", 
                        "import socket; s=socket.socket(); s.settimeout(5); s.connect(('loki', 3100)); s.close(); print('OK')"]
        
        exec_result = input_service_container.exec_run(loki_test_cmd)
        assert exec_result.exit_code == 0, f"Loki连接测试失败: {exec_result.output.decode()}"
        assert b"OK" in exec_result.output, "Loki连接测试失败"
        
        # 测试DNS解析
        dns_test_cmd = ["python", "-c", 
                       "import socket; print(socket.gethostbyname('redis')); print(socket.gethostbyname('loki'))"]
        
        exec_result = input_service_container.exec_run(dns_test_cmd)
        assert exec_result.exit_code == 0, f"DNS解析测试失败: {exec_result.output.decode()}"
    
    def test_a003_api_endpoint_container_access(self, compose_project_name):
        """A003: API端点容器访问测试 - 验证外部可以通过映射端口访问容器化服务"""
        
        base_url = "http://localhost:8000"
        
        # 等待服务完全启动
        self._wait_for_service_ready(base_url, timeout=30)
        
        # 测试健康检查端点
        response = requests.get(f"{base_url}/health", timeout=10)
        assert response.status_code == 200, f"健康检查端点返回错误状态码: {response.status_code}"
        
        health_data = response.json()
        assert health_data.get("status") == "ok", f"健康检查状态异常: {health_data}"
        assert "redis" in health_data, "健康检查响应缺少Redis状态"
        
        # 测试Loki状态端点
        response = requests.get(f"{base_url}/loki-status", timeout=10)
        assert response.status_code == 200, f"Loki状态端点返回错误状态码: {response.status_code}"
        
        # 测试Webhook端点
        webhook_data = {
            "token": "test-token",
            "team_id": "team123",
            "channel_id": "channel456",
            "user_id": "user789",
            "user_name": "testuser",
            "text": "Container test message"
        }
        
        start_time = time.time()
        response = requests.post(f"{base_url}/api/v1/webhook/mattermost", 
                               json=webhook_data, timeout=10)
        response_time = time.time() - start_time
        
        assert response.status_code == 200, f"Webhook端点返回错误状态码: {response.status_code}"
        assert response_time < 2.0, f"响应时间过长: {response_time:.3f}s"
    
    def test_a005_environment_variable_configuration(self, docker_client, compose_project_name):
        """A005: 环境变量配置验证测试 - 验证环境变量在容器中正确设置和应用"""
        
        # 获取Input Service容器
        input_service_container = self._get_container_by_service(
            docker_client, compose_project_name, "input-service"
        )
        assert input_service_container, "Input Service容器未找到"
        
        # 检查环境变量
        expected_env_vars = {
            "REDIS_HOST": "redis",
            "CONFIG_PATH": "/app/config/config.yml",
            "LOKI_URL": "http://loki:3100/loki/api/v1/push",
            "LOKI_ENABLED": "true",
            "SERVICE_NAME": "input-service"
        }
        
        # 获取容器环境变量
        container_env = {}
        for env_var in input_service_container.attrs["Config"]["Env"]:
            if "=" in env_var:
                key, value = env_var.split("=", 1)
                container_env[key] = value
        
        # 验证每个环境变量
        for key, expected_value in expected_env_vars.items():
            assert key in container_env, f"环境变量 {key} 未设置"
            assert container_env[key] == expected_value, \
                f"环境变量 {key} 值错误: 期望 {expected_value}, 实际 {container_env[key]}"
        
        # 验证配置文件存在
        config_check_cmd = ["ls", "-la", "/app/config/config.yml"]
        exec_result = input_service_container.exec_run(config_check_cmd)
        assert exec_result.exit_code == 0, "配置文件不存在"
    
    def test_a006_container_health_check_and_auto_recovery(self, docker_client, compose_project_name):
        """A006: 容器健康检查与自动恢复测试 - 验证容器健康检查机制和自动重启功能"""
        
        # 获取Input Service容器
        input_service_container = self._get_container_by_service(
            docker_client, compose_project_name, "input-service"
        )
        assert input_service_container, "Input Service容器未找到"
        
        # 检查健康检查配置
        health_config = input_service_container.attrs.get("Config", {}).get("Healthcheck", {})
        assert health_config, "Input Service缺少健康检查配置"
        
        # 验证健康检查间隔 (Docker使用纳秒)
        expected_interval = 10 * 1000000000  # 10秒
        actual_interval = health_config.get("Interval", 0)
        assert actual_interval == expected_interval, \
            f"健康检查间隔配置错误: 期望 {expected_interval}, 实际 {actual_interval}"
        
        # 获取Redis容器并检查健康检查
        redis_container = self._get_container_by_service(
            docker_client, compose_project_name, "redis"
        )
        assert redis_container, "Redis容器未找到"
        
        redis_health_config = redis_container.attrs.get("Config", {}).get("Healthcheck", {})
        assert redis_health_config, "Redis缺少健康检查配置"
        
        # 验证当前健康状态
        input_service_container.reload()
        health_status = input_service_container.attrs.get("State", {}).get("Health", {}).get("Status")
        assert health_status == "healthy", f"Input Service健康状态异常: {health_status}"
        
        redis_container.reload()
        redis_health_status = redis_container.attrs.get("State", {}).get("Health", {}).get("Status")
        assert redis_health_status == "healthy", f"Redis健康状态异常: {redis_health_status}"
    
    def test_a010_container_complete_lifecycle(self, docker_client, compose_project_name):
        """A010: 容器完整生命周期测试 - 验证容器的完整生命周期管理"""
        
        # 1. 验证当前所有服务都在运行
        containers = self._get_project_containers(docker_client, compose_project_name)
        running_containers = [c for c in containers if c.status == "running"]
        assert len(running_containers) >= 3, "期望至少3个容器在运行"
        
        # 2. 运行完整业务流程 - 发送webhook请求
        base_url = "http://localhost:8000"
        webhook_data = {
            "token": "lifecycle-test-token",
            "team_id": "team123",
            "channel_id": "channel456",
            "user_id": "user789",
            "user_name": "testuser",
            "text": "Lifecycle test message"
        }
        
        response = requests.post(f"{base_url}/api/v1/webhook/mattermost", 
                               json=webhook_data, timeout=10)
        assert response.status_code == 200, "业务流程测试失败"
        
        # 3. 优雅停止服务
        stop_result = subprocess.run([
            "docker", "compose", "-p", compose_project_name, "stop"
        ], capture_output=True, text=True, cwd=".")
        
        assert stop_result.returncode == 0, f"服务停止失败: {stop_result.stderr}"
        
        # 4. 验证所有容器已停止
        time.sleep(5)
        containers = self._get_project_containers(docker_client, compose_project_name)
        running_containers = [c for c in containers if c.status == "running"]
        assert len(running_containers) == 0, "存在未停止的容器"
        
        # 5. 重新启动服务
        start_result = subprocess.run([
            "docker", "compose", "-p", compose_project_name, "up", "-d"
        ], capture_output=True, text=True, cwd=".")
        
        assert start_result.returncode == 0, f"服务重启失败: {start_result.stderr}"
        
        # 6. 等待服务恢复并验证
        time.sleep(10)
        self._wait_for_health_checks(docker_client, compose_project_name, timeout=60)
        
        # 验证服务重新可用
        self._wait_for_service_ready(base_url, timeout=30)
        response = requests.get(f"{base_url}/health", timeout=10)
        assert response.status_code == 200, "重启后服务不可用"
    
    def _cleanup_containers(self, project_name: str):
        """清理测试容器"""
        subprocess.run([
            "docker", "compose", "-p", project_name, "down", "-v"
        ], capture_output=True, cwd=".")
    
    def _get_project_containers(self, docker_client, project_name: str) -> List:
        """获取项目相关的容器"""
        return docker_client.containers.list(
            all=True, 
            filters={"label": f"com.docker.compose.project={project_name}"}
        )
    
    def _get_container_by_service(self, docker_client, project_name: str, service_name: str):
        """根据服务名获取容器"""
        containers = self._get_project_containers(docker_client, project_name)
        for container in containers:
            if container.attrs["Config"]["Labels"].get("com.docker.compose.service") == service_name:
                return container
        return None
    
    def _wait_for_health_checks(self, docker_client, project_name: str, timeout: int = 60):
        """等待健康检查通过"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            containers = self._get_project_containers(docker_client, project_name)
            all_healthy = True
            
            for container in containers:
                if container.status != "running":
                    all_healthy = False
                    break
                
                container.reload()
                health_config = container.attrs.get("Config", {}).get("Healthcheck")
                if health_config:  # 只检查有健康检查配置的容器
                    health_status = container.attrs.get("State", {}).get("Health", {}).get("Status")
                    if health_status != "healthy":
                        all_healthy = False
                        break
            
            if all_healthy:
                return
            
            time.sleep(2)
        
        raise TimeoutError(f"健康检查在 {timeout} 秒内未通过")
    
    def _wait_for_service_ready(self, base_url: str, timeout: int = 30):
        """等待服务就绪"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    return
            except (requests.RequestException, ConnectionError):
                pass
            
            time.sleep(1)
        
        raise TimeoutError(f"服务在 {timeout} 秒内未就绪")

    @classmethod
    def teardown_class(cls):
        """测试类清理"""
        # 确保测试结束后清理容器
        subprocess.run([
            "docker", "compose", "-p", "ai-re-test", "down", "-v"
        ], capture_output=True, cwd=".") 