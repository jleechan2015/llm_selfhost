#!/usr/bin/env python3
"""
Corrected Simple API Proxy for Vast.ai 
Converts Anthropic API format to Ollama format
"""

import json
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
from datetime import datetime

app = FastAPI()

# Ollama configuration
OLLAMA_HOST = "localhost:11434"
OLLAMA_URL = f"http://{OLLAMA_HOST}"

class Message(BaseModel):
    role: str
    content: Any  # Can be string or complex objects from Claude CLI

class ChatRequest(BaseModel):
    messages: List[Message]
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7
    model: Optional[str] = "qwen2.5-coder:7b"

def convert_messages_to_prompt(messages: List[Message]) -> str:
    """Convert Anthropic messages to a single prompt for Ollama"""
    prompt_parts = []
    for message in messages:
        if message.role == "user":
            prompt_parts.append(f"User: {message.content}")
        elif message.role == "assistant":
            prompt_parts.append(f"Assistant: {message.content}")
        elif message.role == "system":
            prompt_parts.append(f"System: {message.content}")
    
    prompt_parts.append("Assistant:")
    return "\n".join(prompt_parts)

@app.get("/")
async def root():
    return {
        "service": "Simple Anthropic API Proxy",
        "status": "running", 
        "redis_cache": "disabled",
        "ollama_host": OLLAMA_HOST,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    try:
        # Check Ollama health
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        ollama_healthy = response.status_code == 200
    except:
        ollama_healthy = False
    
    return {
        "status": "healthy" if ollama_healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "redis": "disabled",
            "ollama": "healthy" if ollama_healthy else "unhealthy"
        }
    }

@app.post("/v1/messages")
async def create_message(request: ChatRequest):
    try:
        # Convert messages to prompt
        prompt = convert_messages_to_prompt(request.messages)
        
        # Prepare Ollama request
        ollama_request = {
            "model": request.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": request.max_tokens,
                "temperature": request.temperature
            }
        }
        
        # Call Ollama
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=ollama_request,
            timeout=60
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Ollama generation failed: Ollama API error: {response.status_code}"
            )
        
        ollama_response = response.json()
        
        # Convert to Anthropic format
        anthropic_response = {
            "id": f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": ollama_response.get("response", "")
                }
            ],
            "model": request.model,
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": 0,  # Ollama doesn't provide token counts
                "output_tokens": 0
            }
        }
        
        return anthropic_response
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ollama generation failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)