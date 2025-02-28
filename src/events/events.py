from dataclasses import dataclass
from typing import Any

@dataclass
class PipelineEvent:
    """流水线事件基类"""
    operator_name: str

@dataclass
class OperatorStartEvent(PipelineEvent):
    """算子开始事件"""
    pass

@dataclass
class OperatorCompleteEvent(PipelineEvent):
    """算子完成事件"""
    pass

@dataclass
class ProgressEvent(PipelineEvent):
    """进度事件"""
    progress: float
    message: str
    
    def __post_init__(self):
        """验证进度值"""
        if not 0 <= self.progress <= 1:
            raise ValueError(f"进度值必须在0到1之间，当前值: {self.progress}") 