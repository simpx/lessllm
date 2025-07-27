"""
Performance statistics visualization page
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from lessllm.config import get_config
from lessllm.logging.storage import LogStorage

def get_storage():
    """Initialize LogStorage with database path from config"""
    config = get_config()
    db_path = config.logging.storage.get("db_path", "./lessllm_logs.db")
    return LogStorage(db_path)

def render_performance_page():
    st.markdown("## 🚀 Performance Statistics")
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=7),
            key="perf_start_date"
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            key="perf_end_date"
        )
    
    # Model and provider filters
    storage = get_storage()
    db_stats = storage.get_database_stats()
    
    # Get unique models and providers
    models = [item['model'] for item in db_stats.get('top_models', [])]
    providers = [item['provider'] for item in db_stats.get('provider_breakdown', [])]
    
    col1, col2 = st.columns(2)
    with col1:
        selected_models = st.multiselect("Select Models", options=models, default=models[:3] if models else [])
    with col2:
        selected_providers = st.multiselect("Select Providers", options=providers, default=providers[:2] if providers else [])
    
    # Get date range in days
    days_diff = (end_date - start_date).days
    if days_diff <= 0:
        days_diff = 1
    
    # Performance data
    st.markdown("### Performance Metrics Over Time")
    
    # Query performance stats grouped by date
    where_conditions = [f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'"]
    params = []
    
    if selected_models:
        placeholders = ",".join([f"'{model}'" for model in selected_models])
        where_conditions.append(f"model IN ({placeholders})")
    
    if selected_providers:
        placeholders = ",".join([f"'{provider}'" for provider in selected_providers])
        where_conditions.append(f"provider IN ({placeholders})")
    
    where_clause = " AND ".join(where_conditions)
    
    sql = f"""
        SELECT 
            DATE(timestamp) as date,
            model,
            provider,
            COUNT(*) as request_count,
            AVG(estimated_ttft_ms) as avg_ttft_ms,
            AVG(estimated_tpot_ms) as avg_tpot_ms,
            AVG(estimated_total_latency_ms) as avg_latency_ms,
            AVG(estimated_tokens_per_second) as avg_tokens_per_second,
            SUM(actual_total_tokens) as total_tokens,
            SUM(estimated_cost_usd) as total_cost_usd
        FROM api_calls 
        WHERE success = true AND {where_clause}
        GROUP BY DATE(timestamp), model, provider
        ORDER BY date
    """
    
    try:
        perf_data = storage.query(sql, params)
        perf_df = pd.DataFrame(perf_data)
        
        if not perf_df.empty:
            # Convert date column to datetime
            perf_df['date'] = pd.to_datetime(perf_df['date'])
            
            # Create tabs for different metrics
            tab1, tab2, tab3, tab4 = st.tabs([
                "Latency Metrics", 
                "Throughput Metrics", 
                "Token Usage", 
                "Cost Analysis"
            ])
            
            with tab1:
                st.markdown("#### Latency Metrics (ms)")
                fig = px.line(
                    perf_df, 
                    x='date', 
                    y=['avg_ttft_ms', 'avg_tpot_ms', 'avg_latency_ms'],
                    color='model',
                    title="Latency Metrics Over Time"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Bar chart for average latency by model
                avg_latency = perf_df.groupby('model')['avg_latency_ms'].mean().reset_index()
                fig2 = px.bar(
                    avg_latency,
                    x='model',
                    y='avg_latency_ms',
                    title="Average Latency by Model"
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            with tab2:
                st.markdown("#### Throughput Metrics")
                fig = px.line(
                    perf_df,
                    x='date',
                    y='avg_tokens_per_second',
                    color='model',
                    title="Tokens Per Second Over Time"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Request count over time
                fig2 = px.line(
                    perf_df,
                    x='date',
                    y='request_count',
                    color='model',
                    title="Request Count Over Time"
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            with tab3:
                st.markdown("#### Token Usage")
                fig = px.line(
                    perf_df,
                    x='date',
                    y='total_tokens',
                    color='model',
                    title="Total Tokens Used Over Time"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Token distribution pie chart
                token_totals = perf_df.groupby('model')['total_tokens'].sum().reset_index()
                fig2 = px.pie(
                    token_totals,
                    values='total_tokens',
                    names='model',
                    title="Token Usage Distribution by Model"
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            with tab4:
                st.markdown("#### Cost Analysis")
                fig = px.line(
                    perf_df,
                    x='date',
                    y='total_cost_usd',
                    color='model',
                    title="Cost Over Time"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Cost comparison bar chart
                cost_totals = perf_df.groupby('model')['total_cost_usd'].sum().reset_index()
                fig2 = px.bar(
                    cost_totals,
                    x='model',
                    y='total_cost_usd',
                    title="Total Cost by Model"
                )
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No performance data available for the selected filters")
            
    except Exception as e:
        st.error(f"Error loading performance data: {str(e)}")
    
    # Summary statistics
    st.markdown("### Performance Summary")
    perf_stats = storage.get_performance_stats(days=days_diff)
    
    if perf_stats and perf_stats.get('total_requests', 0) > 0:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Requests", 
                perf_stats['total_requests'],
                f"{perf_stats['successful_requests']} successful"
            )
        
        with col2:
            st.metric(
                "Avg Latency", 
                f"{perf_stats['avg_latency_ms'] or 0:.0f} ms"
            )
        
        with col3:
            st.metric(
                "Avg Tokens/sec", 
                f"{perf_stats['avg_tokens_per_second'] or 0:.0f}"
            )
        
        with col4:
            st.metric(
                "Total Cost", 
                f"${perf_stats['total_cost_usd'] or 0:.4f}"
            )
        
        # Additional metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Avg TTFT", 
                f"{perf_stats['avg_ttft_ms'] or 0:.0f} ms"
            )
        
        with col2:
            st.metric(
                "Avg TPOT", 
                f"{perf_stats['avg_tpot_ms'] or 0:.2f} ms"
            )
        
        with col3:
            st.metric(
                "Avg Cache Hit Rate", 
                f"{(perf_stats['avg_cache_hit_rate'] or 0) * 100:.1f}%"
            )
        
        with col4:
            st.metric(
                "Total Tokens", 
                f"{perf_stats['total_tokens'] or 0:,}"
            )
    else:
        st.info("No performance statistics available")

if __name__ == "__main__":
    render_performance_page()