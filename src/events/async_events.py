"""
异步事件系统
解决事件通知的同步开销问题，提供高性能的异步事件处理
"""

import asyncio
import threading
import time
from typing import List, Callable, Any, Optional, Dict, Union
from collections import deque
from dataclasses import dataclass
import queue
from concurrent.futures import ThreadPoolExecutor
from .events import PipelineEvent
from .listener import EventListener


@dataclass
class EventBatch:
    """事件批次"""
    events: List[PipelineEvent]
    timestamp: float
    batch_id: str


class AsyncEventDispatcher:
    """
    异步事件分发器
    
    特性:
    1. 批量处理 - 减少线程切换开销
    2. 异步分发 - 不阻塞主执行流程
    3. 背压控制 - 防止内存过度使用
    4. 错误隔离 - 监听器异常不影响其他监听器
    """
    
    def __init__(self, 
                 max_queue_size: int = 10000,
                 batch_size: int = 50,
                 batch_timeout: float = 0.1,
                 max_workers: int = 2):
        
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_workers = max_workers
        
        # 事件队列
        self.event_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        
        # 监听器管理
        self.listeners: List[EventListener] = []
        self.async_listeners: List[Callable] = []
        self.listener_lock = threading.Lock()
        
        # 分发控制
        self._running = False
        self._dispatcher_thread: Optional[threading.Thread] = None
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        
        # 性能统计
        self.stats = {
            'events_queued': 0,
            'events_processed': 0,
            'batches_processed': 0,
            'listener_errors': 0,
            'queue_full_drops': 0
        }
    
    def start(self):
        """启动异步事件分发"""
        if self._running:
            return
        
        self._running = True
        self._thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self._dispatcher_thread = threading.Thread(
            target=self._dispatch_loop,
            daemon=True,
            name="AsyncEventDispatcher"
        )
        self._dispatcher_thread.start()
    
    def stop(self, timeout: float = 5.0):
        """停止异步事件分发"""
        if not self._running:
            return
        
        self._running = False
        
        # 等待分发线程结束
        if self._dispatcher_thread:
            self._dispatcher_thread.join(timeout=timeout)
        
        # 关闭线程池
        if self._thread_pool:
            self._thread_pool.shutdown(wait=True, timeout=timeout)
    
    def add_listener(self, listener: Union[EventListener, Callable]):
        """添加事件监听器"""
        with self.listener_lock:
            if isinstance(listener, EventListener):
                if listener not in self.listeners:
                    self.listeners.append(listener)
            elif callable(listener):
                if listener not in self.async_listeners:
                    self.async_listeners.append(listener)
    
    def remove_listener(self, listener: Union[EventListener, Callable]):
        """移除事件监听器"""
        with self.listener_lock:
            if isinstance(listener, EventListener):
                if listener in self.listeners:
                    self.listeners.remove(listener)
            elif callable(listener):
                if listener in self.async_listeners:
                    self.async_listeners.remove(listener)
    
    def emit_event(self, event: PipelineEvent) -> bool:
        """发送事件（非阻塞）"""
        try:
            self.event_queue.put_nowait(event)
            self.stats['events_queued'] += 1
            return True
        except queue.Full:
            self.stats['queue_full_drops'] += 1
            return False
    
    def emit_events(self, events: List[PipelineEvent]) -> int:
        """批量发送事件"""
        queued_count = 0
        for event in events:
            if self.emit_event(event):
                queued_count += 1
        return queued_count
    
    def _dispatch_loop(self):
        """事件分发主循环"""
        batch = []
        last_batch_time = time.time()
        
        while self._running:
            try:
                # 尝试获取事件
                try:
                    timeout = max(0.01, self.batch_timeout - (time.time() - last_batch_time))
                    event = self.event_queue.get(timeout=timeout)
                    batch.append(event)
                except queue.Empty:
                    event = None
                
                current_time = time.time()
                
                # 检查是否应该处理当前批次
                should_process_batch = (
                    len(batch) >= self.batch_size or
                    (batch and current_time - last_batch_time >= self.batch_timeout) or
                    not self._running
                )
                
                if should_process_batch and batch:
                    # 处理批次
                    self._process_event_batch(batch)
                    batch = []
                    last_batch_time = current_time
                
            except Exception as e:
                print(f"AsyncEventDispatcher error: {e}")
                time.sleep(0.1)
        
        # 处理剩余的事件
        if batch:
            self._process_event_batch(batch)
    
    def _process_event_batch(self, events: List[PipelineEvent]):
        """处理事件批次"""
        if not events:
            return
        
        batch = EventBatch(
            events=events,
            timestamp=time.time(),
            batch_id=f"batch_{int(time.time() * 1000)}"
        )
        
        # 获取当前监听器的快照
        with self.listener_lock:
            sync_listeners = self.listeners.copy()
            async_listeners = self.async_listeners.copy()
        
        # 异步处理同步监听器
        if sync_listeners:
            self._thread_pool.submit(self._notify_sync_listeners, sync_listeners, events)
        
        # 异步处理异步监听器
        if async_listeners:
            self._thread_pool.submit(self._notify_async_listeners, async_listeners, batch)
        
        self.stats['batches_processed'] += 1
        self.stats['events_processed'] += len(events)
    
    def _notify_sync_listeners(self, listeners: List[EventListener], events: List[PipelineEvent]):
        """通知同步监听器"""
        for listener in listeners:
            for event in events:
                try:
                    listener.on_event(event)
                except Exception as e:
                    self.stats['listener_errors'] += 1
                    # 记录错误但不中断处理
                    print(f"Listener error: {e}")
    
    def _notify_async_listeners(self, listeners: List[Callable], batch: EventBatch):
        """通知异步监听器"""
        for listener in listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    # 异步监听器
                    asyncio.create_task(listener(batch))
                else:
                    # 同步监听器
                    listener(batch)
            except Exception as e:
                self.stats['listener_errors'] += 1
                print(f"Async listener error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'queue_size': self.event_queue.qsize(),
            'listener_count': len(self.listeners) + len(self.async_listeners),
            'running': self._running
        }


class BufferedEventNotifier:
    """
    缓冲事件通知器
    为算子提供的高性能事件通知接口
    """
    
    def __init__(self, dispatcher: AsyncEventDispatcher):
        self.dispatcher = dispatcher
        self.buffer: List[PipelineEvent] = []
        self.buffer_lock = threading.Lock()
        self.max_buffer_size = 20
        self.last_flush = time.time()
        self.flush_interval = 0.05  # 50ms
    
    def notify(self, event: PipelineEvent):
        """通知事件（可能被缓冲）"""
        with self.buffer_lock:
            self.buffer.append(event)
            
            # 检查是否需要立即刷新
            current_time = time.time()
            should_flush = (
                len(self.buffer) >= self.max_buffer_size or
                current_time - self.last_flush >= self.flush_interval
            )
            
            if should_flush:
                self._flush_buffer()
    
    def flush(self):
        """立即刷新缓冲区"""
        with self.buffer_lock:
            self._flush_buffer()
    
    def _flush_buffer(self):
        """刷新缓冲区（需要持有锁）"""
        if not self.buffer:
            return
        
        events_to_send = self.buffer.copy()
        self.buffer.clear()
        self.last_flush = time.time()
        
        # 异步发送事件
        self.dispatcher.emit_events(events_to_send)


class AsyncEventSystem:
    """
    异步事件系统
    整合了分发器和通知器的完整事件系统
    """
    
    def __init__(self, 
                 max_queue_size: int = 10000,
                 batch_size: int = 50,
                 batch_timeout: float = 0.1):
        
        self.dispatcher = AsyncEventDispatcher(
            max_queue_size=max_queue_size,
            batch_size=batch_size,
            batch_timeout=batch_timeout
        )
        
        self._notifiers: Dict[str, BufferedEventNotifier] = {}
        self._notifier_lock = threading.Lock()
    
    def start(self):
        """启动事件系统"""
        self.dispatcher.start()
    
    def stop(self, timeout: float = 5.0):
        """停止事件系统"""
        # 刷新所有通知器
        with self._notifier_lock:
            for notifier in self._notifiers.values():
                notifier.flush()
        
        self.dispatcher.stop(timeout)
    
    def add_listener(self, listener: Union[EventListener, Callable]):
        """添加全局事件监听器"""
        self.dispatcher.add_listener(listener)
    
    def remove_listener(self, listener: Union[EventListener, Callable]):
        """移除全局事件监听器"""
        self.dispatcher.remove_listener(listener)
    
    def get_notifier(self, operator_name: str) -> BufferedEventNotifier:
        """获取算子的事件通知器"""
        with self._notifier_lock:
            if operator_name not in self._notifiers:
                self._notifiers[operator_name] = BufferedEventNotifier(self.dispatcher)
            return self._notifiers[operator_name]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return {
            'dispatcher': self.dispatcher.get_stats(),
            'notifier_count': len(self._notifiers)
        }


# 全局异步事件系统
_global_event_system: Optional[AsyncEventSystem] = None


def get_global_event_system() -> AsyncEventSystem:
    """获取全局异步事件系统"""
    global _global_event_system
    if _global_event_system is None:
        _global_event_system = AsyncEventSystem()
        _global_event_system.start()
    return _global_event_system


def create_async_event_system(**kwargs) -> AsyncEventSystem:
    """创建异步事件系统"""
    system = AsyncEventSystem(**kwargs)
    system.start()
    return system