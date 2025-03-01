from abc import ABC, abstractmethod
from typing import Any, Iterator, Optional
from src.events.events import PipelineEvent, OperatorStartEvent, OperatorCompleteEvent
from src.events.listener import EventListener
from src.executors.base import Executor, SequentialExecutor

class PipelineOperator(ABC):
    """流水线算子基类"""
    
    def __init__(self, name: str, executor: Optional[Executor] = None):
        self.name = name
        self.listeners: list[EventListener] = []  # 统一使用一个监听器列表
        self.executor = executor or SequentialExecutor()
    
    def add_listener(self, listener: EventListener) -> None:
        """添加事件监听器"""
        # 防止重复添加同一个监听器
        if listener not in self.listeners:
            self.listeners.append(listener)
    
    def notify_listeners(self, event: PipelineEvent) -> None:
        """通知所有监听器"""
        for listener in self.listeners:
            listener.on_event(event)
    
    def set_executor(self, executor: Executor) -> 'PipelineOperator':
        """设置执行器"""
        self.executor = executor
        return self
    
    def process(self, data: Any) -> Iterator[Any]:
        """处理数据的统一入口"""
        self.notify_listeners(OperatorStartEvent(self.name))
        try:
            yield from self.executor.execute(self._process_impl, data)
        finally:
            self.notify_listeners(OperatorCompleteEvent(self.name))
    
    @abstractmethod
    def _process_impl(self, data: Any) -> Any:
        """具体的处理逻辑，由子类实现"""
        pass