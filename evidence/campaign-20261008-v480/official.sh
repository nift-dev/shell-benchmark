#!/bin/bash
set -euo pipefail
suite=$1
export PATH=/opt/campaign/tools/bin:/usr/local/bin:/usr/bin:/bin
cd /opt/campaign/"$suite"-benchmark
[ "$(git status --porcelain)" = "" ]
date -u +%FT%TZ > /opt/campaign/evidence/official-start.txt
if [ "$suite" = shell ]; then
 taskset -c 0 python3 scripts/benchmark.py --nift /opt/campaign/tools/bin/nift --samples 100 --work-samples 10 --warmups 3 --output /opt/campaign/evidence/shell-repeated.json
 taskset -c 0 python3 scripts/benchmark.py --nift /opt/campaign/tools/bin/nift --samples 30 --work-samples 10 --warmups 3 --state application-cold --output /opt/campaign/evidence/shell-application-cold.json
 python3 scripts/summarize.py --input /opt/campaign/evidence/shell-repeated.json --output /opt/campaign/evidence/shell-repeated-summary.json
 python3 scripts/summarize.py --input /opt/campaign/evidence/shell-application-cold.json --output /opt/campaign/evidence/shell-fresh-summary.json
 taskset -c 0 python3 scripts/verify_rc.py --nift /opt/campaign/tools/bin/nift --output /opt/campaign/evidence/rc-certification-after.json
else
 taskset -c 0 python3 scripts/campaign.py --nift /opt/campaign/tools/bin/nift --families sanity/noop,sanity/output,sanity/loops,sanity/function-calls,arrays-strings-hash/scan,arrays-strings-hash/frequency-count,arrays-strings-hash/sliding-window,arrays-strings-hash/sort-index,arrays-strings-hash/map-set,dynamic-programming/fibonacci,graphs-trees-search/bfs,structured-data/json-parse,structured-data/json-transform,structured-data/json-traverse,filesystem/traverse --samples 10 --warmups 2 --timeout 180 --output /opt/campaign/evidence/scripting.json
 python3 scripts/summarize.py --input /opt/campaign/evidence/scripting.json --output /opt/campaign/evidence/scripting-summary.json
fi
python3 scripts/test_measurement.py
[ "$(git status --porcelain)" = "" ]
date -u +%FT%TZ > /opt/campaign/evidence/official-end.txt
printf 'OFFICIAL_PASS\n'
