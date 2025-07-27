"""
FastAPI server for LessLLM proxy
"""

import time
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from .config import get_config
from .proxy.manager import ProxyManager
from .providers.openai import OpenAIProvider
from .providers.claude import ClaudeProvider
from .logging.storage import LogStorage
from .logging.models import APICallLog, RawAPIData, EstimatedAnalysis, PerformanceAnalysis, CacheAnalysis
from .monitoring.performance import PerformanceTracker
from .monitoring.cache_estimator import CacheEstimator

logger = logging.getLogger(__name__)


def convert_claude_to_openai(claude_request: Dict[str, Any]) -> Dict[str, Any]:
    """将Claude Messages API请求转换为OpenAI Chat Completions格式"""
    openai_request = {
        "model": claude_request.get("model", "claude-3-5-sonnet-20241022"),
        "messages": [],
        "max_tokens": claude_request.get("max_tokens", 1000),
        "temperature": claude_request.get("temperature", 1.0),
        "stream": claude_request.get("stream", False)
    }
    
    # 转换messages格式
    messages = claude_request.get("messages", [])
    for msg in messages:
        if isinstance(msg.get("content"), str):
            # 简单文本消息
            openai_request["messages"].append({
                "role": msg["role"],
                "content": msg["content"]
            })
        elif isinstance(msg.get("content"), list):
            # 多模态消息，提取文本部分
            text_parts = []
            for content_block in msg["content"]:
                if content_block.get("type") == "text":
                    text_parts.append(content_block.get("text", ""))
            
            openai_request["messages"].append({
                "role": msg["role"],
                "content": " ".join(text_parts)
            })
    
    # 处理system消息
    if "system" in claude_request:
        openai_request["messages"].insert(0, {
            "role": "system",
            "content": claude_request["system"]
        })
    
    return openai_request


def convert_openai_to_claude_response(openai_response: Dict[str, Any], is_streaming: bool = False) -> Dict[str, Any]:
    """将OpenAI响应转换为Claude Messages API格式"""
    if is_streaming:
        # 流式响应转换
        if "choices" in openai_response and openai_response["choices"]:
            choice = openai_response["choices"][0]
            if "delta" in choice and "content" in choice["delta"]:
                return {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {
                        "type": "text_delta",
                        "text": choice["delta"]["content"]
                    }
                }
        return {"type": "ping"}
    else:
        # 非流式响应转换
        claude_response = {
            "id": openai_response.get("id", "msg_unknown"),
            "type": "message",
            "role": "assistant",
            "model": openai_response.get("model", "claude-3-5-sonnet-20241022"),
            "content": [],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": openai_response.get("usage", {}).get("prompt_tokens", 0),
                "output_tokens": openai_response.get("usage", {}).get("completion_tokens", 0)
            }
        }
        
        # 提取消息内容
        if "choices" in openai_response and openai_response["choices"]:
            content = openai_response["choices"][0].get("message", {}).get("content", "")
            claude_response["content"] = [{
                "type": "text",
                "text": content
            }]
        
        return claude_response

# 全局变量
app = FastAPI(title="LessLLM", description="Lightweight LLM API Proxy", version="0.1.0")
storage: Optional[LogStorage] = None
proxy_manager: Optional[ProxyManager] = None
providers: Dict[str, Any] = {}
cache_estimator: Optional[CacheEstimator] = None

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def init_app():
    """初始化应用"""
    global storage, proxy_manager, providers, cache_estimator
    
    # 尝试从环境变量或默认配置加载
    try:
        from .config import get_config
        config = get_config()
    except:
        # 如果无法获取全局配置，创建默认配置
        from .config import Config
        config = Config()
    
    # 初始化存储
    if config.logging.enabled:
        storage = LogStorage(config.logging.storage["db_path"])
    
    # 初始化代理管理器
    proxy_manager = ProxyManager(config.proxy)
    
    # 初始化提供商
    for provider_name, provider_config in config.providers.items():
        api_key = provider_config.get("api_key")
        base_url = provider_config.get("base_url")
        
        if not api_key:
            logger.warning(f"No API key provided for {provider_name}")
            continue
            
        if provider_name.lower() in ["openai", "openai-compatible"]:
            providers[provider_name] = OpenAIProvider(api_key, proxy_manager, base_url)
        elif provider_name.lower() in ["claude", "anthropic"]:
            providers[provider_name] = ClaudeProvider(api_key, proxy_manager, base_url)
        else:
            logger.warning(f"Unknown provider: {provider_name}")
    
    # 初始化缓存估算器
    if config.analysis.enable_cache_estimation:
        cache_estimator = CacheEstimator()
    
    logger.info(f"LessLLM initialized with {len(providers)} providers")


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    init_app()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    # 关闭所有provider连接
    for provider in providers.values():
        await provider.close()


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "LessLLM API Proxy",
        "version": "0.1.0",
        "providers": list(providers.keys())
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    config = get_config()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "providers": list(providers.keys()),
        "proxy": proxy_manager.get_proxy_info() if proxy_manager else None,
        "logging_enabled": config.logging.enabled,
        "cache_analysis_enabled": config.analysis.enable_cache_estimation
    }


def get_provider_for_model(model: str) -> tuple[str, Any]:
    """根据模型选择提供商"""
    # 简单的模型映射逻辑
    if model.startswith("gpt"):
        for name, provider in providers.items():
            if isinstance(provider, OpenAIProvider):
                return name, provider
    elif model.startswith("claude"):
        for name, provider in providers.items():
            if isinstance(provider, ClaudeProvider):
                return name, provider
    
    # 如果没有找到特定的提供商，使用第一个可用的
    if providers:
        first_provider = next(iter(providers.items()))
        return first_provider
    
    raise HTTPException(status_code=400, detail=f"No provider available for model: {model}")


async def handle_claude_messages_api(request: Request):
    """处理Claude Messages API请求 - 智能路由"""
    # 从request body获取数据
    request_data = await request.json()
    request_start_time = time.time()
    request_id = f"req_{int(time.time() * 1000)}"
    
    # 捕获完整的 HTTP 请求信息
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    request_headers = dict(request.headers)
    request_url = str(request.url)
    query_params = dict(request.query_params)
    
    # 记录Claude CLI的beta参数
    if query_params:
        logger.info(f"Claude Messages API called with query params: {query_params}")
    
    try:
        # 获取模型对应的提供商
        model = request_data.get("model", "claude-3-5-sonnet-20241022")
        provider_name, provider = get_provider_for_model(model)
        
        # 检查提供商类型，决定处理方式
        if isinstance(provider, ClaudeProvider):
            # Claude提供商：直接透传Claude Messages API
            logger.info(f"Direct passthrough: Claude Messages API → Claude Provider ({provider_name})")
            return await handle_claude_direct_passthrough(
                request_data, provider, provider_name, request_id, request_headers, 
                client_ip, user_agent, request_url, query_params
            )
        else:
            # 非Claude提供商：需要转换
            logger.info(f"Format conversion: Claude Messages API → OpenAI Provider ({provider_name})")
            return await handle_claude_to_openai_conversion(
                request_data, provider, provider_name, request_id, request_headers,
                client_ip, user_agent, request_url, query_params
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Claude Messages request {request_id} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_openai_chat_completions_api(request: Request):
    """处理OpenAI Chat Completions API请求 - 智能路由"""
    # 从request body获取数据
    request_data = await request.json()
    request_start_time = time.time()
    request_id = f"req_{int(time.time() * 1000)}"
    
    # 捕获完整的 HTTP 请求信息
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    request_headers = dict(request.headers)
    request_url = str(request.url)
    query_params = dict(request.query_params)
    
    try:
        # 获取模型对应的提供商
        model = request_data.get("model")
        if not model:
            raise HTTPException(status_code=400, detail="Model is required")
        
        provider_name, provider = get_provider_for_model(model)
        
        # 检查提供商类型，决定处理方式
        if isinstance(provider, OpenAIProvider):
            # OpenAI提供商：直接透传
            logger.info(f"Direct passthrough: OpenAI Chat Completions API → OpenAI Provider ({provider_name})")
            return await handle_openai_direct_passthrough(
                request_data, provider, provider_name, request_id, request_headers,
                client_ip, user_agent, request_url, query_params
            )
        elif isinstance(provider, ClaudeProvider):
            # Claude提供商：需要转换
            logger.info(f"Format conversion: OpenAI Chat Completions API → Claude Provider ({provider_name})")
            return await handle_openai_to_claude_conversion(
                request_data, provider, provider_name, request_id, request_headers,
                client_ip, user_agent, request_url, query_params
            )
        else:
            # 其他提供商：默认使用OpenAI格式
            logger.info(f"Default OpenAI format: OpenAI Chat Completions API → Provider ({provider_name})")
            return await handle_openai_direct_passthrough(
                request_data, provider, provider_name, request_id, request_headers,
                client_ip, user_agent, request_url, query_params
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OpenAI Chat Completions request {request_id} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 智能路由处理函数
# ============================================================================

async def handle_claude_direct_passthrough(
    request_data: Dict[str, Any], provider: Any, provider_name: str, request_id: str,
    request_headers: Dict[str, str], client_ip: str, user_agent: str, 
    request_url: str, query_params: Dict[str, Any]
):
    """Claude Messages API直接透传到Claude提供商"""
    # 初始化性能跟踪器
    performance_tracker = PerformanceTracker()
    performance_tracker.start_request()
    
    # 构建 HTTP 上下文信息
    http_context = {
        "client_ip": client_ip,
        "user_agent": user_agent,
        "request_headers": request_headers,
        "request_url": request_url,
        "query_params": query_params,
        "request_method": "POST"
    }
    
    # 检查是否为流式请求
    is_streaming = request_data.get("stream", False)
    
    if is_streaming:
        return StreamingResponse(
            handle_claude_messages_streaming(
                request_data, provider, provider_name, request_id, performance_tracker, http_context
            ),
            media_type="text/event-stream"
        )
    else:
        return await handle_claude_messages_regular(
            request_data, provider, provider_name, request_id, performance_tracker, http_context
        )


async def handle_claude_to_openai_conversion(
    request_data: Dict[str, Any], provider: Any, provider_name: str, request_id: str,
    request_headers: Dict[str, str], client_ip: str, user_agent: str,
    request_url: str, query_params: Dict[str, Any]
):
    """将Claude Messages API转换为OpenAI格式并发送到OpenAI提供商"""
    # 转换Claude Messages API格式到OpenAI Chat Completions格式
    openai_request = convert_claude_to_openai(request_data)
    
    # 初始化性能跟踪器
    performance_tracker = PerformanceTracker()
    performance_tracker.start_request()
    
    # 构建 HTTP 上下文信息
    http_context = {
        "client_ip": client_ip,
        "user_agent": user_agent,
        "request_headers": request_headers,
        "request_url": request_url,
        "query_params": query_params,
        "request_method": "POST"
    }
    
    # 检查是否为流式请求
    is_streaming = openai_request.get("stream", False)
    
    if is_streaming:
        # 流式响应需要转换回Claude格式
        return StreamingResponse(
            handle_openai_to_claude_streaming_conversion(
                openai_request, provider, provider_name, request_id, performance_tracker, http_context
            ),
            media_type="text/event-stream"
        )
    else:
        # 非流式响应
        response = await handle_regular_request(
            openai_request, provider, provider_name, request_id, performance_tracker, http_context
        )
        # 转换响应格式回Claude Messages API格式
        return convert_openai_to_claude_response(response)


async def handle_openai_direct_passthrough(
    request_data: Dict[str, Any], provider: Any, provider_name: str, request_id: str,
    request_headers: Dict[str, str], client_ip: str, user_agent: str,
    request_url: str, query_params: Dict[str, Any]
):
    """OpenAI Chat Completions API直接透传到OpenAI提供商"""
    # 初始化性能跟踪器
    performance_tracker = PerformanceTracker()
    performance_tracker.start_request()
    
    # 构建 HTTP 上下文信息
    http_context = {
        "client_ip": client_ip,
        "user_agent": user_agent,
        "request_headers": request_headers,
        "request_url": request_url,
        "query_params": query_params,
        "request_method": "POST"
    }
    
    # 检查是否为流式请求
    is_streaming = request_data.get("stream", False)
    
    if is_streaming:
        return StreamingResponse(
            handle_streaming_request(
                request_data, provider, provider_name, request_id, performance_tracker, http_context
            ),
            media_type="text/plain"
        )
    else:
        return await handle_regular_request(
            request_data, provider, provider_name, request_id, performance_tracker, http_context
        )


async def handle_openai_to_claude_conversion(
    request_data: Dict[str, Any], provider: Any, provider_name: str, request_id: str,
    request_headers: Dict[str, str], client_ip: str, user_agent: str,
    request_url: str, query_params: Dict[str, Any]
):
    """将OpenAI Chat Completions API转换为Claude格式并发送到Claude提供商"""
    # 使用provider的内置转换方法
    claude_request = provider._convert_to_claude_format(request_data)
    
    # 初始化性能跟踪器
    performance_tracker = PerformanceTracker()
    performance_tracker.start_request()
    
    # 构建 HTTP 上下文信息
    http_context = {
        "client_ip": client_ip,
        "user_agent": user_agent,
        "request_headers": request_headers,
        "request_url": request_url,
        "query_params": query_params,
        "request_method": "POST"
    }
    
    # 检查是否为流式请求
    is_streaming = claude_request.get("stream", False)
    
    if is_streaming:
        # 流式响应需要转换回OpenAI格式
        return StreamingResponse(
            handle_claude_to_openai_streaming_conversion(
                claude_request, provider, provider_name, request_id, performance_tracker, http_context
            ),
            media_type="text/plain"
        )
    else:
        # 非流式响应
        response = await provider.send_request(claude_request)
        # 转换响应格式回OpenAI Chat Completions格式
        return provider.normalize_response(response)


async def handle_openai_to_claude_streaming_conversion(
    claude_request: Dict[str, Any], provider: Any, provider_name: str, request_id: str,
    performance_tracker: PerformanceTracker, http_context: Dict[str, Any]
):
    """处理OpenAI到Claude的流式转换"""
    response_chunks = []
    full_response = {"choices": [{"message": {"content": ""}}]}
    
    try:
        async for chunk in provider.send_streaming_request(claude_request):
            # 记录token时间戳
            performance_tracker.record_token()
            
            # 将Claude流式响应转换为OpenAI格式
            openai_chunk = convert_claude_streaming_to_openai(chunk)
            if openai_chunk:
                response_chunks.append(openai_chunk)
                if openai_chunk.get("choices") and openai_chunk["choices"][0].get("delta", {}).get("content"):
                    full_response["choices"][0]["message"]["content"] += openai_chunk["choices"][0]["delta"]["content"]
                
                # 返回OpenAI格式的流式数据
                yield f"data: {json.dumps(openai_chunk)}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"OpenAI to Claude streaming conversion failed: {e}")
        yield f'data: {{"error": "{str(e)}"}}\n\n'
    
    # 异步记录日志
    if storage:
        asyncio.create_task(record_streaming_log(
            claude_request, full_response, provider, provider_name,
            request_id, performance_tracker, len(response_chunks), http_context
        ))


async def handle_claude_to_openai_streaming_conversion(
    openai_request: Dict[str, Any], provider: Any, provider_name: str, request_id: str,
    performance_tracker: PerformanceTracker, http_context: Dict[str, Any]
):
    """处理Claude到OpenAI的流式转换"""
    response_chunks = []
    full_response_content = ""
    
    try:
        async for chunk in provider.send_streaming_request(openai_request):
            # 记录token时间戳
            performance_tracker.record_token()
            
            # 将OpenAI流式响应转换为Claude格式
            claude_chunk = convert_openai_streaming_to_claude(chunk)
            if claude_chunk:
                response_chunks.append(claude_chunk)
                
                # 提取文本内容用于日志记录
                if claude_chunk.get("type") == "content_block_delta":
                    delta = claude_chunk.get("delta", {})
                    if delta.get("type") == "text_delta":
                        full_response_content += delta.get("text", "")
                
                # 返回Claude格式的流式数据
                yield f"data: {json.dumps(claude_chunk)}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Claude to OpenAI streaming conversion failed: {e}")
        error_chunk = {
            "type": "error",
            "error": {
                "type": "api_error", 
                "message": str(e)
            }
        }
        yield f'data: {json.dumps(error_chunk)}\n\n'
    
    # 异步记录日志
    if storage:
        asyncio.create_task(record_claude_streaming_log(
            openai_request, full_response_content, provider, provider_name,
            request_id, performance_tracker, len(response_chunks), http_context
        ))


def convert_claude_streaming_to_openai(claude_chunk: Dict[str, Any]) -> Dict[str, Any]:
    """将Claude流式响应转换为OpenAI格式"""
    if claude_chunk.get("type") == "content_block_delta":
        delta = claude_chunk.get("delta", {})
        if delta.get("type") == "text_delta":
            return {
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": delta.get("text", "")
                    }
                }]
            }
    return None


def convert_openai_streaming_to_claude(openai_chunk: Dict[str, Any]) -> Dict[str, Any]:
    """将OpenAI流式响应转换为Claude格式"""
    if "choices" in openai_chunk and openai_chunk["choices"]:
        choice = openai_chunk["choices"][0]
        if "delta" in choice and "content" in choice["delta"]:
            return {
                "type": "content_block_delta",
                "index": 0,
                "delta": {
                    "type": "text_delta",
                    "text": choice["delta"]["content"]
                }
            }
    return {"type": "ping"}


@app.post("/v1/messages")
async def messages(request: Request):
    """Claude Messages API端点 - 智能路由到合适的提供商"""
    return await handle_claude_messages_api(request)


@app.post("/v1/chat/completions") 
async def chat_completions(request: Request):
    """OpenAI Chat Completions API端点 - 智能路由到合适的提供商"""
    return await handle_openai_chat_completions_api(request)


async def chat_completions_internal(request_data: Dict[str, Any], request: Request):
    """内部聊天完成处理函数"""
    request_start_time = time.time()
    request_id = f"req_{int(time.time() * 1000)}"
    
    # 捕获完整的 HTTP 请求信息
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    request_headers = dict(request.headers)
    request_url = str(request.url)
    query_params = dict(request.query_params)
    
    try:
        # 获取模型对应的提供商
        model = request_data.get("model")
        if not model:
            raise HTTPException(status_code=400, detail="Model is required")
        
        provider_name, provider = get_provider_for_model(model)
        
        # 初始化性能跟踪器
        performance_tracker = PerformanceTracker()
        performance_tracker.start_request()
        
        # 检查是否为流式请求
        is_streaming = request_data.get("stream", False)
        
        # 构建 HTTP 上下文信息
        http_context = {
            "client_ip": client_ip,
            "user_agent": user_agent,
            "request_headers": request_headers,
            "request_url": request_url,
            "query_params": query_params,
            "request_method": "POST"
        }
        
        if is_streaming:
            return StreamingResponse(
                handle_streaming_request(
                    request_data, provider, provider_name, request_id, performance_tracker, http_context
                ),
                media_type="text/plain"
            )
        else:
            return await handle_regular_request(
                request_data, provider, provider_name, request_id, performance_tracker, http_context
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Request {request_id} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_regular_request(
    request_data: Dict[str, Any], 
    provider: Any, 
    provider_name: str, 
    request_id: str,
    performance_tracker: PerformanceTracker,
    http_context: Dict[str, Any]
) -> Dict[str, Any]:
    """处理常规（非流式）请求"""
    
    try:
        # 发送请求
        response = await provider.send_request(request_data)
        
        # 记录性能指标
        performance_metrics = performance_tracker.calculate_non_streaming_metrics()
        
        # 估算缓存
        cache_analysis = CacheAnalysis()
        if cache_estimator:
            messages = request_data.get("messages", [])
            cache_analysis = cache_estimator.estimate_cache_tokens(messages)
        
        # 解析原始数据
        raw_data = provider.parse_raw_response(request_data, response)
        
        # 增强原始数据，添加 HTTP 信息
        raw_data.request_headers = http_context["request_headers"]
        raw_data.client_ip = http_context["client_ip"]
        raw_data.user_agent = http_context["user_agent"]
        raw_data.request_url = http_context["request_url"]
        raw_data.request_query_params = http_context["query_params"]
        raw_data.request_method = http_context["request_method"]
        
        # 模拟响应信息（实际应该从 provider 返回）
        raw_data.response_status_code = 200
        raw_data.response_headers = {"content-type": "application/json"}
        if isinstance(response, dict):
            raw_data.response_size_bytes = len(json.dumps(response).encode('utf-8'))
        
        # 估算成本
        estimated_cost = 0.0
        if raw_data.extracted_usage:
            estimated_cost = provider.estimate_cost(raw_data.extracted_usage, request_data["model"])
        
        # 创建分析数据
        estimated_analysis = EstimatedAnalysis(
            estimated_performance=performance_metrics,
            estimated_cache=cache_analysis,
            estimated_cost_usd=estimated_cost
        )
        
        # 记录日志
        if storage:
            log = APICallLog(
                request_id=request_id,
                provider=provider_name,
                model=request_data["model"],
                endpoint="chat/completions",
                raw_data=raw_data,
                estimated_analysis=estimated_analysis,
                success=True,
                proxy_used=proxy_manager.get_proxy_info()["active_proxy"] if proxy_manager else None
            )
            
            # 异步存储日志
            asyncio.create_task(store_log_async(log))
        
        return response
        
    except Exception as e:
        # 记录失败日志
        if storage:
            error_log = APICallLog(
                request_id=request_id,
                provider=provider_name,
                model=request_data.get("model", "unknown"),
                endpoint="chat/completions",
                raw_data=RawAPIData(raw_request=request_data, raw_response={}),
                estimated_analysis=EstimatedAnalysis(
                    estimated_performance=PerformanceAnalysis(total_latency_ms=0),
                    estimated_cache=CacheAnalysis()
                ),
                success=False,
                error_message=str(e)
            )
            asyncio.create_task(store_log_async(error_log))
        
        raise


async def handle_streaming_request(
    request_data: Dict[str, Any], 
    provider: Any, 
    provider_name: str, 
    request_id: str,
    performance_tracker: PerformanceTracker,
    http_context: Dict[str, Any]
):
    """处理流式请求"""
    
    response_chunks = []
    full_response = {"choices": [{"message": {"content": ""}}]}
    
    try:
        async for chunk in provider.send_streaming_request(request_data):
            # 记录token时间戳
            performance_tracker.record_token()
            
            # 收集响应数据
            response_chunks.append(chunk)
            if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                full_response["choices"][0]["message"]["content"] += chunk["choices"][0]["delta"]["content"]
            
            # 返回给客户端
            yield f"data: {chunk}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Streaming request {request_id} failed: {e}")
        yield f'data: {{"error": "{str(e)}"}}\n\n'
    
    # 异步记录日志
    if storage:
        asyncio.create_task(record_streaming_log(
            request_data, full_response, provider, provider_name, 
            request_id, performance_tracker, len(response_chunks), http_context
        ))


async def record_streaming_log(
    request_data: Dict[str, Any],
    response: Dict[str, Any],
    provider: Any,
    provider_name: str,
    request_id: str,
    performance_tracker: PerformanceTracker,
    chunk_count: int,
    http_context: Dict[str, Any]
):
    """记录流式请求日志"""
    
    try:
        # 计算性能指标
        performance_metrics = performance_tracker.calculate_metrics(chunk_count)
        
        # 估算缓存
        cache_analysis = CacheAnalysis()
        if cache_estimator:
            messages = request_data.get("messages", [])
            cache_analysis = cache_estimator.estimate_cache_tokens(messages)
        
        # 解析原始数据
        raw_data = provider.parse_raw_response(request_data, response)
        
        # 增强原始数据，添加 HTTP 信息
        raw_data.request_headers = http_context["request_headers"]
        raw_data.client_ip = http_context["client_ip"]
        raw_data.user_agent = http_context["user_agent"]
        raw_data.request_url = http_context["request_url"]
        raw_data.request_query_params = http_context["query_params"]
        raw_data.request_method = http_context["request_method"]
        raw_data.response_status_code = 200
        raw_data.response_headers = {"content-type": "text/plain; charset=utf-8"}
        if isinstance(response, dict):
            raw_data.response_size_bytes = len(json.dumps(response).encode('utf-8'))
        
        # 估算成本
        estimated_cost = 0.0
        if raw_data.extracted_usage:
            estimated_cost = provider.estimate_cost(raw_data.extracted_usage, request_data["model"])
        
        # 创建分析数据
        estimated_analysis = EstimatedAnalysis(
            estimated_performance=performance_metrics,
            estimated_cache=cache_analysis,
            estimated_cost_usd=estimated_cost
        )
        
        # 创建日志
        log = APICallLog(
            request_id=request_id,
            provider=provider_name,
            model=request_data["model"],
            endpoint="chat/completions",
            raw_data=raw_data,
            estimated_analysis=estimated_analysis,
            success=True,
            proxy_used=proxy_manager.get_proxy_info()["active_proxy"] if proxy_manager else None
        )
        
        storage.store_log(log)
        
    except Exception as e:
        logger.error(f"Failed to record streaming log: {e}")


async def store_log_async(log: APICallLog):
    """异步存储日志"""
    try:
        storage.store_log(log)
    except Exception as e:
        logger.error(f"Failed to store log: {e}")


async def handle_claude_messages_regular(
    request_data: Dict[str, Any], 
    provider: Any, 
    provider_name: str, 
    request_id: str,
    performance_tracker: PerformanceTracker,
    http_context: Dict[str, Any]
) -> Dict[str, Any]:
    """处理Claude Messages API的常规请求"""
    
    try:
        # 直接发送Claude格式请求
        response = await provider.send_claude_messages_request(request_data)
        
        # 记录性能指标
        performance_metrics = performance_tracker.calculate_non_streaming_metrics()
        
        # 估算缓存
        cache_analysis = CacheAnalysis()
        if cache_estimator:
            messages = request_data.get("messages", [])
            cache_analysis = cache_estimator.estimate_cache_tokens(messages)
        
        # 解析原始数据
        raw_data = RawAPIData(
            raw_request=request_data,
            raw_response=response,
            request_headers=http_context["request_headers"],
            client_ip=http_context["client_ip"],
            user_agent=http_context["user_agent"],
            request_url=http_context["request_url"],
            request_query_params=http_context["query_params"],
            request_method=http_context["request_method"],
            response_status_code=200,
            response_headers={"content-type": "application/json"},
            response_size_bytes=len(json.dumps(response).encode('utf-8'))
        )
        
        # 从Claude响应中提取usage信息
        if "usage" in response:
            raw_data.extracted_usage = response["usage"]
        
        # 估算成本
        estimated_cost = 0.0
        if raw_data.extracted_usage:
            estimated_cost = provider.estimate_cost(raw_data.extracted_usage, request_data.get("model", "claude-3-5-sonnet-20241022"))
        
        # 创建分析数据
        estimated_analysis = EstimatedAnalysis(
            estimated_performance=performance_metrics,
            estimated_cache=cache_analysis,
            estimated_cost_usd=estimated_cost
        )
        
        # 记录日志
        if storage:
            log = APICallLog(
                request_id=request_id,
                provider=provider_name,
                model=request_data.get("model", "claude-3-5-sonnet-20241022"),
                endpoint="messages",
                raw_data=raw_data,
                estimated_analysis=estimated_analysis,
                success=True,
                proxy_used=proxy_manager.get_proxy_info()["active_proxy"] if proxy_manager else None
            )
            
            # 异步存储日志
            asyncio.create_task(store_log_async(log))
        
        return response
        
    except Exception as e:
        # 记录失败日志
        if storage:
            error_log = APICallLog(
                request_id=request_id,
                provider=provider_name,
                model=request_data.get("model", "claude-3-5-sonnet-20241022"),
                endpoint="messages",
                raw_data=RawAPIData(raw_request=request_data, raw_response={}),
                estimated_analysis=EstimatedAnalysis(
                    estimated_performance=PerformanceAnalysis(total_latency_ms=0),
                    estimated_cache=CacheAnalysis()
                ),
                success=False,
                error_message=str(e)
            )
            asyncio.create_task(store_log_async(error_log))
        
        raise


async def handle_claude_messages_streaming(
    request_data: Dict[str, Any], 
    provider: Any, 
    provider_name: str, 
    request_id: str,
    performance_tracker: PerformanceTracker,
    http_context: Dict[str, Any]
):
    """处理Claude Messages API的流式请求"""
    
    response_chunks = []
    full_response_content = ""
    
    try:
        async for chunk in provider.send_claude_messages_streaming_request(request_data):
            # 记录token时间戳
            performance_tracker.record_token()
            
            # 收集响应数据
            response_chunks.append(chunk)
            
            # 提取文本内容用于日志记录
            if chunk.get("type") == "content_block_delta":
                delta = chunk.get("delta", {})
                if delta.get("type") == "text_delta":
                    full_response_content += delta.get("text", "")
            
            # 直接转发Claude格式的流式响应
            yield f"data: {json.dumps(chunk)}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Claude Messages streaming request {request_id} failed: {e}")
        error_chunk = {
            "type": "error",
            "error": {
                "type": "api_error",
                "message": str(e)
            }
        }
        yield f'data: {json.dumps(error_chunk)}\n\n'
    
    # 异步记录日志
    if storage:
        asyncio.create_task(record_claude_streaming_log(
            request_data, full_response_content, provider, provider_name, 
            request_id, performance_tracker, len(response_chunks), http_context
        ))


async def record_claude_streaming_log(
    request_data: Dict[str, Any],
    response_content: str,
    provider: Any,
    provider_name: str,
    request_id: str,
    performance_tracker: PerformanceTracker,
    chunk_count: int,
    http_context: Dict[str, Any]
):
    """记录Claude Messages流式请求日志"""
    
    try:
        # 计算性能指标
        performance_metrics = performance_tracker.calculate_metrics(chunk_count)
        
        # 估算缓存
        cache_analysis = CacheAnalysis()
        if cache_estimator:
            messages = request_data.get("messages", [])
            cache_analysis = cache_estimator.estimate_cache_tokens(messages)
        
        # 构建响应数据
        response = {
            "type": "message",
            "content": [{"type": "text", "text": response_content}],
            "model": request_data.get("model", "claude-3-5-sonnet-20241022")
        }
        
        # 解析原始数据
        raw_data = RawAPIData(
            raw_request=request_data,
            raw_response=response,
            request_headers=http_context["request_headers"],
            client_ip=http_context["client_ip"],
            user_agent=http_context["user_agent"],
            request_url=http_context["request_url"],
            request_query_params=http_context["query_params"],
            request_method=http_context["request_method"],
            response_status_code=200,
            response_headers={"content-type": "text/plain; charset=utf-8"},
            response_size_bytes=len(response_content.encode('utf-8'))
        )
        
        # 估算成本
        estimated_cost = 0.0
        
        # 创建分析数据
        estimated_analysis = EstimatedAnalysis(
            estimated_performance=performance_metrics,
            estimated_cache=cache_analysis,
            estimated_cost_usd=estimated_cost
        )
        
        # 创建日志
        log = APICallLog(
            request_id=request_id,
            provider=provider_name,
            model=request_data.get("model", "claude-3-5-sonnet-20241022"),
            endpoint="messages",
            raw_data=raw_data,
            estimated_analysis=estimated_analysis,
            success=True,
            proxy_used=proxy_manager.get_proxy_info()["active_proxy"] if proxy_manager else None
        )
        
        storage.store_log(log)
        
    except Exception as e:
        logger.error(f"Failed to record Claude streaming log: {e}")


@app.get("/v1/models")
async def list_models():
    """列出可用模型"""
    models = []
    
    for provider_name, provider in providers.items():
        # 这里可以扩展为从每个provider获取其支持的模型列表
        if isinstance(provider, OpenAIProvider):
            models.extend([
                {"id": "gpt-4", "object": "model", "owned_by": "openai"},
                {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "openai"}
            ])
        elif isinstance(provider, ClaudeProvider):
            models.extend([
                {"id": "claude-3-opus-20240229", "object": "model", "owned_by": "anthropic"},
                {"id": "claude-3-sonnet-20240229", "object": "model", "owned_by": "anthropic"}
            ])
    
    return {"data": models}


@app.get("/lessllm/stats")
async def get_stats():
    """获取LessLLM统计信息"""
    if not storage:
        raise HTTPException(status_code=503, detail="Logging not enabled")
    
    try:
        # 获取基本统计
        db_stats = storage.get_database_stats()
        performance_stats = storage.get_performance_stats(days=7)
        cache_stats = storage.get_cache_analysis_summary(days=7)
        
        return {
            "database": db_stats,
            "performance": performance_stats,
            "cache_analysis": cache_stats,
            "recent_logs": storage.get_recent_logs(limit=10)
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def start_server(host: str = "0.0.0.0", port: int = 8000, **kwargs):
    """启动服务器"""
    uvicorn.run(
        "lessllm.server:app",
        host=host,
        port=port,
        reload=False,
        **kwargs
    )