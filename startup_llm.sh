#\!/usr/bin/env bash
# Vast.ai Qwen3-Coder Startup Script
# Automatically configures and starts the Qwen3-Coder API proxy

set -e # Exit immediately if a command fails

echo ">> 1. Installing dependencies..."
pip install ollama redis fastapi uvicorn requests

echo ">> 2. Setting up and starting Ollama..."
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
sleep 5 # Give the server a moment to start up

echo ">> 3. Pulling the LLM model..."
# Using qwen3-coder as specified (30B model, 19GB)
ollama pull qwen3-coder

echo ">> 4. Cloning your application repository..."
# The GIT_REPO environment variable is passed in by the 'vastai create' command.
if [ \! -d "/app" ]; then
    git clone "$GIT_REPO" /app
fi
cd /app

echo ">> 5. Launching the API proxy..."
# Launch the API proxy that bridges Anthropic API to Ollama
python3 simple_api_proxy.py
EOF < /dev/null
