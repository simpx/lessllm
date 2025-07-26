"""
DuckDB storage system for API logs
"""

import duckdb
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from ..logging.models import APICallLog, BatchAnalysisSummary
import logging

logger = logging.getLogger(__name__)


class LogStorage:
    """DuckDB日志存储系统"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        """确保数据库目录存在"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self):
        """初始化数据库和表结构"""
        with duckdb.connect(self.db_path) as conn:
            # 创建主表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_calls (
                    -- 基础信息
                    timestamp TIMESTAMP,
                    request_id VARCHAR PRIMARY KEY,
                    provider VARCHAR,
                    model VARCHAR,
                    endpoint VARCHAR,
                    success BOOLEAN,
                    error_message TEXT,
                    
                    -- 原始API数据（JSON格式完整保存）
                    raw_request JSON,
                    raw_response JSON,
                    extracted_usage JSON,
                    extracted_cache_info JSON,
                    extracted_performance JSON,
                    
                    -- lessllm预估分析
                    estimated_ttft_ms INTEGER,
                    estimated_tpot_ms DOUBLE,
                    estimated_total_latency_ms INTEGER,
                    estimated_tokens_per_second DOUBLE,
                    estimated_cached_tokens INTEGER,
                    estimated_fresh_tokens INTEGER,
                    estimated_cache_hit_rate DOUBLE,
                    estimated_cost_usd DOUBLE,
                    
                    -- 从原始数据提取的关键字段（便于查询）
                    actual_prompt_tokens INTEGER,
                    actual_completion_tokens INTEGER,
                    actual_total_tokens INTEGER,
                    actual_cached_tokens INTEGER,
                    actual_cache_hit_rate DOUBLE,
                    
                    -- 环境信息
                    proxy_used VARCHAR,
                    user_id VARCHAR,
                    session_id VARCHAR,
                    analysis_timestamp TIMESTAMP
                );
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_model_timestamp ON api_calls(model, timestamp);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_performance ON api_calls(estimated_ttft_ms, estimated_tpot_ms);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_analysis ON api_calls(estimated_cache_hit_rate, actual_cache_hit_rate);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_provider_model ON api_calls(provider, model);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_session ON api_calls(user_id, session_id);")
            
            # 创建分析视图
            conn.execute("""
                CREATE VIEW IF NOT EXISTS cache_analysis_comparison AS
                SELECT 
                    request_id,
                    provider,
                    model,
                    estimated_cache_hit_rate,
                    actual_cache_hit_rate,
                    (actual_cache_hit_rate - estimated_cache_hit_rate) as hit_rate_diff,
                    ABS(actual_cache_hit_rate - estimated_cache_hit_rate) as prediction_error,
                    timestamp
                FROM api_calls 
                WHERE actual_cache_hit_rate IS NOT NULL;
            """)
            
            # 创建性能统计视图
            conn.execute("""
                CREATE VIEW IF NOT EXISTS performance_stats AS
                SELECT 
                    model,
                    provider,
                    DATE(timestamp) as date,
                    COUNT(*) as request_count,
                    AVG(estimated_ttft_ms) as avg_ttft_ms,
                    AVG(estimated_tpot_ms) as avg_tpot_ms,
                    AVG(estimated_total_latency_ms) as avg_latency_ms,
                    AVG(estimated_tokens_per_second) as avg_tokens_per_second,
                    SUM(actual_total_tokens) as total_tokens,
                    SUM(estimated_cost_usd) as total_cost_usd
                FROM api_calls 
                WHERE success = true
                GROUP BY model, provider, DATE(timestamp);
            """)
            
        logger.info(f"Database initialized at {self.db_path}")
    
    def store_log(self, log: APICallLog):
        """存储API调用日志"""
        try:
            # 确保提取了关键字段
            log.extract_key_fields()
            
            with duckdb.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO api_calls VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    log.timestamp,
                    log.request_id,
                    log.provider,
                    log.model,
                    log.endpoint,
                    log.success,
                    log.error_message,
                    json.dumps(log.raw_data.raw_request),
                    json.dumps(log.raw_data.raw_response),
                    json.dumps(log.raw_data.extracted_usage) if log.raw_data.extracted_usage else None,
                    json.dumps(log.raw_data.extracted_cache_info) if log.raw_data.extracted_cache_info else None,
                    json.dumps(log.raw_data.extracted_performance) if log.raw_data.extracted_performance else None,
                    log.estimated_analysis.estimated_performance.ttft_ms,
                    log.estimated_analysis.estimated_performance.tpot_ms,
                    log.estimated_analysis.estimated_performance.total_latency_ms,
                    log.estimated_analysis.estimated_performance.tokens_per_second,
                    log.estimated_analysis.estimated_cache.estimated_cached_tokens,
                    log.estimated_analysis.estimated_cache.estimated_fresh_tokens,
                    log.estimated_analysis.estimated_cache.estimated_cache_hit_rate,
                    log.estimated_analysis.estimated_cost_usd,
                    log.actual_prompt_tokens,
                    log.actual_completion_tokens,
                    log.actual_total_tokens,
                    log.actual_cached_tokens,
                    log.actual_cache_hit_rate,
                    log.proxy_used,
                    log.user_id,
                    log.session_id,
                    log.estimated_analysis.analysis_timestamp
                ))
            
            logger.debug(f"Stored log for request {log.request_id}")
            
        except Exception as e:
            logger.error(f"Failed to store log {log.request_id}: {e}")
            raise
    
    def query(self, sql: str, params: Optional[List] = None) -> List[Dict[str, Any]]:
        """执行SQL查询"""
        try:
            with duckdb.connect(self.db_path) as conn:
                if params:
                    result = conn.execute(sql, params).fetchdf()
                else:
                    result = conn.execute(sql).fetchdf()
                return result.to_dict('records')
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    def get_performance_stats(self, 
                            model: Optional[str] = None, 
                            provider: Optional[str] = None,
                            days: int = 7) -> Dict[str, Any]:
        """获取性能统计"""
        where_conditions = ["timestamp >= current_date - INTERVAL ? DAY"]
        params = [days]
        
        if model:
            where_conditions.append("model = ?")
            params.append(model)
            
        if provider:
            where_conditions.append("provider = ?")
            params.append(provider)
            
        where_clause = " AND ".join(where_conditions)
        
        sql = f"""
            SELECT 
                COUNT(*) as total_requests,
                COUNT(CASE WHEN success = true THEN 1 END) as successful_requests,
                AVG(estimated_ttft_ms) as avg_ttft_ms,
                AVG(estimated_tpot_ms) as avg_tpot_ms,
                AVG(estimated_total_latency_ms) as avg_latency_ms,
                AVG(estimated_tokens_per_second) as avg_tokens_per_second,
                AVG(estimated_cache_hit_rate) as avg_cache_hit_rate,
                SUM(actual_total_tokens) as total_tokens,
                SUM(estimated_cost_usd) as total_cost_usd
            FROM api_calls 
            WHERE {where_clause}
        """
        
        results = self.query(sql, params)
        return results[0] if results else {}
    
    def get_cache_analysis_summary(self, days: int = 7) -> Dict[str, Any]:
        """获取缓存分析摘要"""
        sql = """
            SELECT 
                COUNT(*) as total_predictions,
                AVG(prediction_error) as avg_prediction_error,
                MIN(prediction_error) as min_prediction_error,
                MAX(prediction_error) as max_prediction_error,
                COUNT(CASE WHEN prediction_error < 0.1 THEN 1 END) as accurate_predictions,
                AVG(estimated_cache_hit_rate) as avg_estimated_hit_rate,
                AVG(actual_cache_hit_rate) as avg_actual_hit_rate
            FROM cache_analysis_comparison
            WHERE timestamp >= current_date - INTERVAL ? DAY
        """
        
        results = self.query(sql, [days])
        summary = results[0] if results else {}
        
        # 计算准确性百分比
        if summary.get('total_predictions', 0) > 0:
            summary['accuracy_percentage'] = (summary.get('accurate_predictions', 0) / summary['total_predictions']) * 100
        
        return summary
    
    def export_parquet(self, filepath: str, **filters):
        """导出数据到Parquet文件"""
        where_conditions = []
        params = []
        
        for key, value in filters.items():
            if key == "start_date":
                where_conditions.append("timestamp >= ?")
                params.append(value)
            elif key == "end_date":
                where_conditions.append("timestamp <= ?")
                params.append(value)
            elif key == "model":
                if isinstance(value, list):
                    placeholders = ",".join(["?" for _ in value])
                    where_conditions.append(f"model IN ({placeholders})")
                    params.extend(value)
                else:
                    where_conditions.append("model = ?")
                    params.append(value)
            elif key == "provider":
                if isinstance(value, list):
                    placeholders = ",".join(["?" for _ in value])
                    where_conditions.append(f"provider IN ({placeholders})")
                    params.extend(value)
                else:
                    where_conditions.append("provider = ?")
                    params.append(value)
            elif key == "success_only" and value:
                where_conditions.append("success = true")
                
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        sql = f"COPY (SELECT * FROM api_calls{where_clause}) TO '{filepath}' (FORMAT PARQUET)"
        
        try:
            with duckdb.connect(self.db_path) as conn:
                conn.execute(sql, params)
            logger.info(f"Data exported to {filepath}")
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的日志记录"""
        sql = """
            SELECT 
                timestamp,
                request_id,
                provider,
                model,
                success,
                estimated_ttft_ms,
                estimated_tpot_ms,
                estimated_total_latency_ms,
                estimated_cache_hit_rate,
                actual_total_tokens,
                estimated_cost_usd
            FROM api_calls 
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        
        return self.query(sql, [limit])
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """清理旧日志记录"""
        sql = "DELETE FROM api_calls WHERE timestamp < current_date - INTERVAL ? DAY"
        
        try:
            with duckdb.connect(self.db_path) as conn:
                result = conn.execute(sql, [days_to_keep])
                deleted_count = result.fetchone()[0] if result else 0
            
            logger.info(f"Cleaned up {deleted_count} old log records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            raise
    
    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        stats = {}
        
        # 总记录数
        total_records = self.query("SELECT COUNT(*) as count FROM api_calls")[0]['count']
        stats['total_records'] = total_records
        
        # 按提供商统计
        provider_stats = self.query("""
            SELECT provider, COUNT(*) as count 
            FROM api_calls 
            GROUP BY provider 
            ORDER BY count DESC
        """)
        stats['provider_breakdown'] = provider_stats
        
        # 按模型统计
        model_stats = self.query("""
            SELECT model, COUNT(*) as count 
            FROM api_calls 
            GROUP BY model 
            ORDER BY count DESC 
            LIMIT 10
        """)
        stats['top_models'] = model_stats
        
        # 数据库文件大小
        db_path = Path(self.db_path)
        if db_path.exists():
            stats['db_size_mb'] = db_path.stat().st_size / (1024 * 1024)
        
        return stats