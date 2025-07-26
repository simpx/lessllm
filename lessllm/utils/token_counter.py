"""
Token counting utilities
"""

import re
from typing import Union, List, Dict, Any


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    简单的token计数器（估算）
    在生产环境中应该使用tiktoken等专业库
    """
    if not text:
        return 0
    
    # 简单的token估算：每个单词大约1个token，标点符号也算
    # 这是一个粗略的估算，实际应该使用tokenizer
    
    # 分割单词和标点符号  
    tokens = re.findall(r'\w+|[^\w\s]', text)
    
    # 对于中文等，每个字符大约是1个token
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    
    # 基础token数
    base_count = len(tokens) + len(chinese_chars)
    
    # 不同模型的token计算可能略有不同
    if model.startswith("gpt-4"):
        # GPT-4 token计算通常更准确
        return base_count
    elif model.startswith("claude"):
        # Claude的token计算
        return int(base_count * 0.95)  # Claude通常稍微少一点
    else:
        return base_count


def count_messages_tokens(messages: List[Dict[str, Any]], model: str = "gpt-3.5-turbo") -> int:
    """计算消息列表的总token数"""
    total_tokens = 0
    
    for message in messages:
        # 角色字段的token
        role = message.get("role", "")
        total_tokens += count_tokens(role, model)
        
        # 内容字段的token
        content = message.get("content", "")
        if isinstance(content, str):
            total_tokens += count_tokens(content, model)
        elif isinstance(content, list):
            # 多模态内容
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        total_tokens += count_tokens(item.get("text", ""), model)
                    # 图片token计算更复杂，这里简单处理
                    elif item.get("type") == "image_url":
                        total_tokens += 85  # OpenAI图片基础token
        
        # 消息格式的额外token开销
        total_tokens += 4  # 每条消息大约4个额外token
    
    # 对话格式的额外开销
    total_tokens += 2
    
    return total_tokens


def estimate_max_tokens_for_model(model: str) -> int:
    """估算模型的最大token限制"""
    model_limits = {
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "gpt-4-turbo-preview": 128000,
        "claude-3-opus-20240229": 200000,
        "claude-3-sonnet-20240229": 200000,
        "claude-3-haiku-20240307": 200000,
        "claude-2.1": 200000,
        "claude-2.0": 100000,
    }
    
    return model_limits.get(model, 4096)


def validate_token_limit(messages: List[Dict[str, Any]], model: str, max_tokens: int = None) -> Dict[str, Any]:
    """验证token限制"""
    if max_tokens is None:
        max_tokens = estimate_max_tokens_for_model(model)
    
    input_tokens = count_messages_tokens(messages, model)
    max_completion_tokens = max_tokens - input_tokens - 100  # 保留100个token作为缓冲
    
    return {
        "input_tokens": input_tokens,
        "max_tokens": max_tokens,
        "available_for_completion": max_completion_tokens,
        "within_limit": max_completion_tokens > 0,
        "token_usage_percentage": (input_tokens / max_tokens) * 100
    }