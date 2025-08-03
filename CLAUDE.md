# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Core Development
- **Install dependencies**: `pip install -r requirements.txt` 
- **Start main API proxy**: `python3 simple_api_proxy.py`
- **Start alternative proxy**: `python3 api_proxy.py` 
- **Run LLM cache tests**: `python3 llm_cache_app.py`
- **Automated setup**: `./install.sh` (full system installation)
- **Quick startup**: `./startup_llm.sh` (for vast.ai environments)
- **RunPod deployment**: `./runpod_startup.sh` (for RunPod environments)

### Testing and Health Checks
- **Health check**: `curl http://localhost:8000/health`
- **API test**: `curl -X POST http://localhost:8000/v1/messages -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"Hello"}]}'`
- **List models**: `curl http://localhost:8000/v1/models`
- **Check Ollama status**: `ollama list`

### Model Management
- **Pull qwen3-coder**: `ollama pull qwen3-coder`
- **Test model directly**: `ollama run qwen3-coder`
- **Check available models**: `ollama list`

## Architecture Overview

This is a **distributed LLM caching system** that provides cost-effective LLM inference using vast.ai GPU instances with Redis Cloud caching.

### Core Components

1. **API Proxies** (2 implementations):
   - `simple_api_proxy.py`: Lightweight proxy with basic Redis caching
   - `api_proxy.py`: Advanced proxy with ModelCache integration
   - Both provide Anthropic API-compatible endpoints for Claude CLI integration

2. **LLM Backend**:
   - Ollama server running qwen3-coder model (30B MoE, 3.3B active parameters)
   - Default model: `qwen3-coder` (can fall back to `qwen2.5-coder:7b`)

3. **Caching Layer**:
   - Redis Cloud Enterprise for distributed caching
   - 24-hour TTL, MD5-based cache keys
   - Semantic similarity caching in advanced proxy
   - 70-90% typical cache hit ratio

4. **Infrastructure**:
   - Designed for GPU cloud instances (vast.ai, RunPod)
   - RTX 4090/H100 support with persistent storage
   - SSH tunnel support for remote access
   - Health monitoring and graceful fallbacks

### Request Flow

```
Claude CLI → API Proxy → Redis Cache Check → [Cache Hit: Return | Cache Miss: Ollama] → Cache Store → Response
```

### Key Files

- `simple_api_proxy.py`: Main production proxy (recommended)
- `api_proxy.py`: Advanced proxy with ModelCache 
- `main.py`: Legacy entry point
- `llm_cache_app.py`: Standalone cache testing app
- `install.sh`: Comprehensive installation script
- `startup_llm.sh`: Vast.ai deployment script
- `runpod_startup.sh`: RunPod deployment script with robust PATH handling

### Environment Variables

Required for Redis caching:
- `REDIS_HOST`: Redis Cloud host
- `REDIS_PORT`: Redis Cloud port  
- `REDIS_PASSWORD`: Redis Cloud password

Optional:
- `API_PORT`: Server port (default: 8000)
- `OLLAMA_HOST`: Ollama host (default: localhost:11434)

### Claude CLI Integration

The proxy servers expose Anthropic API-compatible endpoints:
- `GET /v1/models`: List available models
- `POST /v1/messages`: Create message completion
- `GET /health`: System health check

Set these environment variables for Claude CLI:
```bash
export ANTHROPIC_BASE_URL="http://localhost:8000"
export ANTHROPIC_MODEL="qwen3-coder"
```

### Cost Model

- **Vast.ai RTX 4090**: ~$0.50/hour (marketplace pricing)
- **RunPod RTX 4090**: ~$0.50-0.70/hour (more reliable)
- **Cache hits**: ~$0.0001 per query  
- **Cache misses**: ~$0.001-0.01 per query
- **Target savings**: 81% vs cloud providers

### Deployment Patterns

1. **Local Development**: Run `python3 simple_api_proxy.py`
2. **Vast.ai Remote**: Use `startup_llm.sh` for automated deployment
3. **RunPod Remote**: Use `runpod_startup.sh` for reliable deployment with persistent storage
4. **Production**: Use `install.sh` for full system setup with monitoring

The system gracefully handles missing Redis credentials and can operate without caching for development.