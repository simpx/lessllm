"""
代理管理器单元测试
"""

import pytest
import httpx
from unittest.mock import Mock, patch, AsyncMock
from lessllm.proxy.manager import ProxyManager
from lessllm.config import ProxyConfig


class TestProxyManager:
    """代理管理器测试"""
    
    def test_init_with_basic_config(self):
        """测试基础配置初始化"""
        config = ProxyConfig(timeout=45)
        manager = ProxyManager(config)
        
        assert manager.http_proxy is None
        assert manager.socks_proxy is None
        assert manager.auth == {}
        assert manager.timeout == 45
    
    def test_init_with_http_proxy(self):
        """测试HTTP代理配置初始化"""
        config = ProxyConfig(
            http_proxy="http://proxy.test:8080",
            auth={"username": "user", "password": "pass"}
        )
        manager = ProxyManager(config)
        
        assert manager.http_proxy == "http://proxy.test:8080"
        assert manager.auth == {"username": "user", "password": "pass"}
    
    def test_init_with_socks_proxy(self):
        """测试SOCKS代理配置初始化"""
        config = ProxyConfig(socks_proxy="socks5://127.0.0.1:1080")
        manager = ProxyManager(config)
        
        assert manager.socks_proxy == "socks5://127.0.0.1:1080"
    
    def test_init_with_both_proxies_warning(self, caplog):
        """测试同时配置HTTP和SOCKS代理时的警告"""
        config = ProxyConfig(
            http_proxy="http://proxy.test:8080",
            socks_proxy="socks5://127.0.0.1:1080"
        )
        
        with caplog.at_level("WARNING"):
            ProxyManager(config)
        
        assert "SOCKS proxy will take precedence" in caplog.text
    
    def test_invalid_socks_proxy_format(self):
        """测试无效SOCKS代理格式"""
        config = ProxyConfig(socks_proxy="invalid://proxy:1080")
        
        with pytest.raises(ValueError, match="Invalid SOCKS proxy format"):
            ProxyManager(config)
    
    def test_invalid_http_proxy_format(self):
        """测试无效HTTP代理格式"""
        config = ProxyConfig(http_proxy="invalid://proxy:8080")
        
        with pytest.raises(ValueError, match="Invalid HTTP proxy format"):
            ProxyManager(config)
    
    def test_build_proxy_config_socks(self):
        """测试构建SOCKS代理配置"""
        config = ProxyConfig(socks_proxy="socks5://127.0.0.1:1080")
        manager = ProxyManager(config)
        
        proxy_config = manager._build_proxy_config()
        expected = {
            "http://": "socks5://127.0.0.1:1080",
            "https://": "socks5://127.0.0.1:1080"
        }
        assert proxy_config == expected
    
    def test_build_proxy_config_http(self):
        """测试构建HTTP代理配置"""
        config = ProxyConfig(http_proxy="http://proxy.test:8080")
        manager = ProxyManager(config)
        
        proxy_config = manager._build_proxy_config()
        expected = {
            "http://": "http://proxy.test:8080",
            "https://": "http://proxy.test:8080"
        }
        assert proxy_config == expected
    
    def test_build_proxy_config_none(self):
        """测试无代理配置"""
        config = ProxyConfig()
        manager = ProxyManager(config)
        
        proxy_config = manager._build_proxy_config()
        assert proxy_config is None
    
    def test_build_auth_config_with_auth(self):
        """测试构建认证配置"""
        config = ProxyConfig(
            auth={"username": "testuser", "password": "testpass"}
        )
        manager = ProxyManager(config)
        
        auth_config = manager._build_auth_config()
        assert auth_config == ("testuser", "testpass")
    
    def test_build_auth_config_username_only(self):
        """测试只有用户名的认证配置"""
        config = ProxyConfig(auth={"username": "testuser"})
        manager = ProxyManager(config)
        
        auth_config = manager._build_auth_config()
        assert auth_config == ("testuser", "")
    
    def test_build_auth_config_none(self):
        """测试无认证配置"""
        config = ProxyConfig()
        manager = ProxyManager(config)
        
        auth_config = manager._build_auth_config()
        assert auth_config is None
    
    @pytest.mark.asyncio
    async def test_get_httpx_client_basic(self):
        """测试获取基础httpx客户端"""
        config = ProxyConfig(timeout=60)
        manager = ProxyManager(config)
        
        client = manager.get_httpx_client()
        
        assert isinstance(client, httpx.AsyncClient)
        assert client.timeout.read == 60
        await client.aclose()
    
    @pytest.mark.asyncio
    async def test_get_httpx_client_with_proxy(self):
        """测试获取带代理的httpx客户端"""
        config = ProxyConfig(
            socks_proxy="socks5://127.0.0.1:1080",
            timeout=45
        )
        manager = ProxyManager(config)
        
        client = manager.get_httpx_client()
        
        assert isinstance(client, httpx.AsyncClient)
        # 注意：实际的代理配置检查可能需要更复杂的方法
        await client.aclose()
    
    @pytest.mark.asyncio
    async def test_get_httpx_client_with_custom_params(self):
        """测试使用自定义参数获取客户端"""
        config = ProxyConfig()
        manager = ProxyManager(config)
        
        client = manager.get_httpx_client(timeout=120)
        
        assert isinstance(client, httpx.AsyncClient)
        assert client.timeout.read == 120  # 自定义参数应该覆盖默认值
        await client.aclose()
    
    def test_get_proxy_info_no_proxy(self):
        """测试获取无代理信息"""
        config = ProxyConfig()
        manager = ProxyManager(config)
        
        info = manager.get_proxy_info()
        
        assert info["http_proxy"] is None
        assert info["socks_proxy"] is None
        assert info["has_auth"] is False
        assert info["timeout"] == 30
        assert info["active_proxy"] == "direct"
    
    def test_get_proxy_info_with_socks(self):
        """测试获取SOCKS代理信息"""
        config = ProxyConfig(
            socks_proxy="socks5://127.0.0.1:1080",
            auth={"username": "user", "password": "pass"}
        )
        manager = ProxyManager(config)
        
        info = manager.get_proxy_info()
        
        assert info["socks_proxy"] == "socks5://127.0.0.1:1080"
        assert info["has_auth"] is True
        assert info["active_proxy"] == "socks5://127.0.0.1:1080"
    
    def test_get_proxy_info_with_http(self):
        """测试获取HTTP代理信息"""
        config = ProxyConfig(http_proxy="http://proxy.test:8080")
        manager = ProxyManager(config)
        
        info = manager.get_proxy_info()
        
        assert info["http_proxy"] == "http://proxy.test:8080"
        assert info["active_proxy"] == "http://proxy.test:8080"


class TestProxyConnectivity:
    """代理连通性测试"""
    
    @patch('httpx.Client')
    def test_connectivity_success(self, mock_client_class):
        """测试连通性检查成功"""
        # 设置mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_client.get.return_value = mock_response
        
        # 使用MagicMock来支持上下文管理器
        from unittest.mock import MagicMock
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_client
        mock_context_manager.__exit__.return_value = None
        mock_client_class.return_value = mock_context_manager
        
        config = ProxyConfig(socks_proxy="socks5://127.0.0.1:1080")
        manager = ProxyManager(config)
        
        result = manager.test_connectivity()
        
        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["response_time_ms"] == 500.0
        assert result["proxy_used"] == "socks5://127.0.0.1:1080"
        assert "successful" in result["message"]
    
    @patch('httpx.Client')
    def test_connectivity_timeout(self, mock_client_class):
        """测试连通性检查超时"""
        # 设置mock抛出超时异常
        mock_client = Mock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        
        # 使用MagicMock来支持上下文管理器
        from unittest.mock import MagicMock
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_client
        mock_context_manager.__exit__.return_value = None
        mock_client_class.return_value = mock_context_manager
        
        config = ProxyConfig(
            http_proxy="http://proxy.test:8080",
            timeout=10
        )
        manager = ProxyManager(config)
        
        result = manager.test_connectivity()
        
        assert result["success"] is False
        assert result["error"] == "Connection timeout"
        assert result["proxy_used"] == "http://proxy.test:8080"
        assert "timed out after 10s" in result["message"]
    
    @patch('httpx.Client')
    def test_connectivity_proxy_error(self, mock_client_class):
        """测试代理错误"""
        # 设置mock抛出代理错误
        mock_client = Mock()
        mock_client.get.side_effect = httpx.ProxyError("Proxy connection failed")
        
        # 使用MagicMock来支持上下文管理器
        from unittest.mock import MagicMock
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_client
        mock_context_manager.__exit__.return_value = None
        mock_client_class.return_value = mock_context_manager
        
        config = ProxyConfig(socks_proxy="socks5://invalid:1080")
        manager = ProxyManager(config)
        
        result = manager.test_connectivity()
        
        assert result["success"] is False
        assert result["error"] == "Proxy error"
        assert "Proxy connection failed" in result["message"]
    
    @patch('httpx.Client')
    def test_connectivity_unknown_error(self, mock_client_class):
        """测试未知错误"""
        # 设置mock抛出其他异常
        mock_client = Mock()
        mock_client.get.side_effect = Exception("Unexpected error")
        
        # 使用MagicMock来支持上下文管理器
        from unittest.mock import MagicMock
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_client
        mock_context_manager.__exit__.return_value = None
        mock_client_class.return_value = mock_context_manager
        
        config = ProxyConfig()
        manager = ProxyManager(config)
        
        result = manager.test_connectivity()
        
        assert result["success"] is False
        assert result["error"] == "Unknown error"
        assert "Unexpected error" in result["message"]
    
    @patch('httpx.Client')
    def test_connectivity_custom_test_url(self, mock_client_class):
        """测试自定义测试URL"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.3
        mock_client.get.return_value = mock_response
        
        # 使用MagicMock来支持上下文管理器
        from unittest.mock import MagicMock
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_client
        mock_context_manager.__exit__.return_value = None
        mock_client_class.return_value = mock_context_manager
        
        config = ProxyConfig()
        manager = ProxyManager(config)
        
        result = manager.test_connectivity("https://custom.test.com/ping")
        
        assert result["success"] is True
        # 验证使用了自定义URL
        mock_client.get.assert_called_with("https://custom.test.com/ping")


class TestProxyManagerEdgeCases:
    """代理管理器边界情况测试"""
    
    def test_empty_auth_dict(self):
        """测试空认证字典"""
        config = ProxyConfig(auth={})
        manager = ProxyManager(config)
        
        auth_config = manager._build_auth_config()
        assert auth_config is None
    
    def test_auth_with_empty_username(self):
        """测试空用户名认证"""
        config = ProxyConfig(auth={"username": "", "password": "pass"})
        manager = ProxyManager(config)
        
        auth_config = manager._build_auth_config()
        assert auth_config is None
    
    def test_both_proxies_socks_precedence(self):
        """测试SOCKS代理优先级"""
        config = ProxyConfig(
            http_proxy="http://http-proxy:8080",
            socks_proxy="socks5://socks-proxy:1080"
        )
        manager = ProxyManager(config)
        
        proxy_config = manager._build_proxy_config()
        # SOCKS代理应该优先
        assert proxy_config["http://"] == "socks5://socks-proxy:1080"
        assert proxy_config["https://"] == "socks5://socks-proxy:1080"
    
    def test_proxy_info_precedence(self):
        """测试代理信息优先级显示"""
        config = ProxyConfig(
            http_proxy="http://http-proxy:8080",
            socks_proxy="socks5://socks-proxy:1080"
        )
        manager = ProxyManager(config)
        
        info = manager.get_proxy_info()
        # active_proxy应该显示SOCKS代理
        assert info["active_proxy"] == "socks5://socks-proxy:1080"