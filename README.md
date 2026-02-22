[English](README.md) | [简体中文](README_zh.md) | [繁體中文](README_tw.md) | [日本語](README_jp.md)

<p align="center">
  <img src="docs/banner.png" alt="EasyPaper Banner" width="100%">
</p>

<h1 align="center">EasyPaper</h1>

<p align="center">
  <strong>Turn academic papers into knowledge you keep.</strong>
</p>

<p align="center">
  <a href="https://github.com/neosun100/EasyPaper/stargazers"><img src="https://img.shields.io/github/stars/neosun100/EasyPaper?style=social" alt="Stars"></a>
  <a href="https://github.com/neosun100/EasyPaper/blob/main/LICENSE"><img src="https://img.shields.io/github/license/neosun100/EasyPaper" alt="License"></a>
  <a href="https://github.com/neosun100/EasyPaper/actions"><img src="https://img.shields.io/github/actions/workflow/status/neosun100/EasyPaper/ci.yml?branch=main&label=CI" alt="CI"></a>
</p>

---

EasyPaper is a **self-hosted** web app that helps you read, understand, and retain knowledge from English academic papers. Upload a PDF — get back a translated or simplified version with layout intact, AI-highlighted key sentences, and a portable knowledge base you can export anywhere.

> **BYOK (Bring Your Own Key)** — all LLM credentials stay in your browser's localStorage. The server never stores your API keys.

## ✨ Features

### 📖 Translate & Simplify

Translate English papers to Chinese or simplify to plain English (CEFR A2/B1), preserving layout, images, and formulas. Powered by [pdf2zh](https://github.com/Byaidu/PDFMathTranslate).

<p align="center">
  <img src="docs/screenshot-reader.png" alt="Reader — dual-pane translated view" width="90%">
</p>

### 🎨 AI Highlighting

Automatically identifies and color-codes key sentences in the processed PDF:

| Color | Category | What It Highlights |
|-------|----------|-------------------|
| 🟡 Yellow | Core Conclusions | Main findings and research outcomes |
| 🔵 Blue | Method Innovations | Novel approaches and technical contributions |
| 🟢 Green | Key Data | Quantitative results, metrics, experimental data |

### 🧠 Knowledge Base

Extract structured knowledge from papers via LLM — entities, relationships, findings, and flashcards — stored as portable JSON.

<p align="center">
  <img src="docs/screenshot-knowledge-base-data.png" alt="Knowledge Base" width="90%">
</p>

<p align="center">
  <img src="docs/screenshot-paper-detail.png" alt="Paper Detail — entities, findings, flashcards" width="90%">
</p>

### 🕸️ Knowledge Graph

Interactive force-directed graph visualization of entities and relationships across all your papers.

<p align="center">
  <img src="docs/screenshot-knowledge-graph-data.png" alt="Knowledge Graph" width="90%">
</p>

### 🃏 Flashcard Review

Built-in spaced repetition (SM-2 algorithm) for reviewing auto-generated flashcards.

<p align="center">
  <img src="docs/screenshot-flashcard-review-data.png" alt="Flashcard Review" width="90%">
</p>

### 📦 Multi-Format Export

| Format | Use Case |
|--------|----------|
| EasyPaper JSON | Complete portable knowledge (primary format) |
| Obsidian Vault | Markdown notes with wikilinks |
| BibTeX | LaTeX citation management |
| CSL-JSON | Zotero / Mendeley compatible |
| CSV | Spreadsheet analysis |

### 🌙 Dark Mode

Full dark mode support across the entire UI.

<p align="center">
  <img src="docs/screenshot-dashboard-data.png" alt="Dashboard" width="90%">
</p>

---

## 🚀 Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/neosun100/EasyPaper.git
cd EasyPaper
docker compose up --build
```

Open **http://localhost:9201**, configure your LLM API key in Settings, and start uploading papers.

<p align="center">
  <img src="docs/screenshot-llm-settings.png" alt="LLM Settings" width="50%">
</p>

### Local Development

**Prerequisites:** Python 3.10+, Node.js 18+, an OpenAI-compatible LLM API key

**Backend:**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install && npm run dev
```

Open **http://localhost:5173**.

---

## 🏗️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI, Python 3.11, pdf2zh, PyMuPDF, httpx |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Database | SQLite via SQLModel |
| AI/LLM | Any OpenAI-compatible API (BYOK) |
| Infra | Docker Compose, nginx, GitHub Actions CI |

---

## 📡 API Reference

| Endpoint | Description |
|----------|-------------|
| `POST /api/upload` | Upload PDF (translate / simplify, optional highlight) |
| `GET /api/status/{id}` | Processing status & progress |
| `GET /api/result/{id}/pdf` | Download processed PDF |
| `POST /api/knowledge/extract/{id}` | Trigger knowledge extraction |
| `GET /api/knowledge/papers` | List knowledge base papers |
| `GET /api/knowledge/papers/{id}` | Paper detail (entities, findings, flashcards) |
| `GET /api/knowledge/graph` | Knowledge graph data |
| `GET /api/knowledge/flashcards/due` | Due flashcards for review |
| `POST /api/knowledge/flashcards/{id}/review` | Submit review (quality 0-5) |
| `GET /api/knowledge/export/{format}` | Export (json, bibtex, csl-json, obsidian, csv) |

All LLM-dependent endpoints require headers: `X-LLM-API-Key`, `X-LLM-Base-URL`, `X-LLM-Model`.

---

## 🛠️ Development

```bash
# Backend lint & test
cd backend && ruff check app/ && pytest

# Frontend lint & type-check
cd frontend && npm run lint && npm run type-check
```

---

## 📄 License

MIT
