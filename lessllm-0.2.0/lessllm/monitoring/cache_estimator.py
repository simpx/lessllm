"""
Intelligent cache analysis system
"""

import re
import hashlib
from typing import List, Dict, Any
from ..logging.models import CacheAnalysis
from ..utils.token_counter import count_tokens


class CacheEstimator:
    """智能缓存分析算法"""
    
    def __init__(self):
        self.system_message_cache: Dict[str, str] = {}  # 系统消息缓存记录
        self.template_patterns = [      # 可缓存模板模式
            r"You are a helpful assistant",
            r"Please (analyze|review|explain|summarize)",
            r"Based on the following (context|information|data)",
            r"Act as a (professional|expert|senior)",
            r"Given the (following|above) (code|text|document)",
            r"Here is (the|a) (code|function|class|file)",
            r"Can you help me (with|to)",
            r"I need (help|assistance) (with|for)",
            r"What (is|are|would be) the",
            r"How (do|can|should) (I|you|we)",
        ]
        
    def estimate_cache_tokens(self, messages: List[Dict[str, Any]]) -> CacheAnalysis:
        """预估缓存token使用情况"""
        if not messages:
            return CacheAnalysis()
            
        total_tokens = self._count_messages_tokens(messages)
        
        # 1. 系统消息缓存分析
        system_cached = self._analyze_system_messages(messages)
        
        # 2. 模板和重复内容缓存分析  
        template_cached = self._analyze_templates(messages)
        
        # 3. 对话历史缓存分析
        history_cached = self._analyze_conversation_history(messages)
        
        estimated_cached = min(total_tokens, system_cached + template_cached + history_cached)
        estimated_fresh = max(0, total_tokens - estimated_cached)
        
        return CacheAnalysis(
            estimated_cached_tokens=estimated_cached,
            estimated_fresh_tokens=estimated_fresh,
            estimated_cache_hit_rate=estimated_cached / total_tokens if total_tokens > 0 else 0,
            system_message_cached=system_cached,
            template_cached=template_cached,
            conversation_history_cached=history_cached
        )
    
    def _count_messages_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """计算消息总token数"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += count_tokens(content)
            elif isinstance(content, list):
                # 处理多模态内容
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        total += count_tokens(item.get("text", ""))
        return total
    
    def _analyze_system_messages(self, messages: List[Dict[str, Any]]) -> int:
        """分析系统消息的缓存潜力"""
        cached_tokens = 0
        for msg in messages:
            if msg.get("role") == "system":
                content = msg.get("content", "")
                if isinstance(content, str):
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                    if content_hash in self.system_message_cache:
                        cached_tokens += count_tokens(content)
                    else:
                        self.system_message_cache[content_hash] = content
        return cached_tokens
        
    def _analyze_templates(self, messages: List[Dict[str, Any]]) -> int:
        """识别常见模板和重复模式"""
        cached_tokens = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                for pattern in self.template_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        # 估算模板部分的token数
                        matched_text = " ".join(matches)
                        cached_tokens += min(count_tokens(matched_text), count_tokens(content) // 4)
                        break  # 每个消息只计算一次模板缓存
        return cached_tokens
    
    def _analyze_conversation_history(self, messages: List[Dict[str, Any]]) -> int:
        """分析对话历史的缓存潜力"""
        if len(messages) <= 2:
            return 0
            
        # 假设除最后一条消息外，其他消息有可能被缓存
        cached_tokens = 0
        for msg in messages[:-1]:  # 排除最后一条消息
            content = msg.get("content", "")
            if isinstance(content, str):
                # 根据消息位置和长度调整缓存概率
                msg_tokens = count_tokens(content)
                cache_probability = self._calculate_history_cache_probability(msg, len(messages))
                cached_tokens += int(msg_tokens * cache_probability)
        
        return cached_tokens
    
    def _calculate_history_cache_probability(self, message: Dict[str, Any], total_messages: int) -> float:
        """计算历史消息的缓存概率"""
        role = message.get("role", "")
        content = message.get("content", "")
        
        # 基础缓存概率
        base_probability = 0.3
        
        # 系统消息更容易被缓存
        if role == "system":
            base_probability = 0.8
        
        # 短消息更容易被缓存
        content_length = len(content)
        if content_length < 100:
            base_probability += 0.2
        elif content_length < 500:
            base_probability += 0.1
        
        # 重复内容更容易被缓存
        if self._has_repetitive_patterns(content):
            base_probability += 0.2
        
        return min(1.0, base_probability)
    
    def _has_repetitive_patterns(self, content: str) -> bool:
        """检测内容是否有重复模式"""
        # 简单的重复模式检测
        words = content.lower().split()
        if len(words) < 10:
            return False
            
        # 检查是否有重复的短语
        phrases = []
        for i in range(len(words) - 2):
            phrase = " ".join(words[i:i+3])
            if phrase in phrases:
                return True
            phrases.append(phrase)
        
        return False
    
    def get_cache_optimization_suggestions(self, messages: List[Dict[str, Any]]) -> List[str]:
        """获取缓存优化建议"""
        suggestions = []
        
        # 检查系统消息
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        if len(system_messages) > 1:
            suggestions.append("考虑合并多个系统消息以提高缓存效率")
        
        # 检查重复模板
        template_usage = {}
        for msg in messages:
            content = msg.get("content", "")
            for pattern in self.template_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    template_usage[pattern] = template_usage.get(pattern, 0) + 1
        
        frequent_templates = [pattern for pattern, count in template_usage.items() if count > 1]
        if frequent_templates:
            suggestions.append(f"发现重复模板模式：{', '.join(frequent_templates[:3])}")
        
        # 检查消息长度
        long_messages = [msg for msg in messages if len(msg.get("content", "")) > 2000]
        if long_messages:
            suggestions.append("考虑分割过长的消息以提高缓存命中率")
        
        return suggestions