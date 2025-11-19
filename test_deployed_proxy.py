from openai import OpenAI
import time
import httpx

# Test direct POST
url = "https://inference-proxy.onrender.com/v1/chat/completions"
data = {
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "test"}]
}

response = httpx.post(url, json=data, timeout=60)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

# Add timeout and retry
client = OpenAI(
    api_key="sk-anything",
    base_url="https://inference-proxy.onrender.com/v1/",
    timeout=60.0  # Render free tier can be slow to wake up
)

print("Sending request to deployed proxy...")

try:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "What is 2+2?"}]
    )
    print(f"Success! Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"Error: {e}")
