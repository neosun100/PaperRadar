[English](README.md) | [简体中文](README_zh.md)

<h1 align="center">🛰️ PaperRadar</h1>

<p align="center">
  <strong>自动发现、理解并串联前沿研究。</strong>
</p>

<p align="center">
  <a href="https://github.com/neosun100/PaperRadar/stargazers"><img src="https://img.shields.io/github/stars/neosun100/PaperRadar?style=social" alt="Stars"></a>
  <a href="https://hub.docker.com/r/neosun/paperradar"><img src="https://img.shields.io/docker/pulls/neosun/paperradar" alt="Docker Pulls"></a>
  <a href="https://github.com/neosun100/PaperRadar/blob/main/LICENSE"><img src="https://img.shields.io/github/license/neosun100/PaperRadar" alt="License"></a>
  <img src="https://img.shields.io/badge/version-2.4.0-blue" alt="Version">
</p>

---

PaperRadar 是一个**自托管**的 AI 驱动学术研究平台，自动发现、翻译、分析和关联学术论文。内置雷达引擎每小时扫描 arXiv，用 LLM 智能评分，并推送通知到手机。

> **BYOK（自带密钥）** — 所有 LLM 凭证保存在浏览器 localStorage 中。处理结果存储在云端，所有用户共享。

## ✨ 核心功能

- 🛰️ **论文雷达** — 自动扫描 arXiv + Semantic Scholar + HuggingFace，智能评分
- 💬 **论文对话** — 单篇/跨论文 RAG 对话（ChromaDB 向量搜索）
- 📖 **多语言翻译** — 英→中、中→英、简化英文（pdf2zh）
- 🎨 **AI 高亮** — 三色标注：结论/方法/数据
- ✏️ **批注 & AI 解释** — 彩色笔记 + 粘贴句子即时解释
- 🔬 **研究洞察** — 文献综述、方法对比、数据提取表、写作助手
- 📊 **引用智能** — 引用网络图谱 + scite.ai 风格引用上下文 + OpenAlex 元数据
- 🎧 **音频摘要** — NotebookLM 风格播客生成
- 🧠 **知识库** — 双语知识提取、论文集、知识图谱、闪卡复习、个性化排序
- 📦 **多格式导出** — JSON / BibTeX / Obsidian / CSL-JSON / CSV
- 🔔 **推送通知** — Bark / 飞书 / Webhook（Slack、Discord 等）
- 🤖 **MCP 服务器** — 12 个工具，集成 Claude/Cursor
- 🌍 **中英双语 UI + 暗色模式**

## 🚀 快速开始

```bash
docker run -d --name paperradar \
  -p 9201:80 \
  -v paperradar-data:/app/data \
  -v paperradar-tmp:/app/tmp \
  neosun/paperradar:latest
```

打开 **http://localhost:9201**，在设置中配置 LLM API 密钥即可开始使用。

## 📄 许可证

MIT
