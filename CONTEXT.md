# PaperRadar — Project Context (for AI continuity)

## Identity
- **Project**: PaperRadar (formerly EasyPaper)
- **GitHub**: https://github.com/neosun100/PaperRadar
- **Docker Hub**: neosun/paperradar
- **Current Version**: 1.0.0
- **Model for Kiro**: claude-opus-4.6-1m

## Architecture
- **All-in-one Docker image**: nginx (frontend :80) + uvicorn (backend :8000) + supervisord
- **Frontend**: React 18 + TypeScript + Vite + Tailwind + shadcn/ui + react-i18next
- **Backend**: FastAPI + Python 3.11 + pdf2zh + PyMuPDF + httpx + SQLModel (SQLite)
- **Source**: /home/neo/upload/EasyPaper (local path, repo name is PaperRadar)

## Key Files
- `Dockerfile` — All-in-one multi-stage build (node → python+nginx+supervisor)
- `backend/app/services/radar_engine.py` — Radar: arXiv + Semantic Scholar + HuggingFace
- `backend/app/services/knowledge_extractor.py` — Bilingual knowledge extraction
- `backend/app/services/paper_chat.py` — Single + cross-paper chat
- `backend/app/services/insights_generator.py` — Cross-paper analysis
- `backend/app/services/notification.py` — Bark + Lark Card 2.0
- `backend/app/api/routes.py` — Upload, URL upload, tasks, queue, radar APIs
- `backend/app/api/knowledge_routes.py` — Knowledge, chat, insights, export APIs
- `backend/app/core/config.py` — Config model (llm, processing, radar, notification, security)
- `frontend/src/i18n/en.json` + `zh.json` — All UI translations
- `frontend/src/lib/biText.ts` — Bilingual field resolver
- `frontend/src/pages/Dashboard.tsx` — Main page with radar panel, stats, upload
- `frontend/src/pages/RadarPage.tsx` — Dedicated radar management
- `frontend/src/pages/ResearchInsights.tsx` — Cross-paper analysis
- `frontend/src/pages/PaperDetail.tsx` — Paper detail with chat tab

## Secrets (NEVER commit to Git)
- Real config at `/home/neo/easypaper-secrets/config.yaml` (mounted read-only)
- Docker image contains only empty placeholder config
- `backend/config/config.yaml` is in `.gitignore`

## Build & Deploy Workflow
```bash
cd /home/neo/upload/EasyPaper
# Frontend build
cd frontend && npx tsc --noEmit && npm run build && cd ..
# Docker build
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

## Rules
1. All UI text must use i18n (t() function), never hardcode Chinese or English
2. All knowledge extraction outputs bilingual {en, zh} JSON
3. No secrets in Git or Docker image — only in runtime volume mount
4. No file size or page limits
5. No auto-cleanup — all results permanent
6. Per-user concurrency (3 per API key)
7. Radar: check queue capacity before adding tasks (≥3 active → scan only)
8. Test TypeScript (tsc --noEmit) before every Docker build
9. Always push both Docker Hub AND GitHub after each feature
