#!/usr/bin/env python3
"""
Simple Anthropic API-compatible proxy server for Claude CLI integration.
Uses Redis for basic caching without ModelCache dependency issues.

Usage:
    python3 simple_api_proxy.py
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
import redis
import requests

print("🚀 Starting Simple Anthropic API Proxy Server...")
print("=" * 50)

# Environment variables
REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
API_PORT = int(os.getenv('API_PORT', 8000))
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'localhost:11434')

# Redis setup
USE_REDIS_CACHE = bool(REDIS_HOST and REDIS_PASSWORD)
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
        redis_client.ping()
        print(f"✅ Redis cache connected: {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        redis_client = None
        USE_REDIS_CACHE = False
else:
    print("⚠️  Redis cache disabled - no credentials")

print(f"🤖 Ollama backend: {OLLAMA_HOST}")
print(f"🌐 API server port: {API_PORT}")
print("=" * 50)

# FastAPI app
app = FastAPI(
    title="Simple Anthropic API Proxy",
    description="Claude CLI compatible API proxy with Redis caching",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_content(content: Union[str, List[Dict]]) -> str:
    """Extract text from content (handles both string and list formats)"""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        # Handle Anthropic API format: [{"type": "text", "text": "content"}]
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                text_parts.append(item.get('text', ''))
            elif isinstance(item, str):
                text_parts.append(item)
        return ' '.join(text_parts)
    else:
        return str(content)

def get_cache_key(messages: List[Dict]) -> str:
    """Generate cache key from messages"""
    # Convert messages to consistent string and hash
    messages_str = json.dumps(messages, sort_keys=True)
    return hashlib.md5(messages_str.encode()).hexdigest()

def get_cached_response(cache_key: str) -> Optional[str]:
    """Get cached response if available"""
    if not USE_REDIS_CACHE or not redis_client:
        return None
    
    try:
        cached = redis_client.get(f"anthropic_cache:{cache_key}")
        if cached:
            print(f"🎯 CACHE HIT for key: {cache_key[:8]}...")
            return cached
    except Exception as e:
        print(f"⚠️  Cache get error: {e}")
    
    return None

def cache_response(cache_key: str, response: str) -> None:
    """Cache response with TTL"""
    if not USE_REDIS_CACHE or not redis_client:
        return
    
    try:
        # Cache for 24 hours
        redis_client.setex(f"anthropic_cache:{cache_key}", 86400, response)
        print(f"💾 Cached response for key: {cache_key[:8]}...")
    except Exception as e:
        print(f"⚠️  Cache set error: {e}")

def call_ollama(model: str, messages: List[Dict]) -> str:
    """Call Ollama API directly"""
    # Convert messages to prompt
    prompt_parts = []
    for msg in messages:
        role = msg.get('role', 'user')
        content = extract_text_content(msg.get('content', ''))
        if role == 'system':
            prompt_parts.append(f"System: {content}")
        elif role == 'user':
            prompt_parts.append(f"User: {content}")
        elif role == 'assistant':
            prompt_parts.append(f"Assistant: {content}")
    
    prompt = "\n".join(prompt_parts)
    
    try:
        response = requests.post(
            f"http://{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '')
        else:
            raise Exception(f"Ollama API error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ollama error: {e}")
        raise HTTPException(status_code=500, detail=f"Ollama generation failed: {str(e)}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Simple Anthropic API Proxy",
        "status": "running",
        "redis_cache": "enabled" if USE_REDIS_CACHE else "disabled",
        "ollama_host": OLLAMA_HOST,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/v1/models")
async def list_models():
    """List available models"""
    try:
        response = requests.get(f"http://{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            ollama_models = response.json().get('models', [])
            anthropic_models = []
            for model in ollama_models:
                model_name = model.get('name', 'unknown')
                anthropic_models.append({
                    "id": model_name,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "anthropic",
                    "type": "text"
                })
            return {"object": "list", "data": anthropic_models}
        else:
            # Fallback
            return {
                "object": "list",
                "data": [{
                    "id": "qwen3-coder:latest",
                    "object": "model", 
                    "created": int(time.time()),
                    "owned_by": "anthropic",
                    "type": "text"
                }]
            }
    except Exception as e:
        return {
            "object": "list",
            "data": [{
                "id": "qwen3-coder:latest",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "anthropic", 
                "type": "text"
            }]
        }

@app.post("/v1/messages")
async def create_message(request: Request):
    """Create message completion (Anthropic API compatible)"""
    try:
        body = await request.json()
        
        model = body.get('model', 'qwen3-coder:latest')
        messages = body.get('messages', [])
        max_tokens = body.get('max_tokens', 1000)
        
        if not messages:
            raise HTTPException(status_code=400, detail="Messages are required")
        
        print(f"📨 Request: model={model}, messages={len(messages)}")
        
        # Check cache first
        cache_key = get_cache_key(messages)
        cached_response = get_cached_response(cache_key)
        
        if cached_response:
            response_content = cached_response
        else:
            print(f"⚡ CACHE MISS - Generating new response with {model}")
            response_content = call_ollama(model, messages)
            cache_response(cache_key, response_content)
        
        # Calculate token counts properly
        input_tokens = 0
        for msg in messages:
            content = extract_text_content(msg.get('content', ''))
            input_tokens += len(content.split())
        
        output_tokens = len(response_content.split())
        
        # Return Anthropic-compatible response
        anthropic_response = {
            "id": f"msg_{int(time.time())}",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": response_content}],
            "model": model,
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }
        }
        
        print(f"✅ Response sent (length: {len(response_content)} chars)")
        return anthropic_response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ API error: {e}")
        print(f"🔍 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check with component status"""
    health = {"status": "healthy", "timestamp": datetime.now().isoformat(), "components": {}}
    
    # Test Redis
    if USE_REDIS_CACHE and redis_client:
        try:
            redis_client.ping()
            health["components"]["redis"] = "healthy"
        except Exception as e:
            health["components"]["redis"] = f"error: {str(e)}"
            health["status"] = "degraded"
    else:
        health["components"]["redis"] = "disabled"
    
    # Test Ollama
    try:
        response = requests.get(f"http://{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            health["components"]["ollama"] = "healthy"
        else:
            health["components"]["ollama"] = f"http_error: {response.status_code}"
            health["status"] = "degraded"
    except Exception as e:
        health["components"]["ollama"] = f"connection_error: {str(e)}"
        health["status"] = "degraded"
    
    return health

if __name__ == "__main__":
    print(f"🌟 Starting Simple API Proxy on port {API_PORT}")
    print(f"📋 Health: http://localhost:{API_PORT}/health")
    print(f"📋 API: http://localhost:{API_PORT}/v1/messages")
    print("🔥 Ready for Claude CLI!")
    print("=" * 50)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=API_PORT,
        log_level="info"
    )