"""
优化的流水线类
集成所有性能优化：流水线并行、共享监控、异步事件等
"""

from typing import Dict, List, Any, Optional, TypeVar, Generic, Callable, Iterator, Type, Union
from collections import defaultdict
import asyncio
import threading

from .operators.base import PipelineOperator
from .operators.source import SourceOperator, ImageSourceOperator
from .operators.map import MapLikeOperator
from .operators.filter import FilterOperator
from .events.events import ProgressEvent
from .events.listener import EventListener
from .executors.base import Executor
from .executors.pipeline_executor import PipelineThreadExecutor, PipelineProcessExecutor
from .pipeline_async import AsyncPipelineExecutor, ThreadBasedPipelineExecutor
from .events.shared_monitor import get_global_monitor, create_optimized_monitor
from .events.async_events import get_global_event_system

T = TypeVar('T')


class OptimizedPipeline(Generic[T]):
    """
    优化的流水线类
    
    性能优化特性:
    1. 真正的算子间并行执行
    2. 高效的流水线批处理
    3. 共享性能监控器
    4. 异步事件系统
    5. 自适应批次大小
    """
    
    def __init__(self, 
                 name: str,
                 enable_async_execution: bool = True,
                 enable_shared_monitoring: bool = True,
                 enable_async_events: bool = True,
                 max_concurrent_operators: int = None):
        
        self.name = name
        self.operators: Dict[str, PipelineOperator] = {}
        self.edges: Dict[str, List[str]] = defaultdict(list)
        self._last_added: Optional[str] = None
        
        # 性能优化配置
        self.enable_async_execution = enable_async_execution
        self.enable_shared_monitoring = enable_shared_monitoring
        self.enable_async_events = enable_async_events
        self.max_concurrent_operators = max_concurrent_operators or 4
        
        # 执行器
        if enable_async_execution:
            self.executor = AsyncPipelineExecutor(max_concurrent_operators)
        else:
            self.executor = ThreadBasedPipelineExecutor(max_concurrent_operators)
        
        # 监控和事件系统
        if enable_shared_monitoring:
            self.monitor = get_global_monitor()
        
        if enable_async_events:
            self.event_system = get_global_event_system()
            self.listeners: List[EventListener] = []
        else:
            self.listeners: List[EventListener] = []
    
    def source(self, name: str, iterator: Iterator[Any]) -> 'OptimizedPipeline[T]':
        """添加通用数据源算子"""
        return self.then(SourceOperator(name, iterator))
    
    def read_image(self, name: str, image_path: str) -> 'OptimizedPipeline[T]':
        """添加图像读取算子"""
        return self.then(ImageSourceOperator(name, image_path))
    
    def map(self, 
            name: str, 
            transform_fn: Callable, 
            parallel_degree: int = 1,
            executor_type: Optional[Type[Executor]] = None,
            use_pipeline_executor: bool = True) -> 'OptimizedPipeline[T]':
        """
        添加映射算子（优化版本）
        
        Args:
            use_pipeline_executor: 是否使用高性能流水线执行器
        """
        if use_pipeline_executor and parallel_degree > 1:
            # 使用高性能流水线执行器
            if executor_type == PipelineProcessExecutor or (
                executor_type is None and parallel_degree > 4
            ):
                executor = PipelineProcessExecutor(
                    max_workers=parallel_degree,
                    max_memory_items=10000 // parallel_degree
                )
            else:
                executor = PipelineThreadExecutor(
                    max_workers=parallel_degree,
                    max_memory_items=10000,
                    pipeline_depth=3,
                    adaptive_batching=True
                )
            
            operator = MapLikeOperator(name, transform_fn)
            operator.set_executor(executor)
        else:
            # 使用标准执行器
            operator = MapLikeOperator(
                name, 
                transform_fn, 
                parallel_degree,
                executor_type
            )
        
        return self.then(operator)
    
    def filter(self, 
              name: str, 
              predicate_fn: Callable[[Any], bool], 
              parallel_degree: int = 1,
              executor_type: Optional[Type[Executor]] = None,
              use_pipeline_executor: bool = True) -> 'OptimizedPipeline[T]':
        """添加过滤算子（优化版本）"""
        if use_pipeline_executor and parallel_degree > 1:
            # 使用高性能流水线执行器
            if executor_type == PipelineProcessExecutor or (
                executor_type is None and parallel_degree > 4
            ):
                executor = PipelineProcessExecutor(
                    max_workers=parallel_degree,
                    max_memory_items=10000 // parallel_degree
                )
            else:
                executor = PipelineThreadExecutor(
                    max_workers=parallel_degree,
                    max_memory_items=10000,
                    pipeline_depth=2,
                    adaptive_batching=True
                )
            
            operator = FilterOperator(name, predicate_fn)
            operator.set_executor(executor)
        else:
            # 使用标准执行器
            operator = FilterOperator(
                name, 
                predicate_fn, 
                parallel_degree,
                executor_type
            )
        
        return self.then(operator)
    
    def then(self, operator: PipelineOperator) -> 'OptimizedPipeline[T]':
        """流式添加算子并自动连接"""
        self.add_operator(operator)
        if self._last_added:
            self.connect(self._last_added, operator.name)
        self._last_added = operator.name
        
        # 设置优化的事件和监控
        self._setup_operator_optimizations(operator)
        
        return self
    
    def add_listener(self, listener: EventListener) -> 'OptimizedPipeline[T]':
        """添加全局事件监听器"""
        if self.enable_async_events:
            self.event_system.add_listener(listener)
        
        if listener not in self.listeners:
            self.listeners.append(listener)
            # 将监听器添加到所有现有算子
            for operator in self.operators.values():
                operator.add_listener(listener)
        return self
    
    def branch(self, *operators: PipelineOperator) -> 'OptimizedPipeline[T]':
        """并行分支处理"""
        if not self._last_added:
            raise ValueError("必须先添加一个算子才能创建分支")
        
        for op in operators:
            self.add_operator(op)
            self.connect(self._last_added, op.name)
            self._setup_operator_optimizations(op)
        
        return self
    
    def join(self, operator: PipelineOperator) -> 'OptimizedPipeline[T]':
        """合并多个分支"""
        self.add_operator(operator)
        # 找到所有叶子节点
        leaves = [op_name for op_name in self.operators 
                 if not self.edges[op_name]]
        
        for leaf in leaves:
            self.connect(leaf, operator.name)
        
        self._last_added = operator.name
        self._setup_operator_optimizations(operator)
        return self
    
    def add_operator(self, operator: PipelineOperator) -> 'OptimizedPipeline[T]':
        """添加算子"""
        if operator.name in self.operators:
            raise ValueError(f"算子 {operator.name} 已存在")
        self.operators[operator.name] = operator
        return self
    
    def connect(self, from_op: str, to_op: str) -> 'OptimizedPipeline[T]':
        """连接算子"""
        if from_op not in self.operators:
            raise ValueError(f"源算子 {from_op} 不存在")
        if to_op not in self.operators:
            raise ValueError(f"目标算子 {to_op} 不存在")
        self.edges[from_op].append(to_op)
        return self
    
    def execute(self, initial_data: Optional[T] = None) -> Dict[str, Any]:
        """执行流水线（优化版本）"""
        if not self.operators:
            raise ValueError("流水线为空")
        
        if self.enable_async_execution:
            # 使用异步执行器
            return self._execute_async(initial_data)
        else:
            # 使用线程执行器
            return self.executor.execute(self.operators, self.edges, initial_data)
    
    def _execute_async(self, initial_data: Optional[T] = None) -> Dict[str, Any]:
        """异步执行流水线"""
        # 创建新的事件循环或使用现有的
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已有运行中的循环，在线程中执行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._run_async_in_thread, initial_data)
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.executor.execute_async(self.operators, self.edges, initial_data)
                )
        except RuntimeError:
            # 没有事件循环，创建新的
            return asyncio.run(
                self.executor.execute_async(self.operators, self.edges, initial_data)
            )
    
    def _run_async_in_thread(self, initial_data: Optional[T] = None) -> Dict[str, Any]:
        """在新线程中运行异步执行"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.executor.execute_async(self.operators, self.edges, initial_data)
            )
        finally:
            loop.close()
    
    def _setup_operator_optimizations(self, operator: PipelineOperator):
        """为算子设置优化功能"""
        # 设置共享监控器（如果启用）
        if self.enable_shared_monitoring:
            # 替换算子的监控器为优化版本
            operator._optimized_monitor = create_optimized_monitor()
        
        # 设置异步事件通知（如果启用）
        if self.enable_async_events:
            # 获取算子的异步事件通知器
            operator._async_notifier = self.event_system.get_notifier(operator.name)
        
        # 添加现有监听器
        for listener in self.listeners:
            operator.add_listener(listener)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        stats = {
            'pipeline_name': self.name,
            'operator_count': len(self.operators),
            'edge_count': sum(len(edges) for edges in self.edges.values()),
            'optimizations': {
                'async_execution': self.enable_async_execution,
                'shared_monitoring': self.enable_shared_monitoring,
                'async_events': self.enable_async_events
            }
        }
        
        if self.enable_shared_monitoring:
            stats['monitoring'] = self.monitor.get_stats()
        
        if self.enable_async_events:
            stats['events'] = self.event_system.get_stats()
        
        return stats
    
    def optimize_for_throughput(self):
        """针对吞吐量优化流水线配置"""
        self.enable_async_execution = True
        self.enable_shared_monitoring = True
        self.enable_async_events = True
        self.max_concurrent_operators = min(8, len(self.operators))
        
        # 重新创建执行器
        self.executor = AsyncPipelineExecutor(self.max_concurrent_operators)
        
        return self
    
    def optimize_for_latency(self):
        """针对延迟优化流水线配置"""
        self.enable_async_execution = True
        self.enable_shared_monitoring = False  # 减少监控开销
        self.enable_async_events = True
        self.max_concurrent_operators = 2  # 减少线程切换开销
        
        # 重新创建执行器
        self.executor = AsyncPipelineExecutor(self.max_concurrent_operators)
        
        return self
    
    def optimize_for_memory(self):
        """针对内存使用优化流水线配置"""
        self.enable_async_execution = False  # 使用线程而非异步
        self.enable_shared_monitoring = True  # 共享监控器节省内存
        self.enable_async_events = False  # 减少事件队列内存使用
        self.max_concurrent_operators = 2
        
        # 重新创建执行器
        self.executor = ThreadBasedPipelineExecutor(self.max_concurrent_operators)
        
        return self


def create_optimized_pipeline(name: str, 
                            optimization_target: str = "throughput") -> OptimizedPipeline:
    """
    工厂函数：创建优化的流水线
    
    Args:
        name: 流水线名称
        optimization_target: 优化目标 ("throughput", "latency", "memory")
    """
    pipeline = OptimizedPipeline(name)
    
    if optimization_target == "throughput":
        pipeline.optimize_for_throughput()
    elif optimization_target == "latency":
        pipeline.optimize_for_latency()
    elif optimization_target == "memory":
        pipeline.optimize_for_memory()
    
    return pipeline