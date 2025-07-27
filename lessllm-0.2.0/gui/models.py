"""
Model usage breakdown page
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

def render_models_page():
    st.markdown("## 🤖 Model Usage Breakdown")
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=7),
            key="models_start_date"
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            key="models_end_date"
        )
    
    # Initialize storage
    storage = get_storage()
    
    # Get date range in days
    days_diff = (end_date - start_date).days
    if days_diff <= 0:
        days_diff = 1
    
    # Query model usage data
    sql = f"""
        SELECT 
            model,
            provider,
            COUNT(*) as request_count,
            SUM(actual_total_tokens) as total_tokens,
            SUM(estimated_cost_usd) as total_cost_usd,
            AVG(estimated_total_latency_ms) as avg_latency_ms,
            AVG(estimated_cache_hit_rate) as avg_cache_hit_rate
        FROM api_calls
        WHERE timestamp >= '{start_date}' AND timestamp <= '{end_date}'
        GROUP BY model, provider
        ORDER BY request_count DESC
    """
    
    try:
        model_data = storage.query(sql)
        model_df = pd.DataFrame(model_data)
        
        if not model_df.empty:
            # Convert data types
            model_df['total_tokens'] = pd.to_numeric(model_df['total_tokens'], errors='coerce').fillna(0)
            model_df['total_cost_usd'] = pd.to_numeric(model_df['total_cost_usd'], errors='coerce').fillna(0)
            model_df['avg_latency_ms'] = pd.to_numeric(model_df['avg_latency_ms'], errors='coerce').fillna(0)
            model_df['avg_cache_hit_rate'] = pd.to_numeric(model_df['avg_cache_hit_rate'], errors='coerce').fillna(0)
            
            # Overall model usage summary
            st.markdown("### Overall Model Usage")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Models Used", model_df['model'].nunique())
            
            with col2:
                st.metric("Total Requests", model_df['request_count'].sum())
            
            with col3:
                st.metric("Total Tokens", f"{model_df['total_tokens'].sum():,}")
            
            with col4:
                st.metric("Total Cost", f"${model_df['total_cost_usd'].sum():.4f}")
            
            # Request count by model
            st.markdown("### Request Distribution by Model")
            fig1 = px.pie(
                model_df,
                values='request_count',
                names='model',
                title="Requests by Model"
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            # Token usage by model
            st.markdown("### Token Usage by Model")
            fig2 = px.bar(
                model_df,
                x='model',
                y='total_tokens',
                color='provider',
                title="Total Tokens by Model"
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # Cost analysis by model
            st.markdown("### Cost Analysis by Model")
            fig3 = px.bar(
                model_df,
                x='model',
                y='total_cost_usd',
                color='provider',
                title="Total Cost by Model"
            )
            st.plotly_chart(fig3, use_container_width=True)
            
            # Performance comparison
            st.markdown("### Model Performance Comparison")
            
            # Latency comparison
            fig4 = px.bar(
                model_df,
                x='model',
                y='avg_latency_ms',
                color='provider',
                title="Average Latency by Model (ms)"
            )
            st.plotly_chart(fig4, use_container_width=True)
            
            # Cache hit rate comparison
            fig5 = px.bar(
                model_df,
                x='model',
                y='avg_cache_hit_rate',
                color='provider',
                title="Average Cache Hit Rate by Model"
            )
            # Convert to percentage for better visualization
            fig5.update_layout(yaxis_tickformat='.1%')
            st.plotly_chart(fig5, use_container_width=True)
            
            # Provider breakdown
            st.markdown("### Provider Analysis")
            provider_df = model_df.groupby('provider').agg({
                'request_count': 'sum',
                'total_tokens': 'sum',
                'total_cost_usd': 'sum',
                'avg_latency_ms': 'mean',
                'avg_cache_hit_rate': 'mean'
            }).reset_index()
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig6 = px.pie(
                    provider_df,
                    values='request_count',
                    names='provider',
                    title="Requests by Provider"
                )
                st.plotly_chart(fig6, use_container_width=True)
            
            with col2:
                fig7 = px.pie(
                    provider_df,
                    values='total_cost_usd',
                    names='provider',
                    title="Cost by Provider"
                )
                st.plotly_chart(fig7, use_container_width=True)
            
            # Detailed model data table
            st.markdown("### Detailed Model Usage Data")
            # Format the data for better display
            display_df = model_df.copy()
            display_df['avg_cache_hit_rate'] = display_df['avg_cache_hit_rate'].apply(lambda x: f"{x*100:.2f}%")
            display_df['avg_latency_ms'] = display_df['avg_latency_ms'].apply(lambda x: f"{x:.0f} ms")
            display_df['total_cost_usd'] = display_df['total_cost_usd'].apply(lambda x: f"${x:.4f}")
            display_df['total_tokens'] = display_df['total_tokens'].apply(lambda x: f"{x:,}")
            
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No model usage data available for the selected date range")
            
    except Exception as e:
        st.error(f"Error loading model usage data: {str(e)}")

if __name__ == "__main__":
    render_models_page()