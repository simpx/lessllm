#!/usr/bin/env python3
"""
Test with exact request body from Anthropic
"""

import httpx
import json

def test_exact_body():
    url = "https://dashscope.aliyuncs.com/api/v2/apps/claude-code-proxy/v1/messages"
    headers = {
        "Authorization": "Bearer sk-001061f9c18447ecbed88b9bb6d87871",
        "Content-Type": "application/json"
    }
    
    # 这是Anthropic库实际发送的请求体格式
    request_body = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user", 
                "content": "Hello, world!"
            }
        ],
        "stream": False
    }
    
    print("Sending request with exact body format...")
    print("URL:", url)
    print("Headers:", json.dumps(headers, indent=2))
    print("Body:", json.dumps(request_body, indent=2))
    
    try:
        response = httpx.post(url, headers=headers, json=request_body, timeout=30.0)
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body: {response.text}")
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    test_exact_body()