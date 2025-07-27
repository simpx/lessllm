"""
Data export functionality page
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import tempfile
import os
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

def render_export_page():
    st.markdown("## 📤 Data Export")
    
    st.info("Export your LessLLM analytics data in various formats for further analysis.")
    
    # Export options
    st.markdown("### Export Configuration")
    
    # Date range
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=30),
            key="export_start_date"
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            key="export_end_date"
        )
    
    # Get unique models and providers for filters
    storage = get_storage()
    db_stats = storage.get_database_stats()
    models = [item['model'] for item in db_stats.get('top_models', [])]
    providers = [item['provider'] for item in db_stats.get('provider_breakdown', [])]
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        selected_models = st.multiselect("Select Models", options=models, default=models)
    with col2:
        selected_providers = st.multiselect("Select Providers", options=providers, default=providers)
    
    # Success filter
    success_only = st.checkbox("Export successful requests only", value=True)
    
    # Export format
    export_format = st.radio(
        "Export Format",
        options=["CSV", "Parquet", "JSON"],
        index=0
    )
    
    # Export button
    if st.button("🚀 Export Data", type="primary", use_container_width=True):
        try:
            # Build filters for export
            filters = {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "success_only": success_only
            }
            
            if selected_models:
                filters["model"] = selected_models
            
            if selected_providers:
                filters["provider"] = selected_providers
            
            if export_format == "Parquet":
                # Use the built-in export functionality for Parquet
                with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                
                try:
                    storage.export_parquet(tmp_path, **filters)
                    
                    # Read the file and provide download
                    with open(tmp_path, "rb") as file:
                        st.download_button(
                            label="📥 Download Parquet File",
                            data=file,
                            file_name=f"lessllm_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet",
                            mime="application/octet-stream"
                        )
                    st.success("✅ Data exported successfully as Parquet!")
                finally:
                    # Clean up temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            
            else:
                # For CSV and JSON, we'll query the data and convert
                where_conditions = [
                    f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'"
                ]
                params = []
                
                if success_only:
                    where_conditions.append("success = true")
                
                if selected_models:
                    placeholders = ",".join([f"'{model}'" for model in selected_models])
                    where_conditions.append(f"model IN ({placeholders})")
                
                if selected_providers:
                    placeholders = ",".join([f"'{provider}'" for provider in selected_providers])
                    where_conditions.append(f"provider IN ({placeholders})")
                
                where_clause = " AND ".join(where_conditions)
                
                sql = f"SELECT * FROM api_calls WHERE {where_clause} ORDER BY timestamp"
                
                # Query data
                data = storage.query(sql, params)
                df = pd.DataFrame(data)
                
                if not df.empty:
                    if export_format == "CSV":
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download CSV File",
                            data=csv,
                            file_name=f"lessllm_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                        st.success("✅ Data exported successfully as CSV!")
                    
                    elif export_format == "JSON":
                        json_str = df.to_json(orient="records", date_format="iso", indent=2)
                        st.download_button(
                            label="📥 Download JSON File",
                            data=json_str,
                            file_name=f"lessllm_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                        st.success("✅ Data exported successfully as JSON!")
                else:
                    st.warning("No data found matching the selected filters.")
                    
        except Exception as e:
            st.error(f"Error exporting data: {str(e)}")
    
    # Export information
    st.markdown("### 📋 Export Information")
    st.markdown("""
    - **CSV**: Best for importing into spreadsheet applications like Excel or Google Sheets
    - **Parquet**: Best for large datasets and efficient storage, compatible with data analysis tools
    - **JSON**: Best for programmatic access and integration with other applications
    
    **Note**: Export performance may vary based on the amount of data selected.
    For large exports, consider filtering by date range or specific models/providers.
    """)
    
    # Database statistics
    st.markdown("### 📊 Database Statistics")
    try:
        db_stats = storage.get_database_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", f"{db_stats.get('total_records', 0):,}")
        with col2:
            st.metric("Database Size", f"{db_stats.get('db_size_mb', 0):.2f} MB")
        with col3:
            st.metric("Models Tracked", len(db_stats.get('top_models', [])))
        
        # Provider breakdown
        st.markdown("#### Provider Distribution")
        provider_data = db_stats.get('provider_breakdown', [])
        if provider_data:
            provider_df = pd.DataFrame(provider_data)
            st.bar_chart(provider_df.set_index('provider')['count'])
        
        # Model breakdown
        st.markdown("#### Top Models")
        model_data = db_stats.get('top_models', [])
        if model_data:
            model_df = pd.DataFrame(model_data)
            st.bar_chart(model_df.set_index('model')['count'])
            
    except Exception as e:
        st.error(f"Error loading database statistics: {str(e)}")

if __name__ == "__main__":
    render_export_page()