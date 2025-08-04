#!/usr/bin/env bash
# Enhanced Vast.ai Qwen3-Coder Startup Script
# Automatically configures and starts the Qwen3-Coder API proxy with reliability improvements

set -e # Exit immediately if a command fails

echo "🚀 Starting Enhanced Vast.ai Qwen3-Coder Setup"
echo "==============================================="

echo ">> 1. Installing dependencies..."
pip install ollama redis fastapi uvicorn requests

echo ">> 2. Installing and starting Ollama..."
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
OLLAMA_PID=$!
echo "✅ Ollama started with PID: $OLLAMA_PID"

echo ">> 3. Waiting for Ollama to be ready..."
for i in {1..30}; do
    if curl -s localhost:11434/api/tags > /dev/null; then
        echo "✅ Ollama is ready after ${i} attempts"
        break
    fi
    echo "⏳ Waiting for Ollama... ($i/30)"
    sleep 2
done

# Verify Ollama is actually responding
if ! curl -s localhost:11434/api/tags > /dev/null; then
    echo "❌ Ollama failed to start properly"
    exit 1
fi

echo ">> 4. Pulling Qwen3-Coder model..."
echo "📦 Downloading ~18GB model, this may take several minutes..."
ollama pull qwen3-coder

echo ">> 5. Verifying model is available..."
ollama list
echo "🧪 Testing model with simple query..."
ollama run qwen3-coder "Hello, I am ready!" || echo "⚠️ Model test returned non-zero, but continuing..."

echo ">> 6. Cloning application repository..."
if [ ! -d "/app" ]; then
    if [ -z "$GIT_REPO" ]; then
        echo "⚠️ GIT_REPO not set, skipping clone"
    else
        git clone "$GIT_REPO" /app
        echo "✅ Repository cloned to /app"
    fi
else
    echo "✅ /app directory already exists"
fi
cd /app 2>/dev/null || echo "⚠️ /app not found, staying in current directory"

echo ">> 7. Testing Ollama API directly..."
echo "🔍 Verifying API endpoint works before starting proxy..."
TEST_RESULT=$(curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-coder","prompt":"Test","stream":false}' \
  --max-time 30 --silent --write-out "%{http_code}")

if [[ "$TEST_RESULT" == *"200"* ]]; then
    echo "✅ Ollama API test successful"
else
    echo "⚠️ Ollama API test returned: $TEST_RESULT"
    echo "Continuing anyway..."
fi

echo ">> 8. Launching API proxy..."
echo "🌐 Starting Anthropic-compatible API proxy on port 8000"
echo "🔗 Endpoints:"
echo "   Health: http://localhost:8000/health"
echo "   Models: http://localhost:8000/v1/models"
echo "   Chat: http://localhost:8000/v1/messages"
echo "==============================================="

# Launch the API proxy that bridges Anthropic API to Ollama
python3 simple_api_proxy.py