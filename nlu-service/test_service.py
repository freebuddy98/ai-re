#!/usr/bin/env python3
"""
NLU Service Test Script

Simple script to test that the NLU service can be imported and configured correctly.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all imports work correctly"""
    try:
        from nlu_service import NLUProcessor, NLUService, main
        print("✓ Successfully imported NLU service components")
        return True
    except ImportError as e:
        print(f"✗ Failed to import NLU service components: {e}")
        return False

def test_configuration():
    """Test that configuration can be loaded"""
    try:
        from nlu_service.config import NLUServiceConfig, load_config_from_env
        
        # Test default configuration
        config = NLUServiceConfig()
        print(f"✓ Default configuration created: {config.service_name}")
        
        # Test environment-based configuration
        env_config = load_config_from_env()
        print(f"✓ Environment configuration loaded: {env_config.service_name}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return False

def test_event_bus_framework():
    """Test that event bus framework can be imported"""
    try:
        from event_bus_framework import RedisStreamEventBus, get_service_config
        print("✓ Successfully imported event bus framework")
        return True
    except ImportError as e:
        print(f"✗ Failed to import event bus framework: {e}")
        return False

def test_service_creation():
    """Test that NLU service can be created"""
    try:
        from nlu_service.main import NLUService
        
        service = NLUService()
        print("✓ Successfully created NLU service instance")
        return True
    except Exception as e:
        print(f"✗ Failed to create NLU service: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing NLU Service...")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Configuration Test", test_configuration),
        ("Event Bus Framework Test", test_event_bus_framework),
        ("Service Creation Test", test_service_creation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print("  This test failed - check dependencies and configuration")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! The NLU service is ready to run.")
        return 0
    else:
        print("✗ Some tests failed. Please fix the issues before running the service.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 