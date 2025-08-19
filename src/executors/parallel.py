from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import Any, Callable, Iterator, Iterable, Union
from .base import Executor
from itertools import islice
import queue
import threading

class ThreadExecutor(Executor):
    """线程池执行器 - 支持流式处理，避免内存溢出"""
    
    def __init__(self, max_workers: int = None, max_memory_items: int = 10000):
        self.max_workers = max_workers
        self.batch_size = (self.max_workers or 4) * 2  # 批次大小为工作线程数的2倍
        self.max_memory_items = max_memory_items  # 内存中最大保持的数据项数
        
    def execute(self, func: Callable, data: Any) -> Iterator[Any]:
        if isinstance(data, (list, tuple)):
            # 对于列表和元组，使用流式批处理
            yield from self._execute_batch_streaming(func, data)
        elif isinstance(data, Iterable) and not isinstance(data, (str, bytes)):
            # 对于其他可迭代对象，使用流式处理
            yield from self._execute_streaming(func, data)
        else:
            # 处理单个数据
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future = executor.submit(func, data)
                yield future.result()
    
    def _execute_streaming(self, func: Callable, data_iter: Iterable) -> Iterator[Any]:
        """流式处理可迭代数据，避免将所有数据加载到内存"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 使用队列控制内存使用
            result_queue = queue.Queue(maxsize=self.batch_size * 2)
            futures_dict = {}
            data_iter = iter(data_iter)
            active_futures = 0
            finished = False
            
            def submit_batch():
                nonlocal active_futures, finished
                batch = list(islice(data_iter, self.batch_size))
                if not batch:
                    finished = True
                    return
                
                for item in batch:
                    future = executor.submit(func, item)
                    futures_dict[future] = item
                    active_futures += 1
            
            # 初始提交
            submit_batch()
            
            # 流式处理结果
            while active_futures > 0 or not finished:
                if active_futures > 0:
                    # 等待任意一个任务完成
                    for future in as_completed(futures_dict.keys(), timeout=0.1):
                        try:
                            result = future.result()
                            yield result
                            del futures_dict[future]
                            active_futures -= 1
                        except Exception as e:
                            # 处理异常但继续处理其他任务
                            del futures_dict[future]
                            active_futures -= 1
                            raise e
                        break
                
                # 如果还有数据且当前活跃任务不多，提交新批次
                if not finished and active_futures < self.max_workers:
                    submit_batch()
    
    def _execute_batch_streaming(self, func: Callable, data_list: Union[list, tuple]) -> Iterator[Any]:
        """对列表进行流式批处理"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 分批处理，避免一次性提交所有任务
            for i in range(0, len(data_list), self.max_memory_items):
                # 限制内存中的数据量
                chunk = data_list[i:i + self.max_memory_items]
                
                # 对当前块进行批处理
                for j in range(0, len(chunk), self.batch_size):
                    batch = chunk[j:j + self.batch_size]
                    futures = [executor.submit(func, item) for item in batch]
                    
                    # 按完成顺序返回结果
                    for future in as_completed(futures):
                        yield future.result()

class ProcessExecutor(Executor):
    """进程池执行器 - 支持流式处理，避免内存溢出"""
    
    def __init__(self, max_workers: int = None, max_memory_items: int = 5000):
        self.max_workers = max_workers
        self.batch_size = (self.max_workers or 4) * 2  # 批次大小为工作进程数的2倍
        self.max_memory_items = max_memory_items  # 进程池的内存限制更保守
        
    def execute(self, func: Callable, data: Any) -> Iterator[Any]:
        if isinstance(data, (list, tuple)):
            # 对于列表和元组，使用流式批处理
            yield from self._execute_batch_streaming(func, data)
        elif isinstance(data, Iterable) and not isinstance(data, (str, bytes)):
            # 对于其他可迭代对象，使用流式处理
            yield from self._execute_streaming(func, data)
        else:
            # 处理单个数据
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                future = executor.submit(func, data)
                yield future.result()
    
    def _execute_streaming(self, func: Callable, data_iter: Iterable) -> Iterator[Any]:
        """流式处理可迭代数据，避免将所有数据加载到内存"""
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 对于进程池，使用更简单的批处理策略以避免序列化开销
            data_iter = iter(data_iter)
            
            while True:
                batch = list(islice(data_iter, self.batch_size))
                if not batch:
                    break
                
                futures = [executor.submit(func, item) for item in batch]
                for future in as_completed(futures):
                    yield future.result()
    
    def _execute_batch_streaming(self, func: Callable, data_list: Union[list, tuple]) -> Iterator[Any]:
        """对列表进行流式批处理"""
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 分批处理，避免一次性提交所有任务
            for i in range(0, len(data_list), self.max_memory_items):
                # 限制内存中的数据量
                chunk = data_list[i:i + self.max_memory_items]
                
                # 对当前块进行批处理
                for j in range(0, len(chunk), self.batch_size):
                    batch = chunk[j:j + self.batch_size]
                    futures = [executor.submit(func, item) for item in batch]
                    
                    # 按完成顺序返回结果
                    for future in as_completed(futures):
                        yield future.result() 