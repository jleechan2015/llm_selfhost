import os
from modelcache import cache
from modelcache.manager import CacheBase
from modelcache.embedding import SentenceTransformer
from ollama import Ollama

print(">> Reading connection details from environment variables...")

# Read connection details securely from environment variables
# The 'vastai create' command sets these up inside the container.
redis_host = os.getenv('REDIS_HOST')
redis_port = int(os.getenv('REDIS_PORT', 6379)) # Use a default port if not set
redis_password = os.getenv('REDIS_PASSWORD')

if not all([redis_host, redis_port, redis_password]):
    print("!! ERROR: Missing Redis connection details in environment variables.")
    exit(1)

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

client = Ollama()

@cache.cache()
def call_ollama(model, prompt, **kwargs):
    print("--- CACHE MISS --- Calling the Ollama API to generate a new response...")
    return client.generate(model=model, prompt=prompt, **kwargs)

if __name__ == "__main__":
    print("\n>> Application started. Sending first request...")
    resp1 = call_ollama('qwen2:7b-instruct-q6_K', "Briefly explain the plot of the movie 'Inception'.")
    print("Response 1:", resp1['response'])

    print("\n=========================\n")

    print(">> Sending second, similar request (should be a cache HIT)...")
    resp2 = call_ollama('qwen2:7b-instruct-q6_K', "Can you tell me what the film 'Inception' is about in a few sentences?")
    # If this is a cache hit, the "CACHE MISS" message will not be printed.
    print("Response 2:", resp2['response'])