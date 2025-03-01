from typing import Iterator, Any
import cv2
import numpy as np
from .base import PipelineOperator
from ..events.events import OperatorStartEvent, OperatorCompleteEvent
import os

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
        """读取图像，支持中文和英文路径"""
        try:
            # 使用numpy读取文件为二进制数据
            img_array = np.fromfile(self.image_path, dtype=np.uint8)
            if len(img_array) == 0:
                raise ValueError(f"图像文件为空 - {self.image_path}")
            
            # 使用imdecode解码图像数据
            image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if image is None:
                # 记录具体的错误信息
                error_msg = ""
                if not os.path.exists(self.image_path):
                    error_msg = f"文件不存在 - {self.image_path}"
                elif not os.access(self.image_path, os.R_OK):
                    error_msg = f"文件无法访问或没有读取权限 - {self.image_path}"
                else:
                    error_msg = f"图像文件可能已损坏或格式不支持 - {self.image_path}"
                print(f"错误：{error_msg}")
                raise ValueError(f"无法读取图像: {error_msg}")
            return image
        except Exception as e:
            if not isinstance(e, ValueError):
                error_msg = f"读取图像时发生异常: {str(e)}"
                print(error_msg)
                raise ValueError(f"无法读取图像: {self.image_path}, 读取时异常: {str(e)}")
            raise