#!/usr/bin/env python3
"""
Cerebras API Proxy for Claude CLI Compatibility (Simple Version)
Converts Anthropic Messages API format to OpenAI Chat Completions format
Uses built-in Python http.server to avoid external dependencies
"""

import os
import json
import requests
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
DEFAULT_MODEL = "qwen-3-coder-480b"
PORT = int(os.getenv("PORT", 8002))

if not CEREBRAS_API_KEY:
    logger.error("CEREBRAS_API_KEY environment variable not set")
    exit(1)

def retry_with_backoff(func, max_retries=3, base_delay=1.0):
    """Retry function with exponential backoff for rate limiting"""
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
                    delay = float(retry_after_ms) / 1000.0
                else:
                    delay = base_delay * (2 ** attempt)
                
                logger.info(f"Rate limited, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries + 1})")
                time.sleep(delay)
                continue
            
            return response
            
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"Max retries exceeded: {e}")
                raise
            
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Request failed, retrying in {delay:.2f}s: {e}")
            time.sleep(delay)
    
    return None

class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/health":
            self.handle_health()
        elif parsed_path.path == "/v1/models":
            self.handle_models()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/v1/messages":
            self.handle_messages()
        else:
            self.send_error(404, "Not Found")
    
    def handle_health(self):
        """Health check endpoint"""
        try:
            # Test Cerebras API connection
            response = requests.get(
                f"{CEREBRAS_BASE_URL}/models",
                headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}"},
                timeout=5
            )
            if response.status_code in [200, 429]:  # 429 is OK, just rate limited
                health_data = {
                    "status": "healthy",
                    "cerebras_proxy": "active",
                    "cerebras_api": CEREBRAS_BASE_URL,
                    "model": DEFAULT_MODEL,
                    "timestamp": time.time()
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(health_data).encode())
                return
        except Exception as e:
            logger.error(f"Health check failed: {e}")
        
        self.send_error(503, "Cerebras API not accessible")
    
    def handle_models(self):
        """List available models"""
        try:
            response = requests.get(
                f"{CEREBRAS_BASE_URL}/models",
                headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}"},
                timeout=10
            )
            self.send_response(response.status_code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            if response.status_code == 200:
                self.wfile.write(response.content)
            else:
                # Return a basic model list if API call fails
                fallback = {
                    "object": "list",
                    "data": [
                        {
                            "id": DEFAULT_MODEL,
                            "object": "model",
                            "created": int(time.time()),
                            "owned_by": "cerebras"
                        }
                    ]
                }
                self.wfile.write(json.dumps(fallback).encode())
                
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            self.send_error(503, "Cerebras API not accessible")
    
    def handle_messages(self):
        """Handle Anthropic-style messages and convert to OpenAI format"""
        try:
            content_length = int(self.headers['Content-Length'])
            request_body = self.rfile.read(content_length)
            data = json.loads(request_body.decode())
            
            logger.info(f"Received Claude request")
            
            # Convert Anthropic format to OpenAI format
            openai_request = {
                "model": DEFAULT_MODEL,
                "messages": data.get("messages", []),
                "max_tokens": data.get("max_tokens", 1000),
                "temperature": data.get("temperature", 0.7),
                "stream": False
            }
            
            # Make request to Cerebras with retry logic
            def make_request():
                return requests.post(
                    f"{CEREBRAS_BASE_URL}/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {CEREBRAS_API_KEY}"
                    },
                    json=openai_request,
                    timeout=60
                )
            
            response = retry_with_backoff(make_request)
            
            if not response or response.status_code != 200:
                logger.error(f"Cerebras API error: {response.status_code if response else 'No response'}")
                self.send_error(response.status_code if response else 500, 
                               response.text if response else "No response from Cerebras API")
                return
            
            openai_response = response.json()
            logger.info(f"Cerebras response received")
            
            # Convert OpenAI response to Anthropic format
            content = openai_response["choices"][0]["message"]["content"]
            
            anthropic_response = {
                "id": f"msg_{int(time.time())}",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": content}],
                "model": DEFAULT_MODEL,
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {
                    "input_tokens": openai_response.get("usage", {}).get("prompt_tokens", 0),
                    "output_tokens": openai_response.get("usage", {}).get("completion_tokens", 0)
                }
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(anthropic_response).encode())
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            self.send_error(500, str(e))

def run_server():
    """Run the proxy server"""
    server = HTTPServer(('0.0.0.0', PORT), ProxyHandler)
    logger.info(f"Starting Cerebras API proxy on port {PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()