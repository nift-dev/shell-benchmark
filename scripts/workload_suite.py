"""Frozen workload definitions. Generated sources are retained verbatim in each run."""
from suite import SHELLS
PAYLOAD='0123456789abcdef'*7+'0123456789abcde\n' # exactly 128 bytes
KEEP='keep-'+('k'*58)+'\n' # exactly 64 bytes

def cases():
 out=[]
 def add(key,category,classification,n=0,shape='flat',heavy=False,**kw):out.append(dict(id=key,category=category,classification=classification,count=n,shape=shape,samples=5 if heavy else 10,warmups=1 if heavy else 2,**kw))
 for n in (1000,10000,100000):
  add(f'create-empty-{n}','filesystem','end-to-end',n,heavy=n==100000,operation='create-empty')
  add(f'delete-selected-{n}','filesystem','end-to-end',n,heavy=n==100000,operation='delete')
 add('create-small-100000','filesystem','end-to-end',100000,heavy=True,operation='create-small')
 add('delete-tree-100000','filesystem','end-to-end',100000,'tree',True,operation='delete')
 for key,op in [('copy-small-10000','copy'),('rename-selected-10000','move'),('concat-small-10000','concat'),('metadata-10000','metadata'),('traverse-100000','traverse')]:add(key,'filesystem','end-to-end',100000 if op=='traverse' else 10000,heavy=op=='traverse',operation=op)
 add('log-filter-group','text','orchestration',operation='log',lines=200000)
 for n in (1,10,100,1000):add(f'processes-{n}','processes','orchestration',n,operation='process')
 for n in (2,4,8):add(f'pipeline-{n}','pipelines','orchestration',n,operation='pipeline')
 for key,n in [('arithmetic',20000),('function-calls',10000),('fibonacci-mod',1000),('string-transform',5000)]:add(key,'algorithms','runtime-native',n,operation=key)
 add('source-tree-report','real-world','orchestration',10000,'tree',operation='report')
 add('selected-cleanup','real-world','end-to-end',1000,'tree',operation='cleanup')
 return out

def nift_write(path,text):return f'f := file({path}); f.open("w"); f.write({text}); f.save(); f.close()'

def source(c,shell):
 op,n=c['operation'],c['count']; traditional=shell in ('bash','zsh','fish');nu=shell=='nu';nift=shell=='nift'
 payload='"'+PAYLOAD.replace('\n','\\n')+'"'
 if op in ('create-empty','create-small','delete','copy','move','concat','cleanup'):
  text='""' if op=='create-empty' else payload
  if nift:
   start='paths := open("targets.txt").trim().split("\\n"); '
   body={'create-empty':'touch(p)','create-small':nift_write('p',text),'delete':'remove(p)','copy':'copy(p, "copied/" + p.split("/").last())','move':'move(p, "moved/" + p.split("/").last())','concat':'dest.write(open(p))','cleanup':'remove(p)'}[op]
   if op=='delete':return start+'remove(paths); print("OK")'
   code=start+('dest := file("output"); dest.open("w"); ' if op=='concat' else '')+'for(p : paths) { '+body+' }; '
   if op=='concat':code+='dest.save(); dest.close(); '
   if op=='cleanup':code+='make_dir("report"); '+'for(p : open("outputs.txt").split("\\n")) { move(p, "report/" + p.split("/").last()) }; '+nift_write('"report/summary"',f'"deleted={n} archived=200"')+'; '
   return code+'print("OK")'
  if nu:
   body={'create-empty':'"" | save --raw $p','create-small':payload+' | save --raw $p','delete':'rm $p','copy':'cp $p ("copied/" + ($p | path basename))','move':'mv $p ("moved/" + ($p | path basename))','cleanup':'rm $p'}.get(op)
   if op=='delete':return 'let paths = (open --raw targets.txt | lines); rm ...$paths; print OK'
   if op=='concat':return 'open --raw targets.txt | lines | each {|p| open --raw $p } | str join | save --raw output; print OK'
   code='for p in (open --raw targets.txt | lines) { '+body+' }; '
   if op=='cleanup':code+=f'mkdir report; let outputs = (open --raw outputs.txt | lines); mv ...$outputs report; "deleted={n} archived=200" | save --raw report/summary; '
   return code+'print OK'
  if op in ('delete','copy','move','concat','cleanup'):
   command={'delete':'/usr/bin/rm --','copy':'/usr/bin/cp -t copied --','move':'/usr/bin/mv -t moved --','concat':'/usr/bin/cat --','cleanup':'/usr/bin/rm --'}[op]
   code='/usr/bin/xargs -0 -a targets.nul '+command+(' > output' if op=='concat' else '')
   if op=='cleanup':code+=f'; /usr/bin/mkdir report; /usr/bin/xargs -0 -a outputs.nul /usr/bin/mv -t report --; printf \"deleted={n} archived=200\" > report/summary'
   return code+'; echo OK'
  body=': > "$p"' if op=='create-empty' else "printf '%s' "+"'"+PAYLOAD+"' > \"$p\""
  if shell=='fish':body='printf %s '+("''" if op=='create-empty' else "'"+PAYLOAD+"'")+' > "$p"';return 'while read -l p; '+body+'; end < targets.txt; echo OK'
  return 'while IFS= read -r p || [ -n "$p" ]; do '+body+'; done < targets.txt; echo OK'
 if op=='report':
  awk='{e=$3; sub(/^.*[.]/,"",e); if($3!="total") {c[e]++;b[e]+=$2;l[e]+=$1}} END{print "cc",c["cc"],b["cc"],l["cc"];print "dat",c["dat"],b["dat"],l["dat"];print "md",c["md"],b["md"],l["md"];print "py",c["py"],b["py"],l["py"]}'
  if nift:
   import json
   return 'r := cmd("/usr/bin/find", "files", "-type", "f", "-print0").pipe(cmd("/usr/bin/xargs", "-0", "/usr/bin/wc", "-lc")).pipe(cmd("/usr/bin/awk", '+json.dumps(awk)+')).run(); print(r.stdout)'
  prefix='^' if nu else ''
  return prefix+'/usr/bin/find files -type f -print0 | '+prefix+'/usr/bin/xargs -0 /usr/bin/wc -lc | '+prefix+"/usr/bin/awk '"+awk+"'"
 if op in ('metadata','traverse','report'):
  if nift:
   start='paths := '+('open("targets.txt").trim().split("\\n")' if op=='metadata' else 'ls("files/**/*.dat")')+'; '
   if op=='traverse':return start+'print(paths.size())'
   return start+'total := 0; for(p : paths) { total += stat(p).size }; '+('print(paths.size()); ' if op=='report' else '')+'print(total)'
  if nu:
   if op=='metadata':return 'let total = (open --raw targets.txt | lines | each {|p| ls $p | get size | first | into int } | math sum); print $total'
   if op=='traverse':return 'print (glob "files/**/*.dat" | length)'
   code='let items = (glob "files/**/*.dat" | each {|p| ls $p | first }); '
   return code+('print ($items | length)' if op=='traverse' else 'print ($items | length); print ($items | get size | into int | math sum)')
  if op=='metadata':return "/usr/bin/xargs -0 -a targets.nul /usr/bin/stat --printf='%s\\n' -- | /usr/bin/awk '{s+=$1} END{printf \"%.0f\\n\",s}'"
  return "/usr/bin/find files -type f -name '*.dat' -printf '%s\\n' | /usr/bin/awk '{n++;s+=$1} END{print n"+(';printf "%.0f\\n",s' if op=='report' else '')+"}'"
 if op=='log':
  # Same external engines and pipeline stages for every shell; neither is credited as a native text engine.
  commands=[('/usr/bin/grep',['^ERROR']),('/usr/bin/awk',['{print $2}']),('/usr/bin/sort',[]),('/usr/bin/uniq',['-c'])]
  if nift:
   commands[0][1].append('logs.txt')
   return 'r := '+'.pipe('.join('cmd("'+exe+'"'+''.join(', "'+a.replace('"','\\"')+'"' for a in args)+')' for exe,args in commands)+')'*(len(commands)-1)+'.run(); print(r.stdout)'
  return ' | '.join(('^' if nu else '')+exe+' '+ ' '.join("'"+a+"'" for a in args)+( ' logs.txt' if i==0 else '') for i,(exe,args) in enumerate(commands))
 if op=='process':
  if nift:return f'i := 0; while(i < {n}) {{ r := run("/usr/bin/true"); if(r.exit_code != 0) {{ print("FAIL") }}; i += 1 }}; print(i)'
  if nu:return f'for i in 1..{n} {{ ^/usr/bin/true; if $env.LAST_EXIT_CODE != 0 {{ exit 1 }} }}; print {n}'
  if shell=='fish':return f'set i 0; while test $i -lt {n}; /usr/bin/true; or exit 1; set i (math $i + 1); end; echo $i'
  return f'for ((i=0;i<{n};i++)); do /usr/bin/true || exit 1; done; echo {n}'
 if op=='pipeline':
  if nift:return 'r := cmd("/usr/bin/printf", "pipeline").'+'.'.join('pipe(cmd("/usr/bin/cat"))' for _ in range(n-1))+'.run(); print(r.stdout)'
  return ('^' if nu else '')+'/usr/bin/printf pipeline' + (' | '+('^' if nu else '')+'/usr/bin/cat')*(n-1)
 if op=='arithmetic':
  if nift:return f's := 0; i := 1; while(i <= {n}) {{ s += i; i += 1 }}; print(s)'
  if nu:return f'mut s = 0; for i in 1..{n} {{ $s = $s + $i }}; print $s'
  if shell=='fish':return f'set s 0; set i 1; while test $i -le {n}; set s (math $s + $i); set i (math $i + 1); end; echo $s'
  return f's=0; for ((i=1;i<={n};i++)); do s=$((s+i)); done; echo $s'
 if op=='function-calls':
  if nift:return f'fn(inc(x)) {{ return x+1 }}; s := 0; i := 0; while(i < {n}) {{ s = inc(s); i += 1 }}; print(s)'
  if nu:return f'def inc [x: int] {{ $x + 1 }}; mut s = 0; for i in 1..{n} {{ $s = (inc $s) }}; print $s'
  if shell=='fish':return f'function inc; set -g s (math $s + 1); end; set s 0; set i 0; while test $i -lt {n}; inc; set i (math $i + 1); end; echo $s'
  return f'inc() {{ s=$((s+1)); }}; s=0; for ((i=0;i<{n};i++)); do inc; done; echo $s'
 if op=='fibonacci-mod':
  if nift:return f'a := 0; b := 1; i := 0; while(i < {n}) {{ t := (a+b)%1000000; a=b; b=t; i+=1 }}; print(a)'
  if nu:return f'mut a = 0; mut b = 1; for i in 1..{n} {{ let t = (($a + $b) mod 1000000); $a = $b; $b = $t }}; print $a'
  if shell=='fish':return f'set a 0; set b 1; set i 0; while test $i -lt {n}; set t (math "($a + $b) % 1000000"); set a $b; set b $t; set i (math $i + 1); end; echo $a'
  return f'a=0; b=1; for ((i=0;i<{n};i++)); do t=$(((a+b)%1000000)); a=$b; b=$t; done; echo $a'
 if op=='string-transform':
  if nift:return f's := "alpha"; i := 0; while(i < {n}) {{ s="alpha".to_upper().replace("A","a"); i+=1 }}; print(s)'
  if nu:return f'mut s = ""; for i in 1..{n} {{ $s = ("alpha" | str upcase | str replace -a A a) }}; print $s'
  if shell=='fish':return f'set i 0; while test $i -lt {n}; set s (string upper alpha | string replace -a A a); set i (math $i + 1); end; echo $s'
  transform='s=${s^^}' if shell=='bash' else 's=${(U)s}'
  return f'for ((i=0;i<{n};i++)); do s=alpha; {transform}; s=${{s//A/a}}; done; echo $s'
 raise ValueError(op)
