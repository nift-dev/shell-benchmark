"""Auditable shell adapters and semantically equivalent synthetic configuration."""
from pathlib import Path

SHELLS=('bash','zsh','fish','nu','nift')
SCENARIOS=('bare','empty','light','moderate')


def config(shell,level):
    n={'bare':0,'empty':0,'light':8,'moderate':32}[level]
    lines=[]
    for i in range(n):
        if shell in ('bash','zsh'): lines += [f'export BENCH_{i}=value{i}',f'bench_fn_{i}() {{ printf "%s\\n" value{i}; }}']
        elif shell=='fish': lines += [f'set -gx BENCH_{i} value{i}',f'function bench_fn_{i}; echo value{i}; end']
        elif shell=='nu': lines += [f'$env.BENCH_{i} = "value{i}"',f'def bench_fn_{i} [] {{ "value{i}" }}']
        else: lines += [f'setenv("BENCH_{i}", "value{i}")',f'fn(bench_fn_{i}()) {{ return "value{i}" }}']
    # Same environment mutation and conditional check. No aliases: Nift's shell
    # has no matching alias primitive; function definitions are comparable.
    if n:
        if shell in ('bash','zsh'): lines += ['export PATH="/benchmark/bin:$PATH"','if [ -d "$HOME" ]; then export BENCH_HOME=yes; fi']
        elif shell=='fish': lines += ['set -gx PATH /benchmark/bin $PATH','if test -d $HOME; set -gx BENCH_HOME yes; end']
        elif shell=='nu': lines += ['$env.PATH = (["/benchmark/bin"] | append $env.PATH)','if ($env.HOME | path exists) { $env.BENCH_HOME = "yes" }']
        else: lines += ['setenv("PATH", "/benchmark/bin:" + getenv("PATH"))','if(exists(getenv("HOME"))) { setenv("BENCH_HOME", "yes") }']
    return '\n'.join(lines)+'\n'


def prepare(home,shell,scenario):
    home=Path(home)
    home.mkdir(parents=True,exist_ok=True)
    if scenario=='bare': return
    body=config(shell,scenario)
    if shell=='bash': files={'.bashrc':body,'.bash_profile':'. "$HOME/.bashrc"\n'}
    elif shell=='zsh': files={'.zshenv':'','.zprofile':'','.zshrc':body,'.zlogin':'','.zlogout':''}
    elif shell=='fish': files={'config/fish/config.fish':body}
    elif shell=='nu': files={'config/nushell/env.nu':'','config/nushell/config.nu':body,'config/nushell/login.nu':''}
    else: files={'.niftrc':body}
    for rel,content in files.items():
        p=home/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content)


def invocation(exe,shell,scenario,interactive=False,login=False,code=None):
    cmd=[exe]
    if shell=='nift':
        if login: raise ValueError('Nift has no login mode')
        return cmd if interactive else cmd+['-e',code or '']
    if scenario=='bare':
        cmd += {'bash':['--noprofile','--norc'],'zsh':['-f'],'fish':['--no-config'],'nu':['--no-config-file']}[shell]
    if login: cmd += ['--login' if shell in ('bash','fish','nu') else '-l']
    if interactive: cmd += ['-i']
    if code is not None: cmd += ['-c',code]
    return cmd


def rc_oracle(shell,scenario):
    n={'bare':0,'empty':0,'light':8,'moderate':32}[scenario]
    if not n: return {'nift':'print("RC_OK")','nu':'print "RC_OK"'}.get(shell,'echo RC_OK'), b'RC_OK'
    if shell in ('bash','zsh'): code='printf "%s:%s:" "$BENCH_0" "$BENCH_HOME"; bench_fn_0'
    elif shell=='fish': code='printf "%s:%s:" $BENCH_0 $BENCH_HOME; bench_fn_0'
    elif shell=='nu': code='print ($env.BENCH_0 + ":" + $env.BENCH_HOME + ":" + (bench_fn_0))'
    else: code='print(getenv("BENCH_0") + ":" + getenv("BENCH_HOME") + ":" + bench_fn_0())'
    return code,b'value0:yes:value0'


def workloads(shell):
    # External programs are absolute paths, so no competitor can substitute a
    # native true/printf/tr implementation. Native-language loops remain native.
    loops={
      'bash':'s=0; for ((i=1;i<=1000;i++)); do s=$((s+i)); done; echo "$s"',
      'zsh':'s=0; for ((i=1;i<=1000;i++)); do s=$((s+i)); done; echo "$s"',
      'fish':'set s 0; set i 1; while test $i -le 1000; set s (math $s + $i); set i (math $i + 1); end; echo $s',
      'nu':'mut s = 0; for i in 1..1000 { $s = $s + $i }; print $s',
      'nift':'s := 0; i := 1; while(i <= 1000) { s += i; i += 1 }; print(s)'}
    # Fish uses native test/math and command substitution; no external range helper.
    external={
      'bash':'for ((i=0;i<100;i++)); do /usr/bin/true || exit 1; done; echo 100',
      'zsh':'for ((i=0;i<100;i++)); do /usr/bin/true || exit 1; done; echo 100',
      'fish':'set i 0; while test $i -lt 100; /usr/bin/true; or exit 1; set i (math $i + 1); end; echo $i',
      'nu':'for i in 1..100 { ^/usr/bin/true; if $env.LAST_EXIT_CODE != 0 { exit 1 } }; print 100',
      'nift':'i := 0; while(i < 100) { r := run("/usr/bin/true"); if(r.exit_code != 0) { print("FAIL") }; i += 1 }; print(i)'}
    pipeline=' /usr/bin/printf abc | /usr/bin/tr a-z A-Z'
    if shell=='nu': pipeline='^/usr/bin/printf abc | ^/usr/bin/tr a-z A-Z'
    if shell=='nift': pipeline='r := cmd("/usr/bin/printf", "abc").pipe(cmd("/usr/bin/tr", "a-z", "A-Z")).run(); print(r.stdout)'
    capture={
      'bash':'x=$(/usr/bin/printf capture); echo "$x"',
      'zsh':'x=$(/usr/bin/printf capture); echo "$x"',
      'fish':'set x (/usr/bin/printf capture); echo $x',
      'nu':'let x = (^/usr/bin/printf capture); print $x',
      'nift':'r := run("/usr/bin/printf", "capture"); print(r.stdout)'}
    fileio='/usr/bin/printf payload > roundtrip.txt; /usr/bin/cat roundtrip.txt'
    if shell=='nu': fileio='^/usr/bin/printf payload | save -f roundtrip.txt; ^/usr/bin/cat roundtrip.txt'
    if shell=='nift': fileio='r := run("/usr/bin/printf", "payload"); f := file("roundtrip.txt"); f.open("w"); f.write(r.stdout); f.save(); f.close(); r = run("/usr/bin/cat", "roundtrip.txt"); print(r.stdout)'
    return [('command-capture',capture[shell],b'capture'),('file-roundtrip',fileio,b'payload'),('native-sum',loops[shell],b'500500'),('external-100',external[shell],b'100'),('short-pipeline',pipeline,b'ABC')]
