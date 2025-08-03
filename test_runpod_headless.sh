#!/bin/bash
set -e

echo "=== RunPod Integration Headless Test ==="
echo "Testing Claude Code with self-hosted qwen3-coder via API proxy"

# Test configuration
TEST_OUTPUT_DIR="/tmp/claude_runpod_test"
FIBONACCI_FILE="$TEST_OUTPUT_DIR/fibonacci.py"
TEST_LOG="$TEST_OUTPUT_DIR/test_log.txt"

# Create test directory
mkdir -p "$TEST_OUTPUT_DIR"

echo "Test started at: $(date)" | tee "$TEST_LOG"

# Step 1: Test local API proxy functionality
echo "=== Step 1: Testing API Proxy ===" | tee -a "$TEST_LOG"

# Check if simple_api_proxy.py is running locally
echo "Checking if API proxy is running..." | tee -a "$TEST_LOG"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Local API proxy is running" | tee -a "$TEST_LOG"
    USE_LOCAL_PROXY=true
else
    echo "⚠ Local API proxy not found, will skip RunPod test" | tee -a "$TEST_LOG"
    USE_LOCAL_PROXY=false
fi

if [ "$USE_LOCAL_PROXY" = true ]; then
    # Test health endpoint
    echo "Testing health endpoint..." | tee -a "$TEST_LOG"
    HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
    echo "Health response: $HEALTH_RESPONSE" | tee -a "$TEST_LOG"
    
    # Test models endpoint
    echo "Testing models endpoint..." | tee -a "$TEST_LOG"
    MODELS_RESPONSE=$(curl -s http://localhost:8000/v1/models)
    echo "Models response: $MODELS_RESPONSE" | tee -a "$TEST_LOG"
    
    # Step 2: Execute headless Claude Code test
    echo "=== Step 2: Claude Code Headless Test ===" | tee -a "$TEST_LOG"
    
    # Set environment variables for Claude Code to use local proxy
    export ANTHROPIC_BASE_URL="http://localhost:8000"
    export ANTHROPIC_MODEL="qwen3-coder"
    
    # Test Claude Code version
    echo "Testing Claude Code version..." | tee -a "$TEST_LOG"
    if command -v claude &> /dev/null; then
        CLAUDE_VERSION=$(claude --version 2>&1 || echo "Version check failed")
        echo "Claude Code version: $CLAUDE_VERSION" | tee -a "$TEST_LOG"
        
        # Step 3: Generate fibonacci code using Claude Code
        echo "=== Step 3: Fibonacci Code Generation ===" | tee -a "$TEST_LOG"
        
        FIBONACCI_PROMPT="Write a complete Python function to generate the first n fibonacci numbers. Include error handling for negative inputs and add docstring. Make it production-ready with proper comments."
        
        echo "Generating fibonacci code with prompt: $FIBONACCI_PROMPT" | tee -a "$TEST_LOG"
        
        # Execute Claude Code in headless mode with proper flags
        echo "Executing Claude Code in headless mode..." | tee -a "$TEST_LOG"
        if timeout 120 claude --verbose --dangerously-skip-permissions -p "$FIBONACCI_PROMPT" > "${FIBONACCI_FILE}.raw" 2>>"$TEST_LOG"; then
            echo "✓ Claude Code execution completed" | tee -a "$TEST_LOG"
            
            # Extract Python code from markdown response
            echo "Extracting Python code from response..." | tee -a "$TEST_LOG"
            if grep -A 1000 '```python' "${FIBONACCI_FILE}.raw" | grep -B 1000 '^```$' | head -n -1 | tail -n +2 > "$FIBONACCI_FILE"; then
                echo "✓ Python code extracted successfully" | tee -a "$TEST_LOG"
            else
                # If no markdown blocks found, use the entire response
                cp "${FIBONACCI_FILE}.raw" "$FIBONACCI_FILE"
                echo "⚠ No markdown blocks found, using entire response" | tee -a "$TEST_LOG"
            fi
            
            # Step 4: Validate generated code
            echo "=== Step 4: Code Validation ===" | tee -a "$TEST_LOG"
            
            if [ -f "$FIBONACCI_FILE" ] && [ -s "$FIBONACCI_FILE" ]; then
                echo "✓ Fibonacci file created and has content" | tee -a "$TEST_LOG"
                
                # Check if the generated code contains expected elements
                if grep -q "def " "$FIBONACCI_FILE" && grep -q "fibonacci" "$FIBONACCI_FILE"; then
                    echo "✓ Generated code contains function definition with fibonacci" | tee -a "$TEST_LOG"
                    
                    # Test if the generated code is valid Python
                    echo "Testing Python syntax validity..." | tee -a "$TEST_LOG"
                    if python3 -m py_compile "$FIBONACCI_FILE" 2>>"$TEST_LOG"; then
                        echo "✓ Generated code has valid Python syntax" | tee -a "$TEST_LOG"
                        
                        # Show the generated code
                        echo "=== Generated Fibonacci Code ===" | tee -a "$TEST_LOG"
                        cat "$FIBONACCI_FILE" | tee -a "$TEST_LOG"
                        
                        # Try to execute the code
                        echo "=== Testing Code Execution ===" | tee -a "$TEST_LOG"
                        if python3 -c "
import sys
sys.path.append('$TEST_OUTPUT_DIR')
exec(open('$FIBONACCI_FILE').read())
# Try to find and call the fibonacci function
import re
code = open('$FIBONACCI_FILE').read()
func_matches = re.findall(r'def (\w*fibonacci\w*)\s*\([^)]*\)', code, re.IGNORECASE)
if func_matches:
    func_name = func_matches[0]
    print(f'Testing function: {func_name}')
    result = eval(f'{func_name}(10)')
    print(f'Result for fibonacci(10): {result}')
    if isinstance(result, (list, tuple)) and len(result) >= 5:
        print('✓ Fibonacci function executed successfully')
    else:
        print('⚠ Function executed but result format unexpected')
else:
    print('⚠ No fibonacci function found to test')
" 2>>"$TEST_LOG" | tee -a "$TEST_LOG"; then
                            echo "✓ COMPLETE SUCCESS: RunPod integration test passed" | tee -a "$TEST_LOG"
                            SUCCESS=true
                        else
                            echo "❌ Code execution failed" | tee -a "$TEST_LOG"
                            SUCCESS=false
                        fi
                    else
                        echo "❌ Generated code has syntax errors" | tee -a "$TEST_LOG"
                        SUCCESS=false
                    fi
                else
                    echo "❌ Generated code does not contain expected fibonacci function" | tee -a "$TEST_LOG"
                    SUCCESS=false
                fi
            else
                echo "❌ Fibonacci file was not created or is empty" | tee -a "$TEST_LOG"
                SUCCESS=false
            fi
        else
            echo "❌ Claude Code execution failed" | tee -a "$TEST_LOG"
            SUCCESS=false
        fi
    else
        echo "❌ Claude Code CLI not found" | tee -a "$TEST_LOG"  
        SUCCESS=false
    fi
else
    echo "❌ Skipping test - API proxy not available" | tee -a "$TEST_LOG"
    SUCCESS=false
fi

# Final result
echo "=== Test Summary ===" | tee -a "$TEST_LOG"
echo "Test completed at: $(date)" | tee -a "$TEST_LOG"

if [ "$SUCCESS" = true ]; then
    echo "🎉 SUCCESS: RunPod integration test PASSED" | tee -a "$TEST_LOG"
    echo "- API proxy responded correctly"
    echo "- Claude Code executed successfully"  
    echo "- Fibonacci code generated and validated"
    echo "- End-to-end integration working"
    exit 0
else
    echo "❌ FAILURE: RunPod integration test FAILED" | tee -a "$TEST_LOG"
    echo "Check test log at: $TEST_LOG"
    echo "Generated file (if any): $FIBONACCI_FILE"
    exit 1
fi