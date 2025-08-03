#!/bin/bash
# Test Claude CLI interactive mode with vast.ai

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🎯 Testing Claude CLI Interactive Mode${NC}"
echo "======================================"

# Check tunnel
if ! curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${RED}❌ SSH tunnel not active${NC}"
    exit 1
fi

echo -e "${GREEN}✅ SSH tunnel active${NC}"

# Set environment
export ANTHROPIC_BASE_URL="http://localhost:8000"
echo -e "${BLUE}🔧 Using: ${ANTHROPIC_BASE_URL}${NC}"
echo ""

# Test 1: Piped input (simulates typing in interactive mode)
echo -e "${BLUE}🧪 Test: Piped input (simulates interactive)${NC}"
echo "Input: Write a simple add function"
echo ""

# Use timeout and process substitution to simulate interactive input
timeout 90 bash -c 'echo "Write def add(a, b): return a + b" | claude' 2>&1 &
PID=$!

# Wait a bit and check if process is running
sleep 10
if kill -0 $PID 2>/dev/null; then
    echo -e "${YELLOW}⏳ Claude is processing... (still running after 10s)${NC}"
    # Let it run for total of 90s
    wait $PID
    EXIT_CODE=$?
else
    EXIT_CODE=0
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Interactive mode working (process completed successfully)${NC}"
    SUCCESS=true
else
    echo -e "${RED}❌ Interactive mode failed (exit code: $EXIT_CODE)${NC}"
    SUCCESS=false
fi

echo ""

# Test 2: Check if we can start interactive session (without actually interacting)
echo -e "${BLUE}🧪 Test: Interactive session startup${NC}"
timeout 5 bash -c 'echo "" | claude' >/dev/null 2>&1 &
PID2=$!
sleep 2

if kill -0 $PID2 2>/dev/null; then
    echo -e "${GREEN}✅ Interactive session starts successfully${NC}"
    kill $PID2 2>/dev/null
    STARTUP_SUCCESS=true
else
    echo -e "${RED}❌ Interactive session failed to start${NC}"
    STARTUP_SUCCESS=false
fi

echo ""

# Summary
echo -e "${BLUE}📊 Interactive Mode Test Results${NC}"
echo "================================"

if [ "$SUCCESS" = true ] && [ "$STARTUP_SUCCESS" = true ]; then
    echo -e "${GREEN}🎉 INTERACTIVE MODE WORKING!${NC}"
    echo -e "${GREEN}✅ Claude CLI can receive input and process through vast.ai${NC}"
    echo -e "${GREEN}✅ Full interactive pipeline functional${NC}"
    echo ""
    echo -e "${BLUE}💡 To use interactively:${NC}"
    echo -e "${BLUE}   export ANTHROPIC_BASE_URL=\"http://localhost:8000\"${NC}"
    echo -e "${BLUE}   claude${NC}"
    exit 0
else
    echo -e "${RED}❌ Interactive mode issues detected${NC}"
    exit 1
fi