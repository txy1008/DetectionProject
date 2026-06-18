import os
from pathlib import Path

def check_label_and_image_match(dataset_root):
    """校验每个子集的图片和标签数量匹配、格式合法"""
    subsets = ["train", "val", "test"]
    errors = []
    
    for subset in subsets:
        img_dir = Path(dataset_root) / subset / "images"
        label_dir = Path(dataset_root) / subset / "labels"

        # 修复：分开遍历多种图片后缀，存入集合
        img_files = set()
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            img_files.update(f.stem for f in img_dir.glob(ext))
            
        label_files = {f.stem for f in label_dir.glob("*.txt")}
        
        # 检查图片标签不匹配
        img_only = img_files - label_files
        label_only = label_files - img_files
        if img_only:
            errors.append(f"{subset}集：图片无对应标签 {list(img_only)[:5]}...")
        if label_only:
            errors.append(f"{subset}集：标签无对应图片 {list(label_only)[:5]}...")
        
        # 逐行校验标签txt格式
        for label_file in label_dir.glob("*.txt"):
            with open(label_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for idx, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    # YOLO标准格式：类别 x y w h 必须5个数字
                    if len(parts) != 5:
                        errors.append(f"{label_file} 第{idx+1}行：格式错误，需要5个数值")
                        continue
                    try:
                        cls_id = int(parts[0])
                        # 你的项目只有0/1/2三类
                        if cls_id not in [0,1,2]:
                            errors.append(f"{label_file} 第{idx+1}行：非法类别ID {cls_id}")
                        # 坐标归一化必须0~1
                        coords = [float(x) for x in parts[1:]]
                        if not all(0 <= num <= 1 for num in coords):
                            errors.append(f"{label_file} 第{idx+1}行：坐标超出0~1范围")
                    except ValueError:
                        errors.append(f"{label_file} 第{idx+1}行：存在非数字内容")
    
    # 输出校验结果
    if errors:
        print("❌ 数据集校验发现异常：")
        for err in errors:
            print(f"- {err}")
    else:
        print("✅ 全部数据集校验通过，图片标签匹配、格式规范！")

if __name__ == "__main__":
    check_label_and_image_match("datasets/traffic_dataset")