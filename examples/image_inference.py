import cv2
import numpy as np
from src.pipeline import Pipeline
from src.operators.source import SourceOperator
from src.operators.map import MapLikeOperator
from src.events.listener import ConsoleEventListener

def split_image(image: np.ndarray, tile_size: int = 1024) -> list[np.ndarray]:
    """将图像切分成小块"""
    height, width = image.shape[:2]
    tiles = []
    
    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            tile = image[y:min(y+tile_size, height), x:min(x+tile_size, width)]
            tiles.append(tile)
            
    return tiles

def mock_inference(tile: np.ndarray) -> np.ndarray:
    """模拟推理过程"""
    # 这里只是一个示例，实际应该替换为真实的推理代码
    return cv2.GaussianBlur(tile, (5, 5), 0)

def is_valid_tile(tile: np.ndarray) -> bool:
    """验证图像块是否有效"""
    # 例如：过滤掉全黑或全白的图像块
    mean_value = np.mean(tile)
    return 10 < mean_value < 245

def main():
    # 创建流水线
    pipeline = (Pipeline("image_inference")
        .read_image("reader", "large_image.jpg")  # 使用 read_image
        .map("image_splitter", split_image)
        .filter("valid_tiles", is_valid_tile)  # 过滤无效的图像块
        .map("inferencer", mock_inference, parallel_degree=4))
    
    # 添加事件监听
    listener = ConsoleEventListener()
    for op in pipeline.operators.values():
        op.add_listener(listener)
    
    # 执行流水线
    results = pipeline.execute()
    print(f"处理完成，共生成 {len(results['inferencer'])} 个结果")

if __name__ == "__main__":
    main() 