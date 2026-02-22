# PaperRadar — Development Roadmap

## ✅ Completed

### Core Platform
- [x] PDF Upload — drag & drop, no file size limit
- [x] PDF Translation — English → Chinese via pdf2zh, preserving layout/images/formulas
- [x] PDF Simplification — Complex English → Plain English (CEFR A2/B1)
- [x] AI Highlighting — Three-color annotation (conclusions/methods/data)
- [x] Document Reader — Split-pane PDF viewer with focus mode
- [x] Task Queue — Per-user concurrency control (3 concurrent per API key)
- [x] Queue Status UI — Processing/queued counts in Dashboard header

### Knowledge Base
- [x] Knowledge Extraction — Bilingual (en/zh) entities, relationships, findings, flashcards
- [x] Paper Detail — Tabs for chat, entities, findings, relations, flashcards, notes
- [x] Paper Chat — Chat with any paper using extracted knowledge as context
- [x] Knowledge Graph — Interactive force-directed graph visualization
- [x] Research Insights — Cross-paper analysis (field overview, method comparison, timeline, research gaps, paper connections)
- [x] Flashcard Review — SM-2 spaced repetition (accessible from knowledge base)
- [x] Multi-Format Export — JSON, BibTeX, Obsidian Vault, CSL-JSON, CSV

### Radar Engine
- [x] arXiv Auto-Scan — Scans cs.CL, cs.AI, cs.LG every hour on the hour
- [x] Startup Scan — Immediate scan when container starts
- [x] LLM Relevance Scoring — Intelligent agent scores each paper's relevance
- [x] Auto-Download & Process — Top 3 papers per scan: download PDF → translate → highlight
- [x] Deduplication — Skip papers already in knowledge base (by arxiv_id)
- [x] Serial Processing — Avoid font/resource conflicts
- [x] Auto-Cleanup — Failed radar tasks automatically removed from UI
- [x] Radar UI Panel — Dashboard shows scanning animation, stats, recent discoveries grid
- [x] Font Pre-Download — All babeldoc fonts baked into Docker image

### Notifications (Code Ready)
- [x] Bark Service — iOS push notification implementation
- [x] Lark Service — Card 2.0 interactive message implementation
- [ ] Configure Bark key in config.yaml to activate
- [ ] Configure Lark webhook in config.yaml to activate

### Infrastructure
- [x] All-in-one Docker — Frontend (nginx) + Backend (uvicorn) + supervisord
- [x] API Token Auth — Bearer token for programmatic access, uses server-side LLM
- [x] Per-User Concurrency — Each API key gets independent processing queue
- [x] No File Limits — No page count or file size restrictions
- [x] Permanent Storage — All results permanently stored on cloud, no auto-cleanup
- [x] Shared Results — All users benefit from each other's processed papers
- [x] Privacy Protection — Secrets only in runtime config volume, never in Git or Docker image

### UI/UX
- [x] Multilingual UI (i18n) — Full English/Chinese with one-click switching
- [x] Bilingual Knowledge — All extracted knowledge has en/zh, follows UI language
- [x] Dark Mode — Full dark mode across entire UI
- [x] Favicon — Radar icon in browser tab
- [x] Cloud/Security Notice — Clear explanation in LLM Settings dialog
- [x] Brand — PaperRadar with radar logo and tagline

### Documentation
- [x] README.md — English, full feature docs
- [x] README_zh.md — Chinese version
- [x] config.example.yaml — Documented configuration template
- [x] TODO.md — This roadmap

---

## 🔲 To Do — Prioritized Roadmap

### Phase 1: Complete the Radar Loop (High Priority)

These make the radar truly autonomous end-to-end:

- [ ] **Radar Auto-Knowledge-Extract** — After radar translates a paper, automatically trigger knowledge extraction + Research Insights regeneration. The full pipeline: arXiv → download → translate → highlight → extract knowledge → update insights → notify.

- [ ] **Radar Management Page** — Dedicated `/radar` page with:
  - Live scan status with animation
  - Configurable categories and topics (editable in UI)
  - Scan history log (timestamp, papers found, papers processed)
  - All discovered papers with scores, filterable/sortable
  - Manual "Scan Now" button
  - Next scan countdown timer

- [ ] **Multi-Source Radar** — Expand beyond arXiv:
  - **Hugging Face Daily Papers** — `https://huggingface.co/api/daily_papers` for community-curated trending AI papers
  - **Semantic Scholar** — Use their free API (200M+ papers, 100 req/5min) for citation-based discovery: find highly-cited recent papers, track influential citations
  - **Papers with Code** — Use `paperswithcode-client` Python package for SOTA results and trending papers with code implementations
  - **alphaXiv** — Hot/trending papers with community discussion scores

### Phase 2: Deeper Understanding (Medium Priority)

These leverage external tools to make PaperRadar smarter:

- [ ] **Cross-Paper Chat** — Chat across the entire knowledge base: "Compare all RLHF methods", "What are the latest advances in RAG?". Uses all extracted knowledge as context.

- [ ] **Vector Search (ChromaDB)** — Embed paper content for semantic search:
  - ChromaDB (pure Python, embedded, zero-config) for vector storage
  - Embed paper abstracts + findings + entities on extraction
  - Power semantic search: "find papers about efficient inference"
  - Enable better cross-paper chat with RAG retrieval
  - Reference: LangGraph Research Agent pattern, ArXiv Paper Curator (GROBID + OpenSearch)

- [ ] **Connected Papers Integration** — Use Connected Papers / Semantic Scholar citation graph to:
  - Auto-discover related papers from citations of papers in knowledge base
  - Show citation network visualization (paper-level, not just entity-level)
  - "Papers that cite this paper" and "Papers this paper cites"

- [ ] **Paper Upload via URL** — Paste arXiv URL or DOI to auto-download and process. Detect arXiv ID from URL, fetch metadata from Semantic Scholar API.

- [ ] **Smart Recommendations** — Based on existing knowledge base:
  - Use Semantic Scholar Recommendations API to find related papers
  - Score recommendations against user's topic interests
  - Show "Recommended for you" section on Dashboard
  - Reference: ResearchRabbit's "paper Spotify" approach, Scholar Inbox's personalization

### Phase 3: Platform Features (Lower Priority)

- [ ] **Paper Reading Enhancements**:
  - ar5iv HTML rendering — Convert LaTeX to HTML5 for better in-browser reading (reference: arXiv Labs ar5iv)
  - Inline AI explanations — Click any sentence to get a simplified explanation
  - Smart Citations — Show citation context (supporting/contrasting) like scite.ai

- [ ] **MCP Server** — Expose PaperRadar as an MCP server so Claude/Cursor can:
  - Search the knowledge base
  - Ask questions about papers
  - Trigger radar scans
  - Reference: blazickjp/arxiv-mcp-server (⭐2.2k), alphaXiv MCP server

- [ ] **Batch Upload** — Upload multiple PDFs at once, or paste multiple arXiv IDs

- [ ] **Email Digest** — Weekly email summary of radar discoveries, configurable

- [ ] **CI/CD Pipeline** — GitHub Actions for:
  - Automated TypeScript type checking
  - Python linting
  - Docker image build and push on tag

- [ ] **Mobile Responsive** — Optimize radar panel and knowledge base for mobile/tablet

---

## 🔍 External Tools & APIs to Integrate

Based on comprehensive research of the arXiv ecosystem:

| Tool/API | How to Use | Priority |
|----------|-----------|----------|
| **Semantic Scholar API** | Free, 200M+ papers, citation data, recommendations, TLDR summaries. 100 req/5min. Python SDK: `semanticscholar` | High |
| **HuggingFace Daily Papers** | `/api/daily_papers` endpoint for trending AI papers. Free, no auth needed | High |
| **Papers with Code** | `paperswithcode-client` Python package. SOTA results, code repos, trending | High |
| **alphaXiv** | MCP server + trending/hot papers with community scores | Medium |
| **ChromaDB** | Embedded vector DB, pure Python, zero-config. For semantic search | Medium |
| **Semantic Scholar Recommendations** | `/recommendations/v1/papers/` endpoint for personalized suggestions | Medium |
| **Connected Papers** | Citation graph visualization, related paper discovery | Medium |
| **ar5iv** | LaTeX → HTML5 conversion for better reading experience | Low |
| **scite.ai** | Smart citation context (supporting/contrasting) | Low |

---

## 📦 Version History

| Version | Date | Highlights |
|---------|------|------------|
| 0.3.4 | 2026-02-22 | Favicon, Chinese message fix |
| 0.3.3 | 2026-02-22 | Fix hardcoded Chinese progress messages |
| 0.3.2 | 2026-02-22 | Auto-cleanup failed radar tasks |
| 0.3.1 | 2026-02-22 | Pre-download fonts, serial radar processing |
| 0.3.0 | 2026-02-22 | Radar UI panel, auto-process top 3, hourly scans |
| 0.2.0 | 2026-02-22 | Radar Engine, Paper Chat, Bark/Lark notifications |
| 0.1.0 | 2026-02-22 | Brand rename to PaperRadar, initial release |

---

## 💡 Design Inspirations

Key insights from the arXiv ecosystem research:

1. **Elicit** — Best-in-class for structured data extraction from papers. Their comparison table UI is excellent. We already have this in Research Insights.

2. **ResearchRabbit** — "Paper Spotify" concept: build collections → get algorithmic recommendations. Our knowledge base + smart recommendations could achieve this.

3. **Scholar Inbox / IArxiv** — Personalized daily recommendations based on research interests. Our radar + LLM scoring already does this, but we can enhance with Semantic Scholar's recommendation API.

4. **Connected Papers / Litmaps** — Citation graph visualization. We have entity-level knowledge graph; adding paper-level citation network would be powerful.

5. **alphaXiv** — Community discussion and trending scores. Their MCP server could feed our radar with community-validated hot papers.

6. **OpenScholar** — RAG-based literature review with accurate citations. Our Research Insights + future vector search could approach this quality.

7. **ArXiv Paper Curator** — Production RAG pipeline (Airflow + GROBID + OpenSearch). Good architecture reference for scaling our radar.

---

*Last updated: 2026-02-22*

> **Note**: Version history moved to CHANGELOG.md for cleaner separation.
