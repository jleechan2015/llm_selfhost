#!/usr/bin/env python3
"""
Tool-Enabled Vast.ai Proxy Server
Combines Redis caching with tool execution capabilities
Designed specifically for vast.ai deployment with Claude Code CLI integration.
"""

import os
import sys
import json
import time
import hashlib
import traceback
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Core dependencies only
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests

# Import base tool classes
from claude_tools_base import ToolExecutionMixin

# Optional Redis dependency
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    print("⚠️  Redis not available - running without cache")

print("🚀 Starting Tool-Enabled Vast.ai Proxy Server...")
print("=" * 50)

# Environment variables
REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
API_PORT = int(os.getenv('API_PORT', 8000))
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'localhost:11434')

# Redis setup
USE_REDIS_CACHE = bool(HAS_REDIS and REDIS_HOST and REDIS_PASSWORD)
redis_client = None

if USE_REDIS_CACHE:
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            ssl=True,
            decode_responses=True,
            socket_timeout=5
        )
        # Test connection
        redis_client.ping()
        print(f"✅ Redis connected: {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("⚠️  Continuing without cache")
        USE_REDIS_CACHE = False
        redis_client = None
else:
    print("ℹ️  Redis cache disabled")

class VastToolsProxy(ToolExecutionMixin):
    """Vast.ai proxy with Redis caching and tool execution"""
    
    def __init__(self):
        super().__init__()
        print(f"🔧 Vast Tools Proxy initialized with session: {self.tools.session_id}")

# Initialize FastAPI app
app = FastAPI(title="Tool-Enabled Vast.ai Proxy", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize proxy with tools
proxy = VastToolsProxy()

def create_cache_key(messages: List[Dict]) -> str:
    """Create a cache key from messages"""
    try:
        # Serialize messages to consistent string
        messages_str = json.dumps(messages, sort_keys=True)
        return hashlib.md5(messages_str.encode()).hexdigest()
    except Exception as e:
        print(f"⚠️  Cache key generation failed: {e}")
        return str(time.time())

def get_cached_response(cache_key: str) -> Optional[Dict]:
    """Get cached response if available"""
    if not USE_REDIS_CACHE:
        return None
    
    try:
        cached = redis_client.get(f"claude_cache:{cache_key}")
        if cached:
            print("🎯 Cache hit!")
            return json.loads(cached)
    except Exception as e:
        print(f"⚠️  Cache read error: {e}")
    
    return None

def cache_response(cache_key: str, response: Dict) -> None:
    """Cache response with TTL"""
    if not USE_REDIS_CACHE:
        return
    
    try:
        redis_client.setex(
            f"claude_cache:{cache_key}",
            86400,  # 24 hours TTL
            json.dumps(response)
        )
        print("💾 Response cached")
    except Exception as e:
        print(f"⚠️  Cache write error: {e}")

# Use methods from the proxy instance
def should_use_tools(content: str) -> bool:
    return proxy.should_use_tools(content)

def extract_tool_requests(content: str) -> List[Dict]:
    return proxy.extract_tool_requests(content)

def execute_tools(tool_requests: List[Dict]) -> str:
    return proxy.execute_tools(tool_requests)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    # Check Ollama connection
    ollama_status = "unknown"
    try:
        response = requests.get(f"http://{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            ollama_status = "healthy"
        else:
            ollama_status = f"error_{response.status_code}"
    except Exception as e:
        ollama_status = f"unreachable"
    
    # Check Redis
    redis_status = "disabled"
    if USE_REDIS_CACHE:
        try:
            redis_client.ping()
            redis_status = "healthy"
        except:
            redis_status = "error"
    
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "vast_tools_proxy": "active",
        "tools_enabled": True,
        "components": {
            "ollama": ollama_status,
            "redis": redis_status
        },
        "tools": {
            "bash": True,
            "str_replace_editor": True,
            "write_file": True
        }
    })

@app.get("/v1/models")
async def list_models():
    """List available models"""
    return JSONResponse({
        "object": "list",
        "data": [
            {
                "id": "claude-3-5-sonnet-20241022",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "anthropic",
                "type": "text"
            },
            {
                "id": "qwen3-coder",
                "object": "model", 
                "created": int(time.time()),
                "owned_by": "qwen",
                "type": "text"
            }
        ]
    })

@app.post("/v1/messages")
async def create_message(request: Request):
    """Create message with tool execution support"""
    try:
        request_data = await request.json()
        messages = request_data.get("messages", [])
        
        print(f"📨 Request: {len(messages)} messages")
        
        # Create cache key
        cache_key = create_cache_key(messages)
        
        # Check cache first
        cached_response = get_cached_response(cache_key)
        if cached_response:
            return JSONResponse(cached_response)
        
        # Forward to Ollama/Qwen
        try:
            # Add tool instructions to system message
            enhanced_messages = proxy.add_tool_instructions_to_messages(messages)
            
            ollama_request = {
                "model": "qwen3-coder",
                "messages": enhanced_messages,
                "stream": False
            }
            
            print(f"🔄 Forwarding to Ollama: {OLLAMA_HOST}")
            
            response = requests.post(
                f"http://{OLLAMA_HOST}/v1/chat/completions",
                json=ollama_request,
                timeout=120
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            ollama_response = response.json()
            
            # Convert to Anthropic format
            anthropic_response = {
                "id": f"msg_{int(time.time())}",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": ollama_response["choices"][0]["message"]["content"]
                    }
                ],
                "model": "claude-3-5-sonnet-20241022",
                "stop_reason": "end_turn",
                "usage": ollama_response.get("usage", {})
            }
            
            # Check if we should execute tools
            response_content = anthropic_response["content"][0]["text"]
            
            if should_use_tools(response_content):
                print("🔧 Tool execution triggered")
                
                # Extract and execute tools
                tool_requests = extract_tool_requests(response_content)
                if tool_requests:
                    tool_results = execute_tools(tool_requests)
                    
                    # Enhance response with tool results
                    enhanced_content = response_content + tool_results
                    anthropic_response["content"][0]["text"] = enhanced_content
                    print(f"✅ Tools executed: {len(tool_requests)} operations")
            
            # Cache the response
            cache_response(cache_key, anthropic_response)
            
            print(f"✅ Response ready ({len(response_content)} chars)")
            return JSONResponse(anthropic_response)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Ollama request failed: {e}")
            raise HTTPException(status_code=503, detail=f"Ollama service unavailable: {str(e)}")
            
    except Exception as e:
        print(f"❌ Error processing request: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("\n🚀 Tool-Enabled Vast.ai Proxy Server")
    print("=" * 40)
    print(f"🌐 Port: {API_PORT}")
    print(f"🤖 Ollama: {OLLAMA_HOST}")
    print(f"💾 Redis: {'Enabled' if USE_REDIS_CACHE else 'Disabled'}")
    print(f"🔧 Tools: bash, str_replace_editor, write_file")
    print("\nReady for Claude Code CLI integration!")
    print("=" * 40)
    
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)