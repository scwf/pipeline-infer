from abc import ABC, abstractmethod
from .events import PipelineEvent

class EventListener(ABC):
    """事件监听器接口"""
    
    def __eq__(self, other):
        """
        重写相等性比较方法，确保相同类型的监听器被视为相等
        """
        if not isinstance(other, EventListener):
            return False
        return self.__class__ == other.__class__
    
    def __hash__(self):
        """
        重写哈希方法，使用类名作为哈希值
        这样相同类型的监听器将具有相同的哈希值
        """
        return hash(self.__class__.__name__)
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