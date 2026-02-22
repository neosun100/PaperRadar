# PaperRadar Changelog

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
