#!/bin/bash

# LessLLM v0.2.0 Release Script

set -e

VERSION="0.2.0"
echo "🚀 Building LessLLM v${VERSION} Release Package"
echo "=================================================="

# Create release directory
RELEASE_DIR="lessllm-${VERSION}"
mkdir -p "${RELEASE_DIR}"

echo "📦 Creating release package..."

# Copy core files
cp -r lessllm/ "${RELEASE_DIR}/"
cp -r gui/ "${RELEASE_DIR}/"
cp pyproject.toml "${RELEASE_DIR}/"
cp README.md "${RELEASE_DIR}/"
cp CHANGELOG.md "${RELEASE_DIR}/"
cp CLAUDE.md "${RELEASE_DIR}/"
cp LICENSE "${RELEASE_DIR}/" 2>/dev/null || echo "⚠️  LICENSE file not found - please add one"

# Copy documentation
cp ENHANCED_ANALYTICS.md "${RELEASE_DIR}/"
cp STREAMING_SUPPORT.md "${RELEASE_DIR}/"
cp TEST_RESULTS.md "${RELEASE_DIR}/"

# Copy example configurations
cp lessllm.yaml "${RELEASE_DIR}/lessllm.yaml.example"
cp test_multi_provider.yaml "${RELEASE_DIR}/test_multi_provider.yaml.example"

# Copy test scripts
mkdir -p "${RELEASE_DIR}/tests"
cp test_*.sh "${RELEASE_DIR}/tests/" 2>/dev/null || true
cp test_*.py "${RELEASE_DIR}/tests/" 2>/dev/null || true

# Create installation script
cat > "${RELEASE_DIR}/install.sh" << 'EOF'
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
EOF

chmod +x "${RELEASE_DIR}/install.sh"

# Create quick start guide
cat > "${RELEASE_DIR}/QUICK_START.md" << 'EOF'
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
EOF

# Create requirements.txt for easier installation
cat > "${RELEASE_DIR}/requirements.txt" << 'EOF'
# LessLLM v0.2.0 Requirements
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
httpx>=0.25.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
pyyaml>=6.0
duckdb>=0.9.0
python-multipart>=0.0.6
streamlit>=1.24.0
plotly>=5.15.0
pandas>=2.0.0
streamlit-aggrid==1.1.7
EOF

# Create archive
echo "🗜️  Creating archives..."
tar -czf "lessllm-${VERSION}.tar.gz" "${RELEASE_DIR}"
zip -r "lessllm-${VERSION}.zip" "${RELEASE_DIR}" > /dev/null

# Generate checksums
echo "🔐 Generating checksums..."
sha256sum "lessllm-${VERSION}.tar.gz" > "lessllm-${VERSION}.tar.gz.sha256"
sha256sum "lessllm-${VERSION}.zip" > "lessllm-${VERSION}.zip.sha256"

# Show package info
echo ""
echo "📋 Release Package Summary"
echo "=========================="
echo "Version: ${VERSION}"
echo "Package size:"
ls -lh lessllm-${VERSION}.*
echo ""
echo "📁 Package contents:"
find "${RELEASE_DIR}" -type f | head -20
echo "... (and more)"
echo ""
echo "✅ Release package created successfully!"
echo ""
echo "📤 Distribution files:"
echo "- lessllm-${VERSION}.tar.gz (with checksum)"
echo "- lessllm-${VERSION}.zip (with checksum)"
echo "- ${RELEASE_DIR}/ (directory)"
echo ""
echo "🚀 Ready for distribution!"
EOF