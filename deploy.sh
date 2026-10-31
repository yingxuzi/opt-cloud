#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ${EUID} -ne 0 ]]; then echo '请用 sudo bash deploy.sh 运行'; exit 1; fi
if ! command -v docker >/dev/null 2>&1; then
  if [[ ${1:-} != --install-docker ]]; then echo '尚未安装 Docker；使用 sudo bash deploy.sh --install-docker 自动安装。'; exit 1; fi
  command -v curl >/dev/null || { echo '请先安装 curl'; exit 1; }
  task_tmp=$(mktemp)
  curl -fsSL https://get.docker.com -o "$task_tmp"
  sh "$task_tmp"
  rm -f -- "$task_tmp"
fi
docker compose version >/dev/null || { echo '需要 Docker Compose 插件'; exit 1; }
case $(uname -m) in aarch64|arm64) opt_arch=arm64;; x86_64|amd64) opt_arch=amd64;; *) echo '目前支持 Linux ARM64 / x86_64'; exit 1;; esac
# TUN is validated inside the core container; built-in kernel drivers may have no /sys/module entry.
command -v curl >/dev/null || { echo '需要 curl'; exit 1; }
if [[ -z ${OPT_PUBLIC_IP:-} && -f .env ]]; then OPT_PUBLIC_IP=$(sed -n 's/^OPT_PUBLIC_IP=//p' .env | head -1); fi
opt_ip=${OPT_PUBLIC_IP:-$(curl -4fsS --noproxy '*' --connect-timeout 8 --max-time 15 https://api.ipify.org)}
if ! printf '%s\n' "$opt_ip" | awk -F. 'NF!=4{exit 1}{for(i=1;i<=4;i++)if($i!~/^[0-9]+$/||$i<0||$i>255)exit 1;if($1==0||$1==10||$1==127||$1>=224||($1==169&&$2==254)||($1==172&&$2>=16&&$2<=31)||($1==192&&$2==168)||($1==100&&$2>=64&&$2<=127))exit 1}'; then echo 'OPT_PUBLIC_IP 必须是公网 IPv4'; exit 1; fi
if [[ -f data/frontend/public-ip.txt && $(cat data/frontend/public-ip.txt) != "$opt_ip" ]]; then echo '已有数据属于另一个 IP，停止以免误覆盖。请先备份并规划迁移。'; exit 1; fi
# Do not stop an existing web server or modify host firewall rules.
opt_existing=$(docker compose ps --status running -q 2>/dev/null || true)
if [[ -n $opt_existing && ! -f data/frontend/public-ip.txt ]]; then echo '已有同名 opt13 项目在运行，停止以免覆盖其他部署。'; exit 1; fi
if [[ -z $opt_existing ]]; then
  for opt_port in 80 7777; do
    if (echo > /dev/tcp/127.0.0.1/"$opt_port") >/dev/null 2>&1; then echo "TCP $opt_port 已被占用。请换用空闲服务器，或先规划现有网站的 HTTP 验证接入；脚本不会停止其他服务。"; exit 1; fi
  done
fi
umask 077
mkdir -p data/{frontend,core,acme}
[[ ! -f .env ]] || cp -p .env ".env.bak.$(date +%Y%m%d%H%M%S)"
printf 'OPT_PUBLIC_IP=%s\nOPT_ARCH=%s\n' "$opt_ip" "$opt_arch" > .env
printf '将部署 opt 1.3：%s；架构：%s。请确认云平台 TCP 80、7777 已放行。\n' "$opt_ip" "$opt_arch"
docker compose up -d --build --wait --wait-timeout 600
printf '\n服务已启动：https://%s:7777\n' "$opt_ip"
printf '账号密码：data/frontend/admin-credentials.txt（仅本机保存，不在日志打印）\n'
printf '节点检测和测速在后台进行，初始订阅可能暂时为空；不会伪造50个节点。\n'
