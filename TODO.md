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
- [x] Paper Detail — Tabs for entities, findings, relations, flashcards, notes
- [x] Paper Chat — Chat with any paper using extracted knowledge as context
- [x] Knowledge Graph — Interactive force-directed graph visualization
- [x] Research Insights — Cross-paper analysis (field overview, method comparison, timeline, research gaps, paper connections)
- [x] Flashcard Review — SM-2 spaced repetition (demoted from main nav, still accessible)
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
- [x] No Auto-Cleanup — All results permanently stored on cloud
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

---

## 🔲 To Do

### High Priority
- [ ] **Radar Auto-Knowledge-Extract** — After radar translates a paper, automatically trigger knowledge extraction so it enters the knowledge base without manual action
- [ ] **Radar Management Page** — Dedicated page to configure categories/topics, view scan history, trigger manual scan, see all discovered papers with scores
- [ ] **Cross-Paper Chat** — Chat across multiple papers: "Compare all RLHF methods in my knowledge base"

### Medium Priority
- [ ] **Vector Search (ChromaDB)** — Embed paper content for semantic search and better cross-paper chat
- [ ] **More Data Sources** — HuggingFace Daily Papers, Semantic Scholar trending, Papers with Code SOTA
- [ ] **Smart Recommendations** — Personalized paper suggestions based on existing knowledge base
- [ ] **Radar Paper Preview** — Click a discovered paper in radar panel to see title/abstract/score before processing

### Low Priority
- [ ] **Email Notifications** — SMTP email push for new paper discoveries
- [ ] **User Accounts** — Optional login/registration for multi-tenant isolation
- [ ] **Paper Upload via URL** — Paste arXiv/DOI URL to auto-download and process
- [ ] **Batch Upload** — Upload multiple PDFs at once via file picker
- [ ] **MCP Server** — Model Context Protocol server for integration with Claude/other AI assistants
- [ ] **CI/CD Pipeline** — GitHub Actions for automated testing and Docker image publishing
- [ ] **Mobile Responsive** — Optimize UI for mobile/tablet viewing

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

*Last updated: 2026-02-22*
