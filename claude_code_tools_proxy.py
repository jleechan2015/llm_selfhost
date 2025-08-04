#!/usr/bin/env python3
"""
Tool-Enabled Claude Code CLI Proxy
Implements Claude Code's tool protocol with actual tool execution
"""

import os
import json
import subprocess
import tempfile
import uuid
import time
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import urllib.request
import urllib.parse

# Use system HTTP server - no external dependencies
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import socket

class ClaudeCodeTools:
    """Implements Claude Code's core tools"""
    
    def __init__(self):
        self.temp_files = {}
        self.session_id = str(uuid.uuid4())
        
    def bash(self, command: str) -> Dict[str, Any]:
        """Execute bash commands like Claude Code's bash tool with security checks"""
        
        # Security checks
        dangerous_commands = [
            'rm -rf /', 'rm -rf *', 'format', 'fdisk', 'mkfs',
            'dd if=', ':(){ :|:& };:', 'chmod -R 777 /',
            'chown -R', 'passwd', 'sudo su', 'su -'
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
                with open(path, 'w') as f:
                    f.write(file_text or "")
                return {
                    "type": "str_replace_editor",
                    "result": f"File created successfully at: {path}"
                }
            except Exception as e:
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

class ClaudeCodeProxy(BaseHTTPRequestHandler):
    """HTTP request handler for Claude Code proxy"""
    
    tools = ClaudeCodeTools()
    vast_api_url = "http://localhost:8000"
    
    def log_message(self, format, *args):
        """Override to reduce logging noise"""
        pass
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/health":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            health_data = {
                "status": "healthy",
                "claude_code_proxy": "active",
                "tools_enabled": True,
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(health_data).encode())
            
        elif self.path == "/v1/models":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            models_data = {
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
            }
            self.wfile.write(json.dumps(models_data).encode())
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path.startswith("/v1/messages"):
            self.handle_messages()
        else:
            self.send_error(404)
    
    def handle_messages(self):
        """Handle Claude Code messages with tool support"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode())
            
            print(f"📨 Claude Code request: {len(request_data.get('messages', []))} messages")
            
            # Check if this is a tool call response
            messages = request_data.get('messages', [])
            if self.has_tool_calls(messages):
                response = self.handle_tool_calls(messages)
            else:
                # Forward to Qwen model
                response = self.forward_to_qwen(request_data)
                
                # Check if response should trigger tools
                if self.should_use_tools(response):
                    response = self.enhance_with_tools(response)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"❌ Error handling request: {e}")
            self.send_error(500)
    
    def has_tool_calls(self, messages: List[Dict]) -> bool:
        """Check if messages contain tool calls to execute"""
        for msg in messages:
            content = msg.get('content', '')
            if isinstance(content, str):
                if '<bash>' in content or '<str_replace_editor>' in content:
                    return True
        return False
    
    def should_use_tools(self, response: Dict) -> bool:
        """Determine if response should trigger tool usage"""
        content = self.extract_text_content(response)
        
        # Look for patterns that indicate tool usage
        patterns = [
            r'```bash\n(.*?)\n```',
            r'I\'ll (run|execute|create|write|edit)',
            r'Let me (run|execute|create|write|edit)',
        ]
        
        for pattern in patterns:
            if re.search(pattern, content, re.DOTALL | re.IGNORECASE):
                return True
        return False
    
    def enhance_with_tools(self, response: Dict) -> Dict:
        """Enhance response by executing tools mentioned in the text"""
        content = self.extract_text_content(response)
        
        # Look for bash commands
        bash_pattern = r'```bash\n(.*?)\n```'
        matches = re.findall(bash_pattern, content, re.DOTALL)
        
        enhanced_content = content
        for command in matches:
            if command.strip():
                result = self.tools.bash(command.strip())
                
                # Insert actual execution results
                execution_block = f"\n\n**Execution Result:**\n```\nExit code: {result['exit_code']}\n"
                if result['stdout']:
                    execution_block += f"Output:\n{result['stdout']}\n"
                if result['stderr']:
                    execution_block += f"Error:\n{result['stderr']}\n"
                execution_block += "```"
                
                enhanced_content = enhanced_content.replace(
                    f"```bash\n{command}\n```",
                    f"```bash\n{command}\n```{execution_block}"
                )
        
        # Update response with enhanced content
        if "content" in response and isinstance(response["content"], list):
            response["content"][0]["text"] = enhanced_content
        
        return response
    
    def forward_to_qwen(self, request_data: Dict) -> Dict:
        """Forward request to Qwen backend with function calling support"""
        try:
            # Enhance messages with tool calling instructions
            messages = request_data.get('messages', [])
            enhanced_messages = self.add_tool_instructions(messages)
            
            enhanced_request = request_data.copy()
            enhanced_request['messages'] = enhanced_messages
            enhanced_request['model'] = 'qwen3-coder'  # Use correct backend model
            
            # Prepare request
            req_data = json.dumps(enhanced_request).encode()
            req = urllib.request.Request(
                f"{self.vast_api_url}/v1/messages",
                data=req_data,
                headers={'Content-Type': 'application/json'}
            )
            
            # Send request  
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    response_data = response.read().decode()
                    print(f"✅ Qwen response received ({len(response_data)} chars)")
                    return json.loads(response_data)
            except urllib.error.HTTPError as e:
                error_msg = e.read().decode() if hasattr(e, 'read') else str(e)
                print(f"❌ HTTP Error {e.code}: {error_msg}")
                raise
                
        except Exception as e:
            print(f"❌ Error forwarding to Qwen: {e}")
            return {
                "id": f"msg_{int(time.time())}",
                "type": "message",
                "role": "assistant", 
                "content": [{"type": "text", "text": f"Error connecting to Qwen backend: {str(e)}"}],
                "model": "qwen3-coder",
                "stop_reason": "error"
            }
    
    def add_tool_instructions(self, messages: List[Dict]) -> List[Dict]:
        """Add tool calling instructions to messages for better Qwen integration"""
        
        # Add system message with tool instructions if not present
        has_system = any(msg.get('role') == 'system' for msg in messages)
        
        enhanced_messages = []
        
        if not has_system:
            tool_system_msg = {
                "role": "system",
                "content": """You are a helpful coding assistant with access to system tools. 

When you need to execute commands or work with files, use these patterns:
- For bash commands: Write ```bash\\ncommand\\n``` blocks
- For file operations: Use clear descriptions like "I'll create a file" or "Let me run this command"
- Always show the actual commands you want to execute in code blocks
- Be specific about file paths and command syntax

You can execute bash commands, create/edit files, and help with coding tasks."""
            }
            enhanced_messages.append(tool_system_msg)
        
        enhanced_messages.extend(messages)
        return enhanced_messages
    
    def extract_text_content(self, response: Dict) -> str:
        """Extract text content from Claude API response"""
        if "content" in response and isinstance(response["content"], list):
            for item in response["content"]:
                if item.get("type") == "text":
                    return item.get("text", "")
        return ""

def main():
    """Start the Claude Code proxy server"""
    PORT = 8001
    
    print("🚀 Starting Claude Code Tools Proxy")
    print(f"📍 Port: {PORT}")
    print(f"📡 Backend: http://localhost:8000")
    print("🔧 Tools: bash, str_replace_editor")
    print("")
    print("To use with Claude Code CLI:")
    print(f'export ANTHROPIC_BASE_URL="http://localhost:{PORT}"')
    print('claude "Write a Python script and run it"')
    print("")
    
    server = HTTPServer(('localhost', PORT), ClaudeCodeProxy)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down proxy server")
        server.shutdown()

if __name__ == "__main__":
    main()