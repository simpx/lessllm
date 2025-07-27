"""
Recent logs table page
"""

import streamlit as st
import pandas as pd
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

def render_logs_page():
    st.markdown("## 📋 Recent Logs")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        limit = st.number_input("Number of Records", min_value=10, max_value=1000, value=100, step=10)
    
    with col2:
        success_filter = st.selectbox(
            "Success Status",
            options=["All", "Success Only", "Failed Only"],
            index=0
        )
    
    with col3:
        # Get unique models for filter
        storage = get_storage()
        db_stats = storage.get_database_stats()
        models = [item['model'] for item in db_stats.get('top_models', [])]
        selected_model = st.selectbox("Filter by Model", options=["All"] + models, index=0)
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=7),
            key="logs_start_date"
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            key="logs_end_date"
        )
    
    # Build query with filters
    where_conditions = [f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'"]
    
    if success_filter == "Success Only":
        where_conditions.append("success = true")
    elif success_filter == "Failed Only":
        where_conditions.append("success = false")
    
    if selected_model != "All":
        where_conditions.append(f"model = '{selected_model}'")
    
    where_clause = " AND ".join(where_conditions)
    
    # Query recent logs with filters
    sql = f"""
        SELECT 
            timestamp,
            request_id,
            provider,
            model,
            success,
            error_message,
            estimated_ttft_ms,
            estimated_tpot_ms,
            estimated_total_latency_ms,
            estimated_cache_hit_rate,
            actual_total_tokens,
            estimated_cost_usd,
            user_id,
            session_id
        FROM api_calls 
        WHERE {where_clause}
        ORDER BY timestamp DESC 
        LIMIT {limit}
    """
    
    try:
        logs_data = storage.query(sql)
        logs_df = pd.DataFrame(logs_data)
        
        if not logs_df.empty:
            # Format the data for better display
            logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            logs_df['estimated_cache_hit_rate'] = logs_df['estimated_cache_hit_rate'].apply(
                lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A"
            )
            logs_df['estimated_cost_usd'] = logs_df['estimated_cost_usd'].apply(
                lambda x: f"${x:.6f}" if pd.notna(x) else "N/A"
            )
            logs_df['estimated_ttft_ms'] = logs_df['estimated_ttft_ms'].apply(
                lambda x: f"{x:.0f} ms" if pd.notna(x) else "N/A"
            )
            logs_df['estimated_tpot_ms'] = logs_df['estimated_tpot_ms'].apply(
                lambda x: f"{x:.2f} ms" if pd.notna(x) else "N/A"
            )
            logs_df['estimated_total_latency_ms'] = logs_df['estimated_total_latency_ms'].apply(
                lambda x: f"{x:.0f} ms" if pd.notna(x) else "N/A"
            )
            logs_df['actual_total_tokens'] = logs_df['actual_total_tokens'].apply(
                lambda x: f"{x:,}" if pd.notna(x) else "N/A"
            )
            
            # Display metrics
            st.markdown("### Log Summary")
            total_logs = len(logs_df)
            success_count = len(logs_df[logs_df['success'] == True]) if 'success' in logs_df.columns else 0
            success_rate = (success_count / total_logs * 100) if total_logs > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Records", total_logs)
            with col2:
                st.metric("Success Rate", f"{success_rate:.1f}%")
            with col3:
                st.metric("Failed Requests", total_logs - success_count)
            
            # Display logs table
            st.markdown("### API Call Logs")
            st.dataframe(logs_df, use_container_width=True)
            
            # Export option
            csv = logs_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Logs as CSV",
                data=csv,
                file_name=f"lessllm_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No logs found matching the selected filters")
            
    except Exception as e:
        st.error(f"Error loading logs data: {str(e)}")

if __name__ == "__main__":
    render_logs_page()