from typing import Iterator, Any, Callable, List, Optional, Union, Type
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base import PipelineOperator
from ..events.events import OperatorStartEvent, OperatorCompleteEvent
from ..executors.base import Executor
from ..executors.parallel import ThreadExecutor, ProcessExecutor

class MapLikeOperator(PipelineOperator):
    """映射算子"""
    
    def __init__(self, 
                 name: str, 
                 transform_fn: Callable, 
                 parallel_degree: int = 1,
                 executor_type: Optional[Type[Executor]] = None):
        """
        初始化映射算子
        
        Args:
            name: 算子名称
            transform_fn: 转换函数
            parallel_degree: 并行度
            executor_type: 执行器类型，支持 ThreadExecutor 或 ProcessExecutor
        """
        # 根据配置创建执行器
        executor = None
        if parallel_degree > 1:
            executor_cls = executor_type or ThreadExecutor  # 默认使用线程池
            executor = executor_cls(max_workers=parallel_degree)
            
        super().__init__(name, executor)
        self.transform_fn = transform_fn
        
    def _process_impl(self, data: Any) -> Any:
        if isinstance(data, list):
            return [self.transform_fn(item) for item in data]
        else:
            return self.transform_fn(data)