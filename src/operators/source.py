from typing import Iterator, Any
import cv2
from .base import PipelineOperator
from ..events.events import OperatorStartEvent, OperatorCompleteEvent

class SourceOperator(PipelineOperator):
    """通用数据源算子"""
    
    def __init__(self, name: str, iterator: Iterator[Any]):
        super().__init__(name)
        self.iterator = iterator
        
    def _process_impl(self, _: Any) -> Any:
        """实现数据源的处理逻辑"""
        try:
            return next(self.iterator)
        except StopIteration:
            return None

class ImageSourceOperator(PipelineOperator):
    """图像读取算子"""
    
    def __init__(self, name: str, image_path: str):
        super().__init__(name)
        self.image_path = image_path
    
    def _process_impl(self, _: Any) -> Any:
        """读取图像"""
        image = cv2.imread(self.image_path)
        if image is None:
            raise ValueError(f"无法读取图像: {self.image_path}")
        return image 