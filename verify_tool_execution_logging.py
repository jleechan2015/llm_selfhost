#!/usr/bin/env python3
"""
Tool Execution Verification Script
Verifies that logging has been properly added to all proxy files
and demonstrates the testing approach
"""

import os
import sys
import json
from datetime import datetime

def log_verify(message):
    """Log verification messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"✅ [{timestamp}] {message}")

def check_logging_in_proxy(proxy_file, expected_prefix):
    """Check if a proxy file has proper tool execution logging"""
    log_verify(f"Checking logging in {proxy_file}")
    
    if not os.path.exists(proxy_file):
        print(f"❌ File {proxy_file} not found")
        return False
    
    with open(proxy_file, 'r') as f:
        content = f.read()
    
    # Check for logging indicators
    required_patterns = [
        f"{expected_prefix} TOOL EXECUTION STARTED",
        "Executing bash:",
        "File operation:",
        f"{expected_prefix} TOOL EXECUTION COMPLETED",
        "timestamp = datetime.now().strftime",
        "print(f\"🔧"
    ]
    
    found_patterns = []
    missing_patterns = []
    
    for pattern in required_patterns:
        if pattern in content:
            found_patterns.append(pattern)
            log_verify(f"  ✅ Found: {pattern}")
        else:
            missing_patterns.append(pattern)
            print(f"  ❌ Missing: {pattern}")
    
    success = len(missing_patterns) == 0
    log_verify(f"  {'✅ PASS' if success else '❌ FAIL'}: {len(found_patterns)}/{len(required_patterns)} patterns found")
    
    return success

def check_test_suite(test_file, test_name):
    """Check if a test suite exists and is properly structured"""
    log_verify(f"Checking test suite: {test_file}")
    
    if not os.path.exists(test_file):
        print(f"❌ Test file {test_file} not found")
        return False
    
    with open(test_file, 'r') as f:
        content = f.read()
    
    # Check for test structure
    required_elements = [
        "def run_claude_",
        "def verify_file_creation",
        "def analyze_logs_for_tool_execution",
        "subprocess.run",
        "tool_indicators",
        "TOOL EXECUTION STARTED"
    ]
    
    found_elements = []
    missing_elements = []
    
    for element in required_elements:
        if element in content:
            found_elements.append(element)
            log_verify(f"  ✅ Found: {element}")
        else:
            missing_elements.append(element)
            print(f"  ❌ Missing: {element}")
    
    success = len(missing_elements) == 0
    log_verify(f"  {'✅ PASS' if success else '❌ FAIL'}: {len(found_elements)}/{len(required_elements)} elements found")
    
    return success

def demonstrate_approach():
    """Demonstrate the testing approach"""
    log_verify("=== DEMONSTRATION OF TESTING APPROACH ===")
    
    print("""
🎯 TESTING METHODOLOGY:

1. ENHANCED LOGGING:
   - Added timestamped logging to all *_tools_proxy.py files
   - Each tool execution logs: START, individual tool operations, completion
   - Uses emojis and clear formatting for easy identification

2. COMPREHENSIVE TEST SUITES:
   - Each claude wrapper gets its own test suite
   - Tests run actual commands through the wrapper
   - Captures all output to log files
   - Verifies both file creation AND log evidence

3. VERIFICATION PROCESS:
   - Run: python3 test_claude_[wrapper]_tools_complete.py
   - Each test creates files and checks they exist
   - Parses logs for tool execution evidence
   - Reports detailed pass/fail status

4. LOG ANALYSIS:
   - Searches for specific logging patterns
   - Confirms tools were actually executed, not just displayed
   - Provides concrete proof of functionality

5. NO MORE FAKING:
   - Tests create real files
   - Logs prove real execution
   - Results are verifiable and repeatable
    """)

def main():
    """Main verification function"""
    log_verify("=== TOOL EXECUTION LOGGING VERIFICATION ===")
    
    # Define proxy files and their expected logging prefixes
    proxy_configs = [
        {
            'file': '/home/jleechan/projects/claude_llm_proxy/vast_tools_proxy.py',
            'prefix': '',
            'name': 'vast_tools_proxy'
        },
        {
            'file': '/home/jleechan/projects/claude_llm_proxy/cerebras_tools_proxy.py', 
            'prefix': 'CEREBRAS',
            'name': 'cerebras_tools_proxy'
        },
        {
            'file': '/home/jleechan/projects/claude_llm_proxy/local_tools_proxy.py',
            'prefix': 'LOCAL',
            'name': 'local_tools_proxy'
        }
    ]
    
    # Define test suites
    test_suites = [
        {
            'file': '/home/jleechan/projects/claude_llm_proxy/test_claude_vast_tools_complete.py',
            'name': 'claude-vast test suite'
        },
        {
            'file': '/home/jleechan/projects/claude_llm_proxy/test_claude_cerebras_tools_complete.py',
            'name': 'claude-cerebras test suite'
        },
        {
            'file': '/home/jleechan/projects/claude_llm_proxy/test_claude_local_tools_complete.py',
            'name': 'claude-local test suite'
        }
    ]
    
    # Check logging in proxies
    log_verify("\n--- CHECKING PROXY LOGGING ---")
    proxy_results = []
    for config in proxy_configs:
        result = check_logging_in_proxy(config['file'], config['prefix'])
        proxy_results.append({
            'name': config['name'],
            'success': result
        })
    
    # Check test suites
    log_verify("\n--- CHECKING TEST SUITES ---")
    test_results = []
    for suite in test_suites:
        result = check_test_suite(suite['file'], suite['name'])
        test_results.append({
            'name': suite['name'],
            'success': result
        })
    
    # Final report
    log_verify("\n=== FINAL VERIFICATION REPORT ===")
    
    proxy_passed = sum(1 for r in proxy_results if r['success'])
    test_passed = sum(1 for r in test_results if r['success'])
    
    log_verify(f"Proxy logging: {proxy_passed}/{len(proxy_results)} ✅")
    log_verify(f"Test suites: {test_passed}/{len(test_suites)} ✅")
    
    for result in proxy_results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        log_verify(f"  {status} {result['name']}")
    
    for result in test_results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        log_verify(f"  {status} {result['name']}")
    
    # Show next steps
    log_verify("\n=== NEXT STEPS ===")
    print("""
🚀 TO RUN TESTS:

1. For claude-local (requires LM Studio):
   python3 test_claude_local_tools_complete.py

2. For claude-cerebras (requires CEREBRAS_API_KEY):
   export CEREBRAS_API_KEY="your-key"
   python3 test_claude_cerebras_tools_complete.py

3. For claude-vast (requires vast.ai setup):
   python3 test_claude_vast_tools_complete.py

📊 WHAT EACH TEST DOES:
- Runs actual claude commands
- Creates real files
- Captures all logs
- Verifies tool execution through log analysis
- Reports concrete pass/fail results

🔍 NO MORE FAKING:
- Files must be created on disk
- Logs must show tool execution
- Everything is verifiable and repeatable
    """)
    
    demonstrate_approach()
    
    total_success = proxy_passed == len(proxy_results) and test_passed == len(test_suites)
    return total_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)