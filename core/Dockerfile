FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 openvpn iproute2 iptables curl ca-certificates procps && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY *.py /app/
COPY LICENSE LICENSE.multi-exit VERSION /app/
COPY entrypoint.sh /entrypoint.sh
COPY protocol_wrapper.py /usr/local/bin/openvpn
RUN chmod 755 /entrypoint.sh /usr/local/bin/openvpn && python3 -m py_compile /app/*.py
ENTRYPOINT ["/entrypoint.sh"]
