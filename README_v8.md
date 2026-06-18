# 🚀 目标检测与追踪分析模型

## ✨ 项目概述

本项目基于 YOLOv8s 搭建完整模型训练工具链，针对交通场景完成多类别融合检测，将原始 6 类交通标注统一合并为行人、机动车、非机动车三大类别。
整套工程覆盖「数据集预处理 → 标签转换 → 数据集校验 → 模型训练调优 → 测试集指标评估 → 训练曲线可视化 → 图片/视频推理」全流程，仅专注模型训练与效果验证模块，无 GUI 界面。

---

## 🤖 AI 项目架构说明
本项目采用模块化拆分，所有脚本独立可单独执行：
- **数据处理模块**：数据集 8:1:1 自动划分、原始标签映射转换、脏数据校验过滤
- **模型训练模块**：集成多种数据增强、余弦退火学习率、早停防过拟合策略
- **模型评估模块**：批量计算 mAP@0.5、mAP@0.5:0.95、精确率、召回率
- **可视化模块**：自动解析训练日志，生成四类指标变化曲线图
- **推理模块**：单张图片检测计数、命令行通用视频推理

### 类别映射规则
- `person`（行人）：原始 `person` 类别
- `car`（机动车）：`car` / `bus` / `truck` 合并
- `bicycle`（非机动车）：`bicycle` / `Electric-bicycle` 合并

---

## 📁 仓库上传完整代码文件清单
1. `train_yolov8.py`：YOLOv8s 训练主脚本，集成全套调优参数
2. `test_my_model.py`：测试集模型精度与 mAP 评估脚本
3. `convert_labels.py`：6 类原始标签批量转为 3 类标准 YOLO 标注
4. `check_dataset_validity.py`：数据集校验（图文匹配、归一化坐标、合法类别检测）
5. `custom.yaml`：YOLO 训练数据集、类别配置文件
6. `analyze_train_logs.py`：训练日志解析与绘图工具
7. `test_image_count.py`：单图检测 + 目标计数可视化
8. `infer_video.py`：命令行视频推理工具，自定义置信度/NMS
9. `requirements.txt`：项目全部依赖库清单
10. `README.md`：项目使用说明文档
11. `.gitignore`：Git 忽略文件配置

---

## 🛠️ 技术栈与依赖
- **编程语言**：Python 3.9+
- **检测框架**：Ultralytics YOLOv8s
- **深度学习框架**：PyTorch
- **图像处理**：OpenCV
- **数值处理**：Pandas、NumPy
- **绘图工具**：Matplotlib

---

## 🚀 训练核心优化亮点
1. **全套数据增强**：mosaic、mixup、HSV 色彩扰动、旋转缩放翻转，提升模型泛化能力
2. **早停策略 patience=50**：连续 50 轮指标无提升自动终止，有效防止过拟合
3. **余弦退火学习率**：训练后期缓慢衰减，提升模型收敛精度
4. **Windows 系统适配**：`workers=0`、关闭混合精度，解决多进程报错、显存溢出
5. **数据集校验机制**：自动过滤缺失图片、无匹配标签、非法坐标、错误类别等脏数据

---

## ⚙️ 环境部署

### 1. 创建并激活虚拟环境（Windows PowerShell）
```python
python -m venv .venv
.venv\Scripts\activate
```

### 2. 一键安装全部项目依赖
```python
pip install -r requirements.txt
```

---

## 📋 完整运行流程

### 步骤 1：数据集预处理
图片、标签存放路径：datasets/traffic_dataset/images、datasets/traffic_dataset/labels
**标签类别合并转换：**
```python
python convert_labels.py
```

**校验数据集标注完整性与格式合法性：**
```python
python check_dataset_validity.py
```

### 步骤 2：启动模型训练
```python
python train_yolov8.py
# 训练参数说明：
# 预训练权重：yolov8s.pt，输入分辨率 640，最大迭代 200 轮
# 批量大小 batch=8，单 GPU 训练 device=0
# 开启 cos_lr 余弦退火学习率，lr0=0.01 lrf=0.01
# 内置 mosaic/mixup/flip 全套数据增强组合
```

### 步骤 3：测试集模型性能评估
```python
python test_my_model.py
# 自动输出 mAP@0.5、mAP@0.5:0.95、Precision、Recall 四大核心检测指标。
```

### 步骤 4：训练日志可视化绘图
```python
python analyze_train_logs.py
# 运行后在项目根目录生成 train_metrics.png，包含框损失、分类损失、mAP、精度 & 召回 4 组变化曲线。
```

### 步骤 5：模型推理测试
**单张图片检测计数：**
```python
python test_image_count.py
```

**自定义视频推理（支持修改置信度、NMS 阈值）：**
```python
python infer_video.py --video-path test_video.mp4
```

---

## 📌 补充规范说明

1. **按照老师要求**：数据集文件夹 datasets/、训练日志与权重 runs/ 不上传代码仓库；
2. **训练完成最优权重存放路径**：runs/detect/runs/traffic_yolov8/weights/best3.pt。