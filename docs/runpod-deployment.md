# RunPod Deployment Guide

This guide covers deploying the LLM proxy on RunPod with persistent storage and robust error handling.

## Quick Start

1. **Create RunPod Pod**: Use RunPod PyTorch template
2. **Use Startup Script**: Copy the startup command from this guide
3. **Configure Storage**: Attach persistent volume to `/datastore`
4. **Expose Port**: Configure port `8000` exposure
5. **Deploy**: Launch the pod

## Robust Startup Script

The following startup script resolves the common `curl: option --model: is unknown` error by:
- Explicitly managing PATH for pip-installed binaries
- Using absolute paths to ensure commands are found
- Adding comprehensive logging for troubleshooting
- Handling persistent storage configuration

```bash
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
```

## Deployment Steps

### 1. Destroy Failed Pod (if applicable)
- Go to **My Pods** page
- Click **Terminate (Trash Can icon)** on any failed pod

### 2. Deploy New Pod
- Select **RunPod PyTorch** template
- Configure the following settings:

#### Container Configuration
- **Start Command**: Paste the startup script above
- **Container Image**: Use default PyTorch image
- **Container Registry Credentials**: Leave as default

#### Storage Configuration
- **Persistent Volume**: Attach your persistent volume
- **Mount Path**: `/datastore`
- **Purpose**: Store Ollama models and cache data

#### Network Configuration
- **Exposed Ports**: `8000`
- **Protocol**: TCP
- **Purpose**: LiteLLM proxy HTTP endpoint

### 3. Launch Pod
- Click **Deploy** to launch the pod
- Monitor startup logs for progress

## Troubleshooting

### Common Issues

#### `curl: option --model: is unknown`
**Cause**: The `litellm` command isn't found in PATH after pip installation.

**Solution**: The robust startup script above resolves this by:
1. Explicitly adding `/root/.local/bin` to PATH
2. Using absolute path `/root/.local/bin/litellm` for execution
3. Verifying command accessibility before use

#### Model Download Failures
**Cause**: Network interruptions during large model downloads.

**Solution**: 
- Use persistent storage (automatically handled by script)
- RunPod's reliable network should minimize this issue
- Model persists across pod restarts once downloaded

#### Storage Issues
**Cause**: Ollama data not persisting across restarts.

**Solution**: The script automatically:
1. Moves `.ollama` to persistent storage at `/datastore/ollama`
2. Creates symbolic link from `/root/.ollama` to persistent location
3. Skips move operation if link already exists

### Verifying Deployment

Once deployed, verify the setup:

```bash
# Check if proxy is running
curl http://YOUR_POD_IP:8000/health

# Test model availability
curl http://YOUR_POD_IP:8000/v1/models

# Test completion
curl -X POST http://YOUR_POD_IP:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

## Integration with Claude CLI

Set these environment variables to use the RunPod endpoint:

```bash
export ANTHROPIC_BASE_URL="http://YOUR_POD_IP:8000"
export ANTHROPIC_MODEL="qwen3-coder:30b"
```

## Cost and Performance

### RunPod Advantages
- **Reliability**: Higher uptime than marketplace solutions
- **Persistent Storage**: Models persist across restarts
- **Predictable Pricing**: More stable than spot pricing
- **Better Network**: More reliable model downloads

### Typical Costs
- **RTX 4090**: ~$0.50-0.70/hour
- **H100**: ~$2.50-4.00/hour
- **Storage**: ~$0.10/GB/month for persistent volumes

### Performance
- **Qwen3-Coder 30B**: ~19GB model size
- **First Load**: 5-10 minutes (model download)
- **Subsequent Starts**: 1-2 minutes (from persistent storage)
- **Inference**: 1-3 seconds per query

## Advanced Configuration

### Custom Models
To use different models, modify the startup script:

```bash
# Replace qwen3-coder:30b with your preferred model
ollama pull your-model:tag
/root/.local/bin/litellm --model ollama/your-model:tag --host 0.0.0.0 --port 8000
```

### Resource Optimization
- **GPU Memory**: Ensure sufficient VRAM for your model
- **Storage**: Allocate at least 30GB for models and cache
- **CPU**: 4+ cores recommended for preprocessing

## Security Considerations

- **Network Access**: Only expose port 8000, keep other ports private
- **API Keys**: Not required for self-hosted setup
- **Model Access**: Restrict access to your pod's IP range if needed

## Next Steps

After successful deployment:
1. Test the endpoint with Claude CLI
2. Configure Redis caching for improved performance (optional)
3. Set up monitoring and alerting
4. Consider load balancing for production use

For support or issues, refer to the main repository documentation or create an issue.