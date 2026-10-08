#!/usr/bin/env python3
"""Additive shell workloads using the existing direct-process supervisor.

Fixture reconstruction/preflight and strict postconditions are outside timing.
Only generated, validated relative manifest paths are used by adapters.
"""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,time
from pathlib import Path
from campaign_measure import measure,summary,metadata,identity,isolated_env
from suite import SHELLS,invocation
from workload_suite import cases,source,PAYLOAD,KEEP
ROOT=Path(__file__).resolve().parents[1]

def digest(b):return hashlib.sha256(b).hexdigest()
def safe(root,relative):
 p=Path(relative)
 if p.is_absolute() or '..' in p.parts or not p.parts:raise ValueError('unsafe fixture path')
 dest=(root/p).resolve()
 if not dest.is_relative_to(root.resolve()) or dest==root.resolve():raise ValueError('fixture path escaped root')
 return dest

def paths(c):
 n=c['count'];d=max(20000 if n==100000 else n//5,1)
 # Every sixth object is a keeper. Targets/keepers share directories and names.
 targets=[];keepers=[]
 for i in range(n+d):
  keep=i%6==0 and len(keepers)<d or len(targets)==n
  rel=('files/'+(f'd{i//max(1,(n+d+99)//100):03d}/' if c['shape']=='tree' else '')+f'obj-{i:06d}-'+('keep' if keep else 'target')+('.dat' if c['operation']!='report' or keep else ('.py','.cc','.md')[i%3]))
  (keepers if keep else targets).append(rel)
 assert len(targets)==n and len(keepers)==d
 return targets,keepers

def content(c,rel):
 if '-keep.' in rel:return KEEP.encode()
 if c['operation']=='report':return {'.py':b'x = 1\n'*16,'.cc':b'int x;\n'*16,'.md':b'# Note\n'*16}[Path(rel).suffix]
 return PAYLOAD.encode()
def prepare(root,c):
 targets,keepers=paths(c) if c['category'] in ('filesystem','real-world') else ([],[])
 checks={};keeper_set=set(keepers)
 for rel in targets+keepers:
  p=safe(root,rel);p.parent.mkdir(parents=True,exist_ok=True)
  data=content(c,rel)
  if rel in keeper_set or c['operation'] not in ('create-empty','create-small'):p.write_bytes(data)
  if rel in keeper_set:
   st=p.stat();checks[rel]=(digest(data),st.st_mode,st.st_mtime_ns,st.st_ino)
 (root/'targets.txt').write_text('\n'.join(targets)+'\n' if targets else '')
 (root/'targets.nul').write_bytes(b''.join(p.encode()+b'\0' for p in targets))
 if c['operation']=='cleanup':
  (root/'outputs').mkdir()
  items=[f'outputs/result-{i:04d}.txt' for i in range(200)]
  for name in items:(root/name).write_bytes(PAYLOAD.encode())
  (root/'outputs.txt').write_text('\n'.join(items))
  (root/'outputs.nul').write_bytes(b''.join(x.encode()+b'\0' for x in items))
 for name in ('copied','moved'):(root/name).mkdir()
 if c['operation']=='log':(root/'logs.txt').write_text(''.join(('ERROR' if i%4==0 else 'INFO')+' worker'+str(i%7)+' message\n' for i in range(c['lines'])))
 initial={str(p.relative_to(root)) for p in (root/'files').rglob('*') if p.is_file()} if (root/'files').exists() else set()
 assert initial==set(keepers if c['operation'] in ('create-empty','create-small') else targets+keepers), 'fixture preflight count/path mismatch'
 return targets,keepers,checks

def expected(c):
 op,n=c['operation'],c['count']
 if op in ('create-empty','create-small','delete','copy','move','concat','cleanup'):return b'OK'
 if op=='metadata':return str(n*128).encode()
 if op=='report':
  targets,keepers=paths(c);rows=[]
  for ext in ('.cc','.dat','.md','.py'):
   files=[p for p in targets+keepers if Path(p).suffix==ext]
   rows.append(f'{ext[1:]} {len(files)} {sum(len(content(c,p)) for p in files)} {sum(content(c,p).count(bytes([10])) for p in files)}')
  return '\n'.join(rows).encode()
 if op=='traverse':
  d=max(20000 if n==100000 else n//5,1)
  return (str(n+d)+ ('\n'+str(n*128+d*64) if op=='report' else '')).encode()
 if op=='arithmetic':return str(n*(n+1)//2).encode()
 if op=='fibonacci-mod':
  a,b=0,1
  for _ in range(n):a,b=b,(a+b)%1000000
  return str(a).encode()
 if op in ('process','function-calls'):return str(n).encode()
 if op=='pipeline':return b'pipeline'
 if op=='string-transform':return b'aLPHa'
 if op=='log':
  counts=[0]*7
  for i in range(0,c['lines'],4):counts[i%7]+=1
  return '\n'.join(f'{v:7d} worker{i}' for i,v in enumerate(counts)).encode()
 raise ValueError(op)

def verify(root,c,fixture,out):
 targets,keepers,checks=fixture;op=c['operation']
 if op=='log':
  # GNU uniq pads counts; whitespace is presentation rather than data semantics.
  ok=[x.split() for x in out.strip().splitlines()]==[x.split() for x in expected(c).splitlines()]
 else:ok=out.strip()==expected(c)
 if not ok:raise AssertionError('output oracle failed: '+repr(out[:200]))
 for rel in keepers:
  p=safe(root,rel);st=p.stat();assert (digest(p.read_bytes()),st.st_mode,st.st_mtime_ns,st.st_ino)==checks[rel],'keeper altered'
 for rel in targets:
  p=safe(root,rel)
  if op in ('delete','move','cleanup'):assert not p.exists(),'target survived'
  else:
   assert p.is_file(),'target missing'
   assert p.read_bytes()==(b'' if op=='create-empty' else content(c,rel)),'target content differs'
  if op in ('copy','move'):
   q=root/('copied' if op=='copy' else 'moved')/p.name;assert q.read_bytes()==PAYLOAD.encode()
 observed={str(p.relative_to(root)) for p in (root/'files').rglob('*') if p.is_file()} if (root/'files').exists() else set()
 assert observed==set(keepers if op in ('delete','move','cleanup') else targets+keepers),'unexpected filesystem path'
 if op in ('copy','move'):assert len(list((root/('copied' if op=='copy' else 'moved')).iterdir()))==len(targets)
 if op=='concat':assert (root/'output').read_bytes()==PAYLOAD.encode()*len(targets)
 if op=='cleanup':
  assert (root/'report/summary').read_text()==f'deleted={len(targets)} archived=200'
  assert not list((root/'outputs').iterdir())
  assert len(list((root/'report').glob('result-*.txt')))==200
  assert all(p.read_bytes()==PAYLOAD.encode() for p in (root/'report').glob('result-*.txt'))
 return {'targets':len(targets),'distractors':len(keepers),'unexpected_survivors':0,'unexpected_deletions':0,'all_distractor_content_metadata_unchanged':True,'manifest_sha256':digest('\n'.join(targets).encode()),'oracle':'all paths and bytes checked; keeper mode/mtime/inode checked'}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--nift',required=True);ap.add_argument('--output',required=True);ap.add_argument('--shells',default=','.join(SHELLS));ap.add_argument('--cases');ap.add_argument('--smoke',action='store_true');ap.add_argument('--timeout',type=float,default=180);a=ap.parse_args()
 definitions=[c for c in cases() if not a.cases or c['id'] in a.cases.split(',')];jobs=[];tools={}
 for shell in a.shells.split(','):
  exe=str(Path(a.nift).resolve()) if shell=='nift' else shutil.which(shell)
  if not exe:raise SystemExit('missing '+shell)
  tools[shell]={**identity(exe,['--version']),'executable':exe}
  for c in definitions:
   code=source(c,shell)
   implementation=('native filesystem API' if shell in ('nift','nu') else 'shell redirection' if c['operation'].startswith('create') else 'common find → xargs/wc → awk pipeline' if c['operation']=='report' else 'batched GNU utilities') if c['category'] in ('filesystem','real-world') else ('native shell code' if c['classification']=='runtime-native' else 'common external utilities')
   if c['operation']=='report':implementation='common find → xargs/wc → awk pipeline'
   jobs.append(dict(id=c['id']+'/'+shell,shell=shell,case=c['id'],definition=c,implementation=implementation,source=code,source_sha256=digest(code.encode()),oracle_sha256=digest(expected(c)),samples=[]))
 # Direct common external baselines: same fixtures and oracles, no shell launch.
 for c in definitions:
  if c['operation'] not in ('delete','copy','move','concat'):continue
  exe={'delete':'/usr/bin/rm','copy':'/usr/bin/cp','move':'/usr/bin/mv','concat':'/usr/bin/cat'}[c['operation']]
  if c['operation']=='concat':continue # output redirection requires a shell; don't mislabel it direct.
  command=['/usr/bin/xargs','-0','-a','targets.nul',exe]+(['-t','copied' if c['operation']=='copy' else 'moved'] if c['operation']!='delete' else [])+['--']
  jobs.append(dict(id=c['id']+'/external-baseline',shell='external-baseline',case=c['id'],definition=c,implementation='direct GNU xargs + '+exe,command=command,source_sha256=digest(json.dumps(command).encode()),oracle_sha256=digest(b''),samples=[]))
 result={'schema':1,'kind':'shell-workloads','machine':metadata(ROOT),'tools':tools,'external_tools':{x:identity('/usr/bin/'+x,['-W','version'] if x=='awk' else ['--version']) for x in ('xargs','rm','cp','mv','cat','find','stat','awk','grep','sort','uniq','true')},'policy':'fresh fixture per sample; OS caches uncontrolled; C-supervised fork/exec-to-exit; all oracles outside timing; rotated case/participant order; every observation retained','smoke':a.smoke,'definitions':definitions,'fixtures':{},'exclusions':[{'case':c['id'],'shell':s,'reason':'no native filesystem deletion API; end-to-end batched GNU rm result is published instead'} for c in definitions if c['operation']=='delete' for s in ('bash','zsh','fish')],'jobs':jobs,'publishable':False}
 if not a.smoke and result['machine']['dirty']:raise RuntimeError('official workloads require a clean suite checkout')
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 def save():dest.write_text(json.dumps(result,indent=2)+'\n')
 rounds=1 if a.smoke else max(c['samples']+c['warmups'] for c in definitions)
 for turn in range(rounds):
  for j in jobs[turn%len(jobs):]+jobs[:turn%len(jobs)]:
   c=j['definition']
   if not a.smoke and turn>=c['samples']+c['warmups']:continue
   with tempfile.TemporaryDirectory(prefix='shell-workload-') as td:
    root=Path(td);fixture=prepare(root,c);env=isolated_env(root/'home');command=j.get('command') or invocation(tools[j['shell']]['executable'],j['shell'],'bare',code=j['source'])
    j['invocation']=command
    rec,out,err=measure(command,root,env,a.timeout)
    rec.update(round=turn,warmup=False if a.smoke else turn<c['warmups'],correct=False)
    j['samples'].append(rec)
    try:
     assert rec['exit_code']==0 and not rec['timeout'],repr(err[:400])
     fixture_key=c['shape']+'/'+str(c['count'])
     if fixture[0] and fixture_key not in result['fixtures']:
      result['fixtures'][fixture_key]={'targets':fixture[0],'distractors':fixture[1],'content_recipes':{k:{'bytes':len(v),'sha256':digest(v)} for k,v in {'small-target':PAYLOAD.encode(),'empty-target':b'','keeper':KEEP.encode(),'source.py':b'x = 1\n'*16,'source.cc':b'int x;\n'*16,'source.md':b'# Note\n'*16}.items()}}
     j['fixture_identity']={'key':fixture_key,'shape':c['shape'],'manifest_sha256':digest('\n'.join(fixture[0]).encode())}
     assert j['shell']!='external-baseline' or out.strip()==b'', 'baseline unexpected stdout'
     validation=verify(root,c,fixture,b'OK' if j['shell']=='external-baseline' else out);rec['validation']=validation;rec['correct']=True
    except Exception as e:result['failure']=j['id']+': '+str(e);save();raise RuntimeError(result['failure']) from e
   print(j['id']+' PASS',flush=True)
  save()
 for j in jobs:j['summary']=summary([x for x in j['samples'] if not x['warmup']])
 result['publishable']=True;save();print('WORKLOADS_PASS',flush=True)
if __name__=='__main__':main()
