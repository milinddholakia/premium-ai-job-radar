#!/bin/bash
# Boot up the Premium GenAI Job Radar Web UI
DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-5050}"

echo "================================================================"
echo " Starting Apex GenAI Job Radar Web UI..."
echo " Opening at: http://localhost:${PORT}"
echo "================================================================"

python3 "$DIR/app.py"
