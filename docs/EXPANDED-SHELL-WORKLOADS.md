# Additive shell workload layer

The startup/configuration harness and schema 2 remain unchanged. `scripts/workload_campaign.py` uses the existing C fork/exec/wait4 supervisor and isolated environment, with a separate schema-1 workload file. No Nift source is changed.

27 representative cases, all five shells, plus six direct GNU baselines: 141 jobs. Ordinary cases retain 10 measured observations + 2 warmups; the five heavyweight 100k cases retain 5 + 1. Including baselines, the workload layer has 1,275 measured observations and 255 warmups. Existing prepared/fresh startup/work matrices retain their original 6,580 + 456. Order rotates; no samples are discarded.

## Fairness classes

- Runtime-native: arithmetic (20k), callable increments (10k), iterative modular Fibonacci (1k), string transformation (5k). Fish uses builtin math/test/string; builtin substitution/pipelines still have shell overhead.
- Orchestration: 1/10/100/1000 identical `/usr/bin/true` children; 2/4/8-stage printf/cat pipelines; a 200k-line grep/awk/sort/uniq log pipeline; a synthetic source-tree find/xargs/wc/awk report grouped by extension with counts, bytes and lines. These share external engines; they do not rank five text engines.
- End-to-end: selected create/delete, copy, rename, concat, metadata, traversal, cleanup. Bash/Zsh/Fish use redirection/batched GNU utilities; Nift/Nu use native APIs where available. Nift file save is atomic temporary-file replacement; this extra work remains timed. Traditional shells have explicit native-deletion exclusions, rather than fake native results.
- External baseline: direct GNU xargs→rm/cp/mv on the identical fixture, excluding shell startup. Never subtract these observations from a shell result.

## Filesystem fixtures and safety

Targets and keepers have deterministic interleaved names and exact retained manifests. At 100k, there are 100,000 targets and 20,000 keepers. Flat shape uses one directory; tree shape uses 100 directories, **each mixing both sets**. Neither whole-root deletion nor target-parent deletion can pass the oracle. Target content is 128 bytes; keeper content 64 bytes. Empty creation is separate. Every sample reconstructs its fixture outside timing and checks initial path/count state. OS caches are not flushed.

Copy/move use 10,000 selected small files. Concat preserves manifest order and verifies the entire output. Metadata totals selected bytes; traversal counts all matching files. Cleanup deletes 1,000 exact targets, preserves 200 keepers, moves 200 outputs and writes a summary. Source report uses `.py`, `.cc`, `.md` and keeper `.dat` files, with full deterministic source contents.

All generated paths are relative, canonical-root checked, and reject traversal/absolute/symlink escapes. Adapters use only these generated paths in a unique temporary cwd. No user-supplied deletion paths or real user dotfiles enter a run. Batch deletion avoids ARG_MAX; huge-argv capability tests and parallel jobs are outside this bounded first extension.

Every post-run oracle verifies all target bytes/absence, every keeper's bytes/mode/mtime/inode, exact inventory, destination bytes/count and report output. Timeouts kill the process group and leave non-publishable evidence. Tests deliberately damage keepers, leave targets, corrupt copies, create stray paths and attempt path escapes.

## Reproduction

Install pins in `docs/TOOL-PINS.json`. Put pinned Fish/Nu on PATH.

```
python3 scripts/test_measurement.py
python3 scripts/test_workloads.py
python3 scripts/workload_campaign.py --nift /path/to/nift --smoke --output /tmp/workload-smoke.json
# Clean frozen checkout; CPU 0; serial execution:
taskset -c 0 python3 scripts/workload_campaign.py --nift /path/to/nift --output /tmp/shell-workloads.json
python3 scripts/validate_workloads.py --input /tmp/shell-workloads.json --output /tmp/workload-validation.json
```

Raw results retain generated sources, exact invocations, source/oracle hashes, fixture manifests, every warmup and measured sample, correctness records, environment/binary identities and distributions. `validate_workloads.py` enforces definitions/counts and recomputes every summary field exactly. JSON schema describes the raw shape, including incomplete/non-publishable runs.
