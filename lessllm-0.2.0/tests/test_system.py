#!/usr/bin/env python3
"""
测试脚本：创建示例数据并测试 LessLLM 系统
"""

import asyncio
import json
import httpx
from datetime import datetime, timedelta
import time
import random

async def test_api_call():
    """测试 API 调用"""
    # 启动服务器后的测试请求
    url = "http://localhost:8000/v1/chat/completions"
    
    test_data = {
        "model": "claude-3-sonnet",
        "messages": [
            {"role": "user", "content": "Hello, this is a test message!"}
        ],
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-key"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=test_data, headers=headers, timeout=10.0)
            print(f"API 测试响应状态: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"API 测试成功: {result.get('choices', [{}])[0].get('message', {}).get('content', 'No content')[:100]}...")
            else:
                print(f"API 测试响应: {response.text}")
                
    except Exception as e:
        print(f"API 测试失败: {e}")

def create_sample_data():
    """创建示例数据用于测试"""
    from lessllm.logging.storage import LogStorage
    from lessllm.logging.models import APICallLog, RawAPIData, EstimatedAnalysis, PerformanceAnalysis, CacheAnalysis
    
    # 初始化存储
    storage = LogStorage("./lessllm_logs.db")
    
    print("正在创建示例数据...")
    
    # 创建一些示例日志记录
    models = ["claude-3-sonnet", "claude-3-haiku", "gpt-4", "gpt-3.5-turbo"]
    providers = ["claude", "openai"]
    
    for i in range(50):
        # 随机选择模型和提供商
        model = random.choice(models)
        provider = "claude" if model.startswith("claude") else "openai"
        
        # 生成随机时间戳（过去7天内）
        base_time = datetime.now() - timedelta(days=random.randint(0, 7))
        
        # 生成随机性能数据
        ttft = random.randint(200, 2000)  # 200-2000ms
        tpot = random.uniform(20, 100)    # 20-100ms per token
        total_tokens = random.randint(50, 500)
        latency = ttft + (total_tokens * tpot)
        
        # 生成成本数据
        cost_per_token = 0.00002 if "gpt-3.5" in model else 0.00005
        estimated_cost = total_tokens * cost_per_token
        
        # 生成缓存数据
        cache_hit_rate = random.uniform(0.1, 0.8)
        cached_tokens = int(total_tokens * cache_hit_rate)
        
        # 创建原始数据
        raw_data = RawAPIData(
            raw_request={
                "model": model,
                "messages": [{"role": "user", "content": f"Test message {i}"}],
                "max_tokens": 100
            },
            raw_response={
                "choices": [{"message": {"content": f"Response {i}"}}],
                "usage": {
                    "prompt_tokens": random.randint(10, 100),
                    "completion_tokens": total_tokens - random.randint(10, 100),
                    "total_tokens": total_tokens
                }
            },
            extracted_usage={
                "prompt_tokens": random.randint(10, 100),
                "completion_tokens": total_tokens - random.randint(10, 100), 
                "total_tokens": total_tokens
            }
        )
        
        # 创建估算分析
        estimated_analysis = EstimatedAnalysis(
            estimated_performance=PerformanceAnalysis(
                ttft_ms=ttft,
                tpot_ms=tpot,
                total_latency_ms=int(latency),
                tokens_per_second=1000/tpot if tpot > 0 else 0
            ),
            estimated_cache=CacheAnalysis(
                estimated_cached_tokens=cached_tokens,
                estimated_fresh_tokens=total_tokens - cached_tokens,
                estimated_cache_hit_rate=cache_hit_rate
            ),
            estimated_cost_usd=estimated_cost
        )
        
        # 创建日志记录
        log = APICallLog(
            request_id=f"test_req_{i}",
            provider=provider,
            model=model,
            endpoint="chat/completions",
            raw_data=raw_data,
            estimated_analysis=estimated_analysis,
            success=random.choice([True, True, True, False]),  # 75% 成功率
            timestamp=base_time,
            proxy_used="direct" if random.random() > 0.3 else "socks5://127.0.0.1:1080"
        )
        
        # 设置实际缓存数据（模拟部分记录有真实的缓存信息）
        if random.random() > 0.5:  # 50% 的记录有实际缓存数据
            log.actual_cached_tokens = cached_tokens + random.randint(-10, 10)
            log.actual_cache_hit_rate = cache_hit_rate + random.uniform(-0.1, 0.1)
            log.actual_cache_hit_rate = max(0, min(1, log.actual_cache_hit_rate))
        
        # 存储日志
        storage.store_log(log)
    
    print(f"✅ 已创建 50 条示例数据记录")
    
    # 显示数据库统计
    stats = storage.get_database_stats()
    print(f"数据库统计: {stats['total_records']} 条记录")
    
    return storage

async def main():
    """主测试函数"""
    print("🚀 LessLLM 系统测试")
    print("=" * 50)
    
    # 1. 创建示例数据
    storage = create_sample_data()
    
    # 2. 显示使用说明
    print("\n📋 使用说明:")
    print("1. 启动代理服务器: lessllm server --config lessllm.yaml")
    print("2. 启动 GUI 界面: lessllm gui")
    print("3. 测试 API 调用: curl http://localhost:8000/health")
    print("4. 查看日志数据: python view_db.py")
    
    # 3. 显示快速测试命令
    print("\n🔧 快速测试命令:")
    print("# 检查健康状态")
    print("curl http://localhost:8000/health")
    print("\n# 测试 API 调用")
    print('curl -X POST http://localhost:8000/v1/chat/completions \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"model": "claude-3-sonnet", "messages": [{"role": "user", "content": "Hello!"}]}\'')
    
    print("\n✅ 测试完成！")
    print("现在你可以:")
    print("1. 运行 'lessllm server' 启动代理服务器")
    print("2. 运行 'lessllm gui' 查看 Web 界面和日志")
    print("3. 使用 SQL 查询功能分析数据")

if __name__ == "__main__":
    asyncio.run(main())