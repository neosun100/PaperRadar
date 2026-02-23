# PaperRadar — Project Context (for AI continuity)

## Identity
- **Project**: PaperRadar (formerly EasyPaper)
- **GitHub**: https://github.com/neosun100/PaperRadar
- **Docker Hub**: neosun/paperradar
- **Current Version**: 2.6.0
- **Kiro Model**: claude-opus-4.6-1m

## Architecture
- **All-in-one Docker image**: nginx (frontend :80) + uvicorn (backend :8000) + supervisord
- **Frontend**: React 18 + TypeScript + Vite + Tailwind + shadcn/ui + react-i18next
- **Backend**: FastAPI + Python 3.11 + pdf2zh + PyMuPDF + httpx + SQLModel (SQLite) + ChromaDB
- **Vector DB**: ChromaDB (embedded, persistent at /app/data/vectordb)
- **Embedding**: Via LLM API /embeddings endpoint (configured in config.yaml, NOT in code)
- **Source**: /home/neo/upload/EasyPaper (local path, repo name is PaperRadar)

## Key Files
- `Dockerfile` — All-in-one multi-stage build (node → python+nginx+supervisor), pre-downloads fonts+ONNX model
- `backend/app/main.py` — FastAPI app, startup: zombie recovery, re-queue, radar, vector init
- `backend/app/services/radar_engine.py` — Radar: arXiv + Semantic Scholar + HuggingFace, smart scoring
- `backend/app/services/knowledge_extractor.py` — Bilingual knowledge extraction, auto vector indexing
- `backend/app/services/vector_search.py` — ChromaDB + embedding API, semantic search, RAG context
- `backend/app/services/paper_chat.py` — Single + cross-paper + RAG chat
- `backend/app/services/insights_generator.py` — Cross-paper analysis (5 dimensions)
- `backend/app/services/literature_review.py` — Auto literature review generation
- `backend/app/services/document_processor.py` — pdf2zh translate/simplify, auto knowledge extraction on completion
- `backend/app/services/audio_summary.py` — Paper audio summary: LLM script + TTS synthesis
- `backend/app/services/notification.py` — Bark (iOS) + Lark (Card 2.0)
- `backend/app/api/routes.py` — Upload, URL upload, tasks, queue, radar, trending, recommendations
- `backend/app/api/knowledge_routes.py` — Knowledge, chat, compare, search, insights, review, export
- `backend/app/api/deps.py` — Auth: Bearer token → server LLM, X-LLM headers → BYOK, get_client_id
- `backend/app/core/config.py` — Config: llm (with embedding_model), processing, radar, notification, security
- `frontend/src/i18n/en.json` + `zh.json` — All UI translations
- `frontend/src/lib/biText.ts` — Bilingual field resolver
- `frontend/src/pages/Dashboard.tsx` — Main: radar panel, stats, upload, URL upload, semantic search
- `frontend/src/pages/RadarPage.tsx` — Radar: discoveries, trending (7d/14d/30d), recommendations (3 tabs)
- `frontend/src/pages/ResearchInsights.tsx` — Cross-paper analysis + literature review
- `frontend/src/pages/KnowledgeBase.tsx` — Papers, semantic search, cross-paper chat, paper comparison
- `frontend/src/pages/PaperDetail.tsx` — Paper detail with chat tab (6 tabs total)
- `frontend/src/pages/KnowledgeGraph.tsx` — Force-directed graph

## Completed Features (v1.8.0)
- Citation Network Visualization (S2 API, force-directed graph on Paper Detail)
- Paper Audio Summary (NotebookLM-style podcast via LLM + TTS)
- 3-source radar (arXiv + Semantic Scholar + HuggingFace Daily Papers)
- HuggingFace upvote ranking, trending 7d/14d/30d
- Smart hybrid scoring (HF upvotes, S2 citations, keyword pre-filter)
- Auto-process top 3 papers per scan (translate → highlight → knowledge extract → vector index)
- Queue capacity control (≥3 active → scan only)
- 5-layer deduplication (KB + tasks + filenames + titles + session)
- Zombie task recovery on restart
- ChromaDB vector search with Bedrock Cohere Embed v4 (1536-dim)
- Semantic search UI on Dashboard and Knowledge Base
- RAG-enhanced cross-paper chat
- Paper comparison (select 2-5 papers → AI comparison)
- Literature review generation (structured Markdown, downloadable)
- Research Insights (field overview, method comparison, timeline, gaps, connections)
- Paper Chat (single paper Q&A)
- Smart Recommendations (Semantic Scholar API)
- PDF translate/simplify + AI highlighting
- URL upload (paste arXiv link)
- Bilingual knowledge extraction (en/zh)
- Knowledge graph (force-directed)
- Multi-format export (JSON, BibTeX, Obsidian, CSL-JSON, CSV)
- i18n (English/Chinese), dark mode, favicon
- API Token auth, per-user concurrency, permanent storage
- Bark + Lark notification (code ready, configure keys to activate)
- All-in-one Docker with pre-downloaded fonts + ONNX model

## Secrets (NEVER commit to Git)
- Real config at `/home/neo/easypaper-secrets/config.yaml` (mounted read-only)
- Docker image contains only empty placeholder config
- `backend/config/config.yaml` is in `.gitignore`
- Embedding model, LLM keys, API tokens — all in secrets config only

## Build & Deploy Workflow
```bash
cd /home/neo/upload/EasyPaper
# Frontend
cd frontend && npx tsc --noEmit && npm run build && cd ..
# Docker
docker stop paperradar && docker rm paperradar
docker build -t neosun/paperradar:VERSION -t neosun/paperradar:latest -f Dockerfile .
# Deploy
docker run -d --name paperradar -p 9201:80 -p 9200:8000 \
  -v /home/neo/easypaper-secrets/config.yaml:/app/config/config.yaml:ro \
  -v easypaper-data:/app/data -v easypaper-tmp:/app/tmp \
  neosun/paperradar:VERSION
# Push
docker push neosun/paperradar:VERSION && docker push neosun/paperradar:latest
git add -A && git commit -m "message" && git push origin main
```

## Critical Rules
1. All UI text must use i18n (t() function), never hardcode Chinese or English
2. All knowledge extraction outputs bilingual {en, zh} JSON
3. No secrets in Git or Docker image — only in runtime volume mount
4. No file size or page limits
5. No auto-cleanup — all results permanent
6. Per-user concurrency (3 per API key)
7. Radar: check queue capacity before adding tasks (≥3 active → scan only)
8. Test TypeScript (tsc --noEmit) before every Docker build
9. Always push both Docker Hub AND GitHub after each feature
10. Pre-download fonts and ONNX model in Dockerfile
11. Auto-sanitize any Chinese progress messages in API responses
12. Vector index papers automatically on knowledge extraction completion

## TODO Priority (next items)
ALL ITEMS COMPLETED! 🎉 See TODO.md for potential future enhancements.
