from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import time
import hashlib
import json
import redis
import re

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = "https://api.openai.com/v1"
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

# Redis connection
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    CACHE_ENABLED = True
except:
    print("⚠️  Redis not available, caching disabled")
    CACHE_ENABLED = False

# Stats tracking
stats = {
    "total_requests": 0,
    "cache_hits": 0,
    "downgraded_to_gpt35": 0,
    "total_savings": 0.0
}

# Cost per 1k tokens
COSTS = {
    "gpt-4": 0.03,
    "gpt-3.5-turbo": 0.002
}

def calculate_cost(model, tokens):
    """Calculate cost for a request"""
    cost_per_1k = COSTS.get(model, 0.002)
    return (tokens / 1000) * cost_per_1k

def cache_key(messages, model):
    """Generate cache key from messages"""
    content = json.dumps({"messages": messages, "model": model}, sort_keys=True)
    return f"cache:{hashlib.md5(content.encode()).hexdigest()}"

def should_use_gpt35(messages, requested_model):
    """Decide if we can downgrade GPT-4 to GPT-3.5"""
    if "gpt-4" not in requested_model.lower():
        return requested_model
    
    last_message = messages[-1]["content"].lower()
    
    # Simple questions
    if any(last_message.startswith(q) for q in ["what is", "what are", "how do", "why", "when", "who", "where"]):
        return "gpt-3.5-turbo"
    
    # Translation
    if "translate" in last_message:
        return "gpt-3.5-turbo"
    
    # Short prompts
    if len(last_message) < 50:
        return "gpt-3.5-turbo"
    
    # Math
    if re.match(r'^[\d\+\-\*/\s]+$', last_message):
        return "gpt-3.5-turbo"
    
    return requested_model

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    Proxy with caching + smart routing + cost tracking
    """
    try:
        body = await request.json()
        messages = body.get("messages", [])
        requested_model = body.get("model", "gpt-3.5-turbo")
        
        stats["total_requests"] += 1
        
        # Smart routing
        actual_model = should_use_gpt35(messages, requested_model)
        was_downgraded = (actual_model != requested_model)
        
        if was_downgraded:
            stats["downgraded_to_gpt35"] += 1
            print(f"🔄 DOWNGRADED: {requested_model} → {actual_model} for '{messages[-1]['content'][:50]}'")
        
        body["model"] = actual_model
        
        # Check cache
        if CACHE_ENABLED:
            key = cache_key(messages, actual_model)
            cached = redis_client.get(key)
            
            if cached:
                stats["cache_hits"] += 1
                cached_data = json.loads(cached)
                
                # Calculate savings from cache hit
                tokens = cached_data.get("usage", {}).get("total_tokens", 30)
                saved_cost = calculate_cost(actual_model, tokens)
                stats["total_savings"] += saved_cost
                
                print(f"✅ CACHE HIT: {messages[-1]['content'][:50]}")
                print(f"💰 SAVED: ${saved_cost:.4f} (cache hit)")
                
                return JSONResponse(cached_data)
        
        # Cache miss - get response
        if MOCK_MODE:
            response_data = {
                "id": "chatcmpl-mock123",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": actual_model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"[MOCK {actual_model}] Response to: {messages[-1]['content']}"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
        else:
            # Real OpenAI call
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{OPENAI_BASE_URL}/chat/completions",
                    json=body,
                    headers=headers,
                    timeout=60.0
                )
            response_data = response.json()
        
        # Calculate savings from downgrade
        tokens = response_data.get("usage", {}).get("total_tokens", 30)
        actual_cost = calculate_cost(actual_model, tokens)
        
        if was_downgraded:
            original_cost = calculate_cost(requested_model, tokens)
            savings = original_cost - actual_cost
            stats["total_savings"] += savings
            print(f"💰 SAVED: ${savings:.4f} (${original_cost:.4f} → ${actual_cost:.4f})")
        
        # Cache the response
        if CACHE_ENABLED:
            redis_client.setex(key, 86400, json.dumps(response_data))
            print(f"💾 CACHED: {messages[-1]['content'][:50]}")
        
        return JSONResponse(response_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "mock_mode": MOCK_MODE,
        "cache_enabled": CACHE_ENABLED
    }

@app.get("/stats")
async def get_stats():
    cache_count = 0
    if CACHE_ENABLED:
        cache_count = len(redis_client.keys("cache:*"))
    
    return {
        "total_requests": stats["total_requests"],
        "cache_hits": stats["cache_hits"],
        "cache_hit_rate": f"{(stats['cache_hits']/stats['total_requests']*100):.1f}%" if stats["total_requests"] > 0 else "0%",
        "downgraded_to_gpt35": stats["downgraded_to_gpt35"],
        "cached_responses": cache_count,
        "total_savings": round(stats["total_savings"], 4)
    }

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)