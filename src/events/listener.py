from abc import ABC, abstractmethod
from .events import PipelineEvent

class EventListener(ABC):
    """事件监听器接口"""
    
    @abstractmethod
    def on_event(self, event: PipelineEvent) -> None:
        """处理事件的抽象方法"""
        pass

class ConsoleEventListener(EventListener):
    """控制台事件监听器实现"""
    
    def on_event(self, event: PipelineEvent) -> None:
        """将事件信息打印到控制台"""
        print(f"事件: {event}") 