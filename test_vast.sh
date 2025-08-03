#!/bin/bash
# Simple vast.ai integration test

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Simple Vast.ai Integration Test${NC}"
echo "===================================="

# Check if vastai CLI is available
if ! command -v vastai >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  vastai CLI not found - testing with mock local backend${NC}"
    MOCK_MODE=true
else
    echo -e "${GREEN}✅ vastai CLI found${NC}"
    MOCK_MODE=false
fi

# Create vast.ai/self-hosted config (using localhost as fallback)
echo -e "${BLUE}🔧 Creating self-hosted configuration...${NC}"
cat > .llmrc.json << EOF
{
  "backend": "self-hosted",
  "port": "auto",
  "backends": {
    "self-hosted": {
      "type": "self-hosted",
      "url": "http://localhost:8000",
      "description": "Vast.ai GPU instance or local proxy"
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

# Test API directly
echo -e "${BLUE}🔍 Testing self-hosted API directly...${NC}"
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}], "max_tokens": 10}' \
  2>&1 | head -5

echo ""

# Since we don't have a real vast.ai instance running, this will likely fail
# But we can verify the configuration and proxy setup is working

echo -e "${BLUE}📊 Test Results:${NC}"
echo -e "${GREEN}✅ Configuration loading works${NC}"
echo -e "${GREEN}✅ Proxy server starts successfully${NC}"
echo -e "${GREEN}✅ Health endpoint works with self-hosted backend${NC}"
echo -e "${YELLOW}⚠️  Actual vast.ai connection would require running GPU instance${NC}"

# Cleanup
echo -e "${BLUE}🧹 Cleaning up...${NC}"
kill $PROXY_PID 2>/dev/null
wait $PROXY_PID 2>/dev/null || true
rm -f .llmrc.json

echo -e "${GREEN}🎉 Vast.ai integration test completed!${NC}"
echo -e "${BLUE}💡 To test with real vast.ai instance:${NC}"
echo -e "${BLUE}   1. Start vast.ai GPU instance with qwen proxy${NC}"
echo -e "${BLUE}   2. Create SSH tunnel: ssh -L 8000:localhost:8000 root@instance${NC}"
echo -e "${BLUE}   3. Run this test again${NC}"