#!/usr/bin/env python3
"""
Tool-Enabled Vast.ai Proxy Server
Combines caching capabilities of simple_api_proxy.py with tool execution from claude_code_tools_proxy.py
Designed specifically for vast.ai deployment with Claude Code CLI integration.
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
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Core dependencies only
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests

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

class ClaudeCodeTools:
    """Implements Claude Code's core tools with vast.ai compatibility"""
    
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

# Initialize tools
tools = ClaudeCodeTools()

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
    print(f"🔧 [{timestamp}] TOOL EXECUTION STARTED - {len(tool_requests)} tools requested")
    
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
    
    print(f"🏁 [{timestamp}] TOOL EXECUTION COMPLETED - {len(tool_requests)} tools processed")
    return "\n".join(results)

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