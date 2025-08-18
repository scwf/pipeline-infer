"""
异步流水线执行器
解决流水线执行的伪并行问题，实现真正的算子间并行执行
"""

import asyncio
from typing import Dict, List, Any, Optional, Set, Callable
from collections import defaultdict, deque
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
import queue

from .operators.base import PipelineOperator
from .events.performance import PerformanceMonitor, PerformanceMetricsEvent
from .events.events import ProgressEvent


class AsyncPipelineExecutor:
    """
    异步流水线执行器
    
    特性:
    1. 真正的算子间并行执行
    2. 基于依赖关系的智能调度
    3. 流式数据传递
    4. 背压控制和错误处理
    """
    
    def __init__(self, max_concurrent_operators: int = None):
        self.max_concurrent_operators = max_concurrent_operators or 4
        self._execution_stats = {}
        
    async def execute_async(self, 
                          operators: Dict[str, PipelineOperator],
                          edges: Dict[str, List[str]],
                          initial_data: Any = None) -> Dict[str, Any]:
        """异步执行流水线"""
        if not operators:
            raise ValueError("流水线为空")
        
        # 构建反向依赖图
        dependencies = defaultdict(list)  # op_name -> [dependency_names]
        dependents = defaultdict(list)    # op_name -> [dependent_names]
        
        for from_op, to_ops in edges.items():
            for to_op in to_ops:
                dependencies[to_op].append(from_op)
                dependents[from_op].append(to_op)
        
        # 执行状态跟踪
        results = {}
        completed = set()
        running = set()
        failed = set()
        
        # 数据传递队列
        data_queues = {op_name: asyncio.Queue(maxsize=10) for op_name in operators}
        
        # 性能监控
        performance_monitors = {}
        
        async def execute_operator(op_name: str) -> Any:
            """执行单个算子"""
            if op_name in completed or op_name in failed:
                return results.get(op_name)
            
            if op_name in running:
                # 等待正在运行的算子完成
                while op_name in running and op_name not in completed:
                    await asyncio.sleep(0.01)
                return results.get(op_name)
            
            running.add(op_name)
            operator = operators[op_name]
            
            try:
                # 等待所有依赖完成
                input_data = await self._collect_input_data(
                    op_name, dependencies, results, data_queues, initial_data
                )
                
                # 开始性能监控
                monitor = PerformanceMonitor()
                monitor.start()
                performance_monitors[op_name] = monitor
                
                # 执行算子
                result = await self._execute_operator_async(operator, input_data)
                
                # 记录结果
                results[op_name] = result
                completed.add(op_name)
                running.remove(op_name)
                
                # 停止性能监控
                perf_event = monitor.stop(op_name)
                operator.notify_listeners(perf_event)
                
                # 更新进度
                progress = len(completed) / len(operators)
                operator.notify_listeners(ProgressEvent(
                    op_name, progress, f"执行进度: {progress:.0%}"
                ))
                
                # 将结果传递给依赖此算子的其他算子
                await self._distribute_result(op_name, result, dependents, data_queues)
                
                return result
                
            except Exception as e:
                failed.add(op_name)
                running.discard(op_name)
                raise e
        
        # 找到所有入口节点（没有依赖的节点）
        entry_nodes = [op_name for op_name in operators if not dependencies[op_name]]
        if not entry_nodes:
            entry_nodes = [next(iter(operators))]  # 如果没有入口节点，使用第一个
        
        # 创建所有算子的执行任务
        tasks = []
        semaphore = asyncio.Semaphore(self.max_concurrent_operators)
        
        async def execute_with_semaphore(op_name: str):
            async with semaphore:
                return await execute_operator(op_name)
        
        # 为所有算子创建任务
        for op_name in operators:
            task = asyncio.create_task(execute_with_semaphore(op_name))
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def _collect_input_data(self, 
                                op_name: str, 
                                dependencies: Dict[str, List[str]],
                                results: Dict[str, Any],
                                data_queues: Dict[str, asyncio.Queue],
                                initial_data: Any) -> Any:
        """收集算子的输入数据"""
        deps = dependencies[op_name]
        
        if not deps:
            # 入口节点，使用初始数据
            return initial_data
        
        if len(deps) == 1:
            # 单个依赖，等待其完成
            dep_name = deps[0]
            while dep_name not in results:
                await asyncio.sleep(0.001)
            return results[dep_name]
        else:
            # 多个依赖，收集所有结果
            dep_results = []
            for dep_name in deps:
                while dep_name not in results:
                    await asyncio.sleep(0.001)
                dep_results.append(results[dep_name])
            return dep_results
    
    async def _execute_operator_async(self, operator: PipelineOperator, input_data: Any) -> Any:
        """异步执行算子"""
        loop = asyncio.get_event_loop()
        
        # 在线程池中执行算子
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._execute_operator_sync, operator, input_data)
            return await loop.run_in_executor(None, future.result)
    
    def _execute_operator_sync(self, operator: PipelineOperator, input_data: Any) -> Any:
        """同步执行算子"""
        return next(operator.process(input_data))
    
    async def _distribute_result(self, 
                               op_name: str, 
                               result: Any,
                               dependents: Dict[str, List[str]],
                               data_queues: Dict[str, asyncio.Queue]):
        """将结果分发给依赖的算子"""
        for dependent in dependents[op_name]:
            try:
                await data_queues[dependent].put(result)
            except asyncio.QueueFull:
                # 如果队列满了，等待一下再重试
                await asyncio.sleep(0.01)
                await data_queues[dependent].put(result)


class ThreadBasedPipelineExecutor:
    """
    基于线程的流水线执行器
    为不支持asyncio的环境提供的替代方案
    """
    
    def __init__(self, max_concurrent_operators: int = None):
        self.max_concurrent_operators = max_concurrent_operators or 4
        
    def execute(self, 
                operators: Dict[str, PipelineOperator],
                edges: Dict[str, List[str]],
                initial_data: Any = None) -> Dict[str, Any]:
        """使用线程执行流水线"""
        
        # 构建依赖关系
        dependencies = defaultdict(list)
        for from_op, to_ops in edges.items():
            for to_op in to_ops:
                dependencies[to_op].append(from_op)
        
        # 执行状态
        results = {}
        completed = set()
        running = set()
        failed = set()
        locks = {op_name: threading.Lock() for op_name in operators}
        results_lock = threading.Lock()
        
        def execute_operator(op_name: str) -> Any:
            """在线程中执行算子"""
            with locks[op_name]:
                if op_name in completed or op_name in failed:
                    return results.get(op_name)
                
                if op_name in running:
                    # 等待正在运行的算子完成
                    while op_name in running:
                        time.sleep(0.01)
                    return results.get(op_name)
                
                running.add(op_name)
                operator = operators[op_name]
                
                try:
                    # 等待依赖完成
                    input_data = self._collect_input_data_sync(
                        op_name, dependencies, results, initial_data
                    )
                    
                    # 执行算子
                    monitor = PerformanceMonitor()
                    monitor.start()
                    
                    result = next(operator.process(input_data))
                    
                    # 记录结果
                    with results_lock:
                        results[op_name] = result
                        completed.add(op_name)
                        running.discard(op_name)
                    
                    # 性能监控
                    perf_event = monitor.stop(op_name)
                    operator.notify_listeners(perf_event)
                    
                    # 进度通知
                    progress = len(completed) / len(operators)
                    operator.notify_listeners(ProgressEvent(
                        op_name, progress, f"执行进度: {progress:.0%}"
                    ))
                    
                    return result
                    
                except Exception as e:
                    with results_lock:
                        failed.add(op_name)
                        running.discard(op_name)
                    raise e
        
        # 使用线程池执行所有算子
        with ThreadPoolExecutor(max_workers=self.max_concurrent_operators) as executor:
            futures = {executor.submit(execute_operator, op_name): op_name 
                      for op_name in operators}
            
            # 等待所有任务完成
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"算子 {futures[future]} 执行失败: {e}")
        
        return results
    
    def _collect_input_data_sync(self, 
                               op_name: str, 
                               dependencies: Dict[str, List[str]],
                               results: Dict[str, Any],
                               initial_data: Any) -> Any:
        """同步收集输入数据"""
        deps = dependencies[op_name]
        
        if not deps:
            return initial_data
        
        # 等待所有依赖完成
        while not all(dep in results for dep in deps):
            time.sleep(0.001)
        
        if len(deps) == 1:
            return results[deps[0]]
        else:
            return [results[dep] for dep in deps]


def create_pipeline_executor(async_mode: bool = True, max_concurrent: int = None):
    """
    工厂函数：创建流水线执行器
    
    Args:
        async_mode: 是否使用异步模式
        max_concurrent: 最大并发算子数
    """
    if async_mode:
        return AsyncPipelineExecutor(max_concurrent)
    else:
        return ThreadBasedPipelineExecutor(max_concurrent)