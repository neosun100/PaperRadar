[English](README.md) | [简体中文](README_zh.md) | [繁體中文](README_tw.md) | [日本語](README_jp.md)


<h1 align="center">EasyPaper</h1>

<p align="center">
  <strong>把論文變成帶得走的知識。</strong>
</p>

<p align="center">
  <a href="https://github.com/neosun100/EasyPaper/stargazers"><img src="https://img.shields.io/github/stars/neosun100/EasyPaper?style=social" alt="Stars"></a>
  <a href="https://github.com/neosun100/EasyPaper/blob/main/LICENSE"><img src="https://img.shields.io/github/license/neosun100/EasyPaper" alt="License"></a>
  <a href="https://github.com/neosun100/EasyPaper/actions"><img src="https://img.shields.io/github/actions/workflow/status/neosun100/EasyPaper/ci.yml?branch=main&label=CI" alt="CI"></a>
</p>

---

EasyPaper 是一個**自託管**的 Web 應用，幫助你閱讀、理解和記憶英文學術論文中的知識。上傳一篇 PDF，即可獲得保留原始排版的翻譯/簡化版本、AI 自動高亮的關鍵語句，以及可匯出到任何地方的便攜式知識庫。

> **BYOK（自帶金鑰）** — 所有 LLM 憑證僅儲存在瀏覽器的 localStorage 中，伺服器不會保存你的 API 金鑰。

## ✨ 功能特性

### 📖 翻譯 & 簡化

將英文論文翻譯為中文，或簡化為通俗英語（CEFR A2/B1），保留排版、圖片和公式。基於 [pdf2zh](https://github.com/Byaidu/PDFMathTranslate)。

<p align="center">
  <img src="docs/screenshot-reader.png" alt="閱讀器 — 雙欄翻譯視圖" width="90%">
</p>

### 🎨 AI 高亮

自動識別並用顏色標註 PDF 中的關鍵語句：

| 顏色 | 類別 | 高亮內容 |
|------|------|---------|
| 🟡 黃色 | 核心結論 | 主要發現和研究成果 |
| 🔵 藍色 | 方法創新 | 新穎方法和技術貢獻 |
| 🟢 綠色 | 關鍵數據 | 定量結果、指標、實驗數據 |

### 🧠 知識庫

透過 LLM 從論文中提取結構化知識 — 實體、關係、發現和閃卡 — 以可移植的 JSON 格式儲存。

### 🕸️ 知識圖譜

互動式力導向圖，視覺化所有論文中的實體和關係。

### 🃏 閃卡複習

內建間隔重複演算法（SM-2），用於複習自動生成的閃卡。

### 📦 多格式匯出

| 格式 | 用途 |
|------|------|
| EasyPaper JSON | 完整的可移植知識（主要格式） |
| Obsidian Vault | 帶 wikilinks 的 Markdown 筆記 |
| BibTeX | LaTeX 引用管理 |
| CSL-JSON | Zotero / Mendeley 相容 |
| CSV | 試算表分析 |

### 🌙 深色模式

全介面深色模式支援。

---

## 🚀 快速開始

### Docker（推薦）

```bash
git clone https://github.com/neosun100/EasyPaper.git
cd EasyPaper
docker compose up --build
```

開啟 **http://localhost:9201**，在設定中配置 LLM API 金鑰，即可開始上傳論文。

### 本地開發

**前置條件：** Python 3.10+、Node.js 18+、OpenAI 相容的 LLM API 金鑰

**後端：**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**前端：**

```bash
cd frontend
npm install && npm run dev
```

開啟 **http://localhost:5173**。

---

## 🏗️ 技術棧

| 元件 | 技術 |
|------|------|
| 後端 | FastAPI, Python 3.11, pdf2zh, PyMuPDF, httpx |
| 前端 | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| 資料庫 | SQLite via SQLModel |
| AI/LLM | 任何 OpenAI 相容 API（BYOK） |
| 基礎設施 | Docker Compose, nginx, GitHub Actions CI |

---

## 🙏 致謝

本專案 fork 自 [CzsGit/EasyPaper](https://github.com/CzsGit/EasyPaper)。感謝原作者的基礎工作。我們在此基礎上進行了 UI/UX 改進、深色模式修復、文件增強及其他優化。

---

## 📄 授權條款

MIT
