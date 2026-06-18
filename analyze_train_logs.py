import pandas as pd
import matplotlib.pyplot as plt
import os

def plot_train_metrics():
    # 改成你本地真实csv路径
    log_path = r"C:\PyTorch_Project\YOLOv8_DeepSORT_Counting\runs\detect\runs\train\traffic_yolov8\results.csv"
    """可视化YOLOv8训练日志（损失/精度/召回率）"""
    # 设置中文字体（避免乱码）
    plt.rcParams["font.sans-serif"] = ["SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    
    # 读取日志
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"训练日志不存在：{log_path}")
    df = pd.read_csv(log_path)
    
    # 创建画布
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. 框损失曲线
    ax1.plot(df["epoch"], df["train/box_loss"], label="训练框损失", color="red", lw=2)
    ax1.plot(df["epoch"], df["val/box_loss"], label="验证框损失", color="blue", lw=2)
    ax1.set_title("框损失变化", fontsize=14)
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("Loss")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 分类损失
    ax2.plot(df["epoch"], df["train/cls_loss"], label="训练分类损失", color="red", lw=2)
    ax2.plot(df["epoch"], df["val/cls_loss"], label="验证分类损失", color="blue", lw=2)
    ax2.set_title("分类损失变化", fontsize=14)
    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("Loss")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. mAP指标
    ax3.plot(df["epoch"], df["metrics/mAP50(B)"], label="mAP@0.5", color="green", lw=2)
    ax3.plot(df["epoch"], df["metrics/mAP50-95(B)"], label="mAP@0.5:0.95", color="orange", lw=2)
    ax3.set_title("mAP变化", fontsize=14)
    ax3.set_xlabel("Epoch")
    ax3.set_ylabel("mAP")
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 精度+召回率
    ax4.plot(df["epoch"], df["metrics/precision(B)"], label="精度(Precision)", color="purple", lw=2)
    ax4.plot(df["epoch"], df["metrics/recall(B)"], label="召回率(Recall)", color="cyan", lw=2)
    ax4.set_title("精度&召回率变化", fontsize=14)
    ax4.set_xlabel("Epoch")
    ax4.set_ylabel("Score")
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 保存图片到项目根目录
    plt.tight_layout()
    plt.savefig("train_metrics.png", dpi=300, bbox_inches="tight")
    print("✅ 训练日志可视化完成！图片已保存为 train_metrics.png")
    plt.show()

if __name__ == "__main__":
    plot_train_metrics()