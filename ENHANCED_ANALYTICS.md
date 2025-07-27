# LessLLM 增强数据分析功能

## 🚀 新增功能概览

### 📊 增强的表格显示

#### 新增列信息
| 列名 | 显示名称 | 说明 | 格式化 |
|------|----------|------|--------|
| `endpoint` | 端点 | API端点类型 | messages/chat/completions |
| `actual_prompt_tokens` | 输入Token | 实际输入token数量 | 1,234 格式 |
| `actual_completion_tokens` | 输出Token | 实际输出token数量 | 1,234 格式 |
| `actual_total_tokens` | 总Token | 总token数量 | 1,234 格式 |
| `actual_cached_tokens` | 缓存Token | 缓存的token数量 | 1,234 格式 |
| `actual_cache_hit_rate` | 缓存率 | 缓存命中率 | 85.5% 格式 |
| `estimated_tpot_ms` | TPOT | 每token时间 | 12.5ms 格式 |
| `estimated_tokens_per_second` | 吞吐量 | 处理速度 | 49.2 t/s 格式 |
| `success` | 状态 | 请求成功状态 | ✅/❌ 图标 |

### 📈 三层关键指标展示

#### 第一层：基础指标
- **总请求数**: 所有请求总数
- **成功率**: 成功请求百分比
- **成功数**: 成功请求数量
- **总成本**: 累计成本 (USD)
- **总Token**: 所有token使用量

#### 第二层：Token分析
- **输入Token**: 所有输入token总和
- **输出Token**: 所有输出token总和  
- **缓存Token**: 缓存节省的token总和
- **平均缓存率**: 整体缓存命中率
- **缓存节省**: 估算缓存节省的成本

#### 第三层：性能指标
- **平均TTFT**: 首字节到达时间平均值
- **平均TPOT**: 每token生成时间平均值
- **平均吞吐量**: tokens/秒平均值
- **Provider数**: 使用的provider数量
- **模型数**: 使用的模型种类数

### 📊 数据可视化

#### 1. Provider使用分布 (饼图)
- 显示各provider的请求数量分布
- 直观了解流量分配

#### 2. 成本分布按模型 (柱状图)
- 按模型显示成本消耗
- 识别高成本模型

#### 3. Token使用趋势 (折线图)
- 时间轴上的token使用变化
- 识别使用模式和峰值

#### 4. TTFT性能趋势 (折线图)
- 响应时间性能变化
- 监控性能退化

### 🔍 增强的SQL查询模板

#### 1. Token分析 - 详细统计
```sql
SELECT 
    model, provider,
    COUNT(*) as request_count,
    SUM(actual_prompt_tokens) as total_input_tokens,
    SUM(actual_completion_tokens) as total_output_tokens,
    SUM(actual_total_tokens) as total_tokens,
    SUM(actual_cached_tokens) as total_cached_tokens,
    AVG(actual_cache_hit_rate) as avg_cache_rate,
    SUM(estimated_cost_usd) as total_cost_usd,
    AVG(actual_total_tokens) as avg_tokens_per_request
FROM api_calls 
WHERE success = true 
GROUP BY model, provider 
ORDER BY total_tokens DESC
```

#### 2. 缓存效率分析
```sql
SELECT 
    model, provider,
    COUNT(*) as request_count,
    AVG(actual_cache_hit_rate) as avg_cache_rate,
    SUM(actual_cached_tokens) as total_cached_tokens,
    SUM(actual_cached_tokens) * 0.0001 as estimated_cache_savings,
    AVG(estimated_ttft_ms) as avg_ttft_ms
FROM api_calls 
WHERE success = true AND actual_cache_hit_rate IS NOT NULL
GROUP BY model, provider 
ORDER BY avg_cache_rate DESC
```

#### 3. 成本效率排行
```sql
SELECT 
    model, provider,
    COUNT(*) as request_count,
    SUM(estimated_cost_usd) as total_cost,
    SUM(actual_total_tokens) as total_tokens,
    (SUM(estimated_cost_usd) / SUM(actual_total_tokens) * 1000) as cost_per_1k_tokens,
    AVG(estimated_cost_usd) as avg_cost_per_request
FROM api_calls 
WHERE success = true AND actual_total_tokens > 0
GROUP BY model, provider 
ORDER BY cost_per_1k_tokens ASC
```

## 🧪 测试和验证

### 示例数据生成
```bash
# 生成30个示例请求用于测试
python3 ./test_enhanced_analytics.py
```

### 功能验证清单

#### ✅ 表格增强功能
- [x] 新增Token相关列显示
- [x] 缓存数据可视化
- [x] 性能指标完整展示
- [x] 状态图标化显示
- [x] 数值格式化处理

#### ✅ 统计指标增强
- [x] 三层指标体系
- [x] Token详细分析
- [x] 缓存效率统计
- [x] 性能平均值计算
- [x] 成本分析增强

#### ✅ 数据可视化
- [x] Provider分布饼图
- [x] 模型成本柱状图
- [x] Token使用趋势图
- [x] 性能趋势图

#### ✅ SQL查询增强
- [x] Token分析模板
- [x] 缓存效率模板
- [x] 成本效率模板
- [x] 性能分析模板

## 📋 实际使用场景

### 1. 成本优化
- 通过成本效率排行识别最经济的模型组合
- 监控高成本请求和模型
- 评估缓存节省效果

### 2. 性能监控
- TTFT/TPOT趋势分析
- 识别性能退化
- 吞吐量优化

### 3. 缓存分析
- 缓存命中率监控
- 缓存token节省量统计
- 缓存策略效果评估

### 4. 流量分析
- Provider使用分布
- 模型选择偏好
- 端点使用模式

### 5. 故障排查
- 失败请求分析
- 性能异常定位
- 成本异常调查

## 🔄 启动和测试

### 1. 生成测试数据
```bash
python3 ./test_enhanced_analytics.py
```

### 2. 启动分析界面
```bash
# 方法1: 直接启动GUI
streamlit run gui/dashboard.py

# 方法2: 通过服务器启动
lessllm server --gui-port 8501 --config lessllm.yaml
```

### 3. 访问和验证
- 打开 http://localhost:8501
- 查看关键指标的三层显示
- 验证表格新列的正确显示
- 测试新的SQL查询模板
- 观察数据可视化图表

## 💡 使用建议

### 监控重点
1. **成本控制**: 关注 cost_per_1k_tokens 指标
2. **性能优化**: 监控 TTFT 和吞吐量趋势
3. **缓存效率**: 提升缓存命中率以降低成本
4. **故障分析**: 使用详细的HTTP信息排查问题

### 分析技巧
1. **对比分析**: 使用 GROUP BY 对比不同模型/provider
2. **趋势分析**: 使用时间序列查询识别模式
3. **异常检测**: 筛选高成本/低性能请求
4. **优化建议**: 基于数据选择最优配置

增强后的分析功能提供了enterprise级别的LLM使用洞察，帮助优化成本、性能和用户体验！