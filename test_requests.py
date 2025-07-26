#!/usr/bin/env python3
"""
Test with requests library
"""

import requests
import json

def test_with_requests():
    url = "https://dashscope.aliyuncs.com/api/v2/apps/claude-code-proxy/v1/messages"
    headers = {
        "Authorization": "Bearer sk-001061f9c18447ecbed88b9bb6d87871",
        "Content-Type": "application/json"
    }
    
    # 使用标准的Claude请求格式
    request_body = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": "Hello, world!"
            }
        ]
    }
    
    print("Sending request with requests library...")
    print("URL:", url)
    print("Headers:", json.dumps(headers, indent=2))
    print("Body:", json.dumps(request_body, indent=2))
    
    try:
        response = requests.post(url, headers=headers, json=request_body, timeout=30.0)
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body: {response.text}")
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    test_with_requests()