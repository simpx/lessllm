# LessLLM 测试策略和计划

## 测试目标

1. **确保代码质量**：保证核心功能的正确性和稳定性
2. **网络连通性验证**：确保代理功能在各种网络环境下正常工作
3. **数据完整性**：验证双轨数据记录的准确性和完整性
4. **性能基准**：验证TTFT/TPOT测量的准确性
5. **兼容性测试**：确保与OpenAI/Claude API的完全兼容

## 测试分层策略

### 1. 单元测试 (Unit Tests)
- **覆盖率目标**: 80%+
- **测试粒度**: 单个函数/方法
- **测试重点**: 业务逻辑、边界条件、异常处理

#### 测试模块划分
```
tests/unit/
├── test_config.py          # 配置管理测试
├── test_proxy_manager.py   # 代理管理器测试
├── test_providers/         # Provider测试
│   ├── test_base.py
│   ├── test_openai.py
│   └── test_claude.py
├── test_storage.py         # DuckDB存储测试
├── test_monitoring/        # 监控模块测试
│   ├── test_performance.py
│   └── test_cache_estimator.py
└── test_utils/             # 工具函数测试
    ├── test_token_counter.py
    └── test_cost_calculator.py
```

### 2. 集成测试 (Integration Tests)
- **测试组件间交互**
- **数据库操作验证**
- **API端点测试**

#### 集成测试重点
```
tests/integration/
├── test_server_endpoints.py    # FastAPI端点测试
├── test_proxy_flow.py          # 代理请求流程测试
├── test_logging_flow.py        # 日志记录流程测试
└── test_provider_integration.py # Provider集成测试
```

### 3. 端到端测试 (E2E Tests)
- **完整用户场景验证**
- **真实API调用测试**
- **性能基准测试**

#### E2E测试场景
```
tests/e2e/
├── test_openai_compatibility.py  # OpenAI客户端兼容性
├── test_streaming_flow.py        # 流式请求完整流程
├── test_proxy_scenarios.py       # 各种代理场景
└── test_performance_benchmarks.py # 性能基准测试
```

## 测试环境设置

### 开发环境
```bash
# 安装测试依赖
pip install -e .[dev]

# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_config.py -v

# 代码覆盖率
pytest --cov=lessllm --cov-report=html
```

### Mock和Fixture策略
- **HTTP请求Mock**: 使用`httpx_mock`模拟API响应
- **数据库Mock**: 使用内存DuckDB进行测试
- **配置Fixture**: 预定义测试配置
- **时间Mock**: 控制时间相关测试

## 测试数据管理

### 测试数据分类
1. **标准测试数据**: 正常的API请求/响应示例
2. **边界测试数据**: 极端情况下的数据
3. **错误测试数据**: 各种错误场景的数据
4. **性能测试数据**: 用于性能基准的数据

### 数据隐私保护
- 所有测试数据脱敏处理
- 不使用真实API密钥进行单元测试
- 敏感信息使用Mock替代

## 测试质量指标

### 代码覆盖率目标
- **总体覆盖率**: ≥80%
- **核心模块覆盖率**: ≥90%
  - config.py: ≥95%
  - proxy/manager.py: ≥90%
  - providers/: ≥85%
  - logging/storage.py: ≥90%

### 性能指标
- **单元测试执行时间**: <30秒
- **集成测试执行时间**: <2分钟
- **完整测试套件**: <5分钟

## 特殊测试场景

### 网络连通性测试
```python
# 代理连接测试矩阵
proxy_scenarios = [
    {"type": "direct", "proxy": None},
    {"type": "http", "proxy": "http://proxy:8080"},
    {"type": "socks5", "proxy": "socks5://proxy:1080"},
    {"type": "auth", "proxy": "http://user:pass@proxy:8080"}
]
```

### 并发测试
- 多线程代理请求
- 并发数据库写入
- 流式请求并发处理

### 错误恢复测试
- 网络中断恢复
- API限流处理
- 数据库连接失败恢复

## 持续集成策略

### GitHub Actions工作流
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: pip install -e .[dev]
      - name: Run tests
        run: pytest --cov=lessllm
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 测试优先级

### P0 (关键路径)
- [ ] 配置加载和验证
- [ ] 代理连接建立
- [ ] API请求转发
- [ ] 数据记录完整性

### P1 (核心功能)
- [ ] 性能指标计算
- [ ] 缓存分析算法
- [ ] 错误处理和恢复
- [ ] 流式请求处理

### P2 (增强功能)
- [ ] CLI命令行工具
- [ ] 统计查询接口
- [ ] 数据导出功能
- [ ] 配置热重载

## 测试执行计划

### 阶段1: 基础单元测试 (本周)
- 配置管理系统测试
- 代理管理器测试
- 基础Provider测试
- 存储系统测试

### 阶段2: 集成测试 (下周)
- FastAPI服务器集成测试
- 端到端请求流程测试
- 监控系统集成测试

### 阶段3: 性能和稳定性测试 (第三周)
- 性能基准测试
- 压力测试
- 长期稳定性测试

这个测试策略确保了LessLLM的质量和可靠性，特别关注网络连通性和本地化数据分析这两个核心优势。