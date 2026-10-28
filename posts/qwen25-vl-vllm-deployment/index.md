---
title: Qwen2.5 - VL的vllm部署方案(图像分析)
date: 2025-06-15
tags: Qwen系列, vLLM
---

# 环境搭建工作

## 1 使用 Conda 创建环境

```bash
conda create -n qwen python=3.11 -y

conda activate qwen

sudo apt update && sudo apt upgrade
```

## 2 模型下载

> **1.首先安装所需依赖**

```bash
pip install "vllm>0.7.2" "transformers>=4.49.0" accelerate qwen-vl-utils modelscope
```

> 注释
> **vllm** 用于高效推理大模型。
> **transformers 和 accelerate** 是 Hugging Face 生态的核心库。
> **qwen-vl-utils** 直接关联 Qwen 的视觉 - 语言模型。
> **modelscope** 用于下载或管理预训练模型。

因为网络问题,可以走国内代理

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple   "vllm>0.7.2" "transformers>=4.49.0" accelerate qwen-vl-utils modelscope
```

> **2.这里我是用的是 Qwen2.5-VL-7B-Instruct-AWQ(量化过的模型)**

我的电脑配置是 (4090,24g 显存,实测此模型基本占满显存)

```bash
modelscope download --model Qwen/Qwen2.5-VL-7B-Instruct-AWQ --local_dir /home/user/qwen
```

注意 local_dir 后面换成自己的目录 (/home/user/qwen)

> **3.使用 vllm 框架启动模型服务**
> 可以通过 nividia-smi,查看是不是成功开启服务

```bash
vllm serve /home/user/qwen --port 8001 --host 0.0.0.0 --dtype bfloat16 --limit-mm-per-prompt image=5,video=5 --max-model-len 8001
```

注意端口不要与你现有的冲突

# 模型正式测试与调用

## 1 使用 OpenAI Python SDK 调用

> **1.可以使用本地 usb 摄像头配合 opencv 手动截图单独存放在 captures 文件夹下,供后续大模型调用分析**

```python
#!/usr/bin/env python3
import cv2
import os
import time
from datetime import datetime

# 配置参数
CAMERA_DEVICE = 0       # /dev/video1
OUTPUT_FOLDER = "captures" # 保存截图的文件夹
AUTO_SAVE_SEC = 0      # 自动截图间隔（秒），0表示手动模式
PRESS_KEY = 's'            # 手动保存的按键

# 创建输出文件夹
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 初始化摄像头
cap = cv2.VideoCapture(CAMERA_DEVICE)
if not cap.isOpened():
    print("无法打开摄像头！")
    exit()

print(f"摄像头已启动，按 '{PRESS_KEY}' 保存截图，ESC键退出")

last_save = 0
while True:
    ret, frame = cap.read()
    if not ret:
        print("无法获取画面")
        break

    # 显示实时画面
    cv2.imshow('Camera', frame)
    
    # 自动保存逻辑
    if AUTO_SAVE_SEC > 0 and (time.time() - last_save) > AUTO_SAVE_SEC:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{OUTPUT_FOLDER}/auto_{timestamp}.jpg"
        cv2.imwrite(filename, frame)
        print(f"自动保存: {filename}")
        last_save = time.time()
    
    # 按键处理
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC键退出
        break
    elif chr(key) == PRESS_KEY:  # 手动保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{OUTPUT_FOLDER}/manual_{timestamp}.jpg"
        cv2.imwrite(filename, frame)
        print(f"手动保存: {filename}")

# 释放资源
cap.release()
cv2.destroyAllWindows()
```

> **2.让大模型逐一读取 captures 内所有图像**

```python
from openai import OpenAI
import base64
import os
import shutil
from pathlib import Path
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
import cv2
import numpy as np
import json

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Set OpenAI's API key and API base to use vLLM's API server.
openai_api_key = "YOUR_API_KEY"
openai_api_base = "http://localhost:8001/v1"
client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url=openai_api_base,
)

# 确保目标文件夹存在
FIRE_IMAGES_DIR = "/home/user/really_fire"
os.makedirs(FIRE_IMAGES_DIR, exist_ok=True)

# 读取本地图片并转换为base64
def encode_image_to_base64(image_path):
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def draw_boxes(image_path, boxes, output_path):
    """在图片上绘制边框"""
    img = cv2.imread(image_path)
    for box in boxes:
        x1, y1, x2, y2 = box
        # 绘制红色边框，线宽为2
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
    cv2.imwrite(output_path, img)

# 处理图片的函数
def process_image(image_path):
    try:
        base64_image = encode_image_to_base64(image_path)
        chat_response = client.chat.completions.create(
            model="/home/user/qwen",
            messages=[
                {
                    "role": "system", 
                    "content": """你是一个专门检测火焰的图像识别助手。你的任务是：
1. 判断图片中是否存在火焰、火灾、烟雾等相关内容
2. 如果存在，请提供每个火焰/烟雾区域的坐标位置（使用像素坐标）
3. 按以下格式回复：
{
    "has_fire": true/false,
    "description": "发现火焰/烟雾：[描述]" 或 "未发现火焰相关内容",
    "boxes": [[x1,y1,x2,y2], ...] // 每个区域的左上角和右下角坐标
}"""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                        {"type":"text","text":"请检测图片中的火焰、火灾或烟雾，并提供准确的位置坐标。"},
                    ],
                },
            ],
        )
        
        response_text = chat_response.choices[0].message.content
        logging.info(f"检测图片 {image_path}:")
        logging.info(f"检测结果: {response_text}")
        
        try:
            # 解析JSON响应
            result = json.loads(response_text)
            
            if result.get("has_fire", False):
                # 获取原始文件名和扩展名
                original_filename = os.path.basename(image_path)
                name, ext = os.path.splitext(original_filename)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                
                # 生成新的文件名
                new_filename = f"{timestamp}_{name}_marked{ext}"
                target_path = os.path.join(FIRE_IMAGES_DIR, new_filename)
                
                # 在图片上绘制边框并保存
                if result.get("boxes"):
                    draw_boxes(image_path, result["boxes"], target_path)
                    logging.info(f"已标记火焰/烟雾区域并保存至: {target_path}")
                else:
                    # 如果没有边框信息，直接复制原图
                    shutil.copy2(image_path, target_path)
                    logging.info(f"发现火焰/烟雾，但无法确定具体位置，已保存原图至: {target_path}")
                
        except json.JSONDecodeError:
            logging.error("无法解析模型返回的JSON格式")
        except Exception as e:
            logging.error(f"处理检测结果时出错: {str(e)}")
            
    except Exception as e:
        logging.error(f"处理图片 {image_path} 时出错: {str(e)}")

# 文件监控处理类
class ImageHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith(('.jpg', '.jpeg')):
            logging.info(f"检测到新图片: {event.src_path}")
            process_image(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith(('.jpg', '.jpeg')):
            logging.info(f"检测到图片修改: {event.src_path}")
            process_image(event.src_path)

def main():
    # 设置监控路径
    path = "/home/user/captures"
    
    # 处理已存在的图片
    logging.info("开始检测现有图片...")
    for file in Path(path).glob("*.jp*g"):
        process_image(str(file))
    
    # 设置监控
    event_handler = ImageHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    
    logging.info(f"开始监控文件夹: {path}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("停止监控")
    
    observer.join()

if __name__ == "__main__":
    main()
```
