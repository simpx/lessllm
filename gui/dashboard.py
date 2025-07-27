"""
Streamlit app for LessLLM analytics dashboard
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os
import json

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from lessllm.logging.storage import LogStorage
from lessllm.config import get_config

def init_storage():
    """初始化存储连接"""
    try:
        config = get_config()
        db_path = config.logging.storage.get("db_path", "./lessllm_logs.db")
        return LogStorage(db_path)
    except Exception as e:
        st.error(f"Failed to initialize storage: {e}")
        return None

def load_data(storage, start_date, end_date):
    """加载指定日期范围的数据"""
    try:
        # 构建SQL查询
        sql = """
            SELECT * FROM api_calls 
            WHERE timestamp >= ? AND timestamp <= ?
        """
        params = [start_date, end_date]
        
        # 执行查询
        data = storage.query(sql, params)
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

def format_currency(value):
    """格式化货币显示"""
    if pd.isna(value) or value == 0:
        return "N/A"
    elif value < 0.0001:
        return f"${value:.6f}"
    else:
        return f"${value:.4f}"

def format_time_ms(value):
    """格式化时间显示"""
    if pd.isna(value):
        return "N/A"
    elif value < 1:
        return f"{value:.2f}ms"
    else:
        return f"{value:.0f}ms"

def main():
    st.set_page_config(
        page_title="LessLLM Analytics Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 隐藏主菜单和页脚以节省空间
    hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        [data-testid="stSidebar"] {
            background-color: #f0f2f6;
        }
        [data-testid="stMetricValue"] {
            font-size: 16px;
        }
        [data-testid="stMetricLabel"] {
            font-size: 14px;
        }
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center; margin-bottom: 10px;'>📊 LessLLM Analytics</h1>", unsafe_allow_html=True)
    
    # 初始化存储
    storage = init_storage()
    if not storage:
        st.error("无法连接到数据库，请检查配置")
        return
    
    # 侧边栏过滤器
    with st.sidebar:
        st.header("过滤器")
        
        # 日期范围选择
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        start_date = st.date_input("开始日期", start_date)
        end_date = st.date_input("结束日期", end_date)
        
        # 转换为datetime格式
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # 刷新按钮
        refresh = st.button("🔄 刷新数据")
    
    # 加载数据
    with st.spinner("正在加载数据..."):
        df = load_data(storage, start_datetime, end_datetime)
    
    if df.empty:
        st.info("所选日期范围内没有数据")
        return
    
    # 显示关键指标
    st.markdown("### 关键指标")
    
    # 计算关键指标
    total_requests = len(df)
    successful_requests = len(df[df['success'] == True])
    success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
    total_cost = df['estimated_cost_usd'].sum()
    total_tokens = df['actual_total_tokens'].sum()
    
    # 使用紧凑的指标布局
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("总请求数", total_requests)
    col2.metric("成功率", f"{success_rate:.1f}%")
    col3.metric("成功数", successful_requests)
    col4.metric("总成本", format_currency(total_cost))
    col5.metric("总Token", f"{total_tokens:,}")
    
    # 创建紧凑的两行布局
    # 第一行：性能统计和缓存分析
    st.markdown("### 性能与缓存")
    perf_col, cache_col = st.columns(2)
    
    with perf_col:
        if not df[df['success'] == True].empty:
            successful_df = df[df['success'] == True]
            
            # TTFT和TPOT分布（并排显示）
            ttft_tpot_col1, ttft_tpot_col2 = st.columns(2)
            
            with ttft_tpot_col1:
                fig_ttft = px.histogram(
                    successful_df, 
                    x='estimated_ttft_ms', 
                    title="TTFT分布",
                    labels={'estimated_ttft_ms': 'TTFT (ms)'}
                )
                fig_ttft.update_layout(
                    margin=dict(l=10, r=10, t=30, b=10),
                    height=200
                )
                st.plotly_chart(fig_ttft, use_container_width=True, config={'displayModeBar': False})
            
            with ttft_tpot_col2:
                fig_tpot = px.histogram(
                    successful_df,
                    x='estimated_tpot_ms',
                    title="TPOT分布",
                    labels={'estimated_tpot_ms': 'TPOT (ms)'}
                )
                fig_tpot.update_layout(
                    margin=dict(l=10, r=10, t=30, b=10),
                    height=200
                )
                st.plotly_chart(fig_tpot, use_container_width=True, config={'displayModeBar': False})
            
            # 模型性能对比
            model_perf = successful_df.groupby('model').agg({
                'estimated_ttft_ms': 'mean',
                'estimated_tpot_ms': 'mean',
                'estimated_total_latency_ms': 'mean'
            }).reset_index()
            
            # 转换数据类型确保一致性
            numeric_columns = ['estimated_ttft_ms', 'estimated_tpot_ms', 'estimated_total_latency_ms']
            for col in numeric_columns:
                model_perf[col] = pd.to_numeric(model_perf[col], errors='coerce')
            
            # 使用长格式数据
            model_perf_melted = model_perf.melt(
                id_vars=['model'],
                value_vars=['estimated_ttft_ms', 'estimated_tpot_ms', 'estimated_total_latency_ms'],
                var_name='metric',
                value_name='value'
            )
            fig_model_perf = px.bar(
                model_perf_melted,
                x='model',
                y='value',
                color='metric',
                title="模型性能对比",
                barmode='group'
            )
            fig_model_perf.update_layout(
                margin=dict(l=10, r=10, t=30, b=10),
                height=250,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            st.plotly_chart(fig_model_perf, use_container_width=True, config={'displayModeBar': False})
    
    with cache_col:
        # 过滤有缓存数据的记录
        cache_df = df[(df['success'] == True) & (df['actual_cache_hit_rate'].notna())]
        
        if not cache_df.empty:
            # 缓存命中率分布
            fig_cache_rate = px.histogram(
                cache_df,
                x='actual_cache_hit_rate',
                title="缓存命中率分布",
                labels={'actual_cache_hit_rate': '命中率'}
            )
            fig_cache_rate.update_xaxes(range=[0, 1])
            fig_cache_rate.update_layout(
                margin=dict(l=10, r=10, t=30, b=10),
                height=200
            )
            st.plotly_chart(fig_cache_rate, use_container_width=True, config={'displayModeBar': False})
            
            # 估算vs实际缓存命中率对比
            fig_cache_compare = px.scatter(
                cache_df,
                x='estimated_cache_hit_rate',
                y='actual_cache_hit_rate',
                title="估算vs实际命中率",
                labels={
                    'estimated_cache_hit_rate': '估算',
                    'actual_cache_hit_rate': '实际'
                }
            )
            fig_cache_compare.add_shape(
                type='line',
                x0=0, x1=1, y0=0, y1=1,
                line=dict(color='red', dash='dash')
            )
            fig_cache_compare.update_layout(
                margin=dict(l=10, r=10, t=30, b=10),
                height=250
            )
            st.plotly_chart(fig_cache_compare, use_container_width=True, config={'displayModeBar': False})
    
    # 第二行：成本分析和模型使用情况
    st.markdown("### 成本与使用")
    cost_col, usage_col = st.columns(2)
    
    with cost_col:
        # 按模型分组的成本统计
        cost_by_model = df.groupby('model').agg({
            'estimated_cost_usd': 'sum',
            'actual_total_tokens': 'sum'
        }).reset_index()
        
        if not cost_by_model.empty:
            # 模型成本分布
            fig_cost_model = px.pie(
                cost_by_model,
                values='estimated_cost_usd',
                names='model',
                title="成本分布"
            )
            fig_cost_model.update_layout(
                margin=dict(l=10, r=10, t=30, b=10),
                height=250
            )
            st.plotly_chart(fig_cost_model, use_container_width=True, config={'displayModeBar': False})
    
    with usage_col:
        model_usage = df.groupby('model').size().reset_index(name='count')
        fig_model_usage = px.pie(
            model_usage,
            values='count',
            names='model',
            title="使用分布"
        )
        fig_model_usage.update_layout(
            margin=dict(l=10, r=10, t=30, b=10),
            height=250
        )
        st.plotly_chart(fig_model_usage, use_container_width=True, config={'displayModeBar': False})
    
    # 最近日志
    st.markdown("### 最近请求")
    
    # 选择要显示的列
    display_columns = [
        'timestamp', 'request_id', 'provider', 'model', 'success', 
        'estimated_ttft_ms', 'actual_total_tokens', 'estimated_cost_usd'
    ]
    
    # 格式化数据显示
    log_df = df[display_columns].copy()
    log_df['timestamp'] = pd.to_datetime(log_df['timestamp']).dt.strftime('%m-%d %H:%M:%S')
    log_df['estimated_cost_usd'] = log_df['estimated_cost_usd'].apply(format_currency)
    log_df['estimated_ttft_ms'] = log_df['estimated_ttft_ms'].apply(format_time_ms)
    
    # 显示最近20条记录
    recent_df = log_df.tail(20).reset_index(drop=True)
    
    # 显示数据表格
    st.dataframe(
        recent_df, 
        use_container_width=True, 
        height=300,
        column_config={
            "timestamp": "时间",
            "request_id": "请求ID", 
            "provider": "提供商",
            "model": "模型",
            "success": "成功",
            "estimated_ttft_ms": "TTFT",
            "actual_total_tokens": "Tokens",
            "estimated_cost_usd": "成本"
        }
    )
    
    # 添加请求ID选择器来查看详情
    st.markdown("### 🔍 查看请求详情")
    
    if not recent_df.empty:
        request_ids = recent_df['request_id'].tolist()
        selected_request_id = st.selectbox(
            "选择请求ID查看详情",
            options=request_ids,
            index=0,
            key="request_detail_selector"
        )
        
        if selected_request_id:
            # 查询完整的请求详情
            detail_sql = "SELECT * FROM api_calls WHERE request_id = ?"
            detail_result = storage.query(detail_sql, [selected_request_id])
            
            if detail_result:
                detail = detail_result[0]
                
                st.markdown("### 📋 请求详情")
                
                # 基本信息
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("请求ID", detail['request_id'])
                    st.metric("提供商", detail['provider'])
                with col2:
                    st.metric("模型", detail['model'])
                    st.metric("状态", "✅ 成功" if detail['success'] else "❌ 失败")
                with col3:
                    st.metric("代理", detail['proxy_used'] or "直连")
                    if detail['error_message']:
                        st.error(f"错误: {detail['error_message']}")
                
                # 详细数据展示
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["📤 请求数据", "📥 响应数据", "🌐 HTTP 详情", "📊 性能指标", "💰 成本分析"])
                
                with tab1:
                    st.markdown("**原始请求数据:**")
                    if detail['raw_request']:
                        try:
                            request_data = json.loads(detail['raw_request'])
                            st.json(request_data)
                        except:
                            st.text(detail['raw_request'])
                    else:
                        st.info("无请求数据")
                
                with tab2:
                    st.markdown("**原始响应数据:**")
                    if detail['raw_response']:
                        try:
                            response_data = json.loads(detail['raw_response'])
                            st.json(response_data)
                        except:
                            st.text(detail['raw_response'])
                    else:
                        st.info("无响应数据")
                
                with tab3:
                    st.markdown("**HTTP 请求详情:**")
                    
                    # 基本请求信息
                    req_col1, req_col2 = st.columns(2)
                    with req_col1:
                        st.metric("请求方法", detail.get('request_method', 'N/A'))
                        st.metric("客户端 IP", detail.get('client_ip', 'N/A'))
                        st.metric("状态码", detail.get('response_status_code', 'N/A'))
                    with req_col2:
                        st.metric("响应大小", f"{detail.get('response_size_bytes', 0)} bytes" if detail.get('response_size_bytes') else 'N/A')
                        st.metric("上游状态码", detail.get('upstream_status_code', 'N/A'))
                        st.metric("上游 URL", detail.get('upstream_url', 'N/A'))
                    
                    # 请求头
                    st.markdown("**请求头:**")
                    if detail.get('request_headers'):
                        try:
                            request_headers = json.loads(detail['request_headers']) if isinstance(detail['request_headers'], str) else detail['request_headers']
                            st.json(request_headers)
                        except:
                            st.text(str(detail['request_headers']))
                    else:
                        st.info("无请求头数据")
                    
                    # 响应头
                    st.markdown("**响应头:**")
                    if detail.get('response_headers'):
                        try:
                            response_headers = json.loads(detail['response_headers']) if isinstance(detail['response_headers'], str) else detail['response_headers']
                            st.json(response_headers)
                        except:
                            st.text(str(detail['response_headers']))
                    else:
                        st.info("无响应头数据")
                    
                    # 上游请求/响应头
                    if detail.get('upstream_request_headers') or detail.get('upstream_response_headers'):
                        st.markdown("**上游 HTTP 详情:**")
                        upstream_col1, upstream_col2 = st.columns(2)
                        
                        with upstream_col1:
                            st.markdown("**上游请求头:**")
                            if detail.get('upstream_request_headers'):
                                try:
                                    upstream_req_headers = json.loads(detail['upstream_request_headers']) if isinstance(detail['upstream_request_headers'], str) else detail['upstream_request_headers']
                                    st.json(upstream_req_headers)
                                except:
                                    st.text(str(detail['upstream_request_headers']))
                            else:
                                st.info("无上游请求头")
                        
                        with upstream_col2:
                            st.markdown("**上游响应头:**")
                            if detail.get('upstream_response_headers'):
                                try:
                                    upstream_resp_headers = json.loads(detail['upstream_response_headers']) if isinstance(detail['upstream_response_headers'], str) else detail['upstream_response_headers']
                                    st.json(upstream_resp_headers)
                                except:
                                    st.text(str(detail['upstream_response_headers']))
                            else:
                                st.info("无上游响应头")
                
                with tab4:
                    perf_col1, perf_col2 = st.columns(2)
                    with perf_col1:
                        st.metric("首字节时间 (TTFT)", format_time_ms(detail['estimated_ttft_ms']))
                        st.metric("每token时间 (TPOT)", format_time_ms(detail['estimated_tpot_ms']))
                    with perf_col2:
                        st.metric("总延迟", format_time_ms(detail['estimated_total_latency_ms']))
                        st.metric("吞吐量", f"{detail['estimated_tokens_per_second']:.1f} tokens/s" if detail['estimated_tokens_per_second'] else "N/A")
                    
                    # 缓存信息
                    if detail['estimated_cache_hit_rate'] is not None:
                        cache_col1, cache_col2 = st.columns(2)
                        with cache_col1:
                            st.metric("估算缓存命中率", f"{detail['estimated_cache_hit_rate']:.1%}")
                            st.metric("估算缓存Token", detail['estimated_cached_tokens'])
                        with cache_col2:
                            if detail['actual_cache_hit_rate'] is not None:
                                st.metric("实际缓存命中率", f"{detail['actual_cache_hit_rate']:.1%}")
                                st.metric("实际缓存Token", detail['actual_cached_tokens'])
                
                with tab5:
                    cost_col1, cost_col2 = st.columns(2)
                    with cost_col1:
                        st.metric("估算成本", format_currency(detail['estimated_cost_usd']))
                        st.metric("输入Token", detail['actual_prompt_tokens'] or "N/A")
                    with cost_col2:
                        st.metric("输出Token", detail['actual_completion_tokens'] or "N/A")
                        st.metric("总Token", detail['actual_total_tokens'] or "N/A")
    else:
        st.info("暂无日志数据")
    
    # SQL 查询功能
    st.markdown("### SQL 查询")
    
    # 创建展开式 SQL 查询区域
    with st.expander("🔍 自定义 SQL 查询", expanded=False):
        
        # 预定义的常用查询
        st.markdown("**常用查询模板：**")
        
        template_options = {
            "选择模板...": "",
            "性能分析 - 按模型": """
SELECT 
    model,
    COUNT(*) as request_count,
    AVG(estimated_ttft_ms) as avg_ttft_ms,
    AVG(estimated_tpot_ms) as avg_tpot_ms,
    AVG(estimated_total_latency_ms) as avg_latency_ms,
    SUM(estimated_cost_usd) as total_cost_usd
FROM api_calls 
WHERE success = true 
GROUP BY model 
ORDER BY request_count DESC""",
            "缓存命中率分析": """
SELECT 
    model,
    provider,
    COUNT(*) as total_requests,
    AVG(estimated_cache_hit_rate) as avg_estimated_hit_rate,
    AVG(actual_cache_hit_rate) as avg_actual_hit_rate,
    ABS(AVG(actual_cache_hit_rate) - AVG(estimated_cache_hit_rate)) as prediction_error
FROM api_calls 
WHERE actual_cache_hit_rate IS NOT NULL 
GROUP BY model, provider""",
            "成本分析": """
SELECT 
    DATE(timestamp) as date,
    model,
    SUM(estimated_cost_usd) as daily_cost,
    SUM(actual_total_tokens) as daily_tokens,
    COUNT(*) as daily_requests
FROM api_calls 
WHERE success = true 
GROUP BY DATE(timestamp), model 
ORDER BY date DESC, daily_cost DESC""",
            "错误分析": """
SELECT 
    provider,
    model,
    error_message,
    COUNT(*) as error_count,
    MIN(timestamp) as first_occurrence,
    MAX(timestamp) as last_occurrence
FROM api_calls 
WHERE success = false 
GROUP BY provider, model, error_message 
ORDER BY error_count DESC""",
            "最近活动": """
SELECT 
    timestamp,
    provider,
    model,
    success,
    estimated_ttft_ms,
    actual_total_tokens,
    estimated_cost_usd,
    proxy_used
FROM api_calls 
ORDER BY timestamp DESC 
LIMIT 50"""
        }
        
        selected_template = st.selectbox("选择查询模板", list(template_options.keys()))
        
        # 查询输入框
        if selected_template != "选择模板...":
            default_query = template_options[selected_template]
        else:
            default_query = "SELECT * FROM api_calls LIMIT 10"
            
        sql_query = st.text_area(
            "SQL 查询语句",
            value=default_query,
            height=150,
            help="可以查询 api_calls 表中的所有数据。支持标准 SQL 语法。"
        )
        
        # 执行查询按钮
        col1, col2 = st.columns([1, 4])
        
        with col1:
            execute_query = st.button("▶️ 执行查询", type="primary")
        
        with col2:
            if st.button("📊 表结构说明"):
                st.info("""
                **api_calls 表主要字段：**
                - timestamp: 请求时间
                - request_id: 请求ID
                - provider: 提供商 (openai, claude等)
                - model: 模型名称
                - success: 是否成功
                - estimated_ttft_ms: 估算首字节时间
                - estimated_tpot_ms: 估算每token时间
                - estimated_total_latency_ms: 估算总延迟
                - actual_total_tokens: 实际token数
                - estimated_cost_usd: 估算成本
                - actual_cache_hit_rate: 实际缓存命中率
                - proxy_used: 使用的代理
                """)
        
        # 执行查询
        if execute_query and sql_query.strip():
            try:
                with st.spinner("正在执行查询..."):
                    # 安全检查 - 只允许 SELECT 语句
                    if not sql_query.strip().upper().startswith('SELECT'):
                        st.error("为了安全起见，只允许执行 SELECT 查询语句")
                    else:
                        # 执行查询
                        query_result = storage.query(sql_query.strip())
                        
                        if query_result:
                            result_df = pd.DataFrame(query_result)
                            
                            # 显示结果统计
                            st.success(f"查询成功！返回 {len(result_df)} 行，{len(result_df.columns)} 列")
                            
                            # 显示结果
                            st.dataframe(
                                result_df,
                                use_container_width=True,
                                height=400
                            )
                            
                            # 下载选项
                            if len(result_df) > 0:
                                csv = result_df.to_csv(index=False)
                                st.download_button(
                                    label="📥 下载 CSV",
                                    data=csv,
                                    file_name=f"lessllm_query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv"
                                )
                        else:
                            st.info("查询执行成功，但没有返回数据")
                            
            except Exception as e:
                st.error(f"查询执行失败：{str(e)}")
                # 提供一些常见错误的解决建议
                if "no such table" in str(e).lower():
                    st.warning("表不存在。请确保数据库中有数据，或检查表名是否正确。")
                elif "syntax error" in str(e).lower():
                    st.warning("SQL 语法错误。请检查查询语句的语法。")

if __name__ == "__main__":
    main()