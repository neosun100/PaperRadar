# PaperRadar — Development Roadmap

## ✅ Completed (v3.9.0) — 80+ Features, 97 API Endpoints

*(See CHANGELOG.md for full history)*

All Phase 7 features completed: Mind Map, AI Paper Writer, Systematic Review,
Slide Deck, Recommendation Feed, Paper Tags, Custom Extraction, PDF Thumbnails,
Keyboard Shortcuts, Deep Research History, User Preferences.

---

## 🔲 Phase 8: World-Class Research Platform

Based on competitive analysis of NotebookLM, Elicit, Paperguide, SciSpace,
Okara, Consensus, Perplexity, and Scite (Feb 2026).

### 8A: Social & Community Intelligence (High Priority)

- [ ] **Reddit/X/HN Discussion Discovery**
  - Search Reddit, X, HackerNews for discussions about a paper
  - Show community sentiment and key takeaways
  - Inspired by: Okara (multi-source search), alphaXiv (discussions)

- [x] **Paper Impact Score**
  - Composite score: citations + social mentions + HF upvotes + recency
  - Display on paper cards and in recommendations
  - Inspired by: Altmetric, Semantic Scholar influence scores

- [ ] **Weekly Research Digest Email**
  - Auto-generated weekly summary of radar discoveries + KB activity
  - HTML email template with paper cards
  - Configurable via preferences

### 8B: Advanced Analysis (Medium Priority)

- [x] **Cross-Paper Timeline**
  - Visual timeline of papers by publication date
  - Show how methods/ideas evolved over time
  - Interactive: click to navigate to paper

- [x] **Method Benchmark Tracker**
  - Track SOTA results across papers for specific benchmarks
  - Auto-extract from paper findings
  - Table view: method × benchmark × score

- [ ] **Paper Dependency Graph**
  - Which papers build on which? (beyond simple citations)
  - "This paper extends X by adding Y"
  - Extracted from knowledge relationships

### 8C: Productivity & Polish (Lower Priority)

- [x] **Quick Notes (global scratchpad)**
  - Markdown notepad accessible from any page
  - Link notes to papers
  - Inspired by: Obsidian daily notes

- [ ] **Bulk Re-extract Knowledge**
  - Re-run knowledge extraction on papers with outdated/incomplete data
  - Progress tracking

- [ ] **API Rate Limit Dashboard**
  - Show remaining S2/arXiv API quota
  - Warn when approaching limits

- [ ] **Accessibility Improvements**
  - ARIA labels on interactive elements
  - Screen reader support for key workflows
  - High contrast mode option

---

## 💡 Design Inspirations (2026 Update)

1. **NotebookLM** — Video Overviews, Interactive Audio, Mind Maps, Deep Research
2. **Elicit** — Systematic Review workflow, custom extraction columns, screening pipeline
3. **Paperguide** — AI Paper Writer, Deep Research, reference management
4. **Consensus** — Claim-based evidence, research snapshots
5. **Okara** — Multi-source search (Reddit, X, YouTube), privacy-first
6. **SciSpace** — Copilot for reading, thematic analysis
7. **Scite** — Smart citations (supporting/contrasting/mentioning)
8. **Perplexity** — Real-time web search with citations

---

*Last updated: 2026-02-25 — v3.9.0*
