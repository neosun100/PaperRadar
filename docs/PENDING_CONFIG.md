# PaperRadar — 待补充信息清单

**日期**: 2026-02-23

---

## 1. 🎧 Audio Summary (NotebookLM 风格播客) — 需要 TTS API

### 当前状态
代码已完成（`backend/app/services/audio_summary.py`），但需要一个 **OpenAI 兼容的 TTS API**。

### 代码调用方式
```python
POST {base_url}/audio/speech
Body: {"model": "tts-1", "input": "text", "voice": "alloy", "response_format": "mp3"}
Header: Authorization: Bearer {api_key}
```

### 你需要提供的
**方案 A：通过 LiteLLM 代理**（推荐）
- 在 LiteLLM 配置中添加 TTS 路由
- 如果 LiteLLM 支持 OpenAI TTS 或其他 TTS 服务的代理

**方案 B：直接用 OpenAI TTS**
- 需要 OpenAI API Key（支持 `/audio/speech` 端点）
- 在 secrets config 中加一个 `tts_base_url` 和 `tts_api_key`

**方案 C：用你服务器上已有的 TTS 服务**
你的服务器上已经有这些 TTS 服务在运行：
- `cosyvoice` (端口 8188)
- `kokoro-tts` (端口 8300)
- `chatterbox-tts` (端口 7866)
- `qwen3-tts` (端口 8766)

如果其中任何一个支持 OpenAI 兼容的 `/audio/speech` 端点，告诉我它的地址，我直接配置。

### 需要加到 secrets config 的字段
```yaml
# 在 /path/to/your/config.yaml 中加：
tts:
  base_url: "http://localhost:8300/v1"  # 或你的 TTS 服务地址
  api_key: ""                            # 如果需要
  model: "tts-1"                         # TTS 模型名
```

---

## 2. 🔔 推送通知 — 需要 Bark/Lark 配置

### 当前状态
代码已完成，需要配置 key 即可激活。

### Bark (iOS 推送)
```yaml
notification:
  bark_url: "https://api.day.app"    # 或你的自建 Bark 服务器
  bark_key: "YOUR_BARK_DEVICE_KEY"   # 从 Bark App 获取
```

### Lark (飞书卡片推送)
```yaml
notification:
  lark_webhook: "https://open.larksuite.com/open-apis/bot/v2/hook/YOUR_WEBHOOK_ID"
```

---

## 3. 📋 当前系统状态

| 指标 | 数值 |
|------|------|
| 版本 | v1.9.2 |
| 总 commits | 80+ |
| 知识库论文 | 23 篇 (19 完成) |
| 向量 chunks | 970 |
| Embedding 模型 | Bedrock Cohere Embed v4 ✅ |
| LLM 模型 | Bedrock Claude Haiku 4.5 ✅ |
| TTS | ❌ 待配置 |
| Bark 推送 | ❌ 待配置 |
| Lark 推送 | ❌ 待配置 |

---

## 4. 🔄 继续迭代方式

### 手动迭代（推荐，效率最高）
在 Kiro CLI 中继续对话，说"继续"即可。

### 自动迭代（后台运行）
```bash
tmux new -s paperradar
cd /home/neo/upload/EasyPaper
./auto-iterate.sh 1000
# Ctrl+B, D 脱离
```
注意：每轮约 30-60 分钟，效率不如手动。

### 监控
```bash
tmux attach -t paperradar          # 查看自动迭代
git log --oneline -10               # 查看提交
curl -s localhost:9200/health       # 系统状态
```

---

## 5. 下一步开发优先级

1. **配置 TTS** → 激活 Audio Summary
2. **配置 Bark/Lark** → 激活推送通知
3. Paper Annotation & Highlighting in Reader
4. AI Inline Explanations
5. 更多数据源 (Papers with Code, alphaXiv)
6. Collaborative Features
7. Mobile Responsive

---

*等你提供 TTS API 信息后，我立即集成。*
