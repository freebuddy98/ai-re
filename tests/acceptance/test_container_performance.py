"""
容器性能验收测试 (Container Performance Acceptance Tests)

测试容器化环境下的性能表现、资源使用、负载处理能力等。
"""
import time
import docker
import pytest
import requests
import threading
import statistics
from typing import List, Dict
import psutil
import concurrent.futures
import json

@pytest.fixture(scope="class")
def docker_client():
    """Docker客户端"""
    return docker.from_env()

@pytest.fixture(scope="class")
def compose_project_name():
    """Docker Compose项目名称"""
    return "ai-re-perf-test"

class TestContainerPerformance:
    """容器性能验收测试类"""
    
    def test_a007_load_handling_container_performance(self, docker_client, compose_project_name):
        """A007: 负载处理容器性能测试 - 验证容器化环境下的并发处理能力"""
        
        base_url = "http://localhost:8000"
        
        # 确保服务可用
        self._wait_for_service_ready(base_url, timeout=30)
        
        # 获取Input Service容器用于资源监控
        input_service_container = self._get_container_by_service(
            docker_client, compose_project_name, "input-service"
        )
        assert input_service_container, "Input Service容器未找到"
        
        # 准备测试数据
        webhook_data_template = {
            "token": "perf-test-token",
            "team_id": "team123",
            "channel_id": "channel{i}",
            "user_id": "user{i}",
            "user_name": "perfuser{i}",
            "text": "Performance test message {i}"
        }
        
        # 并发测试参数
        num_requests = 100
        max_workers = 20
        
        # 开始资源监控
        resource_monitor = ResourceMonitor(input_service_container)
        resource_monitor.start()
        
        try:
            # 执行负载测试
            start_time = time.time()
            results = self._execute_concurrent_requests(
                base_url, webhook_data_template, num_requests, max_workers
            )
            total_time = time.time() - start_time
            
            # 停止资源监控
            resource_monitor.stop()
            resource_stats = resource_monitor.get_stats()
            
            # 分析结果
            successful_requests = sum(1 for r in results if r['success'])
            failed_requests = len(results) - successful_requests
            success_rate = (successful_requests / len(results)) * 100
            
            response_times = [r['response_time'] for r in results if r['success']]
            avg_response_time = statistics.mean(response_times) if response_times else 0
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 10 else 0
            
            # 性能验收标准
            assert success_rate >= 95.0, f"成功率过低: {success_rate:.2f}% (期望 >= 95%)"
            assert avg_response_time < 0.5, f"平均响应时间过长: {avg_response_time:.3f}s (期望 < 0.5s)"
            assert p99_response_time < 2.0, f"P99响应时间过长: {p99_response_time:.3f}s (期望 < 2.0s)"
            
            # 资源使用验收标准
            max_memory_mb = resource_stats.get('max_memory_mb', 0)
            max_cpu_percent = resource_stats.get('max_cpu_percent', 0)
            
            assert max_memory_mb < 512, f"内存使用过高: {max_memory_mb:.1f}MB (期望 < 512MB)"
            assert max_cpu_percent < 80, f"CPU使用过高: {max_cpu_percent:.1f}% (期望 < 80%)"
            
            # 打印性能报告
            print(f"\n=== 负载测试性能报告 ===")
            print(f"总请求数: {num_requests}")
            print(f"成功请求数: {successful_requests}")
            print(f"失败请求数: {failed_requests}")
            print(f"成功率: {success_rate:.2f}%")
            print(f"总耗时: {total_time:.2f}s")
            print(f"平均响应时间: {avg_response_time:.3f}s")
            print(f"P99响应时间: {p99_response_time:.3f}s")
            print(f"最大内存使用: {max_memory_mb:.1f}MB")
            print(f"最大CPU使用: {max_cpu_percent:.1f}%")
            
        finally:
            resource_monitor.stop()
    
    def test_container_resource_monitoring(self, docker_client, compose_project_name):
        """容器资源监控测试 - 验证容器资源使用监控"""
        
        # 获取所有容器
        containers = self._get_project_containers(docker_client, compose_project_name)
        assert len(containers) >= 3, "期望至少3个容器在运行"
        
        # 监控每个容器的资源使用
        for container in containers:
            if container.status != "running":
                continue
            
            service_name = container.attrs["Config"]["Labels"].get("com.docker.compose.service", "unknown")
            
            # 获取容器统计信息
            stats = container.stats(stream=False)
            
            # 计算内存使用
            memory_usage = stats["memory"]["usage"]
            memory_limit = stats["memory"]["limit"]
            memory_percent = (memory_usage / memory_limit) * 100
            
            # 计算CPU使用 (简化计算)
            cpu_stats = stats["cpu_stats"]
            precpu_stats = stats["precpu_stats"]
            
            cpu_delta = cpu_stats["cpu_usage"]["total_usage"] - precpu_stats["cpu_usage"]["total_usage"]
            system_delta = cpu_stats["system_cpu_usage"] - precpu_stats["system_cpu_usage"]
            cpu_percent = (cpu_delta / system_delta) * len(cpu_stats["cpu_usage"]["percpu_usage"]) * 100
            
            print(f"\n=== {service_name} 容器资源使用 ===")
            print(f"内存使用: {memory_usage / 1024 / 1024:.1f}MB ({memory_percent:.1f}%)")
            print(f"CPU使用: {cpu_percent:.1f}%")
            
            # 资源使用合理性检查
            assert memory_percent < 90, f"{service_name} 内存使用率过高: {memory_percent:.1f}%"
            assert cpu_percent < 95, f"{service_name} CPU使用率过高: {cpu_percent:.1f}%"
    
    def test_container_network_performance(self, docker_client, compose_project_name):
        """容器网络性能测试 - 验证容器间网络通信性能"""
        
        # 获取Input Service容器
        input_service_container = self._get_container_by_service(
            docker_client, compose_project_name, "input-service"
        )
        assert input_service_container, "Input Service容器未找到"
        
        # 测试Redis连接延迟
        redis_latency_results = []
        for i in range(10):
            start_time = time.time()
            
            redis_ping_cmd = ["python", "-c", 
                             "import redis; r=redis.Redis(host='redis', port=6379); r.ping()"]
            
            exec_result = input_service_container.exec_run(redis_ping_cmd)
            latency = time.time() - start_time
            
            assert exec_result.exit_code == 0, f"Redis ping失败: {exec_result.output.decode()}"
            redis_latency_results.append(latency)
        
        avg_redis_latency = statistics.mean(redis_latency_results)
        max_redis_latency = max(redis_latency_results)
        
        print(f"\n=== 网络性能测试结果 ===")
        print(f"Redis平均延迟: {avg_redis_latency*1000:.1f}ms")
        print(f"Redis最大延迟: {max_redis_latency*1000:.1f}ms")
        
        # 网络性能验收标准
        assert avg_redis_latency < 0.01, f"Redis平均延迟过高: {avg_redis_latency*1000:.1f}ms (期望 < 10ms)"
        assert max_redis_latency < 0.05, f"Redis最大延迟过高: {max_redis_latency*1000:.1f}ms (期望 < 50ms)"
    
    def test_container_startup_performance(self, docker_client, compose_project_name):
        """容器启动性能测试 - 验证容器启动时间和就绪时间"""
        
        import subprocess
        
        # 停止所有服务
        subprocess.run([
            "docker-compose", "-p", compose_project_name, "stop"
        ], capture_output=True, text=True, cwd=".")
        
        # 测量启动时间
        start_time = time.time()
        
        # 启动服务
        result = subprocess.run([
            "docker-compose", "-p", compose_project_name, "up", "-d"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 0, f"服务启动失败: {result.stderr}"
        
        # 等待所有容器运行
        containers_ready_time = self._wait_for_containers_running(docker_client, compose_project_name)
        
        # 等待服务就绪
        service_ready_time = self._wait_for_service_ready("http://localhost:8000", timeout=60)
        
        startup_time = containers_ready_time - start_time
        total_ready_time = service_ready_time - start_time
        
        print(f"\n=== 启动性能测试结果 ===")
        print(f"容器启动时间: {startup_time:.1f}s")
        print(f"服务就绪时间: {total_ready_time:.1f}s")
        
        # 启动性能验收标准
        assert startup_time < 30, f"容器启动时间过长: {startup_time:.1f}s (期望 < 30s)"
        assert total_ready_time < 60, f"服务就绪时间过长: {total_ready_time:.1f}s (期望 < 60s)"
    
    def _execute_concurrent_requests(self, base_url: str, data_template: dict, 
                                   num_requests: int, max_workers: int) -> List[Dict]:
        """执行并发请求"""
        results = []
        
        def send_request(request_id: int) -> Dict:
            try:
                # 个性化测试数据
                request_data = {}
                for key, value in data_template.items():
                    if isinstance(value, str) and "{i}" in value:
                        request_data[key] = value.format(i=request_id)
                    else:
                        request_data[key] = value
                
                start_time = time.time()
                response = requests.post(f"{base_url}/api/v1/webhook/mattermost", 
                                       json=request_data, timeout=10)
                response_time = time.time() - start_time
                
                return {
                    'request_id': request_id,
                    'success': response.status_code == 200,
                    'status_code': response.status_code,
                    'response_time': response_time
                }
            except Exception as e:
                return {
                    'request_id': request_id,
                    'success': False,
                    'status_code': 0,
                    'response_time': 0,
                    'error': str(e)
                }
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {executor.submit(send_request, i): i for i in range(num_requests)}
            
            for future in concurrent.futures.as_completed(future_to_id):
                result = future.result()
                results.append(result)
        
        return results
    
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
    
    def _wait_for_containers_running(self, docker_client, project_name: str, timeout: int = 30) -> float:
        """等待所有容器运行并返回就绪时间"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            containers = self._get_project_containers(docker_client, project_name)
            running_containers = [c for c in containers if c.status == "running"]
            
            if len(running_containers) >= 3:  # 期望至少3个容器
                return time.time()
            
            time.sleep(1)
        
        raise TimeoutError(f"容器在 {timeout} 秒内未全部运行")
    
    def _wait_for_service_ready(self, base_url: str, timeout: int = 30) -> float:
        """等待服务就绪并返回就绪时间"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    return time.time()
            except (requests.RequestException, ConnectionError):
                pass
            
            time.sleep(1)
        
        raise TimeoutError(f"服务在 {timeout} 秒内未就绪")


class ResourceMonitor:
    """容器资源监控器"""
    
    def __init__(self, container):
        self.container = container
        self.monitoring = False
        self.stats = []
        self.monitor_thread = None
    
    def start(self):
        """开始监控"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()
    
    def stop(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        if not self.stats:
            return {}
        
        memory_values = [s['memory_mb'] for s in self.stats]
        cpu_values = [s['cpu_percent'] for s in self.stats]
        
        return {
            'max_memory_mb': max(memory_values) if memory_values else 0,
            'avg_memory_mb': statistics.mean(memory_values) if memory_values else 0,
            'max_cpu_percent': max(cpu_values) if cpu_values else 0,
            'avg_cpu_percent': statistics.mean(cpu_values) if cpu_values else 0,
            'sample_count': len(self.stats)
        }
    
    def _monitor_loop(self):
        """监控循环"""
        prev_cpu_stats = None
        prev_system_stats = None
        
        while self.monitoring:
            try:
                stats = self.container.stats(stream=False)
                
                # 计算内存使用
                memory_usage = stats["memory"]["usage"]
                memory_mb = memory_usage / 1024 / 1024
                
                # 计算CPU使用
                cpu_percent = 0
                if prev_cpu_stats and prev_system_stats:
                    cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - prev_cpu_stats
                    system_delta = stats["cpu_stats"]["system_cpu_usage"] - prev_system_stats
                    
                    if system_delta > 0:
                        cpu_percent = (cpu_delta / system_delta) * len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"]) * 100
                
                prev_cpu_stats = stats["cpu_stats"]["cpu_usage"]["total_usage"]
                prev_system_stats = stats["cpu_stats"]["system_cpu_usage"]
                
                self.stats.append({
                    'timestamp': time.time(),
                    'memory_mb': memory_mb,
                    'cpu_percent': cpu_percent
                })
                
                time.sleep(1)  # 每秒采样一次
                
            except Exception as e:
                print(f"资源监控错误: {e}")
                break 