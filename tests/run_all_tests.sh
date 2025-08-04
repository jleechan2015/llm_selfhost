#!/bin/bash
# run_all_tests.sh - Comprehensive test runner for all Claude Code CLI proxy configurations

echo "🧪 Claude Code CLI Proxy - Comprehensive Test Suite"
echo "==================================================="
echo ""

# Test 1: Claude-Local (LM Studio Integration)
echo "🏠 Testing Local LM Studio Integration..."
echo "----------------------------------------"
if [ -f "test_claude_local.sh" ]; then
    if ./test_claude_local.sh; then
        echo "✅ Claude-Local tests PASSED"
        LOCAL_RESULT="PASSED"
    else
        echo "❌ Claude-Local tests FAILED"
        LOCAL_RESULT="FAILED"
    fi
else
    echo "⚠️ Claude-Local test script not found"
    LOCAL_RESULT="SKIPPED"
fi

echo ""
echo "🚀 Testing Remote Vast.ai Integration..."
echo "---------------------------------------"

# Test 2: Claude-Vast (Vast.ai Integration) 
if [ -f "test_claude_vast.sh" ]; then
    if ./test_claude_vast.sh; then
        echo "✅ Claude-Vast tests PASSED"
        VAST_RESULT="PASSED"
    else
        echo "❌ Claude-Vast tests FAILED"
        VAST_RESULT="FAILED"
    fi
else
    echo "⚠️ Claude-Vast test script not found"
    VAST_RESULT="SKIPPED"
fi

echo ""
echo "🧠 Testing Cerebras Cloud API Integration..."
echo "------------------------------------------"

# Test 3: Claude-Cerebras (Cerebras Cloud Integration)
if [ -f "test_claude_cerebras.sh" ]; then
    if ./test_claude_cerebras.sh; then
        echo "✅ Claude-Cerebras tests PASSED"
        CEREBRAS_RESULT="PASSED"
    else
        echo "❌ Claude-Cerebras tests FAILED"
        CEREBRAS_RESULT="FAILED"
    fi
else
    echo "⚠️ Claude-Cerebras test script not found"
    CEREBRAS_RESULT="SKIPPED"
fi

echo ""
echo "📊 Test Results Summary"
echo "======================"
echo "🏠 Local LM Studio:   $LOCAL_RESULT"
echo "🚀 Remote Vast.ai:     $VAST_RESULT"
echo "🧠 Cerebras Cloud:     $CEREBRAS_RESULT"
echo ""

# Overall result
if [[ "$LOCAL_RESULT" == "PASSED" && "$VAST_RESULT" == "PASSED" && "$CEREBRAS_RESULT" == "PASSED" ]]; then
    echo "🎉 ALL TESTS PASSED - Claude Code CLI Proxy is fully functional!"
    exit 0
elif [[ "$LOCAL_RESULT" == "FAILED" || "$VAST_RESULT" == "FAILED" || "$CEREBRAS_RESULT" == "FAILED" ]]; then
    echo "❌ SOME TESTS FAILED - Check the output above for details"
    exit 1
else
    echo "⚠️ TESTS INCOMPLETE - Some tests were skipped"
    exit 2
fi