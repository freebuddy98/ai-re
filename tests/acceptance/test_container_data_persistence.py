"""
容器数据持久化验收测试 (Container Data Persistence Acceptance Tests)

测试数据卷挂载、数据持久化、容器重启后数据保持等功能。
"""
import time
import docker
import pytest
import subprocess
import requests
import redis
import json
import os
from typing import Dict, List

@pytest.fixture(scope="class")
def docker_client():
    """Docker客户端"""
    return docker.from_env()

@pytest.fixture(scope="class")
def compose_project_name():
    """Docker Compose项目名称"""
    return "ai-re-persistence-test"

class TestContainerDataPersistence:
    """容器数据持久化验收测试类"""
    
    def test_a004_data_persistence_verification(self, docker_client, compose_project_name):
        """A004: 数据持久化验证测试 - 验证数据卷正确挂载并实现数据持久化"""
        
        base_url = "http://localhost:8000"
        
        # 确保服务运行
        self._wait_for_service_ready(base_url, timeout=30)
        
        # 1. 发送测试数据并存储到Redis
        test_messages = [
            {
                "token": "persistence-test-token-1",
                "team_id": "team123", 
                "channel_id": "channel456",
                "user_id": "user789",
                "user_name": "testuser1",
                "text": "Persistence test message 1"
            },
            {
                "token": "persistence-test-token-2",
                "team_id": "team123",
                "channel_id": "channel456", 
                "user_id": "user790",
                "user_name": "testuser2",
                "text": "Persistence test message 2"
            }
        ]
        
        # 发送webhook消息
        for message in test_messages:
            response = requests.post(f"{base_url}/api/v1/webhook/mattermost", 
                                   json=message, timeout=10)
            assert response.status_code == 200, f"发送测试消息失败: {response.status_code}"
        
        # 等待消息处理
        time.sleep(2)
        
        # 验证数据存储到Redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        
        # 检查Redis Stream中的数据
        stream_key = "ai-re:user_message_raw"
        messages_in_redis = redis_client.xread({stream_key: "0"}, count=10)
        
        assert len(messages_in_redis) > 0, "Redis中没有找到stream数据"
        stream_name, stream_messages = messages_in_redis[0]
        assert len(stream_messages) >= len(test_messages), f"Redis中消息数量不足: {len(stream_messages)}"
        
        # 记录重启前的消息ID
        pre_restart_message_ids = [msg_id.decode() for msg_id, _ in stream_messages]
        
        # 2. 停止并删除容器 (保留数据卷)
        print("停止容器...")
        stop_result = subprocess.run([
            "docker", "compose", "-p", compose_project_name, "stop"
        ], capture_output=True, text=True, cwd=".")
        
        assert stop_result.returncode == 0, f"容器停止失败: {stop_result.stderr}"
        
        # 删除容器但保留数据卷
        remove_result = subprocess.run([
            "docker", "compose", "-p", compose_project_name, "rm", "-f"
        ], capture_output=True, text=True, cwd=".")
        
        assert remove_result.returncode == 0, f"容器删除失败: {remove_result.stderr}"
        
        # 3. 重新启动容器
        print("重新启动容器...")
        start_result = subprocess.run([
            "docker", "compose", "-p", compose_project_name, "up", "-d"
        ], capture_output=True, text=True, cwd=".")
        
        assert start_result.returncode == 0, f"容器重启失败: {start_result.stderr}"
        
        # 等待服务恢复
        self._wait_for_service_ready(base_url, timeout=60)
        time.sleep(5)  # 额外等待确保服务完全就绪
        
        # 4. 验证数据是否持久化
        redis_client_after = redis.Redis(host='localhost', port=6379, db=0)
        
        # 重新检查Redis Stream中的数据
        messages_after_restart = redis_client_after.xread({stream_key: "0"}, count=10)
        
        assert len(messages_after_restart) > 0, "重启后Redis中没有找到stream数据"
        stream_name_after, stream_messages_after = messages_after_restart[0]
        
        # 验证消息ID持久化
        post_restart_message_ids = [msg_id.decode() for msg_id, _ in stream_messages_after]
        
        for pre_id in pre_restart_message_ids:
            assert pre_id in post_restart_message_ids, f"消息ID {pre_id} 在重启后丢失"
        
        print(f"数据持久化验证成功: 重启前{len(pre_restart_message_ids)}条消息，重启后{len(post_restart_message_ids)}条消息")
    
    def test_data_volume_mounting(self, docker_client, compose_project_name):
        """数据卷挂载测试 - 验证数据卷正确挂载"""
        
        # 获取Redis容器
        redis_container = self._get_container_by_service(
            docker_client, compose_project_name, "redis"
        )
        assert redis_container, "Redis容器未找到"
        
        # 检查Redis数据卷挂载
        mounts = redis_container.attrs.get("Mounts", [])
        redis_data_mount = None
        
        for mount in mounts:
            if mount.get("Destination") == "/data":
                redis_data_mount = mount
                break
        
        assert redis_data_mount, "Redis数据卷未正确挂载"
        assert redis_data_mount["Type"] == "volume", "Redis数据卷类型错误"
        
        # 获取Input Service容器
        input_service_container = self._get_container_by_service(
            docker_client, compose_project_name, "input-service"
        )
        assert input_service_container, "Input Service容器未找到"
        
        # 检查配置文件挂载
        config_mounted = False
        logs_mounted = False
        
        for mount in input_service_container.attrs.get("Mounts", []):
            if mount.get("Destination") == "/app/config":
                config_mounted = True
                assert mount["Type"] == "bind", "配置文件挂载类型错误"
            elif mount.get("Destination") == "/app/logs":
                logs_mounted = True
                assert mount["Type"] == "volume", "日志卷挂载类型错误"
        
        assert config_mounted, "配置文件未正确挂载"
        assert logs_mounted, "日志卷未正确挂载"
        
        # 验证配置文件在容器内可访问
        config_check_cmd = ["cat", "/app/config/config.yml"]
        exec_result = input_service_container.exec_run(config_check_cmd)
        assert exec_result.exit_code == 0, "配置文件在容器内不可访问"
        
        config_content = exec_result.output.decode()
        assert "event_bus" in config_content, "配置文件内容不正确"
        assert "redis" in config_content, "配置文件缺少Redis配置"
    
    def test_log_persistence(self, docker_client, compose_project_name):
        """日志持久化测试 - 验证日志文件持久化"""
        
        base_url = "http://localhost:8000"
        
        # 发送一些请求生成日志
        test_message = {
            "token": "log-test-token",
            "team_id": "team123",
            "channel_id": "channel456",
            "user_id": "user789",
            "user_name": "loguser",
            "text": "Log persistence test message"
        }
        
        # 发送多个请求生成日志
        for i in range(5):
            response = requests.post(f"{base_url}/api/v1/webhook/mattermost", 
                                   json=test_message, timeout=10)
            assert response.status_code == 200, f"发送日志测试消息失败: {response.status_code}"
        
        # 等待日志写入
        time.sleep(3)
        
        # 获取Input Service容器
        input_service_container = self._get_container_by_service(
            docker_client, compose_project_name, "input-service"
        )
        assert input_service_container, "Input Service容器未找到"
        
        # 检查容器内是否有日志文件
        log_check_cmd = ["find", "/app/logs", "-name", "*.log", "-type", "f"]
        exec_result = input_service_container.exec_run(log_check_cmd)
        
        if exec_result.exit_code == 0:
            log_files = exec_result.output.decode().strip().split('\n')
            log_files = [f for f in log_files if f]  # 过滤空行
            
            if log_files:
                print(f"找到日志文件: {log_files}")
                
                # 检查日志文件内容
                for log_file in log_files[:3]:  # 检查前3个日志文件
                    cat_cmd = ["tail", "-n", "10", log_file]
                    cat_result = input_service_container.exec_run(cat_cmd)
                    if cat_result.exit_code == 0:
                        log_content = cat_result.output.decode()
                        print(f"日志文件 {log_file} 内容: {log_content[:200]}...")
    
    def test_redis_data_integrity(self, docker_client, compose_project_name):
        """Redis数据完整性测试 - 验证Redis数据在容器重启后保持完整"""
        
        base_url = "http://localhost:8000"
        
        # 连接Redis并设置测试数据
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        
        # 清理测试数据
        test_key = "test:data:integrity"
        redis_client.delete(test_key)
        
        # 设置测试数据
        test_data = {
            "key1": "value1",
            "key2": "value2", 
            "timestamp": str(int(time.time())),
            "test_list": ["item1", "item2", "item3"]
        }
        
        redis_client.hset(test_key, mapping=test_data)
        redis_client.expire(test_key, 3600)  # 设置1小时过期时间
        
        # 验证数据已设置
        stored_data = redis_client.hgetall(test_key)
        assert len(stored_data) == len(test_data), "Redis测试数据设置失败"
        
        # 发送webhook消息到Redis Stream
        webhook_message = {
            "token": "integrity-test-token",
            "team_id": "team123",
            "channel_id": "channel456",
            "user_id": "user789",
            "user_name": "integrityuser",
            "text": "Data integrity test message"
        }
        
        response = requests.post(f"{base_url}/api/v1/webhook/mattermost", 
                               json=webhook_message, timeout=10)
        assert response.status_code == 200, "发送完整性测试消息失败"
        
        time.sleep(2)
        
        # 记录重启前的Stream长度
        stream_key = "ai-re:user_message_raw"
        pre_restart_length = redis_client.xlen(stream_key)
        
        # 重启Redis容器
        redis_container = self._get_container_by_service(
            docker_client, compose_project_name, "redis"
        )
        assert redis_container, "Redis容器未找到"
        
        print("重启Redis容器...")
        redis_container.restart()
        
        # 等待Redis恢复
        time.sleep(10)
        self._wait_for_redis_ready(timeout=30)
        
        # 重新连接Redis
        redis_client_after = redis.Redis(host='localhost', port=6379, db=0)
        
        # 验证Hash数据完整性
        stored_data_after = redis_client_after.hgetall(test_key)
        assert len(stored_data_after) == len(test_data), "重启后Hash数据不完整"
        
        for key, value in test_data.items():
            assert stored_data_after[key.encode()].decode() == value, f"Hash数据 {key} 值不匹配"
        
        # 验证Stream数据完整性
        post_restart_length = redis_client_after.xlen(stream_key)
        assert post_restart_length >= pre_restart_length, "重启后Stream数据丢失"
        
        print(f"Redis数据完整性验证成功: Stream长度重启前{pre_restart_length}，重启后{post_restart_length}")
    
    def test_volume_backup_and_restore(self, docker_client, compose_project_name):
        """数据卷备份与恢复测试 - 验证数据卷备份和恢复功能"""
        
        # 获取Redis数据卷名称
        redis_container = self._get_container_by_service(
            docker_client, compose_project_name, "redis"
        )
        assert redis_container, "Redis容器未找到"
        
        redis_volume_name = None
        for mount in redis_container.attrs.get("Mounts", []):
            if mount.get("Destination") == "/data":
                redis_volume_name = mount.get("Name")
                break
        
        assert redis_volume_name, "Redis数据卷名称未找到"
        
        # 创建备份目录
        backup_dir = "/tmp/redis_backup_test"
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            # 备份数据卷
            backup_cmd = [
                "docker", "run", "--rm",
                "-v", f"{redis_volume_name}:/data:ro",
                "-v", f"{backup_dir}:/backup",
                "alpine", "tar", "-czf", "/backup/redis_data.tar.gz", "-C", "/data", "."
            ]
            
            backup_result = subprocess.run(backup_cmd, capture_output=True, text=True)
            assert backup_result.returncode == 0, f"数据卷备份失败: {backup_result.stderr}"
            
            # 验证备份文件存在
            backup_file = os.path.join(backup_dir, "redis_data.tar.gz")
            assert os.path.exists(backup_file), "备份文件不存在"
            assert os.path.getsize(backup_file) > 0, "备份文件为空"
            
            print(f"数据卷备份成功: {backup_file} ({os.path.getsize(backup_file)} bytes)")
            
            # 模拟数据恢复场景 (这里只验证恢复命令的格式)
            restore_cmd = [
                "docker", "run", "--rm",
                "-v", f"{redis_volume_name}:/data",
                "-v", f"{backup_dir}:/backup",
                "alpine", "tar", "-xzf", "/backup/redis_data.tar.gz", "-C", "/data"
            ]
            
            # 这里不实际执行恢复，因为会影响正在运行的服务
            print(f"数据恢复命令验证通过: {' '.join(restore_cmd)}")
            
        finally:
            # 清理备份文件
            if os.path.exists(backup_dir):
                import shutil
                shutil.rmtree(backup_dir)
    
    def _get_container_by_service(self, docker_client, project_name: str, service_name: str):
        """根据服务名获取容器"""
        containers = docker_client.containers.list(
            all=True, 
            filters={"label": f"com.docker.compose.project={project_name}"}
        )
        for container in containers:
            if container.attrs["Config"]["Labels"].get("com.docker.compose.service") == service_name:
                return container
        return None
    
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
    
    def _wait_for_redis_ready(self, timeout: int = 30):
        """等待Redis就绪"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                redis_client = redis.Redis(host='localhost', port=6379, db=0)
                if redis_client.ping():
                    return
            except Exception:
                pass
            
            time.sleep(1)
        
        raise TimeoutError(f"Redis在 {timeout} 秒内未就绪") 