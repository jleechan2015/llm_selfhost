#!/bin/bash
# Claude CLI RunPod Connection Script

if [ -z "$1" ]; then
    echo "Usage: $0 <pod_ip:port>"
    echo "Example: $0 38.80.152.248:30864"
    echo ""
    echo "Get the IP:port from 'runpod get pods' or the RunPod console"
    exit 1
fi

PUBLIC_URL="http://$1"

echo "🔗 Connecting Claude CLI to RunPod..."
echo "Endpoint: $PUBLIC_URL"

# Set environment variables
export ANTHROPIC_BASE_URL="$PUBLIC_URL"
export ANTHROPIC_MODEL="qwen3-coder:30b"

echo "✅ Environment configured:"
echo "  ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL"
echo "  ANTHROPIC_MODEL=$ANTHROPIC_MODEL"
echo ""
echo "🤖 You can now use Claude CLI normally:"
echo "  claude 'Write a Python function'"
