# LessLLM

> A lightweight LLM API proxy framework with network connectivity and usage analysis

**Do more with less code/gpu/mem**

## Overview

LessLLM is a lightweight Python framework that acts as a proxy for LLM APIs, designed to solve network connectivity issues and provide comprehensive usage analysis.

## Key Features

🌐 **Network Connectivity**
- HTTP/HTTPS proxy support
- SOCKS4/5 proxy support
- Proxy authentication
- Connection pooling and timeout control

📊 **Usage Analysis**
- Complete API request/response logging
- Performance metrics (TTFT/TPOT)
- Intelligent cache analysis
- Cost estimation and tracking
- DuckDB storage with SQL queries

🔌 **API Compatibility**
- OpenAI API compatible
- Claude/Anthropic API support
- Streaming and non-streaming requests
- Multiple provider support

## Quick Start

### Installation

```bash
pip install -e .
```

### Initialize Configuration

```bash
lessllm init --output lessllm.yaml
```

### Start the Proxy Server

```bash
# Set your API keys
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-claude-key"

# Start server
lessllm server --config lessllm.yaml --port 8000
```

### Start the Analytics Dashboard GUI

```bash
# Start GUI (requires optional GUI dependencies)
pip install -e .[gui]
lessllm gui --port 8501 --host localhost
```

### Use with OpenAI Client

```python
import openai

# Point OpenAI client to LessLLM proxy
client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"  # LessLLM uses configured keys
)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## Configuration

Create a `lessllm.yaml` configuration file:

```yaml
proxy:
  socks_proxy: "socks5://127.0.0.1:1080"  # Optional
  timeout: 30

providers:
  openai:
    api_key: "${OPENAI_API_KEY}"
  claude:
    api_key: "${ANTHROPIC_API_KEY}"

logging:
  enabled: true
  storage:
    type: "duckdb"
    db_path: "./lessllm_logs.db"

analysis:
  enable_cache_estimation: true
  enable_performance_tracking: true
```

## Project Status

**Current Implementation Status:**

✅ Core Framework
- ✅ Configuration management system
- ✅ FastAPI proxy server
- ✅ Network proxy support (HTTP/SOCKS)
- ✅ Provider abstraction layer

✅ API Support
- ✅ OpenAI provider implementation
- ✅ Claude provider implementation
- ✅ Streaming and non-streaming support

✅ Logging & Analysis
- ✅ DuckDB storage system
- ✅ Performance tracking (TTFT/TPOT)
- ✅ Cache estimation algorithms
- ✅ Cost calculation utilities

✅ Developer Tools
- ✅ CLI interface
- ✅ Example configurations
- ✅ Test client scripts
- ✅ Analytics dashboard GUI

## Next Steps

🔄 **In Progress:**
- Unit tests and integration tests
- Documentation improvements
- Performance optimizations

📋 **Planned:**
- More LLM provider integrations
- Advanced caching strategies
- Batch request optimization

## License

MIT License