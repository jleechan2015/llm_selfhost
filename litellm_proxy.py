#!/usr/bin/env python3
"""
LiteLLM-based proxy for vast.ai
Proper API translation between Anthropic and Ollama formats
"""

import os
from litellm import completion
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import uvicorn
from datetime import datetime

app = FastAPI(title="LiteLLM Proxy for Vast.ai")

# Configuration
OLLAMA_HOST = "localhost:11434" 
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}"

class Message(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]  # Handle both simple strings and complex content

class ChatRequest(BaseModel):
    messages: List[Message]
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7
    model: Optional[str] = "qwen2.5-coder:7b"

def extract_text_content(content: Union[str, List[Dict[str, Any]]]) -> str:
    """Extract plain text from Claude CLI's complex content format"""
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif "text" in item:
                    text_parts.append(item["text"])
        return "\n".join(text_parts)
    
    return str(content)

@app.get("/")
async def root():
    return {
        "service": "LiteLLM Proxy for Vast.ai",
        "status": "running",
        "ollama_host": OLLAMA_HOST,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    try:
        # Test Ollama connection via LiteLLM
        response = completion(
            model=f"ollama/qwen2.5-coder:7b",
            messages=[{"role": "user", "content": "hi"}],
            api_base=OLLAMA_BASE_URL,
            max_tokens=1
        )
        ollama_healthy = bool(response)
    except Exception as e:
        ollama_healthy = False
    
    return {
        "status": "healthy" if ollama_healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "ollama": "healthy" if ollama_healthy else "unhealthy",
            "litellm": "enabled"
        }
    }

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen2.5-coder:7b",
                "object": "model",
                "created": int(datetime.now().timestamp()),
                "owned_by": "ollama"
            }
        ]
    }

@app.post("/v1/messages")
async def create_message(request: ChatRequest):
    try:
        # Convert messages to LiteLLM format
        litellm_messages = []
        for msg in request.messages:
            content = extract_text_content(msg.content)
            litellm_messages.append({
                "role": msg.role,
                "content": content
            })
        
        # Call LiteLLM with Ollama
        response = completion(
            model=f"ollama/{request.model}",
            messages=litellm_messages,
            api_base=OLLAMA_BASE_URL,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        # Convert to Anthropic format
        anthropic_response = {
            "id": f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "type": "message", 
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": response.choices[0].message.content
                }
            ],
            "model": request.model,
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
                "output_tokens": response.usage.completion_tokens if hasattr(response, 'usage') else 0
            }
        }
        
        return anthropic_response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LiteLLM generation failed: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)