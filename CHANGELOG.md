# PaperRadar Changelog

## v3.0.0 (2026-02-24)
- **TLDR Auto-Summary**
  - Knowledge extraction now generates a one-sentence bilingual TLDR for each paper
  - TLDR displayed prominently on paper cards in Knowledge Base (💡 prefix)
  - TLDR shown at top of abstract in Paper Detail page
  - Backfill API: POST /api/knowledge/papers/{id}/generate-tldr for existing papers
- **Similar Papers Discovery**
  - Vector-based similarity: find related papers from your knowledge base
  - GET /api/knowledge/papers/{id}/similar returns top N similar papers with scores
  - Displayed as clickable chips on Paper Detail page
- **Reading Progress Tracking**
  - New ReadingProgress model saves scroll position and page number
  - PUT/GET /api/knowledge/reading-progress/{id} API
- **Search Highlight**
  - Cmd+K search results now highlight matching words with yellow background
- **Bug Fixes**
  - Fixed numpy array truthiness check in vector similarity queries

## v2.9.0 (2026-02-24)
- **alphaXiv Integration**
  - 4th radar data source: alphaXiv trending papers with community discussions
  - Merged into radar scan loop alongside arXiv, Semantic Scholar, HuggingFace
- **DOI Resolution for Batch Import**
  - DOIs now resolved to arXiv IDs via OpenAlex API
  - Supports `doi:10.xxxx/yyyy` format in batch import
- **Research Gaps Analysis**
  - Dedicated endpoint: POST /api/knowledge/research-gaps
  - Identifies: open problems, contradictions, underexplored areas, future directions
  - Downloadable as Markdown
  - New button on Research Insights page
- **Radar Engine**: 4 sources (arXiv + Semantic Scholar + HuggingFace + alphaXiv)

## v2.8.0 (2026-02-24)
- **Figure & Table Extraction**
  - Extract figures/images from PDFs using PyMuPDF (auto-filters icons/logos)
  - Extract structured tables with headers and rows (PyMuPDF find_tables)
  - New "Figures & Tables" tab on Paper Detail page
  - API: GET /api/knowledge/papers/{id}/figures, /tables, /figures/{index}
- **Paper Similarity Map**
  - 2D PCA visualization of all paper embeddings from ChromaDB
  - Interactive canvas: hover to see title, click to navigate
  - New page at /knowledge/similarity, accessible from Knowledge Base
  - API: GET /api/knowledge/similarity-map
- **Zotero Import**
  - Import papers from Zotero library via API key + library ID
  - Auto-creates KB entries with metadata (title, authors, DOI, abstract)
  - Deduplication by title
  - API: POST /api/knowledge/import/zotero
- **Error Boundary**
  - Global React error boundary catches rendering crashes
  - User-friendly error page with reload button
- **Onboarding Guide**
  - 5-step interactive guide for first-time users
  - Covers: Upload, Knowledge Extraction, Search, Radar, Export
  - Dismissible, persisted in localStorage

## v2.7.0 (2026-02-23)
- **Backup & Restore**
  - GET /api/backup → download ZIP of SQLite DB + ChromaDB vector store
  - POST /api/restore → upload ZIP to restore (requires container restart)
- **Performance Optimization**
  - React.lazy() code splitting: main bundle 620KB → 444KB (28% smaller)
  - 7 pages lazy-loaded on demand (Reader, KnowledgeBase, PaperDetail, etc.)
  - Loading spinner during chunk download
- **SSE Progress Streaming**
  - Reader uses Server-Sent Events for real-time translation progress
  - Visual progress bar with percentage and status message
  - Fallback to polling if SSE unavailable
- **Public API Documentation**
  - Swagger UI accessible at /api/docs (via nginx proxy)
  - ReDoc at /api/redoc, OpenAPI spec at /api/openapi.json

## v2.6.0 (2026-02-23)
- **Paper Summary Cards**
  - Knowledge Base paper cards now show abstract preview (first 200 chars)
  - Quick-glance view without opening paper detail
- **Daily Briefing / Auto-Digest**
  - Scheduled daily digest via Bark/Lark/Webhook
  - Configure `digest_hour` in config.yaml (UTC hour, -1 to disable)
- **Security Hardening**
  - Added security headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
  - Improved error logging (no internal details leaked to clients)
  - Removed partial API key from docs (privacy fix)
- **Privacy Audit** — verified no secrets in codebase, Docker image, or docs

## v2.5.0 (2026-02-23)
- **Batch Import**
  - Import multiple papers via arXiv IDs, DOIs, or BibTeX
  - Paste list or BibTeX → auto-parse and queue all papers
  - Max 20 per batch, deduplication built-in
- **Cmd+K Global Search**
  - Press ⌘K / Ctrl+K anywhere to open semantic search overlay
  - Real-time results from ChromaDB vector search
  - Click result to navigate to paper detail
  - ESC to close
- **Phase 4 Roadmap** defined in TODO.md (12 new items)

## v2.4.0 (2026-02-23) 🎉 ALL TODO COMPLETE
- **Chirpz-style Paper Prioritization**
  - AI ranks papers by personal relevance based on your KB profile
  - POST /api/knowledge/prioritize with candidate papers
  - Builds research profile from your completed papers' methods & topics
- **Multi-Language Paper Support**
  - New "Chinese → English" translation mode (zh2en)
  - pdf2zh bidirectional: en→zh, zh→en, simplify
  - New button on Dashboard for Chinese paper translation
- **Activity Digest**
  - GET /api/knowledge/digest?days=N
  - Summary of new papers, reading events, KB stats
  - Text format ready for email/webhook/Slack
- **MCP Server**: 12 tools (added get_digest)

## v2.3.0 (2026-02-23)
- **Elicit-style Data Extraction Tables**
  - Select papers → extract structured data into comparison table
  - Custom columns (method, dataset, metric, result, etc.)
  - Copy as TSV for spreadsheet paste
  - Interactive table display in Knowledge Base
- Bug fix: f-string syntax error in extract-table endpoint

## v2.2.0 (2026-02-23)
- **OpenAlex Integration**
  - One-click paper enrichment from OpenAlex (250M+ works)
  - Shows citation count, open access status, topics, institutions
  - Auto-fills missing DOI, year, venue from OpenAlex data
  - "Enrich" button on Paper Detail page
- **Reading History / Timeline**
  - Auto-tracks paper views and reads
  - Reading events API with daily aggregation
  - Stats: total events, unique papers read
- **JSON Repair for Knowledge Extraction**
  - Robust repair of malformed LLM JSON responses
  - Handles trailing commas, truncated output, unescaped characters
  - Significantly reduces extraction failures

## v2.1.0 (2026-02-23)
- **Paper Collections** (ResearchRabbit-style)
  - Create, rename, delete collections
  - Add/remove papers to collections
  - Filter Knowledge Base by collection
  - Collection bar with paper counts
- **Paper Writing Assistant**
  - Generate "Related Work" sections from selected papers
  - Supports IEEE, ACM, APA citation styles
  - Topic-focused generation
  - Copy to clipboard
- **Generic Webhook Notifications**
  - Webhook URL support for Slack, Discord, n8n, etc.
  - Auto-detects Slack/Discord format
  - Configurable via config.yaml
- **MCP Server expanded** — 10 tools (added list_collections, generate_related_work)

## v2.0.0 (2026-02-23) 🎉
- **Paper Annotation & Highlighting in Reader**
  - Annotation sidebar in Reader page with note/highlight/question types
  - Color-coded annotations (yellow/blue/green/pink)
  - Annotations saved to DB, persistent across sessions
  - Ctrl+Enter to quickly save annotations
- **AI Inline Explanations**
  - New "AI Explain" panel in Reader
  - Paste any sentence → get CEFR A2/B1 simplified explanation
  - Powered by LLM with academic context awareness
- **Smart Citations (scite.ai-style)**
  - Citation contexts showing HOW this paper is cited
  - Intent classification (methodology/result/background)
  - Blockquote display of actual citation sentences
  - Integrated into Citations tab on Paper Detail
- **Mobile Responsive**
  - Hamburger menu for mobile navigation
  - Active route highlighting
  - Responsive padding and layout adjustments
- **CI/CD Pipeline**
  - GitHub Actions: Docker build+push on tag (docker.yml)
- **MCP Server** (already existed, now documented as complete)
  - 8 tools: search, list, get, chat, trending, radar, process, review

## v1.8.0 (2026-02-23)
- Citation Network Visualization (Connected Papers-style)
  - New "Citations" tab on Paper Detail page
  - Fetches references and citing papers from Semantic Scholar API
  - Interactive force-directed graph with color-coded nodes:
    - 🟡 Amber = current paper, 🔵 Blue = references, 🟢 Green = cited by
  - Click any node to see title, year, citation count, authors
  - Direct links to arXiv and Semantic Scholar for each paper
  - Arrow-directed edges showing citation direction
  - Lazy-loaded on tab click to avoid unnecessary API calls

## v1.7.0 (2026-02-23)
- Paper Audio Summary: NotebookLM-style podcast generation
  - LLM generates conversational podcast script (two AI hosts)
  - OpenAI-compatible TTS API synthesizes audio (alloy + nova voices)
  - New "Audio" tab on Paper Detail page with play/pause/regenerate
  - Audio cached in /app/data/audio/ for instant replay
  - Background generation with polling status updates

## v1.6.1 (2026-02-23)
- Definitive fix for duplicate tasks (5-layer dedup)
- Global semantic search on Dashboard (v1.6.0)
- Semantic search UI in Knowledge Base (v1.5.1)
- ChromaDB + Bedrock Embed v4 vector search (v1.5.0)
- Paper Comparison View (v1.4.0)
- Literature Review generation (v1.3.0)
- Auto knowledge extraction on every paper (v1.2.0)
- Zombie task recovery (v1.0.1)
- Trending papers 7d/14d/30d (v1.0.0)

## v1.1.0 (2026-02-22)
- Smart Recommendations via Semantic Scholar API
- Radar page: "For You" tab with personalized suggestions
- Enriched TODO roadmap with 9 design inspirations

## v1.0.0 (2026-02-22) 🎉
- Trending Papers: HuggingFace 7d/14d/30d trending with upvote ranking
- Radar page overhaul: Discoveries + Trending tabs, reusable PaperCard
- GET /api/radar/trending?days=N endpoint

## v0.9.x (2026-02-22)
- v0.9.9: S2 rate limit handling, i18n fix, auto-iterate script
- v0.9.8: Manual process button on Radar page
- v0.9.7: Dashboard stats overview panel
- v0.9.6: Auto-sanitize Chinese messages in API responses
- v0.9.5: Configurable startup scan
- v0.9.4: Robust deduplication
- v0.9.3: Radar respects queue capacity
- v0.9.2: Expanded keyword matching, source diversity
- Multi-source results: HuggingFace + arXiv + Semantic Scholar

## v0.9.1 (2026-02-22)
- Async radar processing: non-blocking scan loop
- Papers process in background while radar continues scanning

## v0.9.0 (2026-02-22)
- HuggingFace upvote-based ranking (≥30⬆=98%, ≥10⬆=95%)
- Fetch 50 HF papers sorted by community upvotes
- Show upvote counts on paper cards

## v0.8.x (2026-02-22)
- Radar page: next scan countdown, paper abstract preview on click
- Health endpoint with total_tasks/total_papers stats
- Improved deduplication: checks both KB and task queue
- Task filename shows real paper title
- Dashboard radar panel: "View All →" link

## v0.7.x (2026-02-22)
- Smart hybrid scoring: HF upvotes, S2 citations, keyword pre-filter
- Reduced LLM API calls by ~80%
- Source tags on paper cards

## v0.6.0 (2026-02-22)
- Dedicated /radar management page with live status
- Header nav: Radar button (green accent)
- Manual "Scan Now" with real-time feedback

## v0.5.0 (2026-02-22)
- HuggingFace Daily Papers as 3rd data source
- Cross-paper chat: ask questions across entire knowledge base
- Knowledge Base: "Ask All Papers" button

## v0.4.0 (2026-02-22)
- Full auto pipeline: translate → highlight → knowledge extract
- Semantic Scholar as 2nd data source
- URL upload: paste arXiv link or ID

## v0.3.x (2026-02-22)
- Radar UI panel on Dashboard with scanning animation
- Auto-process top 3 papers per scan
- Pre-download fonts in Docker image
- Auto-cleanup failed radar tasks
- Fix hardcoded Chinese progress messages
- Add favicon

## v0.2.0 (2026-02-22)
- Radar Engine: arXiv auto-scan every hour
- Paper Chat: chat with any paper
- Bark + Lark notification services

## v0.1.0 (2026-02-22)
- Brand rename: EasyPaper → PaperRadar
- i18n: Full English/Chinese UI
- Bilingual knowledge extraction (en/zh)
- Research Insights: 5-dimension cross-paper analysis
- API Token authentication
- Per-user concurrency isolation
- All-in-one Docker image
