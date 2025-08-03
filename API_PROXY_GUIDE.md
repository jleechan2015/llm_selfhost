# API Proxy Integration Guide

Complete guide for integrating the LLM self-hosting system with Claude CLI via API proxy.

## Overview

This system allows Claude CLI to use your self-hosted qwen3-coder model by redirecting API calls through an Anthropic-compatible proxy server that includes Redis caching.

## Architecture

```
Claude CLI → ANTHROPIC_BASE_URL → SSH Tunnel → GPU Cloud API Proxy → Redis Cache → qwen3-coder
                                              ↗ vast.ai (marketplace)
                                              ↘ RunPod (reliable)
```

## Quick Start

### 1. Automated Setup (Recommended)

```bash
# SSH into your vast.ai instance
ssh -p PORT root@HOST

# Clone repository and run installer
git clone https://github.com/jleechanorg/llm_selfhost.git
cd llm_selfhost
./install.sh

# Start the system
./start_llm_selfhost.sh
```

**What this does**:
- ✅ Installs Ollama and qwen3-coder model
- ✅ Sets up Python dependencies
- ✅ Configures Redis Cloud connection
- ✅ Creates startup scripts
- ✅ Tests the installation

### 2. Manual Setup (Advanced)

```bash
# SSH into your vast.ai instance
ssh -p PORT root@HOST

# Clone/update repository
cd /root
git clone https://github.com/jleechanorg/llm_selfhost.git
cd llm_selfhost

# Install dependencies
pip3 install fastapi uvicorn redis requests

# Install Ollama and qwen3-coder model
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve &
sleep 5
ollama pull qwen3-coder

# Set environment variables
export REDIS_HOST="your-redis-host.redis-cloud.com"
export REDIS_PORT="your-port"
export REDIS_PASSWORD="your-password"

# Start API proxy server
python3 simple_api_proxy.py
```

### 3. RunPod Deployment (Recommended for Reliability)

RunPod offers more reliable infrastructure with persistent storage. Use the robust startup script to avoid common PATH issues:

```bash
# Deploy using RunPod PyTorch template
# Use this startup command to avoid PATH issues:

#!/bin/bash
set -e
set -x

echo "--- RunPod LLM Proxy Startup Script ---"

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
sleep 5

# Configure persistent storage
if [ ! -L /root/.ollama ]; then
  mv /root/.ollama /datastore/ollama
  ln -s /datastore/ollama /root/.ollama
fi

# Install LiteLLM with PATH handling
pip install litellm
export PATH="$PATH:/root/.local/bin"

# Pull model and start proxy
ollama pull qwen3-coder:30b
/root/.local/bin/litellm --model ollama/qwen3-coder:30b --host 0.0.0.0 --port 8000
```

**RunPod Advantages**:
- ✅ Higher uptime than marketplace solutions
- ✅ Persistent storage (models survive restarts) 
- ✅ More predictable pricing
- ✅ Better network reliability for downloads
- ✅ Resolves common PATH issues with robust startup script

See `docs/runpod-deployment.md` for complete deployment guide.

### 4. Configure Claude CLI Integration

Add to your `claude_start.sh` or equivalent:

```bash
# Set up SSH tunnel (vast.ai only exposes SSH ports)
ssh -N -L 8001:localhost:8000 -o StrictHostKeyChecking=no root@ssh4.vast.ai -p 26192 &

# Set environment variables to redirect Claude CLI
export ANTHROPIC_BASE_URL="http://localhost:8001"
export ANTHROPIC_MODEL="qwen3-coder"

# Launch Claude CLI
claude --model "qwen3-coder" "$@"
```

### 4. Test the Integration

```bash
# Test API proxy directly
curl http://localhost:8001/

# Test health endpoint
curl http://localhost:8001/health

# Test via Claude CLI
echo "Write a Python function to sort a list" | claude --model qwen3-coder
```

## qwen3-coder Model Features

### Enhanced Capabilities

**Latest Model**: qwen3-coder (30B MoE with 3.3B active parameters)

**Key Improvements over qwen2.5-coder**:
- **Better Code Generation**: Improved syntax, logic, and documentation
- **Longer Context**: 256K tokens natively (up to 1M with extrapolation)
- **Agentic Behavior**: Enhanced reasoning and problem-solving capabilities
- **Efficiency**: Only 3.3B parameters active per token despite 30B total

**Specialized Features**:
- Repository-scale understanding with long context support
- Advanced code completion and refactoring
- Better debugging and error analysis
- Improved documentation generation

### Performance Benchmarks

```
Context Window: 256K tokens (vs 32K in qwen2.5-coder)
Inference Speed: ~50-100 tokens/second on RTX 4090
Model Size: ~30GB download (vs ~7GB for qwen2.5-coder)
VRAM Usage: ~20GB (vs ~8GB for qwen2.5-coder)
```

## API Proxy Features

### Anthropic API Compatibility

The proxy implements these Anthropic API endpoints:

- `GET /` - Health check
- `GET /v1/models` - List available models
- `POST /v1/messages` - Create message completion (main endpoint)
- `GET /health` - Detailed component health check

### Redis Caching

- **Cache Key**: MD5 hash of normalized message content
- **TTL**: 24 hours (configurable)
- **Hit Detection**: Automatic cache hit/miss logging
- **Fallback**: Works without Redis if not configured

### Content Format Handling

**Fixed in Latest Version**: Handles both string and list content formats from Claude CLI

```python
def extract_text_content(content):
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        # Handle Anthropic's list format
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                text_parts.append(item.get('text', ''))
        return ' '.join(text_parts)
    return str(content)
```

### Error Handling

- **Ollama Errors**: Proper HTTP status codes and error messages
- **Redis Errors**: Graceful degradation, cache disabled on failure
- **Timeout Handling**: 30-second timeout for Ollama requests
- **Content Format Errors**: Automatic format detection and conversion

## Configuration Options

### Environment Variables

```bash
# Required for Redis caching
REDIS_HOST="redis-host.redis-cloud.com"
REDIS_PORT="6379"
REDIS_PASSWORD="your-password"

# Optional configuration
API_PORT="8000"           # Default: 8000
OLLAMA_HOST="localhost:11434"  # Default: localhost:11434
MODEL_NAME="qwen3-coder"  # Default: qwen3-coder
```

### Hardware Requirements

**Minimum (qwen3-coder)**:
- **GPU**: RTX 4090 (24GB VRAM) or equivalent
- **RAM**: 32GB system memory
- **Storage**: 50GB available (30GB for model + workspace)
- **Network**: Stable internet for model download

**Recommended**:
- **GPU**: RTX 4090 or H100
- **RAM**: 64GB system memory
- **Storage**: 100GB SSD
- **Network**: 1Gbps+ for production

### Redis Cloud Setup

1. Create account at https://redis.com/
2. Create database (free tier available)
3. Get connection details:
   - Host: `redis-xxxxx.region.redis-cloud.com`
   - Port: Usually 5-digit number
   - Password: Generated password

## Troubleshooting

### Common Issues

**Model Installation Problems**
```bash
# Check if qwen3-coder is installed
ollama list | grep qwen3-coder

# Re-install if missing
ollama pull qwen3-coder

# Check disk space (model is ~30GB)
df -h
```

**API Proxy Not Starting**
```bash
# Check dependencies
python3 -c "import fastapi, uvicorn, redis, requests"

# Check logs
tail -f simple_api_proxy.log

# Restart with debug info
python3 simple_api_proxy.py --debug
```

**SSH Tunnel Fails**
```bash
# Test SSH connection
ssh -o ConnectTimeout=5 root@ssh4.vast.ai -p 26192 "echo 'Connected'"

# Check if API proxy is running on vast.ai
ssh root@ssh4.vast.ai -p 26192 "curl -s http://localhost:8000/"

# Kill existing tunnels
pkill -f "ssh.*8001.*ssh4.vast.ai"
```

**Redis Connection Issues**
```bash
# Test Redis connection
python3 -c "
import redis
r = redis.Redis(host='your-host', port=your-port, password='your-password', ssl=True)
print(r.ping())
"
```

**Claude CLI Not Using Proxy**
```bash
# Verify environment variables
echo $ANTHROPIC_BASE_URL

# Test proxy directly
curl -X POST http://localhost:8001/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}],"model":"qwen3-coder"}'
```

**Memory Issues**
```bash
# Check GPU memory usage
nvidia-smi

# Check system memory
free -h

# Restart Ollama if memory leak
pkill ollama && ollama serve &
```

### Debug Commands

```bash
# Check API proxy status
curl -s http://localhost:8001/health | jq

# Monitor API proxy logs
tail -f simple_api_proxy.log

# Check SSH tunnel
ps aux | grep "ssh.*8001"

# Test qwen3-coder directly
ollama run qwen3-coder

# Test end-to-end pipeline
ANTHROPIC_BASE_URL=http://localhost:8001 claude --version
```

## Performance Optimization

### Cache Hit Ratio

Monitor cache performance:

```bash
# Check Redis stats
redis-cli -u "redis://user:pass@host:port" info stats

# Monitor cache hit ratio
grep "Cache hit" simple_api_proxy.log | wc -l
grep "Cache miss" simple_api_proxy.log | wc -l
```

Optimize for higher hit ratios:
- Use consistent message formatting
- Avoid unique timestamps in prompts
- Group similar queries together
- Use common coding patterns

### Model Performance

**qwen3-coder Optimization**:
- **First Load**: Model takes 2-3 minutes to load initially
- **Warm-up**: First few requests may be slower
- **Memory Management**: Restart periodically if memory usage grows
- **Context Length**: Longer contexts = slower inference

### Cost Optimization

- **Cache TTL**: Longer TTL = better cost savings, but potentially stale responses
- **Instance Type**: RTX 4090 offers best price/performance for qwen3-coder
- **Auto-scaling**: Stop instances during off-hours
- **Model Selection**: qwen3-coder vs smaller models based on use case

## Security Considerations

### Network Security

- API proxy only binds to localhost (requires SSH tunnel)
- Redis connection uses SSL/TLS
- No authentication required for localhost connections
- vast.ai instances isolated by default

### Credential Management

```bash
# Store Redis credentials securely
echo "export REDIS_PASSWORD='your-password'" >> ~/.bashrc
source ~/.bashrc

# Or use environment files
echo "REDIS_PASSWORD=your-password" > .env

# Use .env with install script
./install.sh  # Automatically prompts for Redis credentials
```

### Access Control

- SSH key authentication required for vast.ai
- No public HTTP endpoints exposed
- API proxy validates request format
- Redis access limited to configured hosts

## Integration Examples

### WorldArchitect.AI Integration

Complete integration in `claude_start.sh`:

```bash
# Auto-detect and setup qwen3-coder
if ssh root@ssh4.vast.ai -p 26192 "curl -s http://localhost:8000/ > /dev/null" 2>/dev/null; then
    # Setup SSH tunnel
    ssh -N -L 8001:localhost:8000 root@ssh4.vast.ai -p 26192 &
    
    # Configure environment
    export ANTHROPIC_BASE_URL="http://localhost:8001"
    export ANTHROPIC_MODEL="qwen3-coder"
    
    # Launch Claude CLI
    claude --model "qwen3-coder" "$@"
fi
```

### Custom Applications

```python
import requests
import os

# Use the same environment variable
api_base = os.getenv('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')

response = requests.post(f"{api_base}/v1/messages", json={
    "model": "qwen3-coder",
    "messages": [{"role": "user", "content": "Write a Python function to calculate fibonacci"}]
})

print(response.json())
```

### Batch Processing

```python
import requests
import json

api_base = "http://localhost:8001"

# Batch process multiple coding tasks
tasks = [
    "Write a Python class for a binary tree",
    "Create a REST API endpoint for user authentication", 
    "Implement a caching decorator with TTL"
]

for task in tasks:
    response = requests.post(f"{api_base}/v1/messages", json={
        "model": "qwen3-coder",
        "messages": [{"role": "user", "content": task}]
    })
    
    result = response.json()
    print(f"Task: {task}")
    print(f"Response: {result.get('content', 'Error')[:100]}...")
    print("---")
```

## Cost Analysis

### Running Costs (qwen3-coder)

```
API Proxy Server: ~0.1% CPU usage (negligible cost)
Redis Cloud: $0-50/month (depending on cache size)
vast.ai Instance (RTX 4090): $0.40-0.60/hour
Bandwidth: $0.01-0.05/GB

Total: ~$300-500/month for production workload
Savings vs Cloud: 70-85% cost reduction
```

### ROI Calculation

With 70% cache hit ratio using qwen3-coder:
- Cache hits: <1ms response time, ~$0.0001/query
- Cache misses: 4-10s response time, ~$0.015/query  
- Average cost: ~$0.0045/query vs $0.025 on cloud providers

**Result**: ~82% cost savings with superior model capabilities

### Comparison vs Alternatives

```
GPT-4 (OpenAI): $0.03-0.06/1K tokens
Claude Sonnet (Anthropic): $0.015-0.075/1K tokens
qwen3-coder (Self-hosted): $0.002-0.008/1K tokens

Cost Advantage: 3-30x cheaper than cloud providers
Quality: Competitive for code generation tasks
Context: 256K vs 32K-128K for most cloud models
```

## Advanced Features

### Model Switching

```bash
# Switch between models without restart
export ANTHROPIC_MODEL="qwen3-coder"      # Latest model
export ANTHROPIC_MODEL="qwen2.5-coder"    # Legacy support
export ANTHROPIC_MODEL="qwen2:7b"         # Faster inference
```

### Cache Management

```bash
# Clear cache for fresh responses
redis-cli -u "redis://user:pass@host:port" FLUSHDB

# Monitor cache size
redis-cli -u "redis://user:pass@host:port" INFO memory

# Set custom TTL
export CACHE_TTL=86400  # 24 hours (default)
```

### Load Balancing

```bash
# Multiple API proxy instances
python3 simple_api_proxy.py --port 8000 &
python3 simple_api_proxy.py --port 8001 &
python3 simple_api_proxy.py --port 8002 &

# Round-robin load balancing
export ANTHROPIC_BASE_URL="http://localhost:800{0,1,2}"
```

## Support

### Resources

- **GitHub Issues**: https://github.com/jleechanorg/llm_selfhost/issues
- **Main Documentation**: README.md
- **Installation Script**: ./install.sh
- **Integration Status**: INTEGRATION_STATUS.md

### Common Solutions

- **Port conflicts**: Use different local ports (8002, 8003, etc.)
- **Memory issues**: Restart API proxy periodically (`pkill python3 && ./start_llm_selfhost.sh`)
- **Model loading**: Wait 3-5 minutes for first request after restart
- **Tunnel issues**: Kill existing SSH tunnels before creating new ones

### Professional Support

- **Implementation**: Custom deployment assistance
- **Optimization**: Performance tuning for specific workloads
- **Scaling**: Multi-instance and load balancing setup
- **Enterprise**: SLA support and monitoring

---

**Last Updated**: August 2025  
**Version**: 2.0.0 (qwen3-coder)  
**Maintainer**: WorldArchitect.AI Team