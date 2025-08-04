#!/usr/bin/env python3
"""
Local Claude Code CLI compatible proxy that forwards to vast.ai backend.
"""

import os
import json
import time
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

# Configuration
VAST_API_URL = "http://localhost:8000"  # Your SSH tunnel
LOCAL_PORT = 8001  # Different port to avoid conflict

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        response = requests.get(f"{VAST_API_URL}/health", timeout=5)
        return {
            "status": "healthy",
            "vast_backend": "connected" if response.status_code == 200 else "disconnected",
            "timestamp": time.time()
        }
    except:
        return {"status": "unhealthy", "vast_backend": "disconnected"}

@app.get("/v1/models")
async def list_models():
    """List available models - Claude Code CLI compatible"""
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen3-coder",
                "object": "model", 
                "created": int(time.time()),
                "owned_by": "anthropic",
                "type": "text"
            }
        ]
    }

@app.post("/v1/messages")
async def create_message(request: Request):
    """Forward messages to vast.ai backend"""
    try:
        body = await request.json()
        
        # Forward to your vast.ai proxy
        response = requests.post(
            f"{VAST_API_URL}/v1/messages",
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request to vast.ai backend failed: {str(e)}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}") from e

if __name__ == "__main__":
    print(f"🚀 Starting Claude Code Proxy on port {LOCAL_PORT}")
    print(f"📡 Forwarding to vast.ai backend: {VAST_API_URL}")
    uvicorn.run(app, host="127.0.0.1", port=LOCAL_PORT)