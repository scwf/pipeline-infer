from typing import Any, Callable, Optional, Type
from .base import PipelineOperator
from ..executors.base import Executor
from ..executors.parallel import ThreadExecutor, ProcessExecutor

class FilterOperator(PipelineOperator):
    """过滤算子"""
    
    def __init__(self, 
                 name: str, 
                 predicate_fn: Callable[[Any], bool], 
                 parallel_degree: int = 1,
                 executor_type: Optional[Type[Executor]] = None):
        """
        初始化过滤算子
        
        Args:
            name: 算子名称
            predicate_fn: 过滤条件函数
            parallel_degree: 并行度
            executor_type: 执行器类型，支持 ThreadExecutor 或 ProcessExecutor
        """
        # 根据配置创建执行器
        executor = None
        if parallel_degree > 1:
            executor_cls = executor_type or ThreadExecutor  # 默认使用线程池
            executor = executor_cls(max_workers=parallel_degree)
            
        super().__init__(name, executor)
        self.predicate_fn = predicate_fn
    
    def _process_impl(self, data: Any) -> Any:
        """具体的过滤逻辑"""
        if isinstance(data, list):
            return [item for item in data if self.predicate_fn(item)]
        return data if self.predicate_fn(data) else None 