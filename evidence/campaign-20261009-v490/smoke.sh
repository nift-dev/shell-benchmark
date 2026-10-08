#!/bin/bash
set -euo pipefail
suite=$1
export PATH=/opt/campaign/tools/bin:/usr/local/bin:/usr/bin:/bin
cd /opt/campaign/"$suite"-benchmark
[ "$(git status --porcelain)" = "" ]
[ "$(/opt/campaign/tools/bin/nift version)" = "Nift v4.9.0" ]
if [ "$suite" = shell ]; then
 taskset -c 0 python3 scripts/verify_rc.py --nift /opt/campaign/tools/bin/nift --output /opt/campaign/evidence/rc-certification.json
 taskset -c 0 python3 scripts/calibrate.py --output /opt/campaign/evidence/calibration.json
 taskset -c 0 python3 scripts/diagnose_rc.py --output /opt/campaign/evidence/rc-body.json
 taskset -c 0 python3 scripts/benchmark.py --nift /opt/campaign/tools/bin/nift --samples 5 --work-samples 5 --warmups 1 --output /opt/campaign/evidence/smoke-shell-repeated.json
 taskset -c 0 python3 scripts/benchmark.py --nift /opt/campaign/tools/bin/nift --samples 5 --work-samples 5 --warmups 1 --state application-cold --output /opt/campaign/evidence/smoke-shell-fresh.json
 python3 scripts/summarize.py --input /opt/campaign/evidence/smoke-shell-repeated.json --output /opt/campaign/evidence/smoke-shell-summary.json
 python3 scripts/summarize.py --input /opt/campaign/evidence/smoke-shell-fresh.json --output /opt/campaign/evidence/smoke-fresh-summary.json
else
 taskset -c 0 python3 scripts/campaign.py --nift /opt/campaign/tools/bin/nift --families sanity/noop,sanity/output,sanity/loops,sanity/function-calls,arrays-strings-hash/scan,arrays-strings-hash/frequency-count,arrays-strings-hash/sliding-window,arrays-strings-hash/sort-index,arrays-strings-hash/map-set,dynamic-programming/fibonacci,graphs-trees-search/bfs,structured-data/json-parse,structured-data/json-transform,structured-data/json-traverse,filesystem/traverse --samples 5 --warmups 1 --timeout 180 --output /opt/campaign/evidence/smoke-scripting.json
 python3 scripts/summarize.py --input /opt/campaign/evidence/smoke-scripting.json --output /opt/campaign/evidence/smoke-scripting-summary.json
fi
printf 'SMOKE_PASS\n'
