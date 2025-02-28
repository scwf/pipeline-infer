from typing import Dict, List, Any, Optional, TypeVar, Generic, Callable, Iterator, Type
from collections import defaultdict
from .operators.base import PipelineOperator
from .operators.source import SourceOperator, ImageSourceOperator
from .operators.map import MapLikeOperator
from .events.events import ProgressEvent
from .operators.filter import FilterOperator
from .executors.base import Executor

T = TypeVar('T')

class Pipeline(Generic[T]):
    """流水线类，支持流式API构建DAG"""
    
    def __init__(self, name: str):
        self.name = name
        self.operators: Dict[str, PipelineOperator] = {}
        self.edges: Dict[str, List[str]] = defaultdict(list)
        self._last_added: Optional[str] = None
    
    def source(self, name: str, iterator: Iterator[Any]) -> 'Pipeline[T]':
        """添加通用数据源算子
        
        Args:
            name: 算子名称
            iterator: 任意数据迭代器
        """
        return self.then(SourceOperator(name, iterator))
    
    def read_image(self, name: str, image_path: str) -> 'Pipeline[T]':
        """添加图像读取算子
        
        Args:
            name: 算子名称
            image_path: 图像文件路径
        """
        return self.then(ImageSourceOperator(name, image_path))
    
    def map(self, 
            name: str, 
            transform_fn: Callable, 
            parallel_degree: int = 1,
            executor_type: Optional[Type[Executor]] = None) -> 'Pipeline[T]':
        """添加映射算子
        
        Args:
            name: 算子名称
            transform_fn: 转换函数
            parallel_degree: 并行度
            executor_type: 执行器类型，支持 ThreadExecutor 或 ProcessExecutor
        """
        return self.then(MapLikeOperator(
            name, 
            transform_fn, 
            parallel_degree,
            executor_type
        ))
    
    def filter(self, 
              name: str, 
              predicate_fn: Callable[[Any], bool], 
              parallel_degree: int = 1,
              executor_type: Optional[Type[Executor]] = None) -> 'Pipeline[T]':
        """添加过滤算子
        
        Args:
            name: 算子名称
            predicate_fn: 过滤条件函数
            parallel_degree: 并行度
            executor_type: 执行器类型，支持 ThreadExecutor 或 ProcessExecutor
        """
        return self.then(FilterOperator(
            name, 
            predicate_fn, 
            parallel_degree,
            executor_type
        ))
    
    def then(self, operator: PipelineOperator) -> 'Pipeline[T]':
        """流式添加算子并自动连接"""
        self.add_operator(operator)
        if self._last_added:
            self.connect(self._last_added, operator.name)
        self._last_added = operator.name
        return self
    
    def branch(self, *operators: PipelineOperator) -> 'Pipeline[T]':
        """并行分支处理"""
        if not self._last_added:
            raise ValueError("必须先添加一个算子才能创建分支")
            
        for op in operators:
            self.add_operator(op)
            self.connect(self._last_added, op.name)
            
        return self
    
    def join(self, operator: PipelineOperator) -> 'Pipeline[T]':
        """合并多个分支"""
        self.add_operator(operator)
        # 找到所有叶子节点（没有出边的节点）
        leaves = [op_name for op_name in self.operators 
                 if not self.edges[op_name]]
        
        # 将所有叶子节点连接到新算子
        for leaf in leaves:
            self.connect(leaf, operator.name)
            
        self._last_added = operator.name
        return self
    
    def add_operator(self, operator: PipelineOperator) -> 'Pipeline[T]':
        """添加算子"""
        if operator.name in self.operators:
            raise ValueError(f"算子 {operator.name} 已存在")
        self.operators[operator.name] = operator
        return self
    
    def connect(self, from_op: str, to_op: str) -> 'Pipeline[T]':
        """连接算子"""
        if from_op not in self.operators:
            raise ValueError(f"源算子 {from_op} 不存在")
        if to_op not in self.operators:
            raise ValueError(f"目标算子 {to_op} 不存在")
        self.edges[from_op].append(to_op)
        return self
    
    def execute(self, initial_data: Optional[T] = None) -> Dict[str, Any]:
        """执行流水线"""
        if not self.operators:
            raise ValueError("流水线为空")
        
        executed = set()
        results = {}
        
        def execute_op(op_name: str, input_data: Any) -> Any:
            if op_name in executed:
                return results[op_name]
            
            op = self.operators[op_name]
            
            # 获取所有前置依赖
            dependencies = []
            for dep_name in self.operators:
                if op_name in self.edges[dep_name]:
                    # 先执行依赖
                    dep_result = execute_op(dep_name, input_data)
                    dependencies.append(dep_result)
            
            # 如果有依赖，使用依赖的结果作为输入
            if dependencies:
                if len(dependencies) == 1:
                    input_data = dependencies[0]
                else:
                    input_data = dependencies
            
            # 执行当前算子
            result = next(op.process(input_data))
            results[op_name] = result
            executed.add(op_name)
            
            # 更新进度
            progress = len(executed) / len(self.operators)
            op.notify_listeners(ProgressEvent(
                op_name, progress, f"执行进度: {progress:.0%}"
            ))
            
            return result
            
        # 找到所有叶子节点（没有出边的节点）
        leaves = [op_name for op_name in self.operators 
                 if not self.edges[op_name]]
        if not leaves:
            leaves = [next(iter(self.operators))]  # 如果没有叶子节点，使用第一个算子
        
        # 执行所有叶子节点
        for leaf in leaves:
            execute_op(leaf, initial_data)
        
        return results 