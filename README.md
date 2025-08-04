# Claude Code CLI Proxy

## Use Claude Code CLI with your own infrastructure instead of Anthropic's servers

This project provides proxies that let you use Claude Code CLI with:
- 🚀 **Vast.ai GPU instances** running Qwen models
- 🧠 **Cerebras Cloud API** 
- 🏠 **Local Ollama** setup

## Quick Start

**One-command installation:**

```bash
# Download installer
curl -fsSL -o install-claude-proxy.sh \
  https://raw.githubusercontent.com/jleechanorg/claude_llm_proxy/main/install-claude-proxy.sh
# Verify checksum (update with actual checksum)
echo "EXPECTED_SHA256  install-claude-proxy.sh" | sha256sum --check -
# Execute after verification
bash install-claude-proxy.sh
```

Or clone and run:
```bash
git clone https://github.com/jleechanorg/claude_llm_proxy.git
cd claude_llm_proxy
./install-claude-proxy.sh
```

## What It Does

The installer will:
1. ✅ Install minimal Python dependencies 
2. ✅ Configure your chosen backend (Vast.ai/Cerebras/Local)
3. ✅ Set up Claude CLI environment variables
4. ✅ Create startup scripts
5. ✅ Test the complete setup

## Backend Options

### 1. Vast.ai + Qwen (Recommended)
- **Cost**: ~$0.50/hour for RTX 4090
- **Model**: qwen3-coder (30B parameters)
- **Setup**: SSH tunnel to your vast.ai instance
- **Benefits**: Full control, great performance, cost-effective

### 2. Cerebras Cloud API
- **Cost**: Pay-per-token (competitive rates)
- **Model**: qwen-3-coder-480b 
- **Setup**: Just need API key
- **Benefits**: Zero infrastructure, instant setup

### 3. Local Options
#### A) Ollama
- **Cost**: Free (your hardware)
- **Model**: qwen3-coder or qwen2.5-coder:7b
- **Setup**: Installs Ollama locally
- **Benefits**: Complete privacy, no external calls

#### B) LM Studio
- **Cost**: Free (your hardware)
- **Model**: Any model you have loaded (supports qwen3-coder-30b)
- **Setup**: Connects to existing LM Studio installation
- **Benefits**: Use powerful models, familiar GUI, WSL support

## Architecture

```mermaid
Claude CLI → Local Proxy → [Vast.ai/Cerebras/Local] → Response
```

The proxy translates between:
- Anthropic Messages API (Claude CLI format)
- OpenAI Chat Completions API (backend format)

**Key Feature**: Full tool execution support - Claude Code CLI's bash commands, file operations, etc. all work normally.

## Core Components

- **`claude_code_tools_proxy.py`** - Tool-enabled proxy with full CLI support
- **`cerebras_proxy.py`** - Cerebras Cloud integration  
- **`simple_api_proxy.py`** - Lightweight vast.ai proxy
- **`claude-vast`** - SSH tunnel management and auto-startup for vast.ai
- **`claude-local`** - LM Studio integration with WSL host discovery
- **`claude-cerebras`** - Cerebras Cloud API integration 
- **`install-claude-proxy.sh`** - Unified installer script

## Manual Usage

After installation, start your proxy:
```bash
./claude-proxy-start.sh
```

Or use dedicated commands:
```bash
# For vast.ai (auto-starts server if needed)
./claude-vast "help me debug this Python script"

# For LM Studio (auto-discovers Windows host in WSL)
./claude-local "help me debug this Python script"

# For Cerebras Cloud (480B model)
./claude-cerebras "explain this complex algorithm"

# Or use Claude CLI normally after starting proxy
claude "help me debug this Python script"
```

## Environment Variables

The installer configures these automatically:
```bash
export ANTHROPIC_BASE_URL="http://localhost:8001"
export ANTHROPIC_API_KEY="dummy"
```

## Requirements

- Python 3.8+
- For Vast.ai: SSH access to your instance
- For Cerebras: API key
- For Ollama: ~8GB RAM for smaller models
- For LM Studio: LM Studio running with server enabled and model loaded

## Cost Comparison

| Backend | Cost | Model Size | Setup |
|---------|------|------------|-------|
| Anthropic Claude | $15/1M tokens | N/A | Instant |
| Vast.ai RTX 4090 | ~$0.50/hour | 30B | 5 min |
| Cerebras Cloud | ~$1/1M tokens | 480B | 1 min |
| Local Ollama | Free | 7B-30B | 10 min |
| LM Studio | Free | 7B-405B | 2 min |

## Security

- Command filtering prevents dangerous operations
- SSH tunneling for secure vast.ai access
- No data leaves your infrastructure (vast.ai/local options)
- Optional Redis caching with encryption

## Testing

The project includes comprehensive test suites to validate all integrations:

**Run all tests:**
```bash
cd tests/
./run_all_tests.sh
```

**Test individual backends:**
```bash
# Test LM Studio integration
./test_claude_local.sh

# Test vast.ai integration  
./test_claude_vast.sh

# Test Cerebras Cloud integration
./test_claude_cerebras.sh
```

**LLM-driven testing:**
- Tests verify actual file creation/deletion by the LLM
- Validates API format translation (Anthropic ↔ OpenAI)
- Confirms end-to-end functionality of each backend
- Tests include connectivity, performance, and cleanup validation

## Troubleshooting

**Proxy not starting?**
```bash
# Check logs
cat /tmp/claude-vast-tunnel.log

# Test connectivity
curl http://localhost:8001/health
```

**Claude CLI not connecting?**
```bash
# Verify environment
echo $ANTHROPIC_BASE_URL
echo $ANTHROPIC_API_KEY

# Re-source config
source ~/.bashrc
```

**Vast.ai SSH issues?**
```bash
# Test SSH connection
ssh -p YOUR_PORT root@YOUR_HOST.vast.ai

# Check vast.ai instance status
vastai show instances
```

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push branch: `git push origin feature-name`
5. Submit pull request

## License

MIT License - see LICENSE file for details.

## Support

- 📚 [Installation Guide](docs/setup.md)
- 🐛 [Report Issues](https://github.com/jleechanorg/claude_llm_proxy/issues)
- 💬 [Discussions](https://github.com/jleechanorg/claude_llm_proxy/discussions)