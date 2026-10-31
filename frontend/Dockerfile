FROM node:22-alpine AS mihomo
ARG OPT_ARCH=arm64
RUN apk add --no-cache curl ca-certificates gzip
COPY download-mihomo.sh /download-mihomo.sh
RUN sh /download-mihomo.sh "$OPT_ARCH" /mihomo
FROM node:22-alpine
RUN apk add --no-cache curl ca-certificates
COPY --from=mihomo /mihomo /usr/local/bin/mihomo
COPY app /app
COPY worker /app/worker
COPY bootstrap.cjs /app/bootstrap.cjs
COPY LICENSE NOTICE.md /app/
WORKDIR /app
CMD ["node", "server.js"]
