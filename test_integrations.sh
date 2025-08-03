#!/bin/bash
# Comprehensive integration test script for Multi-LLM Proxy
# Tests Cerebras and Vast.ai backends with Claude CLI in headless mode

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TEST_PROMPT="Write a Python function to calculate the first 30 Fibonacci numbers and print them. Then run the code and show the output. Use proper error handling."
TEST_TIMEOUT=60
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source bashrc to get environment variables
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# Logging
LOG_FILE="/tmp/llm_proxy_integration_test.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

echo -e "${BLUE}🧪 Multi-LLM Proxy Integration Tests${NC}"
echo -e "${BLUE}====================================${NC}"
echo "Log file: $LOG_FILE"
echo "Test started at: $(date)"
echo ""

# Function to log with timestamp
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to test a specific backend
test_backend() {
    local backend_name=$1
    local backend_flag=$2
    
    log "${BLUE}🔧 Testing $backend_name backend${NC}"
    echo "========================================"
    
    # Step 1: Start the proxy server with specific backend
    log "${BLUE}🚀 Starting proxy server with $backend_name backend...${NC}"
    
    # Use our startup script to configure and start the backend
    env CEREBRAS_API_KEY="$CEREBRAS_API_KEY" timeout 30 "$SCRIPT_DIR/llm_proxy_start.sh" $backend_flag --test &
    local setup_pid=$!
    
    # Wait for setup to complete or timeout
    wait $setup_pid
    local setup_result=$?
    
    if [ $setup_result -ne 0 ]; then
        log "${RED}❌ Failed to setup $backend_name backend${NC}"
        return 1
    fi
    
    # Step 2: Start the proxy server manually for testing
    log "${BLUE}🚀 Starting proxy server for testing...${NC}"
    
    # Configure the backend first
    case $backend_flag in
        --cerebras)
            if [ -z "$CEREBRAS_API_KEY" ]; then
                log "${RED}❌ CEREBRAS_API_KEY not found${NC}"
                log "${BLUE}💡 Available env vars: $(env | grep -E 'CEREBRAS|API_KEY' | cut -d= -f1 | tr '\n' ' ')${NC}"
                return 1
            fi
            
            log "${GREEN}✅ Using Cerebras API key: ${CEREBRAS_API_KEY:0:10}...${NC}"
            
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
            ;;
        --vast)
            cat > .llmrc.json << EOF
{
  "backend": "self-hosted",
  "port": "auto",
  "backends": {
    "self-hosted": {
      "type": "self-hosted",
      "url": "http://localhost:8000",
      "description": "Vast.ai GPU instance"
    }
  }
}
EOF
            ;;
    esac
    
    chmod 600 .llmrc.json
    
    # Start proxy server in background
    if command -v llm-proxy >/dev/null 2>&1; then
        llm-proxy start &
    else
        node ./bin/llm-proxy.js start &
    fi
    local proxy_pid=$!
    
    # Wait for proxy to start
    sleep 5
    
    # Step 3: Test health endpoint
    log "${BLUE}🔍 Testing proxy health endpoint...${NC}"
    local health_test=false
    for i in {1..10}; do
        if curl -s --connect-timeout 3 http://localhost:8000/health > /dev/null 2>&1; then
            log "${GREEN}✅ Proxy health check passed${NC}"
            health_test=true
            break
        fi
        sleep 1
    done
    
    if [ "$health_test" = false ]; then
        log "${RED}❌ Proxy health check failed${NC}"
        kill $proxy_pid 2>/dev/null || true
        return 1
    fi
    
    # Step 4: Test Claude CLI integration
    log "${BLUE}🤖 Testing Claude CLI integration with $backend_name...${NC}"
    
    # Set environment to use our proxy
    export ANTHROPIC_BASE_URL="http://localhost:8000"
    
    # Run Claude in headless mode with verbose output
    log "${BLUE}📝 Prompt: $TEST_PROMPT${NC}"
    
    local claude_output
    claude_output=$(timeout $TEST_TIMEOUT claude --verbose -p "$TEST_PROMPT" 2>&1)
    local claude_result=$?
    
    # Step 5: Analyze results
    log "${BLUE}📊 Analyzing results...${NC}"
    
    # Check if Claude command succeeded
    if [ $claude_result -eq 0 ]; then
        log "${GREEN}✅ Claude CLI executed successfully${NC}"
    else
        log "${RED}❌ Claude CLI failed with exit code: $claude_result${NC}"
        log "${YELLOW}Output: $claude_output${NC}"
        kill $proxy_pid 2>/dev/null || true
        return 1
    fi
    
    # Check if response contains expected content
    if echo "$claude_output" | grep -qi "fibonacci"; then
        log "${GREEN}✅ Response contains Fibonacci content${NC}"
    else
        log "${RED}❌ Response missing expected Fibonacci content${NC}"
        log "${YELLOW}Output: $claude_output${NC}"
        kill $proxy_pid 2>/dev/null || true
        return 1
    fi
    
    # Check if response contains Python code
    if echo "$claude_output" | grep -qi "def\|python"; then
        log "${GREEN}✅ Response contains Python code${NC}"
    else
        log "${YELLOW}⚠️  Response may not contain expected Python code${NC}"
    fi
    
    # Step 6: Log full response for analysis
    log "${BLUE}📋 Full Claude response:${NC}"
    echo "----------------------------------------"
    echo "$claude_output"
    echo "----------------------------------------"
    
    # Step 7: Cleanup
    log "${BLUE}🧹 Cleaning up $backend_name test...${NC}"
    kill $proxy_pid 2>/dev/null || true
    wait $proxy_pid 2>/dev/null || true
    rm -f .llmrc.json
    
    log "${GREEN}🎉 $backend_name test completed successfully!${NC}"
    return 0
}

# Function to run all tests
run_all_tests() {
    local total_tests=0
    local passed_tests=0
    local failed_backends=()
    
    log "${BLUE}🚀 Starting comprehensive integration tests...${NC}"
    
    # Test Cerebras backend
    echo ""
    log "${YELLOW}==== Testing Cerebras Backend ====${NC}"
    if test_backend "Cerebras" "--cerebras"; then
        ((passed_tests++))
    else
        failed_backends+=("Cerebras")
    fi
    ((total_tests++))
    
    # Test Vast.ai backend (if available)
    echo ""
    log "${YELLOW}==== Testing Vast.ai Backend ====${NC}"
    if command -v vastai >/dev/null 2>&1; then
        if test_backend "Vast.ai" "--vast"; then
            ((passed_tests++))
        else
            failed_backends+=("Vast.ai")
        fi
        ((total_tests++))
    else
        log "${YELLOW}⚠️  Skipping Vast.ai test (vastai CLI not installed)${NC}"
    fi
    
    # Final results
    echo ""
    log "${BLUE}📊 Final Test Results${NC}"
    echo "========================================"
    log "${GREEN}✅ Passed: $passed_tests/$total_tests backends${NC}"
    
    if [ ${#failed_backends[@]} -gt 0 ]; then
        log "${RED}❌ Failed backends: ${failed_backends[*]}${NC}"
    fi
    
    if [ $passed_tests -eq $total_tests ] && [ $total_tests -gt 0 ]; then
        log "${GREEN}🎉 All integration tests passed!${NC}"
        return 0
    else
        log "${RED}❌ Some integration tests failed${NC}"
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --cerebras    Test Cerebras backend only"
    echo "  --vast        Test Vast.ai backend only"
    echo "  --all         Test all available backends (default)"
    echo "  --help        Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  CEREBRAS_API_KEY    Required for Cerebras testing"
    echo ""
    echo "Examples:"
    echo "  $0                    # Test all backends"
    echo "  $0 --cerebras        # Test Cerebras only"
    echo "  $0 --vast            # Test Vast.ai only"
}

# Main execution
case ${1:-"--all"} in
    --cerebras)
        log "${BLUE}🧠 Testing Cerebras backend only${NC}"
        test_backend "Cerebras" "--cerebras"
        ;;
    --vast)
        log "${BLUE}🚀 Testing Vast.ai backend only${NC}"
        test_backend "Vast.ai" "--vast"
        ;;
    --all)
        run_all_tests
        ;;
    --help)
        show_usage
        ;;
    *)
        log "${RED}❌ Unknown option: $1${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac

test_result=$?

echo ""
log "${BLUE}Test completed at: $(date)${NC}"
log "${BLUE}Full log available at: $LOG_FILE${NC}"

exit $test_result