from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Any, Callable, Iterator, Iterable
from .base import Executor
from itertools import islice

class ThreadExecutor(Executor):
    """线程池执行器"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers
        self.batch_size = self.max_workers * 2  # 批次大小为工作线程数的2倍
        
    def execute(self, func: Callable, data: Any) -> Iterator[Any]:
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            if isinstance(data, (list, tuple)) or (isinstance(data, Iterable) and not isinstance(data, (str, bytes))):
                # 转换为列表并分批处理
                data = list(data) # 注意这里会把data数据全放在内存中，如果data数据很大，会导致内存爆满
                results = []
                for i in range(0, len(data), self.batch_size):
                    batch = data[i:i + self.batch_size]
                    futures = [executor.submit(func, item) for item in batch]
                    results.extend(f.result() for f in futures)
                yield results
            else:
                # 处理单个数据
                future = executor.submit(func, data)
                yield future.result()

class ProcessExecutor(Executor):
    """进程池执行器"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers
        self.batch_size = self.max_workers * 2  # 批次大小为工作进程数的2倍
        
    def execute(self, func: Callable, data: Any) -> Iterator[Any]:
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            if isinstance(data, (list, tuple)) or (isinstance(data, Iterable) and not isinstance(data, (str, bytes))):
                # 转换为列表并分批处理
                data = list(data)
                results = []
                for i in range(0, len(data), self.batch_size):
                    batch = data[i:i + self.batch_size]
                    futures = [executor.submit(func, item) for item in batch]
                    results.extend(f.result() for f in futures)
                yield results
            else:
                # 处理单个数据
                future = executor.submit(func, data)
                yield future.result() 