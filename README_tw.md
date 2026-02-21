[English](README.md) | [简体中文](README_zh.md) | [繁體中文](README_tw.md) | [日本語](README_jp.md)

# EasyPaper

**把論文變成帶得走的知識。**

🌐 **線上演示：** [https://easypaper.aws.xin](https://easypaper.aws.xin)（測試帳號：`neo@test.com` / `test123456`）

### 🐳 Docker 一鍵部署

```bash
git clone https://github.com/neosun100/EasyPaper.git
cd EasyPaper
cp backend/config/config.example.yaml backend/config/config.yaml
# 編輯 config.yaml — 填入你的 API Key，選擇模型
docker compose up --build
```

瀏覽器開啟 http://localhost:9201 即可使用。就這麼簡單！

---

EasyPaper 是一個可自行部署的 Web 應用，幫助你閱讀、理解並留住英文學術論文中的知識。上傳一個 PDF — 取得翻譯或簡化版本（排版完整保留）、AI 重點標示，以及可匯出到任何平台的便攜知識庫。

---

## 核心功能

### 1. 翻譯 & 簡化

- **英文 → 中文** 翻譯，保留排版、圖片和公式（基於 [pdf2zh](https://github.com/Byaidu/PDFMathTranslate)）
- **英文 → 簡單英文** 詞彙簡化（CEFR A2/B1 級別，約 2000 常用詞）
- PDF 輸入，PDF 輸出 — 圖表、公式、格式完整保留

### 2. AI 重點標示

自動識別並用顏色標註 PDF 中的關鍵句子：

| 顏色 | 分類 | 標註內容 |
|------|------|---------|
| 黃色 | 核心結論 | 主要發現和研究成果 |
| 藍色 | 方法創新 | 新穎方法和技術貢獻 |
| 綠色 | 關鍵數據 | 定量結果、指標、實驗數據 |

![AI 重點標示](imgs/img-5.png)

### 3. 知識庫（可遷移）

透過 LLM 從論文中提取結構化知識 — 以便攜 JSON 格式儲存，不與本應用綁定：

- **實體**：方法、模型、資料集、指標、概念、任務、人物、機構
- **關係**：擴展、使用、評估於、優於、類似、矛盾、屬於、依賴
- **發現**：結果、局限性、貢獻，附帶證據引用
- **閃卡**：自動生成的學習卡片，支援 SM-2 間隔重複排程

![知識庫 — 論文詳情](imgs/img-2.png)

![知識庫 — 研究發現](imgs/img-3.png)

### 4. 知識圖譜

互動式力導向圖譜，視覺化所有論文中的實體與關係。按實體類型著色，按重要性調整大小，支援搜尋和縮放。

### 5. 多格式匯出

知識是你的，隨時帶走：

| 格式 | 副檔名 | 用途 |
|------|--------|------|
| EasyPaper JSON | `.epaper.json` | 完整便攜知識（主格式） |
| Obsidian Vault | `.zip` | 含雙向連結的 Markdown 筆記 |
| BibTeX | `.bib` | LaTeX 引用管理 |
| CSL-JSON | `.json` | Zotero / Mendeley 相容 |
| CSV | `.zip` | 試算表分析（實體 + 關係） |

### 6. 閃卡複習

內建間隔重複系統（SM-2 演算法），複習自動生成的閃卡。按 0-5 評分你的記憶效果，系統自動安排最佳複習間隔。

![閃卡複習](imgs/img-4.png)

---

## 效果展示

### 翻譯為中文
![翻譯為中文](imgs/img-0.png)

### 簡化英文
![簡化英文](imgs/img-1.png)

### 保留排版技術
![排版分析](imgs/test.png)

---

## 快速開始

### 方式一：Docker 部署（推薦）

```bash
cp backend/config/config.example.yaml backend/config/config.yaml
# 編輯 config.yaml — 填入你的 API Key，選擇模型

docker compose up --build
```

瀏覽器開啟 http://localhost 即可使用。

### 方式二：本地開發

**環境需求：** Python 3.10+、Node.js 18+、一個 OpenAI 相容的 LLM API Key

**啟動後端：**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp config/config.example.yaml config/config.yaml
# 編輯 config.yaml — 填入你的 API Key

uvicorn app.main:app --reload
```

**啟動前端：**

```bash
cd frontend
npm install
npm run dev
```

瀏覽器開啟 http://localhost:5173 即可使用。

---

## 設定說明

編輯 `backend/config/config.yaml`：

```yaml
llm:
  api_key: "YOUR_API_KEY"             # 必填 — 任意 OpenAI 相容 API
  base_url: "https://api.example.com/v1"
  model: "gemini-2.5-flash"           # 翻譯/簡化/知識提取使用的模型
  judge_model: "gemini-2.5-flash"

processing:
  max_pages: 100
  max_upload_mb: 50
  max_concurrent: 3                   # 最大並行處理任務數

storage:
  cleanup_minutes: 30                 # 暫存檔案過期時間（分鐘）
  temp_dir: "./backend/tmp"

database:
  url: "sqlite:///./data/app.db"

security:
  secret_key: "CHANGE_THIS"           # JWT 簽名金鑰 — 正式環境必須修改
  cors_origins:
    - "http://localhost:5173"
```

---

## 技術棧

| 元件 | 技術 |
|------|------|
| 後端 | FastAPI, PyMuPDF, pdf2zh (PDFMathTranslate), httpx |
| 前端 | React 18, TypeScript, Vite, Tailwind CSS, Radix UI |
| 資料庫 | SQLite（SQLModel） |
| 認證 | JWT (python-jose), bcrypt, OAuth2 bearer |
| AI/LLM | 任意 OpenAI 相容 API（可設定） |
| 工程化 | Docker Compose, GitHub Actions, ruff, ESLint |

---

## API 概覽

| 端點 | 說明 |
|------|------|
| `POST /api/upload` | 上傳 PDF（翻譯/簡化，可選標示） |
| `GET /api/status/{id}` | 處理狀態與進度 |
| `GET /api/result/{id}/pdf` | 下載處理後的 PDF |
| `POST /api/knowledge/extract/{id}` | 觸發知識提取 |
| `GET /api/knowledge/papers` | 知識庫論文列表 |
| `GET /api/knowledge/graph` | 知識圖譜（實體 + 關係） |
| `GET /api/knowledge/flashcards/due` | 到期閃卡 |
| `POST /api/knowledge/flashcards/{id}/review` | 提交複習結果 |
| `GET /api/knowledge/export/json` | 匯出完整知識庫 |
| `GET /api/knowledge/export/obsidian` | 匯出為 Obsidian 筆記庫 |
| `GET /api/knowledge/export/bibtex` | 匯出為 BibTeX |

---

## 開發指南

```bash
# 後端
cd backend
ruff check app/
pytest

# 前端
cd frontend
npm run lint
npm run type-check
npm test
```

---

## 開源授權

MIT
