import cv2
import numpy as np
import os
from src.pipeline import Pipeline
from src.operators.map import MapLikeOperator
from src.events.listener import ConsoleEventListener

def check_clarity(image: np.ndarray) -> float:
    """检查图像清晰度"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def check_brightness(image: np.ndarray) -> float:
    """检查图像亮度"""
    return np.mean(image)

def check_contrast(image: np.ndarray) -> float:
    """检查图像对比度"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return np.std(gray)

def make_quality_decision(results: list) -> dict:
    """根据各项指标做出质量判断"""
    clarity, brightness, contrast = results
    
    return {
        "quality_score": (clarity + brightness + contrast) / 3,
        "clarity": clarity,
        "brightness": brightness,
        "contrast": contrast,
        "pass": clarity > 100 and 50 < brightness < 200 and contrast > 30
    }

def main():
    # 创建流水线
    # 构建图片路径
    image_path = os.path.join(os.path.dirname(__file__), "resources", "小鱼儿.jpg")
    
    # 检查文件是否存在
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")
    
    pipeline = (Pipeline("quality_check")
        .read_image("reader", image_path)
        .branch(
            # 清晰度检查
            MapLikeOperator("clarity", check_clarity),
            # 亮度检查
            MapLikeOperator("brightness", check_brightness),
            # 对比度检查
            MapLikeOperator("contrast", check_contrast)
        )
        .map("decision", make_quality_decision))
    
    # 添加事件监听
    listener = ConsoleEventListener()
    for op in pipeline.operators.values():
        op.add_listener(listener)
    
    # 执行流水线
    results = pipeline.execute()
    print("Quality check completed.")
    print(f"Quality check results: {results['decision']}")

if __name__ == "__main__":
    main()