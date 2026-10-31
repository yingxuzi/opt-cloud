'use strict';
const crypto=require('node:crypto');
function equal(a,b){const aa=crypto.createHash('sha256').update(String(a||'')).digest(),bb=crypto.createHash('sha256').update(String(b||'')).digest();return crypto.timingSafeEqual(aa,bb)}
class Auth{
 constructor(secret,credentials){this.secret=secret;this.credentials=credentials;this.failures=new Map()}
 sign(v){return crypto.createHmac('sha256',this.secret).update(v).digest('base64url')}
 token(req,u){const v=req.headers.authorization?.replace(/^Bearer /i,'')||(/^\/sub(?:\/|$)/.test(u.pathname)?u.searchParams.get('token'):'');return !!v&&equal(v,this.secret)}
 session(req){let v=req.headers.cookie?.match(/(?:^|;\s*)opt_session=([^;]+)/)?.[1];if(!v)return false;let [data,sig]=v.split('.');if(!sig||!equal(sig,this.sign(data)))return false;try{let a=JSON.parse(Buffer.from(data,'base64url'));return a.exp>Date.now()&&a.user===this.credentials().username}catch{return false}}
 allowed(req,u){return this.token(req,u)||this.session(req)}
 csrf(req){return this.sign('csrf:'+String(req.headers.cookie||''))}
 mutation(req,u){if(this.token(req,u))return true;return this.session(req)&&equal(req.headers['x-opt-csrf'],this.csrf(req))}
 login(req,user,password,secure=true){const ip=req.socket.remoteAddress,now=Date.now();for(const [k,v]of this.failures)if(now-v.at>15*60e3)this.failures.delete(k);let f=this.failures.get(ip);if(f?.count>=5)throw Error('尝试次数过多，请15分钟后重试');const c=this.credentials();if(!c.password||!equal(user,c.username)||!equal(password,c.password)){this.failures.set(ip,{at:now,count:(f?.count||0)+1});throw Error('账号或密码不正确')}this.failures.delete(ip);const data=Buffer.from(JSON.stringify({user:c.username,exp:now+12*3600e3,nonce:crypto.randomBytes(12).toString('hex')})).toString('base64url');return 'opt_session='+data+'.'+this.sign(data)+'; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200'+(secure?'; Secure':'')}
}
module.exports={Auth,equal};
