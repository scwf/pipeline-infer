"""
高性能流水线执行器
解决批处理效率低下问题，实现真正的流水线并行处理
"""

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import Any, Callable, Iterator, Iterable, Union, Optional
from .base import Executor
from itertools import islice
import queue
import threading
import time
from collections import deque


class PipelineThreadExecutor(Executor):
    """
    高性能流水线线程执行器
    
    特性:
    1. 真正的流水线并行 - 批次间重叠执行
    2. 自适应批次大小 - 根据任务复杂度动态调整
    3. 背压控制 - 防止内存过度使用
    4. 结果有序返回 - 保持输入顺序
    """
    
    def __init__(self, 
                 max_workers: int = None,
                 max_memory_items: int = 10000,
                 pipeline_depth: int = 3,
                 adaptive_batching: bool = True):
        self.max_workers = max_workers or 4
        self.max_memory_items = max_memory_items
        self.pipeline_depth = pipeline_depth  # 流水线深度
        self.adaptive_batching = adaptive_batching
        self.batch_size = self.max_workers * 2
        
        # 性能统计
        self._task_times = deque(maxlen=100)  # 记录最近100个任务的执行时间
        
    def execute(self, func: Callable, data: Any) -> Iterator[Any]:
        """执行函数，支持流水线并行处理"""
        if isinstance(data, (list, tuple)):
            yield from self._execute_pipeline_batch(func, data)
        elif isinstance(data, Iterable) and not isinstance(data, (str, bytes)):
            yield from self._execute_pipeline_streaming(func, data)
        else:
            # 单个数据项
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, data)
                yield future.result()
    
    def _execute_pipeline_streaming(self, func: Callable, data_iter: Iterable) -> Iterator[Any]:
        """流水线流式处理 - 真正的并行流水线"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 使用多个队列实现流水线
            input_queue = queue.Queue(maxsize=self.pipeline_depth * self.batch_size)
            result_queue = queue.Queue(maxsize=self.pipeline_depth * self.batch_size)
            
            # 结果收集器
            futures_with_order = {}  # {future: order_id}
            next_order_id = 0
            next_yield_order = 0
            pending_results = {}  # {order_id: result}
            
            data_iter = iter(data_iter)
            finished_input = False
            active_futures = 0
            
            def submit_tasks():
                """提交任务到执行器"""
                nonlocal next_order_id, active_futures, finished_input
                
                batch_size = self._get_adaptive_batch_size()
                batch = list(islice(data_iter, batch_size))
                
                if not batch:
                    finished_input = True
                    return
                
                # 提交批次中的每个任务
                for item in batch:
                    if active_futures >= self.max_workers * self.pipeline_depth:
                        break
                    
                    future = executor.submit(func, item)
                    futures_with_order[future] = next_order_id
                    next_order_id += 1
                    active_futures += 1
            
            def collect_results():
                """收集完成的结果"""
                nonlocal active_futures, next_yield_order
                
                if not futures_with_order:
                    return
                
                # 检查完成的任务
                completed = []
                for future in list(futures_with_order.keys()):
                    if future.done():
                        completed.append(future)
                
                # 处理完成的任务
                for future in completed:
                    order_id = futures_with_order.pop(future)
                    active_futures -= 1
                    
                    try:
                        result = future.result()
                        pending_results[order_id] = result
                        
                        # 记录任务执行时间用于自适应批处理
                        if hasattr(future, '_start_time'):
                            exec_time = time.time() - future._start_time
                            self._task_times.append(exec_time)
                        
                    except Exception as e:
                        pending_results[order_id] = e
                
                # 按顺序返回结果
                while next_yield_order in pending_results:
                    result = pending_results.pop(next_yield_order)
                    next_yield_order += 1
                    
                    if isinstance(result, Exception):
                        raise result
                    else:
                        return result
                
                return None
            
            # 主处理循环
            while not finished_input or active_futures > 0:
                # 提交新任务（如果有空间）
                if not finished_input and active_futures < self.max_workers * self.pipeline_depth:
                    submit_tasks()
                
                # 收集结果
                result = collect_results()
                if result is not None:
                    yield result
                
                # 短暂等待，避免忙等待
                if active_futures > 0:
                    time.sleep(0.001)  # 1ms
            
            # 返回剩余的有序结果
            while pending_results:
                if next_yield_order in pending_results:
                    result = pending_results.pop(next_yield_order)
                    next_yield_order += 1
                    
                    if isinstance(result, Exception):
                        raise result
                    else:
                        yield result
                else:
                    break
    
    def _execute_pipeline_batch(self, func: Callable, data_list: Union[list, tuple]) -> Iterator[Any]:
        """流水线批处理 - 对列表数据进行高效的流水线处理"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            total_items = len(data_list)
            
            # 使用流水线处理大列表
            for chunk_start in range(0, total_items, self.max_memory_items):
                chunk_end = min(chunk_start + self.max_memory_items, total_items)
                chunk = data_list[chunk_start:chunk_end]
                
                # 对当前块进行流水线处理
                yield from self._process_chunk_pipeline(executor, func, chunk)
    
    def _process_chunk_pipeline(self, executor: ThreadPoolExecutor, func: Callable, chunk: list) -> Iterator[Any]:
        """对数据块进行流水线处理"""
        futures_with_order = []
        
        # 分批提交任务，实现流水线重叠
        batch_size = self._get_adaptive_batch_size()
        
        for i in range(0, len(chunk), batch_size):
            batch = chunk[i:i + batch_size]
            batch_futures = []
            
            # 提交当前批次
            for item in batch:
                future = executor.submit(func, item)
                future._start_time = time.time()  # 记录开始时间
                batch_futures.append(future)
            
            futures_with_order.extend(batch_futures)
            
            # 如果有足够的任务在执行，开始收集早期批次的结果
            if len(futures_with_order) >= self.max_workers * 2:
                # 收集最早批次的结果
                early_batch = futures_with_order[:batch_size]
                futures_with_order = futures_with_order[batch_size:]
                
                for future in early_batch:
                    result = future.result()
                    
                    # 记录执行时间
                    if hasattr(future, '_start_time'):
                        exec_time = time.time() - future._start_time
                        self._task_times.append(exec_time)
                    
                    yield result
        
        # 处理剩余的futures
        for future in futures_with_order:
            result = future.result()
            
            # 记录执行时间
            if hasattr(future, '_start_time'):
                exec_time = time.time() - future._start_time
                self._task_times.append(exec_time)
            
            yield result
    
    def _get_adaptive_batch_size(self) -> int:
        """自适应批次大小 - 根据任务执行时间动态调整"""
        if not self.adaptive_batching or not self._task_times:
            return self.batch_size
        
        # 计算平均任务执行时间
        avg_time = sum(self._task_times) / len(self._task_times)
        
        # 根据任务执行时间调整批次大小
        if avg_time < 0.001:  # 很快的任务，增大批次
            return min(self.batch_size * 2, self.max_workers * 4)
        elif avg_time > 0.1:  # 慢任务，减小批次
            return max(self.batch_size // 2, self.max_workers)
        else:
            return self.batch_size


class PipelineProcessExecutor(Executor):
    """
    高性能流水线进程执行器
    针对CPU密集型任务优化的进程池执行器
    """
    
    def __init__(self, 
                 max_workers: int = None,
                 max_memory_items: int = 5000,
                 chunk_size: int = None):
        self.max_workers = max_workers or 2
        self.max_memory_items = max_memory_items
        self.chunk_size = chunk_size or max(1, self.max_memory_items // self.max_workers)
        
    def execute(self, func: Callable, data: Any) -> Iterator[Any]:
        """执行函数，针对进程池优化"""
        if isinstance(data, (list, tuple)):
            yield from self._execute_chunked_batch(func, data)
        elif isinstance(data, Iterable) and not isinstance(data, (str, bytes)):
            yield from self._execute_chunked_streaming(func, data)
        else:
            # 单个数据项
            with ProcessPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, data)
                yield future.result()
    
    def _execute_chunked_streaming(self, func: Callable, data_iter: Iterable) -> Iterator[Any]:
        """分块流式处理 - 针对进程池优化"""
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            data_iter = iter(data_iter)
            
            while True:
                # 收集一个大块的数据
                chunk = list(islice(data_iter, self.chunk_size))
                if not chunk:
                    break
                
                # 将大块分成小批次并行处理
                batch_size = max(1, len(chunk) // self.max_workers)
                futures = []
                
                for i in range(0, len(chunk), batch_size):
                    batch = chunk[i:i + batch_size]
                    if batch:  # 确保批次不为空
                        # 使用map函数批量处理，减少进程间通信开销
                        future = executor.submit(self._process_batch, func, batch)
                        futures.append(future)
                
                # 收集这个块的所有结果
                for future in as_completed(futures):
                    batch_results = future.result()
                    for result in batch_results:
                        yield result
    
    def _execute_chunked_batch(self, func: Callable, data_list: Union[list, tuple]) -> Iterator[Any]:
        """分块批处理"""
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            total_items = len(data_list)
            
            # 按内存限制分块
            for chunk_start in range(0, total_items, self.max_memory_items):
                chunk_end = min(chunk_start + self.max_memory_items, total_items)
                chunk = data_list[chunk_start:chunk_end]
                
                # 将块分成批次并行处理
                batch_size = max(1, len(chunk) // self.max_workers)
                futures = []
                
                for i in range(0, len(chunk), batch_size):
                    batch = chunk[i:i + batch_size]
                    if batch:
                        future = executor.submit(self._process_batch, func, batch)
                        futures.append(future)
                
                # 收集结果
                for future in as_completed(futures):
                    batch_results = future.result()
                    for result in batch_results:
                        yield result
    
    @staticmethod
    def _process_batch(func: Callable, batch: list) -> list:
        """处理一个批次的数据 - 在子进程中执行"""
        return [func(item) for item in batch]