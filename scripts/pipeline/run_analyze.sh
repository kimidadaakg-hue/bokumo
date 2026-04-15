#!/bin/bash
cd /Volumes/外付けSSD/クロード/bokumo
set -a; source .env.local; set +a
export GEMINI_MODEL="gemini-2.5-flash-lite"

while true; do
    DONE=$(python3 -c "
import json
p=json.load(open('scripts/pipeline/analyze_progress.json'))
print(len(p))
" 2>/dev/null || echo "0")

    if [ "$DONE" = "2438" ]; then
        echo "[$(date '+%H:%M:%S')] ✅ 全2438件完了！"
        break
    fi

    KF=$(python3 -c "import json; d=json.load(open('scripts/pipeline/kid_friendly.json')); print(len(d))" 2>/dev/null || echo "0")
    echo "[$(date '+%H:%M:%S')] 進捗: $DONE/2438 | 子連れ: $KF — 開始"

    python3 scripts/pipeline/analyze_reviews.py 2>&1

    echo "[$(date '+%H:%M:%S')] 120秒待機..."
    sleep 120
done
