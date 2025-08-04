#!/usr/bin/env python3
"""
Enhanced proxy for Claude Code CLI integration with tool support.
Translates Claude Code tool calls to actual system commands.
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
import requests
import uuid
from datetime import datetime

app = FastAPI(title="Claude Code Proxy with Tool Support")

# Configuration
VAST_API_URL = os.getenv("VAST_API_URL", "http://localhost:8000")
LOCAL_PORT = int(os.getenv("LOCAL_PORT", 8001))

class ToolHandler:
    """Handle Claude Code tool calls by executing them locally"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def execute_bash(self, command: str) -> dict:
        """Execute bash command safely"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr, 
                "exit_code": result.returncode,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def write_file(self, path: str, content: str) -> dict:
        """Write content to file"""
        try:
            with open(path, 'w') as f:
                f.write(content)
            return {"success": True, "message": f"File written to {path}"}
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def read_file(self, path: str) -> dict:
        """Read file content"""
        try:
            with open(path, 'r') as f:
                content = f.read()
            return {"success": True, "content": content}
        except Exception as e:
            return {"error": str(e), "success": False}

tool_handler = ToolHandler()

def extract_and_execute_tools(content: str) -> str:
    """Look for tool usage patterns in the response and execute them"""
    if "```bash" in content or "```sh" in content:
        # Extract bash commands
        import re
        bash_pattern = r'```(?:bash|sh)\n(.*?)\n```'
        matches = re.findall(bash_pattern, content, re.DOTALL)
        
        executed_content = content
        for command in matches:
            if command.strip():
                print(f"🔧 Executing: {command.strip()}")
                result = tool_handler.execute_bash(command.strip())
                if result.get("success"):
                    # Replace the bash block with executed output
                    executed_content = executed_content.replace(
                        f"```bash\n{command}\n```",
                        f"```bash\n{command}\n```\n\nOutput:\n```\n{result['stdout']}\n```"
                    )
    
    return executed_content

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        response = requests.get(f"{VAST_API_URL}/health", timeout=5)
        return {
            "status": "healthy",
            "claude_code_proxy": "active",
            "vast_backend": "connected" if response.status_code == 200 else "disconnected",
            "tools": "enabled",
            "timestamp": datetime.now().isoformat()
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
                "created": int(datetime.now().timestamp()),
                "owned_by": "anthropic",
                "type": "text"
            },
            {
                "id": "claude-3-5-sonnet-20241022",
                "object": "model",
                "created": int(datetime.now().timestamp()), 
                "owned_by": "anthropic",
                "type": "text"
            }
        ]
    }

@app.post("/v1/messages")
async def create_message(request: Request):
    """Handle Claude Code CLI messages with tool support"""
    try:
        body = await request.json()
        
        # Forward to vast.ai backend first
        response = requests.post(
            f"{VAST_API_URL}/v1/messages",
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Check if response contains tool usage and execute it
            if "content" in result and result["content"]:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    text_content = content[0].get("text", "")
                    # Execute any tools found in the response
                    enhanced_content = extract_and_execute_tools(text_content)
                    result["content"][0]["text"] = enhanced_content
            
            return result
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print(f"🚀 Starting Claude Code Proxy with Tool Support")
    print(f"📡 Backend: {VAST_API_URL}")
    print(f"🔧 Tools: Bash execution, file operations")
    print(f"📍 Port: {LOCAL_PORT}")
    uvicorn.run(app, host="127.0.0.1", port=LOCAL_PORT)