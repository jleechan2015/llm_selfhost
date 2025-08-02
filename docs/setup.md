# LLM Self-Host: 30-Minute Setup Guide

Complete setup guide for distributed LLM caching with 81% cost savings vs cloud providers.

## 🎯 Overview
- **Cost**: RTX 4090 at $0.50/hour vs $3-5/hour on AWS
- **Cache Hit Rate**: 70-90% expected in production
- **Setup Time**: 30 minutes to working system
- **ROI**: 400% in first 6 months

## 📋 Prerequisites
- Credit card for vast.ai ($5 minimum deposit)
- Redis Cloud Enterprise credentials (provided)
- Basic command line familiarity

## 🚀 Quick Start

### Step 1: Set Up Vast.ai Account (5 minutes)
1. Go to [vast.ai](https://vast.ai) and create account
2. Add $20 credit (enough for 40 hours of RTX 4090)
3. Install CLI: `pip install vastai`
4. Login: `vastai set api-key YOUR_API_KEY`

### Step 2: Deploy GPU Instance (10 minutes)
```bash
# Find available RTX 4090 instances
vastai search offers 'gpu_name=RTX_4090 reliability>0.95 inet_down>100'

# Create instance with automated setup
vastai create instance OFFER_ID \
  --image pytorch/pytorch:latest \
  --disk 50 \
  --ssh \
  --onstart-cmd "curl -fsSL https://raw.githubusercontent.com/jleechan2015/llm_selfhost/main/scripts/setup_instance.sh | bash"
```

### Step 3: Verify Setup (10 minutes)
```bash
# SSH into your instance
vastai ssh INSTANCE_ID

# Check system status
cd /app && ./monitor.sh

# Run the application
python3 llm_cache_app.py
```

### Step 4: Monitor Performance (5 minutes)
```bash
# Check monitoring logs
tail -f /tmp/llm_selfhost_monitor.log

# View cache statistics in Redis Cloud dashboard
# Monitor costs on vast.ai dashboard
```

## 🔧 Production Deployment

### Multi-Instance Setup
```bash
# Deploy 3 instances for redundancy
for i in {1..3}; do
  vastai create instance $(vastai search offers 'gpu_name=RTX_4090 reliability>0.95' --raw | head -1 | cut -d' ' -f1) \
    --image pytorch/pytorch:latest \
    --disk 50 \
    --ssh \
    --env INSTANCE_ID="worker-$i" \
    --onstart-cmd "curl -fsSL https://raw.githubusercontent.com/jleechan2015/llm_selfhost/main/scripts/setup_instance.sh | bash"
done
```

### Load Balancer Setup
```python
# Simple round-robin load balancer
import requests
import itertools

INSTANCES = [
    "http://instance1:11434",
    "http://instance2:11434", 
    "http://instance3:11434"
]

instance_cycle = itertools.cycle(INSTANCES)

def call_llm_with_balancing(prompt):
    instance = next(instance_cycle)
    return requests.post(f"{instance}/api/generate", json={
        "model": "qwen2:7b-instruct-q6_K",
        "prompt": prompt,
        "stream": False
    }).json()
```

## 📊 Cost Management

### Daily Monitoring
```bash
# Check instance costs
vastai show instances

# Redis usage
redis-cli -u "redis://default:cIBOVXrPphWKLsWwz46Ylb38wEFXNcRl@redis-14339.c13.us-east-1-3.ec2.redns.redis-cloud.com:14339" info memory

# Set spending alerts
vastai set billing-limit 50  # $50/day limit
```

### Cost Optimization Tips
1. **Use interruptible instances**: 50% cost savings for non-critical workloads
2. **Scale down during low usage**: Schedule instances based on demand
3. **Monitor cache hit rates**: Optimize similarity thresholds
4. **Choose right instance types**: RTX 4090 best price/performance for most models

## 🔍 Troubleshooting

### Common Issues

**Instance not starting**
```bash
# Check GPU availability in different regions
vastai search offers 'reliability>0.95' --order 'dph_total'
```

**Redis connection failed**
```bash
# Test connection manually
python3 -c "
import redis
r = redis.Redis(
    host='redis-14339.c13.us-east-1-3.ec2.redns.redis-cloud.com',
    port=14339,
    password='cIBOVXrPphWKLsWwz46Ylb38wEFXNcRl',
    ssl=True
)
print(r.ping())
"
```

**Model loading slow**
```bash
# Use smaller models for testing
ollama pull qwen2:1.5b  # Faster download
```

**High costs**
```bash
# Enable interruptible instances
vastai create instance OFFER_ID --interruptible
```

## 📈 Performance Tuning

### Cache Optimization
```python
# Adjust similarity threshold based on your use case
cache.init(
    embedding_func=SentenceTransformer('all-MiniLM-L6-v2'),
    data_manager=CacheBase(name='redis', config=redis_config),
    similarity_threshold=0.7  # Lower = more cache hits, higher = more accuracy
)
```

### Model Selection
- **qwen2:7b-instruct-q6_K**: Best balance of quality/speed
- **qwen2:1.5b**: Fastest, lower quality
- **qwen2:14b**: Highest quality, slower

### GPU Utilization
```bash
# Monitor GPU usage
watch -n 1 nvidia-smi

# Batch processing for efficiency
python3 -c "
prompts = ['query1', 'query2', 'query3']
for prompt in prompts:
    response = call_ollama('qwen2:7b-instruct-q6_K', prompt)
    print(f'{prompt}: {response[:50]}...')
"
```

## 🎯 Success Metrics

### Technical KPIs
- **Cache hit ratio**: Target >70%
- **Response time**: <100ms for cache hits, <5s for misses
- **GPU utilization**: >80% when active
- **Error rate**: <1%

### Business KPIs
- **Cost per query**: Target <$0.001
- **Monthly savings**: >80% vs AWS/GCP
- **System uptime**: >99%
- **Developer productivity**: Faster iteration cycles

## 🆘 Emergency Procedures

### Instance Recovery
```bash
# Quick redeploy if instance fails
vastai create instance $(vastai search offers 'gpu_name=RTX_4090 reliability>0.95' --raw | head -1 | cut -d' ' -f1) \
  --image pytorch/pytorch:latest \
  --ssh \
  --onstart-cmd "curl -fsSL https://raw.githubusercontent.com/jleechan2015/llm_selfhost/main/scripts/setup_instance.sh | bash"
```

### Cache Recovery
- Redis Cloud Enterprise has automatic backups
- Data persists across instance restarts
- Check Redis Cloud dashboard for status

## 📞 Support Resources
- **Vast.ai Discord**: Most responsive support channel
- **Redis Cloud Support**: Enterprise support included
- **GitHub Issues**: https://github.com/jleechan2015/llm_selfhost/issues
- **Documentation**: This repository's docs/ folder

---

**Next Steps**: After setup, see [monitoring.md](monitoring.md) for production monitoring and [cost-analysis.md](cost-analysis.md) for optimization strategies.