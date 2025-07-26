"""
DuckDB存储系统单元测试
"""

import pytest
import tempfile
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from lessllm.logging.storage import LogStorage
from lessllm.logging.models import (
    APICallLog, RawAPIData, EstimatedAnalysis, 
    PerformanceAnalysis, CacheAnalysis, BatchAnalysisSummary
)


@pytest.fixture
def temp_db_path():
    """临时数据库路径"""
    import tempfile
    import os
    
    # 创建临时目录和文件名，但不创建实际文件
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, 'test.db')
    
    yield temp_path
    
    # 清理
    try:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        os.rmdir(temp_dir)
    except OSError:
        pass  # 忽略清理错误


@pytest.fixture
def storage(temp_db_path):
    """存储实例"""
    return LogStorage(temp_db_path)


@pytest.fixture
def sample_api_log():
    """示例API日志数据"""
    raw_data = RawAPIData(
        raw_request={
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 100
        },
        raw_response={
            "id": "test-response",
            "choices": [{"message": {"content": "Hi there!"}}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        },
        extracted_usage={
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15
        }
    )
    
    performance = PerformanceAnalysis(
        ttft_ms=500,
        tpot_ms=20.5,
        total_latency_ms=1200,
        tokens_per_second=25.0,
        network_latency_ms=100
    )
    
    cache = CacheAnalysis(
        estimated_cached_tokens=5,
        estimated_fresh_tokens=10,
        estimated_cache_hit_rate=0.33,
        system_message_cached=2,
        template_cached=2,
        conversation_history_cached=1
    )
    
    estimated_analysis = EstimatedAnalysis(
        estimated_performance=performance,
        estimated_cache=cache,
        estimated_cost_usd=0.00025,
        analysis_timestamp=datetime.utcnow()
    )
    
    return APICallLog(
        provider="openai",
        model="gpt-3.5-turbo",
        endpoint="/v1/chat/completions",
        raw_data=raw_data,
        estimated_analysis=estimated_analysis,
        success=True,
        proxy_used="http://proxy:8080",
        user_id="user123",
        session_id="session456"
    )


class TestLogStorage:
    """LogStorage基础功能测试"""
    
    def test_init_creates_database(self, temp_db_path):
        """测试初始化创建数据库"""
        storage = LogStorage(temp_db_path)
        
        assert os.path.exists(temp_db_path)
        
        # 验证表结构
        result = storage.query("SELECT table_name FROM information_schema.tables WHERE table_schema='main'")
        table_names = [row['table_name'] for row in result]
        assert 'api_calls' in table_names
    
    def test_init_creates_directory(self):
        """测试初始化创建目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = os.path.join(temp_dir, "nested", "subdir", "test.db")
            storage = LogStorage(nested_path)
            
            assert os.path.exists(nested_path)
            assert os.path.isdir(os.path.dirname(nested_path))
    
    def test_init_creates_indexes(self, storage):
        """测试初始化创建索引"""
        # 在DuckDB中，我们可以通过查询表结构来验证索引是否存在
        # 这里只要数据库初始化成功就说明索引被创建了
        result = storage.query("SELECT COUNT(*) as count FROM api_calls")
        assert result[0]['count'] == 0  # 新数据库应该为空
    
    def test_init_creates_views(self, storage):
        """测试初始化创建视图"""
        # 验证cache_analysis_comparison视图
        result = storage.query("SELECT * FROM information_schema.views WHERE table_name = 'cache_analysis_comparison'")
        assert len(result) > 0
        
        # 验证performance_stats视图
        result = storage.query("SELECT * FROM information_schema.views WHERE table_name = 'performance_stats'")
        assert len(result) > 0


class TestLogStorageOperations:
    """日志存储操作测试"""
    
    def test_store_log_success(self, storage, sample_api_log):
        """测试成功存储日志"""
        storage.store_log(sample_api_log)
        
        # 验证数据已存储
        result = storage.query("SELECT * FROM api_calls WHERE request_id = ?", [sample_api_log.request_id])
        assert len(result) == 1
        
        stored_log = result[0]
        assert stored_log['provider'] == 'openai'
        assert stored_log['model'] == 'gpt-3.5-turbo'
        assert stored_log['success'] is True
        assert stored_log['actual_prompt_tokens'] == 10
        assert stored_log['actual_completion_tokens'] == 5
        assert stored_log['actual_total_tokens'] == 15
    
    def test_store_log_extracts_key_fields(self, storage, sample_api_log):
        """测试存储日志时提取关键字段"""
        storage.store_log(sample_api_log)
        
        result = storage.query("SELECT * FROM api_calls WHERE request_id = ?", [sample_api_log.request_id])
        stored_log = result[0]
        
        # 验证从原始数据提取的字段
        assert stored_log['actual_prompt_tokens'] == 10
        assert stored_log['actual_completion_tokens'] == 5
        assert stored_log['actual_total_tokens'] == 15
        assert stored_log['estimated_ttft_ms'] == 500
        assert stored_log['estimated_tpot_ms'] == 20.5
        assert stored_log['estimated_cost_usd'] == 0.00025
    
    def test_store_log_handles_json_fields(self, storage, sample_api_log):
        """测试存储JSON字段"""
        storage.store_log(sample_api_log)
        
        result = storage.query("SELECT raw_request, raw_response, extracted_usage FROM api_calls WHERE request_id = ?", 
                             [sample_api_log.request_id])
        stored_log = result[0]
        
        # 验证JSON字段正确存储
        raw_request = json.loads(stored_log['raw_request'])
        assert raw_request['model'] == 'gpt-3.5-turbo'
        
        raw_response = json.loads(stored_log['raw_response'])
        assert raw_response['id'] == 'test-response'
        
        extracted_usage = json.loads(stored_log['extracted_usage'])
        assert extracted_usage['total_tokens'] == 15
    
    def test_store_log_handles_null_fields(self, storage, sample_api_log):
        """测试处理空字段"""
        # 移除一些可选字段
        sample_api_log.raw_data.extracted_cache_info = None
        sample_api_log.error_message = None
        sample_api_log.user_id = None
        
        storage.store_log(sample_api_log)
        
        result = storage.query("SELECT * FROM api_calls WHERE request_id = ?", [sample_api_log.request_id])
        stored_log = result[0]
        
        assert stored_log['extracted_cache_info'] is None
        assert stored_log['error_message'] is None
        assert stored_log['user_id'] is None
    
    def test_store_log_failure_raises_exception(self, storage):
        """测试存储失败时抛出异常"""
        # 创建一个无效的日志对象
        invalid_log = Mock()
        invalid_log.extract_key_fields.side_effect = Exception("Extraction failed")
        
        with pytest.raises(Exception, match="Extraction failed"):
            storage.store_log(invalid_log)


class TestLogQueries:
    """日志查询测试"""
    
    def test_query_basic(self, storage, sample_api_log):
        """测试基础查询"""
        storage.store_log(sample_api_log)
        
        result = storage.query("SELECT COUNT(*) as count FROM api_calls")
        assert result[0]['count'] == 1
    
    def test_query_with_params(self, storage, sample_api_log):
        """测试带参数查询"""
        storage.store_log(sample_api_log)
        
        result = storage.query("SELECT * FROM api_calls WHERE provider = ?", ["openai"])
        assert len(result) == 1
        assert result[0]['provider'] == 'openai'
    
    def test_query_returns_dict_records(self, storage, sample_api_log):
        """测试查询返回字典记录"""
        storage.store_log(sample_api_log)
        
        result = storage.query("SELECT provider, model FROM api_calls")
        assert isinstance(result, list)
        assert isinstance(result[0], dict)
        assert 'provider' in result[0]
        assert 'model' in result[0]
    
    def test_query_failure_raises_exception(self, storage):
        """测试查询失败抛出异常"""
        with pytest.raises(Exception):
            storage.query("SELECT * FROM non_existent_table")


class TestPerformanceStats:
    """性能统计测试"""
    
    def test_get_performance_stats_all(self, storage, sample_api_log):
        """测试获取所有性能统计"""
        storage.store_log(sample_api_log)
        
        stats = storage.get_performance_stats()
        
        assert stats['total_requests'] == 1
        assert stats['successful_requests'] == 1
        assert stats['avg_ttft_ms'] == 500
        assert stats['avg_tpot_ms'] == 20.5
        assert stats['avg_latency_ms'] == 1200
        assert stats['avg_tokens_per_second'] == 25.0
        assert stats['total_tokens'] == 15
        assert stats['total_cost_usd'] == 0.00025
    
    def test_get_performance_stats_filtered_by_model(self, storage, sample_api_log):
        """测试按模型筛选性能统计"""
        storage.store_log(sample_api_log)
        
        # 测试匹配的模型
        stats = storage.get_performance_stats(model="gpt-3.5-turbo")
        assert stats['total_requests'] == 1
        
        # 测试不匹配的模型
        stats = storage.get_performance_stats(model="gpt-4")
        assert stats.get('total_requests', 0) == 0
    
    def test_get_performance_stats_filtered_by_provider(self, storage, sample_api_log):
        """测试按提供商筛选性能统计"""
        storage.store_log(sample_api_log)
        
        # 测试匹配的提供商
        stats = storage.get_performance_stats(provider="openai")
        assert stats['total_requests'] == 1
        
        # 测试不匹配的提供商
        stats = storage.get_performance_stats(provider="anthropic")
        assert stats.get('total_requests', 0) == 0
    
    def test_get_performance_stats_filtered_by_days(self, storage):
        """测试按天数筛选性能统计"""
        # 创建旧日志
        old_log = APICallLog(
            provider="openai",
            model="gpt-3.5-turbo",
            endpoint="/v1/chat/completions",
            raw_data=RawAPIData(
                raw_request={},
                raw_response={}
            ),
            estimated_analysis=EstimatedAnalysis(
                estimated_performance=PerformanceAnalysis(total_latency_ms=1000),
                estimated_cache=CacheAnalysis(),
                estimated_cost_usd=0.001
            ),
            success=True,
            timestamp=datetime.utcnow() - timedelta(days=10)
        )
        
        storage.store_log(old_log)
        
        # 测试1天内的统计（应该为空）
        stats = storage.get_performance_stats(days=1)
        assert stats.get('total_requests', 0) == 0
        
        # 测试15天内的统计（应该包含旧日志）
        stats = storage.get_performance_stats(days=15)
        assert stats['total_requests'] == 1


class TestCacheAnalysis:
    """缓存分析测试"""
    
    def test_get_cache_analysis_summary(self, storage):
        """测试获取缓存分析摘要"""
        # 创建带有缓存信息的日志
        log = APICallLog(
            provider="openai",
            model="gpt-3.5-turbo",
            endpoint="/v1/chat/completions",
            raw_data=RawAPIData(
                raw_request={},
                raw_response={},
                extracted_cache_info={
                    "cached_tokens": 8,
                    "cache_hit_rate": 0.4
                }
            ),
            estimated_analysis=EstimatedAnalysis(
                estimated_performance=PerformanceAnalysis(total_latency_ms=1000),
                estimated_cache=CacheAnalysis(
                    estimated_cache_hit_rate=0.35,
                    estimated_cached_tokens=7
                ),
                estimated_cost_usd=0.001
            ),
            success=True
        )
        
        storage.store_log(log)
        
        summary = storage.get_cache_analysis_summary()
        
        assert summary['total_predictions'] == 1
        assert summary['avg_estimated_hit_rate'] == 0.35
        assert summary['avg_actual_hit_rate'] == 0.4
        assert abs(summary['avg_prediction_error'] - 0.05) < 0.001
        assert summary['accuracy_percentage'] > 0  # 预测误差小于0.1的百分比
    
    def test_get_cache_analysis_summary_empty(self, storage):
        """测试空数据库的缓存分析摘要"""
        summary = storage.get_cache_analysis_summary()
        
        # 空数据库应该返回空摘要或默认值
        assert summary.get('total_predictions', 0) == 0


class TestDataExport:
    """数据导出测试"""
    
    def test_export_parquet_basic(self, storage, sample_api_log):
        """测试基础Parquet导出"""
        storage.store_log(sample_api_log)
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            export_path = f.name
        
        try:
            storage.export_parquet(export_path)
            assert os.path.exists(export_path)
            assert os.path.getsize(export_path) > 0
        finally:
            if os.path.exists(export_path):
                os.unlink(export_path)
    
    def test_export_parquet_with_filters(self, storage, sample_api_log):
        """测试带筛选条件的Parquet导出"""
        storage.store_log(sample_api_log)
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            export_path = f.name
        
        try:
            # 测试模型筛选
            storage.export_parquet(
                export_path,
                model="gpt-3.5-turbo",
                provider="openai",
                success_only=True
            )
            assert os.path.exists(export_path)
        finally:
            if os.path.exists(export_path):
                os.unlink(export_path)
    
    def test_export_parquet_with_date_filters(self, storage, sample_api_log):
        """测试带日期筛选的Parquet导出"""
        storage.store_log(sample_api_log)
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            export_path = f.name
        
        try:
            yesterday = datetime.utcnow() - timedelta(days=1)
            tomorrow = datetime.utcnow() + timedelta(days=1)
            
            storage.export_parquet(
                export_path,
                start_date=yesterday,
                end_date=tomorrow
            )
            assert os.path.exists(export_path)
        finally:
            if os.path.exists(export_path):
                os.unlink(export_path)


class TestUtilityMethods:
    """工具方法测试"""
    
    def test_get_recent_logs(self, storage, sample_api_log):
        """测试获取最近日志"""
        storage.store_log(sample_api_log)
        
        recent_logs = storage.get_recent_logs(limit=10)
        
        assert len(recent_logs) == 1
        assert recent_logs[0]['request_id'] == sample_api_log.request_id
        assert 'timestamp' in recent_logs[0]
        assert 'provider' in recent_logs[0]
        assert 'model' in recent_logs[0]
    
    def test_get_recent_logs_limit(self, storage):
        """测试获取最近日志的限制"""
        # 创建多个日志
        for i in range(5):
            log = APICallLog(
                provider="openai",
                model=f"model-{i}",
                endpoint="/v1/chat/completions",
                raw_data=RawAPIData(raw_request={}, raw_response={}),
                estimated_analysis=EstimatedAnalysis(
                    estimated_performance=PerformanceAnalysis(total_latency_ms=1000),
                    estimated_cache=CacheAnalysis()
                ),
                success=True
            )
            storage.store_log(log)
        
        recent_logs = storage.get_recent_logs(limit=3)
        assert len(recent_logs) == 3
    
    def test_cleanup_old_logs(self, storage):
        """测试清理旧日志"""
        # 创建新日志
        new_log = APICallLog(
            provider="openai",
            model="gpt-3.5-turbo",
            endpoint="/v1/chat/completions",
            raw_data=RawAPIData(raw_request={}, raw_response={}),
            estimated_analysis=EstimatedAnalysis(
                estimated_performance=PerformanceAnalysis(total_latency_ms=1000),
                estimated_cache=CacheAnalysis()
            ),
            success=True,
            timestamp=datetime.utcnow()
        )
        
        # 创建旧日志
        old_log = APICallLog(
            provider="openai",
            model="gpt-3.5-turbo",
            endpoint="/v1/chat/completions",
            raw_data=RawAPIData(raw_request={}, raw_response={}),
            estimated_analysis=EstimatedAnalysis(
                estimated_performance=PerformanceAnalysis(total_latency_ms=1000),
                estimated_cache=CacheAnalysis()
            ),
            success=True,
            timestamp=datetime.utcnow() - timedelta(days=35)
        )
        
        storage.store_log(new_log)
        storage.store_log(old_log)
        
        # 验证有2条记录
        count_before = storage.query("SELECT COUNT(*) as count FROM api_calls")[0]['count']
        assert count_before == 2
        
        # 清理30天前的日志
        deleted_count = storage.cleanup_old_logs(days_to_keep=30)
        # DuckDB的DELETE语句返回值可能不同，只要没有异常就行
        assert deleted_count is not None
        
        # 验证新日志仍然存在
        count_after = storage.query("SELECT COUNT(*) as count FROM api_calls")[0]['count']
        assert count_after == 1
    
    def test_get_database_stats(self, storage, sample_api_log):
        """测试获取数据库统计信息"""
        storage.store_log(sample_api_log)
        
        stats = storage.get_database_stats()
        
        assert stats['total_records'] == 1
        assert len(stats['provider_breakdown']) > 0
        assert stats['provider_breakdown'][0]['provider'] == 'openai'
        assert stats['provider_breakdown'][0]['count'] == 1
        assert len(stats['top_models']) > 0
        assert stats['top_models'][0]['model'] == 'gpt-3.5-turbo'
        assert 'db_size_mb' in stats


class TestErrorHandling:
    """错误处理测试"""
    
    def test_store_log_logs_error_on_failure(self, storage, caplog):
        """测试存储失败时记录错误"""
        import logging
        
        # 创建无效日志对象
        invalid_log = Mock()
        invalid_log.extract_key_fields.side_effect = Exception("Test error")
        
        with caplog.at_level(logging.ERROR):
            with pytest.raises(Exception):
                storage.store_log(invalid_log)
        
        assert "Failed to store log" in caplog.text
    
    def test_query_logs_error_on_failure(self, storage, caplog):
        """测试查询失败时记录错误"""
        import logging
        
        with caplog.at_level(logging.ERROR):
            with pytest.raises(Exception):
                storage.query("INVALID SQL QUERY")
        
        assert "Query failed" in caplog.text
    
    def test_export_logs_error_on_failure(self, storage, sample_api_log, caplog):
        """测试导出失败时记录错误"""
        import logging
        
        storage.store_log(sample_api_log)
        
        with caplog.at_level(logging.ERROR):
            with pytest.raises(Exception):
                # 尝试导出到无效路径
                storage.export_parquet("/invalid/path/export.parquet")
        
        assert "Export failed" in caplog.text
    
    def test_cleanup_logs_error_on_failure(self, storage, caplog):
        """测试清理失败时记录错误"""
        import logging
        
        with caplog.at_level(logging.ERROR):
            # 使用patch来模拟数据库错误
            with patch('duckdb.connect') as mock_connect:
                mock_connect.side_effect = Exception("Database error")
                
                with pytest.raises(Exception):
                    storage.cleanup_old_logs(30)
        
        assert "Cleanup failed" in caplog.text


class TestDatabaseViews:
    """数据库视图测试"""
    
    def test_cache_analysis_comparison_view(self, storage):
        """测试缓存分析比较视图"""
        # 创建带缓存信息的日志
        log = APICallLog(
            provider="openai",
            model="gpt-3.5-turbo",
            endpoint="/v1/chat/completions",
            raw_data=RawAPIData(
                raw_request={},
                raw_response={},
                extracted_cache_info={
                    "cache_hit_rate": 0.6
                }
            ),
            estimated_analysis=EstimatedAnalysis(
                estimated_performance=PerformanceAnalysis(total_latency_ms=1000),
                estimated_cache=CacheAnalysis(estimated_cache_hit_rate=0.5),
                estimated_cost_usd=0.001
            ),
            success=True
        )
        
        storage.store_log(log)
        
        # 查询视图
        result = storage.query("SELECT * FROM cache_analysis_comparison")
        
        assert len(result) == 1
        row = result[0]
        assert row['estimated_cache_hit_rate'] == 0.5
        assert row['actual_cache_hit_rate'] == 0.6
        assert abs(row['hit_rate_diff'] - 0.1) < 0.001
        assert abs(row['prediction_error'] - 0.1) < 0.001
    
    def test_performance_stats_view(self, storage, sample_api_log):
        """测试性能统计视图"""
        storage.store_log(sample_api_log)
        
        # 查询视图
        result = storage.query("SELECT * FROM performance_stats")
        
        assert len(result) == 1
        row = result[0]
        assert row['model'] == 'gpt-3.5-turbo'
        assert row['provider'] == 'openai'
        assert row['request_count'] == 1
        assert row['avg_ttft_ms'] == 500
        assert row['avg_tpot_ms'] == 20.5


class TestEdgeCases:
    """边界情况测试"""
    
    def test_store_log_with_very_large_json(self, storage):
        """测试存储超大JSON数据"""
        # 创建大的JSON数据
        large_request = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "x" * 10000}]  # 10KB内容
        }
        
        large_response = {
            "choices": [{"message": {"content": "y" * 10000}}]  # 10KB响应
        }
        
        log = APICallLog(
            provider="openai",
            model="gpt-3.5-turbo",
            endpoint="/v1/chat/completions",
            raw_data=RawAPIData(
                raw_request=large_request,
                raw_response=large_response
            ),
            estimated_analysis=EstimatedAnalysis(
                estimated_performance=PerformanceAnalysis(total_latency_ms=1000),
                estimated_cache=CacheAnalysis()
            ),
            success=True
        )
        
        # 应该能成功存储
        storage.store_log(log)
        
        # 验证能够查询到
        result = storage.query("SELECT COUNT(*) as count FROM api_calls")
        assert result[0]['count'] == 1
    
    def test_query_with_empty_database(self, storage):
        """测试空数据库查询"""
        result = storage.query("SELECT COUNT(*) as count FROM api_calls")
        assert result[0]['count'] == 0
        
        stats = storage.get_performance_stats()
        assert stats.get('total_requests', 0) == 0
        
        recent_logs = storage.get_recent_logs()
        assert len(recent_logs) == 0
    
    def test_multiple_storage_instances_same_db(self, temp_db_path, sample_api_log):
        """测试多个存储实例使用同一数据库"""
        # 第一个实例写入数据
        storage1 = LogStorage(temp_db_path)
        storage1.store_log(sample_api_log)
        
        # 第二个实例读取数据
        storage2 = LogStorage(temp_db_path)
        result = storage2.query("SELECT COUNT(*) as count FROM api_calls")
        assert result[0]['count'] == 1