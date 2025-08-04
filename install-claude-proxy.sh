#!/bin/bash
# Claude Code CLI Proxy Installer
# Unified installer for vast.ai, Cerebras, and local deployment

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_NAME="Claude Code CLI Proxy Installer"
VERSION="1.0.0"

echo -e "${BLUE}🚀 $SCRIPT_NAME v$VERSION${NC}"
echo "======================================="
echo ""

# Configuration file
CONFIG_FILE="$HOME/.claude-proxy-config"

# Functions
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

check_python() {
    if command_exists python3; then
        local version
        version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        echo -e "${GREEN}✅ Python $version found${NC}"
        return 0
    else
        echo -e "${RED}❌ Python 3 not found${NC}"
        return 1
    fi
}

install_dependencies() {
    echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
    
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
    else
        echo -e "${YELLOW}⚠️  requirements.txt not found, installing core dependencies${NC}"
        pip3 install fastapi 'uvicorn[standard]' requests redis
    fi
    
    echo -e "${GREEN}✅ Dependencies installed${NC}"
}

configure_backend() {
    echo -e "${BLUE}🔧 Backend Configuration${NC}"
    echo "Choose your backend:"
    echo "1) Vast.ai + Qwen (requires SSH setup)"
    echo "2) Cerebras Cloud API (requires API key)"
    echo "3) Local Ollama (install locally)"
    echo ""
    read -p "Enter choice (1-3): " BACKEND_CHOICE
    
    case $BACKEND_CHOICE in
        1)
            configure_vastai
            ;;
        2)
            configure_cerebras
            ;;
        3)
            configure_local
            ;;
        *)
            echo -e "${RED}❌ Invalid choice${NC}"
            exit 1
            ;;
    esac
}

configure_vastai() {
    echo -e "${YELLOW}📡 Vast.ai Configuration${NC}"
    
    read -p "Vast.ai SSH host (e.g., ssh7.vast.ai): " VAST_SSH_HOST
    : "${VAST_SSH_HOST:?Vast.ai SSH host is required}"
    read -p "Vast.ai SSH port (e.g., 12806): " VAST_SSH_PORT
    : "${VAST_SSH_PORT:?Vast.ai SSH port is required}"
    read -p "Vast.ai SSH user (default: root): " VAST_USER
    VAST_USER=${VAST_USER:-root}
    
    # Save configuration
    cat > "$CONFIG_FILE" << EOF
BACKEND=vastai
VAST_SSH_HOST=$VAST_SSH_HOST
VAST_SSH_PORT=$VAST_SSH_PORT
VAST_USER=$VAST_USER
LOCAL_PORT=8001
VAST_PORT=8000
EOF
    
    echo -e "${GREEN}✅ Vast.ai configuration saved${NC}"
    echo -e "${YELLOW}Note: Make sure your vast.ai instance is running with the startup script${NC}"
}

configure_cerebras() {
    echo -e "${YELLOW}🧠 Cerebras Configuration${NC}"
    
    read -p "Cerebras API Key: " CEREBRAS_API_KEY
    
    # Save configuration
    cat > "$CONFIG_FILE" << EOF
BACKEND=cerebras
CEREBRAS_API_KEY=$CEREBRAS_API_KEY
LOCAL_PORT=8001
EOF
    
    echo -e "${GREEN}✅ Cerebras configuration saved${NC}"
}

configure_local() {
    echo -e "${YELLOW}🏠 Local Configuration${NC}"
    echo "Choose local backend:"
    echo "1) Ollama (download and install models locally)"
    echo "2) LM Studio (use existing LM Studio on Windows/macOS)"
    echo ""
    read -p "Enter choice (1-2): " LOCAL_CHOICE
    
    case $LOCAL_CHOICE in
        1)
            configure_ollama
            ;;
        2)
            configure_lm_studio
            ;;
        *)
            echo -e "${RED}❌ Invalid choice${NC}"
            exit 1
            ;;
    esac
}

configure_ollama() {
    echo -e "${YELLOW}🦙 Ollama Configuration${NC}"
    
    if ! command_exists ollama; then
        echo -e "${BLUE}Installing Ollama...${NC}"
        echo -e "${YELLOW}⚠️  About to download and run Ollama installer from the internet${NC}"
        read -p "Continue? (y/N): " confirm
        if [[ "$confirm" != "y" ]]; then
            echo "Installation cancelled"
            exit 1
        fi
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    
    echo -e "${BLUE}Pulling qwen3-coder model...${NC}"
    ollama pull qwen3-coder || ollama pull qwen2.5-coder:7b
    
    # Save configuration
    cat > "$CONFIG_FILE" << EOF
BACKEND=ollama
OLLAMA_HOST=localhost:11434
LOCAL_PORT=8001
EOF
    
    echo -e "${GREEN}✅ Ollama configuration saved${NC}"
}

configure_lm_studio() {
    echo -e "${YELLOW}🏠 LM Studio Configuration${NC}"
    echo "This will connect to LM Studio running on your Windows/macOS host"
    echo ""
    
    read -p "LM Studio port (default: 1234): " LM_PORT
    LM_PORT=${LM_PORT:-1234}
    
    read -p "Expected model name (default: auto-detect): " LM_MODEL
    LM_MODEL=${LM_MODEL:-auto-detect}
    
    # Save configuration
    cat > "$CONFIG_FILE" << EOF
BACKEND=lmstudio
LM_STUDIO_PORT=$LM_PORT
LM_STUDIO_MODEL=$LM_MODEL
LOCAL_PORT=8001
EOF
    
    echo -e "${GREEN}✅ LM Studio configuration saved${NC}"
    echo -e "${YELLOW}Note: Make sure LM Studio server is enabled with a model loaded${NC}"
}

setup_claude_cli() {
    echo -e "${BLUE}🔧 Configuring Claude CLI...${NC}"
    
    # Load configuration
    source "$CONFIG_FILE"
    
    # Set environment variables
    export ANTHROPIC_BASE_URL="http://localhost:$LOCAL_PORT"
    export ANTHROPIC_API_KEY="dummy"
    
    # Add to shell profile
    SHELL_PROFILE=""
    if [ -f "$HOME/.bashrc" ]; then
        SHELL_PROFILE="$HOME/.bashrc"
    elif [ -f "$HOME/.zshrc" ]; then
        SHELL_PROFILE="$HOME/.zshrc"
    fi
    
    if [ -n "$SHELL_PROFILE" ]; then
        grep -qxF 'export ANTHROPIC_BASE_URL=' "$SHELL_PROFILE" || echo 'export ANTHROPIC_BASE_URL="http://localhost:$LOCAL_PORT"' >> "$SHELL_PROFILE"
        grep -qxF 'export ANTHROPIC_API_KEY=' "$SHELL_PROFILE" || echo 'export ANTHROPIC_API_KEY="dummy"' >> "$SHELL_PROFILE"
        
        echo -e "${GREEN}✅ Environment variables added to $SHELL_PROFILE${NC}"
        echo -e "${YELLOW}Run 'source $SHELL_PROFILE' or restart terminal to apply${NC}"
    fi
}

create_startup_script() {
    echo -e "${BLUE}📝 Creating startup script...${NC}"
    
    cat > claude-proxy-start.sh << 'EOL'
#!/bin/bash
set -euo pipefail
exec >>"$HOME/.claude-proxy.log" 2>&1
# Claude Proxy Startup Script

CONFIG_FILE="$HOME/.claude-proxy-config"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Configuration file not found. Run install-claude-proxy.sh first."
    exit 1
fi

source "$CONFIG_FILE"

case $BACKEND in
    vastai)
        echo "🚀 Starting Vast.ai proxy..."
        ./claude-vast &
        sleep 3
        python3 claude_code_tools_proxy.py
        ;;
    cerebras)
        echo "🧠 Starting Cerebras proxy..."
        export CEREBRAS_API_KEY="$CEREBRAS_API_KEY"
        python3 cerebras_proxy.py
        ;;
    ollama)
        echo "🦙 Starting Ollama proxy..."
        ollama serve &
        sleep 5
        python3 claude_code_tools_proxy.py
        ;;
    lmstudio)
        echo "🏠 Starting LM Studio proxy..."
        export LM_STUDIO_PORT="$LM_STUDIO_PORT"
        export LM_STUDIO_MODEL="$LM_STUDIO_MODEL"
        ./claude-local
        ;;
esac
EOL
    
    chmod +x claude-proxy-start.sh
    echo -e "${GREEN}✅ Startup script created: ./claude-proxy-start.sh${NC}"
}

test_setup() {
    echo -e "${BLUE}🧪 Testing setup...${NC}"
    
    # Load config
    source "$CONFIG_FILE"
    
    # Start proxy in background for testing
    case $BACKEND in
        cerebras)
            export CEREBRAS_API_KEY="$CEREBRAS_API_KEY"
            python3 cerebras_proxy.py &
            ;;
        *)
            python3 claude_code_tools_proxy.py &
            ;;
    esac
    
    PROXY_PID=$!
    sleep 3
    
    # Test health endpoint
    if curl -s "http://localhost:$LOCAL_PORT/health" > /dev/null; then
        echo -e "${GREEN}✅ Proxy is responding${NC}"
        kill $PROXY_PID 2>/dev/null
        return 0
    else
        echo -e "${RED}❌ Proxy not responding${NC}"
        kill $PROXY_PID 2>/dev/null
        return 1
    fi
}

# Main installation flow
main() {
    echo -e "${BLUE}Starting installation...${NC}"
    echo ""
    
    # Check Python
    if ! check_python; then
        echo -e "${RED}Please install Python 3.8+ and try again${NC}"
        exit 1
    fi
    
    # Install dependencies
    install_dependencies
    
    # Configure backend
    configure_backend
    
    # Setup Claude CLI
    setup_claude_cli
    
    # Create startup script
    create_startup_script
    
    # Test setup
    if test_setup; then
        echo ""
        echo -e "${GREEN}🎉 Installation completed successfully!${NC}"
        echo ""
        echo -e "${BLUE}To start the proxy:${NC}"
        echo "  ./claude-proxy-start.sh"
        echo ""
        echo -e "${BLUE}To use with Claude CLI:${NC}"
        echo "  source ~/.bashrc  # or restart terminal"
        echo "  claude --help"
        echo ""
    else
        echo -e "${RED}❌ Installation completed but proxy test failed${NC}"
        echo "Check the configuration and try running ./claude-proxy-start.sh manually"
    fi
}

# Run main installation
main "$@"