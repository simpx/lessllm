"""
OpenAI API provider implementation
"""

import json
from typing import Dict, Any, AsyncIterator, Optional
from .base import BaseProvider
from ..logging.models import RawAPIData
from ..proxy.manager import ProxyManager
import httpx
import logging

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI API提供商实现"""
    
    def __init__(self, api_key: str, proxy_manager: Optional[ProxyManager] = None, base_url: Optional[str] = None):
        super().__init__(api_key, proxy_manager, base_url)
        
        # OpenAI模型价格表 (USD per 1K tokens)
        self.pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-0613": {"input": 0.03, "output": 0.06},
            "gpt-4-32k": {"input": 0.06, "output": 0.12},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-3.5-turbo-0613": {"input": 0.0015, "output": 0.002},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
        }
        
        # 模型最大token数
        self.max_tokens = {
            "gpt-4": 8192,
            "gpt-4-0613": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo": 128000,
            "gpt-4-turbo-preview": 128000,
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-0613": 4096,
            "gpt-3.5-turbo-16k": 16384,
        }
    
    def get_default_base_url(self) -> str:
        return "https://api.openai.com/v1"
    
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送非流式请求"""
        client = await self.get_client()
        url = self.get_endpoint_url("chat/completions")
        headers = self.get_headers()
        
        # 确保不是流式请求
        request_data = request.copy()
        request_data["stream"] = False
        
        try:
            response = await client.post(url, json=request_data, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    async def send_streaming_request(self, request: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """发送流式请求"""
        client = await self.get_client()
        url = self.get_endpoint_url("chat/completions")
        headers = self.get_headers()
        
        # 设置为流式请求
        request_data = request.copy()
        request_data["stream"] = True
        
        try:
            async with client.stream("POST", url, json=request_data, headers=headers) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # 移除 "data: " 前缀
                        
                        if data == "[DONE]":
                            break
                            
                        try:
                            chunk = json.loads(data)
                            yield chunk
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI streaming API error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Streaming request failed: {e}")
            raise
    
    def parse_raw_response(self, request: Dict[str, Any], response: Dict[str, Any]) -> RawAPIData:
        """解析OpenAI响应格式"""
        extracted_usage = None
        extracted_cache_info = None
        extracted_performance = None
        
        if "usage" in response:
            extracted_usage = {
                "prompt_tokens": response["usage"].get("prompt_tokens"),
                "completion_tokens": response["usage"].get("completion_tokens"),
                "total_tokens": response["usage"].get("total_tokens")
            }
        
        # OpenAI可能在某些情况下返回缓存信息
        if "cache_info" in response:
            extracted_cache_info = response["cache_info"]
            
        # 提取性能信息（如果有）
        if "response_metadata" in response:
            metadata = response["response_metadata"]
            if "processing_time_ms" in metadata:
                extracted_performance = {
                    "processing_time_ms": metadata["processing_time_ms"]
                }
        
        return RawAPIData(
            raw_request=request,
            raw_response=response,
            extracted_usage=extracted_usage,
            extracted_cache_info=extracted_cache_info,
            extracted_performance=extracted_performance
        )
    
    def estimate_cost(self, usage: Dict[str, Any], model: str) -> float:
        """估算OpenAI API调用成本"""
        if model not in self.pricing:
            logger.warning(f"Unknown model for cost estimation: {model}")
            return 0.0
        
        pricing = self.pricing[model]
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        # 计算成本 (价格是每1K tokens)
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        
        return input_cost + output_cost
    
    def normalize_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """OpenAI格式已经是标准格式，直接返回"""
        return request
    
    def normalize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """OpenAI格式已经是标准格式，直接返回"""
        return response
    
    def get_test_request(self) -> Dict[str, Any]:
        """获取用于测试API密钥的请求"""
        return {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 5
        }
    
    def get_max_tokens(self, model: str) -> int:
        """获取模型的最大token数"""
        return self.max_tokens.get(model, 4096)
    
    def get_input_cost_per_token(self, model: str) -> float:
        """获取输入token的单价(USD)"""
        if model in self.pricing:
            return self.pricing[model]["input"] / 1000
        return 0.0
    
    def get_output_cost_per_token(self, model: str) -> float:
        """获取输出token的单价(USD)"""
        if model in self.pricing:
            return self.pricing[model]["output"] / 1000
        return 0.0