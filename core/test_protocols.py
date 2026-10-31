import contextlib,hashlib,io,json,sys,tempfile,time,types
from pathlib import Path
sys.path.insert(0,'/app')
import protocol_wrapper as w
import protocol_optimizer as p

def main():
    b={'ok':True,'exit_ip':'8.8.8.8','downBps':100,'upBps':100}
    assert p.improvement(b,dict(b,downBps=120,upBps=80))
    for change in [dict(downBps=110),dict(downBps=200,upBps=50),dict(downBps=200,exit_ip='9.9.9.9'),dict(ok=False)]:assert not p.improvement(b,dict(b,**change))
    with tempfile.TemporaryDirectory() as d:
        w.DATA=Path(d);profiles=w.DATA/'protocol-profiles';profiles.mkdir();base=w.DATA/'.slot_2.ovpn';base.write_text('test-original')
        chosen=profiles/'choice.ovpn';chosen.write_text('test-preferred');source=hashlib.sha256(base.read_bytes()).hexdigest()
        c={'profile':str(chosen),'profile_sha':hashlib.sha256(chosen.read_bytes()).hexdigest(),'expires':time.time()+60,'node_id':'test','protocol':'udp','original_protocol':'tcp','exit_ip':'8.8.8.8'}
        args=['--config',str(base)];w.atomic(w.DATA/'protocol-choices.json',{source:c});assert w.choice(args)
        chosen.write_text('tampered');assert w.choice(args) is None;chosen.write_text('test-preferred')
        w.atomic(w.DATA/'protocol-fallbacks'/f'{source}.json',{'until':time.time()+60});assert w.choice(args) is None
        calls=[]
        class FakeProcess:
            def __init__(self,argv,**kw):
                calls.append(argv);self.returncode=1 if len(calls)==1 else 0
                self.stdout=io.StringIO('FATAL ERROR in preferred transport\n' if len(calls)==1 else 'Initialization Sequence Completed\n')
            def poll(self):return self.returncode
            def terminate(self):pass
            def wait(self,timeout=None):return self.returncode
            def kill(self):pass
        w.subprocess.Popen=FakeProcess
        w.subprocess.run=lambda *args,**kw:types.SimpleNamespace(stdout='100: oif tun122 lookup 1002',returncode=0)
        output=io.StringIO()
        with contextlib.redirect_stdout(output):w.run(args,dict(c,index=0,path=str(chosen),source=source,slot=2))
        assert len(calls)==2
        assert calls[0][2]==str(chosen) and calls[1][2]==str(base)
        assert 'FATAL ERROR' not in output.getvalue()
        status=w.read(w.DATA/'protocol-active'/'2.json')
        assert status['protocol']=='tcp' and status['fallback'] is True
    print('PASS: improvement threshold, upload guard, same exit, checksum/expiry guard, fatal startup fallback, original-profile recovery')
if __name__=='__main__':main()
