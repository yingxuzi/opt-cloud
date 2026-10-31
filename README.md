# opt 1.3 · 独立 Docker 部署

Linux ARM64（甲骨文A1）或 x86_64/AMD64。与当前服务器版相同的家宽多出口管理与VLESS接入；不依赖1Panel、现有镜像或其他服务器的数据。首次启动独立生成管理密码、订阅token与UUID，包内不含原服务器凭据。

## 从 GitHub 一键部署

将本目录内容上传到 GitHub **公开仓库根目录**。以下 OWNER/REPO 是占位符，必须替换成你的实际仓库；发布后命令才可用。

在新服务器执行（默认安装到 /opt/opt13）：

```bash
curl -fL https://raw.githubusercontent.com/yingxuzi/opt-cloud/main/install.sh -o /tmp/opt13-install.sh && sudo bash /tmp/opt13-install.sh yingxuzi/opt-cloud main
```

自动下载源码、按需安装 Docker、构建并启动容器、申请并续签 IP 证书。先放行 TCP 80、7777，两个端口需空闲。脚本不修改防火墙，不停止其他服务。

私有仓库请用已有的 GitHub 认证方式克隆，再执行 `sudo bash deploy.sh --install-docker`；匿名下载命令适用于公开仓库。密码和订阅凭据在首次启动时生成，禁止上传 data/、.env、证书和导出的订阅。

固定版本时创建发布标签，将命令中两处 main 都替换成标签。部署后凭据位于 `/opt/opt13/data/frontend/admin-credentials.txt`。

## 本地源码启动

将压缩包上传到另一台服务器，解压进入目录后执行：

```bash
sudo bash deploy.sh --install-docker
```

Docker已安装时跳过安装；未安装时使用Docker官方安装脚本。需要curl和Docker Compose插件。脚本会自动检测架构、公网IPv4，构建三个镜像，启动证书服务、初始化、节点核心和管理页。

也可以显式指定公网IPv4：

```bash
sudo OPT_PUBLIC_IP=你的公网IPv4 bash deploy.sh --install-docker
```

部署完成终端显示管理页地址：`https://服务器公网IPv4:7777`。用户名和密码保存在 `data/frontend/admin-credentials.txt`，权限0600，不输出到日志。自行在新服务器上查看此文件即可登录。节点验证与测速需要时间，服务启动不等于已经有50个可用节点。

## 必要条件

- 公网IPv4可入站；TUN可用的Linux服务器。OpenVZ/LXC等环境需由宿主机允许TUN；脚本无法突破服务商限制。建议至少2核、4GiB内存，磁盘需留出Docker镜像和日志空间。
- 云安全组、主机防火墙放行TCP 80、7777。80是证书验证/续签专用端口，必须持续可达；不暴露底层管理端口和SOCKS端口。
- 新机80与7777必须空闲。如果已有1Panel/Nginx占用80，脚本会停止并提示，不会自动停止其他网站。已有网站服务器需要单独规划ACME webroot接入，本包默认面向空闲端口的新服务器。
- 可以访问Docker镜像源、Debian/PyPI软件源、Let's Encrypt和VPN Gate；下载失败、ACME限流或网络不可达会导致部署/签发失败，不会以自签名证书冒充成功。

## 证书完全自动化

独立Python/Certbot服务负责HTTP-01验证、首次申请及后续续签，不需要域名或1Panel。使用Let's Encrypt shortlived IP证书，自动检查续期；失败时保留现有证书并退避重试。签发结果通过原子文件同步给前端，前端自动热加载；订阅启用正常CA证书验证，不固定短期证书指纹。

证书服务只处理ACME挑战路径，其他HTTP路径返回404。首次申请必须能从公网访问TCP80。脚本自动接受Let's Encrypt订阅协议，未配置电子邮箱，证书由自动化服务维护。

## Docker Compose

```bash
docker compose ps
docker compose logs --tail 100 certificates
docker compose logs --tail 100 core
docker compose logs --tail 100 frontend
```

手动启动也可以，但需先生成`.env`里的`OPT_PUBLIC_IP`和`OPT_ARCH`（arm64或amd64）：

```bash
docker compose up -d --build --wait --wait-timeout 600
```

启动顺序：证书有效→初始化完成→核心健康→前端。核心和前端共享容器网络命名空间，内部使用127.0.0.1，不依赖固定Docker IP；仅发布80/7777。核心具备TUN所需的容器内网络权限，不使用privileged或Docker socket。

## 更新与迁移

数据集中在`data/`；请备份后再更换版本。重复执行部署脚本保留账号、token和UUID。脚本不覆盖属于另一个公网IP的数据目录。迁移到不同IP应使用空数据目录生成新凭据和证书，不复制本机私钥、ACME账户或老订阅。

订阅最多50个住宅分类出口，按甲骨文/当前部署服务器经出口实测下载速度排序；每15分钟滚动复测，任务忙时顺延。住宅分类不是原生IP保证。每台服务器的候选、国家分布和速度不同，不保证恰好50个。

## 验证边界

已在ARM64环境完成三镜像构建、证书更新/拒绝无效证书测试、首次初始化及重复初始化保留凭据测试、Compose两种架构配置检查、安装脚本占用端口保护检查。AMD64程序来自同一官方Mihomo版本并校验GitHub提供的SHA256，但未在AMD64机器上实际部署。

没有在另一台服务器上真实申请新IP证书或验证它的公网入站连通性；这需要目标服务器满足上述网络条件。没有在当前生产服务器运行此安装器启动新服务，也没有变更当前服务。

## 来源和许可

Mihomo v1.19.33：`frontend/vendor/SOURCES.json`记录官方发布地址与SHA256；构建时按架构下载官方二进制并校验SHA256，无需提交大文件。
上游Mihomo：https://github.com/MetaCubeX/mihomo
Aimili派生核心源码、原版权和许可见`core/LICENSE`、`core/LICENSE.multi-exit`与源码文件。管理前端许可见`frontend/LICENSE`与`frontend/NOTICE.md`。
IP证书官方说明：https://letsencrypt.org/2026/03/11/shorter-certs-certbot/

不要公开分享`data/`，其中包含管理员密码、订阅凭据和证书私钥。
