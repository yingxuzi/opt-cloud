# opt 1.1.1

自托管 VPN Gate 出口管理服务。2026-10-23。

本版本为基于现有 Aimili 部署的衍生管理层，并非全新 VPN 协议或独立实现的 VPN 内核。

- 兼容与复用的底座：OpenMili/aimili-vpngate（本地基线 2cd7dc58cebd1be5a99a0d2d83c701645207596f）、Guli-Joy/aimili-vpngate（本地基线 56deecacf14dd3280dd01d96526d5891692c71c2）及本机多出口补丁。现有核心源码位于 /opt/aimili-deploy/multi-upstream。
- base-model.js 派生自当前部署接入层；该代码与 opt 管理程序按 GPL-3.0-or-later 提供，许可全文见 LICENSE。
- VPN Gate 为独立的志愿者节点来源：https://www.vpngate.net/
- OpenVPN 提供隧道，Mihomo 提供 VLESS/SOCKS 转发；本仓库附带的 mihomo 可执行文件来自既有部署，相关项目：https://github.com/MetaCubeX/mihomo
- 双向测试使用 Cloudflare 公开测试端点，调用方法参考 https://github.com/cloudflare/speedtest 。测试端点、链路和公共节点可能改变，测量结果不构成带宽保证。

保留以上来源及许可说明。opt 未获上述项目官方背书。

- Cloudflare接入兼容性参考：https://github.com/byJoey/cfnew 与 https://github.com/byJoey/cfnew-panel （engine.mjs 的订阅方式）。未复制或分发这两个项目的Worker/面板实现。opt的cloudflare.js与worker/模板为独立编写，适用本项目GPL-3.0-or-later。
- Worker运行时API：https://developers.cloudflare.com/workers/runtime-apis/tcp-sockets/ 。Mihomo OpenVPN配置：https://wiki.metacubex.one/en/config/proxies/openvpn/ 。
