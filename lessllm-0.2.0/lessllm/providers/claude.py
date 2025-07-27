"""
Claude API provider implementation
"""

import json
from typing import Dict, Any, AsyncIterator, Optional
from .base import BaseProvider
from ..logging.models import RawAPIData
from ..proxy.manager import ProxyManager
import httpx
import logging

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseProvider):
    """Claude API提供商实现"""
    
    def __init__(self, api_key: str, proxy_manager: Optional[ProxyManager] = None, base_url: Optional[str] = None):
        super().__init__(api_key, proxy_manager, base_url)
        
        # Claude模型价格表 (USD per 1K tokens)
        self.pricing = {
            "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
            "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
            "claude-2.1": {"input": 0.008, "output": 0.024},
            "claude-2.0": {"input": 0.008, "output": 0.024},
        }
        
        # 模型最大token数
        self.max_tokens = {
            "claude-3-opus-20240229": 200000,
            "claude-3-sonnet-20240229": 200000,
            "claude-3-haiku-20240307": 200000,
            "claude-2.1": 200000,
            "claude-2.0": 100000,
        }
    
    def get_default_base_url(self) -> str:
        return "https://api.anthropic.com/v1"
    
    def get_headers(self) -> Dict[str, str]:
        """获取Claude特定的请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "LessLLM/0.1.0"
        }
        
        # 检查是否使用阿里云代理
        if self.base_url and "aliyuncs.com" in self.base_url:
            # 阿里云代理可能需要Bearer认证
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            # 标准Claude API使用x-api-key
            headers["x-api-key"] = self.api_key
            headers["anthropic-version"] = "2023-06-01"
        
        return headers
    
    async def send_claude_messages_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """直接发送Claude Messages API格式的请求"""
        client = await self.get_client()
        url = self.get_endpoint_url("messages")
        headers = self.get_headers()
        
        # 直接使用Claude格式的请求，不做转换
        claude_request = request.copy()
        claude_request["stream"] = False
        
        try:
            response = await client.post(url, json=claude_request, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Claude API HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Claude API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Claude API request failed: {e}")
            raise
    
    async def send_claude_messages_streaming_request(self, request: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """直接发送Claude Messages API流式请求"""
        client = await self.get_client()
        url = self.get_endpoint_url("messages")
        headers = self.get_headers()
        
        # 直接使用Claude格式的请求，设置流式
        claude_request = request.copy()
        claude_request["stream"] = True
        
        try:
            async with client.stream("POST", url, json=claude_request, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # 移除 "data: " 前缀
                        if data.strip() == "[DONE]":
                            break
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPStatusError as e:
            logger.error(f"Claude streaming API HTTP error: {e.response.status_code}")
            raise Exception(f"Claude streaming API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Claude streaming API request failed: {e}")
            raise
    
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送非流式请求"""
        client = await self.get_client()
        url = self.get_endpoint_url("messages")
        headers = self.get_headers()
        
        # 转换为Claude格式
        claude_request = self._convert_to_claude_format(request)
        claude_request["stream"] = False
        
        try:
            response = await client.post(url, json=claude_request, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Claude API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    async def send_streaming_request(self, request: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """发送流式请求"""
        client = await self.get_client()
        url = self.get_endpoint_url("messages")
        headers = self.get_headers()
        
        # 转换为Claude格式并设置流式
        claude_request = self._convert_to_claude_format(request)
        claude_request["stream"] = True
        
        try:
            async with client.stream("POST", url, json=claude_request, headers=headers) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # 移除 "data: " 前缀
                        
                        try:
                            chunk = json.loads(data)
                            yield chunk
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.HTTPStatusError as e:
            logger.error(f"Claude streaming API error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Streaming request failed: {e}")
            raise
    
    def _convert_to_claude_format(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """将OpenAI格式转换为Claude格式"""
        claude_request = {
            "model": request["model"],
            "max_tokens": request.get("max_tokens", 1000),
            "messages": []
        }
        
        # 转换消息格式
        system_message = None
        for msg in request.get("messages", []):
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_request["messages"].append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        if system_message:
            claude_request["system"] = system_message
            
        # 复制其他参数
        if "temperature" in request:
            claude_request["temperature"] = request["temperature"]
        if "top_p" in request:
            claude_request["top_p"] = request["top_p"]
            
        return claude_request
    
    def parse_raw_response(self, request: Dict[str, Any], response: Dict[str, Any]) -> RawAPIData:
        """解析Claude响应格式"""
        extracted_usage = None
        extracted_cache_info = None
        
        if "usage" in response:
            extracted_usage = {
                "prompt_tokens": response["usage"].get("input_tokens"),
                "completion_tokens": response["usage"].get("output_tokens"),
                "total_tokens": response["usage"].get("input_tokens", 0) + response["usage"].get("output_tokens", 0)
            }
        
        # Claude可能在某些情况下返回缓存信息
        if "cache_info" in response:
            extracted_cache_info = response["cache_info"]
        
        return RawAPIData(
            raw_request=request,
            raw_response=response,
            extracted_usage=extracted_usage,
            extracted_cache_info=extracted_cache_info
        )
    
    def estimate_cost(self, usage: Dict[str, Any], model: str) -> float:
        """估算Claude API调用成本"""
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
        """将通用请求格式转换为Claude格式"""
        return self._convert_to_claude_format(request)
    
    def normalize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """将Claude响应格式转换为OpenAI兼容格式"""
        if "content" not in response:
            return response
            
        # 转换为OpenAI格式
        normalized = {
            "id": response.get("id", ""),
            "object": "chat.completion",
            "created": 0,  # Claude不返回时间戳
            "model": response.get("model", ""),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response["content"][0]["text"] if response["content"] else ""
                },
                "finish_reason": "stop" if response.get("stop_reason") == "end_turn" else response.get("stop_reason")
            }]
        }
        
        # 添加usage信息
        if "usage" in response:
            normalized["usage"] = {
                "prompt_tokens": response["usage"].get("input_tokens", 0),
                "completion_tokens": response["usage"].get("output_tokens", 0),
                "total_tokens": response["usage"].get("input_tokens", 0) + response["usage"].get("output_tokens", 0)
            }
        
        return normalized
    
    def get_test_request(self) -> Dict[str, Any]:
        """获取用于测试API密钥的请求"""
        return {
            "model": "claude-3-haiku-20240307",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 5
        }
    
    def get_max_tokens(self, model: str) -> int:
        """获取模型的最大token数"""
        return self.max_tokens.get(model, 200000)
    
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