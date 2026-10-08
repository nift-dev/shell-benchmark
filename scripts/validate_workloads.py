#!/usr/bin/env python3
"""Recompute all distributions and enforce the frozen workload/result contract."""
import argparse,json,hashlib
from pathlib import Path
from campaign_measure import summary
from workload_suite import cases,SHELLS
from workload_campaign import paths,expected,digest

def validate(d):
 assert d['schema']==1 and d['kind']=='shell-workloads' and d['publishable'] is True
 definitions={x['id']:x for x in cases()};assert d['jobs']
 if not d['smoke']:assert not d['machine']['dirty'] and d['machine']['cpu_affinity']==[0]
 for j in d['jobs']:
  c=j['definition'];assert c==definitions[j['case']];rows=j['samples'];assert rows and all(r['correct'] and r['exit_code']==0 and not r['timeout'] for r in rows)
  measured=[r for r in rows if not r['warmup']];assert len(measured)==(1 if d['smoke'] else c['samples']);assert sum(r['warmup'] for r in rows)==(0 if d['smoke'] else c['warmups'])
  assert summary(measured)==j['summary']
  assert j['source_sha256']==digest(j['source'].encode() if 'source' in j else json.dumps(j['command']).encode())
  assert j['oracle_sha256']==digest(b'' if j['shell']=='external-baseline' else expected(c))
  if c['category'] in ('filesystem','real-world'):
   targets,keepers=paths(c);fixture=d['fixtures'][j['fixture_identity']['key']];assert targets==fixture['targets'] and keepers==fixture['distractors'];assert j['fixture_identity']['manifest_sha256']==digest('\n'.join(targets).encode())
   for r in rows:assert r['validation']['targets']==len(targets) and r['validation']['distractors']==len(keepers) and r['validation']['all_distractor_content_metadata_unchanged'] and r['validation']['unexpected_deletions']==r['validation']['unexpected_survivors']==0
 return {'jobs':len(d['jobs']),'measured':sum(not r['warmup'] for j in d['jobs'] for r in j['samples']),'warmups':sum(r['warmup'] for j in d['jobs'] for r in j['samples']),'summaries':'all fields exactly recomputed','correctness':'all samples passed frozen output/fixture oracles'}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output');a=ap.parse_args();p=Path(a.input);d=json.loads(p.read_text());v=validate(d)
 if a.output:Path(a.output).write_text(json.dumps({**v,'raw_sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2)+'\n')
 print(json.dumps(v))
