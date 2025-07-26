"""
Data models for API logging and analysis
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import uuid


class PerformanceAnalysis(BaseModel):
    """性能分析数据模型"""
    ttft_ms: Optional[int] = None  # Time To First Token (毫秒)
    tpot_ms: Optional[float] = None  # Time Per Output Token (毫秒)
    total_latency_ms: int  # 总延迟 (毫秒)
    tokens_per_second: Optional[float] = None  # Token生成速度
    network_latency_ms: Optional[int] = None  # 网络延迟


class CacheAnalysis(BaseModel):
    """缓存分析数据模型"""
    estimated_cached_tokens: int = 0
    estimated_fresh_tokens: int = 0
    estimated_cache_hit_rate: float = 0.0
    system_message_cached: int = 0
    template_cached: int = 0
    conversation_history_cached: int = 0


class RawAPIData(BaseModel):
    """原始API数据，完全忠实记录"""
    raw_request: Dict[str, Any]  # 完整原始请求
    raw_response: Dict[str, Any]  # 完整原始响应
    extracted_usage: Optional[Dict[str, Any]] = None  # 标准化的usage信息
    extracted_cache_info: Optional[Dict[str, Any]] = None  # API返回的缓存信息
    extracted_performance: Optional[Dict[str, Any]] = None  # API返回的性能信息


class EstimatedAnalysis(BaseModel):
    """lessllm的分析预估"""
    estimated_performance: PerformanceAnalysis
    estimated_cache: CacheAnalysis
    estimated_cost_usd: Optional[float] = None
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)


class APICallLog(BaseModel):
    """完整的API调用日志"""
    # 基础信息
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: str
    model: str
    endpoint: str
    
    # 双轨数据
    raw_data: RawAPIData  # 原始API数据
    estimated_analysis: EstimatedAnalysis  # lessllm分析预估
    
    # 状态信息
    success: bool
    error_message: Optional[str] = None
    proxy_used: Optional[str] = None
    
    # 用户标识（可选）
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # 从原始数据提取的关键字段（便于查询）
    actual_prompt_tokens: Optional[int] = None
    actual_completion_tokens: Optional[int] = None
    actual_total_tokens: Optional[int] = None
    actual_cached_tokens: Optional[int] = None
    actual_cache_hit_rate: Optional[float] = None
    
    def extract_key_fields(self):
        """从原始数据中提取关键字段以便查询"""
        if self.raw_data.extracted_usage:
            usage = self.raw_data.extracted_usage
            self.actual_prompt_tokens = usage.get('prompt_tokens')
            self.actual_completion_tokens = usage.get('completion_tokens')
            self.actual_total_tokens = usage.get('total_tokens')
            
        if self.raw_data.extracted_cache_info:
            cache_info = self.raw_data.extracted_cache_info
            self.actual_cached_tokens = cache_info.get('cached_tokens')
            self.actual_cache_hit_rate = cache_info.get('cache_hit_rate')


class StreamingChunk(BaseModel):
    """流式响应块数据模型"""
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str
    chunk_data: Dict[str, Any]
    is_final: bool = False


class BatchAnalysisSummary(BaseModel):
    """批量分析摘要"""
    start_time: datetime
    end_time: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens: int
    total_cost_usd: float
    avg_ttft_ms: Optional[float] = None
    avg_tpot_ms: Optional[float] = None
    avg_cache_hit_rate: float
    providers_used: List[str]
    models_used: List[str]