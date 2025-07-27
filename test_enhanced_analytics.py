#!/usr/bin/env python3
"""
测试增强的分析功能 - 生成示例数据
"""

import sys
import os
import time
import random
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from lessllm.logging.storage import LogStorage
from lessllm.logging.models import APICallLog, RawAPIData, EstimatedAnalysis, PerformanceAnalysis, CacheAnalysis

def generate_sample_data(storage: LogStorage, num_requests: int = 20):
    """生成示例数据用于测试分析功能"""
    
    print(f"生成 {num_requests} 个示例请求数据...")
    
    providers = ["claude", "openai"]
    models = [
        "claude-3-5-sonnet-20241022",
        "claude-3-haiku-20240307",
        "gpt-4",
        "gpt-3.5-turbo"
    ]
    endpoints = ["messages", "chat/completions"]
    
    base_time = datetime.now() - timedelta(hours=24)
    
    for i in range(num_requests):
        provider = random.choice(providers)
        model = random.choice(models)
        endpoint = random.choice(endpoints)
        
        # 模拟真实的token使用模式
        prompt_tokens = random.randint(10, 500)
        completion_tokens = random.randint(5, 200)
        total_tokens = prompt_tokens + completion_tokens
        
        # 模拟缓存数据 (30%的请求有缓存)
        has_cache = random.random() < 0.3
        cached_tokens = random.randint(0, prompt_tokens // 2) if has_cache else 0
        cache_hit_rate = cached_tokens / prompt_tokens if prompt_tokens > 0 and has_cache else 0
        
        # 模拟性能数据
        ttft_ms = random.randint(100, 1000)
        tpot_ms = random.uniform(10, 50)
        total_latency = ttft_ms + (completion_tokens * tpot_ms)
        tokens_per_second = completion_tokens / (total_latency / 1000) if total_latency > 0 else 0
        
        # 模拟成本 (简化计算)
        cost_per_1k_input = 0.003 if "claude" in model else 0.0015
        cost_per_1k_output = 0.015 if "claude" in model else 0.002
        estimated_cost = (prompt_tokens * cost_per_1k_input + completion_tokens * cost_per_1k_output) / 1000
        
        # 创建请求数据
        request_data = {
            "model": model,
            "messages": [{"role": "user", "content": f"Test request {i+1}"}],
            "max_tokens": completion_tokens,
            "stream": random.choice([True, False])
        }
        
        # 创建响应数据
        response_data = {
            "type": "message" if endpoint == "messages" else "chat.completion",
            "content": [{"type": "text", "text": f"This is test response {i+1}"}],
            "usage": {
                "input_tokens": prompt_tokens,
                "output_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
        }
        
        # 创建原始数据
        raw_data = RawAPIData(
            raw_request=request_data,
            raw_response=response_data,
            extracted_usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            },
            extracted_cache_info={
                "cached_tokens": cached_tokens,
                "cache_hit_rate": cache_hit_rate
            } if has_cache else None,
            # HTTP信息
            request_headers={"content-type": "application/json", "user-agent": "test-client"},
            client_ip="127.0.0.1",
            user_agent="test-client/1.0",
            request_url=f"http://localhost:8000/v1/{endpoint}",
            request_method="POST",
            response_status_code=200,
            response_headers={"content-type": "application/json"}
        )
        
        # 创建性能分析
        performance_analysis = PerformanceAnalysis(
            ttft_ms=ttft_ms,
            tpot_ms=tpot_ms,
            total_latency_ms=int(total_latency),
            tokens_per_second=round(tokens_per_second, 2)
        )
        
        # 创建缓存分析
        cache_analysis = CacheAnalysis(
            estimated_cache_hit_rate=cache_hit_rate if has_cache else 0.0,
            estimated_cached_tokens=cached_tokens if has_cache else 0,
            estimated_fresh_tokens=prompt_tokens - cached_tokens if has_cache else prompt_tokens
        )
        
        # 创建估算分析
        estimated_analysis = EstimatedAnalysis(
            estimated_performance=performance_analysis,
            estimated_cache=cache_analysis,
            estimated_cost_usd=estimated_cost
        )
        
        # 创建API调用日志
        log = APICallLog(
            request_id=f"test_req_{i+1:04d}_{int(time.time()*1000)}",
            provider=provider,
            model=model,
            endpoint=endpoint,
            raw_data=raw_data,
            estimated_analysis=estimated_analysis,
            success=random.random() > 0.05,  # 95%成功率
            error_message=None if random.random() > 0.05 else f"Test error {i+1}",
            timestamp=base_time + timedelta(minutes=i*30)
        )
        
        # 存储到数据库
        storage.store_log(log)
        print(f"✅ 生成请求 {i+1}/{num_requests}: {provider}/{model} - {prompt_tokens}+{completion_tokens}={total_tokens} tokens")
    
    print(f"\n🎉 成功生成 {num_requests} 个示例请求!")

def main():
    """主函数"""
    print("🧪 LessLLM 增强分析功能测试")
    print("=" * 50)
    
    # 初始化存储
    try:
        storage = LogStorage("./lessllm_logs.db")
        print("✅ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return
    
    # 生成示例数据
    try:
        generate_sample_data(storage, num_requests=30)
    except Exception as e:
        print(f"❌ 数据生成失败: {e}")
        return
    
    print("\n📊 测试建议:")
    print("1. 启动GUI: streamlit run gui/dashboard.py")
    print("2. 查看关键指标部分的新统计数据")
    print("3. 检查请求列表中的新列显示")
    print("4. 尝试新的SQL查询模板")
    print("5. 观察数据可视化图表")
    
    print("\n🔍 可测试的新功能:")
    print("- Token详细统计 (输入/输出/缓存)")
    print("- 缓存效率分析")
    print("- 成本效率排行")
    print("- 性能趋势图表")
    print("- Provider和模型使用分布")

if __name__ == "__main__":
    main()