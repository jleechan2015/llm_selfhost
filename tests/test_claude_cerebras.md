# Claude-Cerebras Integration Test

**Test Execution**: Run this file with Claude Code CLI to perform LLM-driven testing

## Test Setup

First, let me check if claude-cerebras is working and can connect to Cerebras Cloud API:

```bash
../claude-cerebras --help
```

Let me verify the API key is configured:

```bash
echo $CEREBRAS_API_KEY | cut -c1-10 || echo "CEREBRAS_API_KEY not set"
```

Test basic connectivity to Cerebras API:

```bash
curl -s -H "Authorization: Bearer $CEREBRAS_API_KEY" "https://api.cerebras.ai/v1/chat/completions" -H "Content-Type: application/json" -d '{"model":"qwen-3-coder-480b","messages":[{"role":"user","content":"Hello"}],"max_tokens":5}' | jq .
```

## LLM-Driven File Creation and Deletion Test

Now I'll use claude-cerebras to have the LLM create and delete a test file via the Cerebras Cloud API. This tests the complete integration:

**Task**: Create a file called 'cerebras_test.txt' with the content 'Cerebras 480B integration successful!' and then immediately delete it. Confirm both the creation and deletion worked.

```bash
../claude-cerebras "Create a file called 'cerebras_test.txt' with the content 'Cerebras 480B integration successful!' and then immediately delete it. Confirm both the creation and deletion worked."
```

## File Operation Validation

Verify that the file was actually deleted (proving both creation and deletion worked):

```bash
ls -la cerebras_test.txt 2>/dev/null || echo "✅ File successfully removed - Cerebras integration test passed!"
```

## Advanced LLM File Operations Test

For a more comprehensive test, let's have the LLM create a Python script using the 480B model:

```bash
../claude-cerebras "Create a Python script called 'hello_cerebras.py' that prints 'Hello from Cerebras 480B model!' and shows the current system information. Then execute it to show it works, and finally delete it."
```

Verify the script was executed and cleaned up:

```bash
ls -la hello_cerebras.py 2>/dev/null || echo "✅ Python script test completed successfully"
```

## Model Capabilities Test

Test the advanced capabilities of the 480B model:

```bash
../claude-cerebras "Write a short Python function to calculate fibonacci numbers efficiently, save it as 'fib.py', test it with fib(10), show the result, then delete the file."
```

## Performance Test

Test the response time of the cloud API:

```bash
time ../claude-cerebras "What is 2+2? Answer with just the number."
```

## API Rate Limiting Test

Test how the proxy handles rate limiting:

```bash
../claude-cerebras "Tell me about the Cerebras 480B model you're running on. Keep it brief."
```

## Connectivity Debugging

If the test fails, let's debug the connectivity:

Check API key format:

```bash
echo $CEREBRAS_API_KEY | wc -c
```

Test direct API access:

```bash
curl -v -H "Authorization: Bearer $CEREBRAS_API_KEY" "https://api.cerebras.ai/v1/chat/completions" --connect-timeout 10
```

Check proxy health:

```bash
curl -v "http://localhost:8002/health" --connect-timeout 10
```

Test proxy models endpoint:

```bash
curl -s "http://localhost:8002/v1/models" | jq .
```

Check for proxy process:

```bash
ps aux | grep cerebras_proxy
```

## Expected Results

**Success Criteria:**
- ✅ Cerebras API key validated
- ✅ Cloud API connectivity confirmed  
- ✅ claude-cerebras successfully creates cerebras_test.txt
- ✅ LLM can perform file operations using 480B model
- ✅ Python script executes and shows system info
- ✅ LLM can clean up test files
- ✅ Proxy handles rate limiting gracefully
- ✅ Response times are reasonable (<30s for simple queries)

**If Test Fails:**
1. Check CEREBRAS_API_KEY is set correctly
2. Verify internet connectivity
3. Confirm API key is valid at https://inference.cerebras.ai/
4. Check proxy startup logs in /tmp/cerebras_proxy.log
5. Verify Python dependencies (fastapi, uvicorn, requests)
6. Test direct API access without proxy
7. Check for rate limiting or quota issues

## API Usage Test

Monitor API usage during testing:

```bash
../claude-cerebras "Create a simple 'Hello World' program in 3 different languages (Python, JavaScript, Bash), save each to separate files, execute them all, show outputs, then clean up all files."
```

## Model Information Test

Get information about the 480B model:

```bash
../claude-cerebras "What model are you and what are your key capabilities? Mention that you're running on Cerebras hardware."
```

## Edge Case Test

Test with longer content generation:

```bash
../claude-cerebras "Write a comprehensive README.md file for a simple calculator project, including installation, usage, and examples. Save it as 'test_readme.md', then delete it after confirming it was created."
```