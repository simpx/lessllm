"""
OpenAI Provider单元测试
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from lessllm.providers.openai import OpenAIProvider
from lessllm.proxy.manager import ProxyManager
from lessllm.config import ProxyConfig
from lessllm.logging.models import RawAPIData


class TestOpenAIProvider:
    """OpenAI Provider测试"""
    
    def test_init(self):
        """测试初始化"""
        provider = OpenAIProvider("test-api-key")
        
        assert provider.api_key == "test-api-key"
        assert provider.proxy_manager is None
        assert provider.base_url is None
        assert len(provider.pricing) > 0
        assert len(provider.max_tokens) > 0
    
    def test_init_with_proxy_and_base_url(self):
        """测试带代理和自定义URL的初始化"""
        config = ProxyConfig(http_proxy="http://proxy:8080")
        proxy_manager = ProxyManager(config)
        
        provider = OpenAIProvider(
            "test-api-key",
            proxy_manager,
            "https://custom.openai.com/v1"
        )
        
        assert provider.proxy_manager is proxy_manager
        assert provider.base_url == "https://custom.openai.com/v1"
    
    def test_get_default_base_url(self):
        """测试获取默认base URL"""
        provider = OpenAIProvider("test-api-key")
        
        base_url = provider.get_default_base_url()
        assert base_url == "https://api.openai.com/v1"
    
    def test_pricing_data_structure(self):
        """测试价格数据结构"""
        provider = OpenAIProvider("test-api-key")
        
        # 检查几个主要模型的价格
        assert "gpt-4" in provider.pricing
        assert "gpt-3.5-turbo" in provider.pricing
        
        for model, pricing in provider.pricing.items():
            assert "input" in pricing
            assert "output" in pricing
            assert isinstance(pricing["input"], (int, float))
            assert isinstance(pricing["output"], (int, float))
            assert pricing["input"] > 0
            assert pricing["output"] > 0
    
    def test_max_tokens_data_structure(self):
        """测试最大token数据结构"""
        provider = OpenAIProvider("test-api-key")
        
        assert "gpt-4" in provider.max_tokens
        assert "gpt-3.5-turbo" in provider.max_tokens
        
        for model, max_tokens in provider.max_tokens.items():
            assert isinstance(max_tokens, int)
            assert max_tokens > 0
    
    @pytest.mark.asyncio
    async def test_send_request_success(self, sample_openai_request, sample_openai_response):
        """测试成功发送请求"""
        provider = OpenAIProvider("test-api-key")
        
        with patch.object(provider, 'get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_openai_response
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            result = await provider.send_request(sample_openai_request)
            
            assert result == sample_openai_response
            mock_client.post.assert_called_once()
            
            # 检查请求参数
            call_args = mock_client.post.call_args
            assert call_args[1]["json"]["stream"] is False  # 应该设置为非流式
    
    @pytest.mark.asyncio
    async def test_send_request_http_error(self, sample_openai_request):
        """测试HTTP错误处理"""
        provider = OpenAIProvider("test-api-key")
        
        with patch.object(provider, 'get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            
            import httpx
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "Unauthorized", request=Mock(), response=mock_response
            )
            mock_get_client.return_value = mock_client
            
            with pytest.raises(httpx.HTTPStatusError):
                await provider.send_request(sample_openai_request)
    
    @pytest.mark.asyncio
    async def test_send_streaming_request_success(self, sample_openai_request, sample_streaming_chunks):
        """测试成功发送流式请求"""
        provider = OpenAIProvider("test-api-key")
        
        # 创建异步生成器来模拟流式响应
        async def mock_aiter_lines():
            for chunk in sample_streaming_chunks:
                yield f"data: {json.dumps(chunk)}"
            yield "data: [DONE]"
        
        with patch.object(provider, 'get_client') as mock_get_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.aiter_lines = Mock(return_value=mock_aiter_lines())
            mock_response.raise_for_status = Mock()
            
            # Create a proper async context manager
            class AsyncStreamContextManager:
                def __init__(self, response):
                    self.response = response
                    
                async def __aenter__(self):
                    return self.response
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    return None
            
            mock_client = AsyncMock()
            # Make stream method return our context manager (use Mock instead of AsyncMock)
            mock_client.stream = Mock(return_value=AsyncStreamContextManager(mock_response))
            mock_get_client.return_value = mock_client
            
            chunks = []
            async for chunk in provider.send_streaming_request(sample_openai_request):
                chunks.append(chunk)
            
            assert len(chunks) == len(sample_streaming_chunks)
            assert chunks == sample_streaming_chunks
            
            # 检查请求参数
            call_args = mock_client.stream.call_args
            assert call_args[1]["json"]["stream"] is True  # 应该设置为流式
    
    @pytest.mark.asyncio
    async def test_send_streaming_request_invalid_json(self, sample_openai_request):
        """测试流式请求中的无效JSON处理"""
        provider = OpenAIProvider("test-api-key")
        
        async def mock_aiter_lines():
            yield "data: {invalid json}"
            yield "data: [DONE]"
        
        with patch.object(provider, 'get_client') as mock_get_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.aiter_lines = Mock(return_value=mock_aiter_lines())
            mock_response.raise_for_status = Mock()
            
            # Create a proper async context manager
            class AsyncStreamContextManager:
                def __init__(self, response):
                    self.response = response
                    
                async def __aenter__(self):
                    return self.response
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    return None
            
            mock_client = AsyncMock()
            # Make stream method return our context manager (use Mock instead of AsyncMock)
            mock_client.stream = Mock(return_value=AsyncStreamContextManager(mock_response))
            mock_get_client.return_value = mock_client
            
            chunks = []
            async for chunk in provider.send_streaming_request(sample_openai_request):
                chunks.append(chunk)
            
            # 无效JSON应该被跳过
            assert len(chunks) == 0
    
    def test_parse_raw_response_with_usage(self, sample_openai_request, sample_openai_response):
        """测试解析包含usage信息的响应"""
        provider = OpenAIProvider("test-api-key")
        
        raw_data = provider.parse_raw_response(sample_openai_request, sample_openai_response)
        
        assert isinstance(raw_data, RawAPIData)
        assert raw_data.raw_request == sample_openai_request
        assert raw_data.raw_response == sample_openai_response
        
        # 检查提取的usage信息
        assert raw_data.extracted_usage is not None
        assert raw_data.extracted_usage["prompt_tokens"] == 20
        assert raw_data.extracted_usage["completion_tokens"] == 17
        assert raw_data.extracted_usage["total_tokens"] == 37
    
    def test_parse_raw_response_without_usage(self, sample_openai_request):
        """测试解析不包含usage信息的响应"""
        provider = OpenAIProvider("test-api-key")
        response_without_usage = {"id": "test", "choices": []}
        
        raw_data = provider.parse_raw_response(sample_openai_request, response_without_usage)
        
        assert raw_data.extracted_usage is None
    
    def test_parse_raw_response_with_cache_info(self, sample_openai_request):
        """测试解析包含缓存信息的响应"""
        provider = OpenAIProvider("test-api-key")
        response_with_cache = {
            "id": "test",
            "cache_info": {"hit_rate": 0.8, "cached_tokens": 100}
        }
        
        raw_data = provider.parse_raw_response(sample_openai_request, response_with_cache)
        
        assert raw_data.extracted_cache_info is not None
        assert raw_data.extracted_cache_info["hit_rate"] == 0.8
        assert raw_data.extracted_cache_info["cached_tokens"] == 100
    
    def test_estimate_cost_known_model(self):
        """测试已知模型的成本估算"""
        provider = OpenAIProvider("test-api-key")
        
        usage = {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "total_tokens": 1500
        }
        
        cost = provider.estimate_cost(usage, "gpt-3.5-turbo")
        
        # gpt-3.5-turbo: input=0.0015, output=0.002 per 1K tokens
        expected_cost = (1000/1000 * 0.0015) + (500/1000 * 0.002)
        assert abs(cost - expected_cost) < 0.0001
    
    def test_estimate_cost_unknown_model(self):
        """测试未知模型的成本估算"""
        provider = OpenAIProvider("test-api-key")
        
        usage = {
            "prompt_tokens": 1000,
            "completion_tokens": 500
        }
        
        cost = provider.estimate_cost(usage, "unknown-model")
        assert cost == 0.0
    
    def test_estimate_cost_missing_tokens(self):
        """测试缺少token信息的成本估算"""
        provider = OpenAIProvider("test-api-key")
        
        usage = {}  # 没有token信息
        
        cost = provider.estimate_cost(usage, "gpt-3.5-turbo")
        assert cost == 0.0
    
    def test_normalize_request_unchanged(self, sample_openai_request):
        """测试请求规范化（OpenAI格式不变）"""
        provider = OpenAIProvider("test-api-key")
        
        normalized = provider.normalize_request(sample_openai_request)
        assert normalized == sample_openai_request
    
    def test_normalize_response_unchanged(self, sample_openai_response):
        """测试响应规范化（OpenAI格式不变）"""
        provider = OpenAIProvider("test-api-key")
        
        normalized = provider.normalize_response(sample_openai_response)
        assert normalized == sample_openai_response
    
    def test_get_test_request(self):
        """测试获取测试请求"""
        provider = OpenAIProvider("test-api-key")
        
        test_request = provider.get_test_request()
        
        assert test_request["model"] == "gpt-3.5-turbo"
        assert "messages" in test_request
        assert test_request["max_tokens"] == 5
        assert len(test_request["messages"]) == 1
        assert test_request["messages"][0]["content"] == "Hello"
    
    def test_get_max_tokens_known_model(self):
        """测试获取已知模型的最大token数"""
        provider = OpenAIProvider("test-api-key")
        
        max_tokens = provider.get_max_tokens("gpt-4")
        assert max_tokens == 8192
        
        max_tokens = provider.get_max_tokens("gpt-3.5-turbo")
        assert max_tokens == 4096
    
    def test_get_max_tokens_unknown_model(self):
        """测试获取未知模型的最大token数"""
        provider = OpenAIProvider("test-api-key")
        
        max_tokens = provider.get_max_tokens("unknown-model")
        assert max_tokens == 4096  # 默认值
    
    def test_get_input_cost_per_token(self):
        """测试获取输入token单价"""
        provider = OpenAIProvider("test-api-key")
        
        cost = provider.get_input_cost_per_token("gpt-3.5-turbo")
        expected = 0.0015 / 1000  # 转换为每个token的价格
        assert abs(cost - expected) < 0.0000001
    
    def test_get_output_cost_per_token(self):
        """测试获取输出token单价"""
        provider = OpenAIProvider("test-api-key")
        
        cost = provider.get_output_cost_per_token("gpt-3.5-turbo")
        expected = 0.002 / 1000  # 转换为每个token的价格
        assert abs(cost - expected) < 0.0000001
    
    def test_get_cost_per_token_unknown_model(self):
        """测试未知模型的token单价"""
        provider = OpenAIProvider("test-api-key")
        
        input_cost = provider.get_input_cost_per_token("unknown-model")
        output_cost = provider.get_output_cost_per_token("unknown-model")
        
        assert input_cost == 0.0
        assert output_cost == 0.0


class TestOpenAIProviderPricingAccuracy:
    """OpenAI Provider价格准确性测试"""
    
    def test_pricing_consistency(self):
        """测试价格数据的一致性"""
        provider = OpenAIProvider("test-api-key")
        
        # 检查所有模型的价格数据
        for model in provider.pricing:
            pricing = provider.pricing[model]
            assert pricing["input"] < pricing["output"], f"Model {model}: input cost should be less than output cost"
    
    def test_max_tokens_consistency(self):
        """测试最大token数的一致性"""
        provider = OpenAIProvider("test-api-key")
        
        # 检查16k模型的token数确实更大
        if "gpt-3.5-turbo-16k" in provider.max_tokens and "gpt-3.5-turbo" in provider.max_tokens:
            assert provider.max_tokens["gpt-3.5-turbo-16k"] > provider.max_tokens["gpt-3.5-turbo"]
    
    def test_cost_calculation_precision(self):
        """测试成本计算精度"""
        provider = OpenAIProvider("test-api-key")
        
        usage = {
            "prompt_tokens": 1,
            "completion_tokens": 1
        }
        
        cost = provider.estimate_cost(usage, "gpt-3.5-turbo")
        
        # 成本应该是非常小的正数
        assert cost > 0
        assert cost < 0.01  # 单个token的成本应该小于1分钱