#!/bin/bash
# scrape_websites.py を完了するまで自動再起動するラッパー
cd /Volumes/外付けSSD/クロード/bokumo

MAX_RETRIES=50
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    RETRY=$((RETRY + 1))
    
    # 現在の進捗を表示
    PROGRESS=$(python3 -c "
import json
p=json.load(open('scripts/pipeline/scrape_progress.json'))
d=json.load(open('scripts/pipeline/kid_friendly.json'))
print(f'{len(p)}/2153 kid_friendly={len(d)}')
" 2>/dev/null || echo "0/2153")
    
    echo "[$(date '+%H:%M:%S')] 試行 $RETRY/$MAX_RETRIES | 進捗: $PROGRESS"
    
    # 実行
    python3 scripts/pipeline/scrape_websites.py 2>&1
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$(date '+%H:%M:%S')] ✅ 正常完了"
        break
    fi
    
    echo "[$(date '+%H:%M:%S')] ⚠️ 終了コード $EXIT_CODE — 5秒後に再開..."
    sleep 5
done

echo "[$(date '+%H:%M:%S')] 完了 (試行 $RETRY 回)"
