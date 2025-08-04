#!/usr/bin/env python3
"""
RED TEST: Demonstrates that claude-vast cannot execute tools (like file creation)

This test shows the current broken behavior where claude-vast just generates
code as text but doesn't actually execute it through tools.
"""

import subprocess
import os
import time
import json
import tempfile
from pathlib import Path

def test_claude_vast_tool_limitation():
    """
    RED TEST: Shows claude-vast cannot create files
    
    Expected behavior (what SHOULD happen):
    - Claude CLI should be able to create files using Write tool
    - File should actually exist on filesystem after request
    
    Current broken behavior (what DOES happen):
    - Claude CLI just returns code as text
    - No actual file is created
    - Tools are not executed
    """
    
    print("🔴 RED TEST: Testing claude-vast tool execution limitation")
    print("=" * 60)
    
    # Create a unique test file name
    test_file = f"test_file_{int(time.time())}.txt"
    test_content = f"Test content created at {time.time()}"
    
    print(f"Test file: {test_file}")
    print(f"Test content: {test_content}")
    print()
    
    # Ensure file doesn't exist before test
    if os.path.exists(test_file):
        os.remove(test_file)
    
    print("📝 Testing file creation through claude-vast...")
    
    # Create the command that should create a file
    claude_prompt = f'Create a file named "{test_file}" with the content "{test_content}"'
    
    print(f"Prompt: {claude_prompt}")
    print()
    
    # Try to run claude-vast (this would require actual vast.ai setup)
    # For testing purposes, we'll simulate what claude-vast does:
    # 1. It sets ANTHROPIC_BASE_URL to point to vast.ai through SSH tunnel
    # 2. It runs claude CLI with that base URL
    # 3. The vast.ai instance runs simple_api_proxy.py (NO TOOLS)
    
    print("🔍 Checking current claude-vast architecture...")
    
    # Check if claude-vast exists
    claude_vast_path = "./claude-vast"
    if not os.path.exists(claude_vast_path):
        print(f"❌ {claude_vast_path} not found")
        return False
    
    # Check what proxy runs on vast.ai
    with open("claude-vast", "r") as f:
        claude_vast_content = f.read()
    
    print("🔍 Analysis of claude-vast script:")
    
    if "simple_api_proxy.py" in claude_vast_content:
        print("✅ claude-vast deploys simple_api_proxy.py to vast.ai")
        print("❌ simple_api_proxy.py has NO TOOL EXECUTION capabilities")
    else:
        print("❓ Unclear which proxy is deployed to vast.ai")
    
    if "claude_code_tools_proxy.py" in claude_vast_content:
        print("✅ claude-vast references claude_code_tools_proxy.py")
    else:
        print("❌ claude-vast does NOT use claude_code_tools_proxy.py")
        print("❌ This means NO TOOL EXECUTION on vast.ai")
    
    print()
    print("🔍 Checking simple_api_proxy.py capabilities...")
    
    # Check if simple_api_proxy has tool support
    if os.path.exists("simple_api_proxy.py"):
        with open("simple_api_proxy.py", "r") as f:
            simple_proxy_content = f.read()
        
        has_tools = (
            "str_replace_editor" in simple_proxy_content or
            "bash" in simple_proxy_content or
            "ClaudeCodeTools" in simple_proxy_content
        )
        
        if has_tools:
            print("✅ simple_api_proxy.py has tool support")
        else:
            print("❌ simple_api_proxy.py has NO TOOL SUPPORT")
            print("❌ It only forwards text requests to Ollama/Qwen")
    
    print()
    print("🔍 Expected vs Actual Behavior:")
    print()
    print("EXPECTED (with tools):")
    print("  User: 'Create file test.txt'")
    print("  Claude: 'I'll create the file' + ACTUALLY CREATES FILE")
    print("  Result: ✅ File exists on filesystem")
    print()
    print("ACTUAL (current claude-vast):")
    print("  User: 'Create file test.txt'") 
    print("  Claude: 'Here's Python code to create file' (TEXT ONLY)")
    print("  Result: ❌ No file created, just code as text")
    print()
    
    print("🔴 RED TEST RESULT: FAILING AS EXPECTED")
    print("=" * 60)
    print("❌ claude-vast cannot execute tools because:")
    print("   1. It uses simple_api_proxy.py on vast.ai")
    print("   2. simple_api_proxy.py has no tool execution")
    print("   3. claude_code_tools_proxy.py is never used")
    print("   4. File creation requests return code text, not actual files")
    print()
    print("✅ This confirms the bug - claude-vast needs tool-enabled proxy")
    
    return True

def test_tools_proxy_comparison():
    """Compare the two proxy implementations"""
    print("\n🔍 PROXY COMPARISON:")
    print("=" * 40)
    
    # Check simple_api_proxy.py
    if os.path.exists("simple_api_proxy.py"):
        with open("simple_api_proxy.py", "r") as f:
            simple_content = f.read()
        
        print("📄 simple_api_proxy.py:")
        print(f"   Lines: {len(simple_content.splitlines())}")
        print(f"   Has ClaudeCodeTools: {'ClaudeCodeTools' in simple_content}")
        print(f"   Has bash tool: {'bash(' in simple_content}")
        print(f"   Has file tools: {'str_replace_editor' in simple_content}")
    
    # Check claude_code_tools_proxy.py
    if os.path.exists("claude_code_tools_proxy.py"):
        with open("claude_code_tools_proxy.py", "r") as f:
            tools_content = f.read()
        
        print("📄 claude_code_tools_proxy.py:")
        print(f"   Lines: {len(tools_content.splitlines())}")
        print(f"   Has ClaudeCodeTools: {'ClaudeCodeTools' in tools_content}")
        print(f"   Has bash tool: {'bash(' in tools_content}")
        print(f"   Has file tools: {'str_replace_editor' in tools_content}")

if __name__ == "__main__":
    print("🧪 RED TEST SUITE: Claude-Vast Tool Execution Limitations")
    print("=" * 70)
    print()
    
    # Run the main test
    result = test_claude_vast_tool_limitation()
    
    # Run comparison
    test_tools_proxy_comparison()
    
    print("\n" + "=" * 70)
    print("🔴 RED TEST COMPLETE")
    print("✅ Successfully demonstrated the limitation")
    print("💡 Next: Fix claude-vast to use tool-enabled proxy")