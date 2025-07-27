# LessLLM v0.2.0 Quick Start Guide

## 🚀 Installation

```bash
# Install LessLLM
./install.sh

# Or manually:
pip install -e .
```

## ⚙️ Configuration

```bash
# Copy example configuration
cp lessllm.yaml.example lessllm.yaml

# Edit with your API keys
nano lessllm.yaml
```

## 🏃 Running

```bash
# Start server with GUI
lessllm server --config lessllm.yaml --gui-port 8501

# Access services:
# - API Server: http://localhost:8000
# - Analytics GUI: http://localhost:8501
```

## 🧪 Testing

```bash
# Generate sample data
python3 tests/test_enhanced_analytics.py

# Test basic functionality
./tests/test_basic_functionality.sh

# Test direct provider access
./tests/test_aliyun_claude.sh
```

## 📊 Key Features

- **Intelligent API Routing**: Use any API format with any provider
- **Real-time Analytics**: Comprehensive token, cost, and performance tracking
- **Interactive Dashboard**: Web-based monitoring and analysis
- **Streaming Support**: Real-time format conversion for streaming requests

## 📚 Documentation

- `README.md` - Complete feature documentation
- `ENHANCED_ANALYTICS.md` - Analytics features guide
- `STREAMING_SUPPORT.md` - Streaming mode details
- `CHANGELOG.md` - Version history and changes

Happy analyzing! 🎉
