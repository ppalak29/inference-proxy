from openai import OpenAI
import time

# Point to your proxy
client = OpenAI(
    api_key="sk-anything",  # Proxy handles real key
    base_url="http://localhost:8000/v1"
)

# Simulate a real app making various calls
prompts = [
    ("gpt-4", "What is the capital of France?"),  # Should downgrade
    ("gpt-4", "What is the capital of France?"),  # Should cache
    ("gpt-3.5-turbo", "Translate 'hello' to Spanish"),  # Already 3.5
    ("gpt-4", "Explain the implications of quantum computing on cryptography in detail with examples"),  # Keep GPT-4
    ("gpt-4", "What is 5+7?"),  # Should downgrade
]

total_cost_without_proxy = 0
total_cost_with_proxy = 0

for model, prompt in prompts:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    
    print(f"[{model}] {prompt[:50]}...")
    print(f"Response: {response.choices[0].message.content[:100]}...\n")
    time.sleep(1)

# Check final stats
import requests
stats = requests.get("http://localhost:8000/stats").json()

print("\n" + "="*50)
print("FINAL RESULTS:")
print("="*50)
print(f"Total requests: {stats['total_requests']}")
print(f"Cache hits: {stats['cache_hits']}")
print(f"Downgraded to GPT-3.5: {stats['downgraded_to_gpt35']}")
print(f"💰 TOTAL SAVINGS: ${stats['total_savings']}")