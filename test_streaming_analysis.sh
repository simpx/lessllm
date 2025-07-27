#!/bin/bash

# Streaming mode analysis test

echo "=== LessLLM 流式模式支持分析 ==="
echo ""

BASE_URL="http://localhost:8000"

echo "1. Testing direct Aliyun streaming (for comparison)..."
echo "直接测试阿里云流式响应格式："
echo ""

curl -X POST "https://dashscope.aliyuncs.com/api/v2/apps/claude-code-proxy/v1/messages" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-001061f9c18447ecbed88b9bb6d87871" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 50,
    "stream": true,
    "messages": [
      {
        "role": "user",
        "content": "Count from 1 to 3, explaining each number"
      }
    ]
  }' \
  --no-buffer | head -20

echo -e "\n\n2. Testing LessLLM streaming proxy (when server is running)..."
echo "注意：此测试需要先启动 lessllm server"
echo ""

echo "curl -X POST \"${BASE_URL}/v1/messages\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{"
echo "    \"model\": \"claude-3-5-sonnet-20241022\","
echo "    \"max_tokens\": 50,"
echo "    \"stream\": true,"
echo "    \"messages\": ["
echo "      {"
echo "        \"role\": \"user\","
echo "        \"content\": \"Count from 1 to 3, explaining each number\""
echo "      }"
echo "    ]"
echo "  }' \\"
echo "  --no-buffer"

echo -e "\n\n=== 流式模式技术分析 ==="
echo ""

cat << 'EOF'
📊 LessLLM 流式支持架构：

1. 🔄 请求流程：
   客户端 → LessLLM(/v1/messages?stream=true) → Provider → 实时流回客户端

2. 📡 数据捕获：
   - 每个chunk都被实时记录到response_chunks[]
   - 同时转发给客户端(yield)
   - 完成后重构完整响应用于数据库存储

3. ⏱️ 性能监控：
   - TTFT (Time To First Token): 第一个token到达时间
   - TPOT (Time Per Output Token): 每个token平均生成时间  
   - Tokens/Second: 实时吞吐量计算
   - 每个chunk调用 performance_tracker.record_token()

4. 💾 数据存储机制：
   流式请求 → 重构完整响应 → 异步存储到DuckDB
   
   存储的数据包括：
   - raw_request: 原始请求
   - raw_response: 重构的完整响应 {"choices":[{"message":{"content":"完整文本"}}]}
   - chunk_count: 流式chunk数量
   - performance_metrics: TTFT, TPOT, 总延迟
   - 完整HTTP信息: headers, IP, user-agent等

5. 🎯 在GUI中看到的内容：
   📤 请求数据: 完整的流式请求JSON
   📥 响应数据: 重构后的完整响应(非chunk格式)
   🌐 HTTP详情: 所有请求/响应头
   📊 性能指标: TTFT、TPOT、tokens/s、总延迟
   💰 成本分析: 基于总token使用量的估算

6. 🔧 智能路由的流式支持：
   - Claude Messages + Claude Provider: 直接透传stream
   - Claude Messages + OpenAI Provider: 转换成OpenAI stream再转回Claude格式
   - OpenAI Chat + OpenAI Provider: 直接透传stream  
   - OpenAI Chat + Claude Provider: 转换成Claude stream再转回OpenAI格式

关键特点：
✅ 实时性能监控(TTFT/TPOT)
✅ 完整数据记录(100%信息保存)
✅ 智能格式转换(支持跨provider流式)
✅ GUI友好显示(完整响应而非chunks)
EOF

echo ""
echo "=== 测试建议 ==="
echo "1. 启动服务器: lessllm server --config lessllm.yaml"  
echo "2. 运行流式测试，观察日志记录"
echo "3. 在GUI中查看请求详情，对比流式vs非流式的差异"
echo "4. 关注性能指标中的TTFT和TPOT数值"