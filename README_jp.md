[English](README.md) | [简体中文](README_zh.md) | [繁體中文](README_tw.md) | [日本語](README_jp.md)


<h1 align="center">EasyPaper</h1>

<p align="center">
  <strong>論文を、持ち歩ける知識に変える。</strong>
</p>

<p align="center">
  <a href="https://github.com/neosun100/EasyPaper/stargazers"><img src="https://img.shields.io/github/stars/neosun100/EasyPaper?style=social" alt="Stars"></a>
  <a href="https://github.com/neosun100/EasyPaper/blob/main/LICENSE"><img src="https://img.shields.io/github/license/neosun100/EasyPaper" alt="License"></a>
  <a href="https://github.com/neosun100/EasyPaper/actions"><img src="https://img.shields.io/github/actions/workflow/status/neosun100/EasyPaper/ci.yml?branch=main&label=CI" alt="CI"></a>
</p>

---

EasyPaper は**セルフホスト型**の Web アプリケーションで、英語の学術論文を読み、理解し、知識を定着させるのに役立ちます。PDF をアップロードするだけで、レイアウトを保持した翻訳・簡略化版、AI による重要文のハイライト、そしてどこにでもエクスポートできるポータブルな知識ベースが得られます。

> **BYOK（Bring Your Own Key）** — すべての LLM 認証情報はブラウザの localStorage にのみ保存されます。サーバーは API キーを保存しません。

## ✨ 機能

### 📖 翻訳 & 簡略化

英語論文を中国語に翻訳、または平易な英語（CEFR A2/B1）に簡略化。レイアウト、画像、数式を保持。[pdf2zh](https://github.com/Byaidu/PDFMathTranslate) を使用。

### 🎨 AI ハイライト

PDF 内の重要文を自動識別し、色分けで表示：

| 色 | カテゴリ | ハイライト内容 |
|----|---------|--------------|
| 🟡 黄色 | 核心的結論 | 主要な発見と研究成果 |
| 🔵 青色 | 手法の革新 | 新しいアプローチと技術的貢献 |
| 🟢 緑色 | 重要データ | 定量的結果、指標、実験データ |

### 🧠 知識ベース

LLM を通じて論文から構造化知識を抽出 — エンティティ、関係、発見、フラッシュカード — ポータブルな JSON 形式で保存。

### 🕸️ 知識グラフ

すべての論文のエンティティと関係をインタラクティブな力指向グラフで可視化。

### 🃏 フラッシュカード復習

自動生成されたフラッシュカードを復習するための間隔反復アルゴリズム（SM-2）を内蔵。

### 📦 マルチフォーマットエクスポート

| フォーマット | 用途 |
|------------|------|
| EasyPaper JSON | 完全なポータブル知識（主要フォーマット） |
| Obsidian Vault | wikilinks 付き Markdown ノート |
| BibTeX | LaTeX 引用管理 |
| CSL-JSON | Zotero / Mendeley 互換 |
| CSV | スプレッドシート分析 |

### 🌙 ダークモード

UI 全体でダークモードをサポート。

---

## 🚀 クイックスタート

### Docker（推奨）

```bash
git clone https://github.com/neosun100/EasyPaper.git
cd EasyPaper
docker compose up --build
```

**http://localhost:9201** を開き、設定で LLM API キーを構成して、論文のアップロードを開始します。

### ローカル開発

**前提条件：** Python 3.10+、Node.js 18+、OpenAI 互換の LLM API キー

**バックエンド：**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**フロントエンド：**

```bash
cd frontend
npm install && npm run dev
```

**http://localhost:5173** を開きます。

---

## 🏗️ 技術スタック

| コンポーネント | 技術 |
|--------------|------|
| バックエンド | FastAPI, Python 3.11, pdf2zh, PyMuPDF, httpx |
| フロントエンド | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| データベース | SQLite via SQLModel |
| AI/LLM | 任意の OpenAI 互換 API（BYOK） |
| インフラ | Docker Compose, nginx, GitHub Actions CI |

---

## 🙏 謝辞

本プロジェクトは [CzsGit/EasyPaper](https://github.com/CzsGit/EasyPaper) からフォークしました。オリジナル作者の基礎的な作業に感謝します。UI/UX の改善、ダークモードの修正、ドキュメントの強化、その他の最適化を行いました。

---

## 📄 ライセンス

MIT
