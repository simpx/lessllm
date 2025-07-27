# LessLLM v0.2.0

> 🚀 A lightweight, enterprise-grade LLM API proxy framework with comprehensive analytics and intelligent routing

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.2.0-green.svg)](https://github.com/simpx/lessllm)

**Do more with less code/gpu/mem**

## ✨ Key Features

### 🎯 Intelligent API Routing
- **Smart Format Conversion**: Seamlessly switch between Claude Messages API and OpenAI Chat Completions API
- **Provider Transparency**: Use any API format with any provider (Claude ↔ OpenAI)
- **Automatic Routing**: Based on model names and endpoint types
- **Streaming Support**: Real-time format conversion for streaming requests

### 📊 Enterprise Analytics
- **100% Data Capture**: Complete HTTP request/response logging to DuckDB
- **Performance Monitoring**: TTFT, TPOT, throughput analysis
- **Cost Tracking**: Token usage and cost estimation per request
- **Cache Analytics**: Cache hit rates and savings calculation
- **Interactive Dashboard**: Web-based analytics with real-time data

### 🔧 Multi-Provider Support
- **Claude (Anthropic)**: Direct Messages API support + Aliyun proxy compatibility
- **OpenAI**: Chat Completions API with full feature parity
- **Extensible**: Easy to add new providers
- **Load Balancing**: Intelligent provider selection

### 🌐 Web Interface
- **Real-time Monitoring**: Live request tracking and analysis
- **Interactive Tables**: Click-to-view detailed request information
- **Data Visualization**: Charts and graphs for usage patterns
- **SQL Query Interface**: Custom analytics with pre-built templates

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