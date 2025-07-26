"""
基础Provider抽象层测试
"""

import pytest
import httpx
from unittest.mock import Mock, AsyncMock, patch
from lessllm.providers.base import BaseProvider
from lessllm.proxy.manager import ProxyManager
from lessllm.config import ProxyConfig
from lessllm.logging.models import RawAPIData


class ConcreteProvider(BaseProvider):
    """用于测试的具体Provider实现"""
    
    def get_default_base_url(self) -> str:
        return "https://api.test.com/v1"
    
    async def send_request(self, request):
        return {"test": "response"}
    
    async def send_streaming_request(self, request):
        yield {"chunk": 1}
        yield {"chunk": 2}
    
    def parse_raw_response(self, request, response):
        return RawAPIData(raw_request=request, raw_response=response)
    
    def estimate_cost(self, usage, model):
        return 0.01
    
    def normalize_request(self, request):
        return request
    
    def normalize_response(self, response):
        return response
    
    def get_test_request(self):
        return {"model": "test-model", "messages": []}
    
    def get_max_tokens(self, model):
        return 4096
    
    def get_input_cost_per_token(self, model):
        return 0.001
    
    def get_output_cost_per_token(self, model):
        return 0.002


class TestBaseProvider:
    """基础Provider测试"""
    
    def test_init_basic(self):
        """测试基础初始化"""
        provider = ConcreteProvider("test-api-key")
        
        assert provider.api_key == "test-api-key"
        assert provider.proxy_manager is None
        assert provider.base_url is None
        assert provider._client is None
    
    def test_init_with_proxy_manager(self):
        """测试带代理管理器的初始化"""
        config = ProxyConfig(socks_proxy="socks5://127.0.0.1:1080")
        proxy_manager = ProxyManager(config)
        
        provider = ConcreteProvider("test-api-key", proxy_manager)
        
        assert provider.proxy_manager is proxy_manager
    
    def test_init_with_base_url(self):
        """测试带自定义base_url的初始化"""
        provider = ConcreteProvider(
            "test-api-key", 
            base_url="https://custom.api.com/v1"
        )
        
        assert provider.base_url == "https://custom.api.com/v1"
    
    @pytest.mark.asyncio
    async def test_get_client_without_proxy(self):
        """测试获取无代理的HTTP客户端"""
        provider = ConcreteProvider("test-api-key")
        
        client = await provider.get_client()
        
        assert isinstance(client, httpx.AsyncClient)
        assert provider._client is client  # 应该被缓存
        
        # 第二次调用应该返回同一个客户端
        client2 = await provider.get_client()
        assert client2 is client
        
        await provider.close()
    
    @pytest.mark.asyncio
    async def test_get_client_with_proxy(self):
        """测试获取带代理的HTTP客户端"""
        config = ProxyConfig(http_proxy="http://proxy:8080")
        proxy_manager = ProxyManager(config)
        provider = ConcreteProvider("test-api-key", proxy_manager)
        
        with patch.object(proxy_manager, 'get_httpx_client') as mock_get_client:
            mock_client = Mock(spec=httpx.AsyncClient)
            mock_get_client.return_value = mock_client
            
            client = await provider.get_client()
            
            assert client is mock_client
            mock_get_client.assert_called_once()
        
        await provider.close()
    
    @pytest.mark.asyncio
    async def test_close_client(self):
        """测试关闭HTTP客户端"""
        provider = ConcreteProvider("test-api-key")
        
        # 获取客户端
        client = await provider.get_client()
        assert provider._client is not None
        
        # 关闭客户端
        await provider.close()
        assert provider._client is None
    
    def test_get_headers_default(self):
        """测试获取默认请求头"""
        provider = ConcreteProvider("test-api-key")
        
        headers = provider.get_headers()
        
        assert headers["Authorization"] == "Bearer test-api-key"
        assert headers["Content-Type"] == "application/json"
        assert headers["User-Agent"] == "LessLLM/0.1.0"
    
    def test_get_endpoint_url_with_base_url(self):
        """测试使用自定义base_url获取端点URL"""
        provider = ConcreteProvider(
            "test-api-key",
            base_url="https://custom.api.com/v1"
        )
        
        url = provider.get_endpoint_url("chat/completions")
        assert url == "https://custom.api.com/v1/chat/completions"
    
    def test_get_endpoint_url_with_default_base_url(self):
        """测试使用默认base_url获取端点URL"""
        provider = ConcreteProvider("test-api-key")
        
        url = provider.get_endpoint_url("chat/completions")
        assert url == "https://api.test.com/v1/chat/completions"
    
    def test_get_endpoint_url_strip_slashes(self):
        """测试端点URL的斜杠处理"""
        provider = ConcreteProvider(
            "test-api-key",
            base_url="https://custom.api.com/v1/"
        )
        
        url = provider.get_endpoint_url("/chat/completions")
        assert url == "https://custom.api.com/v1/chat/completions"
    
    @pytest.mark.asyncio
    async def test_validate_api_key_success(self):
        """测试API密钥验证成功"""
        provider = ConcreteProvider("valid-api-key")
        
        # Mock send_request方法
        with patch.object(provider, 'send_request', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"test": "success"}
            
            is_valid = await provider.validate_api_key()
            
            assert is_valid is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_api_key_failure(self):
        """测试API密钥验证失败"""
        provider = ConcreteProvider("invalid-api-key")
        
        # Mock send_request方法抛出异常
        with patch.object(provider, 'send_request', new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("Unauthorized")
            
            is_valid = await provider.validate_api_key()
            
            assert is_valid is False
    
    def test_get_model_info(self):
        """测试获取模型信息"""
        provider = ConcreteProvider("test-api-key")
        
        info = provider.get_model_info("test-model")
        
        assert info["model"] == "test-model"
        assert info["provider"] == "concrete"  # 类名去掉Provider后缀并小写
        assert info["supports_streaming"] is True
        assert info["max_tokens"] == 4096
        assert info["input_cost_per_token"] == 0.001
        assert info["output_cost_per_token"] == 0.002


class TestAbstractMethods:
    """抽象方法测试"""
    
    def test_cannot_instantiate_base_provider(self):
        """测试不能直接实例化BaseProvider"""
        with pytest.raises(TypeError):
            BaseProvider("test-api-key")
    
    def test_concrete_provider_implements_all_methods(self):
        """测试具体Provider实现了所有必需方法"""
        provider = ConcreteProvider("test-api-key")
        
        # 所有抽象方法都应该可以调用
        assert callable(provider.send_request)
        assert callable(provider.send_streaming_request)
        assert callable(provider.parse_raw_response)
        assert callable(provider.estimate_cost)
        assert callable(provider.normalize_request)
        assert callable(provider.normalize_response)
        assert callable(provider.get_test_request)
        assert callable(provider.get_max_tokens)
        assert callable(provider.get_input_cost_per_token)
        assert callable(provider.get_output_cost_per_token)
        assert callable(provider.get_default_base_url)


class TestProviderUtilityMethods:
    """Provider工具方法测试"""
    
    def test_get_test_request_structure(self):
        """测试测试请求的结构"""
        provider = ConcreteProvider("test-api-key")
        
        test_request = provider.get_test_request()
        
        assert isinstance(test_request, dict)
        assert "model" in test_request
        assert "messages" in test_request
    
    def test_cost_methods_return_numbers(self):
        """测试成本方法返回数字"""
        provider = ConcreteProvider("test-api-key")
        
        input_cost = provider.get_input_cost_per_token("test-model")
        output_cost = provider.get_output_cost_per_token("test-model")
        
        assert isinstance(input_cost, (int, float))
        assert isinstance(output_cost, (int, float))
        assert input_cost >= 0
        assert output_cost >= 0
    
    def test_max_tokens_positive(self):
        """测试最大token数为正数"""
        provider = ConcreteProvider("test-api-key")
        
        max_tokens = provider.get_max_tokens("test-model")
        
        assert isinstance(max_tokens, int)
        assert max_tokens > 0
    
    def test_estimate_cost_with_usage(self):
        """测试成本估算"""
        provider = ConcreteProvider("test-api-key")
        
        usage = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
        
        cost = provider.estimate_cost(usage, "test-model")
        
        assert isinstance(cost, (int, float))
        assert cost >= 0
    
    def test_normalize_methods_preserve_structure(self):
        """测试规范化方法保持结构"""
        provider = ConcreteProvider("test-api-key")
        
        test_request = {"test": "request"}
        test_response = {"test": "response"}
        
        normalized_request = provider.normalize_request(test_request)
        normalized_response = provider.normalize_response(test_response)
        
        assert isinstance(normalized_request, dict)
        assert isinstance(normalized_response, dict)
    
    def test_parse_raw_response_returns_raw_data(self):
        """测试解析原始响应返回RawAPIData"""
        provider = ConcreteProvider("test-api-key")
        
        request = {"test": "request"}
        response = {"test": "response"}
        
        raw_data = provider.parse_raw_response(request, response)
        
        assert isinstance(raw_data, RawAPIData)
        assert raw_data.raw_request == request
        assert raw_data.raw_response == response