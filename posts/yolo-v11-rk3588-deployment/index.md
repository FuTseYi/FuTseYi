---
title: YOLO11 在 RK3588 上的部署与多线程优化
date: 2025-07-26
tags: RKNN, YOLO
---

![](assets/rk3588s.jpg)

参考项目<https://github.com/leafqycc/rknn-multi-threaded>

# 环境部署

# RK3588/RK3588S

## 板端 Anaconda 环境创建

> 安装 Anaconda

```bash
cd ~
wget --user-agent="Mozilla" https://mirrors.tuna.tsinghua.edu.cn/anaconda/archive/Anaconda3-2024.10-1-Linux-aarch64.sh
sh Anaconda3-2024.10-1-Linux-aarch64.sh
# 如果不能使用conda命令，在环境变量最后加上
nano ~/.bashrc
export PATH=/home/orangepi/anaconda3/bin:$PATH
source ~/.bashrc
```

> 创建 yolo11 环境并激活

```bash
conda create -y -n yolo11 python=3.10
conda activate yolo11
```

# 模型选择

## 1.板端下载官方预转换的 ONNX 模型

```bash
# yolo11n
wget https://ftrg.zbox.filez.com/v2/delivery/data/95f00b0fc900458ba134f8b180b3f7a1/examples/yolo11/yolo11n.onnx
# yolo11s
wget https://ftrg.zbox.filez.com/v2/delivery/data/95f00b0fc900458ba134f8b180b3f7a1/examples/yolo11/yolo11s.onnx
# yolo11m
wget https://ftrg.zbox.filez.com/v2/delivery/data/95f00b0fc900458ba134f8b180b3f7a1/examples/yolo11/yolo11m.onnx
```

## 2.使用服务器训练好的模型

# 模型部署

## 板端升级 Cmake 版本

```bash
conda install -c conda-forge cmake=3.25.*
```

## 板端安装 rknn-toolkit（2.3.0 版本）

```bash
git clone --branch v2.3.0 https://github.com/airockchip/rknn-toolkit2.git
cd rknn-toolkit2/packages/arm64

conda activate yolo11
pip install -r arm64_requirements_cp310.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install rknn_toolkit2-2.3.0-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl

cd ~/rknn-toolkit2/rknn-toolkit-lite2/packages
pip install rknn_toolkit_lite2-2.3.0-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl

# 把 RKNN-Toolkit2 里的可执行文件和动态库手动复制到系统的标准路径中，方便系统识别和调用
cd ~/rknn-toolkit2/rknpu2/runtime/Linux/rknn_server/aarch64/usr/bin
sudo cp * /usr/bin/
cd ~/rknn-toolkit2/rknpu2/runtime/Linux/librknn_api/aarch64
sudo cp * /usr/lib/
```

> 注意！务必检查安装的 torch 版本是否等于 1.13.1，版本不对会报错

```bash
# 若版本不对，使用下面命令重新安装torch
pip install torch==1.13.1 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 板端克隆官方 Model 仓库

```bash
git clone https://github.com/airockchip/rknn_model_zoo.git
```

## 板端 ONNX 转 RKNN 模型

```bash
# 将ONNX模型放在rknn_model_zoo/examples/yolo11/model
cd rknn_model_zoo/examples/yolo11/python
python convert.py ../model/best.onnx rk3588 # model文件夹会得到yolo11.rknn
```

## 板端运行示例代码

```bash
python yolo11.py --model_path ../model/yolo11.rknn --target rk3588 --img_show
```

# 其他

## 查看 NPU 驱动版本

```bash
cat /sys/kernel/debug/rknpu/driver_version
```

## 查看实时 NPU 占用

```bash
sudo watch -n 1 "cat /sys/kernel/debug/rknpu/load"
```
