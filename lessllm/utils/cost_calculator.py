"""
Cost calculation utilities
"""

from typing import Dict, Any, Optional


# 模型价格表 (USD per 1K tokens)
MODEL_PRICING = {
    # OpenAI Models
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-0613": {"input": 0.03, "output": 0.06},
    "gpt-4-32k": {"input": 0.06, "output": 0.12},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
    "gpt-3.5-turbo-0613": {"input": 0.0015, "output": 0.002},
    "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
    
    # Claude Models  
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    "claude-2.1": {"input": 0.008, "output": 0.024},
    "claude-2.0": {"input": 0.008, "output": 0.024},
}


def calculate_cost(usage: Dict[str, Any], model: str) -> float:
    """计算API调用成本"""
    if model not in MODEL_PRICING:
        return 0.0
    
    pricing = MODEL_PRICING[model]
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    
    # 计算成本 (价格是每1K tokens)
    input_cost = (prompt_tokens / 1000) * pricing["input"]
    output_cost = (completion_tokens / 1000) * pricing["output"]
    
    return round(input_cost + output_cost, 6)


def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    """估算成本"""
    usage = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens
    }
    return calculate_cost(usage, model)


def get_model_pricing(model: str) -> Optional[Dict[str, float]]:
    """获取模型价格信息"""
    return MODEL_PRICING.get(model)


def calculate_cost_savings(
    original_tokens: int, 
    cached_tokens: int, 
    model: str,
    cache_discount: float = 0.5
) -> Dict[str, Any]:
    """计算缓存节约的成本"""
    if model not in MODEL_PRICING:
        return {"savings_usd": 0.0, "savings_percentage": 0.0}
    
    pricing = MODEL_PRICING[model]
    
    # 原始成本（假设都是输入token）
    original_cost = (original_tokens / 1000) * pricing["input"]
    
    # 缓存后的成本
    fresh_tokens = original_tokens - cached_tokens
    fresh_cost = (fresh_tokens / 1000) * pricing["input"]
    cached_cost = (cached_tokens / 1000) * pricing["input"] * cache_discount
    
    new_cost = fresh_cost + cached_cost
    savings = original_cost - new_cost
    savings_percentage = (savings / original_cost) * 100 if original_cost > 0 else 0
    
    return {
        "original_cost_usd": round(original_cost, 6),
        "new_cost_usd": round(new_cost, 6),
        "savings_usd": round(savings, 6),
        "savings_percentage": round(savings_percentage, 2),
        "cached_tokens": cached_tokens,
        "fresh_tokens": fresh_tokens
    }


def get_cost_per_token(model: str, token_type: str = "input") -> float:
    """获取单个token的成本"""
    if model not in MODEL_PRICING:
        return 0.0
    
    pricing = MODEL_PRICING[model]
    return pricing.get(token_type, 0.0) / 1000


def calculate_monthly_budget_usage(
    total_cost: float, 
    monthly_budget: float
) -> Dict[str, Any]:
    """计算月度预算使用情况"""
    usage_percentage = (total_cost / monthly_budget) * 100 if monthly_budget > 0 else 0
    remaining_budget = max(0, monthly_budget - total_cost)
    
    return {
        "total_cost_usd": round(total_cost, 2),
        "monthly_budget_usd": monthly_budget,
        "remaining_budget_usd": round(remaining_budget, 2),
        "usage_percentage": round(usage_percentage, 2),
        "budget_exceeded": total_cost > monthly_budget
    }


def estimate_daily_cost_trend(costs_by_day: Dict[str, float]) -> Dict[str, Any]:
    """估算日成本趋势"""
    if not costs_by_day:
        return {"trend": "no_data", "daily_average": 0.0}
    
    daily_costs = list(costs_by_day.values())
    daily_average = sum(daily_costs) / len(daily_costs)
    
    # 简单的趋势分析
    if len(daily_costs) >= 3:
        recent_avg = sum(daily_costs[-3:]) / 3
        earlier_avg = sum(daily_costs[:-3]) / len(daily_costs[:-3]) if len(daily_costs) > 3 else daily_average
        
        if recent_avg > earlier_avg * 1.1:
            trend = "increasing"
        elif recent_avg < earlier_avg * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"
    
    return {
        "trend": trend,
        "daily_average": round(daily_average, 4),
        "recent_daily_average": round(sum(daily_costs[-7:]) / min(7, len(daily_costs)), 4),
        "total_days": len(daily_costs),
        "total_cost": round(sum(daily_costs), 2)
    }