#!/bin/sh
set -eu
if [ ! -c /dev/net/tun ]; then
  mkdir -p /dev/net
  mknod /dev/net/tun c 10 200
fi
python3 - <<'PY'
import os,fcntl,array
try:
    fd=os.open('/dev/net/tun',os.O_RDWR)
    fcntl.ioctl(fd,0x800454cf,array.array('I',[0]),True)
    os.close(fd)
except OSError as e:
    raise SystemExit('TUN is unavailable in this container; check host TUN support and Docker device/capability permissions')
PY
python3 /app/protocol_optimizer.py --watch >> /data/protocol-agent.log 2>&1 &
exec python3 /app/vpngate_manager.py
