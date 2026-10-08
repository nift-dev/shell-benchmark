# Official shell series 20261008-v480

Measured on 8 October 2026 with Nift 4.8.0 development snapshot from `c80c2cd6f4a2e782e861431637af014bb8a0668c`. The measured suite SHA is `e79253d24fd9c74ccc8616186a0a1cd2bbf7e726`. Each run is independent; no historical samples are pooled.

`run-identity.json` freezes source/build/node provenance. `setup.sh`, `smoke.sh` and `official.sh` contain the exact provisioning and measurement commands, excluding credentials and connection details. Official raw JSON retains all measured samples and warmups, correctness, binary/source hashes and machine inventory. Summary JSON regenerates exactly with the suite summarizer. Smoke observations are validation evidence, excluded from official figures.

The scripting `same-node-version-diagnostic.json`, where present, is a separate source-built 4.7.2/4.8.0 investigation with five measured samples and two warmups per case. Both binaries use the same compiler and native build defaults; its samples are never pooled with official results.

Frequency/governor sysfs entries were unavailable on the VM; absence is recorded in `machine-extra.json`. CPU affinity for official measurements is logical CPU 0. The plan has shared virtual CPUs; neighbouring tenants and uncontrolled OS caches remain limitations. `teardown.json` records lifecycle status and subsequently authenticated HTTP 404 verification.
