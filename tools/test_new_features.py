#!/usr/bin/env python3
"""
测试新功能脚本

测试:
1. 基于时间戳的Redis流key
2. 紧凑的对话历史显示
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.interactive_dialogue_simulator import DialogueSimulator

def test_compact_history_display():
    """测试紧凑的对话历史显示"""
    print("🧪 测试紧凑对话历史显示功能")
    print("=" * 50)
    
    simulator = DialogueSimulator()
    simulator.start_new_conversation()
    
    # 添加一些测试消息
    test_messages = [
        ("client", "我需要开发一个用户管理系统"),
        ("analyst", "好的，您希望这个系统具备哪些基本功能呢？"),
        ("client", "需要用户注册、登录、密码重置、个人资料管理等功能"),
        ("analyst", "明白了。您期望支持多少并发用户？"),
        ("client", "预计最多1000个并发用户"),
        ("analyst", "好的。关于用户注册，您希望支持哪些注册方式？"),
        ("client", "支持邮箱注册和手机号注册两种方式"),
        ("analyst", "那么关于安全性，您有什么特殊要求吗？"),
    ]
    
    for speaker_type, text in test_messages:
        simulator.add_message_to_conversation(text, speaker_type)
    
    print(f"添加了 {len(test_messages)} 条测试消息\n")
    
    # 测试显示最近5轮对话
    print("显示最近5轮对话:")
    simulator.display_recent_conversation(5)
    
    # 测试显示所有对话
    print("显示完整对话历史:")
    simulator.display_conversation_history()

def test_timestamped_stream_key():
    """测试基于时间戳的Redis流key"""
    print("\n🧪 测试基于时间戳的Redis流key")
    print("=" * 50)
    
    # 检查环境
    simulator = DialogueSimulator()
    
    if not simulator.check_environment():
        print("❌ 环境检查失败，跳过Redis流测试")
        return
    
    if not simulator.initialize_event_bus():
        print("❌ 事件总线初始化失败，跳过Redis流测试")
        return
    
    print("✅ 环境检查通过")
    print(f"当前流前缀: {simulator.event_bus.topic_prefix}")
    
    # 创建测试事件
    test_event = simulator.create_user_message_raw_event(
        "这是一个测试消息，用于验证新的时间戳流key功能", 
        "client"
    )
    
    print(f"创建的测试事件:")
    print(f"  - 用户ID: {test_event['user_id']}")
    print(f"  - 频道ID: {test_event['channel_id']}")
    print(f"  - 文本: {test_event['content']['text']}")
    
    # 发送事件
    success = simulator.send_event_to_bus(test_event)
    if success:
        print("✅ 事件发送成功")
        
        # 检查Redis流
        import time
        time.sleep(1)  # 等待一下确保消息写入
        
        try:
            import subprocess
            result = subprocess.run(
                ['python', 'tools/session_manager.py', 'streams'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                print("当前Redis流状态:")
                print(result.stdout)
            else:
                print(f"查看流状态失败: {result.stderr}")
                
        except Exception as e:
            print(f"检查Redis流时出错: {e}")
    else:
        print("❌ 事件发送失败")

def main():
    """主函数"""
    print("🎯 AI-RE 新功能测试")
    print("=" * 60)
    
    # 测试1: 紧凑对话历史显示
    test_compact_history_display()
    
    # 测试2: 时间戳Redis流key
    test_timestamped_stream_key()
    
    print("\n🎉 所有测试完成！")

if __name__ == "__main__":
    main() 