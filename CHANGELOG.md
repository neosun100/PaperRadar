# PaperRadar Changelog

## v0.8.1 (2026-02-22)
- Radar paper preview: click to expand abstract
- Improved deduplication: checks both KB and task queue
- Task filename shows real paper title

## v0.8.0 (2026-02-22)
- Radar page: next scan countdown, paper status badges
- Health endpoint: total_tasks and total_papers stats
- Dashboard radar panel: "View All →" link

## v0.7.x (2026-02-22)
- Smart hybrid scoring: HF=95%, S2 high-cite=90%, keyword pre-filter
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
