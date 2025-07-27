"""
Cache analysis charts page
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

def render_cache_page():
    st.markdown("## 🧠 Cache Analysis")
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=7),
            key="cache_start_date"
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            key="cache_end_date"
        )
    
    # Initialize storage
    storage = get_storage()
    
    # Get date range in days
    days_diff = (end_date - start_date).days
    if days_diff <= 0:
        days_diff = 1
    
    # Cache analysis summary
    st.markdown("### Cache Analysis Summary")
    cache_summary = storage.get_cache_analysis_summary(days=days_diff)
    
    if cache_summary and cache_summary.get('total_predictions', 0) > 0:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Predictions", 
                cache_summary['total_predictions']
            )
        
        with col2:
            st.metric(
                "Accuracy", 
                f"{cache_summary['accuracy_percentage']:.1f}%",
                f"{cache_summary['accurate_predictions']} accurate"
            )
        
        with col3:
            st.metric(
                "Avg Prediction Error", 
                f"{cache_summary['avg_prediction_error']:.4f}"
            )
        
        with col4:
            st.metric(
                "Hit Rate Difference", 
                f"{abs((cache_summary['avg_actual_hit_rate'] or 0) - (cache_summary['avg_estimated_hit_rate'] or 0)):.4f}"
            )
        
        # Hit rate comparison
        st.markdown("### Estimated vs Actual Cache Hit Rates")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Estimated Hit Rate", 
                f"{(cache_summary['avg_estimated_hit_rate'] or 0) * 100:.1f}%"
            )
        
        with col2:
            st.metric(
                "Actual Hit Rate", 
                f"{(cache_summary['avg_actual_hit_rate'] or 0) * 100:.1f}%"
            )
        
        # Query detailed cache analysis data
        sql = f"""
            SELECT 
                timestamp,
                model,
                provider,
                estimated_cache_hit_rate,
                actual_cache_hit_rate,
                prediction_error,
                hit_rate_diff
            FROM cache_analysis_comparison
            WHERE timestamp >= '{start_date}' AND timestamp <= '{end_date}'
            ORDER BY timestamp
        """
        
        try:
            cache_data = storage.query(sql)
            cache_df = pd.DataFrame(cache_data)
            
            if not cache_df.empty:
                # Convert timestamp to datetime
                cache_df['timestamp'] = pd.to_datetime(cache_df['timestamp'])
                
                # Hit rate over time
                st.markdown("### Cache Hit Rate Over Time")
                fig = px.line(
                    cache_df,
                    x='timestamp',
                    y=['estimated_cache_hit_rate', 'actual_cache_hit_rate'],
                    color='model',
                    title="Estimated vs Actual Cache Hit Rate Over Time"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Prediction error over time
                st.markdown("### Prediction Error Over Time")
                fig2 = px.line(
                    cache_df,
                    x='timestamp',
                    y='prediction_error',
                    color='model',
                    title="Cache Prediction Error Over Time"
                )
                st.plotly_chart(fig2, use_container_width=True)
                
                # Error distribution histogram
                st.markdown("### Prediction Error Distribution")
                fig3 = px.histogram(
                    cache_df,
                    x='prediction_error',
                    nbins=30,
                    title="Distribution of Prediction Errors"
                )
                st.plotly_chart(fig3, use_container_width=True)
                
                # Hit rate comparison scatter plot
                st.markdown("### Hit Rate Correlation")
                fig4 = px.scatter(
                    cache_df,
                    x='estimated_cache_hit_rate',
                    y='actual_cache_hit_rate',
                    color='model',
                    title="Estimated vs Actual Cache Hit Rate Correlation",
                    labels={
                        'estimated_cache_hit_rate': 'Estimated Hit Rate',
                        'actual_cache_hit_rate': 'Actual Hit Rate'
                    }
                )
                # Add perfect correlation line
                fig4.add_shape(
                    type='line',
                    x0=0, x1=1,
                    y0=0, y1=1,
                    line=dict(color='red', dash='dash')
                )
                st.plotly_chart(fig4, use_container_width=True)
                
                # Model-wise cache performance
                st.markdown("### Model-wise Cache Performance")
                model_cache_stats = cache_df.groupby('model').agg({
                    'estimated_cache_hit_rate': 'mean',
                    'actual_cache_hit_rate': 'mean',
                    'prediction_error': 'mean'
                }).reset_index()
                
                fig5 = px.bar(
                    model_cache_stats,
                    x='model',
                    y=['estimated_cache_hit_rate', 'actual_cache_hit_rate'],
                    title="Average Cache Hit Rate by Model",
                    barmode='group'
                )
                st.plotly_chart(fig5, use_container_width=True)
                
                # Show raw data table
                st.markdown("### Detailed Cache Analysis Data")
                st.dataframe(cache_df, use_container_width=True)
            else:
                st.info("No cache analysis data available for the selected date range")
                
        except Exception as e:
            st.error(f"Error loading cache analysis data: {str(e)}")
    else:
        st.info("No cache analysis data available")

if __name__ == "__main__":
    render_cache_page()