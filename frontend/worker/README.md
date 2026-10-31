# opt Cloudflare 前置

本目录是独立编写的最小 VLESS WebSocket TCP 前置，与cfnew的WS客户端接入方式兼容；不包含cfnew内核源码。支持Cloudflare Workers，不在Worker中运行OpenVPN。

## 部署

1. 在opt的“Cloudflare融合”页下载单文件_worker.js（可直接贴进Worker编辑器），或使用本目录多文件项目运行npx wrangler deploy。
2. 在Cloudflare项目变量/机密里设置 u 为自己生成的UUID，重新部署。不要公开UUID。
3. 地址路径固定 /connect，协议 VLESS + WebSocket + TLS。opt面板提供“域名+UUID”录入方式，会按此模板自动生成配置。
4. 已有cfnew也可直接粘贴它导出的VLESS/Trojan WS节点链接。XHTTP链接需在cfnew侧生成WS版本。
5. 在opt测试前置，通过后再复制CF家宽链式订阅。独立Worker部署不需要把Cloudflare账号API令牌交给opt。

## 行为

认证UUID后承载公开TCP连接；不支持通用UDP，不附加ProxyIP或直连兜底。分片VLESS头可累积解析，受限的排队缓冲避免内存无限增长。拒绝已知私网/回环目标及25端口；Cloudflare自身的网络限制仍生效。没有刻意设定每连接384KiB之类的流量断开预算，实际CPU与平台配额仍受你的Cloudflare计划限制。

CF家宽路径：手机Mihomo(OpenVPN) → 此前置 → VPN Gate TCP → 网站。实际速度仍需在手机测量。
