[English](README.md) | [简体中文](README_zh.md)


<h1 align="center">🛰️ PaperRadar</h1>

<p align="center">
  <strong>自动发现、理解并串联前沿研究。</strong>
</p>

---

PaperRadar 是一个**自托管**的 AI 驱动研究平台，能够自动发现、翻译、分析和关联学术论文。内置雷达引擎每小时扫描 arXiv 最新论文，通过 LLM 智能筛选，并推送通知到你的手机。

> **BYOK（自带密钥）** — 所有 LLM 凭证保存在浏览器 localStorage 中。处理结果存储在云端，所有用户共享。

## ✨ 功能特性

### 🛰️ 论文雷达引擎
每小时自动扫描 arXiv 配置类目（cs.CL、cs.AI、cs.LG）的最新论文。使用 LLM 作为智能 Agent 评估相关性，下载高质量论文并自动处理。

### 💬 论文对话
直接与知识库中的任何论文对话。提问、比较方法、探索发现——基于论文全文和提取的知识。

### 📖 翻译与简化
将英文论文翻译为中文或简化为简单英语（CEFR A2/B1），保留排版、图片和公式。基于 [pdf2zh](https://github.com/Byaidu/PDFMathTranslate)。

### 🎨 AI 高亮
自动识别并用颜色标注关键句子：
- 🟡 黄色 — 核心结论
- 🔵 蓝色 — 方法创新
- 🟢 绿色 — 关键数据

### 🔬 研究洞察
AI 驱动的跨论文分析：
- **领域综述** — 自动生成文献综述
- **方法对比** — 并排对比矩阵
- **研究脉络** — 技术演进时间线
- **研究空白** — 未解决的问题和未来方向
- **论文关联** — 论文之间的关系网络

### 🧠 知识库
从论文中提取结构化知识——实体、关系、发现和闪卡——以 JSON 格式存储。所有内容双语输出（中英文）。

### 🕸️ 知识图谱
跨论文实体和关系的交互式力导向图可视化。

### 🔔 智能推送
雷达发现并处理新论文后推送通知：
- **Bark** — iOS 推送通知
- **Lark** — 互动卡片 2.0 消息

### 🌍 多语言界面
完整的中英文界面，一键切换。

---

## 🚀 快速开始

```bash
docker run -d --name paperradar \
  -p 9201:80 \
  -v paperradar-data:/app/data \
  -v paperradar-tmp:/app/tmp \
  neosun/paperradar:latest
```

打开 **http://localhost:9201**，在设置中配置 LLM API Key，开始上传论文。

---

## 📄 许可证

MIT
