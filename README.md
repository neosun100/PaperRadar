[English](README.md) | [简体中文](README_zh.md)


<h1 align="center">🛰️ PaperRadar</h1>

<p align="center">
  <strong>Discover, understand, and connect cutting-edge research — automatically.</strong>
</p>

<p align="center">
  <a href="https://github.com/neosun100/PaperRadar/stargazers"><img src="https://img.shields.io/github/stars/neosun100/PaperRadar?style=social" alt="Stars"></a>
  <a href="https://hub.docker.com/r/neosun/paperradar"><img src="https://img.shields.io/docker/pulls/neosun/paperradar" alt="Docker Pulls"></a>
  <a href="https://github.com/neosun100/PaperRadar/blob/main/LICENSE"><img src="https://img.shields.io/github/license/neosun100/PaperRadar" alt="License"></a>
  <img src="https://img.shields.io/badge/version-3.0.0-blue" alt="Version">
</p>

---

PaperRadar is a **self-hosted** AI-powered research platform that automatically discovers, translates, analyzes, and connects academic papers. It features a built-in radar engine that scans arXiv for the latest papers in your field, processes them with LLM, and pushes notifications to your phone.

> **BYOK (Bring Your Own Key)** — all LLM credentials stay in your browser's localStorage. Processed results are stored on the cloud and shared with all users.

## ✨ Features

### 🛰️ Paper Radar Engine
Automatically scans arXiv, Semantic Scholar, and HuggingFace Daily Papers every hour. Uses LLM-based smart scoring with community upvotes to find the most relevant papers, then auto-downloads and processes them through the full pipeline.

### 💬 Paper Chat
Chat directly with any paper or across your entire knowledge base. RAG-enhanced with ChromaDB vector search for accurate, context-aware answers.

### 📖 Multi-Language Translation
- **English → Chinese** — Translate papers preserving layout, images, and formulas
- **Chinese → English** — Translate Chinese papers to English
- **Simplify** — Rewrite in plain English (CEFR A2/B1)
- Powered by [pdf2zh](https://github.com/Byaidu/PDFMathTranslate)

### 🎨 AI Highlighting
Automatically identifies and color-codes key sentences:
- 🟡 Yellow — Core Conclusions
- 🔵 Blue — Method Innovations
- 🟢 Green — Key Data

### ✏️ Annotations & AI Explain
- Annotate papers with color-coded notes, highlights, and questions
- **AI Explain** — paste any sentence to get a simplified explanation

### 🔬 Research Insights & Writing
- **Field Overview** — Auto-generated literature review
- **Method Comparison** — Side-by-side comparison matrix
- **Data Extraction Tables** — Elicit-style structured extraction across papers
- **Writing Assistant** — Generate "Related Work" sections (IEEE/ACM/APA)
- **Research Gaps** — Unresolved problems and future directions

### 📊 Citation Intelligence
- **Citation Network** — Connected Papers-style force-directed graph
- **Smart Citations** — scite.ai-style citation contexts (supporting/contrasting/mentioning)
- **OpenAlex Enrichment** — One-click metadata from 250M+ works

### 🎧 Paper Audio Summary
NotebookLM-style podcast generation — two AI hosts discuss key findings in conversational format.

### 🧠 Knowledge Base
- Bilingual knowledge extraction (English + Chinese)
- Paper collections (ResearchRabbit-style organization)
- Knowledge graph visualization
- Flashcard review (SM-2 spaced repetition)
- Personalized paper prioritization

### 📦 Multi-Format Export
| Format | Use Case |
|--------|----------|
| PaperRadar JSON | Complete portable knowledge |
| Obsidian Vault | Markdown notes with wikilinks |
| BibTeX | LaTeX citation management |
| CSL-JSON | Zotero / Mendeley compatible |
| CSV | Spreadsheet analysis |

### 🔔 Smart Notifications
- **Bark** — iOS push notifications
- **Lark** — Interactive card 2.0 messages
- **Webhook** — Slack, Discord, n8n, or any URL

### 🤖 MCP Server (Claude/Cursor Integration)
12 tools for AI assistants: search, chat, trending, radar, collections, writing, digest, and more.

### 🌍 Multilingual UI & Dark Mode
Full English and Chinese interface with one-click switching and dark mode support.

---

## 🚀 Quick Start

### Docker (Recommended)

```bash
docker run -d --name paperradar \
  -p 9201:80 \
  -v paperradar-data:/app/data \
  -v paperradar-tmp:/app/tmp \
  neosun/paperradar:latest
```

Open **http://localhost:9201**, configure your LLM API key in Settings, and start uploading papers.

### Docker Compose

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
docker compose up -d
```

### With Custom Config (for Radar & Notifications)

```bash
docker run -d --name paperradar \
  -p 9201:80 \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  -v paperradar-data:/app/data \
  -v paperradar-tmp:/app/tmp \
  neosun/paperradar:latest
```

### MCP Server (Claude/Cursor)

```json
{
  "mcpServers": {
    "paperradar": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/path/to/backend",
      "env": {"PAPERRADAR_API": "http://localhost:9200"}
    }
  }
}
```

Available tools: `search_papers`, `list_papers`, `get_paper`, `chat_with_papers`, `get_trending`, `radar_status`, `process_arxiv_paper`, `generate_literature_review`, `list_collections`, `generate_related_work`, `get_digest`, `scholar_search`, `generate_quiz`, `generate_briefing`

---

## 🏗️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI, Python 3.11, pdf2zh, PyMuPDF, httpx |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Database | SQLite via SQLModel |
| Vector DB | ChromaDB (embedded) |
| AI/LLM | Any OpenAI-compatible API (BYOK) |
| Data Sources | arXiv, Semantic Scholar, HuggingFace, OpenAlex |
| Notifications | Bark, Lark, Generic Webhook |
| Infra | Docker (all-in-one), supervisord, nginx |

---

## 📡 API Reference

| Endpoint | Description |
|----------|-------------|
| `POST /api/upload` | Upload PDF (translate / simplify / zh2en) |
| `GET /api/status/{id}` | Processing status & progress |
| `POST /api/knowledge/extract/{id}` | Trigger knowledge extraction |
| `GET /api/knowledge/papers` | List knowledge base papers |
| `POST /api/knowledge/papers/{id}/chat` | Chat with a paper |
| `POST /api/knowledge/chat` | Cross-paper chat (RAG) |
| `POST /api/knowledge/compare` | Compare 2-5 papers |
| `POST /api/knowledge/extract-table` | Elicit-style data extraction |
| `POST /api/knowledge/writing/related-work` | Generate Related Work section |
| `POST /api/knowledge/explain` | AI inline explanation |
| `POST /api/knowledge/prioritize` | Personalized paper ranking |
| `GET /api/knowledge/digest` | Activity digest |
| `POST /api/knowledge/papers/{id}/enrich` | OpenAlex enrichment |
| `GET /api/knowledge/collections` | List paper collections |
| `GET /api/knowledge/graph` | Knowledge graph data |
| `GET /api/radar/status` | Radar engine status |
| `POST /api/radar/scan` | Trigger manual radar scan |
| `GET /api/radar/trending` | Trending papers |
| `GET /api/radar/recommendations` | Personalized recommendations |
| `GET /api/knowledge/export/{format}` | Export (json, bibtex, obsidian, csv) |
| `GET /api/knowledge/scholar-search` | Search Semantic Scholar (200M+ papers) |
| `POST /api/knowledge/papers/{id}/quiz` | Generate quiz questions |
| `POST /api/knowledge/papers/{id}/briefing` | Generate briefing document |
| `POST /api/knowledge/papers/{id}/share` | Generate share link |
| `GET /share/{token}` | Public shared paper view |
| `GET /api/knowledge/papers/{id}/similar` | Find similar papers (vector) |
| `POST /api/knowledge/papers/{id}/generate-tldr` | Generate TLDR summary |

All LLM-dependent endpoints accept either `Authorization: Bearer <token>` or headers: `X-LLM-API-Key`, `X-LLM-Base-URL`, `X-LLM-Model`.

---

## 🙏 Acknowledgments

This project evolved from [EasyPaper](https://github.com/neosun100/EasyPaper), which was forked from [CzsGit/EasyPaper](https://github.com/CzsGit/EasyPaper). We've rebuilt it into a comprehensive research platform with 60+ features.

---

## 📄 License

MIT
