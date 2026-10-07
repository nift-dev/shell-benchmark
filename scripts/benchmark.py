#!/usr/bin/env python3
import argparse,errno,hashlib,json,os,re,select,shutil,signal,subprocess,tempfile,time
from pathlib import Path
from campaign_measure import measure,isolated_env,metadata,identity,summary
from suite import SHELLS,SCENARIOS,prepare,invocation,rc_oracle,workloads
ROOT=Path(__file__).resolve().parents[1]
PTY_DIR=tempfile.TemporaryDirectory(prefix='pty-supervisor-')
PTY_EXE=str(Path(PTY_DIR.name)/'measure-pty')
subprocess.run(['cc','-O2','-Wall','-Wextra',str(Path(__file__).with_name('measure_pty.c')),'-lutil','-o',PTY_EXE],check=True)
ANSI=re.compile(rb'\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[78=>]')


def interactive(cmd,cwd,env,code,expected,timeout=15):
    # Compiled forkpty bridge: shell launch is independent of Python's growing
    # heap. Both clocks are Linux CLOCK_MONOTONIC; pipe receipt is the endpoint.
    report_dir=tempfile.TemporaryDirectory(prefix='pty-report-')
    report=Path(report_dir.name)/'start.json'
    proc=subprocess.Popen([PTY_EXE,str(report),*cmd],cwd=cwd,env=env,
                          stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    fd=proc.stdout.fileno()
    start=None
    deadline=time.monotonic()+timeout; data=b''; ready=None; checked=False
    marker=b'BENCH_COMMAND_DONE'
    try:
        while time.monotonic()<deadline:
            if not select.select([fd],[],[],.05)[0]: continue
            try: chunk=os.read(fd,65536)
            except OSError as e:
                if e.errno==errno.EIO: break
                raise
            if not chunk: break
            # Emulate the minimal xterm capabilities queried by modern Fish/Nu.
            # These replies are harness work; document PTY terminal model.
            for query,reply in ((b'\x1b[0c',b'\x1b[?1;2c'),(b'\x1b[c',b'\x1b[?1;2c'),(b'\x1b[6n',b'\x1b[1;1R'),(b'\x1b]11;?',b'\x1b]11;rgb:0000/0000/0000\x1b\\')):
                if query in chunk: os.write(proc.stdin.fileno(),reply)
            if start is None:
                start=json.loads(report.read_text())['start_ns']
            data+=chunk
            plain=ANSI.sub(b'',data).rstrip(b'\r\n ')

            if ready is None and (b'\x1b]133;B' in chunk or re.search(rb'(?:\$|#|%|>|\xe2\x9d\xaf) *$',plain)):
                ready=(time.perf_counter_ns()-start)/1e6
                # PTY echoes typed input: match actual result line independently.
                os.write(proc.stdin.fileno(),(code+'\n').encode()); data=b''
            elif ready is not None:
                lines=ANSI.sub(b'',data).replace(b'\r',b'').split(b'\n')
                if expected in [line.strip() for line in lines]:
                    checked=True; break
        if not checked: raise RuntimeError('interactive prompt/RC oracle failed: '+cmd[0]+' '+repr(data[-500:]))
        # Kill after validation. Startup latency ends at prompt; teardown and
        # oracle command execution are outside that metric.
        proc.terminate(); proc.wait(timeout=5)
        return dict(wall_ms=ready,peak_rss_kib=None,correct=True,
                    metric='compiled-forkpty-to-first-prompt',exit_code=None,
                    teardown='SIGTERM bridge kills child process group after oracle; RSS omitted')
    finally:
        if proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill();proc.wait()
        proc.stdin.close();proc.stdout.close();proc.stderr.close()
        report_dir.cleanup()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--nift',required=True); ap.add_argument('--samples',type=int,default=100)
    ap.add_argument('--work-samples',type=int,default=10); ap.add_argument('--warmups',type=int,default=3)
    ap.add_argument('--shells',default=','.join(SHELLS)); ap.add_argument('--output',required=True)
    ap.add_argument('--state',choices=['repeated','application-cold'],default='repeated')
    ap.add_argument('--modes',default='process,interactive,work')
    a=ap.parse_args()
    if a.samples<5 or a.work_samples<5: ap.error('minimum five samples')
    shells=a.shells.split(','); modes=a.modes.split(','); tools={}; jobs=[]
    for shell in shells:
        exe=str(Path(a.nift).resolve()) if shell=='nift' else shutil.which(shell)
        if not exe: raise SystemExit('missing shell: '+shell)
        tools[shell]=identity(exe,['--version'])
        if 'process' in modes:
            for name,code,expected in [('immediate-exit','',b''),('trivial-command',{'nift':'print("OK")','nu':'print "OK"'}.get(shell,'echo OK'),b'OK')]:
                # Empty Bash command must be an explicit ':'; empty Nu is valid.
                if not code and shell in ('bash','zsh','fish'): code='exit 0'
                jobs.append(dict(id=f'{shell}/bare/{name}',shell=shell,scenario='bare',
                                 command=invocation(exe,shell,'bare',code=code),expected=expected,samples=[]))
        if 'interactive' in modes:
            for scenario in SCENARIOS:
                for login in ((False,) if shell=='nift' else (False,True)):
                    code,expected=rc_oracle(shell,scenario)
                    jobs.append(dict(id=f'{shell}/{scenario}/interactive'+('-login' if login else ''),
                                     shell=shell,scenario=scenario,command=invocation(exe,shell,scenario,True,login),
                                     code=code,expected=expected,interactive=True,samples=[]))
        if 'work' in modes:
            for name,code,expected in workloads(shell):
                jobs.append(dict(id=f'{shell}/bare/{name}',shell=shell,scenario='bare',
                                 command=invocation(exe,shell,'bare',code=code),expected=expected,samples=[],work=True))
    result=dict(schema=2,machine=metadata(ROOT),tools=tools,jobs=[],publishable=False,
                policy='fresh processes; allowlisted environment; isolated HOME/XDG; OS caches uncontrolled',
                samples=a.samples,work_samples=a.work_samples,warmups=a.warmups,state=a.state)
    dest=Path(a.output); dest.parent.mkdir(parents=True,exist_ok=True)
    def save():
        result['jobs']=[{k:v for k,v in j.items() if k not in ('expected','code')} for j in jobs]
        dest.write_text(json.dumps(result,indent=2)+'\n')
    with tempfile.TemporaryDirectory(prefix='shell-campaign-') as td:
        homes={}
        for j in jobs:
            key=(j['shell'],j['scenario'],j['id'].split('/')[-1])
            home=Path(td)/'/'.join(key)
            prepare(home,*key[:2]); homes[key]=home
        for round_no in range(a.warmups+max(a.samples,a.work_samples)):
            for j in jobs[round_no%len(jobs):]+jobs[:round_no%len(jobs)]:
                if round_no>=a.warmups+(a.work_samples if j.get('work') else a.samples): continue
                home=homes[(j['shell'],j['scenario'],j['id'].split('/')[-1])]
                if a.state=='application-cold':
                    shutil.rmtree(home,ignore_errors=True); prepare(home,j['shell'],j['scenario'])
                env=isolated_env(home)
                try:
                    if j.get('interactive'): rec=interactive(j['command'],home,env,j['code'],j['expected'])
                    else:
                        rec,out,err=measure(j['command'],home,env)
                        rec['correct']=rec['exit_code']==0 and not rec['timeout'] and out.strip()==j['expected']
                        if not rec['correct']: raise RuntimeError(j['id']+' incorrect: '+repr(out)+repr(err))
                    rec['round']=round_no; rec['warmup']=round_no<a.warmups
                    j['samples'].append(rec)
                except Exception as e:
                    result['failure']=str(e); save(); raise
            save(); print(f'round {round_no+1}',flush=True)
    for j in result['jobs']: j['summary']=summary([r for r in j['samples'] if not r['warmup']])
    result['publishable']=True
    dest.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__': main()
