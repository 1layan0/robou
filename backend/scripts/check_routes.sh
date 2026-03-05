#!/bin/bash
# عرض المسارات المسجلة في الخادم على المنفذ 8000
echo "Routes on http://localhost:8000:"
curl -s http://localhost:8000/openapi.json 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
for p in sorted(d.get('paths', {}).keys()):
    print(' ', p)
" 2>/dev/null || echo " (Could not fetch - is the server running?)"
