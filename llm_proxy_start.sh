#!/bin/bash
# Enhanced Multi-LLM Proxy startup script for Claude Code CLI
# Adapted from claude_start.sh for llm-proxy server integration
# Tests Cerebras, vast.ai, and other backends with TDD approach

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
FORCE_CLEAN=false
MODE=""
TEST_MODE=false
REMAINING_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--clean)
            FORCE_CLEAN=true
            shift
            ;;
        --cerebras)
            MODE="cerebras"
            shift
            ;;
        --vast)
            MODE="vast"
            shift
            ;;
        --local)
            MODE="local"
            shift
            ;;
        --test)
            TEST_MODE=true
            shift
            ;;
        *)
            REMAINING_ARGS+=("$1")
            shift
            ;;
    esac
done

# Restore remaining arguments
set -- "${REMAINING_ARGS[@]}"

echo -e "${BLUE}🚀 Multi-LLM Proxy Startup Script${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Check for required dependencies
if ! command -v jq >/dev/null 2>&1; then
    echo -e "${RED}❌ jq is required but not installed${NC}"
    echo "Please install jq: sudo apt-get install jq (or equivalent for your OS)"
    exit 1
fi

# Check if llm-proxy CLI is available
if ! command -v llm-proxy >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  llm-proxy CLI not found, checking local installation...${NC}"
    if [ -f "./bin/llm-proxy.js" ]; then
        echo -e "${GREEN}✅ Found local llm-proxy.js${NC}"
        LLM_PROXY_CMD="node ./bin/llm-proxy.js"
    else
        echo -e "${RED}❌ llm-proxy not found. Please install or run npm install${NC}"
        exit 1
    fi
else
    LLM_PROXY_CMD="llm-proxy"
fi

# Check if Claude CLI is available (for end-to-end testing)
if ! command -v claude >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Claude CLI not found - end-to-end testing will be limited${NC}"
    CLAUDE_AVAILABLE=false
else
    echo -e "${GREEN}✅ Claude CLI found${NC}"
    CLAUDE_AVAILABLE=true
fi

# Function to test backend health
test_backend_health() {
    local backend_name=$1
    local base_url=$2
    
    echo -e "${BLUE}🔍 Testing $backend_name health...${NC}"
    
    # Test health endpoint
    if curl -s --connect-timeout 5 "$base_url/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $backend_name health check passed${NC}"
        return 0
    else
        echo -e "${RED}❌ $backend_name health check failed${NC}"
        return 1
    fi
}

# Function to test API compatibility
test_api_compatibility() {
    local backend_name=$1
    local base_url=$2
    
    echo -e "${BLUE}🔍 Testing $backend_name API compatibility...${NC}"
    
    # Test models endpoint
    local models_response=$(curl -s --connect-timeout 5 "$base_url/v1/models" 2>/dev/null)
    if echo "$models_response" | jq -e '.data[]?' > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $backend_name models endpoint working${NC}"
    else
        echo -e "${RED}❌ $backend_name models endpoint failed${NC}"
        return 1
    fi
    
    # Test messages endpoint with simple request
    local test_request='{
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 10
    }'
    
    local response=$(curl -s --connect-timeout 10 \
        -X POST "$base_url/v1/messages" \
        -H "Content-Type: application/json" \
        -d "$test_request" 2>/dev/null)
    
    if echo "$response" | jq -e '.content[]?' > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $backend_name messages endpoint working${NC}"
        return 0
    else
        echo -e "${RED}❌ $backend_name messages endpoint failed${NC}"
        echo -e "${YELLOW}Response: $response${NC}"
        return 1
    fi
}

# Function to run end-to-end test with Claude CLI
test_claude_integration() {
    local backend_name=$1
    local base_url=$2
    
    if [ "$CLAUDE_AVAILABLE" = false ]; then
        echo -e "${YELLOW}⚠️  Skipping Claude CLI integration test (Claude CLI not available)${NC}"
        return 0
    fi
    
    echo -e "${BLUE}🔍 Testing Claude CLI integration with $backend_name...${NC}"
    
    # Set environment variables
    export ANTHROPIC_BASE_URL="$base_url"
    
    # Test simple Claude CLI request
    local claude_response=$(timeout 30 claude "Say 'test successful' and nothing else" 2>/dev/null || echo "TIMEOUT")
    
    if echo "$claude_response" | grep -q "test successful"; then
        echo -e "${GREEN}✅ Claude CLI integration test passed${NC}"
        return 0
    else
        echo -e "${RED}❌ Claude CLI integration test failed${NC}"
        echo -e "${YELLOW}Response: $claude_response${NC}"
        return 1
    fi
}

# Function to setup Cerebras backend
setup_cerebras() {
    echo -e "${BLUE}🧠 Setting up Cerebras backend...${NC}"
    
    # Check for API key in bashrc
    if [ -z "$CEREBRAS_API_KEY" ]; then
        if [ -f ~/.bashrc ]; then
            source ~/.bashrc
        fi
    fi
    
    if [ -z "$CEREBRAS_API_KEY" ]; then
        echo -e "${RED}❌ CEREBRAS_API_KEY not found in environment${NC}"
        echo -e "${BLUE}💡 Set it with: export CEREBRAS_API_KEY='your-key-here'${NC}"
        echo -e "${BLUE}💡 Debug: $(env | grep -E 'CEREBRAS|API_KEY' | head -3)${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Found Cerebras API key: ${CEREBRAS_API_KEY:0:10}...${NC}"
    
    # Test API key validity
    echo -e "${BLUE}🔍 Testing Cerebras API key...${NC}"
    local response=$(curl -s -H "Authorization: Bearer $CEREBRAS_API_KEY" https://api.cerebras.ai/v1/models)
    if echo "$response" | grep -q "Wrong API Key\|invalid_request_error"; then
        echo -e "${RED}❌ Cerebras API key validation failed${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Cerebras API key validated${NC}"
    
    # Generate configuration for Cerebras
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
    echo -e "${GREEN}✅ Cerebras configuration created${NC}"
    return 0
}

# Function to setup vast.ai backend
setup_vast() {
    echo -e "${BLUE}🚀 Setting up vast.ai backend...${NC}"
    
    # Check if vastai CLI is installed
    if ! command -v vastai >/dev/null 2>&1; then
        echo -e "${RED}❌ Vast.ai CLI not found${NC}"
        echo -e "${BLUE}💡 Install with: pip install vastai${NC}"
        return 1
    fi
    
    # Check API key
    if ! vastai show user >/dev/null 2>&1; then
        echo -e "${RED}❌ Vast.ai API key not configured${NC}"
        echo -e "${BLUE}💡 Set API key with: vastai set api-key YOUR_KEY${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Vast.ai CLI configured${NC}"
    
    # Look for existing running instances with qwen label
    echo -e "${BLUE}🔍 Looking for existing qwen instances...${NC}"
    local existing_instances=$(vastai show instances --raw | jq -r '.[] | select(.actual_status == "running" and (.label // "" | contains("qwen"))) | .id' 2>/dev/null || echo "")
    
    local instance_url=""
    if [ -n "$existing_instances" ]; then
        for instance_id in $existing_instances; do
            echo -e "${GREEN}✅ Found existing instance: $instance_id${NC}"
            
            # Get connection details
            local instance_details=$(vastai show instance $instance_id --raw)
            local ssh_host=$(echo "$instance_details" | jq -r '.ssh_host')
            local ssh_port=$(echo "$instance_details" | jq -r '.ssh_port')
            
            echo -e "${BLUE}🔗 Testing connection to $ssh_host:$ssh_port${NC}"
            
            # Test if API is accessible via SSH tunnel
            if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
                -p "$ssh_port" root@"$ssh_host" 'curl -s http://localhost:8000/health' 2>/dev/null | grep -q "healthy"; then
                
                echo -e "${GREEN}✅ Instance $instance_id is healthy${NC}"
                instance_url="http://localhost:8000"
                
                # Create SSH tunnel
                pkill -f "ssh.*8000" 2>/dev/null || true
                ssh -N -L 8000:localhost:8000 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
                    -p "$ssh_port" root@"$ssh_host" &
                local tunnel_pid=$!
                echo $tunnel_pid > /tmp/vast_ssh_tunnel.pid
                
                sleep 3
                break
            else
                echo -e "${YELLOW}⚠️  Instance $instance_id not responding${NC}"
            fi
        done
    fi
    
    if [ -z "$instance_url" ]; then
        echo -e "${YELLOW}⚠️  No healthy existing instances found${NC}"
        echo -e "${BLUE}💡 For testing purposes, assuming local proxy at localhost:8000${NC}"
        instance_url="http://localhost:8000"
    fi
    
    # Generate configuration for vast.ai/self-hosted
    cat > .llmrc.json << EOF
{
  "backend": "self-hosted",
  "port": "auto",
  "backends": {
    "self-hosted": {
      "type": "self-hosted",
      "url": "$instance_url",
      "description": "Vast.ai GPU instance or local proxy"
    }
  }
}
EOF
    chmod 600 .llmrc.json
    echo -e "${GREEN}✅ Vast.ai configuration created${NC}"
    return 0
}

# Function to setup local backend
setup_local() {
    echo -e "${BLUE}🏠 Setting up local backend...${NC}"
    
    # Generate configuration for local Ollama
    cat > .llmrc.json << EOF
{
  "backend": "self-hosted",
  "port": "auto",
  "backends": {
    "self-hosted": {
      "type": "self-hosted",
      "url": "http://localhost:11434",
      "description": "Local Ollama instance"
    }
  }
}
EOF
    chmod 600 .llmrc.json
    echo -e "${GREEN}✅ Local configuration created${NC}"
    return 0
}

# Function to run comprehensive tests
run_comprehensive_tests() {
    local backend_name=$1
    local passed_tests=0
    local total_tests=3
    
    echo -e "${BLUE}🧪 Running comprehensive tests for $backend_name${NC}"
    echo "============================================"
    
    # Start the proxy server
    echo -e "${BLUE}🚀 Starting proxy server...${NC}"
    $LLM_PROXY_CMD start &
    local proxy_pid=$!
    
    # Wait for server to start
    sleep 5
    
    # Get the server URL from status
    local server_status=$($LLM_PROXY_CMD status 2>/dev/null || echo "")
    local base_url="http://localhost:8000"  # Default assumption
    
    # Try to extract port from status output
    if echo "$server_status" | grep -q "Port:"; then
        local port=$(echo "$server_status" | grep "Port:" | awk '{print $2}')
        if [ -n "$port" ] && [ "$port" != "auto" ]; then
            base_url="http://localhost:$port"
        fi
    fi
    
    echo -e "${BLUE}📍 Testing against: $base_url${NC}"
    
    # Test 1: Health check
    if test_backend_health "$backend_name" "$base_url"; then
        ((passed_tests++))
    fi
    
    # Test 2: API compatibility
    if test_api_compatibility "$backend_name" "$base_url"; then
        ((passed_tests++))
    fi
    
    # Test 3: Claude CLI integration (if available)
    if test_claude_integration "$backend_name" "$base_url"; then
        ((passed_tests++))
    fi
    
    # Stop the proxy server
    kill $proxy_pid 2>/dev/null || true
    wait $proxy_pid 2>/dev/null || true
    
    # Cleanup
    rm -f .llmrc.json
    
    echo ""
    echo -e "${BLUE}📊 Test Results for $backend_name:${NC}"
    echo -e "${GREEN}✅ Passed: $passed_tests/$total_tests tests${NC}"
    
    if [ $passed_tests -eq $total_tests ]; then
        echo -e "${GREEN}🎉 All tests passed for $backend_name!${NC}"
        return 0
    else
        echo -e "${RED}❌ Some tests failed for $backend_name${NC}"
        return 1
    fi
}

# Main execution
if [ "$TEST_MODE" = true ]; then
    echo -e "${BLUE}🧪 Running in test mode${NC}"
    
    # Test all backends if no specific mode
    if [ -z "$MODE" ]; then
        echo -e "${BLUE}Testing all available backends...${NC}"
        
        total_backends=0
        passed_backends=0
        
        # Test Cerebras
        echo -e "${YELLOW}==== Testing Cerebras Backend ====${NC}"
        if setup_cerebras && run_comprehensive_tests "Cerebras"; then
            ((passed_backends++))
        fi
        ((total_backends++))
        
        echo ""
        
        # Test vast.ai
        echo -e "${YELLOW}==== Testing Vast.ai Backend ====${NC}"
        if setup_vast && run_comprehensive_tests "Vast.ai"; then
            ((passed_backends++))
        fi
        ((total_backends++))
        
        echo ""
        echo -e "${BLUE}📊 Overall Test Results:${NC}"
        echo -e "${GREEN}✅ $passed_backends/$total_backends backends passed all tests${NC}"
        
        if [ $passed_backends -eq $total_backends ]; then
            echo -e "${GREEN}🎉 All backend integrations working!${NC}"
            exit 0
        else
            echo -e "${RED}❌ Some backend integrations failed${NC}"
            exit 1
        fi
    fi
fi

# Handle specific backend modes
case $MODE in
    cerebras)
        echo -e "${BLUE}🧠 Cerebras mode selected${NC}"
        if setup_cerebras; then
            if [ "$TEST_MODE" = true ]; then
                run_comprehensive_tests "Cerebras"
            else
                echo -e "${GREEN}🚀 Starting proxy with Cerebras backend...${NC}"
                $LLM_PROXY_CMD start
            fi
        fi
        ;;
    vast)
        echo -e "${BLUE}🚀 Vast.ai mode selected${NC}"
        if setup_vast; then
            if [ "$TEST_MODE" = true ]; then
                run_comprehensive_tests "Vast.ai"
            else
                echo -e "${GREEN}🚀 Starting proxy with Vast.ai backend...${NC}"
                $LLM_PROXY_CMD start
            fi
        fi
        ;;
    local)
        echo -e "${BLUE}🏠 Local mode selected${NC}"
        if setup_local; then
            if [ "$TEST_MODE" = true ]; then
                run_comprehensive_tests "Local"
            else
                echo -e "${GREEN}🚀 Starting proxy with local backend...${NC}"
                $LLM_PROXY_CMD start
            fi
        fi
        ;;
    *)
        # Interactive mode
        echo -e "${BLUE}Select backend to test:${NC}"
        echo -e "${YELLOW}1) Cerebras (SaaS API)${NC}"
        echo -e "${BLUE}2) Vast.ai (GPU instances)${NC}"
        echo -e "${GREEN}3) Local (Ollama)${NC}"
        echo -e "${RED}4) Run all tests${NC}"
        read -p "Choice [1]: " choice
        
        case ${choice:-1} in
        1)
            MODE="cerebras"
            if setup_cerebras; then
                run_comprehensive_tests "Cerebras"
            fi
            ;;
        2)
            MODE="vast"
            if setup_vast; then
                run_comprehensive_tests "Vast.ai"
            fi
            ;;
        3)
            MODE="local"
            if setup_local; then
                run_comprehensive_tests "Local"
            fi
            ;;
        4)
            TEST_MODE=true
            MODE=""
            exec "$0" --test
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            exit 1
            ;;
        esac
        ;;
esac

# Cleanup function
cleanup() {
    echo -e "${BLUE}🧹 Cleaning up...${NC}"
    
    # Kill any SSH tunnels
    if [ -f /tmp/vast_ssh_tunnel.pid ]; then
        local pid=$(cat /tmp/vast_ssh_tunnel.pid)
        kill $pid 2>/dev/null || true
        rm -f /tmp/vast_ssh_tunnel.pid
    fi
    
    # Remove temporary config
    rm -f .llmrc.json
    
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Set up trap for cleanup on exit
trap cleanup EXIT