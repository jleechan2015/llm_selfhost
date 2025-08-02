#!/usr/bin/env python3
"""
Cerebras API Proxy for Claude CLI Compatibility
Converts Anthropic Messages API format to OpenAI Chat Completions format
"""

import os
import json
import logging
import time
import random
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import requests
import uvicorn
from typing import Dict, Any, List, Iterator
import asyncio

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

def retry_with_backoff(func, max_retries=3, base_delay=1.0):
    """
    Retry function with exponential backoff for rate limiting
    """
    for attempt in range(max_retries + 1):
        try:
            response = func()

            # If we get a 429 (rate limit), handle it specially
            if response.status_code == 429:
                if attempt == max_retries:
                    logger.error(f"Max retries ({max_retries}) exceeded for rate limiting")
                    return response

                # Get retry delay from header or use exponential backoff
                retry_after_ms = response.headers.get('retry-after-ms')
                if retry_after_ms:
                    delay = float(retry_after_ms) / 1000.0  # Convert ms to seconds
                else:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)

                logger.warning(f"Rate limited (429). Attempt {attempt + 1}/{max_retries + 1}. Waiting {delay:.2f}s...")
                time.sleep(delay)
                continue

            # For any other status code, return immediately
            return response

        except Exception as e:
            if attempt == max_retries:
                logger.error(f"Max retries exceeded. Last error: {e}")
                raise

            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"Request failed: {e}. Retrying in {delay:.2f}s...")
            time.sleep(delay)

    return None

def convert_openai_chunk_to_anthropic(openai_chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert OpenAI streaming chunk to Anthropic streaming format"""
    chunks = []

    if "choices" not in openai_chunk:
        return chunks

    choice = openai_chunk["choices"][0]
    delta = choice.get("delta", {})

    # Handle role start
    if "role" in delta:
        chunks.append({
            "type": "message_start",
            "message": {
                "id": openai_chunk.get("id", ""),
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": openai_chunk.get("model", DEFAULT_MODEL),
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0}
            }
        })
        chunks.append({
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""}
        })

    # Handle content delta
    if "content" in delta and delta["content"]:
        chunks.append({
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": delta["content"]}
        })

    # Handle finish
    if choice.get("finish_reason"):
        chunks.append({
            "type": "content_block_stop",
            "index": 0
        })

        # Extract usage if available
        usage = openai_chunk.get("usage", {})
        chunks.append({
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn" if choice["finish_reason"] == "stop" else "max_tokens"},
            "usage": {
                "output_tokens": usage.get("completion_tokens", 0)
            }
        })

    return chunks

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

        # Send to Cerebras with retry logic
        def make_request():
            return requests.post(
                f"{CEREBRAS_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {CEREBRAS_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=openai_request,
                timeout=60,
                stream=openai_request.get("stream", False)  # Enable streaming if requested
            )

        response = retry_with_backoff(make_request, max_retries=3, base_delay=1.0)

        # Log raw response for debugging
        logger.info(f"Cerebras response status: {response.status_code}")
        logger.info(f"Cerebras response headers: {dict(response.headers)}")

        # Monitor rate limits and warn user
        remaining_requests = response.headers.get('x-ratelimit-remaining-requests-day')
        remaining_tokens = response.headers.get('x-ratelimit-remaining-tokens-minute')

        if remaining_requests:
            remaining_req_count = int(remaining_requests)
            if remaining_req_count < 10:
                logger.warning(f"⚠️ LOW RATE LIMIT: Only {remaining_req_count} requests remaining today!")
            elif remaining_req_count < 25:
                logger.info(f"📊 Rate limit status: {remaining_req_count} requests remaining today")

        if remaining_tokens:
            remaining_token_count = int(remaining_tokens)
            if remaining_token_count < 10000:
                logger.warning(f"⚠️ LOW TOKEN LIMIT: Only {remaining_token_count:,} tokens remaining this minute!")
            elif remaining_token_count < 50000:
                logger.info(f"📊 Token limit status: {remaining_token_count:,} tokens remaining this minute")

        if response.status_code != 200:
            # For error responses, we can still read .text
            error_text = response.text
            logger.error(f"Cerebras API error: {response.status_code} - {error_text}")
            error_response = {
                "id": "error",
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": f"Cerebras API error {response.status_code}: {error_text}"
                }
            }
            return JSONResponse(content=error_response, status_code=response.status_code)

        # Check if this is a streaming response
        is_streaming = openai_request.get("stream", False)

        if is_streaming:
            logger.info("Processing streaming response")

            # Return Anthropic-formatted streaming response
            def stream_generator():
                try:
                    # Process the streaming response line by line
                    for line in response.iter_lines(decode_unicode=True):
                        if line:
                            logger.debug(f"Streaming line: {line[:200]}...")

                            # Parse OpenAI SSE format and convert to Anthropic
                            if line.startswith("data: "):
                                data_content = line[6:]  # Remove "data: " prefix

                                if data_content.strip() == "[DONE]":
                                    # OpenAI end-of-stream marker
                                    yield "event: message_stop\ndata: {\"type\":\"message_stop\"}\n\n"
                                    break

                                try:
                                    openai_chunk = json.loads(data_content)
                                    # Convert OpenAI chunk to Anthropic format
                                    anthropic_chunks = convert_openai_chunk_to_anthropic(openai_chunk)
                                    for anthropic_chunk in anthropic_chunks:
                                        yield f"data: {json.dumps(anthropic_chunk)}\n\n"
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to parse streaming chunk: {data_content[:200]}")
                                    continue

                except Exception as e:
                    logger.error(f"Error in streaming: {e}")
                    error_chunk = {
                        "type": "error",
                        "error": {"type": "api_error", "message": str(e)}
                    }
                    yield f"event: error\ndata: {json.dumps(error_chunk)}\n\n"

            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )
        else:
            # Non-streaming response (original logic)
            response_text = response.text
            logger.info(f"Non-streaming response body: {response_text[:500]}...")

            # Handle empty response
            if not response_text.strip():
                logger.error("Cerebras returned empty response")
                error_response = {
                    "id": "error",
                    "type": "error",
                    "error": {
                        "type": "api_error",
                        "message": "Cerebras API returned empty response"
                    }
                }
                return JSONResponse(content=error_response, status_code=500)

            # Parse JSON response
            try:
                openai_response = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Cerebras response as JSON: {e}")
                logger.error(f"Raw response: {response.text}")
                error_response = {
                    "id": "error",
                    "type": "error",
                    "error": {
                        "type": "api_error",
                        "message": f"Invalid JSON response from Cerebras: {response.text[:200]}"
                    }
                }
                return JSONResponse(content=error_response, status_code=500)

            # Convert response back to Anthropic format
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