import os
import sys
from modelcache import cache
from modelcache.manager import CacheBase
from modelcache.embedding import SentenceTransformer
from ollama import Ollama

print(">> Reading connection details from environment variables...")

# Read connection details securely from environment variables
# The 'vastai create' command sets these up inside the container.
redis_host = os.getenv('REDIS_HOST')
redis_port = int(os.getenv('REDIS_PORT', 6379))  # Use a default port if not set
redis_password = os.getenv('REDIS_PASSWORD')

# Support optional Redis (fallback to no cache)
use_redis_cache = redis_host and redis_password

if use_redis_cache:
    print(f">> Initializing cache with Redis at {redis_host}:{redis_port}")
    
    # Initialize the ModelCache system
    cache.init(
        embedding_func=SentenceTransformer('all-MiniLM-L6-v2'),
        data_manager=CacheBase(
            name='redis',
            config={
                'host': redis_host,
                'port': redis_port,
                'password': redis_password
            }
        ),
        similarity_threshold=0.8
    )
else:
    print(">> No Redis cache configured, running without cache")

client = Ollama()

def call_ollama(model, prompt, **kwargs):
    """Call Ollama with optional caching"""
    if use_redis_cache:
        @cache.cache()
        def cached_call(model, prompt, **kwargs):
            print("--- CACHE MISS --- Calling the Ollama API to generate a new response...")
            return client.generate(model=model, prompt=prompt, **kwargs)
        return cached_call(model, prompt, **kwargs)
    else:
        print("--- NO CACHE --- Calling the Ollama API directly...")
        return client.generate(model=model, prompt=prompt, **kwargs)

def test_coding_capabilities(model):
    """Test coding-specific capabilities"""
    print(f"\n>> Testing {model} coding capabilities...\n")
    
    # Test 1: Code generation
    code_prompt = "Write a Python function to calculate fibonacci numbers with memoization"
    print("=== Code Generation Test ===")
    resp1 = call_ollama(model, code_prompt)
    print("Response 1:", resp1['response'][:200] + "..." if len(resp1['response']) > 200 else resp1['response'])
    
    print("\n=========================\n")
    
    # Test 2: Code debugging
    debug_prompt = "Debug this Python code and explain the issue: def factorial(n): return n * factorial(n)"
    print("=== Code Debugging Test ===")
    resp2 = call_ollama(model, debug_prompt)
    print("Response 2:", resp2['response'][:200] + "..." if len(resp2['response']) > 200 else resp2['response'])
    
    print("\n=========================\n")
    
    # Test 3: Similar to first (cache test)
    similar_prompt = "Create a Python function for fibonacci sequence using memoization technique"
    print("=== Cache Test (similar to first) ===")
    resp3 = call_ollama(model, similar_prompt)
    print("Response 3:", resp3['response'][:200] + "..." if len(resp3['response']) > 200 else resp3['response'])

if __name__ == "__main__":
    # Auto-detect available qwen-coder models or use default
    available_models = [
        'qwen2.5-coder:7b',
        'qwen2.5-coder:14b', 
        'qwen2.5-coder:32b',
        'qwen2:7b-instruct-q6_K',  # fallback
        'qwen2:7b'  # fallback
    ]
    
    model_to_use = None
    
    # Check what models are available
    try:
        import subprocess
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            available_local = result.stdout.lower()
            for model in available_models:
                if model.lower() in available_local:
                    model_to_use = model
                    print(f">> Found available model: {model}")
                    break
    except Exception as e:
        print(f">> Warning: Could not check available models: {e}")
    
    # Use first available model or default
    if not model_to_use:
        model_to_use = available_models[0]
        print(f">> Using default model: {model_to_use}")
        print(">> Note: Run 'ollama pull qwen2.5-coder:7b' to get the latest coding model")
    
    print(f"\n>> Application started with model: {model_to_use}")
    
    # Run coding capability tests
    test_coding_capabilities(model_to_use)
    
    print(f"\n✅ Self-hosted LLM testing completed with {model_to_use}!")
    if use_redis_cache:
        print("✅ Redis cache integration working")
    else:
        print("ℹ️  Running without Redis cache")