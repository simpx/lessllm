# LessLLM GUI 使用说明

## 启动GUI

```bash
# 使用CLI命令启动GUI
lessllm gui --port 8501 --host localhost

# 或者使用Python模块方式启动
python -c "import lessllm.cli; lessllm.cli.main()" gui --port 8501 --host localhost
```

## 访问GUI

启动后，在浏览器中打开以下地址：
http://localhost:8501

## 常见问题解决

1. **无法访问GUI**：
   - 确保GUI已正确启动
   - 检查端口是否被占用：`netstat -tuln | grep 8501`
   - 确保防火墙允许本地访问

2. **数据库连接错误**：
   - 确保lessllm_logs.db文件存在
   - 确保配置文件中数据库路径正确

3. **依赖项缺失**：
   - 安装GUI依赖项：`pip install -e .[gui]`