# Instance Configuration Guide

Configuration details for vast.ai instances running qwen3-coder.

## Current Production Instances

### Primary qwen3-coder Instance
- **Instance ID**: 24632695
- **Connection**: `ssh8.vast.ai:32694`
- **GPU**: RTX 4090
- **Storage**: 201GB (50GB allocated)
- **Model**: qwen3-coder (30B MoE with 3.3B active parameters)
- **Status**: Production Ready
- **Purpose**: Primary qwen3-coder inference with Claude CLI integration

### Legacy Instance (Fallback)
- **Instance ID**: 24626192
- **Connection**: `ssh4.vast.ai:26192`
- **GPU**: RTX 4090
- **Storage**: 10GB
- **Model**: qwen2.5-coder:7b
- **Status**: Active (fallback)
- **Purpose**: Fallback for smaller models and compatibility

## Automatic Instance Selection

The `claude_start.sh` script automatically detects and connects to instances in this order:

1. **Local Ollama** (if available)
2. **Primary qwen3-coder instance** (`ssh8.vast.ai:32694`)
3. **Legacy instance fallback** (`ssh4.vast.ai:26192`)

### Connection Flow

```bash
# Priority 1: Local Ollama
if ollama list | grep -q "qwen.*coder"; then
    use localhost:8000
    
# Priority 2: qwen3-coder instance
elif ssh root@ssh8.vast.ai -p 32694 "curl -s localhost:8000/"; then
    create_tunnel localhost:8001 -> ssh8.vast.ai:32694:8000
    
# Priority 3: Legacy fallback
elif ssh root@ssh4.vast.ai -p 26192 "curl -s localhost:8000/"; then
    create_tunnel localhost:8001 -> ssh4.vast.ai:26192:8000
fi
```

## Instance Management

### Starting New Instance
```bash
# Create new instance with qwen3-coder setup
vastai create instance OFFER_ID \
  --image pytorch/pytorch:latest \
  --disk 50 \
  --ssh \
  --onstart-cmd "curl -fsSL https://raw.githubusercontent.com/jleechanorg/llm_selfhost/main/install.sh | bash && ollama pull qwen3-coder"
```

### Monitoring Instances
```bash
# Check all instances
vastai show instances

# Check specific instance
vastai show instances | grep INSTANCE_ID

# SSH into instance
vastai ssh INSTANCE_ID
```

### Cost Management
```bash
# Stop instance when not needed
vastai destroy instance INSTANCE_ID

# Check costs
vastai show instances --sum
```

## Model Configuration

### qwen3-coder Instance
- **Model Size**: ~18-30GB
- **VRAM Usage**: ~20GB
- **Context Window**: 256K tokens (up to 1M with extrapolation)
- **Performance**: ~50-100 tokens/second on RTX 4090
- **Specialization**: Advanced code generation and agentic tasks

### Installation Verification
```bash
# SSH into instance
ssh root@ssh8.vast.ai -p 32694

# Check model installation
ollama list

# Test model
echo "Write a Python hello world" | ollama run qwen3-coder

# Check API proxy
curl http://localhost:8000/health
```

## Integration with Claude CLI

### Environment Setup
```bash
# Automatically handled by claude_start.sh --qwen
export ANTHROPIC_BASE_URL="http://localhost:8001"
export ANTHROPIC_MODEL="qwen3-coder"
```

### Testing Integration
```bash
# Test the complete pipeline
./claude_start.sh --qwen

# Verify qwen3-coder is being used
claude --model "qwen3-coder" "What model are you?"
```

## Troubleshooting

### Instance Not Responding
```bash
# Check instance status
vastai show instances | grep INSTANCE_ID

# Restart if needed
vastai restart instance INSTANCE_ID

# Check logs
vastai ssh INSTANCE_ID "tail -f /tmp/ollama.log"
```

### SSH Connection Issues
```bash
# Test SSH connectivity
ssh -o ConnectTimeout=10 root@ssh8.vast.ai -p 32694 "echo 'Connected'"

# Kill existing tunnels
pkill -f "ssh.*8001.*vast.ai"

# Manual tunnel creation
ssh -N -L 8001:localhost:8000 root@ssh8.vast.ai -p 32694 &
```

### Model Issues
```bash
# Re-pull model if corrupted
ssh root@ssh8.vast.ai -p 32694 "ollama pull qwen3-coder"

# Check disk space
ssh root@ssh8.vast.ai -p 32694 "df -h"

# Restart API proxy
ssh root@ssh8.vast.ai -p 32694 "pkill python3 && cd llm_selfhost && python3 simple_api_proxy.py &"
```

## Performance Monitoring

### System Resources
```bash
# GPU utilization
ssh root@ssh8.vast.ai -p 32694 "nvidia-smi"

# Memory usage
ssh root@ssh8.vast.ai -p 32694 "free -h"

# API proxy performance
curl -s http://localhost:8001/health | jq
```

### Cost Tracking
- **qwen3-coder instance**: ~$0.27/hour
- **Legacy instance**: ~$0.25/hour
- **Recommended**: Use qwen3-coder for complex tasks, legacy for simple ones

## Security Notes

- All connections use SSH key authentication
- API proxy only binds to localhost (requires SSH tunnel)
- No public endpoints exposed
- Redis Cloud uses SSL/TLS encryption

## Backup and Recovery

### Data Backup
- Models are re-downloadable from Ollama registry
- Configuration stored in GitHub repositories
- Redis Cloud handles data persistence

### Instance Recovery
```bash
# If instance becomes corrupted, create new one
vastai create instance OFFER_ID \
  --image pytorch/pytorch:latest \
  --disk 50 \
  --ssh \
  --onstart-cmd "curl -fsSL https://raw.githubusercontent.com/jleechanorg/llm_selfhost/main/install.sh | bash && ollama pull qwen3-coder"

# Update claude_start.sh with new connection details
```

---

**Last Updated**: August 2025  
**Version**: 1.0.0 (qwen3-coder)  
**Maintainer**: WorldArchitect.AI Team