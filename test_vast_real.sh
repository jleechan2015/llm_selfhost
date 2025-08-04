#!/bin/bash
# Real vast.ai integration test with actual SSH tunnel

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Real Vast.ai Integration Test${NC}"
echo "=================================="

# Check if SSH tunnel is active
if ! curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${RED}❌ SSH tunnel to vast.ai not active${NC}"
    echo -e "${YELLOW}Start tunnel: ssh -N -L 8000:localhost:8000 -p 12806 root@ssh7.vast.ai${NC}"
    exit 1
fi

echo -e "${GREEN}✅ SSH tunnel active${NC}"

# Kill any existing process on port 8001
echo -e "${YELLOW}🔧 Ensuring port 8001 is free...${NC}"
fuser -k 8001/tcp >/dev/null 2>&1

# Create vast.ai configuration
echo -e "${BLUE}🔧 Creating vast.ai configuration...${NC}"
cat > .llmrc.json << EOF
{
  "backend": "vast-ai",
  "port": 8001,
  "backends": {
    "vast-ai": {
      "type": "self-hosted",
      "url": "http://localhost:8000",
      "model": "qwen3-coder",
      "description": "Vast.ai GPU instance via SSH tunnel"
    }
  }
}
EOF
chmod 600 .llmrc.json

# Start our proxy server
echo -e "${BLUE}🚀 Starting local proxy server...${NC}"
node ./bin/llm-proxy.js start &
LOCAL_PROXY_PID=$!

# Wait for startup 
sleep 5

echo -e "${BLUE}🔍 Testing local proxy health...${NC}"
LOCAL_HEALTH=$(curl -s http://localhost:8001/health 2>/dev/null || echo "FAILED")
echo "Local proxy health: $LOCAL_HEALTH"

if echo "$LOCAL_HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Local proxy healthy${NC}"
else
    echo -e "${RED}❌ Local proxy failed${NC}"
    kill $LOCAL_PROXY_PID 2>/dev/null
    rm -f .llmrc.json
    exit 1
fi

# Test end-to-end with Claude CLI
echo -e "${BLUE}🤖 Testing Claude CLI with real vast.ai backend...${NC}"
export ANTHROPIC_BASE_URL="http://localhost:8001"
export ANTHROPIC_API_KEY="dummy"

echo -e "${BLUE}Sending: Write a Python function to calculate factorial${NC}"
CLAUDE_RESPONSE=$(timeout 60 claude --model qwen3-coder "Write a Python function to calculate factorial of a number. Just show the code." 2>&1)

echo ""
echo "=== Claude Response ==="
echo "$CLAUDE_RESPONSE"
echo "======================="

# Check if we got real code generation
if echo "$CLAUDE_RESPONSE" | grep -qi "def.*factorial" && echo "$CLAUDE_RESPONSE" | grep -qi "return"; then
    echo -e "${GREEN}✅ Real code generation successful!${NC}"
    SUCCESS=true
else
    echo -e "${RED}❌ No code generation detected${NC}"
    SUCCESS=false
fi

# Test direct API call to vast.ai
echo -e "${BLUE}🔍 Testing direct API call...${NC}"
DIRECT_RESPONSE=$(curl -s -X POST http://localhost:8001/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen3-coder", "messages": [{"role": "user", "content": "Write a Python function to calculate factorial of a number. Just show the code."}], "max_tokens": 150}')

echo "Direct API response preview:"
echo "$DIRECT_RESPONSE" | head -c 200

# Cleanup
echo -e "${BLUE}🧹 Cleaning up...${NC}"
kill $LOCAL_PROXY_PID 2>/dev/null
wait $LOCAL_PROXY_PID 2>/dev/null || true
rm -f .llmrc.json

if [ "$SUCCESS" = true ]; then
    echo -e "${GREEN}🎉 Real vast.ai integration test PASSED!${NC}"
    echo -e "${GREEN}✅ Full pipeline: Claude CLI -> Local Proxy -> SSH Tunnel -> Vast.ai GPU -> Ollama${NC}"
    exit 0
else
    echo -e "${RED}❌ Test failed${NC}"
    exit 1
fi
