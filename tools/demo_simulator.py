#!/usr/bin/env python3
"""
Demo script for the Interactive Dialogue Simulator

This script demonstrates how to use the DialogueSimulator programmatically
for automated testing or demo purposes.
"""

import sys
import os
import time

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.interactive_dialogue_simulator import DialogueSimulator


def demo_environment_check():
    """Demonstrate environment checking capabilities"""
    print("🎬 Demo: Environment Check")
    print("=" * 50)
    
    simulator = DialogueSimulator()
    result = simulator.check_environment()
    
    if result:
        print("✅ Environment check passed!")
    else:
        print("❌ Environment check failed!")
    
    return result


def demo_conversation_creation():
    """Demonstrate conversation creation and event formatting"""
    print("\n🎬 Demo: Conversation Creation")
    print("=" * 50)
    
    simulator = DialogueSimulator()
    simulator.start_new_conversation()
    
    # Simulate some messages
    client_message = "我们需要一个电商网站，用户可以浏览商品、加入购物车、下单支付。"
    analyst_message = "好的，这是一个典型的电商系统。请问您预计有多少用户同时在线？对性能有什么要求？"
    
    # Add messages to conversation
    simulator.add_message_to_conversation(client_message, 'client')
    simulator.add_message_to_conversation(analyst_message, 'analyst')
    
    # Show conversation history
    simulator.display_conversation_history()
    
    # Create and show event format for client message
    print("\n📨 Client Message Event Format:")
    print("-" * 40)
    event = simulator.create_user_message_raw_event(client_message, 'client')
    
    import json
    print(json.dumps(event, indent=2, ensure_ascii=False))
    
    return simulator


def demo_conversation_save_load():
    """Demonstrate saving and loading conversations"""
    print("\n🎬 Demo: Save/Load Conversations")
    print("=" * 50)
    
    simulator = demo_conversation_creation()
    
    # Save conversation
    conversation_name = "demo_ecommerce_system"
    success = simulator.save_conversation(conversation_name)
    
    if success:
        print(f"✅ Conversation saved as '{conversation_name}'")
    
    # Create new simulator and load conversation
    new_simulator = DialogueSimulator()
    load_success = new_simulator.load_conversation(conversation_name)
    
    if load_success:
        print(f"✅ Conversation '{conversation_name}' loaded successfully")
        print("\n📖 Loaded conversation:")
        new_simulator.display_conversation_history()
    
    return new_simulator


def demo_event_bus_integration():
    """Demonstrate event bus integration"""
    print("\n🎬 Demo: Event Bus Integration")
    print("=" * 50)
    
    simulator = DialogueSimulator()
    
    # Initialize event bus
    if simulator.initialize_event_bus():
        print("✅ Event bus initialized successfully")
        
        # Create a test message
        test_message = "系统需要支持多语言，包括中文、英文和日文。"
        event_data = simulator.create_user_message_raw_event(test_message, 'client')
        
        print(f"\n📝 Test message: {test_message}")
        print("🚀 Sending to event bus...")
        
        # Send event (this would actually send to Redis/event bus)
        success = simulator.send_event_to_bus(event_data)
        
        if success:
            print("✅ Event sent successfully!")
            print("   This message is now available for NLU service processing")
        else:
            print("❌ Failed to send event")
    else:
        print("❌ Failed to initialize event bus")


def demo_existing_conversations():
    """Demonstrate listing and loading existing conversations"""
    print("\n🎬 Demo: Existing Conversations")
    print("=" * 50)
    
    simulator = DialogueSimulator()
    conversations = simulator.list_existing_conversations()
    
    print(f"📋 Found {len(conversations)} existing conversations:")
    for i, conv in enumerate(conversations, 1):
        print(f"  {i}. {conv}")
    
    # Try to load the example conversation
    if "example_login_system" in conversations:
        print(f"\n📖 Loading example conversation...")
        success = simulator.load_conversation("example_login_system")
        if success:
            simulator.display_conversation_history()


def main():
    """Run all demos"""
    print("🎭 Interactive Dialogue Simulator - Demo")
    print("=" * 60)
    print("This demo shows the capabilities of the dialogue simulator.")
    print("All operations are performed programmatically.\n")
    
    try:
        # Demo 1: Environment check
        env_ok = demo_environment_check()
        
        if env_ok:
            # Demo 2: Event bus integration
            demo_event_bus_integration()
        
        # Demo 3: Conversation creation
        demo_conversation_creation()
        
        # Demo 4: Save/Load functionality
        demo_conversation_save_load()
        
        # Demo 5: Existing conversations
        demo_existing_conversations()
        
        print("\n🎉 Demo completed successfully!")
        print("\nTo run the interactive simulator, use:")
        print("python tools/interactive_dialogue_simulator.py")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 