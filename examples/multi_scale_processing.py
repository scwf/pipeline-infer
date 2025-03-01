import cv2
import numpy as np
import os
from src.pipeline import Pipeline
from src.operators.map import MapLikeOperator
from src.events.listener import ConsoleEventListener

def resize_with_scale(scale: float):
    """创建特定尺度的resize函数"""
    def resize_fn(image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        new_size = (int(w * scale), int(h * scale))
        return cv2.resize(image, new_size)
    return resize_fn

def fusion_multi_scale(results: list) -> np.ndarray:
    """融合多尺度结果"""
    # 在实际应用中，这里会实现具体的多尺度融合策略
    # 这里简单地选择中等尺度的结果
    return results[1]  # 返回中等尺度结果

def main():
    # 创建流水线
    # 构建图片路径
    image_path = os.path.join(os.path.dirname(__file__), "resources", "遥感飞机.jpg")
    
    # 检查文件是否存在
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")
    
    pipeline = (Pipeline("multi_scale")
        .read_image("reader", image_path)  # 使用 read_image
        .branch(
            # 小尺度处理分支 (0.5x)
            MapLikeOperator("small_scale", resize_with_scale(0.5)),
            # 中尺度处理分支 (1.0x)
            MapLikeOperator("medium_scale", resize_with_scale(1.0)),
            # 大尺度处理分支 (2.0x)
            MapLikeOperator("large_scale", resize_with_scale(2.0))
        )
        .map("fusion", fusion_multi_scale))
    
    # 添加事件监听
    listener = ConsoleEventListener()
    for op in pipeline.operators.values():
        op.add_listener(listener)
    
    # 执行流水线
    results = pipeline.execute()
    print("Multi-scale processing completed.")
    
    # 保存结果
    cv2.imwrite("multi_scale_result.jpg", results["fusion"])

if __name__ == "__main__":
    main()