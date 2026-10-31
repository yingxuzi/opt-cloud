#!/usr/bin/env python3
"""Select only a verified same-server profile for slot launches; retain original fallback."""
import hashlib,json,os,re,queue,signal,subprocess,sys,time,threading
from pathlib import Path
DATA=Path(os.environ.get('VPNGATE_DATA_DIR','/data'))
REAL='/usr/sbin/openvpn'
def read(p,d=None):
    try:return json.loads(Path(p).read_text())
    except Exception:return d

def atomic(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_name(p.name+'.'+str(os.getpid())+'.tmp');q.write_text(json.dumps(v));q.chmod(0o600);q.replace(p)

def choice(args):
    try:
        i=args.index('--config');base=Path(args[i+1]);slot=int(re.fullmatch(r'\.slot_(\d+)\.ovpn',base.name)[1])
        source=hashlib.sha256(base.read_bytes()).hexdigest();c=read(DATA/'protocol-choices.json',{}).get(source)
        if not c or c.get('expires',0)<time.time():return None
        p=Path(c['profile']).resolve()
        if p.parent!=(DATA/'protocol-profiles').resolve() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=c.get('profile_sha'):return None
        fallback=read(DATA/'protocol-fallbacks'/f'{source}.json',{})
        if fallback.get('until',0)>time.time():return None
        return dict(c,slot=slot,source=source,index=i,path=str(p))
    except Exception:return None

def run(args,c):
    current=None;stopped=False
    def terminate(sig,frame):
        nonlocal stopped
        stopped=True
        if current and current.poll() is None:
            try:current.terminate()
            except ProcessLookupError:pass
    signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
    status=DATA/'protocol-active'/f"{c['slot']}.json"
    for preferred in [True,False]:
        if stopped:break
        argv=list(args)
        if preferred:argv[c['index']+1]=c['path']
        current=subprocess.Popen([REAL]+argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        lines=queue.Queue()
        def reader(pipe):
            for line in pipe:lines.put(line)
            lines.put(None)
        threading.Thread(target=reader,args=(current.stdout,),daemon=True).start()
        started=time.monotonic();ready=False;failed=False;pending=[]
        while not stopped:
            if not ready and time.monotonic()-started>(14 if preferred else 22):failed=True;break
            try:line=lines.get(timeout=.4)
            except queue.Empty:
                if current.poll() is not None:break
                continue
            if line is None:break
            if preferred and not ready:
                pending.append(line)
                if 'auth_failed' in line.lower() or 'fatal error' in line.lower():failed=True;break
            if 'Initialization Sequence Completed' in line:
                dev='tun'+str(120+c['slot']);table=str(1000+c['slot'])
                subprocess.run(['ip','route','replace','default','dev',dev,'table',table],capture_output=True,timeout=3)
                # Existing manager also creates this rule; add only when missing.
                rules=subprocess.run(['ip','rule','show'],capture_output=True,text=True,timeout=3).stdout
                if not re.search(r'\boif '+re.escape(dev)+r'\b.*\blookup '+table+r'\b',rules):subprocess.run(['ip','rule','add','oif',dev,'table',table],capture_output=True,timeout=3)
                if preferred:
                    probe=subprocess.run(['curl','-fsS','--noproxy','*','--interface',dev,'--connect-timeout','3','--max-time','6','https://api.ipify.org'],capture_output=True,text=True)
                    if probe.returncode or probe.stdout.strip()!=c['exit_ip']:failed=True;break
                ready=True
                atomic(status,{'node_id':c['node_id'],'protocol':c['protocol'] if preferred else c['original_protocol'],'fallback':not preferred,'at':time.time(),'source':c['source']})
            if preferred and not ready:continue
            if pending:
                for saved in pending:print(saved,end='',flush=True)
                pending=[]
            else:print(line,end='',flush=True)
        if current.poll() is None:
            current.terminate()
            try:current.wait(timeout=2)
            except subprocess.TimeoutExpired:current.kill();current.wait()
        if stopped:return 0
        if preferred:
            atomic(DATA/'protocol-fallbacks'/f"{c['source']}.json",{'until':time.time()+3600,'reason':'preferred_connection_failed','at':time.time()})
            print('[opt] preferred transport failed; returning to original profile',flush=True)
        else:return current.returncode or 1
    return 0

def main():
    args=sys.argv[1:];c=choice(args)
    if c:return run(args,c)
    os.execv(REAL,[REAL]+args)
if __name__=='__main__':sys.exit(main())
