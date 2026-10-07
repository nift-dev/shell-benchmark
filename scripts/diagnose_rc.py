#!/usr/bin/env python3
"""Independent native-clock RC diagnostics for Bash/Zsh; never subtract from startup."""
import argparse,json,shutil,tempfile,statistics
from pathlib import Path
from campaign_measure import measure,isolated_env,metadata
from suite import prepare,invocation
ROOT=Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--output',required=True);args=a.parse_args()
result=dict(machine=metadata(ROOT),policy='User synthetic RC parse/execute only, no system RC; native clock diagnostics; never subtracted.',jobs=[])
with tempfile.TemporaryDirectory(prefix='rc-body-') as td:
 for shell in ('bash','zsh'):
  exe=shutil.which(shell)
  for level,n in (('light',8),('moderate',32)):
   home=Path(td)/shell/level;prepare(home,shell,level);env=isolated_env(home)
   if shell=='bash':
    code='s=${EPOCHREALTIME/./}; . "$HOME/.bashrc"; e=${EPOCHREALTIME/./}; printf "%s\\n" "$((e-s))"'
   else:
    code='zmodload zsh/datetime; s=$EPOCHREALTIME; . "$ZDOTDIR/.zshrc"; e=$EPOCHREALTIME; printf "%.9f\\n" "$(( (e-s)*1000 ))"'
   code+=f'; [[ "$BENCH_HOME" == yes && "$BENCH_{n-1}" == value{n-1} ]] || exit 1'
   samples=[]
   for i in range(50):
    rec,out,err=measure(invocation(exe,shell,'bare',code=code),home,env)
    if rec['exit_code'] or rec['timeout']:raise SystemExit('RC diagnostic oracle failed')
    value=float(out.strip())/(1000 if shell=='bash' else 1)
    if value<0:raise SystemExit('wall clock moved backwards')
    samples.append(dict(sample=i,rc_body_ms=value,process_ms=rec['wall_ms'],correct=True))
   vals=[s['rc_body_ms'] for s in samples]
   result['jobs'].append(dict(id=shell+'/'+level,samples=samples,median_rc_body_ms=statistics.median(vals),min_rc_body_ms=min(vals),max_rc_body_ms=max(vals)))
Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
print({j['id']:j['median_rc_body_ms'] for j in result['jobs']})
