#!/usr/bin/env python3
"""
更新现有数据库中的token信息
从extracted_usage JSON字段中提取并更新actual_*字段
"""

import duckdb
import json
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from lessllm.config import get_config

def update_token_data():
    """更新token数据"""
    try:
        # 获取数据库路径
        config = get_config()
        db_path = config.logging.storage.get("db_path", "./lessllm_logs.db")
        
        print(f"Updating token data in database: {db_path}")
        
        with duckdb.connect(db_path) as conn:
            # 获取所有有usage数据但actual_*字段为空的记录
            rows = conn.execute("""
                SELECT request_id, extracted_usage 
                FROM api_calls 
                WHERE extracted_usage IS NOT NULL 
                AND (actual_prompt_tokens IS NULL OR actual_completion_tokens IS NULL)
            """).fetchall()
            
            print(f"Found {len(rows)} records to update")
            
            updated_count = 0
            for request_id, extracted_usage_json in rows:
                try:
                    usage = json.loads(extracted_usage_json)
                    
                    # 提取token信息
                    prompt_tokens = None
                    completion_tokens = None
                    total_tokens = None
                    
                    # 支持OpenAI格式
                    if 'prompt_tokens' in usage:
                        prompt_tokens = usage.get('prompt_tokens')
                        completion_tokens = usage.get('completion_tokens')
                        total_tokens = usage.get('total_tokens')
                    # 支持Claude格式
                    elif 'input_tokens' in usage:
                        prompt_tokens = usage.get('input_tokens')
                        completion_tokens = usage.get('output_tokens')
                        if prompt_tokens and completion_tokens:
                            total_tokens = prompt_tokens + completion_tokens
                    
                    # 更新数据库
                    if prompt_tokens is not None or completion_tokens is not None:
                        conn.execute("""
                            UPDATE api_calls 
                            SET actual_prompt_tokens = ?, 
                                actual_completion_tokens = ?, 
                                actual_total_tokens = ?
                            WHERE request_id = ?
                        """, (prompt_tokens, completion_tokens, total_tokens, request_id))
                        updated_count += 1
                        
                except json.JSONDecodeError:
                    print(f"Warning: Invalid JSON in extracted_usage for request {request_id}")
                    continue
                except Exception as e:
                    print(f"Error processing request {request_id}: {e}")
                    continue
            
            print(f"Successfully updated {updated_count} records")
            
            # 验证更新结果
            result = conn.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(actual_prompt_tokens) as records_with_prompt_tokens,
                    COUNT(actual_completion_tokens) as records_with_completion_tokens,
                    COUNT(actual_total_tokens) as records_with_total_tokens,
                    SUM(actual_prompt_tokens) as total_prompt_tokens,
                    SUM(actual_completion_tokens) as total_completion_tokens
                FROM api_calls
                WHERE extracted_usage IS NOT NULL
            """).fetchone()
            
            print("\nUpdate verification:")
            print(f"  Total records with usage data: {result[0]}")
            print(f"  Records with prompt tokens: {result[1]}")
            print(f"  Records with completion tokens: {result[2]}")
            print(f"  Records with total tokens: {result[3]}")
            print(f"  Total prompt tokens: {result[4] or 0}")
            print(f"  Total completion tokens: {result[5] or 0}")
            
    except Exception as e:
        print(f"Error updating token data: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = update_token_data()
    if success:
        print("\n✅ Token data update completed successfully!")
    else:
        print("\n❌ Token data update failed!")
        sys.exit(1)