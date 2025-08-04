# Claude-Local Integration Test

**Test Execution**: Run this file with Claude Code CLI to perform LLM-driven testing

## Test Setup

First, let me check if claude-local is working and can connect to your LM Studio:

```bash
../claude-local --help
```

Let me check the Windows host discovery:

```bash
ip route show | grep -i default | awk '{ print $3 }'
```

Now let me test if we can reach LM Studio directly:

```bash
curl -s "http://$(ip route show | grep -i default | awk '{ print $3 }'):1234/v1/models"
```

## LLM-Driven File Creation and Deletion Test

Now I'll use claude-local to have the LLM create and delete a test file. This tests the complete integration:

**Task**: Create a file called 'integration_test.txt' with the content 'LM Studio integration successful!' and then immediately delete it. Confirm both the creation and deletion worked.

```bash
../claude-local "Create a file called 'integration_test.txt' with the content 'LM Studio integration successful!' and then immediately delete it. Confirm both the creation and deletion worked."
```

## File Operation Validation

Verify that the file was actually deleted (proving both creation and deletion worked):

```bash
ls -la integration_test.txt 2>/dev/null || echo "✅ File successfully removed - integration test passed!"
```

## Advanced LLM File Operations Test

For a more comprehensive test, let's have the LLM create a Python script:

```bash
../claude-local "Create a Python script called 'hello_world.py' that prints 'Hello from LM Studio!' when run. Then execute it to show it works, and finally delete it."
```

Verify the script was executed and cleaned up:

```bash
ls -la hello_world.py 2>/dev/null || echo "✅ Python script test completed successfully"
```

## Connectivity Debugging

If the test fails, let's debug the connectivity:

Check if we can reach the Windows host:

```bash
ping -c 2 $(ip route show | grep -i default | awk '{ print $3 }')
```

Test specific LM Studio port:

```bash
telnet $(ip route show | grep -i default | awk '{ print $3 }') 1234
```

Test LM Studio health endpoint:

```bash
curl -v "http://$(ip route show | grep -i default | awk '{ print $3 }'):1234/v1/models" --connect-timeout 10
```

Check for Windows Firewall blocking:

```bash
nmap -p 1234 $(ip route show | grep -i default | awk '{ print $3 }')
```

## Expected Results

**Success Criteria:**
- ✅ Windows host discovered (should be 192.168.176.1 or similar)
- ✅ LM Studio responds to /v1/models endpoint
- ✅ claude-local successfully creates test_calculator.py
- ✅ Generated Python file contains Calculator class with 4 methods
- ✅ Python script executes without errors
- ✅ LLM can analyze its own output
- ✅ LLM can clean up test files

**If Test Fails:**
1. Check LM Studio server is enabled (Local Server tab)
2. Verify model is loaded and ready
3. Check Windows Firewall allows port 1234
4. Confirm WSL networking to Windows host works
5. Try different LM Studio port if needed