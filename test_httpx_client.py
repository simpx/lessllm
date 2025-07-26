#!/usr/bin/env python3
"""
Test with httpx client configuration matching Anthropic
"""

import httpx
import json

def test_with_httpx_client():
    # 创建httpx客户端，模拟Anthropic库的配置
    client = httpx.Client(
        timeout=30.0,
        follow_redirects=True
    )
    
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
    
    print("Sending request with httpx client...")
    print("URL:", url)
    print("Headers:", json.dumps(headers, indent=2))
    print("Body:", json.dumps(request_body, indent=2))
    
    try:
        response = client.post(url, headers=headers, json=request_body)
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body: {response.text}")
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        client.close()

if __name__ == "__main__":
    test_with_httpx_client()