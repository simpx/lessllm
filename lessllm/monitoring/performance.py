"""
Performance monitoring and metrics collection
"""

import time
from typing import List, Optional
from ..logging.models import PerformanceAnalysis


class PerformanceTracker:
    """精确的性能指标收集器"""
    
    def __init__(self):
        self.request_start: Optional[float] = None
        self.first_token_time: Optional[float] = None
        self.token_timestamps: List[float] = []
        
    def start_request(self):
        """记录请求开始时间"""
        self.request_start = time.time()
        
    def record_first_token(self):
        """记录第一个token到达时间 - TTFT测量"""
        if self.first_token_time is None:
            self.first_token_time = time.time()
            
    def record_token(self):
        """记录每个token到达时间 - TPOT计算基础"""
        current_time = time.time()
        if self.first_token_time is None:
            self.record_first_token()
        self.token_timestamps.append(current_time)
        
    def calculate_metrics(self, output_tokens: int) -> PerformanceAnalysis:
        """计算流式请求的最终性能指标"""
        if not self.request_start:
            raise ValueError("Request start time not recorded")
            
        if not self.first_token_time:
            # 如果没有记录到token，可能是空响应
            return PerformanceAnalysis(
                ttft_ms=None,
                tpot_ms=None,
                total_latency_ms=int((time.time() - self.request_start) * 1000),
                tokens_per_second=None
            )
        
        # TTFT = 第一个token时间 - 请求开始时间
        ttft = (self.first_token_time - self.request_start) * 1000
        
        # TPOT = 总生成时间 / 输出token数
        tpot = None
        tokens_per_second = None
        
        if len(self.token_timestamps) > 1 and output_tokens > 0:
            generation_time = self.token_timestamps[-1] - self.first_token_time
            if generation_time > 0:
                tpot = (generation_time * 1000) / output_tokens
                tokens_per_second = output_tokens / generation_time
        
        total_latency = int((self.token_timestamps[-1] if self.token_timestamps else time.time() - self.request_start) * 1000)
        
        return PerformanceAnalysis(
            ttft_ms=int(ttft),
            tpot_ms=round(tpot, 2) if tpot else None,
            total_latency_ms=total_latency,
            tokens_per_second=round(tokens_per_second, 2) if tokens_per_second else None
        )
    
    def calculate_non_streaming_metrics(self) -> PerformanceAnalysis:
        """计算非流式请求的性能指标"""
        if not self.request_start:
            raise ValueError("Request start time not recorded")
            
        end_time = time.time()
        total_latency = int((end_time - self.request_start) * 1000)
        
        # 非流式响应：TTFT = 总延迟，TPOT无法测量
        return PerformanceAnalysis(
            ttft_ms=total_latency,
            tpot_ms=None,
            total_latency_ms=total_latency,
            tokens_per_second=None
        )
    
    def get_current_latency(self) -> int:
        """获取当前延迟（毫秒）"""
        if not self.request_start:
            return 0
        return int((time.time() - self.request_start) * 1000)