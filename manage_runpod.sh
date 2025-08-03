#!/bin/bash
# RunPod Management Script
# Wrapper for managing RunPod instances with proper Python environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.runpod_venv"

# Pod configuration - UPDATE THESE VALUES
VOLUME_ID="YOUR_VOLUME_ID_HERE"
POD_NAME="Claude-Qwen3-Coder"
GPU_TYPE="NVIDIA GeForce RTX 4090"

echo -e "${BLUE}🚀 RunPod Management Script${NC}"
echo "================================"

# Check if API key is set
check_api_key() {
    if [ -z "$RUNPOD_API_KEY" ]; then
        echo -e "${RED}❌ RUNPOD_API_KEY not set${NC}"
        echo "Please set your RunPod API key:"
        echo "  export RUNPOD_API_KEY='your-api-key-here'"
        echo ""
        echo "Get your API key from: https://www.runpod.io/console/user/settings"
        return 1
    else
        echo -e "${GREEN}✅ API key configured${NC}"
        return 0
    fi
}

# Setup Python environment
setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${BLUE}Setting up Python virtual environment...${NC}"
        python3 -m venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        pip install --upgrade pip
        pip install runpod
        echo -e "${GREEN}✅ Virtual environment created${NC}"
    else
        echo -e "${GREEN}✅ Using existing virtual environment${NC}"
    fi
    source "$VENV_DIR/bin/activate"
}

# Create pod using RunPod CLI
create_pod() {
    echo -e "${BLUE}🚀 Creating RunPod instance...${NC}"
    
    if [ "$VOLUME_ID" = "YOUR_VOLUME_ID_HERE" ]; then
        echo -e "${RED}❌ Please update VOLUME_ID in this script${NC}"
        echo "Get your volume ID from: https://www.runpod.io/console/volumes"
        return 1
    fi
    
    # Create pod with all necessary configuration
    runpod create pod \
        --name "$POD_NAME" \
        --image-name "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04" \
        --gpu-type "$GPU_TYPE" \
        --container-disk 40 \
        --volume-mount-path "/datastore" \
        --ports "8000/tcp" \
        --volume-id "$VOLUME_ID" \
        --start-jupyter false \
        --start-ssh false
    
    echo -e "${GREEN}✅ Pod creation command sent${NC}"
    echo "Monitor progress at: https://www.runpod.io/console/pods"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Wait for pod to be 'Running' (2-3 minutes)"
    echo "2. Run the startup command in the pod terminal"
    echo "3. Use 'list' command to get connection details"
}

# List all pods
list_pods() {
    echo -e "${BLUE}📋 Listing RunPod instances...${NC}"
    runpod get pods
}

# Get specific pod details
get_pod() {
    if [ -z "$1" ]; then
        echo -e "${RED}❌ Pod ID required${NC}"
        echo "Usage: $0 get <pod_id>"
        return 1
    fi
    
    echo -e "${BLUE}🔍 Getting pod details: $1${NC}"
    runpod get pod "$1"
}

# Terminate pod
terminate_pod() {
    if [ -z "$1" ]; then
        echo -e "${RED}❌ Pod ID required${NC}"
        echo "Usage: $0 terminate <pod_id>"
        return 1
    fi
    
    echo -e "${YELLOW}🛑 Terminating pod: $1${NC}"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        runpod remove pod "$1"
        echo -e "${GREEN}✅ Pod termination command sent${NC}"
    else
        echo "Cancelled."
    fi
}

# Generate startup command for manual execution
show_startup_command() {
    echo -e "${BLUE}📋 RunPod Startup Command${NC}"
    echo "Copy and paste this into your RunPod terminal:"
    echo ""
    echo "----------------------------------------"
    cat << 'EOF'
#!/bin/bash
set -e
set -x

echo "=== RunPod Startup Script for Claude CLI Integration ==="
echo "Starting at: $(date)"

# Install Ollama
echo "Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server in background
echo "Starting Ollama server..."
ollama serve &
sleep 10

# Setup persistent storage for Ollama models
echo "Setting up persistent storage..."
if [ ! -L /root/.ollama ]; then
    if [ -d /root/.ollama ]; then
        echo "Moving existing Ollama data to persistent storage..."
        mv /root/.ollama /datastore/ollama
    else
        echo "Creating Ollama directory in persistent storage..."
        mkdir -p /datastore/ollama
    fi
    ln -s /datastore/ollama /root/.ollama
    echo "Linked /root/.ollama to /datastore/ollama"
fi

# Install LiteLLM
echo "Installing LiteLLM..."
pip install litellm

# Ensure LiteLLM is in PATH
if ! command -v litellm &> /dev/null; then
    echo "Adding ~/.local/bin to PATH..."
    export PATH="$PATH:/root/.local/bin"
fi

# Pull the Qwen model (check if already exists to save time)
echo "Checking for Qwen model..."
if ! ollama list | grep -q "qwen3-coder:30b"; then
    echo "Pulling qwen3-coder:30b model (this may take 10-15 minutes)..."
    ollama pull qwen3-coder:30b
else
    echo "qwen3-coder:30b model already exists, skipping download"
fi

# Test Ollama is working
echo "Testing Ollama..."
ollama list

# Start LiteLLM proxy
echo "Starting LiteLLM proxy on port 8000..."
echo "Startup completed at: $(date)"
echo "=== LiteLLM Proxy Starting ==="
/root/.local/bin/litellm --model ollama/qwen3-coder:30b --host 0.0.0.0 --port 8000
EOF
    echo "----------------------------------------"
    echo ""
    echo -e "${YELLOW}This will take 10-15 minutes to complete${NC}"
    echo "The model download is the longest part."
}

# Generate connection script
create_connection_script() {
    cat << 'EOF' > connect_claude_runpod.sh
#!/bin/bash
# Claude CLI RunPod Connection Script

if [ -z "$1" ]; then
    echo "Usage: $0 <pod_ip:port>"
    echo "Example: $0 38.80.152.248:30864"
    echo ""
    echo "Get the IP:port from 'runpod get pods' or the RunPod console"
    exit 1
fi

PUBLIC_URL="http://$1"

echo "🔗 Connecting Claude CLI to RunPod..."
echo "Endpoint: $PUBLIC_URL"

# Set environment variables
export ANTHROPIC_BASE_URL="$PUBLIC_URL"
export ANTHROPIC_MODEL="qwen3-coder:30b"

echo "✅ Environment configured:"
echo "  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL"
echo "  ANTHROPIC_MODEL=$ANTHROPIC_MODEL"
echo ""
echo "🤖 You can now use Claude CLI normally:"
echo "  claude 'Write a Python function'"
EOF
    
    chmod +x connect_claude_runpod.sh
    echo -e "${GREEN}✅ Created connect_claude_runpod.sh${NC}"
    echo "Usage: ./connect_claude_runpod.sh <ip:port>"
}

# Main function
main() {
    case "${1:-help}" in
        "create")
            check_api_key && setup_venv && create_pod
            ;;
        "list")
            check_api_key && setup_venv && list_pods
            ;;
        "get")
            check_api_key && setup_venv && get_pod "$2"
            ;;
        "terminate")
            check_api_key && setup_venv && terminate_pod "$2"
            ;;
        "startup")
            show_startup_command
            ;;
        "connect")
            create_connection_script
            ;;
        "help"|*)
            echo "RunPod Management Script"
            echo ""
            echo "Usage:"
            echo "  $0 create              # Create new pod"
            echo "  $0 list                # List all pods"
            echo "  $0 get <pod_id>        # Get pod details"
            echo "  $0 terminate <pod_id>  # Terminate pod"
            echo "  $0 startup             # Show startup command"
            echo "  $0 connect             # Create connection script"
            echo "  $0 help                # Show this help"
            echo ""
            echo "Environment variables:"
            echo "  RUNPOD_API_KEY - Your RunPod API key (required)"
            echo ""
            echo "Configuration:"
            echo "  Edit VOLUME_ID in this script with your volume ID"
            echo "  Get it from: https://www.runpod.io/console/volumes"
            echo ""
            echo "Workflow:"
            echo "  1. Update VOLUME_ID in this script"
            echo "  2. export RUNPOD_API_KEY='your-key'"
            echo "  3. $0 create"
            echo "  4. $0 startup  # Get command to run in pod"
            echo "  5. $0 list     # Get connection details"
            echo "  6. $0 connect  # Create connection script"
            ;;
    esac
}

main "$@"