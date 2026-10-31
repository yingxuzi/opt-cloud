'use strict';
const crypto=require('node:crypto');
const LIMIT=50,TOTAL=100,TTL=90*60*1000;
const DEFAULT_POLICY={officialMbps:100,measuredMbps:0};
function key(id){return crypto.createHash('sha256').update(id).digest('hex').slice(0,16)}
function rank(a,b){return (b.speedBps||0)-(a.speedBps||0)||(a.latencyMs||Infinity)-(b.latencyMs||Infinity)||a.node_id.localeCompare(b.node_id)}
function isHome(s){return s.ipType==='residential'&&['medium','high'].includes(s.ipConfidence)}
function eligible(slots,nodes){let map=new Map(nodes.map(n=>[n.id,n])),seen=new Set();return slots.filter(s=>{if(s.status!=='up'||s.egress_ok!==true||!map.has(s.node_id)||seen.has(s.ip))return false;seen.add(s.ip);return true}).slice(0,TOTAL).map(s=>{let n=map.get(s.node_id);return {...s,officialSpeedBps:n.speed||0,ipType:n.ip_type||'unknown',ipConfidence:n.ip_type_confidence||'low'}})}
function ranked(slots,nodes,metrics,now=Date.now()){return eligible(slots,nodes).map(s=>({...s,...(metrics[s.node_id]||{}),key:key(s.node_id)})).filter(s=>s.verifiedAt&&now-s.verifiedAt<TTL&&(s.sourceIP?s.sourceIP===s.ip&&s.exitClassified===true:s.exitIP===s.ip)).map(s=>({...s,serverIP:s.ip,ip:s.exitIP,ipType:s.exitType||s.ipType,ipConfidence:s.exitConfidence||s.ipConfidence})).sort(rank).filter((s,i,a)=>a.findIndex(x=>x.ip===s.ip)===i)}
function categories(entries,policy=DEFAULT_POLICY){let fast=s=>s.speedBps>0&&s.officialSpeedBps>=policy.officialMbps*1e6&&s.speedBps*8>=policy.measuredMbps*1e6;let sorted=[...entries].sort(rank);return {fast:sorted.filter(s=>!isHome(s)&&fast(s)).slice(0,LIMIT),home:sorted.filter(isHome).slice(0,LIMIT),'fast-home':sorted.filter(s=>isHome(s)&&fast(s)).slice(0,LIMIT)}}
function ingress(backend,uuid){return {mode:'rule','log-level':'error','allow-lan':false,proxies:Array.from({length:TOTAL},(_,i)=>({name:'slot-'+i,type:'socks5',server:backend,port:17928+i,udp:false})),listeners:Array.from({length:TOTAL},(_,i)=>({name:'entry-'+i,type:'vless',listen:'127.0.0.1',port:28000+i,users:[{username:'owner',uuid}],'ws-path':'/relay/S'+i,'allow-insecure':true,proxy:'slot-'+i})),rules:['MATCH,REJECT']}}
module.exports={LIMIT,TOTAL,TTL,DEFAULT_POLICY,key,rank,isHome,categories,eligible,ranked,ingress};
