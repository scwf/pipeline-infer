import cv2
import numpy as np
from src.pipeline import Pipeline
from src.operators.map import MapLikeOperator
from src.events.listener import ConsoleEventListener

def rotate_augment(image: np.ndarray) -> np.ndarray:
    """旋转增强"""
    angle = 30  # 旋转30度
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, M, (w, h))

def flip_augment(image: np.ndarray) -> np.ndarray:
    """翻转增强"""
    return cv2.flip(image, 1)  # 水平翻转

def color_augment(image: np.ndarray) -> np.ndarray:
    """颜色增强"""
    # 提高亮度和对比度
    return cv2.convertScaleAbs(image, alpha=1.2, beta=10)

def collect_augmented_data(results: list) -> list:
    """收集增强后的数据"""
    return results  # 返回所有增强结果

def main():
    # 创建流水线
    pipeline = (Pipeline("augmentation")
        .read_image("reader", "train_image.jpg")  # 使用 read_image
        .branch(
            # 旋转增强
            MapLikeOperator("rotate", rotate_augment),
            # 翻转增强
            MapLikeOperator("flip", flip_augment),
            # 颜色增强
            MapLikeOperator("color", color_augment)
        )
        .map("collect", collect_augmented_data))
    
    # 添加事件监听
    listener = ConsoleEventListener()
    for op in pipeline.operators.values():
        op.add_listener(listener)
    
    # 执行流水线
    results = pipeline.execute()
    print("Data augmentation completed.")
    
    # 保存增强后的图像
    augmented_images = results["collect"]
    for i, img in enumerate(augmented_images):
        cv2.imwrite(f"augmented_{i}.jpg", img)

if __name__ == "__main__":
    main() 