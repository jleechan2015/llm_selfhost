#!/usr/bin/env python3
"""
Tool-Enabled Cerebras Proxy Server
Combines Cerebras Cloud API integration with full tool execution capabilities
Designed for Claude Code CLI integration with Cerebras 480B model.
"""

import os
import sys
import json
import time
import hashlib
import traceback
import subprocess
import tempfile
import uuid
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Core dependencies only
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("🧠 Starting Tool-Enabled Cerebras Proxy Server...")
print("=" * 50)

# Environment variables
CEREBRAS_API_KEY = os.getenv('CEREBRAS_API_KEY')
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
DEFAULT_MODEL = "qwen-3-coder-480b"
API_PORT = int(os.getenv('PORT', 8002))

if not CEREBRAS_API_KEY:
    print("❌ CEREBRAS_API_KEY environment variable not set")
    print("💡 Get your API key from: https://inference.cerebras.ai/")
    sys.exit(1)

print(f"✅ Cerebras API key configured")
print(f"🌐 Cerebras API: {CEREBRAS_BASE_URL}")
print(f"📱 Model: {DEFAULT_MODEL}")

class ClaudeCodeTools:
    """Implements Claude Code's core tools with Cerebras compatibility"""
    
    def __init__(self):
        self.temp_files = {}
        self.session_id = str(uuid.uuid4())
        print(f"🔧 Tools session: {self.session_id}")
        
    def bash(self, command: str) -> Dict[str, Any]:
        """Execute bash commands with security checks"""
        
        # Security checks
        dangerous_commands = [
            'rm -rf /', 'rm -rf *', 'format', 'fdisk', 'mkfs',
            'dd if=', ':(){ :|:& };:', 'chmod -R 777 /',
            'chown -R', 'passwd', 'sudo su', 'su -',
            'curl http://169.254.169.254'  # Block metadata access
        ]
        
        command_lower = command.lower()
        for dangerous in dangerous_commands:
            if dangerous in command_lower:
                return {
                    "type": "bash",
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": f"Security: Dangerous command blocked: {dangerous}"
                }
        
        try:
            print(f"🔧 Executing bash: {command}")
            
            # Limit command length
            if len(command) > 1000:
                return {
                    "type": "bash",
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": "Command too long (max 1000 characters)"
                }
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd(),
                env=dict(os.environ, PATH=os.environ.get('PATH', ''))
            )
            
            print(f"✅ Bash result: exit_code={result.returncode}")
            
            return {
                "type": "bash",
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "type": "bash",
                "exit_code": 124,
                "stdout": "",
                "stderr": "Command timed out after 30 seconds"
            }
        except Exception as e:
            return {
                "type": "bash", 
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e)
            }
    
    def str_replace_editor(self, command: str, path: str = None, file_text: str = None, 
                          new_str: str = None, old_str: str = None, insert_line: int = None,
                          view_range: List[int] = None) -> Dict[str, Any]:
        """File editing tool like Claude Code's str_replace_editor"""
        
        if command == "create":
            try:
                print(f"📝 Creating file: {path}")
                with open(path, 'w') as f:
                    f.write(file_text or "")
                print(f"✅ File created successfully: {path}")
                return {
                    "type": "str_replace_editor",
                    "result": f"File created successfully at: {path}"
                }
            except Exception as e:
                print(f"❌ Failed to create file {path}: {e}")
                return {
                    "type": "str_replace_editor",
                    "error": f"Failed to create file: {str(e)}"
                }
                
        elif command == "view":
            try:
                with open(path, 'r') as f:
                    content = f.read()
                
                if view_range:
                    lines = content.split('\n')
                    start, end = view_range
                    content = '\n'.join(lines[start-1:end])
                
                return {
                    "type": "str_replace_editor",
                    "result": content
                }
            except Exception as e:
                return {
                    "type": "str_replace_editor", 
                    "error": f"Failed to read file: {str(e)}"
                }
                
        elif command == "str_replace":
            try:
                with open(path, 'r') as f:
                    content = f.read()
                
                if old_str not in content:
                    return {
                        "type": "str_replace_editor",
                        "error": f"String not found: {old_str[:50]}..."
                    }
                
                new_content = content.replace(old_str, new_str, 1)
                
                with open(path, 'w') as f:
                    f.write(new_content)
                
                print(f"✅ String replaced in {path}")
                return {
                    "type": "str_replace_editor",
                    "result": f"String replaced successfully in {path}"
                }
            except Exception as e:
                return {
                    "type": "str_replace_editor",
                    "error": f"Failed to replace string: {str(e)}"
                }
        
        return {"type": "str_replace_editor", "error": f"Unknown command: {command}"}

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Direct file write tool for Claude Code CLI compatibility"""
        try:
            print(f"📝 Writing file: {path}")
            with open(path, 'w') as f:
                f.write(content)
            print(f"✅ File written successfully: {path}")
            return {
                "type": "write_file",
                "result": f"File written successfully at: {path}"
            }
        except Exception as e:
            print(f"❌ Failed to write file {path}: {e}")
            return {
                "type": "write_file",
                "error": f"Failed to write file: {str(e)}"
            }

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

# Initialize FastAPI app
app = FastAPI(title="Tool-Enabled Cerebras Proxy", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize tools
tools = ClaudeCodeTools()

def should_use_tools(content: str) -> bool:
    """Determine if response should trigger tool usage"""
    patterns = [
        r'```bash\n(.*?)\n```',
        r'I\'ll (run|execute|create|write|edit)',
        r'Let me (run|execute|create|write|edit)',
        r'I need to (run|execute|create|write|edit)',
        r'I\'m going to (run|execute|create|write|edit)',
        r'Creating? (a )?file',
        r'Writing (a )?file',
        r'Running (the )?command',
    ]
    
    for pattern in patterns:
        if re.search(pattern, content, re.DOTALL | re.IGNORECASE):
            return True
    return False

def extract_tool_requests(content: str) -> List[Dict]:
    """Extract tool requests from Claude's response"""
    tool_requests = []
    
    # Extract bash commands
    bash_pattern = r'```bash\n(.*?)\n```'
    bash_matches = re.findall(bash_pattern, content, re.DOTALL)
    
    for command in bash_matches:
        if command.strip():
            tool_requests.append({
                "type": "bash",
                "command": command.strip()
            })
    
    # Extract file creation requests (simple pattern matching)
    if re.search(r'creat[ei]ng?\s+.*file.*named?\s+"([^"]+)"', content, re.IGNORECASE):
        file_match = re.search(r'creat[ei]ng?\s+.*file.*named?\s+"([^"]+)"', content, re.IGNORECASE)
        if file_match:
            filename = file_match.group(1)
            # Look for content in the same response
            content_match = re.search(r'with.*content\s+"([^"]+)"', content, re.IGNORECASE)
            file_content = content_match.group(1) if content_match else ""
            
            tool_requests.append({
                "type": "str_replace_editor",
                "command": "create",
                "path": filename,
                "file_text": file_content
            })
    
    return tool_requests

def execute_tools(tool_requests: List[Dict]) -> str:
    """Execute tool requests and return results"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🔧 [{timestamp}] CEREBRAS TOOL EXECUTION STARTED - {len(tool_requests)} tools requested")
    
    results = []
    
    for i, request in enumerate(tool_requests):
        try:
            tool_type = request["type"]
            print(f"🛠️  [{timestamp}] Tool {i+1}/{len(tool_requests)}: {tool_type}")
            
            if request["type"] == "bash":
                command = request["command"]
                print(f"📝 [{timestamp}] Executing bash: {command}")
                result = tools.bash(command)
                print(f"✅ [{timestamp}] Bash completed - Exit code: {result['exit_code']}")
                results.append(f"\n**Bash Execution:**\n```\nCommand: {command}\nExit code: {result['exit_code']}\nOutput: {result['stdout']}\nError: {result['stderr']}\n```")
            
            elif request["type"] == "str_replace_editor":
                operation = request.get("command", "unknown")
                file_path = request.get("path", "unknown")
                print(f"📄 [{timestamp}] File operation: {operation} on {file_path}")
                result = tools.str_replace_editor(**{k: v for k, v in request.items() if k != "type"})
                if "error" in result:
                    print(f"❌ [{timestamp}] File operation failed: {result['error']}")
                    results.append(f"\n**File Operation Error:** {result['error']}")
                else:
                    print(f"✅ [{timestamp}] File operation successful")
                    results.append(f"\n**File Operation:** {result['result']}")
            
        except Exception as e:
            print(f"❌ [{timestamp}] Tool execution error: {str(e)}")
            results.append(f"\n**Tool Error:** {str(e)}")
    
    print(f"🏁 [{timestamp}] CEREBRAS TOOL EXECUTION COMPLETED - {len(tool_requests)} tools processed")
    return "\n".join(results)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    # Check Cerebras API connection
    cerebras_status = "unknown"
    try:
        response = requests.get(
            f"{CEREBRAS_BASE_URL}/models",
            headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}"},
            timeout=5
        )
        if response.status_code in [200, 429]:  # 429 is OK, just rate limited
            cerebras_status = "healthy"
        else:
            cerebras_status = f"error_{response.status_code}"
    except Exception as e:
        cerebras_status = f"unreachable"
    
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cerebras_tools_proxy": "active",
        "tools_enabled": True,
        "components": {
            "cerebras_api": cerebras_status,
            "model": DEFAULT_MODEL
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
    try:
        response = requests.get(
            f"{CEREBRAS_BASE_URL}/models",
            headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}"},
            timeout=10
        )
        
        if response.status_code == 200:
            return JSONResponse(response.json())
        else:
            # Return fallback model list
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
                        "id": DEFAULT_MODEL,
                        "object": "model", 
                        "created": int(time.time()),
                        "owned_by": "cerebras",
                        "type": "text"
                    }
                ]
            })
            
    except Exception as e:
        logger.error(f"Failed to get models: {e}")
        # Return basic model list as fallback
        return JSONResponse({
            "object": "list",
            "data": [
                {
                    "id": "claude-3-5-sonnet-20241022",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "anthropic",
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
        
        # Forward to Cerebras API
        try:
            # Add tool instructions to system message
            enhanced_messages = []
            has_system = any(msg.get('role') == 'system' for msg in messages)
            
            if not has_system:
                enhanced_messages.append({
                    "role": "system",
                    "content": """You are a helpful coding assistant with access to system tools.

When you need to execute commands or work with files, be explicit about your actions:
- For bash commands: Write ```bash\\ncommand\\n``` blocks
- For file creation: Say "I'll create a file named 'filename'" and include the content
- Always show the actual commands you want to execute in code blocks
- Be specific about file paths and command syntax

You have access to bash execution and file operations."""
                })
            
            enhanced_messages.extend(messages)
            
            # Convert to OpenAI format for Cerebras
            cerebras_request = {
                "model": DEFAULT_MODEL,
                "messages": enhanced_messages,
                "max_tokens": request_data.get("max_tokens", 1000),
                "temperature": request_data.get("temperature", 0.7),
                "stream": False
            }
            
            print(f"🔄 Forwarding to Cerebras: {CEREBRAS_BASE_URL}")
            
            # Make request with retry logic
            def make_request():
                return requests.post(
                    f"{CEREBRAS_BASE_URL}/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {CEREBRAS_API_KEY}"
                    },
                    json=cerebras_request,
                    timeout=60
                )
            
            response = retry_with_backoff(make_request)
            
            if not response or response.status_code != 200:
                logger.error(f"Cerebras API error: {response.status_code if response else 'No response'}")
                raise HTTPException(
                    status_code=response.status_code if response else 500,
                    detail=response.text if response else "No response from Cerebras API"
                )
            
            cerebras_response = response.json()
            
            # Convert to Anthropic format
            content = cerebras_response["choices"][0]["message"]["content"]
            
            anthropic_response = {
                "id": f"msg_{int(time.time())}",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": content
                    }
                ],
                "model": "claude-3-5-sonnet-20241022",
                "stop_reason": "end_turn",
                "usage": {
                    "input_tokens": cerebras_response.get("usage", {}).get("prompt_tokens", 0),
                    "output_tokens": cerebras_response.get("usage", {}).get("completion_tokens", 0)
                }
            }
            
            # Check if we should execute tools
            if should_use_tools(content):
                print("🔧 Tool execution triggered")
                
                # Extract and execute tools
                tool_requests = extract_tool_requests(content)
                if tool_requests:
                    tool_results = execute_tools(tool_requests)
                    
                    # Enhance response with tool results
                    enhanced_content = content + tool_results
                    anthropic_response["content"][0]["text"] = enhanced_content
                    print(f"✅ Tools executed: {len(tool_requests)} operations")
            
            print(f"✅ Response ready ({len(content)} chars)")
            return JSONResponse(anthropic_response)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Cerebras request failed: {e}")
            raise HTTPException(status_code=503, detail=f"Cerebras service unavailable: {str(e)}")
            
    except Exception as e:
        print(f"❌ Error processing request: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("\n🧠 Tool-Enabled Cerebras Proxy Server")
    print("=" * 40)
    print(f"🌐 Port: {API_PORT}")
    print(f"🤖 Cerebras: {CEREBRAS_BASE_URL}")
    print(f"📱 Model: {DEFAULT_MODEL}")
    print(f"🔧 Tools: bash, str_replace_editor, write_file")
    print("\nReady for Claude Code CLI integration!")
    print("=" * 40)
    
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)