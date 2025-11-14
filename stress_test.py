"""
Stress test for the optimization proxy.
Simulates realistic usage with 100+ requests to test latency and caching.
"""

from openai import OpenAI
import time
import random

client = OpenAI(
    api_key="sk-anything",
    base_url="http://localhost:8000/v1"
)

# Realistic prompts (mix of duplicates and unique)
prompts = [
    ("gpt-4", "What is the capital of France?"),  # Simple, will cache
    ("gpt-4", "What is the capital of France?"),  # Cache hit
    ("gpt-4", "What is 2+2?"),  # Simple
    ("gpt-4", "What is 2+2?"),  # Cache hit
    ("gpt-3.5-turbo", "Translate 'hello' to Spanish"),
    ("gpt-4", "Translate 'goodbye' to French"),
    ("gpt-4", "What is Python?"),  # Simple
    ("gpt-4", "Explain quantum computing in detail with technical depth"),  # Keep GPT-4
    ("gpt-4", "What is the weather?"),  # Simple
    ("gpt-3.5-turbo", "How do I make a sandwich?"),
    ("gpt-4", "What is machine learning?"),  # Simple
    ("gpt-4", "What is machine learning?"),  # Cache hit
]

# Duplicate prompts more to simulate real usage
all_prompts = prompts * 10  # 120 total requests
random.shuffle(all_prompts)

print("🚀 Starting stress test with 120 requests...\n")
print(f"{'Request':<10} {'Model':<15} {'Latency':<12} {'Response Preview'}")
print("-" * 80)

latencies = []
start_time = time.time()

for i, (model, prompt) in enumerate(all_prompts, 1):
    req_start = time.time()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        
        latency = (time.time() - req_start) * 1000  # Convert to ms
        latencies.append(latency)
        
        response_preview = response.choices[0].message.content[:40]
        print(f"{i:<10} {model:<15} {latency:>6.1f}ms     {response_preview}...")
        
    except Exception as e:
        print(f"{i:<10} {model:<15} ERROR       {str(e)[:40]}")
    
    # Small delay between requests (realistic)
    time.sleep(0.1)

total_time = time.time() - start_time

# Get final stats
import requests
stats = requests.get("http://localhost:8000/stats").json()

print("\n" + "="*80)
print("📊 STRESS TEST RESULTS")
print("="*80)
print(f"\nTotal requests:        {len(all_prompts)}")
print(f"Total time:            {total_time:.2f}s")
print(f"Requests/second:       {len(all_prompts)/total_time:.2f}")
print(f"\nLatency statistics:")
print(f"  Average:             {sum(latencies)/len(latencies):.1f}ms")
print(f"  Min:                 {min(latencies):.1f}ms")
print(f"  Max:                 {max(latencies):.1f}ms")
print(f"  Median:              {sorted(latencies)[len(latencies)//2]:.1f}ms")

print(f"\nProxy statistics:")
print(f"  Cache hits:          {stats['cache_hits']} ({stats['cache_hit_rate']})")
print(f"  Downgraded to 3.5:   {stats['downgraded_to_gpt35']}")
print(f"  Total savings:       ${stats['total_savings']:.4f}")

print("\n" + "="*80)

# Performance assessment
avg_latency = sum(latencies) / len(latencies)
if avg_latency < 100:
    print("✅ EXCELLENT: Latency under 100ms (proxy overhead minimal)")
elif avg_latency < 200:
    print("✅ GOOD: Latency under 200ms (acceptable for production)")
elif avg_latency < 500:
    print("⚠️  WARNING: Latency over 200ms (investigate bottleneck)")
else:
    print("❌ POOR: Latency over 500ms (optimization needed)")

cache_rate = stats['cache_hits'] / stats['total_requests'] * 100
if cache_rate > 50:
    print(f"✅ EXCELLENT: {cache_rate:.1f}% cache hit rate (high savings)")
elif cache_rate > 30:
    print(f"✅ GOOD: {cache_rate:.1f}% cache hit rate (decent savings)")
else:
    print(f"⚠️  LOW: {cache_rate:.1f}% cache hit rate (needs more duplicates)")

print("="*80 + "\n")