"""
Pytest配置和全局fixtures
"""

import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import MagicMock
from lessllm.config import Config, ProxyConfig, LoggingConfig, AnalysisConfig
from lessllm.proxy.manager import ProxyManager
from lessllm.logging.storage import LogStorage


@pytest.fixture
def temp_db():
    """临时数据库fixture"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    # 清理
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def test_config():
    """测试配置fixture"""
    return Config(
        proxy=ProxyConfig(
            http_proxy=None,
            socks_proxy=None,
            timeout=30
        ),
        providers={
            "openai": {
                "api_key": "test-openai-key",
                "base_url": "https://api.openai.com/v1"
            },
            "claude": {
                "api_key": "test-claude-key", 
                "base_url": "https://api.anthropic.com/v1"
            }
        },
        logging=LoggingConfig(
            enabled=True,
            level="DEBUG",
            storage={"type": "duckdb", "db_path": ":memory:"}
        ),
        analysis=AnalysisConfig(
            enable_cache_estimation=True,
            enable_performance_tracking=True
        )
    )


@pytest.fixture
def proxy_config():
    """代理配置fixture"""
    return ProxyConfig(
        http_proxy="http://proxy.test:8080",
        socks_proxy=None,
        auth={"username": "testuser", "password": "testpass"},
        timeout=30
    )


@pytest.fixture
def socks_proxy_config():
    """SOCKS代理配置fixture"""
    return ProxyConfig(
        http_proxy=None,
        socks_proxy="socks5://127.0.0.1:1080",
        timeout=30
    )


@pytest.fixture
def test_storage(temp_db):
    """测试存储系统fixture"""
    storage = LogStorage(temp_db)
    yield storage


@pytest.fixture
def mock_httpx_client():
    """Mock httpx客户端"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"test": "response"}
    mock_response.text = "test response"
    mock_client.post.return_value = mock_response
    mock_client.get.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_openai_request():
    """OpenAI请求样例"""
    return {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "max_tokens": 100,
        "temperature": 0.7
    }


@pytest.fixture
def sample_openai_response():
    """OpenAI响应样例"""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1699000000,
        "model": "gpt-3.5-turbo-0613",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! I'm doing well, thank you for asking. How can I help you today?"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 17,
            "total_tokens": 37
        }
    }


@pytest.fixture
def sample_claude_request():
    """Claude请求样例"""
    return {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "system": "You are a helpful assistant."
    }


@pytest.fixture
def sample_claude_response():
    """Claude响应样例"""
    return {
        "id": "msg_test123",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Hello! I'm doing well, thank you for asking. How can I help you today?"
            }
        ],
        "model": "claude-3-sonnet-20240229",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 15,
            "output_tokens": 17
        }
    }


@pytest.fixture
def sample_streaming_chunks():
    """流式响应块样例"""
    return [
        {
            "id": "chatcmpl-test123",
            "object": "chat.completion.chunk",
            "created": 1699000000,
            "model": "gpt-3.5-turbo-0613",
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None
                }
            ]
        },
        {
            "id": "chatcmpl-test123",
            "object": "chat.completion.chunk", 
            "created": 1699000000,
            "model": "gpt-3.5-turbo-0613",
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": "Hello"},
                    "finish_reason": None
                }
            ]
        },
        {
            "id": "chatcmpl-test123",
            "object": "chat.completion.chunk",
            "created": 1699000000,
            "model": "gpt-3.5-turbo-0613",
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": "!"},
                    "finish_reason": "stop"
                }
            ]
        }
    ]


@pytest.fixture
def mock_performance_data():
    """性能测试数据"""
    return {
        "request_start": 1699000000.0,
        "first_token_time": 1699000000.5,
        "token_timestamps": [
            1699000000.5,
            1699000000.6,
            1699000000.7,
            1699000000.8,
            1699000000.9
        ],
        "total_tokens": 5
    }


# 测试标记定义
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "e2e: 端到端测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "network: 需要网络连接的测试")


# 自动使用标记
def pytest_collection_modifyitems(config, items):
    """自动为测试添加标记"""
    for item in items:
        # 根据路径添加标记
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            
        # 标记可能需要网络的测试
        if "proxy" in item.name.lower() or "network" in item.name.lower():
            item.add_marker(pytest.mark.network)