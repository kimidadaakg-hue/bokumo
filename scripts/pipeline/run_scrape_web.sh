#!/bin/bash
cd /Volumes/外付けSSD/クロード/bokumo
while true; do
    DONE=$(python3 -c "
import json
try:
    p=json.load(open('scripts/pipeline/scrape_progress_web.json'))
    d=json.load(open('scripts/pipeline/kid_friendly_web.json'))
    print(f'{len(p)}/2438 kid_friendly={len(d)}')
except: print('0/2438')
" 2>/dev/null)
    
    echo "[$(date '+%H:%M:%S')] $DONE — 開始"
    python3 scripts/pipeline/scrape_websites.py 2>&1
    
    TOTAL=$(python3 -c "
import json
p=json.load(open('scripts/pipeline/scrape_progress_web.json'))
print(len(p))
" 2>/dev/null || echo "0")
    
    if [ "$TOTAL" = "2438" ]; then
        echo "[$(date '+%H:%M:%S')] ✅ 完了"
        break
    fi
    echo "[$(date '+%H:%M:%S')] 再開(5秒後)..."
    sleep 5
done
