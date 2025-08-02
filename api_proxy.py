#!/usr/bin/env python3
"""
Anthropic API-compatible proxy server for Claude CLI integration.

This server accepts Anthropic API requests and routes them through:
1. Redis Cloud semantic caching (check for similar queries)
2. Ollama qwen2.5-coder:7b model (for cache misses)
3. Response caching for future queries

Usage:
    python3 api_proxy.py

Environment Variables:
    REDIS_HOST - Redis Cloud host
    REDIS_PORT - Redis Cloud port  
    REDIS_PASSWORD - Redis Cloud password
    API_PORT - Server port (default: 8000)
    OLLAMA_HOST - Ollama host (default: localhost:11434)
"""

import os
import sys
import json
import time
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime

# FastAPI for HTTP server
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Cache and LLM integration
from modelcache import cache
from modelcache.manager import CacheBase
from modelcache.embedding import SentenceTransformer
import ollama
import requests

print("🚀 Starting Anthropic API Proxy Server...")
print("=" * 50)

# Read environment variables
REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
API_PORT = int(os.getenv('API_PORT', 8000))
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'localhost:11434')

# Check if Redis cache is available
USE_REDIS_CACHE = bool(REDIS_HOST and REDIS_PASSWORD)

if USE_REDIS_CACHE:
    print(f"✅ Redis cache enabled: {REDIS_HOST}:{REDIS_PORT}")
    
    # Initialize ModelCache with Redis
    cache.init(
        embedding_func=SentenceTransformer('all-MiniLM-L6-v2'),
        data_manager=CacheBase(
            name='redis',
            config={
                'host': REDIS_HOST,
                'port': REDIS_PORT,
                'password': REDIS_PASSWORD,
                'ssl': True,  # Redis Cloud requires SSL
                'db': 0
            }
        ),
        similarity_threshold=0.8,
        ttl=86400  # 24 hours
    )
else:
    print("⚠️  Redis cache disabled - no credentials provided")

print(f"🤖 Ollama backend: {OLLAMA_HOST}")
print(f"🌐 API server port: {API_PORT}")
print("=" * 50)

# Initialize FastAPI app
app = FastAPI(
    title="Anthropic API Proxy",
    description="Claude CLI compatible API proxy with Redis caching + qwen backend",
    version="1.0.0"
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Ollama client
ollama_client = ollama.Client(host=f"http://{OLLAMA_HOST}")

def call_ollama_with_cache(model: str, messages: List[Dict], **kwargs) -> Dict[str, Any]:
    """
    Call Ollama with Redis caching integration.
    
    Args:
        model: Model name (e.g., "qwen2.5-coder:7b")
        messages: List of message dictionaries
        **kwargs: Additional parameters
        
    Returns:
        Response dictionary with 'content' field
    """
    # Convert messages to a single prompt for Ollama
    prompt_parts = []
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        if role == 'system':
            prompt_parts.append(f"System: {content}")
        elif role == 'user':
            prompt_parts.append(f"User: {content}")
        elif role == 'assistant':
            prompt_parts.append(f"Assistant: {content}")
    
    prompt = "\n".join(prompt_parts)
    
    if USE_REDIS_CACHE:
        @cache.cache()
        def cached_ollama_call(model, prompt, **kwargs):
            print(f"⚡ CACHE MISS - Generating new response with {model}")
            try:
                response = ollama_client.generate(
                    model=model,
                    prompt=prompt,
                    stream=False,
                    **kwargs
                )
                return {
                    'content': response['response'],
                    'model': model,
                    'timestamp': time.time(),
                    'cached': False
                }
            except Exception as e:
                print(f"❌ Ollama error: {e}")
                raise HTTPException(status_code=500, detail=f"Ollama generation failed: {str(e)}")
        
        print(f"🔍 Checking cache for prompt (length: {len(prompt)} chars)")
        result = cached_ollama_call(model, prompt, **kwargs)
        
        # Check if this was a cache hit
        if hasattr(result, '__dict__') and not result.get('cached', True):
            print(f"⚡ CACHE MISS - Generated new response")
        else:
            print(f"🎯 CACHE HIT - Retrieved cached response")
            
        return result
        
    else:
        print(f"🔄 NO CACHE - Direct Ollama call with {model}")
        try:
            response = ollama_client.generate(
                model=model,
                prompt=prompt,
                stream=False,
                **kwargs
            )
            return {
                'content': response['response'],
                'model': model,
                'timestamp': time.time(),
                'cached': False
            }
        except Exception as e:
            print(f"❌ Ollama error: {e}")
            raise HTTPException(status_code=500, detail=f"Ollama generation failed: {str(e)}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Anthropic API Proxy",
        "status": "running",
        "redis_cache": "enabled" if USE_REDIS_CACHE else "disabled",
        "ollama_host": OLLAMA_HOST,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/v1/models")
async def list_models():
    """List available models (Anthropic API compatible)"""
    try:
        # Try to get available models from Ollama
        models_response = requests.get(f"http://{OLLAMA_HOST}/api/tags", timeout=5)
        if models_response.status_code == 200:
            ollama_models = models_response.json().get('models', [])
            
            # Convert to Anthropic API format
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
            
            return {
                "object": "list",
                "data": anthropic_models
            }
        else:
            # Fallback list if Ollama is not available
            return {
                "object": "list", 
                "data": [
                    {
                        "id": "qwen2.5-coder:7b",
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "anthropic",
                        "type": "text"
                    }
                ]
            }
    except Exception as e:
        print(f"⚠️  Model list error: {e}")
        # Return default model list
        return {
            "object": "list",
            "data": [
                {
                    "id": "qwen2.5-coder:7b", 
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "anthropic",
                    "type": "text"
                }
            ]
        }

@app.post("/v1/messages")
async def create_message(request: Request):
    """
    Create a message completion (Anthropic API compatible).
    
    This is the main endpoint that Claude CLI uses.
    """
    try:
        # Parse request body
        body = await request.json()
        
        # Extract parameters
        model = body.get('model', 'qwen2.5-coder:7b')
        messages = body.get('messages', [])
        max_tokens = body.get('max_tokens', 1000)
        temperature = body.get('temperature', 0.7)
        stream = body.get('stream', False)
        
        print(f"📨 Request: model={model}, messages={len(messages)}, stream={stream}")
        
        if not messages:
            raise HTTPException(status_code=400, detail="Messages are required")
        
        # Get response from Ollama via cache
        result = call_ollama_with_cache(
            model=model,
            messages=messages,
            options={
                'temperature': temperature,
                'num_predict': max_tokens
            }
        )
        
        response_content = result['content']
        
        if stream:
            # Streaming response (for future enhancement)
            async def generate_stream():
                # For now, send the full response as a single chunk
                chunk = {
                    "type": "content_block_delta",
                    "delta": {"text": response_content}
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                
                # Send completion
                final_chunk = {"type": "message_stop"}
                yield f"data: {json.dumps(final_chunk)}\n\n"
                
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache"}
            )
        else:
            # Non-streaming response (standard)
            anthropic_response = {
                "id": f"msg_{int(time.time())}",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": response_content
                    }
                ],
                "model": model,
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {
                    "input_tokens": sum(len(msg.get('content', '').split()) for msg in messages),
                    "output_tokens": len(response_content.split())
                }
            }
            
            print(f"✅ Response generated (length: {len(response_content)} chars)")
            return anthropic_response
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ API error: {e}")
        print(f"🔍 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    """Extended health check with component status"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # Check Redis connection
    if USE_REDIS_CACHE:
        try:
            # Try a simple Redis operation
            import redis
            r = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                ssl=True,
                decode_responses=True
            )
            r.ping()
            health_status["components"]["redis"] = "healthy"
        except Exception as e:
            health_status["components"]["redis"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
    else:
        health_status["components"]["redis"] = "disabled"
    
    # Check Ollama connection
    try:
        response = requests.get(f"http://{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            health_status["components"]["ollama"] = "healthy"
        else:
            health_status["components"]["ollama"] = f"http_error: {response.status_code}"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["ollama"] = f"connection_error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status

if __name__ == "__main__":
    print(f"🌟 Starting Anthropic API Proxy on port {API_PORT}")
    print(f"📋 Health check: http://localhost:{API_PORT}/health")
    print(f"📋 API endpoint: http://localhost:{API_PORT}/v1/messages")
    print("🔥 Ready to handle Claude CLI requests!")
    print("=" * 50)
    
    uvicorn.run(
        app,
        host="0.0.0.0",  # Allow external connections
        port=API_PORT,
        log_level="info"
    )