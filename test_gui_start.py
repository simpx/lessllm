#!/usr/bin/env python3
"""
测试 GUI 启动功能
"""

import sys
import os
sys.path.insert(0, '.')

from lessllm.cli import start_gui_process
import time

def test_gui_startup():
    print("🧪 测试 GUI 启动功能...")
    
    # 测试 GUI 启动
    print("启动 GUI 进程...")
    process = start_gui_process("localhost", 8501)
    
    if process:
        print("✅ GUI 进程启动成功")
        print("等待 5 秒...")
        time.sleep(5)
        
        # 检查进程状态
        if process.poll() is None:
            print("✅ GUI 进程仍在运行")
            print("🌐 请访问 http://localhost:8501 查看 GUI")
            
            # 等待用户输入后停止
            input("按 Enter 键停止 GUI...")
            
            # 停止进程
            process.terminate()
            process.wait()
            print("🛑 GUI 进程已停止")
        else:
            print("❌ GUI 进程已停止")
            # 获取错误信息
            try:
                stdout, stderr = process.communicate()
                if stdout:
                    print(f"STDOUT: {stdout.decode()}")
                if stderr:
                    print(f"STDERR: {stderr.decode()}")
            except:
                pass
    else:
        print("❌ GUI 进程启动失败")

if __name__ == "__main__":
    test_gui_startup()