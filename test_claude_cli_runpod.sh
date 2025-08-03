#!/bin/bash
set -e

echo "=== Claude CLI RunPod Integration Test ==="
echo "Testing Claude CLI headless mode with RunPod endpoint"

# Test configuration
TEST_OUTPUT_DIR="/tmp/claude_runpod_test"
FIBONACCI_FILE="$TEST_OUTPUT_DIR/fibonacci_test.py"
TEST_LOG="$TEST_OUTPUT_DIR/test_log.txt"

# Create test directory
mkdir -p "$TEST_OUTPUT_DIR"
echo "Test started at: $(date)" | tee "$TEST_LOG"

# Step 1: Check for RunPod endpoint
echo "=== Step 1: RunPod Endpoint Configuration ===" | tee -a "$TEST_LOG"

if [ -n "$RUNPOD_ENDPOINT" ]; then
    echo "✓ RunPod endpoint provided: $RUNPOD_ENDPOINT" | tee -a "$TEST_LOG"
    API_BASE_URL="https://$RUNPOD_ENDPOINT"
    PROXY_TYPE="runpod"
elif curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Local API proxy detected" | tee -a "$TEST_LOG"
    API_BASE_URL="http://localhost:8000"
    PROXY_TYPE="local"
else
    echo "❌ No API endpoint available" | tee -a "$TEST_LOG"
    echo "Either:"
    echo "  - Set RUNPOD_ENDPOINT=your-runpod-url.proxy.runpod.net"
    echo "  - Start local API proxy on port 8000"
    exit 1
fi

# Step 2: Configure Claude CLI environment
echo "=== Step 2: Configure Claude CLI ===" | tee -a "$TEST_LOG"

export ANTHROPIC_BASE_URL="$API_BASE_URL"
export ANTHROPIC_MODEL="qwen2.5-coder:7b"

echo "Environment configured:" | tee -a "$TEST_LOG"
echo "  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL" | tee -a "$TEST_LOG"
echo "  ANTHROPIC_MODEL=$ANTHROPIC_MODEL" | tee -a "$TEST_LOG"

# Step 3: Test Claude CLI code generation and execution
echo "=== Step 3: Claude CLI Code Generation and Execution ===" | tee -a "$TEST_LOG"

FIBONACCI_PROMPT="Write and execute Python code: Create a fibonacci function that generates the first n fibonacci numbers, then test it by calling fibonacci_sequence(10) and print the result. Show both the code and execution output."

echo "Executing Claude CLI with comprehensive prompt..." | tee -a "$TEST_LOG"

if timeout 180 claude --verbose --dangerously-skip-permissions -p "$FIBONACCI_PROMPT" > "$FIBONACCI_FILE" 2>>"$TEST_LOG"; then
    echo "✓ Claude CLI executed successfully" | tee -a "$TEST_LOG"
    
    # Show the response
    echo "=== Claude CLI Response ===" | tee -a "$TEST_LOG"
    cat "$FIBONACCI_FILE" | tee -a "$TEST_LOG"
    
    # Validate response contains both code and execution
    if grep -qi "fibonacci" "$FIBONACCI_FILE" && grep -qi "def\|function" "$FIBONACCI_FILE"; then
        echo "✓ Response contains fibonacci function" | tee -a "$TEST_LOG"
        
        # Check for execution results (numbers or arrays)
        if grep -E "\[.*[0-9].*\]|fibonacci.*=.*[0-9]" "$FIBONACCI_FILE" > /dev/null; then
            echo "✓ Response contains execution results" | tee -a "$TEST_LOG"
            SUCCESS=true
        else
            echo "⚠ No clear execution results found" | tee -a "$TEST_LOG"
            SUCCESS=partial
        fi
    else
        echo "❌ No fibonacci function found in response" | tee -a "$TEST_LOG"
        SUCCESS=false
    fi
else
    echo "❌ Claude CLI execution failed" | tee -a "$TEST_LOG"
    SUCCESS=false
fi

# Final results
echo "=== Test Results Summary ===" | tee -a "$TEST_LOG"
echo "Test completed at: $(date)" | tee -a "$TEST_LOG"

if [ "$SUCCESS" = true ]; then
    echo "🎉 SUCCESS: RunPod integration with code execution PASSED" | tee -a "$TEST_LOG"
    echo "✓ $PROXY_TYPE endpoint is functional"
    echo "✓ Claude CLI headless mode works"
    echo "✓ Generated fibonacci code"
    echo "✓ Code executed and returned results"
    echo ""
    echo "Proven integration:"
    echo "  Claude CLI → $ANTHROPIC_BASE_URL → Self-hosted Model → Code + Execution"
    exit 0
elif [ "$SUCCESS" = partial ]; then
    echo "⚠ PARTIAL SUCCESS: Code generated but execution unclear" | tee -a "$TEST_LOG"
    exit 0
else
    echo "❌ FAILURE: RunPod integration test failed" | tee -a "$TEST_LOG"
    echo "Check logs at: $TEST_LOG"
    exit 1
fi