# Claude Code CLI Proxy

**Use Claude Code CLI with your own infrastructure instead of Anthropic's servers**

This project provides proxies that let you use Claude Code CLI with:
- 🚀 **Vast.ai GPU instances** running Qwen models
- 🧠 **Cerebras Cloud API** 
- 🏠 **Local Ollama** setup

## Quick Start

**One-command installation:**

```bash
curl -fsSL https://raw.githubusercontent.com/jleechanorg/claude_llm_proxy/main/install-claude-proxy.sh | bash
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

### 3. Local Ollama
- **Cost**: Free (your hardware)
- **Model**: qwen3-coder or qwen2.5-coder:7b
- **Setup**: Installs Ollama locally
- **Benefits**: Complete privacy, no external calls

## Architecture

```
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
- **`install-claude-proxy.sh`** - Unified installer script
- **`claude-vast`** - SSH tunnel management for vast.ai

## Manual Usage

After installation, start your proxy:
```bash
./claude-proxy-start.sh
```

Then use Claude CLI normally:
```bash
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
- For Local: ~8GB RAM for smaller models

## Cost Comparison

| Backend | Cost | Model Size | Setup |
|---------|------|------------|-------|
| Anthropic Claude | $15/1M tokens | N/A | Instant |
| Vast.ai RTX 4090 | ~$0.50/hour | 30B | 5 min |
| Cerebras Cloud | ~$1/1M tokens | 480B | 1 min |
| Local | Free | 7B-30B | 10 min |

## Security

- Command filtering prevents dangerous operations
- SSH tunneling for secure vast.ai access
- No data leaves your infrastructure (vast.ai/local options)
- Optional Redis caching with encryption

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