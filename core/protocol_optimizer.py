#!/usr/bin/env python3
"""Serial paired TCP/UDP tests in a spare tunnel, followed by one-slot application."""
from __future__ import annotations
import argparse,contextlib,fcntl,hashlib,html,ipaddress,json,os,re,signal,ssl,subprocess,threading,time,urllib.parse,urllib.request,http.cookiejar
from pathlib import Path
import vpngate_manager as vm
import proxy_server
from protocol_wrapper import atomic,read
DATA=vm.DATA_DIR;PROFILES=DATA/'protocol-profiles';REPORT=DATA/'protocol-report.json';CHOICES=DATA/'protocol-choices.json'
DEVICE='tun910';TABLE=50000;PORT=27990
stop=False

def fetch(url):
    u=urllib.parse.urlsplit(url)
    if u.scheme!='https' or u.hostname!='www.vpngate.net':raise ValueError('untrusted_config_source')
    return subprocess.run(['curl','-fsS','--compressed','--proto','=https','--proto-redir','=https','--max-time','35','--max-redirs','2',url],capture_output=True,check=True,timeout=40).stdout.decode('utf-8-sig')

def links(text,pattern):return [html.unescape(x) for x in re.findall(r'''href=['"]([^'"]*'''+pattern+r'''[^'"]*)['"]''',text)]

def official_map():
    text=fetch('https://www.vpngate.net/en/');out={}
    for link in links(text,r'do_openvpn'):
        url=urllib.parse.urljoin('https://www.vpngate.net/en/',link);q=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        try:
            if int(q.get('tcp',['0'])[0]) and int(q.get('udp',['0'])[0]):out[q['ip'][0]]=url
        except (ValueError,KeyError):pass
    return out

def profiles(node,url):
    page=fetch(url);out={}
    for link in links(page,r'\.ovpn'):
        u=urllib.parse.urljoin('https://www.vpngate.net',link);q=urllib.parse.parse_qs(urllib.parse.urlsplit(u).query)
        if q.get('host',[''])[0]!=node['ip']:continue
        proto='udp' if q.get('udp')==['1'] else 'tcp' if q.get('tcp')==['1'] else None
        if not proto or proto in out:continue
        config=fetch(u);vm.snapshot_utils.validate_openvpn_config(config)
        remote,port,actual=vm.vpn_utils.parse_remote(config,node['ip'])
        if remote!=node['ip'] or port!=int(q['port'][0]) or ('udp' if actual.startswith('udp') else 'tcp')!=proto:raise ValueError('profile_endpoint_mismatch')
        p=PROFILES/(hashlib.sha256((node['id']+proto).encode()).hexdigest()[:24]+'.ovpn')
        if p.exists():
            bak=p.with_suffix('.ovpn.bak');bak.write_bytes(p.read_bytes());bak.chmod(0o600)
        p.write_text(config);p.chmod(0o600);out[proto]=p
    if set(out)!={'tcp','udp'}:raise ValueError('official_pair_missing')
    return out

def curl(proxy,url,upload=0,echo=False):
    args=['curl','-fsS','--noproxy','','--connect-timeout','5','--max-time','25','--proxy',proxy]
    if not echo:args+=['-o','/dev/null','-w','%{json}']
    if upload:args+=['-H','Content-Type: application/octet-stream','--data-binary','@-']
    args+=[url];r=subprocess.run(args,input=os.urandom(upload) if upload else None,capture_output=True,check=True,timeout=28)
    return r.stdout.decode().strip() if echo else json.loads(r.stdout)

def test_profile(path):
    vm.OPENVPN_CMD='/usr/sbin/openvpn';process=None;event=threading.Event()
    try:
        ok,msg,process=vm.run_openvpn_until_ready(str(path),True,True,timeout=18,dev=DEVICE,extra_args=['--setenv','OPT_PROTOCOL_TEST','1','--setenv','OPT_CLOUD_SLOT','910'],report_status=False)
        if not ok:return {'ok':False,'reason':'handshake_failed'}
        vm.setup_policy_routing(DEVICE,TABLE)
        threading.Thread(target=proxy_server.start_proxy_server,args=('127.0.0.1',PORT,DEVICE,event),daemon=True).start()
        time.sleep(.3);proxy='socks5h://127.0.0.1:'+str(PORT)
        exit_ip=curl(proxy,'https://api.ipify.org',echo=True)
        if not ipaddress.ip_address(exit_ip).is_global:raise ValueError('invalid_exit')
        down=curl(proxy,'https://speed.cloudflare.com/__down?bytes=4194304')
        up=curl(proxy,'https://speed.cloudflare.com/__up',upload=1048576)
        if down['http_code']!=200 or down['size_download']!=4194304 or not 200<=up['http_code']<300 or up['size_upload']!=1048576:raise ValueError('incomplete_transfer')
        latency=curl(proxy,'https://speed.cloudflare.com/__down?bytes=0')['time_total']*1000
        return {'ok':True,'exit_ip':exit_ip,'downBps':round(down['speed_download']),'upBps':round(up['speed_upload']),'latencyMs':round(latency)}
    except Exception:return {'ok':False,'reason':'transfer_failed'}
    finally:
        event.set();time.sleep(1.1)
        if process:vm.stop_process(process)
        vm.cleanup_policy_routing(TABLE)

def improvement(base,other):
    if not other.get('ok'):return False
    if not base.get('ok'):return True
    if other.get('exit_ip')!=base.get('exit_ip'):return False
    return other['downBps']>=base['downBps']*1.15 and other['upBps']>=base['upBps']*.75

def api(path,payload):
    cfg=read(DATA/'ui_auth.json',{});base='http://127.0.0.1:8787/'+cfg['secret_path']+'/api/'
    jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    def post(url,obj):
        req=urllib.request.Request(url,json.dumps(obj).encode(),{'Content-Type':'application/json'},method='POST')
        with opener.open(req,timeout=45) as r:return json.load(r)
    post(base+'login',{'username':cfg['username'],'password':cfg['password']})
    return post(base+path,payload)

def apply(node,slot,choice):
    before=read(DATA/'ui_auth.json',{}).get('exit_slot_pin_map',{}).get(str(slot))
    try:
        result=api('assign_slot_node',{'slot':slot,'node_id':node['id']})
        return bool(result.get('ok'))
    except Exception:return False
    finally:
        # Restore only the temporary pin we set; preserve any other user pin.
        p=DATA/'ui_auth.json';cfg=read(p,{})
        if cfg.get('exit_slot_pin_map',{}).get(str(slot))==node['id']:
            backup=p.with_suffix('.json.protocol.bak');backup.write_bytes(p.read_bytes());backup.chmod(0o600)
            if before:cfg['exit_slot_pin_map'][str(slot)]=before
            else:cfg['exit_slot_pin_map'].pop(str(slot),None)
            atomic(p,cfg)

def cycle(limit=0):
    PROFILES.mkdir(exist_ok=True,parents=True);report=read(REPORT,{'results':{}});report.update(running=True,startedAt=time.time(),phase='fetching_official_profiles');atomic(REPORT,report)
    official=official_map();nodes={n['id']:n for n in read(DATA/'nodes.json',[])}
    slots=read(DATA/'slots.json',{}).get('slots',[]);pool=[s for s in slots if s.get('slot',100)>=0 and s.get('slot',100)<50 and s.get('status')=='up' and s.get('egress_ok') and s.get('ip') in official and nodes.get(s.get('node_id'),{}).get('ip_type')=='residential']
    pool.sort(key=lambda s:-nodes[s['node_id']].get('speed',0));report['eligiblePairs']=len(pool);done=0
    for s in pool:
        if stop or limit and done>=limit:break
        node=nodes[s['node_id']];old=report['results'].get(node['id'],{})
        if time.time()-old.get('at',0)<6*3600:continue
        report.update(phase='testing',currentSlot=s['slot']);atomic(REPORT,report)
        try:
            pair=profiles(node,official[s['ip']]);original='udp' if node['proto'].startswith('udp') else 'tcp';other='tcp' if original=='udp' else 'udp'
            baseline=test_profile(pair[original]);alternative=test_profile(pair[other]);selected=original
            if alternative.get('exit_ip')!=s.get('exit_ip'):alternative={'ok':False,'reason':'different_actual_exit'}
            # Confirm a promising challenger before modifying a live slot.
            confirmation=None
            if improvement(baseline,alternative):
                confirmation=test_profile(pair[other])
                if improvement(baseline,confirmation):selected=other
            result={'at':time.time(),'slot':s['slot'],'original':original,'selected':selected,'tcp':baseline if original=='tcp' else alternative,'udp':alternative if other=='udp' else baseline,'confirmation':confirmation,'applied':False}
            if selected!=original:
                current=next((x for x in read(DATA/'slots.json',{}).get('slots',[]) if x.get('slot')==s['slot'] and x.get('node_id')==node['id']),None)
                source=hashlib.sha256(node['config_text'].encode()).hexdigest()
                if current:
                    choices=read(CHOICES,{})
                    choice={'node_id':node['id'],'protocol':selected,'original_protocol':original,'profile':str(pair[selected]),'profile_sha':hashlib.sha256(pair[selected].read_bytes()).hexdigest(),'expires':time.time()+24*3600,'exit_ip':confirmation['exit_ip']}
                    choices[source]=choice;atomic(CHOICES,choices)
                    report.update(phase='applying',currentSlot=s['slot']);atomic(REPORT,report)
                    result['applied']=apply(node,s['slot'],choice)
                    if not result['applied']:
                        choices=read(CHOICES,{});choices.pop(source,None);atomic(CHOICES,choices)
            report['results'][node['id']]=result;done+=1
        except Exception:report['results'][node['id']]={'at':time.time(),'slot':s['slot'],'selected':node.get('proto'),'reason':'official_profile_or_comparison_failed','applied':False};done+=1
        atomic(REPORT,report)
    report.update(running=False,phase='idle',finishedAt=time.time(),testedThisCycle=done);report.pop('currentSlot',None);atomic(REPORT,report)

@contextlib.contextmanager
def coordinated_measurement():
    control=read(DATA/'protocol-control.json',{})
    url=control.get('opt_url','').rstrip('/')
    cfg=read(DATA/'ui_auth.json',{})
    context=ssl.create_default_context(cafile=str(DATA/'protocol-opt-ca.crt'))
    jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPSHandler(context=context),urllib.request.HTTPCookieProcessor(jar))
    csrf=None
    def call(path,obj=None):
        headers={'Content-Type':'application/json'}
        if csrf:headers['X-Opt-CSRF']=csrf
        req=urllib.request.Request(url+path,json.dumps(obj).encode() if obj is not None else None,headers)
        with opener.open(req,timeout=15) as r:return json.load(r)
    call('/api/login',{'username':cfg['username'],'password':cfg['password']})
    state=call('/api/opt/state');csrf=state['csrf'];changed=state['settings']['autoTest']
    if changed:call('/api/opt/settings',{'autoTest':False})
    r=read(REPORT,{'results':{}});r.update(running=True,phase='waiting_for_opt');atomic(REPORT,r)
    try:
        started=time.time()
        while any(j['status']=='running' for j in state['jobs']):
            if stop or time.time()-started>180:raise RuntimeError('measurement_queue_busy')
            time.sleep(3);state=call('/api/opt/state')
        yield
    finally:
        if changed:
            try:call('/api/opt/settings',{'autoTest':True})
            except Exception:
                r=read(REPORT,{'results':{}});r['restoreAutoTestRequired']=True;atomic(REPORT,r)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--watch',action='store_true');parser.add_argument('--limit',type=int,default=0);args=parser.parse_args()
    DATA.mkdir(exist_ok=True,parents=True)
    with open(DATA/'protocol-agent.lock','w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        if args.watch:time.sleep(30)
        while not stop:
            log=DATA/'protocol-agent.log'
            if log.exists() and log.stat().st_size>10*1024*1024:
                with open(log,'r+') as stream:stream.truncate(0)
            try:
                with coordinated_measurement():cycle(args.limit)
            except Exception:
                r=read(REPORT,{'results':{}});r.update(running=False,phase='retry_pending',lastError='official_source_temporarily_unavailable');atomic(REPORT,r)
            if not args.watch:break
            for _ in range(15 if read(REPORT,{}).get('phase')=='retry_pending' else 360):
                if stop:break
                time.sleep(60)
if __name__=='__main__':
    def halt(sig,frame):
        global stop
        stop=True
    signal.signal(signal.SIGTERM,halt);signal.signal(signal.SIGINT,halt);main()
