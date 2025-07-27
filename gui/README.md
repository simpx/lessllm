# LessLLM Analytics Dashboard

A Streamlit-based web interface for visualizing LessLLM analytics data stored in DuckDB.

## Features

- Dashboard overview with key metrics
- Performance statistics visualization
- Cache analysis charts
- Model usage breakdown
- Cost analysis
- Recent logs table
- Date range filtering
- Data export functionality

## Installation

The GUI requires additional dependencies:

```bash
pip install -r gui/requirements.txt
```

## Usage

To run the analytics dashboard:

```bash
streamlit run gui/app.py
```

The dashboard will be available at http://localhost:8501

## Navigation

The interface is organized into multiple pages accessible from the sidebar:

1. **Dashboard** - Overview of key metrics and recent activity
2. **Performance Statistics** - Detailed performance metrics over time
3. **Cache Analysis** - Cache hit rate analysis and prediction accuracy
4. **Model Usage** - Breakdown of model usage and provider analysis
5. **Cost Analysis** - Cost trends and efficiency metrics
6. **Recent Logs** - Filterable table of recent API calls
7. **Data Export** - Export functionality in multiple formats

## Data Source

The dashboard connects to the DuckDB database configured in your LessLLM configuration. By default, this is `lessllm_logs.db` in the project root directory.