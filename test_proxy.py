from openai import OpenAI
import time

client = OpenAI(
    api_key="sk-anything",
    base_url="http://localhost:8000/v1"
)

print("Running tests...\n")

# Test 1: Simple question with GPT-4 (should downgrade and save money)
print("Test 1: Simple question with GPT-4")
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What is 2+2?"}]
)
print(f"Response: {response.choices[0].message.content}\n")
time.sleep(1)

# Test 2: Same question again (should hit cache)
print("Test 2: Same question (cache hit)")
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What is 2+2?"}]
)
print(f"Response: {response.choices[0].message.content}\n")
time.sleep(1)

# Test 3: Complex task with GPT-4 (should keep GPT-4)
print("Test 3: Complex question with GPT-4")
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Write a detailed analysis of quantum entanglement"}]
)
print(f"Response: {response.choices[0].message.content}\n")
time.sleep(1)

# Test 4: Check stats
print("Final Stats:")
import requests
stats = requests.get("http://localhost:8000/stats").json()
for key, value in stats.items():
    print(f"  {key}: {value}")