# Vast.ai + Qwen3-Coder Integration Plan

## Current Situation Analysis

### What We Have ✅
- **Working SSH tunnels** to vast.ai instance (port 12806)
- **Simple API proxy** (`simple_api_proxy.py`) that's Redis-cache enabled
- **Startup script** (`startup_llm.sh`) configured for qwen3-coder
- **Health endpoints** responding correctly
- **Previous success** - we know the system can work

### What's Broken ❌
- **Ollama 404 errors** - proxy can't reach Ollama on vast.ai instance
- **Model loading issues** - qwen3-coder might not be properly loaded
- **Service startup coordination** - timing issues between Ollama and proxy

## Root Cause Analysis

Based on `VAST_AI_STATUS.md`, the issue is:
```
{"detail": "Ollama generation failed: Ollama API error: 404"}
```

This means:
1. Ollama service is not running on vast.ai instance
2. OR qwen3-coder model isn't loaded
3. OR there's a timing issue in the startup sequence

## Implementation Plan

### Phase 1: Diagnostic & Verification
```bash
# 1.1 Check vast.ai instance status
ssh -p 12806 root@ssh7.vast.ai "ps aux | grep ollama"
ssh -p 12806 root@ssh7.vast.ai "curl localhost:11434/api/tags"

# 1.2 Verify model availability
ssh -p 12806 root@ssh7.vast.ai "ollama list"
ssh -p 12806 root@ssh7.vast.ai "df -h"  # Check disk space

# 1.3 Test direct Ollama access
ssh -p 12806 root@ssh7.vast.ai "ollama run qwen3-coder 'Hello, world!'"
```

### Phase 2: Service Recovery
```bash
# 2.1 Restart Ollama service
ssh -p 12806 root@ssh7.vast.ai "pkill ollama; ollama serve &"

# 2.2 Re-pull model if needed
ssh -p 12806 root@ssh7.vast.ai "ollama pull qwen3-coder"

# 2.3 Verify model loading
ssh -p 12806 root@ssh7.vast.ai "ollama run qwen3-coder 'Test message'"
```

### Phase 3: Startup Script Enhancement

Update `startup_llm.sh` with better error handling and verification:

```bash
#!/usr/bin/env bash
# Enhanced Vast.ai Qwen3-Coder Startup Script
set -e

echo ">> 1. Installing dependencies..."
pip install ollama redis fastapi uvicorn requests

echo ">> 2. Installing and starting Ollama..."
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo ">> 3. Waiting for Ollama to start..."
for i in {1..30}; do
    if curl -s localhost:11434/api/tags > /dev/null; then
        echo "✅ Ollama is ready"
        break
    fi
    echo "Waiting for Ollama... ($i/30)"
    sleep 2
done

echo ">> 4. Pulling Qwen3-Coder model..."
ollama pull qwen3-coder

echo ">> 5. Verifying model is available..."
ollama list
ollama run qwen3-coder "Hello, I am ready!" || echo "❌ Model test failed"

echo ">> 6. Cloning application repository..."
if [ ! -d "/app" ]; then
    git clone "$GIT_REPO" /app
fi
cd /app

echo ">> 7. Testing Ollama API directly..."
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-coder","prompt":"Test","stream":false}' || echo "❌ API test failed"

echo ">> 8. Launching API proxy..."
python3 simple_api_proxy.py
```

### Phase 4: Local Testing Pipeline

```bash
# 4.1 Test SSH tunnels
ssh -N -L 8000:localhost:8000 -p 12806 root@ssh7.vast.ai &
ssh -N -L 11434:localhost:11434 -p 12806 root@ssh7.vast.ai &

# 4.2 Test local Ollama access
curl http://localhost:11434/api/tags

# 4.3 Test proxy health
curl http://localhost:8000/health

# 4.4 Test full pipeline
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Write a simple hello function"}]}'

# 4.5 Test Claude CLI integration
export ANTHROPIC_BASE_URL="http://localhost:8000"
export ANTHROPIC_MODEL="qwen3-coder"
claude "Write a fibonacci function"
```

### Phase 5: Monitoring & Optimization

```bash
# 5.1 Setup monitoring script
cat > monitor_vast.sh << 'EOF'
#!/bin/bash
while true; do
    echo "=== $(date) ==="
    echo "Ollama status:"
    curl -s localhost:11434/api/tags | jq '.models[]? | .name' || echo "❌ Ollama down"
    echo "Proxy status:"
    curl -s localhost:8000/health | jq '.status' || echo "❌ Proxy down"
    echo "Memory usage:"
    free -h
    echo "Disk usage:"
    df -h /
    sleep 30
done
EOF

# 5.2 Log aggregation
tail -f /var/log/ollama.log &
tail -f /app/proxy.log &
```

## Success Criteria

### ✅ System is working when:
1. `curl localhost:11434/api/tags` returns model list including qwen3-coder
2. `curl localhost:8000/health` shows all components healthy
3. `curl -X POST localhost:8000/v1/messages` returns valid responses
4. Claude CLI commands generate actual code

### 🎯 Performance targets:
- **Cache hit ratio**: >70%
- **Response time**: <10s for cache misses, <1s for cache hits
- **Model loading**: qwen3-coder ready within 2 minutes
- **System uptime**: >95% during active usage

## Risk Mitigation

### Fallback Models
If qwen3-coder (19GB) fails:
1. Try `qwen2.5-coder:7b` (4.7GB) 
2. Try `qwen2.5-coder:1.5b` (1.6GB)
3. Use `llama3.1:8b` as last resort

### Disk Space Management
```bash
# Monitor disk usage - qwen3-coder needs ~19GB
df -h
docker system prune -f  # Clean up if needed
```

### Memory Management
```bash
# qwen3-coder requires ~12GB RAM during inference
free -h
# Kill non-essential processes if needed
```

## Expected Timeline

- **Phase 1 (Diagnostics)**: 15 minutes
- **Phase 2 (Service Recovery)**: 15 minutes  
- **Phase 3 (Script Enhancement)**: 30 minutes
- **Phase 4 (Testing)**: 30 minutes
- **Phase 5 (Monitoring)**: 15 minutes

**Total**: ~1.5 hours to full working system

## Files to Modify/Create

1. **Update** `startup_llm.sh` with enhanced error handling
2. **Create** `scripts/diagnose_vast.sh` for debugging
3. **Create** `scripts/monitor_vast.sh` for ongoing monitoring
4. **Update** `simple_api_proxy.py` with better Ollama error handling (if needed)

## Next Immediate Steps

1. **SSH into vast.ai instance** and diagnose current state
2. **Restart Ollama service** and verify model loading  
3. **Test direct model inference** before testing through proxy
4. **Update startup script** with enhanced reliability
5. **Test full pipeline** end-to-end

This plan should get qwen3-coder working reliably on vast.ai with proper error handling and monitoring.