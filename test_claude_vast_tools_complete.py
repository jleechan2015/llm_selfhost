#!/usr/bin/env python3
"""
Complete Tool Execution Test Suite for claude-vast
Tests actual tool execution through logged proxy interactions
"""

import os
import sys
import time
import subprocess
import tempfile
import json
from pathlib import Path
from datetime import datetime

def log_test(message):
    """Log test messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🧪 [{timestamp}] {message}")

def run_claude_vast_test(prompt, test_name, timeout=60):
    """Run a claude-vast command and capture all output"""
    log_test(f"Starting test: {test_name}")
    
    # Create temp log file for this test
    log_file = f"/tmp/claude_vast_test_{test_name.replace(' ', '_')}.log"
    
    try:
        # Run claude-vast with output redirection
        cmd = f"./claude-vast -p '{prompt}' > {log_file} 2>&1"
        log_test(f"Executing: {cmd}")
        
        result = subprocess.run(
            cmd, 
            shell=True, 
            timeout=timeout,
            cwd="/home/jleechan/projects/claude_llm_proxy"
        )
        
        # Read the output
        with open(log_file, 'r') as f:
            output = f.read()
        
        log_test(f"Test {test_name} completed with exit code: {result.returncode}")
        return {
            'exit_code': result.returncode,
            'output': output,
            'log_file': log_file
        }
        
    except subprocess.TimeoutExpired:
        log_test(f"Test {test_name} timed out after {timeout} seconds")
        return {
            'exit_code': -1,
            'output': 'TIMEOUT',
            'log_file': log_file
        }
    except Exception as e:
        log_test(f"Test {test_name} failed with error: {str(e)}")
        return {
            'exit_code': -2,
            'output': f'ERROR: {str(e)}',
            'log_file': log_file
        }

def verify_file_creation(filename, expected_content=None):
    """Verify a file was actually created"""
    filepath = f"/home/jleechan/projects/claude_llm_proxy/{filename}"
    
    if os.path.exists(filepath):
        log_test(f"✅ File {filename} was created")
        if expected_content:
            with open(filepath, 'r') as f:
                actual_content = f.read().strip()
            if expected_content in actual_content:
                log_test(f"✅ File {filename} contains expected content")
                return True
            else:
                log_test(f"❌ File {filename} content mismatch. Expected: '{expected_content}', Got: '{actual_content}'")
                return False
        return True
    else:
        log_test(f"❌ File {filename} was NOT created")
        return False

def analyze_logs_for_tool_execution(log_file):
    """Analyze logs to verify tool execution occurred"""
    if not os.path.exists(log_file):
        log_test(f"❌ Log file {log_file} not found")
        return False
    
    with open(log_file, 'r') as f:
        content = f.read()
    
    # Look for tool execution indicators
    tool_indicators = [
        "TOOL EXECUTION STARTED",
        "Executing bash:",
        "File operation:",
        "TOOL EXECUTION COMPLETED"
    ]
    
    found_indicators = []
    for indicator in tool_indicators:
        if indicator in content:
            found_indicators.append(indicator)
            log_test(f"✅ Found tool execution indicator: {indicator}")
        else:
            log_test(f"❌ Missing tool execution indicator: {indicator}")
    
    if len(found_indicators) >= 2:  # At least START and some execution
        log_test("✅ Tool execution confirmed through logs")
        return True
    else:
        log_test("❌ No clear evidence of tool execution in logs")
        return False

def main():
    """Run comprehensive claude-vast tool execution tests"""
    log_test("=== Claude-Vast Tool Execution Test Suite ===")
    
    # Clean up from previous tests
    test_files = [
        "test_vast_file_create.txt",
        "test_vast_file_edit.txt", 
        "test_vast_bash_output.txt"
    ]
    
    for file in test_files:
        filepath = f"/home/jleechan/projects/claude_llm_proxy/{file}"
        if os.path.exists(filepath):
            os.remove(filepath)
            log_test(f"🧹 Cleaned up existing file: {file}")
    
    # Test cases
    tests = [
        {
            'name': 'file_creation',
            'prompt': 'Create a file called test_vast_file_create.txt with the content "Hello from claude-vast tools"',
            'verify_file': 'test_vast_file_create.txt',
            'expected_content': 'Hello from claude-vast tools'
        },
        {
            'name': 'bash_execution',
            'prompt': 'Run the command "echo \'Bash execution test\' > test_vast_bash_output.txt"',
            'verify_file': 'test_vast_bash_output.txt',
            'expected_content': 'Bash execution test'
        },
        {
            'name': 'file_editing',
            'prompt': 'Create a file test_vast_file_edit.txt with "original content", then edit it to say "edited content"',
            'verify_file': 'test_vast_file_edit.txt',
            'expected_content': 'edited content'
        }
    ]
    
    results = []
    
    for test in tests:
        log_test(f"\n--- Running Test: {test['name']} ---")
        
        # Run the test
        result = run_claude_vast_test(test['prompt'], test['name'])
        
        # Verify file creation
        file_created = verify_file_creation(test['verify_file'], test.get('expected_content'))
        
        # Analyze logs for tool execution
        tools_executed = analyze_logs_for_tool_execution(result['log_file'])
        
        # Store results
        test_result = {
            'name': test['name'],
            'exit_code': result['exit_code'],
            'file_created': file_created,
            'tools_executed': tools_executed,
            'log_file': result['log_file'],
            'success': file_created and tools_executed and result['exit_code'] == 0
        }
        
        results.append(test_result)
        
        if test_result['success']:
            log_test(f"✅ Test {test['name']} PASSED")
        else:
            log_test(f"❌ Test {test['name']} FAILED")
    
    # Final report
    log_test("\n=== FINAL RESULTS ===")
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    log_test(f"Tests passed: {passed}/{total}")
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        log_test(f"{status} {result['name']}: exit_code={result['exit_code']}, file_created={result['file_created']}, tools_executed={result['tools_executed']}")
    
    # Save detailed results
    results_file = "/tmp/claude_vast_test_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    log_test(f"Detailed results saved to: {results_file}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)