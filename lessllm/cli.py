"""
Command line interface for LessLLM
"""

import argparse
import sys
import os
import subprocess
import time
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
    server_parser.add_argument("--gui-port", type=int, default=8501, help="Port to run the GUI on")
    server_parser.add_argument("--gui-host", default="localhost", help="Host to run the GUI on")
    server_parser.add_argument("--no-gui", action="store_true", help="Disable GUI dashboard (GUI is enabled by default)")
    
    # test命令
    test_parser = subparsers.add_parser("test", help="Test proxy connectivity")
    test_parser.add_argument("--config", help="Path to configuration file")
    
    # init命令
    init_parser = subparsers.add_parser("init", help="Initialize configuration file")
    init_parser.add_argument("--output", default="lessllm.yaml", help="Output configuration file")
    
    # gui命令（独立模式）
    gui_parser = subparsers.add_parser("gui", help="Start the analytics dashboard GUI only")
    gui_parser.add_argument("--port", type=int, default=8501, help="Port to run the GUI on")
    gui_parser.add_argument("--host", default="localhost", help="Host to run the GUI on")
    
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
    elif args.command == "gui":
        run_gui(args)


def start_gui_process(host, port):
    """启动 GUI 进程"""
    try:
        # 获取GUI脚本路径
        gui_script = os.path.join(os.path.dirname(__file__), "..", "gui", "dashboard.py")
        gui_script = os.path.abspath(gui_script)
        
        if not os.path.exists(gui_script):
            print(f"Warning: GUI script not found at {gui_script}, GUI will not be started")
            return None
        
        # 构建streamlit命令
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            gui_script,
            "--server.port", str(port),
            "--server.address", host,
            "--server.headless", "true",  # 禁用自动打开浏览器
            "--logger.level", "error"     # 减少日志输出
        ]
        
        # 启动进程，重定向输出减少噪音
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        
        # 等待一小段时间确保 GUI 启动
        time.sleep(3)
        
        # 检查进程是否还在运行
        if process.poll() is None:
            return process
        else:
            print("Warning: GUI process failed to start")
            return None
            
    except Exception as e:
        print(f"Warning: Failed to start GUI: {e}")
        return None


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
        
        # 启动 GUI（如果未禁用）
        gui_process = None
        if not getattr(args, 'no_gui', False):
            gui_host = getattr(args, 'gui_host', 'localhost')
            gui_port = getattr(args, 'gui_port', 8501)
            gui_process = start_gui_process(gui_host, gui_port)
        
        print(f"Starting LessLLM server on {args.host}:{args.port}")
        if not getattr(args, 'no_gui', False):
            gui_host = getattr(args, 'gui_host', 'localhost')
            gui_port = getattr(args, 'gui_port', 8501)
            print(f"GUI dashboard available at http://{gui_host}:{gui_port}")
        print("Press Ctrl+C to stop")
        print()  # 空行分隔
        
        try:
            start_server(
                host=args.host,
                port=args.port,
                workers=args.workers
            )
        finally:
            # 确保 GUI 进程被正确关闭
            if gui_process:
                terminate_gui_process(gui_process)
        
    except KeyboardInterrupt:
        print("\nServer stopped")
        if gui_process:
            terminate_gui_process(gui_process)
    except Exception as e:
        print(f"Error starting server: {e}")
        if gui_process:
            terminate_gui_process(gui_process)
        sys.exit(1)


def terminate_gui_process(process):
    """安全地终止 GUI 进程"""
    try:
        if process and process.poll() is None:
            # 尝试优雅终止
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # 如果优雅终止失败，强制杀死
                process.kill()
                process.wait()
    except Exception as e:
        print(f"Warning: Error terminating GUI process: {e}")


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


def run_gui(args):
    """运行GUI"""
    try:
        import subprocess
        import sys
        import os
        
        # 获取GUI脚本路径
        gui_script = os.path.join(os.path.dirname(__file__), "..", "gui", "dashboard.py")
        gui_script = os.path.abspath(gui_script)
        
        if not os.path.exists(gui_script):
            print(f"Error: GUI script not found at {gui_script}")
            sys.exit(1)
        
        # 构建streamlit命令
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            gui_script,
            "--server.port", str(args.port),
            "--server.address", args.host
        ]
        
        print(f"Starting LessLLM Analytics Dashboard on {args.host}:{args.port}")
        print("Press Ctrl+C to stop")
        
        # 运行streamlit
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\nGUI stopped")
    except subprocess.CalledProcessError as e:
        print(f"Error running GUI: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting GUI: {e}")
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