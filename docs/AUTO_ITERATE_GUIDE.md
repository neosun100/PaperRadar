# Kiro CLI 自循环迭代指南

## 概述

使用 Kiro CLI 在 tmux 中实现 AI 自驱动的持续开发迭代。AI 会自动读取项目上下文、选择任务、实现功能、测试、构建、部署、推送，然后进入下一轮。

## 前置条件

1. Kiro CLI 已安装并登录
2. tmux 已安装（`apt install tmux`）
3. Docker 已登录（`docker login`）
4. Git 已配置推送权限

## 核心文件

项目中需要两个关键文件让 AI 保持上下文：

### CONTEXT.md — AI 的记忆

包含项目的所有关键信息，每次迭代 AI 都会先读这个文件：
- 项目名称、仓库地址、Docker Hub 地址
- 技术架构、关键文件路径
- 已完成功能列表
- 构建部署流程（精确命令）
- 关键规则（不可违反的约束）
- 密钥保护策略

**重要**：每次手动开发后，务必更新 CONTEXT.md。

### TODO.md — AI 的任务清单

按优先级排列的待办事项，AI 每轮从中选择最高优先级任务执行。

## 启动步骤

### 1. 启动 tmux 会话

```bash
tmux new -s paperradar
```

### 2. 进入项目目录并启动

```bash
cd /home/neo/upload/EasyPaper
./auto-iterate.sh 1000
```

### 3. 脱离 tmux（进程继续运行）

按 `Ctrl+B`，然后按 `D`

现在可以安全关闭终端，AI 会持续运行。

## 日常操作

### 查看进度

```bash
# 重新连接 tmux 看实时输出
tmux attach -t paperradar

# 查看 Git 提交历史
cd /home/neo/upload/EasyPaper && git log --oneline -20

# 查看系统状态
curl -s http://localhost:9200/health | python3 -m json.tool

# 查看当前 Docker 版本
docker ps --format "{{.Image}}" | grep paperradar
```

### 暂停迭代

```bash
# 方式1：连接 tmux 后按 Ctrl+C
tmux attach -t paperradar
# 然后 Ctrl+C

# 方式2：直接杀进程
tmux kill-session -t paperradar
```

### 恢复迭代

```bash
tmux new -s paperradar
cd /home/neo/upload/EasyPaper
./auto-iterate.sh 1000
# Ctrl+B, D 脱离
```

### 手动介入后恢复

如果你手动做了开发，恢复前务必：

```bash
# 1. 更新 CONTEXT.md（加入新完成的功能）
# 2. 更新 TODO.md（调整优先级）
# 3. 提交
cd /home/neo/upload/EasyPaper
git add -A && git commit -m "docs: update context" && git push origin main
# 4. 重新启动迭代
tmux new -s paperradar
./auto-iterate.sh 1000
```

## auto-iterate.sh 关键参数

| 参数 | 说明 |
|------|------|
| `HOME=~/.kiro-homes/account3` | Kiro 认证目录，必须匹配你的登录账号 |
| `--trust-all-tools` | 允许 AI 执行所有工具（文件读写、命令执行等） |
| `--model claude-opus-4.6-1m` | 使用 1M 上下文的 Opus 模型 |
| `1000` | 最大迭代次数，每轮约 5-15 分钟 |

## 风险与注意事项

### 已知限制
- 每轮是独立会话，AI 通过 CONTEXT.md 恢复上下文
- 深度上下文不如连续对话，复杂重构可能出偏差
- 建议每天早上检查 `git log` 确认没有走偏

### 安全检查清单
```bash
# 检查是否有密钥泄露到 Git
cd /home/neo/upload/EasyPaper
grep -rn "sk-y7wO\|litellm.aws\|cohere.embed" --include='*.py' --include='*.ts' --include='*.yaml' . | grep -v node_modules

# 检查 Docker 镜像是否干净
docker run --rm neosun/paperradar:latest cat /app/config/config.yaml | grep api_key
# 应该显示空值
```

### 回滚
```bash
# 如果 AI 搞砸了，回滚到某个版本
git log --oneline -20  # 找到好的 commit
git reset --hard <commit_hash>
git push origin main --force
```

## 模板：适配其他项目

将此模式应用到其他项目，需要：

1. 创建 `CONTEXT.md`：项目架构、文件、规则、构建流程
2. 创建 `TODO.md`：按优先级排列的任务
3. 复制 `auto-iterate.sh`，修改 PROMPT 中的项目特定信息
4. 用 tmux 启动

```bash
# 通用启动模板
tmux new -s <project_name>
cd <project_dir>
./auto-iterate.sh <iterations>
# Ctrl+B, D
```
