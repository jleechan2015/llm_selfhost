#!/bin/bash
# Test Claude CLI headless mode with vast.ai LiteLLM proxy

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🤖 Testing Claude CLI Headless Mode with Vast.ai${NC}"
echo "=================================================="

# Check SSH tunnel
if ! curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${RED}❌ SSH tunnel to vast.ai not active${NC}"
    echo -e "${YELLOW}Start tunnel: ssh -N -L 8000:localhost:8000 -p 12806 root@ssh7.vast.ai${NC}"
    exit 1
fi

echo -e "${GREEN}✅ SSH tunnel active${NC}"

# Set environment for Claude CLI
export ANTHROPIC_BASE_URL="http://localhost:8000"
echo -e "${BLUE}🔧 ANTHROPIC_BASE_URL set to: ${ANTHROPIC_BASE_URL}${NC}"

# Test 1: Simple code generation
echo -e "${BLUE}🧪 Test 1: Simple function generation${NC}"
echo "Prompt: Write def factorial(n): with implementation"
echo ""

CLAUDE_OUTPUT=$(timeout 120 claude --verbose -p "Write def factorial(n): with complete implementation in Python. Show only the code, no explanations." 2>&1)
EXIT_CODE=$?

echo "=== Claude Output ==="
echo "$CLAUDE_OUTPUT"
echo "===================="
echo ""

# Check if we got real code
if [ $EXIT_CODE -eq 0 ] && echo "$CLAUDE_OUTPUT" | grep -qi "def factorial"; then
    echo -e "${GREEN}✅ Test 1 PASSED: Claude generated factorial function${NC}"
    TEST1_PASS=true
else
    echo -e "${RED}❌ Test 1 FAILED: No factorial function generated (exit code: $EXIT_CODE)${NC}"
    TEST1_PASS=false
fi

echo ""

# Test 2: More complex generation  
echo -e "${BLUE}🧪 Test 2: Fibonacci sequence generation${NC}"
echo "Prompt: Write fibonacci function for 30 elements"
echo ""

CLAUDE_OUTPUT2=$(timeout 120 claude --verbose -p "Write a Python function to generate the first 30 Fibonacci numbers. Return a list. Show only the code." 2>&1)
EXIT_CODE2=$?

echo "=== Claude Output 2 ==="
echo "$CLAUDE_OUTPUT2"
echo "======================="
echo ""

# Check if we got fibonacci code
if [ $EXIT_CODE2 -eq 0 ] && echo "$CLAUDE_OUTPUT2" | grep -qi "fibonacci"; then
    echo -e "${GREEN}✅ Test 2 PASSED: Claude generated fibonacci function${NC}"
    TEST2_PASS=true
else
    echo -e "${RED}❌ Test 2 FAILED: No fibonacci function generated (exit code: $EXIT_CODE2)${NC}"
    TEST2_PASS=false
fi

echo ""

# Summary
echo -e "${BLUE}📊 Test Summary${NC}"
echo "==============="
if [ "$TEST1_PASS" = true ] && [ "$TEST2_PASS" = true ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}✅ Claude CLI headless mode working with vast.ai LiteLLM proxy${NC}"
    echo -e "${GREEN}✅ Full pipeline: Claude CLI -> Local -> SSH Tunnel -> Vast.ai -> LiteLLM -> Ollama${NC}"
    exit 0
elif [ "$TEST1_PASS" = true ] || [ "$TEST2_PASS" = true ]; then
    echo -e "${YELLOW}⚠️  PARTIAL SUCCESS: Some tests passed${NC}"
    exit 0
else
    echo -e "${RED}❌ ALL TESTS FAILED${NC}"
    exit 1
fi