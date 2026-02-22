# TODO — EasyPaper Optimization Roadmap

A systematic list of optimization opportunities identified during comprehensive code review and functional testing.

---

## 🔴 High Priority

### Dead Code Cleanup
- [ ] Remove unused backend modules: `pdf_translator.py`, `rewriter.py`, `pdf_parser.py`, `pdf_builder.py`, `block_classifier.py`, `layout_analyzer.py` — these are legacy files superseded by the pdf2zh integration
- [ ] Remove unused frontend pages: `Login.tsx`, `Register.tsx` — not wired into routes
- [ ] Remove unused backend auth modules: `auth.py`, `user.py`, `security.py` — auth system exists but is NOT connected to the app

### Configuration
- [ ] Remove redundant config example file — both `config.example.yaml` and `config.yaml.example` exist; keep only one
- [ ] Rename `package.json` name from `pdf-simplifier-ui` to `easypaper-ui` (old project name artifact)

### Reliability
- [ ] Improve knowledge extraction JSON parsing — LLM sometimes returns malformed JSON, causing retries; add more robust parsing/retry logic
- [ ] Add error handling for stuck tasks — old tasks can remain in "rewriting 30%" state if the process crashes mid-way; add a cleanup mechanism

---

## 🟡 Medium Priority

### Code Quality
- [ ] Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` throughout backend — `utcnow()` is deprecated in Python 3.12+
- [ ] Fix thread-safety issue: `os.environ` mutation in `document_processor.py` is not thread-safe; use a proper configuration mechanism instead
- [ ] Add `LICENSE` file to the repository root (README references MIT but no LICENSE file exists)

### Frontend
- [ ] Add loading states for knowledge extraction (currently no visual feedback during extraction)
- [ ] Add error toast notifications for failed API calls
- [ ] Improve mobile responsiveness for the Reader dual-pane view

### Backend
- [ ] Add request validation for upload endpoint (file size limits, PDF format verification)
- [ ] Add rate limiting for LLM-dependent endpoints
- [ ] Add health check endpoint (`GET /api/health`)

---

## 🟢 Low Priority / Nice-to-Have

### Features
- [ ] Support batch PDF upload
- [ ] Add paper search/filter in knowledge base
- [ ] Add flashcard statistics dashboard (review history, retention rate)
- [ ] Support more target languages beyond Chinese for translation
- [ ] Add PDF annotation/note-taking in the Reader view

### DevOps
- [ ] Add backend unit tests (currently no test coverage)
- [ ] Add frontend component tests
- [ ] Add Docker health checks in `docker-compose.yml`
- [ ] Add `.env.example` for environment variable documentation

### Documentation
- [ ] Add CONTRIBUTING.md with development setup guide
- [ ] Add architecture diagram to README
- [ ] Document the knowledge extraction prompt format for customization
