# Changelog

All notable changes to LessLLM will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-07-27

### 🚀 Major Features Added

#### Intelligent API Routing System
- **Smart Format Conversion**: Automatic conversion between Claude Messages API and OpenAI Chat Completions API
- **Provider Transparency**: Use any API format with any provider type
- **4-Way Routing Matrix**: 
  - Claude API + Claude Provider → Direct passthrough
  - Claude API + OpenAI Provider → Format conversion
  - OpenAI API + OpenAI Provider → Direct passthrough  
  - OpenAI API + Claude Provider → Format conversion
- **Streaming Support**: Real-time format conversion for all routing scenarios

#### Enhanced Analytics Dashboard
- **Comprehensive Table Display**: 9 new columns including token details, cache metrics, performance data
- **Three-Tier Metrics System**: Basic metrics, token analysis, performance indicators
- **Data Visualization Suite**: Provider distribution, cost analysis, performance trends
- **Interactive Features**: Click-to-view request details with streamlit-aggrid integration

#### Advanced SQL Analytics
- **Pre-built Query Templates**: Token analysis, cache efficiency, cost ranking, performance analysis
- **Enhanced Data Model**: Extended database schema with 15+ new analytical fields
- **Visual Query Builder**: Interactive SQL interface with result visualization

### 🎯 New API Endpoints
- **Claude Messages API** (`/v1/messages`): Full Claude API compatibility
- **Enhanced OpenAI API** (`/v1/chat/completions`): Extended with intelligent routing
- **Health Check** (`/health`): Comprehensive system status
- **Statistics** (`/lessllm/stats`): Real-time analytics API

### 📊 Analytics Enhancements
- **Token Tracking**: Input/output/cached token breakdown per request
- **Cache Analytics**: Hit rates, savings calculation, efficiency metrics
- **Performance Monitoring**: TTFT, TPOT, throughput with trend analysis
- **Cost Optimization**: Per-model efficiency rankings and optimization insights
- **HTTP Details**: Complete request/response header capture

### 🔧 Technical Improvements
- **Streaming Architecture**: Robust chunk collection and response reconstruction
- **Error Handling**: Comprehensive exception handling with detailed logging
- **Data Persistence**: Optimized DuckDB schema with analytical indexes
- **Configuration**: Enhanced YAML configuration with multi-provider support

### 🧪 Testing & Validation
- **Test Suite**: Comprehensive testing scripts for all features
- **Sample Data Generator**: Realistic test data for analytics validation
- **Multi-Provider Testing**: Validation across different provider combinations
- **Performance Benchmarks**: Load testing and performance validation

### 📚 Documentation
- **Complete README**: Comprehensive documentation with examples
- **Streaming Guide**: Detailed streaming mode analysis
- **Analytics Guide**: Enhanced analytics feature documentation
- **Test Reports**: Comprehensive test result documentation

### 🛠️ Developer Experience
- **CLI Enhancements**: Improved command-line interface with GUI integration
- **Debug Tools**: Enhanced logging and debugging capabilities
- **Development Scripts**: Automated testing and validation tools
- **Code Quality**: Improved error handling and code organization

---

## [0.1.0] - 2025-01-XX

### Initial Release
- Basic proxy functionality
- OpenAI API compatibility
- Claude provider support
- DuckDB logging
- Basic performance tracking
- Configuration management
- CLI interface

### Core Features
- FastAPI-based proxy server
- Multi-provider abstraction
- Request/response logging
- Performance metrics (TTFT/TPOT)
- Cache estimation
- Cost calculation

---

## Upgrade Guide

### From 0.1.0 to 0.2.0

#### Configuration Changes
- **New Format**: Update configuration to use new provider structure
- **GUI Integration**: Add GUI-related configuration options
- **Enhanced Logging**: Update logging configuration for new analytics features

#### Database Migration
- **Automatic Migration**: Database schema will be updated automatically
- **New Fields**: 15+ new analytical fields added to api_calls table
- **Indexes**: New indexes for improved query performance

#### API Changes
- **New Endpoints**: `/v1/messages` endpoint added for Claude API
- **Enhanced Responses**: More detailed response metadata
- **Streaming Improvements**: Better streaming format handling

#### Dependencies
- **New Requirements**: streamlit-aggrid, enhanced plotly integration
- **Python Version**: Minimum Python 3.10 (upgraded from 3.9)
- **Optional Dependencies**: GUI dependencies moved to main requirements

#### Migration Steps
1. **Backup Configuration**: Save existing `lessllm.yaml`
2. **Update Dependencies**: Run `pip install -e .` or `uv sync`
3. **Update Configuration**: Use new configuration format
4. **Test Functionality**: Run test scripts to validate upgrade
5. **Start Services**: Launch server with new GUI integration

For detailed migration assistance, see [MIGRATION.md](MIGRATION.md)