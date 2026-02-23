# PaperRadar — Development Roadmap

## ✅ Completed (v1.0.3)

### Core Platform
- [x] PDF Upload (drag & drop, URL upload, no size limit)
- [x] PDF Translation (English → Chinese, pdf2zh, layout preserved)
- [x] PDF Simplification (Complex → Plain English, CEFR A2/B1)
- [x] AI Highlighting (3-color: conclusions/methods/data)
- [x] Document Reader (split-pane, focus mode)
- [x] Task Queue (per-user concurrency, queue status UI)
- [x] Zombie Task Recovery (auto-detect and re-process on restart)

### Knowledge Base
- [x] Bilingual Knowledge Extraction (en/zh entities, relationships, findings, flashcards)
- [x] Paper Chat (single-paper Q&A with knowledge context)
- [x] Cross-Paper Chat ("Ask All Papers" across entire KB)
- [x] Research Insights (field overview, method comparison, timeline, gaps, connections)
- [x] Knowledge Graph (force-directed, bilingual nodes)
- [x] Multi-Format Export (JSON, BibTeX, Obsidian, CSL-JSON, CSV)
- [x] Flashcard Review (SM-2 spaced repetition)

### Radar Engine
- [x] 3-Source Radar: arXiv + Semantic Scholar + HuggingFace Daily Papers
- [x] HuggingFace Upvote Ranking (community signal for quality)
- [x] Trending Papers (7d/14d/30d aggregation with upvote sort)
- [x] Smart Hybrid Scoring (HF upvotes, S2 citations, keyword pre-filter)
- [x] Auto-Download & Process (top 3 per scan, serial, with knowledge extraction)
- [x] Queue Capacity Control (≥3 active → scan only, no flooding)
- [x] Robust Deduplication (KB + tasks + session)
- [x] Configurable Startup Scan
- [x] Radar Management Page (/radar with stats, discoveries, trending tabs)
- [x] Dashboard Radar Panel (animation, recent discoveries, source tags, upvotes)

### Notifications
- [x] Bark iOS Push (code ready, configure bark_key to activate)
- [x] Lark Card 2.0 (code ready, configure lark_webhook to activate)

### Infrastructure
- [x] All-in-one Docker (nginx + uvicorn + supervisord)
- [x] Pre-downloaded fonts + ONNX model in image
- [x] API Token Auth (Bearer token → server-side LLM)
- [x] Per-User Concurrency Isolation
- [x] Permanent Storage (no auto-cleanup)
- [x] Privacy Protection (secrets in volume, never in Git/image)

### UI/UX
- [x] i18n (English/Chinese, one-click switch)
- [x] Bilingual Knowledge (follows UI language)
- [x] Dark Mode
- [x] Favicon (radar icon)
- [x] Stats Overview Panel
- [x] Auto-sanitize legacy Chinese messages

---

## 🔲 To Do — Prioritized Roadmap

### Phase 1: Intelligence & Discovery (High Priority)

- [x] **Paper Audio Summary (NotebookLM-style)**
  - Generate podcast-style audio overview of papers using TTS
  - Two AI hosts discuss key findings in conversational format
  - Inspired by Google NotebookLM's Audio Overviews feature
  - Uses OpenAI-compatible TTS API (/audio/speech)

- [x] **Smart Paper Recommendations**
  - Use Semantic Scholar Recommendations API (`/recommendations/v1/papers/`)
  - Based on papers already in knowledge base, suggest related papers
  - "Because you read X, you might like Y" — ResearchRabbit-style
  - Show on Dashboard as "Recommended for You" section

- [x] **Citation Network Visualization**
  - Paper-level citation graph (not just entity-level)
  - "Papers that cite this" and "Papers this cites"
  - Use Semantic Scholar citation data
  - Connected Papers / Litmaps style visualization
  - Inspired by: Connected Papers, Litmaps, Paperscape

- [x] **Automatic Literature Review Generation**
  - Given a topic/question, generate a structured literature review
  - Cite papers from knowledge base with proper references
  - Inspired by: OpenScholar, Elicit systematic review automation
  - Output as Markdown, exportable

### Phase 2: Enhanced Reading & Understanding (Medium Priority)

- [x] **Paper Annotation & Highlighting in Reader**
  - User can highlight text in the PDF reader
  - Add notes to specific passages
  - Annotations saved and searchable
  - Inspired by: Hypothesis, Readwise

- [x] **AI Inline Explanations**
  - Click any sentence in the reader to get simplified explanation
  - "Explain this to me like I'm a beginner"
  - Context-aware using paper's knowledge

- [x] **Smart Citations (scite.ai-style)**
  - Show how a paper is cited: supporting, contrasting, or mentioning
  - Help users understand citation context
  - Use Semantic Scholar citation context API

- [x] **Vector Search (ChromaDB)**
  - Embed paper content for semantic search
  - "Find papers about efficient inference" → semantic matching
  - Power better cross-paper chat with RAG retrieval
  - ChromaDB: pure Python, embedded, zero-config

- [x] **Paper Comparison View**
  - Side-by-side comparison of 2-3 papers
  - Auto-generated comparison table (methods, results, datasets)
  - Inspired by: Elicit's comparison tables

### Phase 3: Platform & Integration (Lower Priority)

- [x] **MCP Server**
  - Expose PaperRadar as MCP server for Claude/Cursor
  - Tools: search KB, ask questions, trigger scans, get trending
  - Inspired by: blazickjp/arxiv-mcp-server (⭐2.2k), alphaXiv MCP

- [x] **Chirpz-style Paper Prioritization**
  - AI agent that understands your research context
  - Ranks papers by relevance to YOUR specific work
  - Learns from your reading patterns
  - Inspired by: Chirpz Agent (280M+ papers)

- [x] **Multi-Language Paper Support**
  - Support Chinese papers (翻译为英文)
  - Support papers in other languages
  - Bidirectional translation

- [x] **OpenAlex Integration**
  - Free open-access metadata for 250M+ works
  - Replace Papers with Code (shut down 2025)
  - Author profiles, institution data, topic classification
  - API: https://api.openalex.org

- [x] **Elicit-style Data Extraction Tables**
  - Extract structured data from multiple papers into comparison tables
  - Custom columns (method, dataset, metric, result)
  - Export as CSV/spreadsheet
  - Inspired by: Elicit's data extraction feature

- [x] **Paper Timeline / Reading History**
  - Track which papers you've read and when
  - Visual timeline of your research journey
  - Reading statistics and streaks

- [x] **Email Digest**
  - Daily/weekly email summary of radar discoveries
  - Configurable frequency and format

- [x] **Collaborative Features**
  - Shared reading lists / paper collections
  - Team annotations and discussions
  - Inspired by: alphaXiv discussions, ResearchRabbit collections

- [x] **Paper Writing Assistant**
  - Help write related work sections
  - Auto-generate citations from knowledge base
  - Inspired by: Paperguide writing assistance

- [x] **Webhook / API Notifications**
  - Webhook callback when radar discovers papers
  - Slack / Discord / Telegram integration
  - Email digest (daily/weekly)

- [x] **CI/CD Pipeline**
  - GitHub Actions: TypeScript check, Python lint, Docker build+push on tag

- [x] **Mobile Responsive**
  - Optimize for mobile/tablet viewing

---

## 🔲 To Do — Phase 4: Production Polish & Advanced Features

### Phase 4A: UX & Reliability (High Priority)

- [x] **Batch Import (DOI / arXiv / BibTeX)**
  - Import multiple papers at once via DOI list, arXiv IDs, or BibTeX file
  - Auto-download PDFs and queue for processing
  - Drag-and-drop BibTeX file support

- [x] **Paper Summary Cards on Dashboard**
  - Show AI-generated 1-sentence summary for each paper
  - Quick-glance view without opening paper detail
  - Generated during knowledge extraction

- [ ] **SSE Progress Streaming**
  - Replace polling with Server-Sent Events for real-time progress
  - Smoother UX for translation/extraction progress bars

- [x] **Search Across Everything**
  - Unified search: papers, annotations, flashcards, collections
  - Keyboard shortcut (Cmd+K / Ctrl+K) to open search

### Phase 4B: Intelligence (Medium Priority)

- [x] **Daily Briefing / Auto-Digest**
  - Scheduled daily summary of new radar discoveries
  - Push via configured notification channels (Bark/Lark/Webhook)
  - Configurable schedule in config.yaml

- [ ] **Figure & Table Extraction**
  - Extract figures and tables from PDFs as images
  - Display in Paper Detail alongside knowledge
  - Inspired by: SciSpace, Paperguide

- [ ] **Zotero / Mendeley Sync**
  - Import from Zotero library via API
  - Export collections to Zotero
  - Two-way sync of reading status

- [ ] **Paper Similarity Map**
  - 2D embedding visualization of all KB papers
  - Cluster papers by topic using vector embeddings
  - Interactive: click cluster to see papers

### Phase 4C: Platform (Lower Priority)

- [ ] **Public API Documentation Page**
  - Interactive Swagger UI at /api/docs (already exists)
  - Add usage examples and rate limit info

- [x] **Keyboard Shortcuts**
  - Cmd+K: global search
  - Cmd+N: new upload
  - Arrow keys: navigate papers
  - Esc: close panels

- [ ] **Performance Optimization**
  - Lazy-load heavy pages (KnowledgeGraph, PaperDetail)
  - Code splitting with React.lazy()
  - Reduce bundle size (currently 620KB gzipped 190KB)

- [ ] **Backup & Restore**
  - One-click backup of entire DB + vector store
  - Restore from backup file
  - Scheduled auto-backup

| Tool/API | Integration Plan | Status |
|----------|-----------------|--------|
| **arXiv API** | Paper discovery, PDF download | ✅ Integrated |
| **Semantic Scholar API** | Citation data, recommendations, contexts | ✅ Integrated |
| **HuggingFace Daily Papers** | Community-curated trending, upvotes | ✅ Integrated |
| **ChromaDB** | Vector search, semantic retrieval | ✅ Integrated |
| **scite.ai-style** | Smart citation context (via S2 API) | ✅ Integrated |
| **Connected Papers-style** | Citation graph visualization (via S2 API) | ✅ Integrated |
| **OpenAlex** | Open metadata, author profiles, topics | ✅ Integrated |
| **Papers with Code** | SOTA results, code repos | ❌ Shut down (2025) |
| **alphaXiv** | Community discussions, hot papers | 🔲 Planned |

---

## 💡 Design Inspirations

1. **Google NotebookLM** — Audio Overviews: turn papers into podcast-style conversations. Revolutionary UX for consuming research.
2. **Elicit** — Structured data extraction, comparison tables, systematic review automation. Gold standard for research workflow.
3. **Chirpz Agent** — Context-aware paper prioritization across 280M+ papers. Understands YOUR research needs.
4. **ResearchRabbit** — "Paper Spotify": collections → algorithmic recommendations → citation graphs.
5. **OpenScholar** — RAG-based literature review with accurate citations. Outperforms GPT in citation accuracy.
6. **Connected Papers / Litmaps** — Citation graph visualization. See how papers relate.
7. **alphaXiv** — Community discussion layer on top of arXiv. Social signal for paper quality.
8. **Paperguide** — Chat with PDFs, writing assistance, reference management. All-in-one research tool.
9. **scite.ai** — Smart citations: supporting vs contrasting. Understand citation context.

---

*Last updated: 2026-02-23*
