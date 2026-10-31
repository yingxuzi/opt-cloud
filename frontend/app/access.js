'use strict';
const net=require('node:net');
// Only the configured domain and the known server IP can become subscription endpoints.
// Never use an arbitrary Host/X-Forwarded-Host as a proxy address or redirect target.
function access(req,publicURL,serverIP,options={}){
 const direct=new URL('https://'+serverIP+':7777');
 const raw=String(req?.headers?.host||'').toLowerCase();
 const url=raw===direct.host?direct:publicURL;
 return {url,endpoint:{port:Number(url.port||443),trusted:net.isIP(url.hostname)===0||options.trustedIP===true}};
}
module.exports={access};
