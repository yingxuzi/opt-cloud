'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),os=require('os'),path=require('path'),crypto=require('crypto'),{execFileSync}=require('child_process');
test('fresh Docker bootstrap creates private independent credentials and reruns preserve them',()=>{
 const d=fs.mkdtempSync(path.join(os.tmpdir(),'opt-bootstrap-'));try{
 const front=path.join(d,'front'),core=path.join(d,'core');fs.mkdirSync(front);fs.mkdirSync(core);
 const cert=path.join(d,'cert.pem'),key=path.join(d,'key.pem');execFileSync('openssl',['req','-x509','-newkey','ec','-pkeyopt','ec_paramgen_curve:prime256v1','-nodes','-days','2','-subj','/CN=test','-addext','subjectAltName=IP:203.0.113.20','-keyout',key,'-out',cert],{stdio:'ignore'});
 fs.writeFileSync(path.join(front,'tls-bundle.json'),JSON.stringify({cert:fs.readFileSync(cert,'utf8'),key:fs.readFileSync(key,'utf8'),trustedIP:true}));
 const env={...process.env,OPT_DATA_DIR:front,OPT_CORE_DIR:core,OPT_PUBLIC_IP:'203.0.113.20'};
 const run=()=>execFileSync(process.execPath,[path.join(__dirname,'../frontend/bootstrap.cjs')],{env,stdio:'pipe'});run();
 const secretFile=path.join(front,'secrets.json'),adminFile=path.join(core,'ui_auth.json'),before=fs.readFileSync(secretFile,'utf8'),admin=JSON.parse(fs.readFileSync(adminFile));assert.ok(admin.password.length>=24);assert.equal(admin.username,'admin');assert.equal(fs.statSync(secretFile).mode&0o777,0o600);assert.equal(fs.readFileSync(path.join(front,'backend-ip.txt'),'utf8'),'127.0.0.1');assert.notEqual(JSON.parse(before).token,admin.password);assert.ok(crypto.randomUUID());run();assert.equal(fs.readFileSync(secretFile,'utf8'),before);assert.equal(JSON.parse(fs.readFileSync(adminFile)).password,admin.password);
 }finally{fs.rmSync(d,{recursive:true,force:true});}
});
