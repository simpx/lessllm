# LessLLM 技术设计文档

## 整体架构

### 分层架构设计

```
┌─────────────────────────────────────┐
│             API Gateway             │ HTTP服务器(FastAPI)
├─────────────────────────────────────┤
│          Request Router             │ 路由和中间件
├─────────────────────────────────────┤
│       Provider Clients              │ OpenAI/Claude客户端
├─────────────────────────────────────┤
│      Performance Tracker            │ TTFT/TPOT性能监控
├─────────────────────────────────────┤
│       Cache Estimator               │ 智能缓存分析
├─────────────────────────────────────┤
│      Logging & Storage              │ 双轨数据记录
├─────────────────────────────────────┤
│       Network & Proxy              │ HTTP/SOCKS代理
└─────────────────────────────────────┘
```

### 模块结构

```
lessllm/
├── __init__.py
├── server.py              # FastAPI服务器
├── config.py              # 配置管理
├── proxy/                 # 网络代理模块
│   ├── __init__.py
│   ├── http_proxy.py      # HTTP/HTTPS代理
│   └── socks_proxy.py     # SOCKS代理
├── providers/             # API提供商
│   ├── __init__.py
│   ├── base.py           # 基础Provider类
│   ├── openai.py         # OpenAI API客户端
│   └── claude.py         # Claude API客户端
├── monitoring/            # 监控分析模块
│   ├── __init__.py
│   ├── performance.py    # 性能指标收集
│   └── cache_estimator.py # 缓存分析算法
├── logging/               # 日志系统
│   ├── __init__.py
│   ├── logger.py         # 日志记录器
│   ├── storage.py        # DuckDB存储
│   └── models.py         # 数据模型定义
└── utils/                 # 通用工具
    ├── __init__.py
    ├── token_counter.py  # Token计数工具
    └── cost_calculator.py # 成本计算
```

## 核心组件设计

### 1. 双轨数据记录系统

#### 设计原则
- **完整保存原始数据**: API请求和响应的100%忠实记录
- **独立分析预估**: lessllm自己的分析结果独立存储
- **对比验证机制**: 支持原始数据与预估分析的对比

#### 数据模型

```python
class RawAPIData(BaseModel):
    """原始API数据，完全忠实记录"""
    raw_request: Dict[str, Any]           # 完整原始请求
    raw_response: Dict[str, Any]          # 完整原始响应
    extracted_usage: Optional[Dict] = None # 标准化的usage信息
    extracted_cache_info: Optional[Dict] = None # API返回的缓存信息
    extracted_performance: Optional[Dict] = None # API返回的性能信息

class EstimatedAnalysis(BaseModel):
    """lessllm的分析预估"""
    estimated_performance: PerformanceAnalysis
    estimated_cache: CacheAnalysis
    estimated_cost_usd: Optional[float] = None
    analysis_timestamp: datetime

class APICallLog(BaseModel):
    """完整的API调用日志"""
    # 基础信息
    timestamp: datetime
    request_id: str
    provider: str
    model: str
    endpoint: str
    
    # 双轨数据
    raw_data: RawAPIData                  # 原始API数据
    estimated_analysis: EstimatedAnalysis # lessllm分析预估
    
    # 状态信息
    success: bool
    error_message: Optional[str] = None
    proxy_used: Optional[str] = None
```

### 2. 性能监控系统

#### TTFT/TPOT测量算法

```python
class PerformanceTracker:
    """精确的性能指标收集器"""
    
    def __init__(self):
        self.request_start = None
        self.first_token_time = None
        self.token_timestamps = []
        
    def start_request(self):
        """记录请求开始时间"""
        self.request_start = time.time()
        
    def record_first_token(self):
        """记录第一个token到达时间 - TTFT测量"""
        if self.first_token_time is None:
            self.first_token_time = time.time()
            
    def record_token(self):
        """记录每个token到达时间 - TPOT计算基础"""
        current_time = time.time()
        if self.first_token_time is None:
            self.record_first_token()
        self.token_timestamps.append(current_time)
        
    def calculate_metrics(self, output_tokens: int) -> PerformanceAnalysis:
        """计算最终性能指标"""
        # TTFT = 第一个token时间 - 请求开始时间
        ttft = (self.first_token_time - self.request_start) * 1000
        
        # TPOT = 总生成时间 / 输出token数
        if len(self.token_timestamps) > 1:
            generation_time = self.token_timestamps[-1] - self.first_token_time
            tpot = (generation_time * 1000) / output_tokens
        else:
            tpot = None
            
        return PerformanceAnalysis(
            ttft_ms=int(ttft),
            tpot_ms=round(tpot, 2) if tpot else None,
            total_latency_ms=int((self.token_timestamps[-1] - self.request_start) * 1000),
            tokens_per_second=output_tokens / generation_time if generation_time > 0 else None
        )
```

#### 流式与非流式处理

```python
async def handle_streaming_request(request, provider_client):
    """流式请求处理 - 可精确测量TTFT和TPOT"""
    tracker = PerformanceTracker()
    tracker.start_request()
    
    response_chunks = []
    
    async for chunk in provider_client.stream(request):
        tracker.record_token()  # 记录每个token的时间
        
        if chunk.choices and chunk.choices[0].delta.content:
            response_chunks.append(chunk.choices[0].delta.content)
    
    # 精确的性能指标
    performance = tracker.calculate_metrics(len(response_chunks))
    return response_chunks, performance

async def handle_non_streaming_request(request, provider_client):
    """非流式请求处理 - 只能测量总延迟"""
    tracker = PerformanceTracker()
    tracker.start_request()
    
    response = await provider_client.send(request)
    
    # 非流式响应：TTFT = 总延迟，TPOT无法测量
    performance = PerformanceAnalysis(
        ttft_ms=tracker.get_total_latency(),
        tpot_ms=None,  # 无法精确测量
        total_latency_ms=tracker.get_total_latency()
    )
    return response, performance
```

### 3. 智能缓存分析系统

#### 缓存预估算法

```python
class CacheEstimator:
    """智能缓存分析算法"""
    
    def __init__(self):
        self.system_message_cache = {}  # 系统消息缓存记录
        self.template_patterns = [      # 可缓存模板模式
            r"You are a helpful assistant",
            r"Please (analyze|review|explain)",
            r"Based on the following (context|information)",
            # ... 更多模式
        ]
        
    def estimate_cache_tokens(self, messages: List[Dict]) -> CacheAnalysis:
        """预估缓存token使用情况"""
        total_tokens = self._count_tokens(messages)
        
        # 1. 系统消息缓存分析
        system_cached = self._analyze_system_messages(messages)
        
        # 2. 模板和重复内容缓存分析  
        template_cached = self._analyze_templates(messages)
        
        # 3. 对话历史缓存分析
        history_cached = self._analyze_conversation_history(messages)
        
        estimated_cached = system_cached + template_cached + history_cached
        estimated_fresh = max(0, total_tokens - estimated_cached)
        
        return CacheAnalysis(
            estimated_cached_tokens=estimated_cached,
            estimated_fresh_tokens=estimated_fresh,
            estimated_cache_hit_rate=estimated_cached / total_tokens if total_tokens > 0 else 0,
            system_message_cached=system_cached,
            template_cached=template_cached,
            conversation_history_cached=history_cached
        )
    
    def _analyze_system_messages(self, messages):
        """分析系统消息的缓存潜力"""
        cached_tokens = 0
        for msg in messages:
            if msg.get("role") == "system":
                content_hash = hashlib.md5(msg["content"].encode()).hexdigest()
                if content_hash in self.system_message_cache:
                    cached_tokens += self._count_tokens([msg])
                else:
                    self.system_message_cache[content_hash] = msg["content"]
        return cached_tokens
        
    def _analyze_templates(self, messages):
        """识别常见模板和重复模式"""
        cached_tokens = 0
        for msg in messages:
            content = msg["content"]
            for pattern in self.template_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    matched_text = " ".join(matches)
                    cached_tokens += self._estimate_token_count(matched_text)
        return cached_tokens
```

#### 缓存效果对比

```python
class CacheAnalysisComparator:
    """对比预估缓存与实际缓存效果"""
    
    def compare_cache_accuracy(self, log: APICallLog) -> Dict[str, Any]:
        """计算缓存预估准确性"""
        estimated = log.estimated_analysis.estimated_cache
        actual = self._extract_actual_cache_from_raw(log.raw_data)
        
        if not actual:
            return {"status": "no_actual_data"}
            
        hit_rate_diff = actual["cache_hit_rate"] - estimated.estimated_cache_hit_rate
        accuracy_score = 1 - abs(hit_rate_diff)
        
        return {
            "hit_rate_difference": hit_rate_diff,
            "accuracy_score": accuracy_score,
            "estimation_quality": "excellent" if accuracy_score > 0.9 
                                 else "good" if accuracy_score > 0.7 
                                 else "needs_improvement",
            "estimated_cached": estimated.estimated_cached_tokens,
            "actual_cached": actual.get("cached_tokens"),
        }
```

### 4. 网络代理系统

#### 多协议代理支持

```python
class ProxyManager:
    """统一的代理管理器"""
    
    def __init__(self, config):
        self.http_proxy = config.get("http_proxy")
        self.socks_proxy = config.get("socks_proxy") 
        self.auth = config.get("auth", {})
        
    def get_httpx_client(self) -> httpx.AsyncClient:
        """获取配置了代理的httpx客户端"""
        proxies = {}
        
        if self.socks_proxy:
            proxies = {
                "http://": self.socks_proxy,
                "https://": self.socks_proxy
            }
        elif self.http_proxy:
            proxies = {
                "http://": self.http_proxy,
                "https://": self.http_proxy
            }
            
        # 代理认证
        auth = None
        if self.auth.get("username"):
            auth = (self.auth["username"], self.auth["password"])
            
        return httpx.AsyncClient(
            proxies=proxies,
            auth=auth,
            timeout=30.0,
            limits=httpx.Limits(max_connections=10)
        )
```

### 5. Provider抽象层

#### 统一的Provider接口

```python
class BaseProvider(ABC):
    """所有LLM提供商的基础接口"""
    
    @abstractmethod
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求到LLM API"""
        pass
        
    @abstractmethod 
    def parse_raw_response(self, request: dict, response: dict) -> RawAPIData:
        """解析原始API响应"""
        pass
        
    @abstractmethod
    def estimate_cost(self, usage: Dict[str, Any]) -> float:
        """估算API调用成本"""
        pass

class OpenAIProvider(BaseProvider):
    """OpenAI API提供商实现"""
    
    def __init__(self, api_key: str, proxy_manager: ProxyManager):
        self.api_key = api_key
        self.client = proxy_manager.get_httpx_client()
        
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = await self.client.post(
            "https://api.openai.com/v1/chat/completions",
            json=request,
            headers=headers
        )
        return response.json()
        
    def parse_raw_response(self, request: dict, response: dict) -> RawAPIData:
        """解析OpenAI响应格式"""
        extracted_usage = None
        if "usage" in response:
            extracted_usage = {
                "prompt_tokens": response["usage"].get("prompt_tokens"),
                "completion_tokens": response["usage"].get("completion_tokens"),
                "total_tokens": response["usage"].get("total_tokens")
            }
            
        return RawAPIData(
            raw_request=request,
            raw_response=response,
            extracted_usage=extracted_usage
        )
```

## 数据存储设计

### DuckDB表结构

```sql
-- 主要的API调用日志表
CREATE TABLE IF NOT EXISTS api_calls (
    -- 基础信息
    timestamp TIMESTAMP,
    request_id VARCHAR PRIMARY KEY,
    provider VARCHAR,
    model VARCHAR,
    endpoint VARCHAR,
    success BOOLEAN,
    error_message TEXT,
    
    -- 原始API数据（JSON格式完整保存）
    raw_request JSON,
    raw_response JSON,
    extracted_usage JSON,
    extracted_cache_info JSON,
    
    -- lessllm预估分析
    estimated_ttft_ms INTEGER,
    estimated_tpot_ms DOUBLE,
    estimated_total_latency_ms INTEGER,
    estimated_tokens_per_second DOUBLE,
    estimated_cached_tokens INTEGER,
    estimated_fresh_tokens INTEGER,
    estimated_cache_hit_rate DOUBLE,
    estimated_cost_usd DOUBLE,
    
    -- 从原始数据提取的关键字段（便于查询）
    actual_prompt_tokens INTEGER,
    actual_completion_tokens INTEGER,
    actual_total_tokens INTEGER,
    actual_cached_tokens INTEGER,
    actual_cache_hit_rate DOUBLE,
    
    -- 环境信息
    proxy_used VARCHAR,
    analysis_timestamp TIMESTAMP
);

-- 性能分析索引
CREATE INDEX idx_model_timestamp ON api_calls(model, timestamp);
CREATE INDEX idx_performance ON api_calls(estimated_ttft_ms, estimated_tpot_ms);
CREATE INDEX idx_cache_analysis ON api_calls(estimated_cache_hit_rate, actual_cache_hit_rate);

-- 缓存分析对比视图
CREATE VIEW cache_analysis_comparison AS
SELECT 
    request_id,
    provider,
    model,
    estimated_cache_hit_rate,
    actual_cache_hit_rate,
    (actual_cache_hit_rate - estimated_cache_hit_rate) as hit_rate_diff,
    ABS(actual_cache_hit_rate - estimated_cache_hit_rate) as prediction_error,
    timestamp
FROM api_calls 
WHERE actual_cache_hit_rate IS NOT NULL;
```

### 查询接口设计

```python
class QueryInterface:
    """统一的数据查询接口"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def query(self, sql: str) -> List[Dict]:
        """执行SQL查询"""
        with duckdb.connect(self.db_path) as conn:
            return conn.execute(sql).fetchdf().to_dict('records')
            
    def get_performance_stats(self, 
                            model: str = None, 
                            days: int = 7) -> Dict[str, Any]:
        """获取性能统计"""
        where_clause = "WHERE timestamp >= current_date - INTERVAL ? DAY"
        params = [days]
        
        if model:
            where_clause += " AND model = ?"
            params.append(model)
            
        sql = f"""
            SELECT 
                AVG(estimated_ttft_ms) as avg_ttft,
                AVG(estimated_tpot_ms) as avg_tpot,
                AVG(estimated_total_latency_ms) as avg_latency,
                COUNT(*) as total_requests
            FROM api_calls {where_clause}
        """
        
        return self.query(sql)[0] if self.query(sql) else {}
        
    def export_parquet(self, filepath: str, **filters):
        """导出数据到Parquet文件"""
        where_conditions = []
        params = []
        
        for key, value in filters.items():
            if key == "start_date":
                where_conditions.append("timestamp >= ?")
                params.append(value)
            elif key == "model":
                if isinstance(value, list):
                    placeholders = ",".join(["?" for _ in value])
                    where_conditions.append(f"model IN ({placeholders})")
                    params.extend(value)
                else:
                    where_conditions.append("model = ?")
                    params.append(value)
                    
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        sql = f"COPY (SELECT * FROM api_calls{where_clause}) TO '{filepath}' (FORMAT PARQUET)"
        
        with duckdb.connect(self.db_path) as conn:
            conn.execute(sql, params)
```

## 配置系统设计

### 配置文件结构

```yaml
# lessllm.yaml
proxy:
  http_proxy: "http://proxy.company.com:8080"
  socks_proxy: "socks5://127.0.0.1:1080"
  auth:
    username: "${PROXY_USER}"
    password: "${PROXY_PASS}"
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
```

### 配置管理器

```python
class Config(BaseSettings):
    """基于Pydantic的配置管理"""
    
    class ProxyConfig(BaseModel):
        http_proxy: Optional[str] = None
        socks_proxy: Optional[str] = None
        auth: Optional[Dict[str, str]] = None
        timeout: int = 30
        
    class LoggingConfig(BaseModel):
        enabled: bool = True
        level: str = "INFO"
        storage: Dict[str, Any] = {"type": "duckdb", "db_path": "./lessllm_logs.db"}
        
    class AnalysisConfig(BaseModel):
        enable_cache_estimation: bool = True
        enable_performance_tracking: bool = True
        cache_estimation_accuracy_threshold: float = 0.8
        
    proxy: ProxyConfig = ProxyConfig()
    providers: Dict[str, Dict[str, str]] = {}
    logging: LoggingConfig = LoggingConfig()
    analysis: AnalysisConfig = AnalysisConfig()
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

## 部署和使用模式

### 1. 独立服务器模式

```bash
# 安装
pip install lessllm

# 启动服务器
lessllm server --config lessllm.yaml --port 8000

# 客户端使用
export OPENAI_BASE_URL="http://localhost:8000/v1"
python my_ai_app.py
```

### 2. Python库集成模式  

```python
import lessllm

# 初始化配置
lessllm.configure({
    "proxy": {"socks_proxy": "socks5://127.0.0.1:1080"},
    "logging": {"enabled": True}
})

# 获取代理URL
proxy_url = lessllm.get_proxy_url()
client = openai.OpenAI(base_url=proxy_url)
```

### 3. Docker容器模式

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["lessllm", "server", "--host", "0.0.0.0", "--port", "8000"]
```

这个技术设计确保了lessllm的架构清晰、功能完整，同时保持了简单性和可扩展性的平衡。