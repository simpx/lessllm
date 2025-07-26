"""
Command line interface for LessLLM
"""

import argparse
import sys
import os
from pathlib import Path
from .config import configure
from .server import start_server


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(description="LessLLM - Lightweight LLM API Proxy")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # server命令
    server_parser = subparsers.add_parser("server", help="Start the LessLLM proxy server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    server_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    server_parser.add_argument("--config", help="Path to configuration file")
    server_parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    
    # test命令
    test_parser = subparsers.add_parser("test", help="Test proxy connectivity")
    test_parser.add_argument("--config", help="Path to configuration file")
    
    # init命令
    init_parser = subparsers.add_parser("init", help="Initialize configuration file")
    init_parser.add_argument("--output", default="lessllm.yaml", help="Output configuration file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "server":
        run_server(args)
    elif args.command == "test":
        test_connectivity(args)
    elif args.command == "init":
        init_config(args)


def run_server(args):
    """运行服务器"""
    try:
        # 加载配置
        if args.config:
            if not os.path.exists(args.config):
                print(f"Error: Configuration file not found: {args.config}")
                sys.exit(1)
            configure(yaml_path=args.config)
        else:
            configure()
        
        print(f"Starting LessLLM server on {args.host}:{args.port}")
        print("Press Ctrl+C to stop")
        
        start_server(
            host=args.host,
            port=args.port,
            workers=args.workers
        )
        
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


def test_connectivity(args):
    """测试连接性"""
    try:
        # 加载配置
        if args.config:
            config = configure(yaml_path=args.config)
        else:
            config = configure()
        
        from .proxy.manager import ProxyManager
        
        proxy_manager = ProxyManager(config.proxy)
        result = proxy_manager.test_connectivity()
        
        if result["success"]:
            print("✓ Proxy connectivity test successful")
            print(f"  Response time: {result['response_time_ms']:.2f}ms")
            print(f"  Proxy used: {result['proxy_used']}")
        else:
            print("✗ Proxy connectivity test failed")
            print(f"  Error: {result['error']}")
            print(f"  Message: {result['message']}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error testing connectivity: {e}")
        sys.exit(1)


def init_config(args):
    """初始化配置文件"""
    config_content = """# LessLLM Configuration File

proxy:
  # HTTP代理配置
  # http_proxy: "http://proxy.company.com:8080"
  
  # SOCKS代理配置
  # socks_proxy: "socks5://127.0.0.1:1080"
  
  # 代理认证
  # auth:
  #   username: "${PROXY_USER}"
  #   password: "${PROXY_PASS}"
  
  timeout: 30

providers:
  openai:
    api_key: "${OPENAI_API_KEY}"
    base_url: "https://api.openai.com/v1"
    
  claude:
    api_key: "${ANTHROPIC_API_KEY}"
    base_url: "https://api.anthropic.com/v1"

logging:
  enabled: true
  level: "INFO"
  storage:
    type: "duckdb"
    db_path: "./lessllm_logs.db"

analysis:
  enable_cache_estimation: true
  enable_performance_tracking: true
  cache_estimation_accuracy_threshold: 0.8

server:
  host: "0.0.0.0"
  port: 8000
  workers: 1
"""
    
    try:
        output_path = Path(args.output)
        
        if output_path.exists():
            response = input(f"Configuration file {args.output} already exists. Overwrite? (y/N): ")
            if response.lower() != 'y':
                print("Configuration initialization cancelled")
                return
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        print(f"✓ Configuration file created: {args.output}")
        print("Please edit the file and set your API keys and proxy settings")
        
    except Exception as e:
        print(f"Error creating configuration file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()