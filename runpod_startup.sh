#!/bin/bash
set -e
set -x

echo "--- RunPod LLM Proxy Startup Script ---"
echo "--- Starting Robust Setup Script ---"

# STEP 1: Install Ollama
echo "--- Installing Ollama ---"
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
sleep 5
echo "--- Ollama Service Started ---"

# STEP 2: Configure Persistent Storage
echo "--- Configuring Storage ---"
if [ ! -L /root/.ollama ]; then
  echo "Moving .ollama to persistent storage at /datastore/ollama"
  mv /root/.ollama /datastore/ollama
  ln -s /datastore/ollama /root/.ollama
else
  echo ".ollama is already linked. Skipping."
fi

# STEP 3: Install Python Packages
echo "--- Installing Python Packages ---"
pip install litellm
echo "--- LiteLLM installed ---"

# STEP 4: Ensure litellm is in the PATH
echo "--- Verifying command path ---"
if ! command -v litellm &> /dev/null
then
    echo "litellm command not found, adding ~/.local/bin to PATH."
    export PATH="$PATH:/root/.local/bin"
fi

# Verify litellm is now accessible
echo "--- Testing LiteLLM command ---"
/root/.local/bin/litellm --version || echo "Warning: LiteLLM version check failed"

# STEP 5: Pull the Model
echo "--- Pulling Qwen3 Coder Model ---"
ollama pull qwen3-coder:30b
echo "--- Model Pull Complete ---"

# STEP 6: Start the Proxy
echo "--- Starting LiteLLM Proxy ---"
echo "--- Using explicit path to ensure command is found ---"
/root/.local/bin/litellm --model ollama/qwen3-coder:30b --host 0.0.0.0 --port 8000