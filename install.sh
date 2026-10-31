#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo '请以 root 或 sudo 运行'; exit 1; }
opt_repo=${1:-}
opt_ref=${2:-main}
[[ $opt_repo =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || { echo '用法：sudo bash install.sh OWNER/REPO [分支或标签]'; exit 1; }
[[ $opt_ref =~ ^[A-Za-z0-9_.-]+$ && $opt_ref != . && $opt_ref != .. ]] || { echo '分支或标签格式无效'; exit 1; }
opt_dest=${OPT_INSTALL_DIR:-/opt/opt13}
[[ $opt_dest = /* && ! -e $opt_dest ]] || { echo '安装目录必须为不存在的绝对路径；已有部署请先备份并按 README 更新。'; exit 1; }
for opt_tool in curl tar; do command -v "$opt_tool" >/dev/null || { echo "缺少命令：$opt_tool"; exit 1; }; done
opt_tmp=$(mktemp -d)
trap 'rm -rf -- "$opt_tmp"' EXIT
curl -fL --retry 3 --connect-timeout 15 --max-time 300 "https://github.com/$opt_repo/archive/$opt_ref.tar.gz" -o "$opt_tmp/source.tar.gz"
mkdir "$opt_tmp/source"
tar -xzf "$opt_tmp/source.tar.gz" --strip-components=1 -C "$opt_tmp/source"
[[ -f $opt_tmp/source/deploy.sh && -f $opt_tmp/source/compose.yaml ]] || { echo '仓库中缺少部署文件'; exit 1; }
umask 077
mkdir -p -- "$(dirname -- "$opt_dest")"
mv -- "$opt_tmp/source" "$opt_dest"
bash "$opt_dest/deploy.sh" --install-docker
