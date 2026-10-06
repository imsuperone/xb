# 更新日志

## v0.7.46
- 📦 **测试脚本不上包**：pack 排除 `selftest/`（12 个探针文件），成品包从 105 条降到 93 条；main.py「测试testxb」调用处本就 try/except 兜底，selftest 缺失时优雅降级。
- 🧹 **文档只留最新一版**：CHANGELOG 裁掉 79 个历史版本节、README 删 v0.7.43 及更早 16 段版本介绍，均只保留最新一版，历史可查 git。
