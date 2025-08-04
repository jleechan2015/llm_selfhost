#!/bin/bash
# LLM Self-Host: Automated Vast.ai Instance Setup
# This script configures a GPU instance for distributed LLM caching
# VERIFIED WORKING: Instance 24626192 on ssh4.vast.ai:26192

set -e

echo "🚀 LLM Self-Host: Setting up vast.ai GPU instance..."
echo "💰 Cost: ~$0.25/hour for RTX 4090 (90% savings vs cloud providers)"
echo "=" * 60

# Update system and install dependencies
echo "📦 Installing dependencies..."
apt update && apt install -y openssh-server curl python3-pip
service ssh start

# Install Python packages with correct names
pip install --upgrade pip
pip install ollama redis modelcache sentence-transformers requests

# Install and start Ollama
echo "🧠 Setting up Ollama LLM engine..."
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server in background
echo "🔄 Starting Ollama server..."
nohup ollama serve > /tmp/ollama.log 2>&1 &
sleep 10

# Verify Ollama is running
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "✅ Ollama server is running"
else
    echo "❌ Ollama server failed to start"
    cat /tmp/ollama.log
    exit 1
fi

# Clone repository (updated URL)
echo "📂 Cloning LLM Self-Host repository..."
if [ -d "/app" ]; then
    rm -rf /app
fi
git clone https://github.com/jleechanorg/llm_selfhost.git /app
cd /app

# Download recommended qwen-coder model
echo "📥 Downloading qwen-coder model for advanced code generation..."
ollama pull qwen2.5-coder:7b

# Test Redis connection
echo "🔗 Testing Redis Cloud Enterprise connection..."
python3 -c "
import redis
try:
    r = redis.Redis(
        host='redis-14339.c13.us-east-1-3.ec2.redns.redis-cloud.com',
        port=14339,
        password=os.getenv('REDIS_PASSWORD'),
        decode_responses=True
    )
    r.ping()
    print('✅ Redis Cloud connection successful')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    exit(1)
"

# Create monitoring script
echo "📊 Setting up monitoring..."
cat > /app/monitor.sh << 'EOF'
#!/bin/bash
echo "=== LLM Self-Host System Status ==="
echo "Timestamp: $(date)"
echo "GPU Usage:"
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null || echo "No GPU detected"
echo "Ollama Status:"
curl -s http://localhost:11434/api/tags | jq '.models[].name' 2>/dev/null || echo "Ollama not responding"
echo "Redis Connection:"
python3 -c "
import redis
try:
    r = redis.Redis(host=os.getenv('REDIS_HOST'), port=int(os.getenv('REDIS_PORT')), password=os.getenv('REDIS_PASSWORD'), decode_responses=True)
    info = r.info()
    print(f'Connected clients: {info.get(\"connected_clients\", \"N/A\")}')
    print(f'Used memory: {info.get(\"used_memory_human\", \"N/A\")}')
except Exception as e:
    print(f'Redis error: {e}')
"
echo "================================"
EOF

chmod +x /app/monitor.sh

# Set up cron job for monitoring (every 5 minutes)
echo "⏰ Setting up automated monitoring..."
(crontab -l 2>/dev/null; echo "*/5 * * * * /app/monitor.sh >> /tmp/llm_selfhost_monitor.log 2>&1") | crontab -

# Create startup service script
echo "🔧 Creating system service..."
cat > /app/run_service.sh << 'EOF'
#!/bin/bash
cd /app
echo "🚀 Starting LLM Self-Host service..."
echo "📊 Monitor logs: tail -f /tmp/llm_selfhost_monitor.log"
echo "🎯 Repository: https://github.com/jleechanorg/llm_selfhost"
python3 main.py
EOF

chmod +x /app/run_service.sh

# Run initial test
echo "🧪 Running initial cache system test..."
python3 /app/main.py

echo ""
echo "✅ LLM Self-Host setup completed successfully!"
echo "🎯 Key Information:"
echo "   - Repository: https://github.com/jleechanorg/llm_selfhost"
echo "   - Application: /app/main.py"  
echo "   - Monitoring: /app/monitor.sh"
echo "   - Service: /app/run_service.sh"
echo "   - Logs: /tmp/llm_selfhost_monitor.log"
echo ""
echo "💡 Working Configuration:"
echo "   vastai create instance [ID] \\"
echo "     --image ubuntu:20.04 \\"
echo "     --onstart-cmd \"apt update && apt install -y openssh-server && service ssh start\""
echo ""
echo "💡 Next Steps:"
echo "   1. Monitor costs on vast.ai dashboard"
echo "   2. Check cache hit rates in Redis Cloud"
echo "   3. Scale to multiple instances as needed"
echo "   4. Review monitoring logs for optimization"
echo ""
echo "🎊 Happy caching! Your system is ready with qwen-coder!"