# LessLLM 需求分析与使用场景

## 项目定位

LessLLM 是一个轻量级的 LLM API 代理框架，专注于解决 **网络连通性** 和 **API使用分析** 两大核心痛点。项目秉承 "doing more with less code/gpu/mem" 的理念，为开发者提供简单高效的 LLM 使用体验。

## 核心需求

### 1. 网络连通性问题 🌐

**痛点**: 在受限网络环境下无法直接访问 LLM API 服务

**需求细节**:
- 支持 HTTP/HTTPS 代理
- 支持 SOCKS4/5 代理  
- 代理认证支持（用户名密码）
- 连接池管理和超时控制
- 代理失败时的错误提示和回退机制

**目标用户**: 
- 企业环境开发者
- 网络受限地区的用户
- 需要通过代理访问外部服务的团队

### 2. API使用分析需求 📊

**痛点**: 缺乏对 LLM API 使用情况的深度洞察，难以优化成本和性能

**需求细节**:

#### 完整的调用记录
- 记录完整的请求/响应数据（JSON格式）
- 支持 OpenAI 和 Claude API 格式
- 请求元数据：时间戳、模型、用户ID等
- 响应数据：token使用量、成本、错误信息等

#### 性能指标收集
- **TTFT (Time To First Token)**: 响应实时性指标
- **TPOT (Time Per Output Token)**: 生成速度指标  
- **总延迟**: 端到端响应时间
- **流式 vs 非流式**: 不同模式的性能对比
- **网络延迟分解**: 区分网络和计算时间

#### 智能缓存分析
- **预估缓存命中**: 基于 prompt 内容预测缓存效果
- **实际缓存对比**: 与 API 返回的真实缓存数据对比
- **缓存优化建议**: 识别可优化的 prompt 模式
- **成本影响分析**: 缓存对成本的影响量化

### 3. 数据持久化需求 💾

**痛点**: 需要灵活的数据存储方案，便于后续分析

**需求细节**:
- 本地化存储（无需额外基础设施）
- 支持 SQL 查询（便于复杂分析）
- 数据导出功能（Parquet 格式，pandas 友好）
- 轻量级数据库（DuckDB）
- 保持 lessllm 简单，让用户在外部系统做深度分析

## 主要使用场景

### 场景1: AI工具开发团队

**背景**: 某 AI 工具开发团队需要在不同 LLM 间切换以找到最适合的模型

**具体痛点**:
- 每个模型 API 格式不同，切换成本高
- 无法统一监控所有模型的使用情况  
- 测试时需要频繁修改代码
- 网络环境可能无法直接访问某些 API

**lessllm 解决方案**:
```python
# 开发者只需要修改配置，无需改代码
# 配置文件 lessllm.yaml
proxy:
  socks_proxy: "socks5://127.0.0.1:1080" 
  
models:
  "gpt-4": 
    provider: "openai"
    model: "gpt-4-0613"
  "claude": 
    provider: "anthropic" 
    model: "claude-3-opus-20240229"

# 应用代码保持不变
client = openai.OpenAI(base_url="http://localhost:8000/v1")
response = client.chat.completions.create(
    model="claude",  # 实际会路由到Claude API
    messages=[{"role": "user", "content": "Hello"}]
)
```

**价值体现**:
- 统一接口，无需修改业务代码
- 完整的使用数据记录，便于模型选择决策
- 解决网络连通性问题

### 场景2: 企业内部AI应用

**背景**: 大型企业内部多个部门都在使用 LLM，需要统一管理和监控

**具体痛点**:
- 各部门使用不同模型，成本难以控制
- 无法监控敏感数据是否泄漏
- 网络安全要求，需要通过代理访问外部 API
- 缺乏使用效率分析

**lessllm 解决方案**:
```python
# 企业级使用
import lessllm

# 配置代理和日志
lessllm.configure({
    "proxy": {
        "http_proxy": "http://proxy.company.com:8080",
        "auth": {
            "username": "${PROXY_USER}",
            "password": "${PROXY_PASS}"
        }
    },
    "logging": {
        "enabled": True,
        "storage": "duckdb",
        "db_path": "/shared/ai_usage_logs.db"
    }
})

# 正常使用，自动记录所有调用
client = openai.OpenAI(base_url="http://localhost:8000/v1")
response = client.chat.completions.create(...)

# 管理员分析使用情况
usage_report = lessllm.query("""
    SELECT 
        model,
        COUNT(*) as calls,
        SUM(estimated_cost_usd) as total_cost,
        AVG(estimated_cache_hit_rate) as avg_cache_hit_rate
    FROM api_calls 
    WHERE timestamp >= '2024-01-01'
    GROUP BY model
""")
```

**价值体现**:
- 解决企业网络环境的连通性问题
- 提供详细的使用量和成本分析
- 支持集中化的使用监控和管理

### 场景3: AI研究和模型比较

**背景**: 研究人员需要比较不同模型在相同任务上的表现

**具体痛点**:
- 需要同时调用多个模型 API
- 结果格式不统一，难以比较
- 无法方便地记录实验数据
- 缺乏性能和效率的量化指标

**lessllm 解决方案**:
```python
# 研究实验设置
models_to_test = ["gpt-4", "claude-3-opus", "gemini-pro"]
test_prompts = [...]

results = []
for model in models_to_test:
    for prompt in test_prompts:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            # lessllm自动记录所有请求详情
        )
        results.append({
            "model": model,
            "prompt": prompt,
            "response": response.choices[0].message.content
        })

# 自动生成实验报告
experiment_data = lessllm.query("""
    SELECT 
        model,
        AVG(estimated_ttft_ms) as avg_ttft,
        AVG(estimated_tpot_ms) as avg_tpot,
        AVG(estimated_cache_hit_rate) as avg_cache_hit,
        AVG(estimated_cost_usd) as avg_cost
    FROM api_calls 
    WHERE timestamp >= '2024-01-01'
    GROUP BY model
""")

# 导出详细数据用于进一步分析
lessllm.export_logs("experiment_results.parquet")
```

**价值体现**:
- 统一的API接口，便于批量测试
- 自动收集性能和成本数据
- 结构化的实验数据记录

### 场景4: 开发调试和性能优化

**背景**: 开发者在调试 LLM 应用时需要详细的请求信息

**具体痛点**:
- 难以复现特定的 API 调用问题
- 不知道哪些 prompt 导致了高成本
- 无法分析响应时间瓶颈
- 缺乏缓存优化的量化指标

**lessllm 解决方案**:
```python
# 开启详细调试模式
lessllm.config.debug_mode = True
lessllm.config.enable_cache_analysis = True

# 所有请求都会被详细记录
response = client.chat.completions.create(
    model="gpt-4",
    messages=[...],
    # lessllm自动记录:
    # - 完整的请求/响应
    # - 性能指标(TTFT/TPOT)
    # - 缓存分析
    # - 网络延迟分解
)

# 性能分析查询
performance_issues = lessllm.query("""
    SELECT 
        request_id,
        model,
        estimated_ttft_ms,
        estimated_tpot_ms,
        estimated_cache_hit_rate,
        actual_cache_hit_rate
    FROM api_calls 
    WHERE estimated_ttft_ms > 5000  -- 找出响应慢的请求
    ORDER BY timestamp DESC
""")

# 缓存优化分析
cache_optimization = lessllm.query("""
    SELECT 
        model,
        AVG(estimated_cache_hit_rate) as predicted_hit_rate,
        AVG(actual_cache_hit_rate) as actual_hit_rate,
        (AVG(actual_cache_hit_rate) - AVG(estimated_cache_hit_rate)) as hit_rate_diff
    FROM api_calls 
    WHERE actual_cache_hit_rate IS NOT NULL
    GROUP BY model
""")
```

**价值体现**:
- 完整的调试信息记录
- 性能瓶颈识别和分析
- 缓存优化的量化指导

## 典型用法模式

### 1. 作为代理服务器使用

```bash
# 启动 lessllm 代理服务器
lessllm server --port 8000 --config lessllm.yaml

# 应用程序连接到 lessllm
export OPENAI_BASE_URL="http://localhost:8000/v1"
python my_ai_app.py
```

### 2. 作为 Python 库集成

```python
import lessllm
import openai

# 配置 lessllm
lessllm.configure({
    "proxy": {"socks_proxy": "socks5://127.0.0.1:1080"},
    "logging": {"enabled": True}
})

# 正常使用 OpenAI 客户端
client = openai.OpenAI(base_url=lessllm.get_proxy_url())
response = client.chat.completions.create(...)

# 查询使用情况
stats = lessllm.get_usage_stats(days=7)
```

### 3. 数据分析和导出

```python
# SQL 查询分析
results = lessllm.query("""
    SELECT model, date(timestamp) as date, 
           sum(actual_total_tokens) as daily_tokens,
           avg(estimated_cache_hit_rate) as avg_cache_hit
    FROM api_calls 
    GROUP BY model, date(timestamp)
    ORDER BY date DESC
""")

# 导出到 Parquet 文件用于深度分析
lessllm.export_logs(
    filepath="ai_usage_analysis.parquet",
    start_date="2024-01-01",
    filters={"model": ["gpt-4", "claude-3-opus"]}
)

# 在 pandas 中进行分析
import pandas as pd
df = pd.read_parquet("ai_usage_analysis.parquet")
```

## 核心设计原则

### 1. 简单性优先
- 最小化依赖，避免复杂的基础设施要求
- 开箱即用，配置简单
- 保持 lessllm 功能聚焦，复杂分析留给外部工具

### 2. 数据完整性
- 完整保存原始 API 请求和响应
- 区分原始数据和预估分析
- 支持数据溯源和验证

### 3. 性能和成本意识
- 提供性能和成本的量化指标
- 智能缓存分析，帮助优化使用策略
- 支持使用模式的深度分析

### 4. 可扩展性
- 支持多种 LLM 提供商
- 灵活的配置系统
- 便于集成的 API 设计

## 项目价值

LessLLM 不仅解决了网络连通性这一基础问题，更重要的是提供了 **LLM 使用的性能和成本优化工具**。通过详细的数据记录和智能分析，帮助用户：

1. **优化模型选择** - 基于性能和成本数据做出数据驱动的决策
2. **改进 prompt 设计** - 基于缓存分析优化提示词策略  
3. **监控服务质量** - 基于性能指标趋势发现问题
4. **控制使用成本** - 通过使用量分析和预算管理

这使得 LessLLM 成为 LLM 应用开发和运维中不可或缺的工具。