#!/usr/bin/env python3
"""
Mock DPSS Service

This module provides a mock implementation of the DPSS service for testing
and development purposes. It serves dialogue context data that conforms to
the schema defined in config/dialogue_context.yml.

Usage:
    python tools/mock_dpss_service.py

The service will start on http://localhost:8080 by default.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class MockDPSSService:
    """Mock DPSS Service implementation"""
    
    def __init__(self, data_file: str = "tools/mock_dpss_data.yml"):
        """
        Initialize Mock DPSS Service
        
        Args:
            data_file: Path to YAML file containing mock dialogue context data
        """
        self.data_file = Path(data_file)
        self.mock_data: Dict[str, Any] = {}
        self.load_mock_data()
        
        # Create FastAPI app
        self.app = FastAPI(
            title="Mock DPSS Service",
            description="Mock implementation of DPSS service for testing NLU service",
            version="0.1.0"
        )
        
        # Setup routes
        self.setup_routes()
    
    def load_mock_data(self) -> None:
        """Load mock data from YAML file"""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.mock_data = yaml.safe_load(f) or {}
                print(f"Loaded mock data from {self.data_file}")
            else:
                # Create default mock data if file doesn't exist
                self.create_default_mock_data()
                print(f"Created default mock data at {self.data_file}")
        except Exception as e:
            print(f"Error loading mock data: {e}")
            self.create_default_mock_data()
    
    def create_default_mock_data(self) -> None:
        """Create default mock data and save to file"""
        default_data = {
            "dialogue_contexts": {
                "channel123": {
                    "channel_id": "channel123",
                    "retrieval_timestamp_utc": "2025-06-05T10:29:00Z",
                    "recent_history": [],
                    "current_focus_reis_summary": [],
                    "active_questions": []
                },
                "channel456": {
                    "channel_id": "channel456",
                    "retrieval_timestamp_utc": "2025-06-05T10:30:00Z",
                    "recent_history": [
                        {
                            "turn_id": "turn001",
                            "speaker_type": "assistant",
                            "utterance_text": "关于订单系统，我们首先要明确它的核心目标是什么？",
                            "timestamp_utc": "2025-06-05T10:25:00Z"
                        },
                        {
                            "turn_id": "turn002",
                            "speaker_type": "user",
                            "user_id_if_user": "client_A",
                            "utterance_text": "核心目标是提升下单效率和用户满意度。",
                            "timestamp_utc": "2025-06-05T10:26:00Z",
                            "simplified_uar_if_available": {
                                "intent_name": "ProposeNewREI",
                                "key_entity_types": ["Goal"]
                            }
                        }
                    ],
                    "current_focus_reis_summary": [
                        {
                            "rei_id": "G-100",
                            "rei_type": "Goal",
                            "name_or_summary": "提升下单效率和用户满意度",
                            "status": "Drafting",
                            "key_attributes_text": "业务目标: 提高用户体验, 关键指标: 下单时间, 用户满意度评分",
                            "source_utterances_summary": [
                                "核心目标是提升下单效率和用户满意度。"
                            ]
                        },
                        {
                            "rei_id": "FR-101",
                            "rei_type": "FunctionalRequirement",
                            "name_or_summary": "用户快速查询历史订单",
                            "status": "Drafting",
                            "key_attributes_text": "功能描述: 查询历史订单, 性能要求: 快速响应",
                            "source_utterances_summary": [
                                "用户应该能够快速查询历史订单"
                            ]
                        }
                    ],
                    "active_questions": [
                        {
                            "question_id": "q001",
                            "question_text": "您说的'快速'具体指什么？是希望页面加载时间少于多少秒？",
                            "relates_to_rei_id": "FR-101",
                            "relates_to_attribute": "performance_requirement"
                        }
                    ]
                },
                "default": {
                    "channel_id": "default",
                    "retrieval_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "recent_history": [
                        {
                            "turn_id": "default_turn_001",
                            "speaker_type": "user",
                            "user_id_if_user": "test_user",
                            "utterance_text": "我想开发一个电商系统",
                            "timestamp_utc": datetime.now(timezone.utc).isoformat()
                        }
                    ],
                    "current_focus_reis_summary": [
                        {
                            "rei_id": "G-001",
                            "rei_type": "Goal",
                            "name_or_summary": "开发电商系统",
                            "status": "Drafting",
                            "key_attributes_text": "业务目标: 构建在线销售平台",
                            "source_utterances_summary": [
                                "我想开发一个电商系统"
                            ]
                        }
                    ],
                    "active_questions": []
                }
            }
        }
        
        self.mock_data = default_data
        self.save_mock_data()
    
    def save_mock_data(self) -> None:
        """Save current mock data to file"""
        try:
            # Ensure directory exists
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.mock_data, f, default_flow_style=False, allow_unicode=True)
            print(f"Saved mock data to {self.data_file}")
        except Exception as e:
            print(f"Error saving mock data: {e}")
    
    def setup_routes(self) -> None:
        """Setup FastAPI routes"""
        
        @self.app.get("/")
        async def root():
            """Root endpoint"""
            return {
                "service": "Mock DPSS Service",
                "version": "0.1.0",
                "status": "running",
                "endpoints": {
                    "context": "/api/v1/dpss/context",
                    "health": "/health",
                    "data": "/data"
                }
            }
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "mock-dpss-service"
            }
        
        @self.app.get("/api/v1/dpss/context")
        async def get_dialogue_context(
            channel_id: str = Query(..., description="Channel ID to get context for"),
            limit: int = Query(5, description="Maximum number of recent history items")
        ):
            """
            Get dialogue context for a channel
            
            This endpoint mimics the real DPSS service API and returns dialogue context
            data that conforms to the schema defined in config/dialogue_context.yml
            """
            try:
                print(f"Received context request for channel_id: {channel_id}, limit: {limit}")
                
                # Get context data for the channel
                contexts = self.mock_data.get("dialogue_contexts", {})
                
                if channel_id in contexts:
                    context_data = contexts[channel_id].copy()
                else:
                    # Use default context if channel not found
                    context_data = contexts.get("default", {}).copy()
                    context_data["channel_id"] = channel_id
                
                # Update timestamp to current time
                context_data["retrieval_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
                
                # Limit recent history if requested
                if "recent_history" in context_data and len(context_data["recent_history"]) > limit:
                    context_data["recent_history"] = context_data["recent_history"][-limit:]
                
                print(f"Returning context for channel {channel_id}")
                return JSONResponse(content=context_data)
                
            except Exception as e:
                print(f"Error processing context request: {e}")
                raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
        
        @self.app.get("/data")
        async def get_mock_data():
            """Get current mock data (for debugging)"""
            return JSONResponse(content=self.mock_data)
        
        @self.app.post("/data/reload")
        async def reload_mock_data():
            """Reload mock data from file"""
            try:
                self.load_mock_data()
                return {"status": "success", "message": "Mock data reloaded"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to reload data: {str(e)}")
        
        @self.app.put("/data/channel/{channel_id}")
        async def update_channel_context(channel_id: str, context_data: Dict[str, Any]):
            """Update context data for a specific channel"""
            try:
                if "dialogue_contexts" not in self.mock_data:
                    self.mock_data["dialogue_contexts"] = {}
                
                # Ensure channel_id matches
                context_data["channel_id"] = channel_id
                context_data["retrieval_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
                
                self.mock_data["dialogue_contexts"][channel_id] = context_data
                self.save_mock_data()
                
                return {
                    "status": "success", 
                    "message": f"Updated context for channel {channel_id}"
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to update context: {str(e)}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Mock DPSS Service")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--data-file", default="tools/mock_dpss_data.yml", 
                       help="Path to mock data file")
    parser.add_argument("--reload", action="store_true", 
                       help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    # Create mock service
    mock_service = MockDPSSService(data_file=args.data_file)
    
    print(f"Starting Mock DPSS Service on {args.host}:{args.port}")
    print(f"Mock data file: {args.data_file}")
    print(f"API endpoint: http://{args.host}:{args.port}/api/v1/dpss/context")
    print(f"Health check: http://{args.host}:{args.port}/health")
    print(f"Data management: http://{args.host}:{args.port}/data")
    
    # Run the service
    uvicorn.run(
        mock_service.app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main() 