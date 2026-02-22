#!/bin/bash
# PaperRadar Auto-Iteration Script
# Uses claude-opus-4.6-1m with full project context
# Usage: ./auto-iterate.sh [max_iterations]

MAX_ITERATIONS=${1:-5000}
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
2. Test: run 'cd frontend && npx tsc --noEmit && npm run build'
3. Build Docker: docker build -t neosun/paperradar:NEW_VERSION -t neosun/paperradar:latest -f Dockerfile .
4. Deploy and verify: docker run with secrets volume mount, check health endpoint
5. Push: docker push + git add -A + git commit + git push origin main
6. Update CHANGELOG.md with what you did

CRITICAL RULES (read CONTEXT.md for full details):
- All UI text must use i18n t() function
- Never commit secrets to Git
- Test TypeScript before Docker build
- Push to BOTH Docker Hub (neosun/paperradar) AND GitHub
- Secrets config at /home/neo/easypaper-secrets/config.yaml (mount read-only)
- Source code at /home/neo/upload/EasyPaper"

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    ITERATION=$((ITERATION + 1))
    echo ""
    echo "=== Iteration $ITERATION / $MAX_ITERATIONS — $(date) ==="
    
    cd "$PROJECT_DIR"
    
    kiro-cli chat \
        --no-interactive \
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

echo ""
echo "🏁 Auto-iteration complete: $ITERATION iterations"
