#!/usr/bin/env python3
"""Certify every synthetic variable/function plus conditional and PATH state."""
import argparse,json,shutil,tempfile
from pathlib import Path
from benchmark import interactive
from campaign_measure import isolated_env,metadata
from suite import prepare,invocation
ROOT=Path(__file__).resolve().parents[1]
def oracle(shell,n):
 expected=''.join(f'value{i}|value{i}|' for i in range(n))+'yes|/benchmark/bin'
 if shell in ('bash','zsh'):
  code='; '.join(f'printf "%s|%s|" "$BENCH_{i}" "$(bench_fn_{i})"' for i in range(n))+'; printf "%s|%s\\n" "$BENCH_HOME" "${PATH%%:*}"'
 elif shell=='fish':
  code='; '.join(f'printf "%s|%s|" $BENCH_{i} (bench_fn_{i})' for i in range(n))+'; printf "%s|%s\\n" $BENCH_HOME $PATH[1]'
 elif shell=='nu':
  terms=[f'$env.BENCH_{i} + "|" + (bench_fn_{i}) + "|"' for i in range(n)]
  code='print ('+' + '.join(terms)+' + $env.BENCH_HOME + "|" + $env.PATH.0)'
 else:
  terms=[f'getenv("BENCH_{i}") + "|" + bench_fn_{i}() + "|"' for i in range(n)]
  code='print('+' + '.join(terms)+' + getenv("BENCH_HOME") + "|" + getenv("PATH").split(":")[0])'
 return code,expected.encode()
a=argparse.ArgumentParser();a.add_argument('--nift',required=True);a.add_argument('--output',required=True);args=a.parse_args()
result=dict(machine=metadata(ROOT),all_state_valid=False,cases=[])
with tempfile.TemporaryDirectory(prefix='rc-certification-') as td:
 for shell in ('bash','zsh','fish','nu','nift'):
  exe=str(Path(args.nift).resolve()) if shell=='nift' else shutil.which(shell)
  for scenario,n in (('light',8),('moderate',32)):
   for login in ((False,) if shell=='nift' else (False,True)):
    home=Path(td)/shell/scenario/str(login);prepare(home,shell,scenario)
    code,expected=oracle(shell,n)
    interactive(invocation(exe,shell,scenario,True,login),home,isolated_env(home),code,expected,timeout=30)
    result['cases'].append(dict(shell=shell,scenario=scenario,login=login,variables=n,functions=n,conditional=True,path=True,correct=True))
result['all_state_valid']=True
Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
print('Certified complete synthetic RC state in',len(result['cases']),'cases.')
