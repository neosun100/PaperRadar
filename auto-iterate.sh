#!/bin/bash
# PaperRadar Auto-Iteration Script
# Runs Kiro CLI in a loop, each iteration continues development
# Usage: ./auto-iterate.sh [max_iterations]

MAX_ITERATIONS=${1:-10}
ITERATION=0
PROJECT_DIR="/home/neo/upload/EasyPaper"

echo "🛰️ PaperRadar Auto-Iteration — max $MAX_ITERATIONS iterations"
echo "=================================================="

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    ITERATION=$((ITERATION + 1))
    echo ""
    echo "=== Iteration $ITERATION / $MAX_ITERATIONS — $(date) ==="
    
    cd "$PROJECT_DIR"
    
    kiro-cli chat \
        --no-interactive \
        --trust-all-tools \
        --resume \
        "Continue iterating on PaperRadar. Check TODO.md for next tasks. Pick the highest priority incomplete item, implement it, test it, build Docker image, push to Docker Hub (neosun/paperradar) and GitHub. Then update TODO.md and CHANGELOG.md. Be thorough but fast. After completing one feature, commit with a descriptive message."
    
    EXIT_CODE=$?
    echo "--- Iteration $ITERATION completed (exit: $EXIT_CODE) ---"
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo "⚠️ Iteration failed, waiting 30s before retry..."
        sleep 30
    else
        echo "✅ Iteration $ITERATION successful"
        sleep 5
    fi
done

echo ""
echo "🏁 Auto-iteration complete: $ITERATION iterations"
