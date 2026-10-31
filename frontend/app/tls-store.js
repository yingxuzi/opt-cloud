'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
function material(cert,key,ip,trustedIP=false){
 const leaf=new crypto.X509Certificate(cert);
 if(!leaf.checkPrivateKey(crypto.createPrivateKey(key)))throw Error('TLS key mismatch');
 if(!leaf.checkIP(ip))throw Error('TLS IP mismatch');
 if(Date.parse(leaf.validFrom)>Date.now()||Date.parse(leaf.validTo)<=Date.now())throw Error('TLS certificate not valid now');
 return {cert,key,trustedIP:!!trustedIP,issuer:leaf.issuer, fingerprint:leaf.fingerprint256.replaceAll(':','').toLowerCase(),expiresAt:Date.parse(leaf.validTo)};
}
class TLSStore{
 constructor(dir,ip){this.file=path.join(dir,'tls-bundle.json');this.ip=ip;this.stamp=null;this.loadedAt=null;this.reloadError=false;
  // A current issued certificate must work even if the legacy fallback has expired.
  if(fs.existsSync(this.file))this.refresh();
  else{this.current=material(fs.readFileSync(path.join(dir,'server.crt')),fs.readFileSync(path.join(dir,'server.key')),ip);this.loadedAt=Date.now();}
 }
 refresh(apply=()=>{}){
  if(!fs.existsSync(this.file))return false;
  const text=fs.readFileSync(this.file,'utf8'),stamp=crypto.createHash('sha256').update(text).digest('hex');
  if(stamp===this.stamp)return false;
  try{const b=JSON.parse(text),next=material(b.cert,b.key,this.ip,b.trustedIP===true);apply(next);this.current=next;this.stamp=stamp;this.loadedAt=Date.now();this.reloadError=false;return true;}catch(e){this.reloadError=true;throw e;}
 }
 status(sync,now=Date.now()){
  const c=this.current,fresh=!!sync?.checkedAt&&now-sync.checkedAt<180000;
  return {trustedIP:c.trustedIP,issuer:c.issuer,expiresAt:c.expiresAt,loadedAt:this.loadedAt,autoRenewEnabled:sync?.autoRenewEnabled===true,syncHealthy:fresh&&sync?.ok===true,syncCheckedAt:sync?.checkedAt||null,reloadError:this.reloadError,state:c.expiresAt<=now?'expired':!c.trustedIP?'self-signed':!fresh||!sync?.ok?'sync-error':!sync.autoRenewEnabled?'renewal-disabled':this.reloadError?'reload-error':c.expiresAt-now<2*86400e3?'expiring':'ready'};
 }
}
module.exports={TLSStore,material};
