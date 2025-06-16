#!/usr/bin/env python3
"""
Session Manager Tool

Manages session timestamps for Redis stream keys to separate different
development/testing sessions and enable better debugging and replay capabilities.

The tool generates session timestamps and updates configuration files
to use timestamped stream prefixes like "ai-re:20240605143022:user_message_raw"
instead of "ai-re:user_message_raw".

Usage:
    python tools/session_manager.py [command] [options]

Commands:
    init        Initialize a new session with current timestamp
    current     Show current session info
    list        List recent sessions
    clean       Clean old session data from Redis
"""

import os
import sys
import yaml
import time
import redis
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from libs.event_bus_framework.src.event_bus_framework.common.config import get_config
except ImportError as e:
    print(f"Error importing config module: {e}")
    print("Please ensure you're running from the project root.")
    sys.exit(1)


class SessionManager:
    """Manages Redis stream session timestamps"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.config_file = self.project_root / "config" / "config.yml"
        self.sessions_file = self.project_root / "tools" / "sessions.yml"
        
        # Ensure sessions file exists
        self.sessions_file.parent.mkdir(exist_ok=True)
        if not self.sessions_file.exists():
            self._init_sessions_file()
    
    def _init_sessions_file(self):
        """Initialize the sessions tracking file"""
        initial_data = {
            "current_session": "",
            "sessions": []
        }
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(initial_data, f, default_flow_style=False, allow_unicode=True)
    
    def _load_sessions_data(self) -> Dict[str, Any]:
        """Load sessions data"""
        if not self.sessions_file.exists():
            self._init_sessions_file()
        
        with open(self.sessions_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _save_sessions_data(self, data: Dict[str, Any]):
        """Save sessions data"""
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load main configuration"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _save_config(self, config: Dict[str, Any]):
        """Save main configuration"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True)
    
    def generate_session_timestamp(self) -> str:
        """Generate a session timestamp in format YYYYMMDDHHMMSS"""
        return datetime.now().strftime("%Y%m%d%H%M%S")
    
    def init_new_session(self, description: str = "") -> str:
        """Initialize a new session with timestamp"""
        timestamp = self.generate_session_timestamp()
        
        # Update main config
        config = self._load_config()
        old_prefix = config.get('event_bus', {}).get('stream_prefix', 'ai-re')
        
        # Extract base prefix (remove existing timestamp if any)
        base_prefix = old_prefix.split(':')[0] if ':' in old_prefix else old_prefix
        new_prefix = f"{base_prefix}:{timestamp}"
        
        config.setdefault('event_bus', {})['stream_prefix'] = new_prefix
        self._save_config(config)
        
        # Update sessions tracking
        sessions_data = self._load_sessions_data()
        session_info = {
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "description": description or f"Session created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "prefix": new_prefix,
            "base_prefix": base_prefix
        }
        
        sessions_data["current_session"] = timestamp
        sessions_data.setdefault("sessions", []).append(session_info)
        
        # Keep only last 10 sessions
        sessions_data["sessions"] = sessions_data["sessions"][-10:]
        
        self._save_sessions_data(sessions_data)
        
        print(f"✅ New session initialized: {timestamp}")
        print(f"   Stream prefix: {new_prefix}")
        print(f"   Description: {session_info['description']}")
        
        return timestamp
    
    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """Get current session info"""
        sessions_data = self._load_sessions_data()
        current_timestamp = sessions_data.get("current_session")
        
        if not current_timestamp:
            return None
        
        for session in sessions_data.get("sessions", []):
            if session["timestamp"] == current_timestamp:
                return session
        
        return None
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all recorded sessions"""
        sessions_data = self._load_sessions_data()
        return sessions_data.get("sessions", [])
    
    def switch_to_session(self, timestamp: str) -> bool:
        """Switch to an existing session"""
        sessions_data = self._load_sessions_data()
        
        # Find the session
        target_session = None
        for session in sessions_data.get("sessions", []):
            if session["timestamp"] == timestamp:
                target_session = session
                break
        
        if not target_session:
            print(f"❌ Session {timestamp} not found")
            return False
        
        # Update config
        config = self._load_config()
        config.setdefault('event_bus', {})['stream_prefix'] = target_session['prefix']
        self._save_config(config)
        
        # Update current session
        sessions_data["current_session"] = timestamp
        self._save_sessions_data(sessions_data)
        
        print(f"✅ Switched to session: {timestamp}")
        print(f"   Stream prefix: {target_session['prefix']}")
        print(f"   Description: {target_session['description']}")
        
        return True
    
    def clean_old_sessions(self, keep_recent: int = 3, dry_run: bool = True):
        """Clean old session data from Redis"""
        try:
            config = get_config()
            redis_config = config.get('event_bus', {}).get('redis', {})
            
            # Use localhost instead of container name for host machine access
            host = redis_config.get('host', 'localhost')
            if host == 'redis':  # Docker container name
                host = 'localhost'  # Connect via port mapping
            
            redis_client = redis.Redis(
                host=host,
                port=redis_config.get('port', 6379),
                db=redis_config.get('db', 0),
                password=redis_config.get('password', '') or None,
                decode_responses=True
            )
            
            # Test connection
            redis_client.ping()
            
            sessions_data = self._load_sessions_data()
            sessions = sessions_data.get("sessions", [])
            
            if len(sessions) <= keep_recent:
                print(f"Only {len(sessions)} sessions found, nothing to clean")
                return
            
            # Get sessions to clean (all except recent ones)
            sessions_to_clean = sessions[:-keep_recent]
            
            print(f"Found {len(sessions)} sessions, will {'simulate cleaning' if dry_run else 'clean'} {len(sessions_to_clean)} old sessions:")
            
            for session in sessions_to_clean:
                prefix = session['prefix']
                print(f"  - {session['timestamp']}: {prefix} ({session['description']})")
                
                if not dry_run:
                    # Find and delete Redis keys with this prefix
                    pattern = f"{prefix}:*"
                    keys = redis_client.keys(pattern)
                    if keys:
                        redis_client.delete(*keys)
                        print(f"    Deleted {len(keys)} Redis keys")
                    else:
                        print(f"    No Redis keys found")
            
            if not dry_run:
                # Update sessions file to keep only recent sessions
                sessions_data["sessions"] = sessions[-keep_recent:]
                self._save_sessions_data(sessions_data)
                print(f"✅ Cleanup completed, kept {keep_recent} recent sessions")
            else:
                print("🔍 Dry run completed. Use --execute to actually clean")
                
        except redis.ConnectionError:
            print("❌ Could not connect to Redis")
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
    
    def show_redis_streams(self):
        """Show current Redis streams matching our patterns"""
        try:
            config = get_config()
            redis_config = config.get('event_bus', {}).get('redis', {})
            
            # Use localhost instead of container name for host machine access
            host = redis_config.get('host', 'localhost')
            if host == 'redis':  # Docker container name
                host = 'localhost'  # Connect via port mapping
            
            redis_client = redis.Redis(
                host=host,
                port=redis_config.get('port', 6379),
                db=redis_config.get('db', 0),
                password=redis_config.get('password', '') or None,
                decode_responses=True
            )
            
            # Test connection
            redis_client.ping()
            
            current_session = self.get_current_session()
            if current_session:
                current_prefix = current_session['prefix']
                print(f"Current session: {current_session['timestamp']}")
                print(f"Current prefix: {current_prefix}")
                
                pattern = f"{current_prefix}:*"
                keys = redis_client.keys(pattern)
                
                if keys:
                    print(f"\nActive streams ({len(keys)}):")
                    for key in sorted(keys):
                        try:
                            info = redis_client.xinfo_stream(key)
                            length = info.get('length', 0)
                            print(f"  - {key}: {length} messages")
                        except:
                            print(f"  - {key}: (unable to get info)")
                else:
                    print(f"\nNo active streams found for current session")
            else:
                print("No current session set")
            
            # Show all AI-RE related streams
            print(f"\nAll AI-RE streams:")
            all_keys = redis_client.keys("ai-re*")
            if all_keys:
                for key in sorted(all_keys):
                    try:
                        info = redis_client.xinfo_stream(key)
                        length = info.get('length', 0)
                        print(f"  - {key}: {length} messages")
                    except:
                        print(f"  - {key}: (unable to get info)")
            else:
                print("  No AI-RE streams found")
                
        except redis.ConnectionError:
            print("❌ Could not connect to Redis")
        except Exception as e:
            print(f"❌ Error checking Redis: {e}")


def main():
    parser = argparse.ArgumentParser(description="Session Manager for AI-RE Redis Streams")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize a new session')
    init_parser.add_argument('--description', '-d', type=str, help='Session description')
    
    # Current command
    subparsers.add_parser('current', help='Show current session info')
    
    # List command
    subparsers.add_parser('list', help='List all sessions')
    
    # Switch command
    switch_parser = subparsers.add_parser('switch', help='Switch to an existing session')
    switch_parser.add_argument('timestamp', help='Session timestamp to switch to')
    
    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Clean old session data from Redis')
    clean_parser.add_argument('--keep', type=int, default=3, help='Number of recent sessions to keep (default: 3)')
    clean_parser.add_argument('--execute', action='store_true', help='Actually perform cleanup (default is dry-run)')
    
    # Streams command
    subparsers.add_parser('streams', help='Show current Redis streams')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = SessionManager()
    
    if args.command == 'init':
        manager.init_new_session(args.description or "")
    
    elif args.command == 'current':
        current = manager.get_current_session()
        if current:
            print(f"Current session: {current['timestamp']}")
            print(f"Created: {current['created_at']}")
            print(f"Stream prefix: {current['prefix']}")
            print(f"Description: {current['description']}")
        else:
            print("No current session set")
    
    elif args.command == 'list':
        sessions = manager.list_sessions()
        current_session = manager.get_current_session()
        current_timestamp = current_session['timestamp'] if current_session else None
        
        if sessions:
            print(f"Available sessions ({len(sessions)}):")
            for session in reversed(sessions):  # Show newest first
                marker = " ← current" if session['timestamp'] == current_timestamp else ""
                print(f"  {session['timestamp']}: {session['prefix']}{marker}")
                print(f"    Created: {session['created_at']}")
                print(f"    Description: {session['description']}")
                print()
        else:
            print("No sessions found")
    
    elif args.command == 'switch':
        manager.switch_to_session(args.timestamp)
    
    elif args.command == 'clean':
        manager.clean_old_sessions(args.keep, not args.execute)
    
    elif args.command == 'streams':
        manager.show_redis_streams()


if __name__ == "__main__":
    main() 