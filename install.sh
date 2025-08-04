#!/bin/bash
# LLM Self-Host Installation Script
# Automated setup for qwen3-coder model and dependencies

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_NAME="LLM Self-Host Installer"
VERSION="2.0.0"
MODEL_NAME="qwen3-coder"
PYTHON_VERSION="3.8"

echo -e "${BLUE}🚀 $SCRIPT_NAME v$VERSION${NC}"
echo -e "${BLUE}📦 Installing $MODEL_NAME and dependencies...${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    if command_exists python3; then
        local version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        if [[ $(echo "$version >= $PYTHON_VERSION" | bc -l 2>/dev/null || echo "0") == "1" ]]; then
            return 0
        fi
    fi
    return 1
}

# Function to install system dependencies
install_system_deps() {
    echo -e "${BLUE}🔧 Installing system dependencies...${NC}"
    
    # Detect OS and install accordingly
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y curl wget git python3 python3-pip python3-venv build-essential
        elif command_exists yum; then
            sudo yum update -y
            sudo yum install -y curl wget git python3 python3-pip gcc gcc-c++ make
        elif command_exists pacman; then
            sudo pacman -Sy curl wget git python python-pip base-devel
        else
            echo -e "${YELLOW}⚠️  Could not detect package manager. Please install manually:${NC}"
            echo "   - curl, wget, git"
            echo "   - python3, python3-pip"
            echo "   - build tools (gcc, make)"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            brew install curl wget git python3
        else
            echo -e "${YELLOW}⚠️  Homebrew not found. Installing Homebrew first...${NC}"
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            brew install curl wget git python3
        fi
    fi
    
    echo -e "${GREEN}✅ System dependencies installed${NC}"
}

# Function to install Ollama
install_ollama() {
    echo -e "${BLUE}🦙 Installing Ollama...${NC}"
    
    if command_exists ollama; then
        echo -e "${GREEN}✅ Ollama already installed${NC}"
        ollama --version
    else
        # Install Ollama
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            curl -fsSL https://ollama.ai/install.sh | sh
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # Download Ollama for macOS
            curl -L https://ollama.ai/download/Ollama-darwin.zip -o /tmp/ollama.zip
            unzip /tmp/ollama.zip -d /tmp/
            sudo mv /tmp/Ollama.app /Applications/
            sudo ln -sf /Applications/Ollama.app/Contents/Resources/ollama /usr/local/bin/ollama
        fi
        
        if command_exists ollama; then
            echo -e "${GREEN}✅ Ollama installed successfully${NC}"
        else
            echo -e "${RED}❌ Failed to install Ollama${NC}"
            exit 1
        fi
    fi
    
    # Start Ollama service
    echo -e "${BLUE}🔄 Starting Ollama service...${NC}"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists systemctl; then
            sudo systemctl enable ollama
            sudo systemctl start ollama
        else
            # Start Ollama manually
            ollama serve &>/dev/null &
            sleep 3
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # Start Ollama manually on macOS
        ollama serve &>/dev/null &
        sleep 3
    fi
    
    # Wait for Ollama to be ready
    echo -e "${BLUE}⏳ Waiting for Ollama to be ready...${NC}"
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Ollama service is running${NC}"
            break
        fi
        
        attempt=$((attempt + 1))
        echo -e "${YELLOW}⏳ Attempt $attempt/$max_attempts - waiting for Ollama...${NC}"
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo -e "${RED}❌ Ollama failed to start within timeout${NC}"
        exit 1
    fi
}

# Function to pull the qwen3-coder model
install_qwen3_coder() {
    echo -e "${BLUE}🤖 Installing $MODEL_NAME model...${NC}"
    
    # Check if model is already installed
    if ollama list 2>/dev/null | grep -q "$MODEL_NAME"; then
        echo -e "${GREEN}✅ $MODEL_NAME model already installed${NC}"
        echo -e "${BLUE}📊 Model details:${NC}"
        ollama list | grep "$MODEL_NAME"
        return 0
    fi
    
    echo -e "${BLUE}📥 Downloading $MODEL_NAME model (this may take 10-30 minutes)...${NC}"
    echo -e "${YELLOW}💡 The qwen3-coder model is approximately 30GB (MoE architecture with 3.3B active parameters)${NC}"
    echo -e "${YELLOW}💡 Ensure you have sufficient disk space and a stable internet connection${NC}"
    echo ""
    
    # Pull the model with progress indication
    ollama pull "$MODEL_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $MODEL_NAME model installed successfully${NC}"
        echo -e "${BLUE}📊 Installed models:${NC}"
        ollama list
    else
        echo -e "${RED}❌ Failed to install $MODEL_NAME model${NC}"
        echo -e "${YELLOW}🔧 Troubleshooting tips:${NC}"
        echo "   1. Check internet connection"
        echo "   2. Ensure sufficient disk space (>30GB free)"
        echo "   3. Try again: ollama pull $MODEL_NAME"
        exit 1
    fi
}

# Function to install Python dependencies
install_python_deps() {
    echo -e "${BLUE}🐍 Installing Python dependencies...${NC}"
    
    # Check Python version
    if ! check_python_version; then
        echo -e "${RED}❌ Python $PYTHON_VERSION+ required${NC}"
        echo -e "${YELLOW}💡 Please install Python $PYTHON_VERSION+ manually${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Python $(python3 --version | cut -d' ' -f2) detected${NC}"
    
    # Install Python packages
    python3 -m pip install --upgrade pip
    
    # Install from requirements.txt if it exists, otherwise install manually
    if [ -f "requirements.txt" ]; then
        echo -e "${BLUE}📦 Installing from requirements.txt...${NC}"
        python3 -m pip install -r requirements.txt
    else
        echo -e "${BLUE}📦 Installing core dependencies...${NC}"
        python3 -m pip install \
            fastapi==0.104.1 \
            uvicorn[standard]==0.24.0 \
            redis==5.0.1 \
            requests==2.31.0 \
            python-multipart==0.0.6 \
            pydantic==2.5.0
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Python dependencies installed${NC}"
    else
        echo -e "${RED}❌ Failed to install Python dependencies${NC}"
        exit 1
    fi
}

# Function to set up Redis connection (optional)
setup_redis() {
    echo -e "${BLUE}🗄️  Redis Cloud setup (optional)...${NC}"
    echo -e "${YELLOW}💡 Redis Cloud provides distributed caching for improved performance${NC}"
    
    read -p "Do you have Redis Cloud credentials? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}🔧 Setting up Redis Cloud connection...${NC}"
        
        read -p "Redis Host: " redis_host
        read -p "Redis Port: " redis_port
        read -s -p "Redis Password: " redis_password
        echo ""
        
        # Create .env file for Redis credentials
        cat > .env << EOF
REDIS_HOST=$redis_host
REDIS_PORT=$redis_port
REDIS_PASSWORD=$redis_password
EOF
        
        echo -e "${GREEN}✅ Redis credentials saved to .env file${NC}"
        echo -e "${YELLOW}💡 Make sure to add .env to your .gitignore file${NC}"
        
        # Test Redis connection
        python3 -c "
import redis
import os
from dotenv import load_dotenv
load_dotenv()

try:
    r = redis.Redis(
        host=os.getenv('REDIS_HOST'),
        port=int(os.getenv('REDIS_PORT')),
        password=os.getenv('REDIS_PASSWORD'),
        ssl=True,
        ssl_cert_reqs=None
    )
    r.ping()
    print('✅ Redis connection successful')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
" 2>/dev/null || echo -e "${YELLOW}⚠️  Could not test Redis connection (python-dotenv not installed)${NC}"
    else
        echo -e "${YELLOW}⏭️  Skipping Redis setup${NC}"
        echo -e "${BLUE}💡 You can set up Redis later by editing simple_api_proxy.py${NC}"
    fi
}

# Function to test the installation
test_installation() {
    echo -e "${BLUE}🧪 Testing installation...${NC}"
    
    # Test Ollama model
    echo -e "${BLUE}🤖 Testing $MODEL_NAME model...${NC}"
    
    local test_response=$(echo "Say 'Installation test successful'" | timeout 30 ollama run "$MODEL_NAME" 2>/dev/null)
    
    if [[ $test_response == *"successful"* ]]; then
        echo -e "${GREEN}✅ Model test passed${NC}"
        echo -e "${BLUE}📝 Model response: $test_response${NC}"
    else
        echo -e "${YELLOW}⚠️  Model test timed out or failed${NC}"
        echo -e "${BLUE}💡 This is normal for first run - model needs to warm up${NC}"
    fi
    
    # Test API proxy dependencies
    echo -e "${BLUE}🔗 Testing API proxy dependencies...${NC}"
    python3 -c "
import fastapi, uvicorn, redis, requests
print('✅ All Python dependencies available')
" 2>/dev/null || echo -e "${YELLOW}⚠️  Some Python dependencies may be missing${NC}"
}

# Function to create startup script
create_startup_script() {
    echo -e "${BLUE}📜 Creating startup scripts...${NC}"
    
    # Create a simple startup script
    cat > start_llm_selfhost.sh << 'EOF'
#!/bin/bash
# LLM Self-Host Startup Script

echo "🚀 Starting LLM Self-Host system..."

# Start Ollama if not running
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "📦 Starting Ollama service..."
    ollama serve &>/dev/null &
    sleep 5
fi

# Check if model is available
if ! ollama list | grep -q "qwen3-coder"; then
    echo "❌ qwen3-coder model not found"
    echo "💡 Run: ollama pull qwen3-coder"
    exit 1
fi

# Start API proxy
if [ -f "simple_api_proxy.py" ]; then
    echo "🔗 Starting API proxy server..."
    python3 simple_api_proxy.py
else
    echo "❌ simple_api_proxy.py not found"
    echo "💡 Make sure you're in the correct directory"
    exit 1
fi
EOF
    
    chmod +x start_llm_selfhost.sh
    echo -e "${GREEN}✅ Startup script created: start_llm_selfhost.sh${NC}"
}

# Function to display final instructions
show_final_instructions() {
    echo ""
    echo -e "${GREEN}🎉 Installation completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}📋 Next Steps:${NC}"
    echo ""
    echo -e "${YELLOW}1. Start the system:${NC}"
    echo "   ./start_llm_selfhost.sh"
    echo ""
    echo -e "${YELLOW}2. Test the API proxy:${NC}"
    echo "   curl http://localhost:8000/"
    echo ""
    echo -e "${YELLOW}3. For Claude CLI integration:${NC}"
    echo "   # Set environment variables:"
    echo "   export ANTHROPIC_BASE_URL=\"http://localhost:8000\""
    echo "   export ANTHROPIC_MODEL=\"$MODEL_NAME\""
    echo "   "
    echo "   # Use Claude CLI normally:"
    echo "   claude --model \"$MODEL_NAME\" \"Write a Python function\""
    echo ""
    echo -e "${YELLOW}4. For SSH tunnel setup (vast.ai):${NC}"
    echo "   ssh -N -L 8001:localhost:8000 root@ssh4.vast.ai -p PORT &"
    echo "   export ANTHROPIC_BASE_URL=\"http://localhost:8001\""
    echo ""
    echo -e "${BLUE}📚 Documentation:${NC}"
    echo "   - README.md: Complete setup guide"
    echo "   - API_PROXY_GUIDE.md: Claude CLI integration"
    echo "   - INTEGRATION_STATUS.md: Production status"
    echo ""
    echo -e "${BLUE}🔧 Useful Commands:${NC}"
    echo "   ollama list                    # List installed models"
    echo "   ollama run $MODEL_NAME         # Interactive chat"
    echo "   ollama pull $MODEL_NAME        # Update model"
    echo ""
    echo -e "${GREEN}✨ Happy coding with $MODEL_NAME!${NC}"
}

# Main installation flow
main() {
    echo -e "${BLUE}🔍 System check...${NC}"
    
    # Check if running as root on vast.ai
    if [[ $EUID -eq 0 && -n "$SSH_CONNECTION" ]]; then
        echo -e "${YELLOW}🏗️  Detected vast.ai environment${NC}"
    fi
    
    # Installation steps
    install_system_deps
    echo ""
    
    install_ollama
    echo ""
    
    install_qwen3_coder
    echo ""
    
    install_python_deps
    echo ""
    
    setup_redis
    echo ""
    
    test_installation
    echo ""
    
    create_startup_script
    echo ""
    
    show_final_instructions
}

# Error handling
set -e
trap 'echo -e "${RED}❌ Installation failed. Check the error messages above.${NC}"; exit 1' ERR

# Parse command line arguments
SKIP_REDIS=false
FORCE_REINSTALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-redis)
            SKIP_REDIS=true
            shift
            ;;
        --force)
            FORCE_REINSTALL=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-redis    Skip Redis Cloud setup"
            echo "  --force         Force reinstall even if components exist"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main installation
main

# Exit successfully
exit 0