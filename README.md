[English](README.md) | [简体中文](README_zh.md)


<h1 align="center">🛰️ PaperRadar</h1>

<p align="center">
  <strong>Discover, understand, and connect cutting-edge research — automatically.</strong>
</p>

<p align="center">
  <a href="https://github.com/neosun100/PaperRadar/stargazers"><img src="https://img.shields.io/github/stars/neosun100/PaperRadar?style=social" alt="Stars"></a>
  <a href="https://github.com/neosun100/PaperRadar/blob/main/LICENSE"><img src="https://img.shields.io/github/license/neosun100/PaperRadar" alt="License"></a>
</p>

---

PaperRadar is a **self-hosted** AI-powered research platform that automatically discovers, translates, analyzes, and connects academic papers. It features a built-in radar engine that scans arXiv for the latest papers in your field, processes them with LLM, and pushes notifications to your phone.

> **BYOK (Bring Your Own Key)** — all LLM credentials stay in your browser's localStorage. Processed results are stored on the cloud and shared with all users.

## ✨ Features

### 🛰️ Paper Radar Engine
Automatically scans arXiv every hour for the latest papers in your configured categories (cs.CL, cs.AI, cs.LG). Uses LLM as an intelligent agent to score relevance, downloads high-quality papers, and processes them through the full pipeline.

### 💬 Paper Chat
Chat directly with any paper in your knowledge base. Ask questions, compare methods, or explore findings — powered by the paper's full text and extracted knowledge.

### 📖 Translate & Simplify
Translate English papers to Chinese or simplify to plain English (CEFR A2/B1), preserving layout, images, and formulas. Powered by [pdf2zh](https://github.com/Byaidu/PDFMathTranslate).

### 🎨 AI Highlighting
Automatically identifies and color-codes key sentences:
- 🟡 Yellow — Core Conclusions
- 🔵 Blue — Method Innovations
- 🟢 Green — Key Data

### 🔬 Research Insights
AI-powered cross-paper analysis across your entire knowledge base:
- **Field Overview** — Auto-generated literature review
- **Method Comparison** — Side-by-side comparison matrix
- **Research Timeline** — Chronological evolution of techniques
- **Research Gaps** — Unresolved problems and future directions
- **Paper Connections** — How papers relate to each other

### 🧠 Knowledge Base
Extract structured knowledge from papers — entities, relationships, findings, and flashcards — stored as portable JSON. All content is bilingual (English + Chinese).

### 🕸️ Knowledge Graph
Interactive force-directed graph visualization of entities and relationships across all papers.

### 📦 Multi-Format Export
| Format | Use Case |
|--------|----------|
| PaperRadar JSON | Complete portable knowledge |
| Obsidian Vault | Markdown notes with wikilinks |
| BibTeX | LaTeX citation management |
| CSL-JSON | Zotero / Mendeley compatible |
| CSV | Spreadsheet analysis |

### 🔔 Smart Notifications
Get notified when the radar discovers and processes new papers:
- **Bark** — iOS push notifications
- **Lark** — Interactive card 2.0 messages

### 🌍 Multilingual UI
Full English and Chinese interface with one-click language switching.

### 🌙 Dark Mode
Full dark mode support across the entire UI.

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

### With Custom Config (for Radar & Notifications)

```bash
# Create your config file
cp config.example.yaml config.yaml
# Edit config.yaml with your settings

docker run -d --name paperradar \
  -p 9201:80 \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  -v paperradar-data:/app/data \
  -v paperradar-tmp:/app/tmp \
  neosun/paperradar:latest
```

### API Token Access

```bash
# Use the API token for programmatic access (uses server-side LLM config)
curl -X POST http://localhost:9201/api/upload \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -F "file=@paper.pdf" -F "mode=translate"
```

---

## 🏗️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI, Python 3.11, pdf2zh, PyMuPDF, httpx |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, react-i18next |
| Database | SQLite via SQLModel |
| AI/LLM | Any OpenAI-compatible API (BYOK) |
| Radar | arXiv API, LLM-based relevance scoring |
| Notifications | Bark (iOS), Lark (Card 2.0) |
| Infra | Docker (all-in-one), supervisord, nginx |

---

## 📡 API Reference

| Endpoint | Description |
|----------|-------------|
| `POST /api/upload` | Upload PDF (translate / simplify, optional highlight) |
| `GET /api/status/{id}` | Processing status & progress |
| `GET /api/queue` | Queue status (processing/queued counts) |
| `POST /api/knowledge/extract/{id}` | Trigger knowledge extraction |
| `GET /api/knowledge/papers` | List knowledge base papers |
| `GET /api/knowledge/papers/{id}` | Paper detail with chat context |
| `POST /api/knowledge/papers/{id}/chat` | Chat with a paper |
| `GET /api/knowledge/graph` | Knowledge graph data |
| `POST /api/knowledge/insights/generate` | Generate cross-paper insights |
| `GET /api/knowledge/insights` | Get latest insights |
| `GET /api/radar/status` | Radar engine status |
| `POST /api/radar/scan` | Trigger manual radar scan |
| `GET /api/knowledge/export/{format}` | Export (json, bibtex, csl-json, obsidian, csv) |

All LLM-dependent endpoints accept either `Authorization: Bearer <token>` or headers: `X-LLM-API-Key`, `X-LLM-Base-URL`, `X-LLM-Model`.

---

## 🙏 Acknowledgments

This project evolved from [EasyPaper](https://github.com/neosun100/EasyPaper), which was forked from [CzsGit/EasyPaper](https://github.com/CzsGit/EasyPaper). We've rebuilt it into a comprehensive research platform with automatic paper discovery, cross-paper analysis, bilingual support, and smart notifications.

---

## 📄 License

MIT
