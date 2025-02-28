import cv2
import numpy as np
from src.pipeline import Pipeline
from src.operators.map import MapLikeOperator
from src.events.listener import ConsoleEventListener

class MockModel:
    """模拟推理模型"""
    def __init__(self, name: str):
        self.name = name
        
    def predict(self, image: np.ndarray) -> np.ndarray:
        """模拟模型推理"""
        print(f"Running {self.name} inference...")
        return image  # 实际应用中这里会是真实的模型输出

def preprocess_image(image: np.ndarray) -> np.ndarray:
    """图像预处理"""
    # 调整图像大小为统一尺寸
    return cv2.resize(image, (224, 224))

def merge_results(results: list) -> dict:
    """合并多个模型的结果"""
    # 在实际应用中，这里会根据具体需求合并结果
    return {
        "classification": results[0],
        "detection": results[1],
        "segmentation": results[2]
    }

def main():
    # 创建模拟模型
    classification_model = MockModel("Classification")
    detection_model = MockModel("Detection")
    segmentation_model = MockModel("Segmentation")
    
    # 创建流水线
    pipeline = (Pipeline("multi_model")
        .read_image("reader", "example.jpg")
        .map("preprocess", preprocess_image)
        .branch(
            # 分类模型
            MapLikeOperator("classifier", classification_model.predict),
            # 目标检测模型
            MapLikeOperator("detector", detection_model.predict),
            # 分割模型
            MapLikeOperator("segmentor", segmentation_model.predict)
        )
        .map("merger", merge_results))
    
    # 添加事件监听
    listener = ConsoleEventListener()
    for op in pipeline.operators.values():
        op.add_listener(listener)
    
    # 执行流水线
    results = pipeline.execute()
    print("Pipeline execution completed.")
    print(f"Results: {results}")

if __name__ == "__main__":
    main() 