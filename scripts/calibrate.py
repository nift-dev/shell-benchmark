#!/usr/bin/env python3
"""Retain measurement floor and demonstrate PTY independence from Python heap."""
import argparse,json,subprocess,tempfile
from pathlib import Path
from benchmark import interactive
from campaign_measure import measure,isolated_env,metadata,summary
ROOT=Path(__file__).resolve().parents[1]
SOURCE='#include <stdio.h>\nint main(void){char s[4096];printf("$ ");fflush(stdout);while(fgets(s,sizeof(s),stdin)){puts("RC_OK");fflush(stdout);}return 0;}\n'
a=argparse.ArgumentParser();a.add_argument('--output',required=True);args=a.parse_args()
result=dict(machine=metadata(ROOT),policy='Calibration is disclosed, never subtracted from shell results.',source=SOURCE,jobs=[])
with tempfile.TemporaryDirectory(prefix='calibration-') as td:
 root=Path(td);src=root/'probe.c';exe=root/'probe';src.write_text(SOURCE)
 subprocess.run(['cc','-O2',str(src),'-o',str(exe)],check=True)
 env=isolated_env(root/'home')
 for kind in ('process-floor','pty-small-heap','pty-128MiB-heap'):
  allocation=bytearray(128*1024*1024) if kind.endswith('128MiB-heap') else None
  rows=[]
  for i in range(50):
   if kind=='process-floor':
    rec,out,err=measure(['/usr/bin/true'],root,env);rec['correct']=rec['exit_code']==0 and out==b''
   else:rec=interactive([str(exe)],root,env,'probe',b'RC_OK')
   rec['sample']=i;rows.append(rec)
  result['jobs'].append(dict(id=kind,samples=rows,summary=summary(rows)))
  del allocation
Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
print({j['id']:j['summary']['median_ms'] for j in result['jobs']})
