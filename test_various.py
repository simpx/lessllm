#!/usr/bin/env python3
"""
Test various request body formats
"""

import httpx
import json

def test_various_formats():
    url = "https://dashscope.aliyuncs.com/api/v2/apps/claude-code-proxy/v1/messages"
    headers = {
        "Authorization": "Bearer sk-001061f9c18447ecbed88b9bb6d87871",
        "Content-Type": "application/json"
    }
    
    # 尝试不同的请求体格式
    test_cases = [
        # 1. 最简格式
        {
            "model": "claude-3-haiku-20240307",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 100
        },
        
        # 2. 包含stream字段
        {
            "model": "claude-3-haiku-20240307", 
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 100,
            "stream": False
        },
        
        # 3. 包含默认参数
        {
            "model": "claude-3-haiku-20240307",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 100,
            "temperature": 1.0,
            "top_p": 0.999,  # 略微不同的值
        },
        
        # 4. 包含system消息
        {
            "model": "claude-3-haiku-20240307",
            "messages": [{"role": "user", "content": "Hello"}],
            "system": "You are a helpful assistant.",
            "max_tokens": 100
        }
    ]
    
    for i, request_body in enumerate(test_cases, 1):
        print(f"\n=== Test Case {i} ===")
        print(f"Body: {json.dumps(request_body, indent=2)}")
        
        try:
            response = httpx.post(url, headers=headers, json=request_body, timeout=30.0)
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                print(f"SUCCESS! Response: {response.text[:100]}...")
                return response
            else:
                print(f"Response body: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nAll test cases failed.")
    return None

if __name__ == "__main__":
    test_various_formats()