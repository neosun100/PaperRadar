#!/bin/bash
# PaperRadar Auto-Iteration Script
# Usage: ./auto-iterate.sh [max_iterations]

MAX_ITERATIONS=${1:-100}
ITERATION=0
PROJECT_DIR="/home/neo/upload/EasyPaper"
MODEL="claude-opus-4.6-1m"

echo "🛰️ PaperRadar Auto-Iteration"
echo "Model: $MODEL"
echo "Max iterations: $MAX_ITERATIONS"
echo "=================================================="

PROMPT="You are continuing development of PaperRadar.

FIRST: Read CONTEXT.md and TODO.md to understand the project fully.

Then pick the highest priority incomplete item from TODO.md and:
1. Implement it carefully (read existing code first)
2. Test: cd frontend && npx tsc --noEmit && npm run build
3. Build Docker: docker build -t neosun/paperradar:NEW_VERSION -t neosun/paperradar:latest -f Dockerfile .
4. Deploy: docker stop paperradar; docker rm paperradar; docker run -d --name paperradar -p 9201:80 -p 9200:8000 -v /home/neo/easypaper-secrets/config.yaml:/app/config/config.yaml:ro -v easypaper-data:/app/data -v easypaper-tmp:/app/tmp neosun/paperradar:NEW_VERSION
5. Verify: curl health endpoint
6. Push: docker push neosun/paperradar:NEW_VERSION && docker push neosun/paperradar:latest
7. Git: git add -A && git commit -m descriptive_message && git push origin main
8. Update CHANGELOG.md

CRITICAL RULES (read CONTEXT.md for full details):
- All UI text must use i18n t() function
- Never commit secrets to Git or Docker image
- Test TypeScript before Docker build
- Push to BOTH Docker Hub (neosun/paperradar) AND GitHub
- Secrets config at /home/neo/easypaper-secrets/config.yaml (mount read-only)
- Source code at /home/neo/upload/EasyPaper
- Pre-download fonts and models in Dockerfile"

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    ITERATION=$((ITERATION + 1))
    echo ""
    echo "=== Iteration $ITERATION / $MAX_ITERATIONS — $(date) ==="

    cd "$PROJECT_DIR"

    HOME=~/.kiro-homes/account3 kiro-cli chat \
        --trust-all-tools \
        --model "$MODEL" \
        "$PROMPT"

    EXIT_CODE=$?
    echo "--- Iteration $ITERATION completed (exit: $EXIT_CODE) ---"

    if [ $EXIT_CODE -ne 0 ]; then
        echo "⚠️ Iteration failed, waiting 60s before retry..."
        sleep 60
    else
        echo "✅ Iteration $ITERATION successful"
        sleep 10
    fi
done

echo "🏁 Auto-iteration complete: $ITERATION iterations"
