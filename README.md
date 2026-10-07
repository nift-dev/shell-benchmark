# Shell Benchmark

Evidence-first Linux shell/runtime experiment: Nift, Bash, Zsh, Fish and Nushell.
No Bash compatibility claim is made for Nift. Scripts and configuration are
idiomatic semantic equivalents, not identical source text.

```sh
python3 scripts/benchmark.py --nift /path/to/pinned/nift \
  --samples 100 --work-samples 10 --warmups 3 --output results/official.json
```

Requires Linux, Python 3.12+, cc, and the five pinned shell executables on PATH.
A C supervisor is compiled in temporary storage before timing. Its latency spans
fork/exec to wait4 completion, excluding Python orchestration/supervisor launch.
RSS is Linux waited-child high-water RSS, not simultaneous aggregate tree RSS.
Do not compare it to the old website suite's sampled aggregate RSS.

## Startup boundaries

- Immediate exit and trivial command: non-interactive bare command evaluation.
- Interactive ready: controlling PTY, compiled forkpty start timestamp through pipe receipt of the first
  prompt. An RC-state command runs afterwards and must yield the expected line.
  This metric excludes Python fork and bridge launch, but includes terminal query
response and pipe-forwarding overhead; it is
  not directly subtractable from the C-supervised invocation metric.
- Login is separate for Bash/Zsh/Fish/Nu. Nift has no separate login mode.
- Every invocation is a fresh process. Repeated prepared HOME/XDG state is reused
  within a scenario; OS caches are uncontrolled. No machine-cold claim is made.

The PTY answers xterm primary-device, cursor-position and background-colour
queries. It detects OSC 133 prompt completion where available, otherwise the
shell's prompt suffix. Terminal query handling affects interactive timing;
results concern this documented terminal model. Configuration or shell changes
which break the oracle stop the run. No arbitrary sleeps determine readiness.
PTY RSS is omitted because prompt timing ends before oracle/teardown accounting. Process-mode
RSS remains available; the post-prompt correctness probe is outside latency.

## RC matrix

Bare uses Bash --noprofile --norc; Zsh -f; Fish --no-config; Nu --no-config-file;
Nift an empty isolated HOME (there is no no-RC CLI switch). Nu's standard library
remains enabled. No time is subtracted from configured startup.

Empty uses normal configuration discovery with empty user files. Light defines
8 environment variables and 8 functions; moderate defines 32 of each. Both
prepend one PATH entry and perform a HOME-existence conditional. The post-prompt
oracle checks an environment value, the conditional and a callable function.
No aliases are included because Nift does not have an equivalent alias facility.
No enormous dotfile collection or external plugin manager is involved.

Generated homes contain Bash .bashrc/.bash_profile; Zsh .zshenv/.zprofile/.zshrc/
.zlogin/.zlogout; Fish XDG config/fish/config.fish; Nu env.nu/config.nu/login.nu;
Nift .niftrc. Bash login profile explicitly sources its synthetic bashrc.
Host user files are never moved, replaced or deleted. Environment variables are
allowlisted; BASH_ENV, ENV, inherited functions, arbitrary XDG/ZDOTDIR and token
variables cannot enter the measured process.

Zsh always reads its compiled system zshenv even with -f. Normal configured and
login cases can read distro-wide files (Bash /etc/profile, distro bashrc; Zsh
/etc/zsh/*; Fish compiled system/vendor configuration; Nu vendor autoload).
Inventory and hash those files on the official machine. Label Bare as minimum
supported **no user configuration**, not universal "no RC". Distro defaults are
part of the Empty/light/moderate normal path and are a disclosed confounder.
A separate Default row is omitted until a reproducible definition adds useful
information beyond these normal-path scenarios.

## Work and correctness

Native sum measures assignments, expansion, arithmetic, iteration and conditions.
External-100 explicitly executes /usr/bin/true 100 times; competitors cannot
substitute a builtin. Short pipeline uses the same printf/tr binaries. Nift uses
structured run()/cmd().pipe() capture in command evaluation, so interpretation
must disclose this difference from a terminal pipeline.
Fish uses native test/math in while loops. Command capture and file roundtrip
are separate rows. Nu uses its native save and Nift its native file API; these
file-write architecture differences are disclosed rather than forced through sh.

Every sample must pass an output/exit oracle. A failed run retains non-publishable
raw evidence and cannot yield summary tables. Samples are interleaved with
rotating shell order; warmups are retained but excluded from summaries. Median,
min/max, p90/p95/p99 and sample counts describe the full retained distribution.
Percentiles use linear interpolation and are descriptive, not confidence bounds.

## Sources for startup rules

- https://www.gnu.org/software/bash/manual/html_node/Bash-Startup-Files.html
- https://zsh.sourceforge.io/Doc/Release/Files.html
- https://fishshell.com/docs/current/cmds/fish.html
- https://www.nushell.sh/book/configuration.html
- Nift src/CLI.cpp, run_script_shell_loop and command dispatcher at the recorded
  Nift source revision; the measured release must pass independent probes.

Status: harness under validation; no local smoke timings are official results.

Use --state application-cold to regenerate HOME/XDG and synthetic RC before
every invocation, outside timing. This resets application files, not OS caches.

Function/string work defines a callable and performs native uppercase/replacement.
File and capture rows are deliberately small, so startup contributes substantially.
Traversal is covered in the scripting suite's recursive fixture; SQLite/structured
runtime work belongs there too. Parallel job control was investigated but is not
in the first timed matrix: Nift's REPL job table, Nu jobs/closures and POSIX async
lists require separate completion/state oracles before they are comparable.
Repeated long pipeline and concurrent-job distributions remain an expansion gap;
the current process row launches 100 children serially and the pipeline row two.
This is a bounded suite, not comprehensive interactive-shell feature coverage.

## Measurement revision 2

The growing Python result heap contaminated initial PTY fork latency. Retain the
original prepared/fresh-home series under diagnostic-python-pty; never quote it
as intrinsic startup. A compiled forkpty bridge now reports CLOCK_MONOTONIC
launch timestamps; the Python reader uses the same clock at first prompt receipt.
Bridge/Python launch is excluded; terminal response/forwarding remains included.

Fresh configured Zsh invokes Ubuntu system compinit and rebuilds a completion
cache on every regenerated HOME. This is intentionally retained normal-path
behaviour, not a reason to suppress system RC or hide the result. Its expensive
startup means the fresh-state series uses 30 measured samples per startup cell;
prepared state uses 100. This sampling policy is frozen before corrected runs.
No already-collected corrected observations are removed.
