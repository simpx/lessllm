#!/usr/bin/env python3
"""
Main Streamlit application for LessLLM analytics dashboard
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from gui.dashboard import render_dashboard
from gui.performance import render_performance_page
from gui.cache import render_cache_page
from gui.models import render_models_page
from gui.costs import render_costs_page
from gui.logs import render_logs_page
from gui.export import render_export_page

def main():
    st.set_page_config(
        page_title="LessLLM Analytics Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    # Custom CSS for better styling
    st.markdown("""
        <style>
        .main-header {
            font-size: 2rem;
            color: #4B8BBE;
            text-align: center;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 0.5rem;
            text-align: center;
        }
        .metric-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #4B8BBE;
        }
        .metric-label {
            font-size: 0.9rem;
            color: #666;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        [
            "Dashboard",
            "Performance Statistics",
            "Cache Analysis",
            "Model Usage",
            "Cost Analysis",
            "Recent Logs",
            "Data Export"
        ]
    )
    
    # Page title
    st.markdown(f"<h1 class='main-header'>LessLLM Analytics - {page}</h1>", unsafe_allow_html=True)
    
    # Render the selected page
    if page == "Dashboard":
        render_dashboard()
    elif page == "Performance Statistics":
        render_performance_page()
    elif page == "Cache Analysis":
        render_cache_page()
    elif page == "Model Usage":
        render_models_page()
    elif page == "Cost Analysis":
        render_costs_page()
    elif page == "Recent Logs":
        render_logs_page()
    elif page == "Data Export":
        render_export_page()

if __name__ == "__main__":
    main()