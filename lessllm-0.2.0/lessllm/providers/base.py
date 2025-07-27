"""
Base provider abstraction for LLM APIs
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncIterator, Optional
from ..logging.models import RawAPIData
from ..proxy.manager import ProxyManager
import httpx
import logging

logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    """所有LLM提供商的基础接口"""
    
    def __init__(self, api_key: str, proxy_manager: Optional[ProxyManager] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.proxy_manager = proxy_manager
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None
    
    async def get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端，复用连接"""
        if self._client is None:
            if self.proxy_manager:
                self._client = self.proxy_manager.get_httpx_client()
            else:
                self._client = httpx.AsyncClient(
                    timeout=30.0,
                    limits=httpx.Limits(max_connections=10)
                )
        return self._client
    
    async def close(self):
        """关闭HTTP客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @abstractmethod
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求到LLM API"""
        pass
    
    @abstractmethod
    async def send_streaming_request(self, request: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """发送流式请求到LLM API"""
        pass
    
    @abstractmethod
    def parse_raw_response(self, request: Dict[str, Any], response: Dict[str, Any]) -> RawAPIData:
        """解析原始API响应"""
        pass
    
    @abstractmethod
    def estimate_cost(self, usage: Dict[str, Any], model: str) -> float:
        """估算API调用成本"""
        pass
    
    @abstractmethod
    def normalize_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """将通用请求格式转换为提供商特定格式"""
        pass
    
    @abstractmethod
    def normalize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """将提供商响应格式转换为通用格式"""
        pass
    
    def get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "LessLLM/0.1.0"
        }
    
    def get_endpoint_url(self, endpoint: str) -> str:
        """获取完整的端点URL"""
        if self.base_url:
            # 阿里云代理需要/v1/messages后缀
            if "aliyuncs.com" in self.base_url:
                return f"{self.base_url.rstrip('/')}/v1/{endpoint.lstrip('/')}"
            return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        return self.get_default_base_url() + "/" + endpoint.lstrip('/')
    
    @abstractmethod
    def get_default_base_url(self) -> str:
        """获取默认的基础URL"""
        pass
    
    async def validate_api_key(self) -> bool:
        """验证API密钥的有效性"""
        try:
            # 每个提供商可以覆盖这个方法来实现特定的验证逻辑
            test_request = self.get_test_request()
            await self.send_request(test_request)
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False
    
    @abstractmethod
    def get_test_request(self) -> Dict[str, Any]:
        """获取用于测试API密钥的请求"""
        pass
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model": model,
            "provider": self.__class__.__name__.replace("Provider", "").lower(),
            "supports_streaming": True,
            "max_tokens": self.get_max_tokens(model),
            "input_cost_per_token": self.get_input_cost_per_token(model),
            "output_cost_per_token": self.get_output_cost_per_token(model)
        }
    
    @abstractmethod
    def get_max_tokens(self, model: str) -> int:
        """获取模型的最大token数"""
        pass
    
    @abstractmethod
    def get_input_cost_per_token(self, model: str) -> float:
        """获取输入token的单价(USD)"""
        pass
    
    @abstractmethod
    def get_output_cost_per_token(self, model: str) -> float:
        """获取输出token的单价(USD)"""
        pass