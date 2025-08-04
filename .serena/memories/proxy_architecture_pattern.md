# Proxy Architecture Pattern

## Consistent Design Pattern
All three Claude integrations now follow the same clean architecture:

```
Claude CLI → Tool-Enabled Proxy → Backend API
              ↑
       FULL TOOL EXECUTION
       - ClaudeCodeTools class
       - bash() method
       - str_replace_editor() method  
       - write_file() method
       - Pattern-based tool detection
```

## Tool-Enabled Proxy Files
1. **vast_tools_proxy.py**: 
   - Backend: Ollama/Qwen via vast.ai
   - Features: Redis caching + tool execution
   - Port: 8000 (deployed via SSH tunnel to 8001)

2. **cerebras_tools_proxy.py**:
   - Backend: Cerebras Cloud API (480B model)
   - Features: Retry logic + rate limiting + tool execution
   - Port: 8002

3. **local_tools_proxy.py**:
   - Backend: LM Studio (local)
   - Features: Environment-based config + tool execution
   - Port: 8001

## ClaudeCodeTools Class
Consistent across all proxies:
- `__init__()`: Initialize session
- `bash(command)`: Execute bash with security checks
- `str_replace_editor(command, path, ...)`: File operations
- `write_file(path, content)`: Direct file writing

## Integration Scripts
- **claude-vast**: Deploys vast_tools_proxy.py to remote instance
- **claude-cerebras**: Starts cerebras_tools_proxy.py locally
- **claude-local**: Starts local_tools_proxy.py with env vars

## Pattern Benefits
- Consistent tool execution across all backends
- Maintainable codebase with shared tool logic
- Environment-specific optimizations maintained
- Clean separation of concerns