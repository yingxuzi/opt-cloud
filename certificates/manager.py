import os,json,time,threading,subprocess,ipaddress,datetime
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import unquote,urlsplit
from cryptography import x509
from cryptography.hazmat.primitives import serialization
DATA=Path(os.environ.get('OPT_CERT_DATA','/data'))
ACME=Path('/var/www/acme')
LE=Path('/etc/letsencrypt')
def atomic(path,data):
    path=Path(path);temp=Path(str(path)+'.tmp')
    fd=os.open(temp,os.O_CREAT|os.O_WRONLY|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f: json.dump(data,f)
    os.chmod(temp,0o600);os.replace(temp,path)
def sync_certificate(cert_file,key_file,ip,data=DATA):
    cert=Path(cert_file).read_text();key=Path(key_file).read_text()
    leaf=x509.load_pem_x509_certificate(cert.encode());private=serialization.load_pem_private_key(key.encode(),password=None)
    if ipaddress.ip_address(ip) not in leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.IPAddress): raise ValueError('IP mismatch')
    options=(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
    if leaf.public_key().public_bytes(*options)!=private.public_key().public_bytes(*options):raise ValueError('Key mismatch')
    now=datetime.datetime.now(datetime.timezone.utc)
    if not leaf.not_valid_before_utc<=now<leaf.not_valid_after_utc:raise ValueError('Expired certificate')
    if leaf.issuer==leaf.subject:raise ValueError('Self-signed certificate is not accepted')
    expires=int(leaf.not_valid_after_utc.timestamp()*1000)
    bundle={'cert':cert,'key':key,'trustedIP':True,'expiresAt':expires}
    dest=Path(data)/'tls-bundle.json'
    try:old=json.loads(dest.read_text())
    except Exception:old={}
    if old.get('cert')!=cert or old.get('key')!=key:atomic(dest,bundle)
    return expires
class Challenge(BaseHTTPRequestHandler):
    def do_GET(self):
        p=unquote(urlsplit(self.path).path);prefix='/.well-known/acme-challenge/'
        token=p[len(prefix):] if p.startswith(prefix) else ''
        if not token or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in token):self.send_error(404);return
        file=ACME/'.well-known/acme-challenge'/token
        if not file.is_file():self.send_error(404);return
        body=file.read_bytes();self.send_response(200);self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass
def main():
    ip=str(ipaddress.IPv4Address(os.environ['OPT_PUBLIC_IP']))
    DATA.mkdir(parents=True,exist_ok=True);ACME.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('0.0.0.0',80),Challenge);threading.Thread(target=server.serve_forever,daemon=True).start()
    next_renew=0
    failures=0
    while True:
        status={'checkedAt':int(time.time()*1000),'ok':False,'autoRenewEnabled':True,'code':'CERTIFICATE_NOT_READY'}
        try:
            lineage=LE/'live/opt-ip'
            if not (lineage/'fullchain.pem').exists():
                print('Requesting a trusted IP certificate; inbound TCP 80 must be reachable.',flush=True)
                cmd=['certbot','certonly','--webroot','-w',str(ACME),'--preferred-profile','shortlived','--ip-address',ip,'--cert-name','opt-ip','--agree-tos','--non-interactive','--register-unsafely-without-email','--key-type','ecdsa']
                subprocess.run(cmd,check=True,timeout=240);next_renew=time.time()+6*3600
            elif time.time()>=next_renew:
                subprocess.run(['certbot','renew','--non-interactive','--quiet','--no-random-sleep-on-renew'],check=True,timeout=240);next_renew=time.time()+6*3600
            status.update(ok=True,code='OK',expiresAt=sync_certificate(lineage/'fullchain.pem',lineage/'privkey.pem',ip))
        except Exception:
            print('Certificate acquisition/renewal failed; check TCP 80 and certificate service logs. Existing certificate retained.',flush=True)
            status['code']='ACME_OR_SYNC_FAILED'
        if not status['ok']:
            try: status['expiresAt']=sync_certificate(LE/'live/opt-ip/fullchain.pem',LE/'live/opt-ip/privkey.pem',ip)
            except Exception: pass
        atomic(DATA/'tls-sync-status.json',status)
        failures=0 if status['ok'] else failures+1
        time.sleep(60 if status['ok'] else min(3600,300*2**min(failures-1,4)))
if __name__=='__main__':main()
