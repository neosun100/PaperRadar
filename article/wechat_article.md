>微信公众号：**[AI健自习室]**
>关注Crypto与LLM技术、关注`AI-StudyLab`。问题或建议，请公众号留言。

# 【一键部署系列】｜｜Paper｜EasyPaper 让英文论文不再难读，自带翻译+AI高亮+知识库

>[!info]
>**原项目**: [CzsGit/EasyPaper](https://github.com/CzsGit/EasyPaper)
>**增强版**: [neosun100/EasyPaper](https://github.com/neosun100/EasyPaper)
>**在线体验**: [https://easypaper.aws.xin](https://easypaper.aws.xin)

> 读英文论文最痛苦的不是理解不了内容——而是读了三遍才发现自己一直在查单词，根本没进入深度思考。EasyPaper 就是为了解决这个问题：上传 PDF，拿回一份翻译好的、重点高亮好的、知识结构化好的论文。你自带 API Key，数据不离开你的浏览器。

![EasyPaper 宣传图](https://zfile.aws.xin/directlink/1/easypaper/banner.png)

---

## 🤔 为什么做这个？

每个搞 AI 的人都有同一个痛点：**论文读不完，读不快，读不透。**

我试过很多工具：
- **Google 翻译** — 翻译质量勉强，但排版全毁了，公式变乱码
- **ChatGPT 直接扔 PDF** — 回答挺好，但我想要的是一份完整的翻译版 PDF，不是问答
- **各种论文阅读器** — 要么收费，要么数据上传到别人服务器，隐私堪忧

我想要的很简单：**一个自部署的工具，用我自己的 API Key，翻译完保持原始排版，顺便帮我高亮重点、提取知识。**

于是有了 EasyPaper。

### 现有方案 vs EasyPaper

| 特性 | Google 翻译 | ChatGPT | Kimi/通义 | **EasyPaper** |
|------|-----------|---------|----------|--------------|
| PDF 翻译保留排版 | ❌ 全毁 | ❌ 纯文本 | ⚠️ 部分 | ✅ 完整保留 |
| 公式/图片保留 | ❌ | ❌ | ⚠️ | ✅ |
| AI 重点高亮 | ❌ | ❌ | ❌ | ✅ 三色分类 |
| 知识库提取 | ❌ | ⚠️ 手动 | ❌ | ✅ 自动结构化 |
| 知识图谱 | ❌ | ❌ | ❌ | ✅ |
| 闪卡复习 | ❌ | ❌ | ❌ | ✅ SM-2 算法 |
| 自部署 | - | - | - | ✅ Docker |
| 数据隐私 | ❌ 上传 Google | ❌ 上传 OpenAI | ❌ 上传云端 | ✅ 自带 Key |

---

## 🚀 30 秒部署

```bash
git clone https://github.com/neosun100/EasyPaper.git
cd EasyPaper
docker compose up --build -d
```

打开 `http://localhost:9201` —— 搞定。不需要注册，不需要登录，打开就用。

第一次使用时，点右上角 ⚙️ 配置你的 API Key（支持 OpenAI / Anthropic / OpenRouter 等任何 OpenAI 兼容 API）。

> 🔒 你的 API Key 只存在浏览器的 localStorage 中，永远不会上传到服务器。

---

## ✨ 核心功能

### 1. 翻译 & 简化

- **英→中翻译**：保留 PDF 原始排版、图片、公式（基于 [pdf2zh](https://github.com/Byaidu/PDFMathTranslate)）
- **英→简单英语**：CEFR A2/B1 级别词汇替换，适合非母语读者
- PDF 进，PDF 出 —— 图表、公式、格式完整保留

![EasyPaper UI](https://zfile.aws.xin/directlink/1/easypaper/screenshot_ui.png)

### 2. AI 智能高亮

自动识别论文关键句子，三色分类：

| 颜色 | 类别 | 高亮内容 |
|------|------|---------|
| 🟡 黄色 | 核心结论 | 主要发现和研究成果 |
| 🔵 蓝色 | 方法创新 | 新方法和技术贡献 |
| 🟢 绿色 | 关键数据 | 定量结果、指标、实验数据 |

省去你满篇找重点的时间 —— AI 帮你标好了。

### 3. 知识库（可导出）

通过 LLM 从论文中自动提取结构化知识：

- **实体**：方法、模型、数据集、指标、概念
- **关系**：extends、uses、outperforms、contradicts
- **发现**：结果、局限性、贡献
- **闪卡**：自动生成学习卡片，SM-2 间隔重复

知识以 JSON 存储，支持导出为 **Obsidian 笔记库** 或 **BibTeX**，不锁定在任何平台。

### 4. 知识图谱

所有论文的实体和关系，以交互式图谱展示。节点可点击，关系可过滤。帮你看清论文之间的知识网络。

---

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | FastAPI, PyMuPDF, pdf2zh, httpx |
| 前端 | React 18, TypeScript, Tailwind, Radix UI |
| 数据库 | SQLite（零配置） |
| AI | 任何 OpenAI 兼容 API（你自带 Key） |
| 部署 | Docker Compose（两个容器：后端 + 前端） |

### BYOK（Bring Your Own Key）架构

这是 EasyPaper 最核心的设计决策：**工具是壳子，AI 是你的。**

- API Key 存在浏览器 localStorage，不上传
- 每个 API 请求通过 HTTP Header 传递你的 Key
- 后端不存储任何凭证
- 你可以随时换模型（GPT-4o → Claude → Gemini）

---

## ⚙️ 配置

打开右上角 ⚙️，三个字段：

| 字段 | 示例 | 说明 |
|------|------|------|
| API Endpoint | `https://api.openai.com/v1` | 提供预设下拉 |
| API Key | `sk-xxx...` | 你自己的 Key |
| Model | `gpt-4o` | 推荐 gpt-4o 或 claude-3.5-sonnet |

内置预设：OpenAI / Anthropic / OpenRouter / 自定义。

---

## 📚 API 接口

| 端点 | 说明 |
|------|------|
| `POST /api/upload` | 上传 PDF（翻译/简化/高亮） |
| `GET /api/status/{id}` | 处理进度（支持 SSE 实时推送） |
| `GET /api/result/{id}/pdf` | 下载处理后的 PDF |
| `POST /api/knowledge/extract/{id}` | 触发知识提取 |
| `GET /api/knowledge/graph` | 获取知识图谱 |
| `GET /api/knowledge/flashcards/due` | 获取待复习闪卡 |
| `GET /api/knowledge/export/json` | 导出完整知识库 |
| `GET /api/knowledge/export/obsidian` | 导出为 Obsidian |

完整 Swagger 文档：`/api/docs`

---

## 💡 坦诚说不足

1. **翻译速度**：取决于你用的 LLM API 速度，长论文（50+ 页）可能需要几分钟
2. **公式翻译**：极复杂的 LaTeX 公式偶尔会有排版偏差
3. **中文生成质量**：依赖底层模型能力，GPT-4o 效果最好
4. **暂无批量处理**：目前一次上传一篇
5. **知识图谱**：节点多时渲染可能略卡

---

## 📚 参考资料

1. [pdf2zh - PDFMathTranslate](https://github.com/Byaidu/PDFMathTranslate) — PDF 翻译引擎
2. [PyMuPDF](https://pymupdf.readthedocs.io/) — PDF 解析库
3. [FastAPI](https://fastapi.tiangolo.com/) — 后端框架
4. [SM-2 Algorithm](https://en.wikipedia.org/wiki/SuperMemo#Description_of_SM-2_algorithm) — 间隔重复算法

---

💬 **互动时间**：
对本文有任何想法或疑问？欢迎在评论区留言讨论！
如果觉得有帮助，别忘了点个"在看"并分享给需要的朋友～

![扫码_搜索联合传播样式-标准色版](https://img.aws.xin/uPic/扫码_搜索联合传播样式-标准色版.png)
👆 扫码关注，获取更多精彩内容
