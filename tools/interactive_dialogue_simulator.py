#!/usr/bin/env python3
"""
Interactive Dialogue Simulator

This script provides an interactive, wizard-style simulation environment for:
1. Multi-turn dialogue between client and requirements analyst
2. Loading existing conversations or starting new ones
3. Sending user_message_raw events to the event bus
4. Environment checks to ensure Redis server is running

Usage:
    python tools/interactive_dialogue_simulator.py
    
Input Formats:
    客户: <message>     - Client message (sent to event bus)
    分析师: <message>   - Analyst message (stored locally)
    C: <message>       - Client message (short form)
    A: <message>       - Analyst message (short form)
    > <message>        - Client message (symbol form)
    < <message>        - Analyst message (symbol form)
    
Special Commands:
    quit              - Exit the dialogue
    history           - Show full conversation history
    save <name>       - Save conversation with given name
    help              - Show input format help
"""

import os
import sys
import json
import uuid
import time
import redis
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, UTC
from pathlib import Path

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from event_bus_framework import create_event_bus, get_service_config
    from event_bus_framework.core.interfaces import IEventBus
except ImportError as e:
    print(f"Error importing event bus framework: {e}")
    print("Please ensure you're running from the project root and the event bus framework is installed.")
    sys.exit(1)


class DialogueSimulator:
    """Interactive dialogue simulator with event bus integration"""
    
    def __init__(self):
        self.event_bus: Optional[IEventBus] = None
        self.conversations_dir = Path("tools/conversations")
        self.conversations_dir.mkdir(exist_ok=True)
        self.current_conversation: List[Dict[str, Any]] = []
        self.current_session_id: str = ""
        self.current_channel_id: str = ""
        
    def check_environment(self) -> bool:
        """Check if Redis server is running and accessible"""
        print("🔍 Checking environment...")
        
        # First check if Redis is running via Docker
        if self._check_redis_docker():
            return True
        
        # Then check if Redis is running locally
        if self._check_redis_local():
            return True
        
        # If neither worked, try to start Redis via Docker
        print("⚠️ Redis not found, attempting to start via Docker...")
        if self._start_redis_docker():
            return True
        
        print("❌ Could not start or connect to Redis")
        print("Please ensure Redis is running either:")
        print("  1. Via Docker: docker run -d -p 6379:6379 redis:alpine")
        print("  2. Locally: sudo systemctl start redis-server")
        print("  3. Via docker-compose: docker-compose up -d redis")
        return False
    
    def _check_redis_docker(self) -> bool:
        """Check if Redis is running in Docker container"""
        try:
            import subprocess
            result = subprocess.run(['docker', 'ps', '--filter', 'ancestor=redis', '--format', '{{.Names}}'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                print("📦 Found Redis running in Docker container")
                # Try to connect to it
                redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
                redis_client.ping()
                print("✅ Redis Docker container is accessible")
                return True
        except subprocess.TimeoutExpired:
            print("⏰ Docker command timed out")
        except subprocess.CalledProcessError:
            print("🔍 Docker not available or no Redis containers found")
        except redis.ConnectionError:
            print("📦 Redis container found but not accessible on localhost:6379")
        except Exception as e:
            print(f"🔍 Error checking Docker Redis: {e}")
        
        return False
    
    def _check_redis_local(self) -> bool:
        """Check if Redis is running locally"""
        try:
            redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            redis_client.ping()
            print("✅ Local Redis server is running and accessible")
            return True
        except redis.ConnectionError:
            print("🔍 Local Redis server not accessible")
        except Exception as e:
            print(f"🔍 Error checking local Redis: {e}")
        
        return False
    
    def _start_redis_docker(self) -> bool:
        """Attempt to start Redis via Docker"""
        try:
            import subprocess
            print("🚀 Starting Redis container...")
            
            # Check if docker is available
            result = subprocess.run(['docker', '--version'], capture_output=True, timeout=5)
            if result.returncode != 0:
                print("❌ Docker is not available")
                return False
            
            # Start Redis container
            result = subprocess.run([
                'docker', 'run', '-d', 
                '--name', 'redis-dialogue-sim',
                '-p', '6379:6379',
                'redis:alpine'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("🎉 Redis container started successfully")
                # Wait a moment for Redis to start
                time.sleep(2)
                # Test connection
                return self._check_redis_local()
            else:
                # Container might already exist, try to start existing one
                result = subprocess.run([
                    'docker', 'start', 'redis-dialogue-sim'
                ], capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0:
                    print("🎉 Existing Redis container started successfully")
                    time.sleep(2)
                    return self._check_redis_local()
                else:
                    print(f"❌ Failed to start Redis container: {result.stderr}")
                    return False
                    
        except subprocess.TimeoutExpired:
            print("⏰ Docker command timed out")
        except FileNotFoundError:
            print("❌ Docker command not found")
        except Exception as e:
            print(f"❌ Error starting Redis Docker container: {e}")
        
        return False
    
    def initialize_event_bus(self) -> bool:
        """Initialize the event bus connection"""
        try:
            print("🔗 Initializing event bus connection...")
            
            # Load event bus configuration
            event_bus_config = get_service_config('event_bus')
            if not event_bus_config:
                print("❌ No event bus configuration found")
                print("Please ensure config/event_bus.yml exists and is properly configured")
                return False
            
            # Modify Redis host for local development if needed
            redis_config = event_bus_config.get('redis', {})
            if redis_config.get('host') == 'redis':
                # For local development, connect to localhost instead of container name
                redis_config = redis_config.copy()
                redis_config['host'] = 'localhost'
                event_bus_config = event_bus_config.copy()
                event_bus_config['redis'] = redis_config
            
            # Create event bus
            self.event_bus = create_event_bus(
                config=event_bus_config,
                service_name="dialogue_simulator"
            )
            
            print("✅ Event bus initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error initializing event bus: {e}")
            return False
    
    def list_existing_conversations(self) -> List[str]:
        """List all existing conversation files"""
        conversations = []
        for file_path in self.conversations_dir.glob("*.json"):
            conversations.append(file_path.stem)
        return sorted(conversations)
    
    def load_conversation(self, conversation_name: str) -> bool:
        """Load an existing conversation"""
        try:
            file_path = self.conversations_dir / f"{conversation_name}.json"
            if not file_path.exists():
                print(f"❌ Conversation '{conversation_name}' not found")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.current_conversation = data.get('messages', [])
                self.current_session_id = data.get('session_id', str(uuid.uuid4()))
                self.current_channel_id = data.get('channel_id', f"ecommerce_dev")
            
            print(f"✅ Loaded conversation '{conversation_name}' with {len(self.current_conversation)} messages")
            return True
            
        except Exception as e:
            print(f"❌ Error loading conversation: {e}")
            return False
    
    def save_conversation(self, conversation_name: str) -> bool:
        """Save the current conversation"""
        try:
            file_path = self.conversations_dir / f"{conversation_name}.json"
            data = {
                'session_id': self.current_session_id,
                'channel_id': self.current_channel_id,
                'created_at': datetime.now(UTC).isoformat(),
                'messages': self.current_conversation
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Conversation saved as '{conversation_name}'")
            return True
            
        except Exception as e:
            print(f"❌ Error saving conversation: {e}")
            return False
    
    def start_new_conversation(self):
        """Start a new conversation"""
        self.current_conversation = []
        self.current_session_id = str(uuid.uuid4())
        self.current_channel_id = f"ecommerce_dev"
        print(f"🆕 Started new conversation")
        print(f"   Session ID: {self.current_session_id}")
        print(f"   Channel ID: {self.current_channel_id}")
    
    def display_conversation_history(self):
        """Display the current conversation history"""
        if not self.current_conversation:
            print("📝 No messages in current conversation")
            return
        
        print("\n📝 Conversation History:")
        print("=" * 60)
        for i, msg in enumerate(self.current_conversation, 1):
            speaker = "👤 客户" if msg['speaker_type'] == 'client' else "🤖 需求分析师"
            timestamp = msg.get('timestamp', 'Unknown time')
            text = msg.get('text', '')
            print(f"{i:2d}. [{timestamp}] {speaker}")
            print(f"    {text}")
            print()
    
    def display_recent_conversation(self, count: int = 5):
        """Display recent conversation turns in compact format"""
        if not self.current_conversation:
            return
        
        recent_messages = self.current_conversation[-count:] if len(self.current_conversation) > count else self.current_conversation
        
        if recent_messages:
            print(f"\n📝 最近 {len(recent_messages)} 轮对话:")
            print("-" * 50)
            for i, msg in enumerate(recent_messages, len(self.current_conversation) - len(recent_messages) + 1):
                speaker_icon = "👤" if msg['speaker_type'] == 'client' else "🤖"
                speaker_name = "客户" if msg['speaker_type'] == 'client' else "分析师"
                text = msg.get('text', '')
                
                # 截断长文本
                if len(text) > 80:
                    text = text[:77] + "..."
                
                print(f"{i:2d}. {speaker_icon} {speaker_name}: {text}")
            print()
    
    def show_input_help(self):
        """Show help for input formats"""
        print("\n💡 输入格式帮助:")
        print("=" * 50)
        print("🧑‍💼 客户消息 (会发送到事件总线):")
        print("   客户: <消息内容>")
        print("   C: <消息内容>")
        print("   > <消息内容>")
        print()
        print("🤖 需求分析师消息 (仅保存到本地):")
        print("   分析师: <消息内容>")
        print("   A: <消息内容>")
        print("   < <消息内容>")
        print()
        print("🔧 特殊命令:")
        print("   quit           - 退出对话")
        print("   history        - 显示完整对话历史")
        print("   save <名称>    - 保存对话")
        print("   help           - 显示此帮助")
        print("=" * 50)
    
    def parse_input_message(self, user_input: str) -> Optional[Tuple[str, str]]:
        """
        Parse user input to extract speaker type and message
        Returns: (speaker_type, message) or None if invalid/special command
        """
        user_input = user_input.strip()
        
        # Handle special commands
        if user_input.lower() == 'quit':
            return None
        elif user_input.lower() == 'history':
            self.display_conversation_history()
            return self.parse_input_message(input("\n💬 请输入消息: "))
        elif user_input.lower().startswith('save '):
            name = user_input[5:].strip()
            if name:
                self.save_conversation(name)
            else:
                print("❌ 请提供保存名称，例如: save 对话1")
            return self.parse_input_message(input("\n💬 请输入消息: "))
        elif user_input.lower() == 'help':
            self.show_input_help()
            return self.parse_input_message(input("\n💬 请输入消息: "))
        
        # Parse message with prefixes
        if user_input.startswith('客户:') or user_input.startswith('客户：'):
            message = user_input[3:].strip()
            return ('client', message) if message else None
        elif user_input.startswith('分析师:') or user_input.startswith('分析师：'):
            message = user_input[4:].strip()
            return ('analyst', message) if message else None
        elif user_input.startswith('C:') or user_input.startswith('C：'):
            message = user_input[2:].strip()
            return ('client', message) if message else None
        elif user_input.startswith('A:') or user_input.startswith('A：'):
            message = user_input[2:].strip()
            return ('analyst', message) if message else None
        elif user_input.startswith('> '):
            message = user_input[2:].strip()
            return ('client', message) if message else None
        elif user_input.startswith('< '):
            message = user_input[2:].strip()
            return ('analyst', message) if message else None
        else:
            print("❌ 无效输入格式！请使用以下格式之一:")
            print("   客户: <消息>  或  C: <消息>  或  > <消息>")
            print("   分析师: <消息>  或  A: <消息>  或  < <消息>")
            print("   输入 'help' 查看详细帮助")
            return self.parse_input_message(input("\n💬 请输入消息: "))
    
    def create_user_message_raw_event(self, text: str, speaker_type: str) -> Dict[str, Any]:
        """Create a user_message_raw event following the events.yml schema"""
        # For client messages, we send to event bus; for analyst messages, we just store
        timestamp_ms = int(time.time() * 1000)
        
        return {
            "meta": {
                "event_id": str(uuid.uuid4()),
                "source": "dialogue_simulator",
                "timestamp": timestamp_ms
            },
            "user_id": f"{speaker_type}_user_{int(time.time())}",
            "username": "客户" if speaker_type == 'client' else "需求分析师",
            "platform": "dialogue_simulator",
            "channel_id": self.current_channel_id,
            "content": {
                "text": text,
                "attachments": None
            },
            "raw_data": {
                "speaker_type": speaker_type,
                "session_id": self.current_session_id
            }
        }
    
    def send_event_to_bus(self, event_data: Dict[str, Any]) -> bool:
        """Send user_message_raw event to the event bus"""
        try:
            if not self.event_bus:
                print("❌ Event bus not initialized")
                return False
            
            topic = "user_message_raw"
            message_id = self.event_bus.publish(topic, event_data)
            
            if message_id:
                print(f"✅ Event sent to bus with ID: {message_id}")
                return True
            else:
                print("❌ Failed to send event to bus")
                return False
                
        except Exception as e:
            print(f"❌ Error sending event to bus: {e}")
            return False
    
    def add_message_to_conversation(self, text: str, speaker_type: str):
        """Add a message to the current conversation"""
        message = {
            "timestamp": datetime.now(UTC).isoformat(),
            "speaker_type": speaker_type,
            "text": text,
            "event_sent": speaker_type == 'client'  # Only client messages are sent as events
        }
        self.current_conversation.append(message)
    
    def choose_conversation_mode(self) -> str:
        """Let user choose between new conversation or loading existing one"""
        existing_conversations = self.list_existing_conversations()
        
        print("\n📋 选择对话模式:")
        print("1. 开始新对话")
        
        if existing_conversations:
            print("2. 继续已有对话")
            print("\n已有对话:")
            for i, conv in enumerate(existing_conversations, 1):
                print(f"   {i}. {conv}")
        
        while True:
            choice = input("\n请选择 (1 开始新对话, 2 继续已有对话): ").strip()
            
            if choice == '1':
                return 'new'
            elif choice == '2' and existing_conversations:
                return 'existing'
            else:
                print("❌ 无效选择")
    
    def choose_existing_conversation(self) -> Optional[str]:
        """Let user choose from existing conversations"""
        existing_conversations = self.list_existing_conversations()
        
        if not existing_conversations:
            print("❌ 没有已有对话")
            return None
        
        print("\n选择要继续的对话:")
        for i, conv in enumerate(existing_conversations, 1):
            print(f"{i}. {conv}")
        
        while True:
            try:
                choice = input(f"请输入编号 (1-{len(existing_conversations)}): ").strip()
                index = int(choice) - 1
                
                if 0 <= index < len(existing_conversations):
                    return existing_conversations[index]
                else:
                    print(f"❌ 请输入 1 到 {len(existing_conversations)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效数字")
    
    def run_dialogue_loop(self):
        """Main dialogue loop"""
        print("\n🎯 开始对话仿真...")
        print("输入格式: 客户: <消息> 或 分析师: <消息> (输入 'help' 查看详细帮助)")
        print("客户消息将作为 user_message_raw 事件发送到事件总线")
        print("需求分析师消息仅保存到对话历史中")
        
        while True:
            # Get user input with new streamlined format
            user_input = input("\n💬 请输入消息: ").strip()
            
            # Parse the input
            result = self.parse_input_message(user_input)
            if result is None:  # User chose to quit or invalid input was handled
                break
            
            speaker_type, text = result
            
            # Add to conversation history
            self.add_message_to_conversation(text, speaker_type)
            
            # If it's a client message, send as event to bus
            if speaker_type == 'client':
                event_data = self.create_user_message_raw_event(text, speaker_type)
                success = self.send_event_to_bus(event_data)
                if success:
                    print("📨 客户消息已发送到事件总线，等待 NLU 服务处理...")
                else:
                    print("⚠️ 客户消息发送失败，但已保存到对话历史")
            else:
                print("📝 需求分析师消息已保存到对话历史")
            
            # Display recent conversation after each message
            self.display_recent_conversation(3)
            
            print(f"📊 当前对话包含 {len(self.current_conversation)} 条消息")
    
    def run(self):
        """Main entry point"""
        print("🎭 交互式对话仿真器")
        print("=" * 50)
        
        # Environment check
        if not self.check_environment():
            return
        
        # Initialize event bus
        if not self.initialize_event_bus():
            return
        
        # Choose conversation mode
        mode = self.choose_conversation_mode()
        
        if mode == 'new':
            self.start_new_conversation()
        elif mode == 'existing':
            conv_name = self.choose_existing_conversation()
            if conv_name and not self.load_conversation(conv_name):
                print("切换到新对话模式")
                self.start_new_conversation()
        
        # Display current conversation if any
        if self.current_conversation:
            self.display_conversation_history()
        
        # Show input help
        self.show_input_help()
        
        # Run main dialogue loop
        self.run_dialogue_loop()
        
        # Save conversation on exit
        if self.current_conversation:
            save_choice = input("\n💾 是否保存当前对话? (y/n): ").strip().lower()
            if save_choice == 'y':
                name = input("请输入对话名称: ").strip()
                if name:
                    self.save_conversation(name)
        
        print("\n👋 对话仿真结束！")


def main():
    """Main function"""
    try:
        simulator = DialogueSimulator()
        simulator.run()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断，程序退出")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 