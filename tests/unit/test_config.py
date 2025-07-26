"""
配置管理系统单元测试
"""

import pytest
import tempfile
import os
import yaml
from unittest.mock import patch, mock_open
from lessllm.config import Config, ProxyConfig, LoggingConfig, AnalysisConfig, configure, get_config


class TestProxyConfig:
    """代理配置测试"""
    
    def test_default_proxy_config(self):
        """测试默认代理配置"""
        config = ProxyConfig()
        assert config.http_proxy is None
        assert config.socks_proxy is None
        assert config.auth is None
        assert config.timeout == 30
    
    def test_proxy_config_with_values(self):
        """测试设置代理配置值"""
        config = ProxyConfig(
            http_proxy="http://proxy:8080",
            socks_proxy="socks5://127.0.0.1:1080",
            auth={"username": "user", "password": "pass"},
            timeout=60
        )
        assert config.http_proxy == "http://proxy:8080"
        assert config.socks_proxy == "socks5://127.0.0.1:1080"
        assert config.auth == {"username": "user", "password": "pass"}
        assert config.timeout == 60


class TestLoggingConfig:
    """日志配置测试"""
    
    def test_default_logging_config(self):
        """测试默认日志配置"""
        config = LoggingConfig()
        assert config.enabled is True
        assert config.level == "INFO"
        assert config.storage == {"type": "duckdb", "db_path": "./lessllm_logs.db"}
    
    def test_custom_logging_config(self):
        """测试自定义日志配置"""
        config = LoggingConfig(
            enabled=False,
            level="DEBUG",
            storage={"type": "duckdb", "db_path": "/tmp/test.db"}
        )
        assert config.enabled is False
        assert config.level == "DEBUG"
        assert config.storage["db_path"] == "/tmp/test.db"


class TestAnalysisConfig:
    """分析配置测试"""
    
    def test_default_analysis_config(self):
        """测试默认分析配置"""
        config = AnalysisConfig()
        assert config.enable_cache_estimation is True
        assert config.enable_performance_tracking is True
        assert config.cache_estimation_accuracy_threshold == 0.8
    
    def test_custom_analysis_config(self):
        """测试自定义分析配置"""
        config = AnalysisConfig(
            enable_cache_estimation=False,
            enable_performance_tracking=False,
            cache_estimation_accuracy_threshold=0.9
        )
        assert config.enable_cache_estimation is False
        assert config.enable_performance_tracking is False
        assert config.cache_estimation_accuracy_threshold == 0.9


class TestConfig:
    """主配置类测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = Config()
        assert isinstance(config.proxy, ProxyConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.analysis, AnalysisConfig)
        assert config.providers == {}
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = Config(
            providers={
                "openai": {"api_key": "test-key"}
            }
        )
        assert config.providers == {"openai": {"api_key": "test-key"}}
    
    def test_config_to_dict(self):
        """测试配置转换为字典"""
        config = Config()
        config_dict = config.to_dict()
        
        assert "proxy" in config_dict
        assert "providers" in config_dict
        assert "logging" in config_dict
        assert "analysis" in config_dict
        assert "server" in config_dict
    
    @patch.dict(os.environ, {"TEST_VAR": "test_value"})
    def test_replace_env_vars(self):
        """测试环境变量替换"""
        data = {
            "key1": "${TEST_VAR}",
            "key2": "normal_value",
            "nested": {
                "key3": "${TEST_VAR}_suffix"
            }
        }
        
        result = Config._replace_env_vars(data)
        assert result["key1"] == "test_value"
        assert result["key2"] == "normal_value"
        assert result["nested"]["key3"] == "test_value_suffix"
    
    def test_replace_env_vars_missing(self):
        """测试缺失环境变量的处理"""
        data = {"key": "${MISSING_VAR}"}
        result = Config._replace_env_vars(data)
        assert result["key"] == "${MISSING_VAR}"  # 保持原值
    
    def test_from_yaml_valid_file(self):
        """测试从有效YAML文件加载配置"""
        yaml_content = """
        proxy:
          http_proxy: "http://proxy:8080"
          timeout: 60
        
        providers:
          openai:
            api_key: "test-key"
        
        logging:
          enabled: true
          level: "DEBUG"
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name
        
        try:
            config = Config.from_yaml(yaml_path)
            assert config.proxy.http_proxy == "http://proxy:8080"
            assert config.proxy.timeout == 60
            assert config.providers["openai"]["api_key"] == "test-key"
            assert config.logging.level == "DEBUG"
        finally:
            os.unlink(yaml_path)
    
    def test_from_yaml_file_not_found(self):
        """测试YAML文件不存在时的错误处理"""
        with pytest.raises(FileNotFoundError):
            Config.from_yaml("nonexistent.yaml")
    
    @patch.dict(os.environ, {"API_KEY": "env_api_key"})
    def test_from_yaml_with_env_vars(self):
        """测试YAML配置中的环境变量替换"""
        yaml_content = """
        providers:
          openai:
            api_key: "${API_KEY}"
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name
        
        try:
            config = Config.from_yaml(yaml_path)
            assert config.providers["openai"]["api_key"] == "env_api_key"
        finally:
            os.unlink(yaml_path)
    
    def test_from_yaml_invalid_yaml(self):
        """测试无效YAML文件的处理"""
        yaml_content = """
        invalid: yaml: content:
          - missing
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name
        
        try:
            with pytest.raises(yaml.YAMLError):
                Config.from_yaml(yaml_path)
        finally:
            os.unlink(yaml_path)


class TestGlobalConfigManagement:
    """全局配置管理测试"""
    
    def test_configure_with_dict(self):
        """测试使用字典配置"""
        config_dict = {
            "proxy": {"timeout": 45},
            "providers": {"test": {"api_key": "test"}}
        }
        
        config = configure(config_dict)
        assert config.proxy.timeout == 45
        assert config.providers["test"]["api_key"] == "test"
    
    def test_configure_with_yaml_path(self):
        """测试使用YAML路径配置"""
        yaml_content = """
        proxy:
          timeout: 50
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name
        
        try:
            config = configure(yaml_path=yaml_path)
            assert config.proxy.timeout == 50
        finally:
            os.unlink(yaml_path)
    
    def test_configure_default(self):
        """测试默认配置"""
        config = configure()
        assert isinstance(config, Config)
        assert config.proxy.timeout == 30  # 默认值
    
    def test_get_config_after_configure(self):
        """测试配置后获取配置"""
        config_dict = {"proxy": {"timeout": 99}}
        configure(config_dict)
        
        retrieved_config = get_config()
        assert retrieved_config.proxy.timeout == 99
    
    def test_get_config_without_configure(self):
        """测试未配置时获取默认配置"""
        # 重置全局配置
        import lessllm.config
        lessllm.config._global_config = None
        
        config = get_config()
        assert isinstance(config, Config)
        assert config.proxy.timeout == 30  # 默认值


class TestConfigValidation:
    """配置验证测试"""
    
    def test_valid_config_structure(self):
        """测试有效配置结构"""
        config_data = {
            "proxy": {
                "http_proxy": "http://proxy:8080",
                "timeout": 30
            },
            "providers": {
                "openai": {
                    "api_key": "sk-test123",
                    "base_url": "https://api.openai.com/v1"
                }
            }
        }
        
        # 应该能够成功创建配置
        config = Config(**config_data)
        assert config.proxy.http_proxy == "http://proxy:8080"
        assert config.providers["openai"]["api_key"] == "sk-test123"
    
    def test_config_with_extra_fields(self):
        """测试包含额外字段的配置"""
        config_data = {
            "proxy": {"timeout": 30},
            "unknown_field": "should_be_ignored"
        }
        
        # Pydantic应该忽略未知字段
        config = Config(**config_data)
        assert config.proxy.timeout == 30
        assert not hasattr(config, "unknown_field")
    
    def test_config_type_validation(self):
        """测试配置类型验证"""
        # timeout应该是整数
        with pytest.raises(ValueError):
            ProxyConfig(timeout="invalid")
        
        # enabled应该是布尔值
        with pytest.raises(ValueError):
            LoggingConfig(enabled="invalid")