"""
API request logger
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from .models import APICallLog, RawAPIData, EstimatedAnalysis, PerformanceAnalysis, CacheAnalysis
from .storage import LogStorage
import logging

logger = logging.getLogger(__name__)


class APILogger:
    """API调用日志记录器"""
    
    def __init__(self, storage: LogStorage):
        self.storage = storage
        self._log_queue = asyncio.Queue()
        self._logger_task: Optional[asyncio.Task] = None
        self._shutdown = False
    
    async def start(self):
        """启动日志记录器"""
        if self._logger_task is None:
            self._logger_task = asyncio.create_task(self._log_worker())
            logger.info("API logger started")
    
    async def stop(self):
        """停止日志记录器"""
        self._shutdown = True
        if self._logger_task:
            await self._logger_task
            self._logger_task = None
            logger.info("API logger stopped")
    
    async def log_request(self, log: APICallLog):
        """异步记录API请求"""
        if not self._shutdown:
            await self._log_queue.put(log)
    
    async def _log_worker(self):
        """日志工作线程"""
        while not self._shutdown or not self._log_queue.empty():
            try:
                # 等待日志条目或超时
                try:
                    log = await asyncio.wait_for(self._log_queue.get(), timeout=1.0)
                    self.storage.store_log(log)
                    self._log_queue.task_done()
                except asyncio.TimeoutError:
                    continue
                    
            except Exception as e:
                logger.error(f"Failed to process log entry: {e}")
    
    def log_sync(self, log: APICallLog):
        """同步记录日志（用于关键路径）"""
        try:
            self.storage.store_log(log)
        except Exception as e:
            logger.error(f"Failed to store log synchronously: {e}")
    
    def create_success_log(
        self,
        request_id: str,
        provider: str,
        model: str,
        endpoint: str,
        raw_request: Dict[str, Any],
        raw_response: Dict[str, Any],
        performance: PerformanceAnalysis,
        cache_analysis: CacheAnalysis,
        estimated_cost: float = 0.0,
        proxy_used: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> APICallLog:
        """创建成功的API调用日志"""
        
        # 解析原始响应数据
        raw_data = RawAPIData(
            raw_request=raw_request,
            raw_response=raw_response
        )
        
        # 提取usage信息
        if "usage" in raw_response:
            raw_data.extracted_usage = raw_response["usage"]
        
        # 提取缓存信息
        if "cache_info" in raw_response:
            raw_data.extracted_cache_info = raw_response["cache_info"]
        
        # 创建估算分析
        estimated_analysis = EstimatedAnalysis(
            estimated_performance=performance,
            estimated_cache=cache_analysis,
            estimated_cost_usd=estimated_cost
        )
        
        return APICallLog(
            request_id=request_id,
            provider=provider,
            model=model,
            endpoint=endpoint,
            raw_data=raw_data,
            estimated_analysis=estimated_analysis,
            success=True,
            proxy_used=proxy_used,
            user_id=user_id,
            session_id=session_id
        )
    
    def create_error_log(
        self,
        request_id: str,
        provider: str,
        model: str,
        endpoint: str,
        raw_request: Dict[str, Any],
        error_message: str,
        proxy_used: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> APICallLog:
        """创建失败的API调用日志"""
        
        raw_data = RawAPIData(
            raw_request=raw_request,
            raw_response={"error": error_message}
        )
        
        estimated_analysis = EstimatedAnalysis(
            estimated_performance=PerformanceAnalysis(total_latency_ms=0),
            estimated_cache=CacheAnalysis(),
            estimated_cost_usd=0.0
        )
        
        return APICallLog(
            request_id=request_id,
            provider=provider,
            model=model,
            endpoint=endpoint,
            raw_data=raw_data,
            estimated_analysis=estimated_analysis,
            success=False,
            error_message=error_message,
            proxy_used=proxy_used,
            user_id=user_id,
            session_id=session_id
        )