# EasyPaper：让英文论文阅读效率翻倍的 AI 工具，一键部署指南

> 一键部署系列 | 项目难度：⭐⭐ | 部署时间：5 分钟

---

## 📖 前言

读英文论文是每个科研人、技术人的日常，但这个过程往往痛苦而低效：

- 专业词汇太多，一边读一边查词典
- 读完就忘，知识留不住
- 论文之间的关联理不清
- 笔记散落各处，无法系统化

如果有一个工具，能帮你**翻译论文**、**简化英文**、**自动高亮重点**、**提取知识图谱**、**生成闪卡复习**，而且**数据完全自主**——那就是今天介绍的 EasyPaper。

**在线体验：** https://easypaper.aws.xin

**测试账号：** neo@test.com / test123456

---

## 🔍 项目介绍

EasyPaper 是一个开源的学术论文辅助阅读工具，支持自部署。核心理念是：**把论文变成带得走的知识**。

上传一篇 PDF 论文，EasyPaper 会帮你完成从「读」到「记」的全流程：

![项目截图](imgs/img-0.png)

**GitHub：** https://github.com/neosun100/EasyPaper

---

## 🎯 六大核心功能

### 1️⃣ 论文翻译（英 → 中）

基于 pdf2zh（PDFMathTranslate）引擎，翻译后**完整保留原始排版**——图表、公式、页眉页脚都不会乱。

![翻译效果](imgs/img-0.png)

这不是简单的文字替换，而是真正理解 PDF 结构后的版面级翻译。

### 2️⃣ 英文简化

如果你更想练英文阅读能力，EasyPaper 支持将学术英语简化为 CEFR A2/B1 级别（约 2000 常用词），降低阅读门槛的同时保留原文含义。

![简化效果](imgs/img-1.png)

### 3️⃣ AI 智能高亮

上传论文后，AI 自动识别三类关键信息，用颜色标注：

| 颜色 | 含义 | 标注内容 |
|------|------|---------|
| 🟡 黄色 | 核心结论 | 主要发现和研究成果 |
| 🔵 蓝色 | 方法创新 | 新颖方法和技术贡献 |
| 🟢 绿色 | 关键数据 | 定量结果、指标、实验数据 |

![AI高亮效果](imgs/img-5.png)

再也不用满篇论文找重点了！

### 4️⃣ 便携知识库

通过 LLM 从论文中提取结构化知识，以 JSON 格式存储：

- **实体提取**：方法、模型、数据集、指标、概念、人物、机构
- **关系推理**：扩展、使用、优于、类似、矛盾等
- **发现归纳**：结果、局限性、贡献，附带证据引用

![知识库](imgs/img-2.png)

![研究发现](imgs/img-3.png)

最重要的是——**你的知识不被锁定**。支持导出为 Obsidian Vault、BibTeX、CSL-JSON、CSV 等多种格式。

### 5️⃣ 知识图谱

跨论文的实体与关系自动构建为**交互式力导向图谱**：

- 按实体类型着色
- 按重要性调整节点大小
- 支持搜索和缩放
- 一眼看清研究脉络

论文读多了，知识图谱的价值就越大。

### 6️⃣ 闪卡复习

内置 SM-2 间隔重复系统，自动从论文中生成闪卡。按 0-5 评分记忆效果，系统自动安排最优复习间隔。

![闪卡复习](imgs/img-4.png)

「艾宾浩斯遗忘曲线」告诉我们，不复习就会忘。EasyPaper 帮你把论文知识真正记住。

---

## 🐳 一键部署

### 环境要求

- Docker + Docker Compose
- 一个 OpenAI 兼容的 LLM API Key（支持 GPT、Claude、Gemini 等）

### 部署步骤

```bash
# 1. 克隆项目
git clone https://github.com/neosun100/EasyPaper.git
cd EasyPaper

# 2. 配置 API Key
cp backend/config/config.example.yaml backend/config/config.yaml
```

编辑 `backend/config/config.yaml`，填入你的 API Key：

```yaml
llm:
  api_key: "YOUR_API_KEY"
  base_url: "https://api.example.com/v1"
  model: "gemini-2.5-flash"
```

```bash
# 3. 一键启动
docker compose up --build -d
```

启动后访问 **http://localhost:9201** 即可使用。

### 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 9201 | Web 界面 |
| 后端 | 9200 | API 服务 |

---

## 📱 使用演示

### 第一步：注册登录

打开浏览器访问部署地址，注册一个账号。

### 第二步：上传论文

点击上传，选择一篇英文 PDF 论文。可以选择：
- **翻译模式**：英文 → 中文
- **简化模式**：学术英语 → 简单英语
- **AI 高亮**：自动标注重点（可与上述模式叠加）

### 第三步：查看结果

处理完成后，下载翻译/简化后的 PDF，重点句子已用颜色标注。

### 第四步：探索知识库

进入知识库页面，查看从论文中提取的：
- 结构化实体与关系
- 研究发现与证据
- 自动生成的闪卡

### 第五步：知识图谱

随着论文数量增加，知识图谱会越来越丰富，帮你建立系统化的学科认知。

---

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | FastAPI, PyMuPDF, pdf2zh, httpx |
| 前端 | React 18, TypeScript, Vite, Tailwind CSS |
| 数据库 | SQLite (SQLModel) |
| AI | 任意 OpenAI 兼容 API |
| 部署 | Docker Compose |

---

## 💡 总结

EasyPaper 解决了英文论文阅读的四大痛点：

1. **读不懂** → 翻译 + 简化，双管齐下
2. **找不到重点** → AI 三色高亮，一目了然
3. **记不住** → 闪卡 + 间隔重复，科学记忆
4. **理不清** → 知识图谱，构建认知网络

而且所有数据都在你自己的服务器上，知识不被任何平台锁定。

**在线体验：** https://easypaper.aws.xin

**GitHub：** https://github.com/neosun100/EasyPaper

**Docker 一键部署：**

```bash
git clone https://github.com/neosun100/EasyPaper.git
cd EasyPaper
cp backend/config/config.example.yaml backend/config/config.yaml
# 编辑 config.yaml 填入 API Key
docker compose up --build -d
```

---

> 本文是「一键部署系列」的一篇。关注我，每期带你用 Docker 部署一个实用 AI 工具。
