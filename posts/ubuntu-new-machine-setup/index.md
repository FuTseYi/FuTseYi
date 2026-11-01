---
title: Ubuntu 新机初始化与开发环境配置
date: 2025-07-17
tags: Linux
---

![](assets/linux.gif)

# 我新机到手一般都会做如下配置

> 按顺序执行

# 1：更改主机名

```bash
hostnamectl set-hostname localhost
```

# 2：换国内系统源（开源脚本）

```bash
bash <(curl -sSL https://gitee.com/SuperManito/LinuxMirrors/raw/main/ChangeMirrors.sh)
```

# 3：更新系统常用包

```bash
apt update && apt install -y curl wget git zip tar lsof vim sudo
```

# 4：启用 BBR

```bash
sudo modprobe tcp_bbr && echo "net.ipv4.tcp_congestion_control = bbr" | sudo tee -a /etc/sysctl.conf && sudo sysctl -p
```

# 5：启用虚拟内存

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 700 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

# 6：使用国内镜像安装 docker（开源脚本）

```bash
bash <(curl -sSL https://gitee.com/SuperManito/LinuxMirrors/raw/main/DockerInstallation.sh)
```

# 7：加强 SSH 防护

修改 SSH 配置文件

```bash
sudo vim /etc/ssh/sshd_config
```

找到对应的配置然后修改

```bash
# 修改SSH服务端口
Port 2222

# 禁止使用空密码登录
PermitEmptyPasswords no
```

重启 SSH 服务

```bash
sudo systemctl restart ssh
```

# 8：安装 web 服务（caddy）

```bash
sudo apt install -yq debian-keyring debian-archive-keyring apt-transport-https curl && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list && sudo apt update -q && sudo apt install -yq caddy
```

# 9：更改系统语言为中文

```bash
sudo nano /etc/locale.gen
# zh_CN.UTF-8 UTF-8       // 取消这行注释

sudo locale-gen
sudo update-locale LANG=zh_CN.UTF-8
sudo localectl set-locale LANG=zh_CN.UTF-8
```

# 10：配置系统时区为上海

```bash
sudo ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
```

# 11：然后就可以使用 docker 愉快的部署各种服务了（脚本已自动配置国内镜像源），然后配合 caddy 反代各种服务

# 其他参考

```bash
# 鱼香 ros 一键安装
wget http://fishros.com/install -O fishros && . fishros
```

[GitHub · Build and ship software on a single, collaborative platform · GitHub](https://bgithub.xyz)

[KGitHub Help](https://help.kkgithub.com/)

[方达极客社区](https://gitclone.com/)

[Title Unavailable \| Site Unreachable](https://github.hscsec.cn)

[Title Unavailable \| Site Unreachable](https://git.homegu.com)

[GitHub 加速下载 - 在线工具](https://github.ur1.fun/)

[GitHub - 233boy/v2ray: 最好用的 V2Ray 一键安装脚本 & 管理脚本](https://github.com/233boy/v2ray)

 [Docker镜像加速服务整理](https://linux.do/t/topic/789917)

> docker 国内代理看这个帖子：[https://linux.do/t/topic/789917](https://linux.do/t/topic/789917)
> 科学上完用 clash verge + 机场订阅链接
> 系统 apt 源换国内的（Google 搜一些帖子非常多）
>
> 命令行走代理修改~/.bashrc 文件, 12334 端口修改为实际的代理端口。
> 注意对于 ping 这类 icmp 协议工具，是没办法走代理的。
>
> - HTTP / HTTPS 代理 export HTTP_PROXY="http://127.0.0.1:12334" export HTTPS_PROXY="http://127.0.0.1:12334"
> - 如果你需要走 SOCKS5（某些工具优先用 ALL_PROXY） export ALL_PROXY="socks5:<//127.0.0.1:12334>"
> 修改后 `source ~/.bashrc` 保存生效

> 配置 apt 镜像源；
> BBR 优化；
> 优化 SSH 配置（改端口、配置密钥对、心跳维持连接等）；
> 配置 fail2ban、UFW 等；
> 配置 .zshrc、.vimrc 等，添加常用的几个 alias；
> 配置 proxychains；
> ~~安装 neofetch、cowsay 等强大的 CLI 工具；~~
> ~~每天来一把 sudo apt upgrade -y。~~

# 实验室备份

```bash

apt
cd /etc/apt
cp /etc/apt/sources.list /etc/apt/sources.list.bak
gedit sources.list

deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/ bionic main multiverse restricted universe
deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/ bionic-security main multiverse restricted universe
deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/ bionic-updates main multiverse restricted universe
deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/ bionic-backports main multiverse restricted universe
deb-src http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/ bionic main multiverse restricted universe
deb-src http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/ bionic-security main multiverse restricted universe
deb-src http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/ bionic-updates main multiverse restricted universe
deb-src http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/ bionic-backports main multiverse restricted universe

sudo apt-get update

pip
pip3 install --upgrade pip
mkdir ~/.pip
gedit ~/.pip/pip.conf
[global]
index-url =  https://pypi.mirrors.ustc.edu.cn/simple
[install]
trusted-host =  https://pypi.mirrors.ustc.edu.cn

torch
sudo apt-get install python3-pip libopenblas-base libopenmpi-dev libomp-dev
pip3 install Cython
pip3 install numpy torch-1.8.0-cp36-cp36m-linux_aarch64.whl

import torch
import torchvision
print(torch.__version__)
print(torchvision.__version__)

torchvison
sudo apt-get install libjpeg-dev zlib1g-dev libpython3-dev libavcodec-dev libavformat-dev libswscale-dev
cd torchvision
$ export BUILD_VERSION=0.x.0  # where 0.x.0 is the torchvision version  
$ python3 setup.py install --user
$ cd ../  # attempting to load torchvision from build dir will result in import error
$ pip install 'pillow<7' # always needed for Python 2.7, not needed torchvision v0.5.0+ with Python 3.6

```
