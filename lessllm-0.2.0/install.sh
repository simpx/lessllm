#!/bin/bash

echo "🚀 Installing LessLLM v0.2.0"
echo "=============================="

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.10+ required, found Python $python_version"
    exit 1
fi

echo "✅ Python $python_version detected"

# Install with pip
echo "📦 Installing LessLLM..."
pip install -e .

echo "🎉 Installation completed!"
echo ""
echo "📋 Next Steps:"
echo "1. Copy lessllm.yaml.example to lessllm.yaml"
echo "2. Edit lessllm.yaml with your API keys"
echo "3. Run: lessllm server --config lessllm.yaml --gui-port 8501"
echo "4. Open: http://localhost:8000 (API) and http://localhost:8501 (GUI)"
echo ""
echo "📚 Documentation: README.md"
echo "🧪 Testing: Run scripts in tests/ directory"
