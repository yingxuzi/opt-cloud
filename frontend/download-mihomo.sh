#!/bin/sh
set -eu
case "${1:-}" in
arm64) asset=mihomo-linux-arm64-v1.19.33.gz; digest=ba408b317080ee265c46cb923a50018c1b82cbd708551cdd46a1e3e307396187 ;;
amd64) asset=mihomo-linux-amd64-compatible-v1.19.33.gz; digest=386508bfb1c72c43b6a0eda73708ecdce82546581b0ebcb16366c53757c622b6 ;;
*) echo 'Unsupported architecture' >&2; exit 1 ;;
esac
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
curl -fL --retry 3 --connect-timeout 15 --max-time 300 "https://github.com/MetaCubeX/mihomo/releases/download/v1.19.33/$asset" -o "$work/mihomo.gz"
printf '%s  %s\n' "$digest" "$work/mihomo.gz" | sha256sum -c -
gzip -dc "$work/mihomo.gz" > "${2:?output path required}"
chmod 755 "$2"
