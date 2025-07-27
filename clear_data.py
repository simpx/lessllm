#!/usr/bin/env python3
"""
清空 LessLLM 数据库的脚本
"""

import os
import sys
from pathlib import Path

def clear_database():
    """清空数据库"""
    db_path = "./lessllm_logs.db"
    
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"✅ 已删除数据库文件: {db_path}")
            print("下次启动时将创建新的空数据库")
        except Exception as e:
            print(f"❌ 删除失败: {e}")
            return False
    else:
        print("ℹ️  数据库文件不存在，无需清空")
    
    return True

def clear_logs_only():
    """只清空日志记录，保留数据库结构"""
    try:
        from lessllm.logging.storage import LogStorage
        
        db_path = "./lessllm_logs.db"
        if not os.path.exists(db_path):
            print("ℹ️  数据库文件不存在")
            return
            
        storage = LogStorage(db_path)
        
        # 执行清空操作
        result = storage.query("DELETE FROM api_calls")
        print("✅ 已清空所有日志记录，保留数据库结构")
        
        # 显示清空后的统计
        stats = storage.get_database_stats()
        print(f"当前记录数: {stats['total_records']}")
        
    except Exception as e:
        print(f"❌ 清空失败: {e}")

if __name__ == "__main__":
    print("🗑️  LessLLM 数据清空工具")
    print("=" * 30)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--logs-only":
        print("只清空日志记录...")
        clear_logs_only()
    else:
        print("完全删除数据库文件...")
        clear_database()
    
    print("\n使用方法:")
    print("python clear_data.py           # 删除整个数据库文件")
    print("python clear_data.py --logs-only  # 只清空记录，保留结构")