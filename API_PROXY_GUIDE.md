# API Proxy Integration Guide

Complete guide for integrating the LLM self-hosting system with Claude CLI via API proxy.

## Overview

This system allows Claude CLI to use your self-hosted qwen model by redirecting API calls through an Anthropic-compatible proxy server that includes Redis caching.

## Architecture

```
Claude CLI → ANTHROPIC_BASE_URL → SSH Tunnel → vast.ai API Proxy → Redis Cache → qwen2.5-coder:7b
```

## Quick Start

### 1. Deploy API Proxy on vast.ai

```bash
# SSH into your vast.ai instance
ssh -p PORT root@HOST

# Clone/update repository
cd /root
git clone https://github.com/jleechanorg/llm_selfhost.git
cd llm_selfhost

# Install dependencies
pip3 install fastapi uvicorn redis requests

# Set environment variables
export REDIS_HOST="your-redis-host.redis-cloud.com"
export REDIS_PORT="your-port"
export REDIS_PASSWORD="your-password"

# Start API proxy server
python3 simple_api_proxy.py
```

### 2. Configure Claude CLI Integration

Add to your `claude_start.sh` or equivalent:

```bash
# Set up SSH tunnel (vast.ai only exposes SSH ports)
ssh -N -L 8001:localhost:8000 -o StrictHostKeyChecking=no root@ssh4.vast.ai -p 26192 &

# Set environment variables to redirect Claude CLI
export ANTHROPIC_BASE_URL="http://localhost:8001"
export ANTHROPIC_MODEL="qwen2.5-coder:7b"

# Launch Claude CLI
claude --model "qwen2.5-coder:7b" "$@"
```

### 3. Test the Integration

```bash
# Test API proxy directly
curl http://localhost:8001/

# Test health endpoint
curl http://localhost:8001/health

# Test via Claude CLI
echo "Write a Python function to sort a list" | claude --model qwen2.5-coder:7b
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

### Error Handling

- **Ollama Errors**: Proper HTTP status codes and error messages
- **Redis Errors**: Graceful degradation, cache disabled on failure
- **Timeout Handling**: 30-second timeout for Ollama requests

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
```

### Redis Cloud Setup

1. Create account at https://redis.com/
2. Create database (free tier available)
3. Get connection details:
   - Host: `redis-xxxxx.region.redis-cloud.com`
   - Port: Usually 5-digit number
   - Password: Generated password

## Troubleshooting

### Common Issues

**API Proxy Not Starting**
```bash
# Check dependencies
python3 -c "import fastapi, uvicorn, redis, requests"

# Check logs
tail -f simple_api_proxy.log
```

**SSH Tunnel Fails**
```bash
# Test SSH connection
ssh -o ConnectTimeout=5 root@ssh4.vast.ai -p 26192 "echo 'Connected'"

# Check if API proxy is running on vast.ai
ssh root@ssh4.vast.ai -p 26192 "curl -s http://localhost:8000/"
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
  -d '{"messages":[{"role":"user","content":"Hello"}],"model":"qwen2.5-coder:7b"}'
```

### Debug Commands

```bash
# Check API proxy status
curl -s http://localhost:8001/health | jq

# Monitor API proxy logs
tail -f simple_api_proxy.log

# Check SSH tunnel
ps aux | grep "ssh.*8001"

# Test end-to-end pipeline
ANTHROPIC_BASE_URL=http://localhost:8001 claude --version
```

## Performance Optimization

### Cache Hit Ratio

Monitor cache performance:

```bash
# Check Redis stats
redis-cli -u "redis://user:pass@host:port" info stats
```

Optimize for higher hit ratios:
- Use consistent message formatting
- Avoid unique timestamps in prompts
- Group similar queries together

### Cost Optimization

- **Cache TTL**: Longer TTL = better cost savings, but stale responses
- **Instance Type**: RTX 4090 offers best price/performance
- **Auto-scaling**: Stop instances during off-hours

## Security Considerations

### Network Security

- API proxy only binds to localhost (requires SSH tunnel)
- Redis connection uses SSL/TLS
- No authentication required for localhost connections

### Credential Management

```bash
# Store Redis credentials securely
echo "export REDIS_PASSWORD='your-password'" >> ~/.bashrc
source ~/.bashrc

# Or use environment files
echo "REDIS_PASSWORD=your-password" > .env
```

### Access Control

- vast.ai instances are isolated by default
- SSH key authentication required
- No public HTTP endpoints exposed

## Integration Examples

### WorldArchitect.AI Integration

Complete integration in `claude_start.sh`:

```bash
# Auto-detect and setup
if ssh root@ssh4.vast.ai -p 26192 "curl -s http://localhost:8000/ > /dev/null" 2>/dev/null; then
    # Setup SSH tunnel
    ssh -N -L 8001:localhost:8000 root@ssh4.vast.ai -p 26192 &
    
    # Configure environment
    export ANTHROPIC_BASE_URL="http://localhost:8001"
    
    # Launch Claude CLI
    claude --model "qwen2.5-coder:7b" "$@"
fi
```

### Custom Applications

```python
import requests
import os

# Use the same environment variable
api_base = os.getenv('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')

response = requests.post(f"{api_base}/v1/messages", json={
    "model": "qwen2.5-coder:7b",
    "messages": [{"role": "user", "content": "Hello"}]
})
```

## Cost Analysis

### Running Costs

```
API Proxy Server: ~0.1% CPU usage (negligible cost)
Redis Cloud: $0-50/month (depending on cache size)
vast.ai Instance: $0.25-1.00/hour (model dependent)

Total: ~$200-800/month for production workload
Savings vs Cloud: 70-90% cost reduction
```

### ROI Calculation

With 70% cache hit ratio:
- Cache hits: <1ms response time, ~$0.0001/query
- Cache misses: 3-8s response time, ~$0.01/query
- Average cost: ~$0.003/query vs $0.015 on cloud providers

**Result**: ~80% cost savings with better performance

## Support

### Resources

- **GitHub Issues**: https://github.com/jleechanorg/llm_selfhost/issues
- **Main Documentation**: README.md
- **Architecture Details**: docs/ directory

### Common Solutions

- **Port conflicts**: Use different local ports (8002, 8003, etc.)
- **Memory issues**: Restart API proxy periodically
- **Model loading**: Wait 2-3 minutes for first request after restart

---

**Last Updated**: August 2025  
**Version**: 1.0.0  
**Maintainer**: WorldArchitect.AI Team