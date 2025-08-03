#!/usr/bin/env python3
"""
RunPod Pod Management Script
Automates creation, monitoring, and termination of RunPod instances for Claude CLI integration.
"""

import runpod
import os
import time
import sys
import json

# --- CONFIGURE YOUR POD HERE ---
POD_CONFIGURATION = {
    "name": "Qwen3 Coder API Server",
    "image_name": "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04",
    "gpu_type_id": "NVIDIA GeForce RTX 4090",
    "container_disk_in_gb": 40,
    "volume_mount_path": "/datastore",
    "ports": "8000/tcp",
    "volume_id": "YOUR_VOLUME_ID_HERE"  # <-- IMPORTANT: Replace this with your volume ID!
}

# The full startup command to be executed inside the pod
STARTUP_COMMAND = """#!/bin/bash
set -e
set -x

echo "=== RunPod Startup Script for Claude CLI Integration ==="
echo "Starting at: $(date)"

# Install Ollama
echo "Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server in background
echo "Starting Ollama server..."
ollama serve &
sleep 10

# Setup persistent storage for Ollama models
echo "Setting up persistent storage..."
if [ ! -L /root/.ollama ]; then
    if [ -d /root/.ollama ]; then
        echo "Moving existing Ollama data to persistent storage..."
        mv /root/.ollama /datastore/ollama
    else
        echo "Creating Ollama directory in persistent storage..."
        mkdir -p /datastore/ollama
    fi
    ln -s /datastore/ollama /root/.ollama
    echo "Linked /root/.ollama to /datastore/ollama"
fi

# Install LiteLLM
echo "Installing LiteLLM..."
pip install litellm

# Ensure LiteLLM is in PATH
if ! command -v litellm &> /dev/null; then
    echo "Adding ~/.local/bin to PATH..."
    export PATH="$PATH:/root/.local/bin"
fi

# Pull the Qwen model (check if already exists to save time)
echo "Checking for Qwen model..."
if ! ollama list | grep -q "qwen3-coder:30b"; then
    echo "Pulling qwen3-coder:30b model (this may take 10-15 minutes)..."
    ollama pull qwen3-coder:30b
else
    echo "qwen3-coder:30b model already exists, skipping download"
fi

# Test Ollama is working
echo "Testing Ollama..."
ollama list

# Start LiteLLM proxy
echo "Starting LiteLLM proxy on port 8000..."
echo "Startup completed at: $(date)"
echo "=== LiteLLM Proxy Starting ==="
/root/.local/bin/litellm --model ollama/qwen3-coder:30b --host 0.0.0.0 --port 8000
"""

def check_configuration():
    """Validate configuration before creating pod."""
    if POD_CONFIGURATION["volume_id"] == "YOUR_VOLUME_ID_HERE":
        print("❌ Error: Please update the volume_id in POD_CONFIGURATION")
        print("   Go to RunPod > Volumes and copy your volume ID")
        return False
    
    if not os.getenv('RUNPOD_API_KEY'):
        print("❌ Error: RUNPOD_API_KEY environment variable not set")
        print("   Run: export RUNPOD_API_KEY='your-api-key-here'")
        return False
    
    return True

def create_pod_from_config():
    """Creates a new pod and runs the startup command."""
    if not check_configuration():
        return None
    
    print("🚀 Creating RunPod instance...")
    print(f"   Name: {POD_CONFIGURATION['name']}")
    print(f"   GPU: {POD_CONFIGURATION['gpu_type_id']}")
    print(f"   Volume: {POD_CONFIGURATION['volume_id']}")
    
    try:
        new_pod = runpod.create_pod(**POD_CONFIGURATION)
        pod_id = new_pod['id']
        print(f"✅ Pod created successfully!")
        print(f"   Pod ID: {pod_id}")
        print(f"   Waiting for pod to be ready...")
        
        # Wait for pod to be running
        max_wait = 300  # 5 minutes
        waited = 0
        while waited < max_wait:
            try:
                pod_info = runpod.get_pod(pod_id)
                status = pod_info['status']
                print(f"   Status: {status} (waited {waited}s)")
                
                if status == "RUNNING":
                    print("✅ Pod is RUNNING! Executing startup command...")
                    
                    # Execute startup command
                    result = runpod.run_in_pod(pod_id, STARTUP_COMMAND)
                    print("✅ Startup command sent successfully!")
                    print("\n" + "="*50)
                    print("🎉 POD IS READY FOR USE!")
                    print("="*50)
                    print(f"Pod ID: {pod_id}")
                    print(f"Status: {status}")
                    
                    # Get connection info
                    if 'runtime' in pod_info and 'ports' in pod_info['runtime']:
                        ports = pod_info['runtime']['ports']
                        if ports:
                            for port_info in ports:
                                if port_info.get('privatePort') == 8000:
                                    public_ip = port_info.get('ip')
                                    public_port = port_info.get('publicPort')
                                    if public_ip and public_port:
                                        public_url = f"http://{public_ip}:{public_port}"
                                        print(f"Public URL: {public_url}")
                                        print(f"\nTo connect Claude CLI:")
                                        print(f"export ANTHROPIC_BASE_URL='{public_url}'")
                                        print(f"export ANTHROPIC_MODEL='qwen3-coder:30b'")
                                    break
                    
                    print(f"\nMonitor startup progress in RunPod UI:")
                    print(f"https://www.runpod.io/console/pods/{pod_id}")
                    print(f"\nStartup will take 10-15 minutes for model download.")
                    return new_pod
                    
                elif status in ["FAILED", "TERMINATED"]:
                    print(f"❌ Pod failed to start: {status}")
                    return None
                    
            except Exception as e:
                print(f"   Error checking status: {e}")
            
            time.sleep(10)
            waited += 10
        
        print(f"❌ Timeout waiting for pod to start (waited {max_wait}s)")
        return None
        
    except Exception as e:
        print(f"❌ Error creating pod: {e}")
        return None

def list_pods():
    """List all current pods."""
    if not os.getenv('RUNPOD_API_KEY'):
        print("❌ Error: RUNPOD_API_KEY environment variable not set")
        return
    
    runpod.api_key = os.getenv('RUNPOD_API_KEY')
    
    try:
        pods = runpod.get_pods()
        if not pods:
            print("No pods found.")
            return
        
        print(f"Found {len(pods)} pod(s):")
        for pod in pods:
            pod_id = pod.get('id', 'unknown')
            name = pod.get('name', 'unnamed')
            status = pod.get('status', 'unknown')
            gpu_type = pod.get('gpuType', 'unknown')
            
            print(f"  {pod_id}: {name} ({status}) - {gpu_type}")
            
            # Show connection info for running pods
            if status == "RUNNING" and 'runtime' in pod and 'ports' in pod['runtime']:
                ports = pod['runtime']['ports']
                for port_info in ports:
                    if port_info.get('privatePort') == 8000:
                        public_ip = port_info.get('ip')
                        public_port = port_info.get('publicPort')
                        if public_ip and public_port:
                            print(f"    URL: http://{public_ip}:{public_port}")
    
    except Exception as e:
        print(f"❌ Error listing pods: {e}")

def terminate_pod(pod_id):
    """Terminates a specific pod."""
    if not os.getenv('RUNPOD_API_KEY'):
        print("❌ Error: RUNPOD_API_KEY environment variable not set")
        return
    
    runpod.api_key = os.getenv('RUNPOD_API_KEY')
    
    print(f"🛑 Terminating pod {pod_id}...")
    try:
        runpod.terminate_pod(pod_id)
        print("✅ Termination command sent successfully.")
    except Exception as e:
        print(f"❌ Error terminating pod: {e}")

def main():
    """Main function with command line interface."""
    if len(sys.argv) < 2:
        print("RunPod Management Script")
        print("Usage:")
        print("  python manage_pod.py create              # Create new pod")
        print("  python manage_pod.py list                # List all pods")
        print("  python manage_pod.py terminate <pod_id>  # Terminate specific pod")
        print("  python manage_pod.py help                # Show this help")
        print("")
        print("Environment variables needed:")
        print("  RUNPOD_API_KEY - Your RunPod API key")
        print("")
        print("Configuration:")
        print("  Edit POD_CONFIGURATION in this script to set volume_id")
        return
    
    command = sys.argv[1].lower()
    
    if command == "create":
        if not check_configuration():
            return
        runpod.api_key = os.getenv('RUNPOD_API_KEY')
        create_pod_from_config()
    
    elif command == "list":
        list_pods()
    
    elif command == "terminate":
        if len(sys.argv) < 3:
            print("❌ Error: Pod ID required for terminate command")
            print("Usage: python manage_pod.py terminate <pod_id>")
            return
        pod_id = sys.argv[2]
        terminate_pod(pod_id)
    
    elif command == "help":
        main()  # Show help
    
    else:
        print(f"❌ Unknown command: {command}")
        main()  # Show help

if __name__ == "__main__":
    main()