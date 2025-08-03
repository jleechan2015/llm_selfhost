#!/bin/bash
# Simple direct test of Cerebras integration

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Source environment
source ~/.bashrc

# Explicitly set the API key in case of sourcing issues
export CEREBRAS_API_KEY="csk-r3ccctjjpfx53m5nnr2y3v9rv954vcy5e59mmx4w3cxyfejn"

echo -e "${BLUE}🧪 Simple Cerebras Integration Test${NC}"
echo "===================================="
echo -e "${BLUE}API Key: ${CEREBRAS_API_KEY:0:10}...${NC}"
echo ""

# Create Cerebras config
echo -e "${BLUE}🔧 Creating Cerebras configuration...${NC}"
cat > .llmrc.json << EOF
{
  "backend": "cerebras",
  "port": "auto",
  "backends": {
    "cerebras": {
      "type": "cerebras",
      "apiKey": "$CEREBRAS_API_KEY",
      "description": "Cerebras SaaS API"
    }
  }
}
EOF
chmod 600 .llmrc.json

echo -e "${BLUE}🔍 Debug: Configuration file contents:${NC}"
cat .llmrc.json
echo ""

# Start proxy server
echo -e "${BLUE}🚀 Starting proxy server...${NC}"
node ./bin/llm-proxy.js start &
PROXY_PID=$!

# Wait for startup
sleep 8

# Test health endpoint
echo -e "${BLUE}🔍 Testing health endpoint...${NC}"
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health 2>/dev/null || echo "FAILED")
echo "Health response: $HEALTH_RESPONSE"

if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
    kill $PROXY_PID 2>/dev/null
    rm -f .llmrc.json
    exit 1
fi

# First test API directly
echo -e "${BLUE}🔍 Testing API directly...${NC}"
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}], "max_tokens": 10}' \
  2>&1 | head -10

echo ""
echo ""

# Test Claude CLI with simple prompt
echo -e "${BLUE}🤖 Testing Claude CLI with simple prompt...${NC}"
export ANTHROPIC_BASE_URL="http://localhost:8000"

CLAUDE_RESPONSE=$(timeout 30 claude --verbose -p "Write a simple Python function to add two numbers. Just show the code." 2>&1)
echo ""
echo "=== Claude Response ==="
echo "$CLAUDE_RESPONSE"
echo "======================="

# Check if response contains expected content
if echo "$CLAUDE_RESPONSE" | grep -qi "def"; then
    echo -e "${GREEN}✅ Claude response contains function definition${NC}"
    SUCCESS=true
else
    echo -e "${RED}❌ Claude response missing expected content${NC}"
    SUCCESS=false
fi

# Cleanup
echo -e "${BLUE}🧹 Cleaning up...${NC}"
kill $PROXY_PID 2>/dev/null
wait $PROXY_PID 2>/dev/null || true
rm -f .llmrc.json

if [ "$SUCCESS" = true ]; then
    echo -e "${GREEN}🎉 Test passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Test failed!${NC}"  
    exit 1
fi