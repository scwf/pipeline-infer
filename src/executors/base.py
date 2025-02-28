from abc import ABC, abstractmethod
from typing import Any, Callable, Iterator

class Executor(ABC):
    """执行器基类"""
    
    @abstractmethod
    def execute(self, func: Callable, data: Any) -> Iterator[Any]:
        """执行函数"""
        pass

class SequentialExecutor(Executor):
    """串行执行器"""
    
    def execute(self, func: Callable, data: Any) -> Iterator[Any]:
        yield func(data)
