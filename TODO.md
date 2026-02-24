# PaperRadar — Development Roadmap

## ✅ Completed (v3.6.0) — 70+ Features

### Core Platform
- [x] PDF Upload (drag & drop, URL upload, no size limit)
- [x] PDF Translation (English ↔ Chinese, pdf2zh)
- [x] PDF Simplification (Complex → Plain English)
- [x] AI Highlighting (3-color: conclusions/methods/data)
- [x] Document Reader (split-pane, focus mode, reading progress)
- [x] Task Queue (per-user concurrency, queue status UI)
- [x] Zombie/Stale Task Recovery

### Knowledge Base
- [x] Bilingual Knowledge Extraction (en/zh)
- [x] TLDR Auto-Summary (one-sentence bilingual)
- [x] Paper Chat (single-paper + cross-paper RAG)
- [x] Expert Chat (world-class researcher persona, cited sources)
- [x] Claim Evidence Analysis (supports/contradicts/related)
- [x] Deep Research (auto search → download → synthesize expert report)
- [x] Research Insights (field overview, method comparison, gaps)
- [x] Literature Review Generation
- [x] Paper Comparison (2-5 papers)
- [x] Data Extraction Tables (Elicit-style)
- [x] Research Gaps Analysis
- [x] Paper Quiz (5 multiple-choice questions)
- [x] Paper Briefing Doc (structured Markdown)
- [x] Paper Audio Summary (NotebookLM-style podcast, gpt-4o-mini-tts)
- [x] AI Inline Explanations
- [x] Paper Writing Assistant (Related Work, IEEE/ACM/APA)
- [x] Knowledge Graph (force-directed, bilingual)
- [x] Similarity Map (2D PCA visualization)
- [x] Multi-Format Export (JSON, BibTeX, Obsidian, CSL-JSON, CSV)
- [x] Flashcard Review (SM-2 spaced repetition)
- [x] Paper Collections (ResearchRabbit-style)
- [x] Paper Annotations & Notes
- [x] Paper Sharing (public link, no auth needed)
- [x] Similar Papers (vector-based discovery)
- [x] Semantic Search (ChromaDB + Cohere Embed v4)
- [x] Cmd+K Global Search (with highlight)
- [x] KB Sorting (date/year/title)
- [x] Batch Delete
- [x] Batch Import (arXiv IDs, DOIs, BibTeX)
- [x] Zotero Import

### Radar Engine
- [x] 4-Source Radar (arXiv + Semantic Scholar + HuggingFace + alphaXiv)
- [x] Smart Hybrid Scoring (upvotes + citations + keywords)
- [x] Trending Papers (7d/14d/30d)
- [x] Smart Recommendations (S2 + vector fallback)
- [x] Auto-Download & Process (top papers per scan)
- [x] Scholar Search (200M+ papers from Dashboard)

### Notifications
- [x] Bark iOS Push
- [x] Lark Card 2.0
- [x] Webhook (Slack Block Kit, Discord Embed, generic JSON)
- [x] Daily Digest (scheduled)

### Infrastructure
- [x] All-in-one Docker (nginx + uvicorn + supervisord)
- [x] MCP Server (16 tools for Claude/Cursor)
- [x] CI/CD Pipeline (GitHub Actions)
- [x] Backup & Restore
- [x] SSE Progress Streaming
- [x] API Token Auth + BYOK
- [x] i18n (English/Chinese, 326 keys)
- [x] Dark Mode + Mobile Responsive
- [x] Reading Progress (save/restore)
- [x] Onboarding Guide
- [x] Error Boundary

---

## 🔲 Phase 7: From Good to Great

### 7A: UX Polish (High Priority)

- [ ] **Paper Tags/Labels**
  - User-defined tags (e.g. "must-read", "methodology", "baseline")
  - Filter KB by tags, combine with collections
  - Tag suggestions based on paper content

- [ ] **Keyboard Shortcuts Help Panel**
  - Press ? to open shortcuts overlay
  - Cmd+K search, Cmd+N upload, arrow navigation, Esc close

- [ ] **PDF Thumbnail Preview**
  - Generate first-page thumbnail on upload
  - Display on paper cards in KB and Dashboard

- [ ] **Deep Research History (Server-side)**
  - Save research reports to DB
  - Browse past research topics
  - Re-open and continue expert chat

- [ ] **Custom Extraction Columns**
  - User defines what to extract (e.g. "sample size", "GPU hours")
  - LLM extracts custom fields from each paper
  - Export as CSV with custom columns

### 7B: Intelligence (Medium Priority)

- [ ] **Mind Map Visualization**
  - Interactive concept map from paper entities
  - Drag, zoom, click to explore
  - Export as image

- [ ] **AI Paper Writer**
  - Generate full paper sections from KB references
  - Introduction, Methodology, Results, Discussion
  - Proper citation formatting

- [ ] **Systematic Review Pipeline**
  - Define inclusion/exclusion criteria
  - Auto-screen papers from search results
  - PRISMA flow diagram

- [ ] **Paper Recommendation Feed**
  - Daily personalized feed based on reading history
  - "Papers you might like" on Dashboard
  - Learn from user interactions

### 7C: Platform (Lower Priority)

- [ ] **Multi-user Support**
  - Separate KB per user/API key
  - Shared collections between users

- [ ] **Slide Deck Generation**
  - Generate presentation slides from paper knowledge
  - Export as HTML or PDF

- [ ] **Plugin System**
  - Custom data sources (PubMed, bioRxiv)
  - Custom notification channels
  - Custom extraction pipelines

---

## 💡 Design Inspirations

1. **NotebookLM** — Audio/Video Overviews, Mind Maps, Deep Research, Quizzes
2. **Elicit** — Structured extraction, systematic review, custom columns
3. **Paperguide** — AI Paper Writer, reference management, Deep Research
4. **Consensus** — Claim-based evidence analysis, research snapshots
5. **ResearchRabbit** — Collections, algorithmic recommendations, citation graphs
6. **Connected Papers / Litmaps** — Citation visualization
7. **scite.ai** — Smart citations (supporting vs contrasting)
8. **SciSpace** — Copilot for reading, thematic analysis

---

*Last updated: 2026-02-24 — v3.6.0*
