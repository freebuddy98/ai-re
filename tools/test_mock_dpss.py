#!/usr/bin/env python3
"""
Test Mock DPSS Service

This script tests the Mock DPSS service functionality including:
- Health check
- Context retrieval for different channels
- Data management endpoints
- Error handling
"""

import json
import requests
import sys
import time
from typing import Dict, Any, Optional


class MockDPSSServiceTester:
    """Test client for Mock DPSS Service"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        """
        Initialize tester
        
        Args:
            base_url: Base URL of the Mock DPSS service
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 10
    
    def test_health_check(self) -> bool:
        """Test health check endpoint"""
        try:
            print("Testing health check...")
            response = self.session.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Health check passed: {data.get('status')}")
                return True
            else:
                print(f"✗ Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Health check error: {e}")
            return False
    
    def test_service_info(self) -> bool:
        """Test service info endpoint"""
        try:
            print("Testing service info...")
            response = self.session.get(f"{self.base_url}/")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Service info: {data.get('service')} v{data.get('version')}")
                return True
            else:
                print(f"✗ Service info failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Service info error: {e}")
            return False
    
    def test_context_retrieval(self, channel_id: str, limit: int = 5) -> Optional[Dict[str, Any]]:
        """Test context retrieval for a specific channel"""
        try:
            print(f"Testing context retrieval for channel: {channel_id}")
            
            params = {
                'channel_id': channel_id,
                'limit': limit
            }
            
            response = self.session.get(
                f"{self.base_url}/api/v1/dpss/context",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                required_fields = ['channel_id', 'retrieval_timestamp_utc', 'recent_history', 
                                 'current_focus_reis_summary', 'active_questions']
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    print(f"✗ Missing required fields: {missing_fields}")
                    return None
                
                print(f"✓ Context retrieved for {channel_id}:")
                print(f"  - History items: {len(data['recent_history'])}")
                print(f"  - Focus REIs: {len(data['current_focus_reis_summary'])}")
                print(f"  - Active questions: {len(data['active_questions'])}")
                
                return data
            else:
                print(f"✗ Context retrieval failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"✗ Context retrieval error: {e}")
            return None
    
    def test_data_endpoint(self) -> bool:
        """Test data management endpoint"""
        try:
            print("Testing data endpoint...")
            response = self.session.get(f"{self.base_url}/data")
            
            if response.status_code == 200:
                data = response.json()
                contexts = data.get('dialogue_contexts', {})
                print(f"✓ Data endpoint accessible, {len(contexts)} contexts available")
                return True
            else:
                print(f"✗ Data endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Data endpoint error: {e}")
            return False
    
    def test_reload_endpoint(self) -> bool:
        """Test data reload endpoint"""
        try:
            print("Testing data reload...")
            response = self.session.post(f"{self.base_url}/data/reload")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Data reload successful: {data.get('message')}")
                return True
            else:
                print(f"✗ Data reload failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Data reload error: {e}")
            return False
    
    def test_channel_update(self, channel_id: str = "test_channel") -> bool:
        """Test channel context update"""
        try:
            print(f"Testing channel update for: {channel_id}")
            
            test_context = {
                "channel_id": channel_id,
                "recent_history": [
                    {
                        "turn_id": "test_001",
                        "speaker_type": "user",
                        "user_id_if_user": "test_user",
                        "utterance_text": "这是一个测试消息",
                        "timestamp_utc": "2025-06-14T12:00:00Z"
                    }
                ],
                "current_focus_reis_summary": [
                    {
                        "rei_id": "TEST-001",
                        "rei_type": "Goal",
                        "name_or_summary": "测试目标",
                        "status": "Drafting",
                        "key_attributes_text": "测试属性",
                        "source_utterances_summary": ["这是一个测试消息"]
                    }
                ],
                "active_questions": []
            }
            
            response = self.session.put(
                f"{self.base_url}/data/channel/{channel_id}",
                json=test_context
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Channel update successful: {data.get('message')}")
                
                # Verify the update by retrieving the context
                retrieved_context = self.test_context_retrieval(channel_id, limit=1)
                if retrieved_context and retrieved_context['channel_id'] == channel_id:
                    print(f"✓ Updated context verified")
                    return True
                else:
                    print(f"✗ Updated context verification failed")
                    return False
            else:
                print(f"✗ Channel update failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Channel update error: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests"""
        print(f"Starting Mock DPSS Service tests...")
        print(f"Service URL: {self.base_url}")
        print("=" * 50)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Service Info", self.test_service_info),
            ("Data Endpoint", self.test_data_endpoint),
            ("Context - Empty Channel", lambda: self.test_context_retrieval("channel123") is not None),
            ("Context - Rich Channel", lambda: self.test_context_retrieval("channel456", limit=3) is not None),
            ("Context - Ecommerce Channel", lambda: self.test_context_retrieval("ecommerce_dev", limit=2) is not None),
            ("Context - Nonexistent Channel", lambda: self.test_context_retrieval("nonexistent_channel", limit=1) is not None),
            ("Data Reload", self.test_reload_endpoint),
            ("Channel Update", self.test_channel_update),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            try:
                if test_func():
                    passed += 1
                else:
                    print(f"Test failed: {test_name}")
            except Exception as e:
                print(f"Test error in {test_name}: {e}")
        
        print("\n" + "=" * 50)
        print(f"Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"❌ {total - passed} tests failed")
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Mock DPSS Service")
    parser.add_argument("--url", default="http://localhost:8080", 
                       help="Base URL of Mock DPSS service")
    parser.add_argument("--wait", type=int, default=0,
                       help="Wait time in seconds before starting tests")
    
    args = parser.parse_args()
    
    if args.wait > 0:
        print(f"Waiting {args.wait} seconds for service to start...")
        time.sleep(args.wait)
    
    # Create tester and run tests
    tester = MockDPSSServiceTester(args.url)
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test runner error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 