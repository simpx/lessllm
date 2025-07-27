# LessLLM 流式模式完整支持说明

## 🔄 流式处理架构

### 基本流程
```
客户端请求(stream=true) 
    ↓
LessLLM接收并路由
    ↓  
Provider返回stream chunks
    ↓
实时转发 + 数据收集
    ↓
重构完整响应 + 异步存储
```

## 📊 性能监控机制

### 关键指标实时计算
- **TTFT (Time To First Token)**: 从请求开始到第一个token到达的时间
- **TPOT (Time Per Output Token)**: 平均每个token的生成时间
- **Tokens/Second**: 实时吞吐量
- **Total Latency**: 总请求时间

### 实现细节
```python
# 每个chunk到达时调用
performance_tracker.record_token()

# 最终计算指标
performance_metrics = performance_tracker.calculate_metrics(chunk_count)
```

## 💾 数据存储策略

### 流式请求的数据处理

#### 1. 实时数据收集
```python
response_chunks = []        # 保存所有chunks
full_response = {"choices": [{"message": {"content": ""}}]}

async for chunk in provider.send_streaming_request(request_data):
    performance_tracker.record_token()    # 性能监控
    response_chunks.append(chunk)         # 保存chunk
    
    # 重构完整内容
    if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
        full_response["choices"][0]["message"]["content"] += chunk["choices"][0]["delta"]["content"]
    
    yield f"data: {chunk}\n\n"           # 实时转发
```

#### 2. 异步数据库存储
```python
# 流式结束后异步存储
asyncio.create_task(record_streaming_log(
    request_data,           # 原始请求
    full_response,          # 重构的完整响应
    provider, 
    provider_name,
    request_id,
    performance_tracker,    # 性能数据
    len(response_chunks),   # chunk数量
    http_context           # HTTP详情
))
```

## 🎯 GUI中的显示内容

当你发送一个流式请求后，在请求详情中会看到：

### 📤 请求数据 Tab
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 100,
  "stream": true,              // ← 显示这是流式请求
  "messages": [
    {
      "role": "user", 
      "content": "Count from 1 to 3"
    }
  ]
}
```

### 📥 响应数据 Tab
**注意：这里显示的是重构后的完整响应，不是原始chunks**
```json
{
  "type": "message",
  "role": "assistant", 
  "model": "claude-3-5-sonnet-20241022",
  "content": [
    {
      "type": "text",
      "text": "1. One - This is the first number in the sequence.\n2. Two - This follows one and represents the second position.\n3. Three - This is the third and final number as requested."
    }
  ],
  "usage": {
    "input_tokens": 15,
    "output_tokens": 32
  }
}
```

### 🌐 HTTP 详情 Tab
```json
{
  "request_method": "POST",
  "client_ip": "127.0.0.1",
  "response_status_code": 200,
  "response_headers": {
    "content-type": "text/event-stream"    // ← 流式响应类型
  },
  "response_size_bytes": 847,              // ← 重构响应的大小
  "request_headers": {
    "content-type": "application/json",
    "user-agent": "curl/7.81.0"
  }
}
```

### 📊 性能指标 Tab
```
首字节时间 (TTFT): 245ms        // ← 流式特有指标
每token时间 (TPOT): 12.5ms       // ← 流式特有指标  
总延迟: 650ms
吞吐量: 49.2 tokens/s            // ← 流式特有指标
```

### 💰 成本分析 Tab
```
估算成本: $0.0008
输入Token: 15
输出Token: 32
总Token: 47
```

## 🔧 智能路由的流式支持

### 4种路由场景的流式处理

#### 1. Claude Messages + Claude Provider (直接透传)
```python
# 直接转发Claude流格式
async for chunk in provider.send_claude_messages_streaming_request(request_data):
    yield f"data: {json.dumps(chunk)}\n\n"
```
**Client收到**: Claude原生SSE格式

#### 2. Claude Messages + OpenAI Provider (格式转换)
```python
# 转换: Claude请求 → OpenAI请求 → OpenAI流 → Claude流格式
async for openai_chunk in provider.send_streaming_request(openai_request):
    claude_chunk = convert_openai_streaming_to_claude(openai_chunk)
    yield f"data: {json.dumps(claude_chunk)}\n\n"
```
**Client收到**: 转换后的Claude SSE格式

#### 3. OpenAI Chat + OpenAI Provider (直接透传)
```python
# 直接转发OpenAI流格式
async for chunk in provider.send_streaming_request(request_data):
    yield f"data: {json.dumps(chunk)}\n\n"
```
**Client收到**: OpenAI原生SSE格式

#### 4. OpenAI Chat + Claude Provider (格式转换)
```python
# 转换: OpenAI请求 → Claude请求 → Claude流 → OpenAI流格式  
async for claude_chunk in provider.send_streaming_request(claude_request):
    openai_chunk = convert_claude_streaming_to_openai(claude_chunk)
    yield f"data: {json.dumps(openai_chunk)}\n\n"
```
**Client收到**: 转换后的OpenAI SSE格式

## 🎮 实际使用体验

### 客户端视角
- **实时响应**: 每个token立即到达，无延迟
- **格式透明**: 无论后端provider是什么，都能获得期望的API格式
- **性能一致**: 转换开销极小，基本不影响流式体验

### 开发者视角  
- **完整监控**: GUI中可查看所有流式请求的详细性能数据
- **调试友好**: 重构后的完整响应便于分析内容
- **成本透明**: 精确的token计算和成本估算

## 🚀 测试流式功能

### 基础测试
```bash
# 1. 启动服务器
lessllm server --config lessllm.yaml

# 2. 发送流式请求
curl -X POST "http://localhost:8000/v1/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 100,
    "stream": true,
    "messages": [{"role": "user", "content": "Count slowly from 1 to 5"}]
  }' \
  --no-buffer

# 3. 观察GUI中的记录
# 打开 http://localhost:8501 查看请求详情
```

### 高级测试
```bash
# 测试跨格式转换的流式
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 100, 
    "stream": true,
    "messages": [{"role": "user", "content": "Write a short poem"}]
  }' \
  --no-buffer
```

## ✨ 流式模式的优势

1. **实时体验**: 用户立即看到响应开始
2. **性能洞察**: 精确的TTFT/TPOT监控
3. **格式兼容**: 支持任意API格式 + 任意Provider组合
4. **完整记录**: 不丢失任何调试信息
5. **成本控制**: 实时token使用量监控

流式模式是LessLLM的核心功能之一，提供了enterprise级别的监控和分析能力！