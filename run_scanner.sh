#!/bin/zsh
# run_scanner.sh — wrapper for cron execution
# 4:00 AM IST daily scan

export PATH="/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/cron_run.log"

echo "========================================" >> "$LOG"
echo "Cron run: $(date '+%Y-%m-%d %H:%M:%S %Z')" >> "$LOG"

/usr/bin/python3 "$SCRIPT_DIR/premium_ai_job_scanner.py" >> "$LOG" 2>&1
EXIT_CODE=$?

echo "Exit code: $EXIT_CODE" >> "$LOG"
echo "========================================" >> "$LOG"
