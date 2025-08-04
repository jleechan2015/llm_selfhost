#!/usr/bin/env python3
"""
Base class for Claude Code tool execution
Provides common tool implementations that all proxies can inherit from
"""

import os
import json
import subprocess
import tempfile
import uuid
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class ClaudeCodeTools:
    """Base class implementing Claude Code's core tools"""
    
    def __init__(self):
        self.temp_files = {}
        self.session_id = str(uuid.uuid4())
        
    def bash(self, command: str) -> Dict[str, Any]:
        """Execute bash commands with security checks"""
        
        # Enhanced security checks with regex patterns
        dangerous_patterns = [
            r'rm\s+-rf\s+/', r'rm\s+-rf\s+\*', r'\bformat\b', r'\bfdisk\b', r'\bmkfs\b',
            r'dd\s+if=', r':\(\)\s*\{\s*:\|:&\s*\};:', r'chmod\s+-R\s+777\s+/',
            r'chown\s+-R', r'\bpasswd\b', r'sudo\s+su', r'\bsu\s+-',
            r'curl.*169\.254\.169\.254',  # Block metadata access
            r'>\s*/dev/sd[a-z]',  # Block direct disk writes
            r'mkfs\.',  # Block any mkfs variant
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return {
                    "type": "bash",
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": f"Security: Command blocked by security policy"
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
    
    def _validate_file_path(self, path: str) -> bool:
        """Validate file path to prevent directory traversal"""
        if not path:
            return False
        
        # Resolve to absolute path
        try:
            abs_path = os.path.abspath(path)
            # Ensure path is within current directory or allowed directories
            cwd = os.getcwd()
            if not abs_path.startswith(cwd):
                return False
            
            # Block access to sensitive files
            blocked_patterns = ['.ssh', '.git', '.env', 'id_rsa', 'id_dsa']
            for pattern in blocked_patterns:
                if pattern in abs_path:
                    return False
            
            return True
        except:
            return False

    def str_replace_editor(self, command: str, path: str = None, file_text: str = None, 
                          new_str: str = None, old_str: str = None, insert_line: int = None,
                          view_range: List[int] = None) -> Dict[str, Any]:
        """File editing tool like Claude Code's str_replace_editor"""
        
        if path and not self._validate_file_path(path):
            return {
                "type": "str_replace_editor",
                "error": "Invalid file path: access denied"
            }

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

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Direct file write tool for Claude Code CLI compatibility"""
        if not self._validate_file_path(path):
            return {
                "type": "write_file",
                "error": "Invalid file path: access denied"
            }
        try:
            with open(path, 'w') as f:
                f.write(content)
            return {
                "type": "write_file",
                "result": f"File written successfully at: {path}"
            }
        except Exception as e:
            return {
                "type": "write_file",
                "error": f"Failed to write file: {str(e)}"
            }


class ToolExecutionMixin:
    """Mixin class providing tool execution logic for proxies"""
    
    def __init__(self):
        self.tools = ClaudeCodeTools()
    
    def should_use_tools(self, content: str) -> bool:
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

    def extract_tool_requests(self, content: str) -> List[Dict]:
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

    def execute_tools(self, tool_requests: List[Dict]) -> str:
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
                    result = self.tools.bash(command)
                    results.append(f"\n**Bash Execution:**\n```\nCommand: {command}\nExit code: {result['exit_code']}\nOutput: {result['stdout']}\nError: {result['stderr']}\n```")
                
                elif request["type"] == "str_replace_editor":
                    result = self.tools.str_replace_editor(**{k: v for k, v in request.items() if k != "type"})
                    if "error" in result:
                        results.append(f"\n**File Operation Error:** {result['error']}")
                    else:
                        results.append(f"\n**File Operation:** {result['result']}")
                
            except Exception as e:
                print(f"❌ [{timestamp}] Tool execution error: {str(e)}")
                results.append(f"\n**Tool Error:** {str(e)}")
        
        print(f"🏁 [{timestamp}] TOOL EXECUTION COMPLETED - {len(tool_requests)} tools processed")
        return "\n".join(results)

    def add_tool_instructions_to_messages(self, messages: List[Dict]) -> List[Dict]:
        """Add tool calling instructions to messages"""
        enhanced_messages = []
        has_system = any(msg.get('role') == 'system' for msg in messages)
        
        if not has_system:
            tool_system_msg = {
                "role": "system",
                "content": """You are a helpful coding assistant with access to system tools.

When you need to execute commands or work with files, be explicit about your actions:
- For bash commands: Write ```bash\\ncommand\\n``` blocks
- For file creation: Say "I'll create a file named 'filename'" and include the content
- Always show the actual commands you want to execute in code blocks
- Be specific about file paths and command syntax

You have access to bash execution and file operations."""
            }
            enhanced_messages.append(tool_system_msg)
        
        enhanced_messages.extend(messages)
        return enhanced_messages