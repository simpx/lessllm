# LessLLM 开发指南

## 环境设置

### 使用 uv 进行项目管理

本项目使用 [uv](https://docs.astral.sh/uv/) 作为 Python 包管理器和虚拟环境管理工具，提供更快的依赖解析和安装速度。

#### 1. 安装 uv

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 添加到 PATH（根据你的 shell 配置）
export PATH="$HOME/.local/bin:$PATH"

# 验证安装
uv --version
```

#### 2. 项目设置

```bash
# 克隆项目
git clone https://github.com/simpx/lessllm.git
cd lessllm

# 安装所有依赖（包括开发依赖）
uv sync --dev

# 只安装基础依赖
uv sync

# 安装特定额外依赖组
uv sync --extra test      # 测试依赖
uv sync --extra docs      # 文档依赖
```

#### 3. 激活虚拟环境

```bash
# 方式1: 使用 uv run 运行命令
uv run python -c "import lessllm; print(lessllm.__version__)"
uv run pytest
uv run lessllm --help

# 方式2: 激活虚拟环境（传统方式）
source .venv/bin/activate  # Linux/macOS
# 或
.venv\\Scripts\\activate   # Windows

# 退出虚拟环境
deactivate
```

## 项目结构

```
lessllm/
├── lessllm/                 # 主包目录
│   ├── __init__.py
│   ├── cli.py              # 命令行接口
│   ├── config.py           # 配置管理
│   ├── server.py           # FastAPI服务器
│   ├── proxy/              # 代理管理模块
│   ├── providers/          # LLM提供商抽象
│   ├── logging/            # 日志和存储系统
│   ├── monitoring/         # 性能监控和缓存分析
│   └── utils/              # 工具函数
├── tests/                  # 测试目录
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   ├── e2e/               # 端到端测试
│   └── conftest.py        # pytest配置
├── docs/                   # 文档
├── examples/               # 示例代码和配置
├── pyproject.toml         # 项目配置和依赖
├── .gitignore
└── README.md
```

## 开发工作流

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试类型
uv run pytest tests/unit                    # 单元测试
uv run pytest tests/integration             # 集成测试
uv run pytest tests/e2e                     # 端到端测试

# 运行特定测试文件
uv run pytest tests/unit/test_config.py

# 运行带覆盖率的测试
uv run pytest --cov=lessllm --cov-report=html

# 跳过覆盖率检查
uv run pytest --no-cov
```

### 代码质量检查

```bash
# 代码格式化
uv run black lessllm tests
uv run isort lessllm tests

# 代码检查
uv run ruff check lessllm tests
uv run ruff --fix lessllm tests

# 类型检查
uv run mypy lessllm

# 一键格式化和检查（如果使用hatch环境）
uv run --group lint format
uv run --group lint check
```

### 运行服务器

```bash
# 开发模式运行
uv run lessllm server --config examples/lessllm.yaml --port 8000

# 或者直接运行模块
uv run python -m lessllm.cli server --port 8000

# 生成配置文件
uv run lessllm init --output my-config.yaml
```

## 依赖管理

### 添加新依赖

```bash
# 添加运行时依赖
uv add httpx fastapi

# 添加开发依赖
uv add --dev pytest black

# 添加可选依赖组
uv add --optional docs mkdocs
```

### 更新依赖

```bash
# 更新所有依赖
uv sync --upgrade

# 更新特定包
uv sync --upgrade-package httpx
```

### 锁定依赖版本

uv 会自动生成 `uv.lock` 文件来锁定确切的依赖版本，确保在不同环境中的一致性。

## 配置管理

### pyproject.toml 主要配置

- **project**: 项目元数据和依赖
- **project.optional-dependencies**: 可选依赖组（dev, test, docs）
- **project.scripts**: 命令行脚本入口点
- **tool.pytest.ini_options**: pytest 配置
- **tool.black**: 代码格式化配置
- **tool.ruff**: 代码检查配置
- **tool.mypy**: 类型检查配置
- **tool.coverage**: 覆盖率配置

### 环境变量

创建 `.env` 文件来设置环境变量：

```bash
# .env 文件示例
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-claude-key
PROXY_USER=your-proxy-username
PROXY_PASS=your-proxy-password
```

## 测试策略

### 测试分层

1. **单元测试** (tests/unit/): 测试单个函数和类
2. **集成测试** (tests/integration/): 测试组件间交互
3. **端到端测试** (tests/e2e/): 测试完整用户场景

### 测试标记

使用 pytest 标记来分类测试：

```python
@pytest.mark.unit
def test_config_loading():
    pass

@pytest.mark.integration
def test_proxy_flow():
    pass

@pytest.mark.network
def test_actual_api_call():
    pass

@pytest.mark.slow  
def test_performance_benchmark():
    pass
```

### 运行特定标记的测试

```bash
uv run pytest -m unit                    # 只运行单元测试
uv run pytest -m "not network"           # 跳过网络测试
uv run pytest -m "integration and not slow"  # 集成测试但跳过慢速测试
```

## CI/CD 集成

### GitHub Actions 示例

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      - name: Set up Python
        run: uv python install ${{ matrix.python-version }}
      - name: Install dependencies
        run: uv sync --dev
      - name: Run tests
        run: uv run pytest --cov=lessllm
      - name: Upload coverage
        uses: codecov/codecov-action@v4
```

## 调试技巧

### 使用 iPython/Jupyter

```bash
# 安装调试工具
uv add --dev ipython jupyter

# 启动 iPython
uv run ipython

# 在代码中添加断点
import IPython; IPython.embed()
```

### 使用 pytest 调试

```bash
# 进入 pdb 调试器
uv run pytest --pdb

# 在第一个失败时停止
uv run pytest -x

# 显示详细输出
uv run pytest -v -s
```

## 性能优化

### uv 优化

- uv 使用 Rust 编写，比传统的 pip 快 10-100 倍
- 并行下载和安装依赖
- 智能缓存机制
- 更好的依赖解析算法

### 开发技巧

1. 使用 `uv run` 而不是激活虚拟环境，减少环境切换开销
2. 利用 `uv.lock` 文件确保环境一致性
3. 使用 `--no-dev` 在生产环境中只安装必需依赖
4. 定期运行 `uv sync --upgrade` 更新依赖

这个开发指南确保了团队成员能够快速上手，并遵循最佳实践进行开发。