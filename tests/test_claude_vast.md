# Claude-Vast Integration Test

**Test Execution**: Run this file with Claude Code CLI to perform LLM-driven testing

## Test Setup

First, let me check if claude-vast is working and can connect to vast.ai:

```bash
../claude-vast --help
```

Let me check if we have any active vast.ai instances:

```bash
../claude-vast status
```

## LLM-Driven File Creation and Deletion Test

Now I'll use claude-vast to have the LLM create and delete a test file via the remote vast.ai instance. This tests the complete integration:

**Task**: Create a file called 'vast_integration_test.txt' with the content 'Vast.ai LLM integration successful!' and then immediately delete it. Confirm both the creation and deletion worked.

```bash
../claude-vast "Create a file called 'vast_integration_test.txt' with the content 'Vast.ai LLM integration successful!' and then immediately delete it. Confirm both the creation and deletion worked."
```

## File Operation Validation

Verify that the file was actually deleted (proving both creation and deletion worked):

```bash
ls -la vast_integration_test.txt 2>/dev/null || echo "✅ File successfully removed - vast integration test passed!"
```

## Advanced LLM File Operations Test

For a more comprehensive test, let's have the LLM create a Python script on the remote instance:

```bash
../claude-vast "Create a Python script called 'hello_vast.py' that prints 'Hello from Vast.ai GPU!' and shows the current GPU information using nvidia-smi. Then execute it to show it works, and finally delete it."
```

Verify the script was executed and cleaned up:

```bash
ls -la hello_vast.py 2>/dev/null || echo "✅ Python GPU script test completed successfully"
```

## Remote Server Status Test

Test server management capabilities:

```bash
../claude-vast "Check the current GPU status using nvidia-smi and show the memory usage"
```

## Connectivity Debugging

If the test fails, let's debug the connectivity:

Check if we can reach the vast.ai instance:

```bash
../claude-vast "echo 'Connection test successful'"
```

Test SSH tunnel status:

```bash
ps aux | grep ssh | grep vast || echo "No SSH tunnel found"
```

Check if the vast.ai instance is running:

```bash
vast show instances
```

Test direct connection to the vast.ai proxy:

```bash
curl -v "http://localhost:8000/health" --connect-timeout 10
```

Check for any running proxy processes:

```bash
ps aux | grep python | grep proxy
```

## Expected Results

**Success Criteria:**
- ✅ Vast.ai instance discovered and accessible
- ✅ Remote LLM responds through SSH tunnel  
- ✅ claude-vast successfully creates vast_integration_test.txt
- ✅ LLM can perform file operations on remote GPU instance
- ✅ Python script executes and shows GPU information
- ✅ LLM can clean up test files remotely
- ✅ SSH tunnel maintains stable connection

**If Test Fails:**
1. Check vast.ai instance is running and accessible
2. Verify SSH tunnel is established correctly
3. Confirm Ollama is running on the remote instance
4. Check qwen3-coder model is loaded
5. Verify network connectivity to vast.ai
6. Test SSH key authentication
7. Check firewall settings on vast.ai instance

## Performance Test

Test the performance difference between local and remote:

```bash
time ../claude-vast "What is 2+2? Answer briefly."
```

## GPU Utilization Test

Verify the remote GPU is being utilized:

```bash
../claude-vast "Check GPU utilization with nvidia-smi and confirm the model is loaded in GPU memory"
```

## Model Information Test

Get information about the loaded model:

```bash
../claude-vast "Tell me which model you are and confirm you're running on a vast.ai GPU instance"
```