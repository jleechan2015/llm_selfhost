#!/bin/bash
# Test Claude Code CLI Interactive Mode with Tool-Enabled Proxy

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🤖 Testing Claude Code CLI Interactive Mode${NC}"
echo "================================================="

# Check if proxy is running
if ! curl -s http://localhost:8001/health >/dev/null 2>&1; then
    echo -e "${RED}❌ Tool-enabled proxy not running${NC}"
    echo "Start with: python3 claude_code_tools_proxy.py &"
    exit 1
fi

echo -e "${GREEN}✅ Tool-enabled proxy is running${NC}"

# Set environment for Claude Code CLI
export ANTHROPIC_BASE_URL="http://localhost:8001"
export ANTHROPIC_API_KEY="dummy"

echo -e "${BLUE}🔧 Environment configured:${NC}"
echo "ANTHROPIC_BASE_URL: $ANTHROPIC_BASE_URL"
echo ""

# Test interactive mode with a series of commands
echo -e "${BLUE}🧪 Starting Interactive Mode Test${NC}"
echo "Testing Claude Code CLI with tool execution..."
echo ""

# Create a script to send multiple commands to Claude
cat > interactive_test_commands.txt << 'EOF'
Create a Python script called 'hello_interactive.py' that prints "Interactive mode working!" and run it
List all .py files in the current directory and count them
Show me the current working directory
Create a simple text file with today's date and time
EOF

echo -e "${YELLOW}Commands to test:${NC}"
cat interactive_test_commands.txt
echo ""

# Test each command
echo -e "${BLUE}🚀 Executing interactive commands...${NC}"
echo ""

COMMAND_COUNT=1
while IFS= read -r command; do
    if [ -n "$command" ]; then
        echo -e "${BLUE}Command $COMMAND_COUNT: ${NC}$command"
        echo "----------------------------------------"
        
        # Execute the command with timeout
        timeout 45 claude --model "claude-3-5-sonnet-20241022" -p "$command"
        EXIT_CODE=$?
        
        if [ $EXIT_CODE -eq 0 ]; then
            echo -e "${GREEN}✅ Command $COMMAND_COUNT completed successfully${NC}"
        else
            echo -e "${RED}❌ Command $COMMAND_COUNT failed (exit code: $EXIT_CODE)${NC}"
        fi
        
        echo ""
        echo "================================================="
        echo ""
        
        ((COMMAND_COUNT++))
        
        # Brief pause between commands
        sleep 2
    fi
done < interactive_test_commands.txt

echo -e "${BLUE}📊 Interactive Mode Test Complete${NC}"

# Clean up
rm -f interactive_test_commands.txt

echo ""
echo -e "${GREEN}🎉 Interactive mode testing finished!${NC}"
echo "Check the files created during the test:"
echo "- hello_interactive.py"
echo "- Any other files created by the commands"