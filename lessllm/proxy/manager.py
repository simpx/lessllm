"""
Network proxy management system
"""

import httpx
from typing import Optional, Dict, Any, Tuple
from ..config import ProxyConfig
import logging

logger = logging.getLogger(__name__)


class ProxyManager:
    """统一的代理管理器"""
    
    def __init__(self, config: ProxyConfig):
        self.http_proxy = config.http_proxy
        self.socks_proxy = config.socks_proxy
        self.auth = config.auth or {}
        self.timeout = config.timeout
        
        # 验证代理配置
        self._validate_config()
        
    def _validate_config(self):
        """验证代理配置的有效性"""
        if self.http_proxy and self.socks_proxy:
            logger.warning("Both HTTP and SOCKS proxy configured, SOCKS proxy will take precedence")
            
        if self.socks_proxy and not self.socks_proxy.startswith(('socks4://', 'socks5://')):
            raise ValueError(f"Invalid SOCKS proxy format: {self.socks_proxy}")
            
        if self.http_proxy and not self.http_proxy.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid HTTP proxy format: {self.http_proxy}")
    
    def get_httpx_client(self, **kwargs) -> httpx.AsyncClient:
        """获取配置了代理的httpx客户端"""
        proxies = self._build_proxy_config()
        auth = self._build_auth_config()
        
        # 合并默认配置和用户配置
        client_config = {
            "timeout": self.timeout,
            "limits": httpx.Limits(max_connections=10, max_keepalive_connections=5),
            "follow_redirects": True,
            **kwargs  # 允许用户覆盖默认配置
        }
        
        # 添加代理配置（如果有）- 注意新版本httpx使用proxies参数
        if proxies:
            client_config["proxies"] = proxies
            
        # 添加认证配置（如果有）
        if auth:
            client_config["auth"] = auth
        
        logger.debug(f"Creating httpx client with proxy config: {proxies}")
        try:
            return httpx.AsyncClient(**client_config)
        except TypeError as e:
            # 如果proxies参数不被支持，则去掉proxies参数重试
            if "proxies" in str(e) and "proxies" in client_config:
                logger.warning(f"Proxies not supported in httpx client init, removing proxies parameter: {e}")
                client_config.pop("proxies", None)
                return httpx.AsyncClient(**client_config)
            raise
    
    def _build_proxy_config(self) -> Optional[Dict[str, str]]:
        """构建代理配置"""
        if self.socks_proxy:
            return {
                "http://": self.socks_proxy,
                "https://": self.socks_proxy
            }
        elif self.http_proxy:
            return {
                "http://": self.http_proxy,
                "https://": self.http_proxy
            }
        return None
    
    def _build_auth_config(self) -> Optional[Tuple[str, str]]:
        """构建认证配置"""
        if self.auth and self.auth.get("username"):
            return (self.auth["username"], self.auth.get("password", ""))
        return None
    
    def test_connectivity(self, test_url: str = "https://httpbin.org/get") -> Dict[str, Any]:
        """测试代理连接性"""
        try:
            client = self.get_httpx_client()
            
            # 使用同步客户端进行测试
            with httpx.Client(
                proxies=self._build_proxy_config(),
                auth=self._build_auth_config(),
                timeout=self.timeout
            ) as sync_client:
                response = sync_client.get(test_url)
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "proxy_used": self.socks_proxy or self.http_proxy,
                    "message": "Proxy connection successful"
                }
                
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Connection timeout",
                "proxy_used": self.socks_proxy or self.http_proxy,
                "message": f"Proxy connection timed out after {self.timeout}s"
            }
        except httpx.ProxyError as e:
            return {
                "success": False,
                "error": "Proxy error",
                "proxy_used": self.socks_proxy or self.http_proxy,
                "message": f"Proxy connection failed: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": "Unknown error",
                "proxy_used": self.socks_proxy or self.http_proxy,
                "message": f"Unexpected error: {str(e)}"
            }
    
    def get_proxy_info(self) -> Dict[str, Any]:
        """获取代理信息"""
        return {
            "http_proxy": self.http_proxy,
            "socks_proxy": self.socks_proxy,
            "has_auth": bool(self.auth and self.auth.get("username")),
            "timeout": self.timeout,
            "active_proxy": self.socks_proxy or self.http_proxy or "direct"
        }