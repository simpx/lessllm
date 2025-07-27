"""
Cost analysis page
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

def render_costs_page():
    st.markdown("## 💰 Cost Analysis")
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=7),
            key="costs_start_date"
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            key="costs_end_date"
        )
    
    # Initialize storage
    storage = get_storage()
    
    # Get date range in days
    days_diff = (end_date - start_date).days
    if days_diff <= 0:
        days_diff = 1
    
    # Query cost data grouped by date
    sql = f"""
        SELECT 
            DATE(timestamp) as date,
            model,
            provider,
            COUNT(*) as request_count,
            SUM(actual_total_tokens) as total_tokens,
            SUM(estimated_cost_usd) as total_cost_usd,
            AVG(estimated_cost_usd) as avg_cost_per_request
        FROM api_calls
        WHERE timestamp >= '{start_date}' AND timestamp <= '{end_date}'
        GROUP BY DATE(timestamp), model, provider
        ORDER BY date
    """
    
    try:
        cost_data = storage.query(sql)
        cost_df = pd.DataFrame(cost_data)
        
        if not cost_df.empty:
            # Convert date column to datetime
            cost_df['date'] = pd.to_datetime(cost_df['date'])
            cost_df['total_cost_usd'] = pd.to_numeric(cost_df['total_cost_usd'], errors='coerce').fillna(0)
            cost_df['avg_cost_per_request'] = pd.to_numeric(cost_df['avg_cost_per_request'], errors='coerce').fillna(0)
            cost_df['total_tokens'] = pd.to_numeric(cost_df['total_tokens'], errors='coerce').fillna(0)
            
            # Cost summary metrics
            st.markdown("### Cost Summary")
            total_cost = cost_df['total_cost_usd'].sum()
            total_requests = cost_df['request_count'].sum()
            total_tokens = cost_df['total_tokens'].sum()
            avg_cost_per_request = total_cost / total_requests if total_requests > 0 else 0
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Cost", f"${total_cost:.4f}")
            
            with col2:
                st.metric("Total Requests", f"{total_requests:,}")
            
            with col3:
                st.metric("Total Tokens", f"{total_tokens:,}")
            
            with col4:
                st.metric("Avg Cost/Request", f"${avg_cost_per_request:.6f}")
            
            # Cost over time
            st.markdown("### Cost Trends Over Time")
            
            # Daily cost trend
            daily_cost = cost_df.groupby('date')['total_cost_usd'].sum().reset_index()
            fig1 = px.line(
                daily_cost,
                x='date',
                y='total_cost_usd',
                title="Daily Cost Trend"
            )
            fig1.update_layout(yaxis_tickprefix='$')
            st.plotly_chart(fig1, use_container_width=True)
            
            # Cost by model over time
            st.markdown("### Cost by Model Over Time")
            fig2 = px.line(
                cost_df,
                x='date',
                y='total_cost_usd',
                color='model',
                title="Cost by Model Over Time"
            )
            fig2.update_layout(yaxis_tickprefix='$')
            st.plotly_chart(fig2, use_container_width=True)
            
            # Cost distribution
            st.markdown("### Cost Distribution")
            
            # Cost by model pie chart
            model_cost = cost_df.groupby('model')['total_cost_usd'].sum().reset_index()
            fig3 = px.pie(
                model_cost,
                values='total_cost_usd',
                names='model',
                title="Cost Distribution by Model"
            )
            fig3.update_traces(textinfo='percent+label')
            st.plotly_chart(fig3, use_container_width=True)
            
            # Cost by provider
            provider_cost = cost_df.groupby('provider')['total_cost_usd'].sum().reset_index()
            fig4 = px.pie(
                provider_cost,
                values='total_cost_usd',
                names='provider',
                title="Cost Distribution by Provider"
            )
            fig4.update_traces(textinfo='percent+label')
            st.plotly_chart(fig4, use_container_width=True)
            
            # Cost efficiency analysis
            st.markdown("### Cost Efficiency Analysis")
            
            # Cost per token
            cost_df['cost_per_token'] = cost_df['total_cost_usd'] / cost_df['total_tokens']
            cost_df['cost_per_token'] = cost_df['cost_per_token'].replace([float('inf'), -float('inf')], 0)
            
            fig5 = px.bar(
                cost_df,
                x='model',
                y='cost_per_token',
                color='provider',
                title="Cost Per Token by Model"
            )
            fig5.update_layout(yaxis_tickprefix='$')
            st.plotly_chart(fig5, use_container_width=True)
            
            # Average cost per request by model
            fig6 = px.bar(
                cost_df,
                x='model',
                y='avg_cost_per_request',
                color='provider',
                title="Average Cost Per Request by Model"
            )
            fig6.update_layout(yaxis_tickprefix='$')
            st.plotly_chart(fig6, use_container_width=True)
            
            # Detailed cost data
            st.markdown("### Detailed Cost Analysis Data")
            display_df = cost_df.copy()
            display_df['total_cost_usd'] = display_df['total_cost_usd'].apply(lambda x: f"${x:.6f}")
            display_df['avg_cost_per_request'] = display_df['avg_cost_per_request'].apply(lambda x: f"${x:.6f}")
            display_df['cost_per_token'] = display_df['cost_per_token'].apply(lambda x: f"${x:.8f}" if pd.notna(x) else "$0.00000000")
            display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
            
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No cost data available for the selected date range")
            
    except Exception as e:
        st.error(f"Error loading cost analysis data: {str(e)}")
    
    # Additional cost insights
    st.markdown("### Cost Insights")
    
    # Query for top expensive requests
    try:
        expensive_sql = f"""
            SELECT 
                timestamp,
                request_id,
                model,
                provider,
                actual_total_tokens,
                estimated_cost_usd
            FROM api_calls
            WHERE timestamp >= '{start_date}' AND timestamp <= '{end_date}'
            ORDER BY estimated_cost_usd DESC
            LIMIT 10
        """
        
        expensive_data = storage.query(expensive_sql)
        expensive_df = pd.DataFrame(expensive_data)
        
        if not expensive_df.empty:
            st.markdown("#### Top 10 Most Expensive Requests")
            expensive_df['timestamp'] = pd.to_datetime(expensive_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            expensive_df['estimated_cost_usd'] = expensive_df['estimated_cost_usd'].apply(lambda x: f"${x:.6f}")
            expensive_df['actual_total_tokens'] = expensive_df['actual_total_tokens'].apply(lambda x: f"{x:,}")
            
            st.dataframe(expensive_df, use_container_width=True)
        else:
            st.info("No expensive request data available")
            
    except Exception as e:
        st.error(f"Error loading expensive requests data: {str(e)}")

if __name__ == "__main__":
    render_costs_page()