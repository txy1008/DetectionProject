import os
from pathlib import Path

# ---------------------- 配置路径（完全适配你的文件夹！） ----------------------
dataset_root = Path("datasets/traffic_dataset")
subsets = ["train", "val", "test"]

# 类别映射：你的原始ID → 新ID
class_map = {
    0: 2,   # Electric-bicycle → bicycle(2)
    1: 2,   # bicycle → bicycle(2)
    2: 1,   # bus → car(1)
    3: 1,   # car → car(1)
    4: 0,   # person → person(0)
    5: 1    # truck → car(1)
}

# ---------------------- 批量转换标签 ----------------------
for subset in subsets:
    input_label_dir = dataset_root / subset / "labels"
    output_label_dir = dataset_root / subset / "labels_converted"
    output_label_dir.mkdir(parents=True, exist_ok=True)

    print(f"正在处理 {subset} 集的标签...")
    for label_file in input_label_dir.glob("*.txt"):
        new_lines = []
        with open(label_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                old_class_id = int(parts[0])
                if old_class_id not in class_map:
                    continue
                new_class_id = class_map[old_class_id]
                new_line = f"{new_class_id} {' '.join(parts[1:])}\n"
                new_lines.append(new_line)

        new_label_path = output_label_dir / label_file.name
        with open(new_label_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    # 自动替换原标签
    input_label_dir.replace(input_label_dir.with_name("labels_old"))
    output_label_dir.replace(input_label_dir)

print("✅ 所有标签转换完成！现在只有 0 1 2 三类！")