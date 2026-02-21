[English](README.md) | [简体中文](README_zh.md) | [繁體中文](README_tw.md) | [日本語](README_jp.md)

# EasyPaper

**論文を、持ち歩ける知識に変える。**

🌐 **ライブデモ：** [https://easypaper.aws.xin](https://easypaper.aws.xin)（テストアカウント：`neo@test.com` / `test123456`）

### 🐳 Docker クイックスタート

```bash
git clone https://github.com/neosun100/EasyPaper.git
cd EasyPaper
cp backend/config/config.example.yaml backend/config/config.yaml
# config.yaml を編集 — API キーを入力し、モデルを選択
docker compose up --build
```

ブラウザで http://localhost:9201 を開くだけ。以上！

---

EasyPaper は、英語の学術論文を読み、理解し、知識として定着させるためのセルフホスト型ウェブアプリです。PDF をアップロードするだけで、レイアウトを維持した翻訳版や簡略版、AI によるキーセンテンスのハイライト、そしてどこにでもエクスポート可能なポータブル知識ベースが手に入ります。

---

## 主な機能

### 1. 翻訳 & 簡略化

- **英語 → 中国語** レイアウト、画像、数式を保持した翻訳（[pdf2zh](https://github.com/Byaidu/PDFMathTranslate) ベース）
- **英語 → やさしい英語** 語彙の簡略化（CEFR A2/B1 レベル、約 2000 基本語彙）
- PDF 入力 → PDF 出力 — 図表、数式、書式はそのまま

### 2. AI ハイライト

PDF 内のキーセンテンスを自動識別し、カラーコードで強調表示：

| 色 | カテゴリ | ハイライト対象 |
|----|---------|--------------|
| 黄色 | 中核的結論 | 主要な発見と研究成果 |
| 青色 | 手法の革新 | 新しいアプローチと技術的貢献 |
| 緑色 | キーデータ | 定量的結果、指標、実験データ |

![AI ハイライト](imgs/img-5.png)

### 3. ナレッジベース（ポータブル）

LLM を通じて論文から構造化知識を抽出 — ポータブル JSON 形式で保存、アプリに依存しません：

- **エンティティ**：手法、モデル、データセット、指標、概念、タスク、人物、組織
- **関係**：拡張、使用、評価対象、上回る、類似、矛盾、一部、要件
- **知見**：結果、限界、貢献（エビデンス参照付き）
- **フラッシュカード**：自動生成の学習カード、SM-2 間隔反復スケジューリング対応

![ナレッジベース — 論文詳細](imgs/img-2.png)

![ナレッジベース — 研究知見](imgs/img-3.png)

### 4. ナレッジグラフ

すべての論文のエンティティと関係をインタラクティブな力指向グラフで可視化。エンティティタイプ別に色分け、重要度に応じたサイズ調整、検索・ズーム機能付き。

### 5. マルチフォーマットエクスポート

あなたの知識は、あなたのもの。いつでも持ち出せます：

| フォーマット | 拡張子 | 用途 |
|------------|--------|------|
| EasyPaper JSON | `.epaper.json` | 完全なポータブル知識（メインフォーマット） |
| Obsidian Vault | `.zip` | ウィキリンク付き Markdown ノート |
| BibTeX | `.bib` | LaTeX 引用管理 |
| CSL-JSON | `.json` | Zotero / Mendeley 互換 |
| CSV | `.zip` | スプレッドシート分析（エンティティ + 関係） |

### 6. フラッシュカード復習

内蔵の間隔反復システム（SM-2 アルゴリズム）で、自動生成されたフラッシュカードを復習。0〜5 で記憶度を評価すると、最適な復習間隔を自動スケジューリング。

![フラッシュカード復習](imgs/img-4.png)

---

## スクリーンショット

### 中国語に翻訳
![中国語に翻訳](imgs/img-0.png)

### 英語を簡略化
![英語を簡略化](imgs/img-1.png)

### レイアウト保持技術
![レイアウト分析](imgs/test.png)

---

## クイックスタート

### オプション 1：Docker（推奨）

```bash
cp backend/config/config.example.yaml backend/config/config.yaml
# config.yaml を編集 — API キーを入力し、モデルを選択

docker compose up --build
```

ブラウザで http://localhost を開きます。

### オプション 2：ローカル開発

**前提条件：** Python 3.10+、Node.js 18+、OpenAI 互換 LLM API キー

**バックエンド：**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp config/config.example.yaml config/config.yaml
# config.yaml を編集 — API キーを入力

uvicorn app.main:app --reload
```

**フロントエンド：**

```bash
cd frontend
npm install
npm run dev
```

ブラウザで http://localhost:5173 を開きます。

---

## 設定

`backend/config/config.yaml` を編集：

```yaml
llm:
  api_key: "YOUR_API_KEY"             # 必須 — 任意の OpenAI 互換 API
  base_url: "https://api.example.com/v1"
  model: "gemini-2.5-flash"           # 翻訳/簡略化/知識抽出に使用するモデル
  judge_model: "gemini-2.5-flash"

processing:
  max_pages: 100
  max_upload_mb: 50
  max_concurrent: 3                   # 最大同時処理タスク数

storage:
  cleanup_minutes: 30                 # 一時ファイルの有効期限（分）
  temp_dir: "./backend/tmp"

database:
  url: "sqlite:///./data/app.db"

security:
  secret_key: "CHANGE_THIS"           # JWT 署名キー — 本番環境では必ず変更
  cors_origins:
    - "http://localhost:5173"
```

---

## 技術スタック

| コンポーネント | 技術 |
|--------------|------|
| バックエンド | FastAPI, PyMuPDF, pdf2zh (PDFMathTranslate), httpx |
| フロントエンド | React 18, TypeScript, Vite, Tailwind CSS, Radix UI |
| データベース | SQLite (SQLModel) |
| 認証 | JWT (python-jose), bcrypt, OAuth2 bearer |
| AI/LLM | 任意の OpenAI 互換 API（設定可能） |
| DevOps | Docker Compose, GitHub Actions, ruff, ESLint |

---

## API 概要

| エンドポイント | 説明 |
|--------------|------|
| `POST /api/upload` | PDF アップロード（翻訳/簡略化、オプションでハイライト） |
| `GET /api/status/{id}` | 処理ステータスと進捗 |
| `GET /api/result/{id}/pdf` | 処理済み PDF のダウンロード |
| `POST /api/knowledge/extract/{id}` | 知識抽出のトリガー |
| `GET /api/knowledge/papers` | ナレッジベースの論文一覧 |
| `GET /api/knowledge/graph` | ナレッジグラフ（エンティティ + 関係） |
| `GET /api/knowledge/flashcards/due` | 復習期限のフラッシュカード |
| `POST /api/knowledge/flashcards/{id}/review` | 復習結果の送信 |
| `GET /api/knowledge/export/json` | ナレッジベース全体のエクスポート |
| `GET /api/knowledge/export/obsidian` | Obsidian Vault としてエクスポート |
| `GET /api/knowledge/export/bibtex` | BibTeX としてエクスポート |

---

## 開発

```bash
# バックエンド
cd backend
ruff check app/
pytest

# フロントエンド
cd frontend
npm run lint
npm run type-check
npm test
```

---

## ライセンス

MIT
