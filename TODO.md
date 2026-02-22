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

- [ ] **Smart Paper Recommendations**
  - Use Semantic Scholar Recommendations API (`/recommendations/v1/papers/`)
  - Based on papers already in knowledge base, suggest related papers
  - "Because you read X, you might like Y" — ResearchRabbit-style
  - Show on Dashboard as "Recommended for You" section

- [ ] **Citation Network Visualization**
  - Paper-level citation graph (not just entity-level)
  - "Papers that cite this" and "Papers this cites"
  - Use Semantic Scholar citation data
  - Connected Papers / Litmaps style visualization
  - Inspired by: Connected Papers, Litmaps, Paperscape

- [ ] **Automatic Literature Review Generation**
  - Given a topic/question, generate a structured literature review
  - Cite papers from knowledge base with proper references
  - Inspired by: OpenScholar, Elicit systematic review automation
  - Output as Markdown, exportable

### Phase 2: Enhanced Reading & Understanding (Medium Priority)

- [ ] **Paper Annotation & Highlighting in Reader**
  - User can highlight text in the PDF reader
  - Add notes to specific passages
  - Annotations saved and searchable
  - Inspired by: Hypothesis, Readwise

- [ ] **AI Inline Explanations**
  - Click any sentence in the reader to get simplified explanation
  - "Explain this to me like I'm a beginner"
  - Context-aware using paper's knowledge

- [ ] **Smart Citations (scite.ai-style)**
  - Show how a paper is cited: supporting, contrasting, or mentioning
  - Help users understand citation context
  - Use Semantic Scholar citation context API

- [ ] **Vector Search (ChromaDB)**
  - Embed paper content for semantic search
  - "Find papers about efficient inference" → semantic matching
  - Power better cross-paper chat with RAG retrieval
  - ChromaDB: pure Python, embedded, zero-config

- [ ] **Paper Comparison View**
  - Side-by-side comparison of 2-3 papers
  - Auto-generated comparison table (methods, results, datasets)
  - Inspired by: Elicit's comparison tables

### Phase 3: Platform & Integration (Lower Priority)

- [ ] **MCP Server**
  - Expose PaperRadar as MCP server for Claude/Cursor
  - Tools: search KB, ask questions, trigger scans, get trending
  - Inspired by: blazickjp/arxiv-mcp-server (⭐2.2k), alphaXiv MCP

- [ ] **Chirpz-style Paper Prioritization**
  - AI agent that understands your research context
  - Ranks papers by relevance to YOUR specific work
  - Learns from your reading patterns
  - Inspired by: Chirpz Agent (280M+ papers)

- [ ] **Multi-Language Paper Support**
  - Support Chinese papers (翻译为英文)
  - Support papers in other languages
  - Bidirectional translation

- [ ] **Collaborative Features**
  - Shared reading lists / paper collections
  - Team annotations and discussions
  - Inspired by: alphaXiv discussions, ResearchRabbit collections

- [ ] **Paper Writing Assistant**
  - Help write related work sections
  - Auto-generate citations from knowledge base
  - Inspired by: Paperguide writing assistance

- [ ] **Webhook / API Notifications**
  - Webhook callback when radar discovers papers
  - Slack / Discord / Telegram integration
  - Email digest (daily/weekly)

- [ ] **CI/CD Pipeline**
  - GitHub Actions: TypeScript check, Python lint, Docker build+push on tag

- [ ] **Mobile Responsive**
  - Optimize for mobile/tablet viewing

---

## 🔍 External Tools & APIs Reference

| Tool/API | Integration Plan | Status |
|----------|-----------------|--------|
| **arXiv API** | Paper discovery, PDF download | ✅ Integrated |
| **Semantic Scholar API** | Citation data, recommendations, trending | ✅ Partial (search), 🔲 recommendations |
| **HuggingFace Daily Papers** | Community-curated trending, upvotes | ✅ Integrated |
| **Papers with Code** | SOTA results, code repos | 🔲 Planned |
| **alphaXiv** | Community discussions, hot papers | 🔲 Planned |
| **ChromaDB** | Vector search, semantic retrieval | 🔲 Planned |
| **scite.ai** | Smart citation context | 🔲 Planned |
| **Connected Papers** | Citation graph visualization | 🔲 Planned (via S2 API) |
| **Google NotebookLM** | Audio overview inspiration | 🔲 Planned (own TTS) |

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
