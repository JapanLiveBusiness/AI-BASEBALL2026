#!/bin/bash

set -e

REPO_DIR="/opt/hawks-ai"
LOG_FILE="/opt/hawks-ai/github_backup.log"

cd "$REPO_DIR"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$LOG_FILE"

git add .

if git diff --cached --quiet; then
    echo "No changes" >> "$LOG_FILE"
    exit 0
fi

git commit -m "Auto backup $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE" 2>&1
git push origin main >> "$LOG_FILE" 2>&1

echo "Backup completed" >> "$LOG_FILE"
echo >> "$LOG_FILE"
