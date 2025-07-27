# LessLLM 使用指南

LessLLM 是一个轻量级的 LLM API 代理，提供完整的日志记录和分析功能。

## 🚀 快速开始

### 1. 安装和配置

```bash
# 安装开发版本
pip install -e .

# 初始化配置文件
lessllm init

# 编辑配置文件，设置你的 API 密钥
vim lessllm.yaml
```

### 2. 启动服务

#### 默认模式（服务器 + GUI）
```bash
lessllm server --config lessllm.yaml
```
这将启动：
- API 代理服务器：`http://localhost:8000`
- Web 分析界面：`http://localhost:8501`

#### 仅启动服务器（无 GUI）
```bash
lessllm server --config lessllm.yaml --no-gui
```

#### 自定义端口
```bash
lessllm server --config lessllm.yaml --port 9000 --gui-port 9501
```

### 3. 使用 API

```bash
# 健康检查
curl http://localhost:8000/health

# 聊天接口
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-sonnet",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'

# 流式聊天
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-sonnet",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

## 📊 Web 分析界面

访问 `http://localhost:8501` 查看：

### 仪表板功能
- **关键指标**：总请求数、成功率、总成本、Token 使用量
- **性能分析**：TTFT/TPOT 分布、模型性能对比
- **缓存分析**：命中率分布、估算 vs 实际对比
- **成本分析**：按模型的成本和使用分布
- **最近日志**：最新的 API 调用记录

### SQL 查询功能
- 展开 "🔍 自定义 SQL 查询" 区域
- 选择预定义查询模板或自定义 SQL
- 支持结果导出为 CSV

#### 常用 SQL 查询示例

```sql
-- 按模型统计性能
SELECT 
    model,
    COUNT(*) as request_count,
    AVG(estimated_ttft_ms) as avg_ttft_ms,
    AVG(estimated_tpot_ms) as avg_tpot_ms,
    SUM(estimated_cost_usd) as total_cost_usd
FROM api_calls 
WHERE success = true 
GROUP BY model 
ORDER BY request_count DESC;

-- 缓存命中率分析
SELECT 
    model,
    provider,
    AVG(estimated_cache_hit_rate) as avg_estimated_hit_rate,
    AVG(actual_cache_hit_rate) as avg_actual_hit_rate,
    ABS(AVG(actual_cache_hit_rate) - AVG(estimated_cache_hit_rate)) as prediction_error
FROM api_calls 
WHERE actual_cache_hit_rate IS NOT NULL 
GROUP BY model, provider;

-- 错误分析
SELECT 
    provider,
    model,
    error_message,
    COUNT(*) as error_count
FROM api_calls 
WHERE success = false 
GROUP BY provider, model, error_message 
ORDER BY error_count DESC;
```

## 🗄️ 数据管理

### 查看数据
```bash
# 直接查看数据库
python view_db.py

# 清空所有数据
python clear_data.py

# 只清空记录保留结构
python clear_data.py --logs-only
```

### 数据库表结构

主表 `api_calls` 包含：
- **基础信息**：timestamp, request_id, provider, model, endpoint, success
- **原始数据**：完整的请求和响应 JSON
- **性能指标**：TTFT、TPOT、延迟、吞吐量
- **缓存分析**：估算和实际缓存命中率
- **成本估算**：按模型计算的使用成本
- **环境信息**：代理使用情况、用户和会话信息

## ⚙️ 配置选项

### lessllm.yaml 示例
```yaml
providers:
  claude:
    api_key: "your-api-key"
    base_url: "https://api.anthropic.com/v1"
  
  openai:
    api_key: "your-openai-key"  
    base_url: "https://api.openai.com/v1"

proxy:
  # http_proxy: "http://proxy.company.com:8080"
  # socks_proxy: "socks5://127.0.0.1:1080"
  timeout: 30

logging:
  enabled: true
  level: "INFO"
  storage:
    type: "duckdb"
    db_path: "./lessllm_logs.db"

analysis:
  enable_cache_estimation: true
  enable_performance_tracking: true
  cache_estimation_accuracy_threshold: 0.8

server:
  host: "0.0.0.0"
  port: 8000
  workers: 1
```

## 🛠️ 命令参考

### 主要命令

```bash
# 服务器（默认带 GUI）
lessllm server [options]

# 仅启动 GUI
lessllm gui [options]

# 测试连接
lessllm test [--config CONFIG]

# 初始化配置
lessllm init [--output FILE]
```

### 服务器选项

```bash
--host HOST              # 绑定主机 (默认: 0.0.0.0)
--port PORT              # 服务端口 (默认: 8000)
--config CONFIG          # 配置文件路径
--workers WORKERS        # 工作进程数 (默认: 1)
--gui-port GUI_PORT      # GUI 端口 (默认: 8501)
--gui-host GUI_HOST      # GUI 主机 (默认: localhost)
--no-gui                 # 禁用 GUI
```

## 🔍 故障排除

### 常见问题

1. **GUI 无法启动**
   - 确保安装了 streamlit: `pip install streamlit plotly pandas`
   - 检查端口是否被占用

2. **API 调用失败**
   - 检查配置文件中的 API 密钥
   - 验证网络连接和代理设置

3. **数据库问题**
   - 确保有写入权限到数据库目录
   - 尝试删除并重新创建数据库

### 日志查看
- 服务器日志：控制台输出
- 应用日志：查看配置中的日志级别设置
- GUI 日志：在 GUI 界面中查看错误信息

## 📈 性能优化

1. **多进程模式**：`--workers 4` 
2. **缓存优化**：调整 `cache_estimation_accuracy_threshold`
3. **数据库维护**：定期清理旧日志记录
4. **代理配置**：优化网络代理设置

## 🔒 安全注意事项

- 不要在公共网络上暴露服务器端口
- 定期轮换 API 密钥
- 注意日志中的敏感信息
- 使用环境变量存储敏感配置

## 📊 集成使用

LessLLM 可以作为任何支持 OpenAI API 格式的应用的代理：

```python
import openai

# 设置客户端指向 LessLLM 代理
client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="any-key"  # LessLLM 会转发到实际的 API
)

response = client.chat.completions.create(
    model="claude-3-sonnet",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

这样所有的调用都会被 LessLLM 记录和分析！