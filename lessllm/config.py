"""
Configuration management system for LessLLM
"""

import os
import yaml
from typing import Dict, Any, Optional
from pydantic import BaseSettings, BaseModel
from pathlib import Path


class ProxyConfig(BaseModel):
    """代理配置"""
    http_proxy: Optional[str] = None
    socks_proxy: Optional[str] = None
    auth: Optional[Dict[str, str]] = None
    timeout: int = 30


class LoggingConfig(BaseModel):
    """日志配置"""
    enabled: bool = True
    level: str = "INFO"
    storage: Dict[str, Any] = {"type": "duckdb", "db_path": "./lessllm_logs.db"}


class AnalysisConfig(BaseModel):
    """分析配置"""
    enable_cache_estimation: bool = True
    enable_performance_tracking: bool = True
    cache_estimation_accuracy_threshold: float = 0.8


class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1


class Config(BaseSettings):
    """主配置类"""
    
    proxy: ProxyConfig = ProxyConfig()
    providers: Dict[str, Dict[str, str]] = {}
    logging: LoggingConfig = LoggingConfig()
    analysis: AnalysisConfig = AnalysisConfig()
    server: ServerConfig = ServerConfig()
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @classmethod
    def from_yaml(cls, yaml_path: str) -> "Config":
        """从YAML文件加载配置"""
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")
            
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
            
        # 替换环境变量
        yaml_data = cls._replace_env_vars(yaml_data)
        
        return cls(**yaml_data)
    
    @staticmethod
    def _replace_env_vars(data: Any) -> Any:
        """递归替换环境变量"""
        if isinstance(data, dict):
            return {k: Config._replace_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [Config._replace_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            env_var = data[2:-1]
            return os.getenv(env_var, data)
        return data
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "proxy": self.proxy.dict(),
            "providers": self.providers,
            "logging": self.logging.dict(),
            "analysis": self.analysis.dict(),
            "server": self.server.dict()
        }


# 全局配置实例
_global_config: Optional[Config] = None


def configure(config_dict: Optional[Dict[str, Any]] = None, yaml_path: Optional[str] = None) -> Config:
    """配置LessLLM"""
    global _global_config
    
    if yaml_path:
        _global_config = Config.from_yaml(yaml_path)
    elif config_dict:
        _global_config = Config(**config_dict)
    else:
        _global_config = Config()
    
    return _global_config


def get_config() -> Config:
    """获取当前配置"""
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config