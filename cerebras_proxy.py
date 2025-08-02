#!/usr/bin/env python3
"""
Cerebras API Proxy for Claude CLI Compatibility
Converts Anthropic Messages API format to OpenAI Chat Completions format
"""

import os
import json
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import requests
import uvicorn
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Cerebras API Proxy", version="1.0.0")

# Configuration
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
DEFAULT_MODEL = "qwen-3-coder-480b"

if not CEREBRAS_API_KEY:
    logger.error("CEREBRAS_API_KEY environment variable not set")
    exit(1)

def convert_anthropic_to_openai(anthropic_request: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Anthropic Messages API format to OpenAI Chat Completions format"""

    messages = anthropic_request.get("messages", [])

    # Convert messages format
    openai_messages = []
    for msg in messages:
        content = msg.get("content", "")

        # Handle Anthropic's complex content format
        if isinstance(content, list):
            # Extract text from content blocks
            text_content = ""
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content += block.get("text", "")
                elif isinstance(block, str):
                    text_content += block
            content = text_content
        elif not isinstance(content, str):
            content = str(content)

        openai_messages.append({
            "role": msg["role"],
            "content": content
        })

    # Build OpenAI request - always use our DEFAULT_MODEL (qwen-3-coder-480b)
    openai_request = {
        "model": DEFAULT_MODEL,  # Force our model instead of what Claude CLI requests
        "messages": openai_messages,
        "max_tokens": anthropic_request.get("max_tokens", 1000),
        "temperature": anthropic_request.get("temperature", 0.7),
        "stream": anthropic_request.get("stream", False)
    }

    return openai_request

def convert_openai_to_anthropic(openai_response: Dict[str, Any]) -> Dict[str, Any]:
    """Convert OpenAI Chat Completions response to Anthropic Messages format"""

    if "choices" not in openai_response:
        return {"error": "Invalid OpenAI response format"}

    choice = openai_response["choices"][0]
    message = choice.get("message", {})

    # Build Anthropic response
    anthropic_response = {
        "id": openai_response.get("id", ""),
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": message.get("content", "")
            }
        ],
        "model": openai_response.get("model", DEFAULT_MODEL),
        "stop_reason": "end_turn" if choice.get("finish_reason") == "stop" else "max_tokens",
        "stop_sequence": None,
        "usage": {
            "input_tokens": openai_response.get("usage", {}).get("prompt_tokens", 0),
            "output_tokens": openai_response.get("usage", {}).get("completion_tokens", 0)
        }
    }

    return anthropic_response

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "cerebras-proxy", "model": DEFAULT_MODEL}

@app.get("/v1/models")
async def list_models():
    """List available models"""
    try:
        response = requests.get(
            f"{CEREBRAS_BASE_URL}/models",
            headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}"}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/messages")
async def create_message(request: Request):
    """Handle Anthropic Messages API requests and convert to OpenAI format"""
    try:
        # Parse Anthropic request
        anthropic_request = await request.json()
        logger.info(f"Received request for model: {anthropic_request.get('model', 'unknown')}")

        # Convert to OpenAI format
        requested_model = anthropic_request.get('model', 'unknown')
        openai_request = convert_anthropic_to_openai(anthropic_request)
        if requested_model != DEFAULT_MODEL:
            logger.info(f"Model override: {requested_model} -> {DEFAULT_MODEL}")
        logger.info(f"Using Cerebras model: {openai_request['model']}")

        # Send to Cerebras
        response = requests.post(
            f"{CEREBRAS_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {CEREBRAS_API_KEY}",
                "Content-Type": "application/json"
            },
            json=openai_request,
            timeout=60
        )

        if response.status_code != 200:
            logger.error(f"Cerebras API error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)

        # Convert response back to Anthropic format
        openai_response = response.json()
        anthropic_response = convert_openai_to_anthropic(openai_response)

        logger.info(f"Successfully converted response")
        return JSONResponse(content=anthropic_response)

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def detailed_health():
    """Detailed health check with Cerebras connectivity"""
    try:
        # Test Cerebras connection
        response = requests.get(
            f"{CEREBRAS_BASE_URL}/models",
            headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}"},
            timeout=10
        )

        if response.status_code == 200:
            models = response.json().get("data", [])
            model_names = [model.get("id", "unknown") for model in models]

            return {
                "status": "healthy",
                "service": "cerebras-proxy",
                "cerebras_connection": "connected",
                "available_models": model_names[:5],  # Show first 5 models
                "default_model": DEFAULT_MODEL,
                "api_key_valid": True
            }
        else:
            return {
                "status": "degraded",
                "service": "cerebras-proxy",
                "cerebras_connection": "failed",
                "error": f"HTTP {response.status_code}",
                "api_key_valid": False
            }

    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "cerebras-proxy",
            "cerebras_connection": "error",
            "error": str(e),
            "api_key_valid": False
        }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8002))
    logger.info(f"Starting Cerebras API proxy on port {port}")
    logger.info(f"Using model: {DEFAULT_MODEL}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )