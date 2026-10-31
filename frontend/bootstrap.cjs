'use strict';
const fs=require('fs'),crypto=require('crypto'),net=require('net');const front=process.env.OPT_DATA_DIR||'/data',core=process.env.OPT_CORE_DIR||'/core-data';
function write(file,value){if(fs.existsSync(file))return;fs.writeFileSync(file,typeof value==='string'?value:JSON.stringify(value),{mode:0o600,flag:'wx'});}
const ip=process.env.OPT_PUBLIC_IP;if(net.isIP(ip)!==4)throw Error('OPT_PUBLIC_IP must be a public IPv4');
fs.mkdirSync(front,{recursive:true});fs.mkdirSync(core,{recursive:true});
const b=JSON.parse(fs.readFileSync(front+'/tls-bundle.json'));const cert=new crypto.X509Certificate(b.cert);if(!cert.checkIP(ip)||!cert.checkPrivateKey(crypto.createPrivateKey(b.key))||Date.parse(cert.validTo)<=Date.now())throw Error('A valid IP certificate is required');
const random=()=>crypto.randomBytes(24).toString('base64url');
write(front+'/secrets.json',{token:random(),uuid:crypto.randomUUID()});
write(core+'/ui_auth.json',{username:'admin',password:random(),secret_path:random()});
write(front+'/public-ip.txt',ip);write(front+'/backend-ip.txt','127.0.0.1');write(front+'/server.crt',b.cert);write(front+'/server.key',b.key);
write(front+'/settings.json',{autoTest:true,sort:'download',officialMbps:100});
const auth=JSON.parse(fs.readFileSync(core+'/ui_auth.json'));
write(front+'/admin-credentials.txt','用户名：'+auth.username+'\n密码：'+auth.password+'\n管理地址：https://'+ip+':7777\n');
console.log('opt initialized. Credentials stored privately in data/frontend/admin-credentials.txt.');
