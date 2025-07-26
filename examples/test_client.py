#!/usr/bin/env python3
"""
LessLLM 测试客户端示例
"""

import asyncio
import httpx
import json
import os
from datetime import datetime


async def test_lessllm_proxy():
    """测试LessLLM代理服务"""
    
    # LessLLM代理服务地址
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        
        # 1. 健康检查
        print("🔍 Testing health check...")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"✓ Health check: {response.status_code}")
            print(f"  Response: {response.json()}")
        except Exception as e:
            print(f"✗ Health check failed: {e}")
            return
        
        # 2. 列出可用模型
        print("\n🤖 Testing models endpoint...")
        try:
            response = await client.get(f"{base_url}/v1/models")
            print(f"✓ Models: {response.status_code}")
            models = response.json()
            print(f"  Available models: {len(models.get('data', []))}")
            for model in models.get('data', [])[:3]:
                print(f"    - {model['id']}")
        except Exception as e:
            print(f"✗ Models endpoint failed: {e}")
        
        # 3. 测试聊天完成 (非流式)
        print("\n💬 Testing chat completions (non-streaming)...")
        try:
            chat_request = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello! Please respond with a short greeting."}
                ],
                "max_tokens": 50,
                "temperature": 0.7
            }
            
            response = await client.post(
                f"{base_url}/v1/chat/completions",
                json=chat_request,
                timeout=30.0
            )
            
            print(f"✓ Chat completion: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and result["choices"]:
                    content = result["choices"][0]["message"]["content"]
                    print(f"  Response: {content[:100]}...")
                    
                if "usage" in result:
                    usage = result["usage"]
                    print(f"  Tokens used: {usage.get('total_tokens', 'N/A')}")
            else:
                print(f"  Error: {response.text}")
                
        except Exception as e:
            print(f"✗ Chat completion failed: {e}")
        
        # 4. 测试流式聊天完成
        print("\n🌊 Testing streaming chat completions...")
        try:
            chat_request = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": "Count from 1 to 5, each number on a new line."}
                ],
                "max_tokens": 30,
                "stream": True
            }
            
            chunks_received = 0
            content_parts = []
            
            async with client.stream(
                "POST",
                f"{base_url}/v1/chat/completions",
                json=chat_request,
                timeout=30.0
            ) as response:
                
                print(f"✓ Streaming started: {response.status_code}")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            chunks_received += 1
                            
                            if ("choices" in chunk and 
                                chunk["choices"] and 
                                "delta" in chunk["choices"][0] and
                                "content" in chunk["choices"][0]["delta"]):
                                content = chunk["choices"][0]["delta"]["content"]
                                content_parts.append(content)
                                
                        except json.JSONDecodeError:
                            continue
            
            print(f"  Chunks received: {chunks_received}")
            print(f"  Content: {''.join(content_parts)[:100]}...")
            
        except Exception as e:
            print(f"✗ Streaming chat completion failed: {e}")
        
        # 5. 获取统计信息
        print("\n📊 Testing stats endpoint...")
        try:
            response = await client.get(f"{base_url}/lessllm/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"✓ Stats retrieved")
                if "database" in stats:
                    db_stats = stats["database"]
                    print(f"  Total records: {db_stats.get('total_records', 'N/A')}")
                    print(f"  DB size: {db_stats.get('db_size_mb', 0):.2f} MB")
            else:
                print(f"  Stats not available: {response.status_code}")
        except Exception as e:
            print(f"✗ Stats endpoint failed: {e}")


def test_openai_compatibility():
    """测试OpenAI客户端兼容性"""
    print("\n🔌 Testing OpenAI client compatibility...")
    
    try:
        # 这里可以使用真实的OpenAI客户端库来测试兼容性
        import openai
        
        # 设置自定义base_url指向LessLLM
        client = openai.OpenAI(
            api_key="dummy-key",  # LessLLM会使用配置文件中的真实API key
            base_url="http://localhost:8000/v1"
        )
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say hello in one word"}
            ],
            max_tokens=5
        )
        
        print("✓ OpenAI client compatibility test passed")
        print(f"  Response: {response.choices[0].message.content}")
        
    except ImportError:
        print("  OpenAI library not installed, skipping compatibility test")
    except Exception as e:
        print(f"✗ OpenAI client compatibility test failed: {e}")


async def main():
    """主测试函数"""
    print("🚀 LessLLM Proxy Test Suite")
    print(f"Time: {datetime.now().isoformat()}")
    print("="*50)
    
    await test_lessllm_proxy()
    
    print("\n" + "="*50)
    test_openai_compatibility()
    
    print("\n✅ Test suite completed!")
    print("\nNote: Make sure to:")
    print("1. Start LessLLM server: lessllm server --config examples/lessllm.yaml")
    print("2. Set your API keys as environment variables")
    print("3. Configure proxy settings if needed")


if __name__ == "__main__":
    asyncio.run(main())