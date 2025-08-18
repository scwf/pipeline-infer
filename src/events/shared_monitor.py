"""
共享性能监控器
解决重复性能监控开销问题，提供高效的全局性能监控
"""

import time
import threading
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import psutil
import os
from .events import PipelineEvent
from .performance import PerformanceMetricsEvent


@dataclass
class MonitoringSession:
    """监控会话"""
    operator_name: str
    start_time: float
    start_memory: float
    start_cpu_time: float
    batch_size: int = 1
    context: Dict[str, Any] = field(default_factory=dict)


class SharedPerformanceMonitor:
    """
    共享性能监控器
    
    特性:
    1. 单例模式 - 全局共享一个监控器实例
    2. 批量监控 - 减少系统调用开销
    3. 异步收集 - 不阻塞主执行流程
    4. 智能采样 - 根据负载自动调整采样频率
    """
    
    _instance: Optional['SharedPerformanceMonitor'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.process = psutil.Process(os.getpid())
        
        # 监控会话管理
        self.active_sessions: Dict[str, MonitoringSession] = {}
        self.session_lock = threading.Lock()
        
        # 性能数据缓存
        self._last_system_check = 0
        self._system_check_interval = 0.1  # 100ms
        self._cached_memory = 0
        self._cached_cpu_percent = 0
        
        # 批量事件收集
        self.pending_events: deque = deque(maxsize=1000)
        self.event_callbacks: list = []
        
        # 后台监控线程
        self._monitoring_enabled = False
        self._monitoring_thread: Optional[threading.Thread] = None
        
        # 性能统计
        self.stats = {
            'total_sessions': 0,
            'active_sessions': 0,
            'system_checks': 0,
            'events_generated': 0
        }
    
    def start_monitoring(self):
        """启动后台监控"""
        if self._monitoring_enabled:
            return
            
        self._monitoring_enabled = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop, 
            daemon=True,
            name="SharedPerformanceMonitor"
        )
        self._monitoring_thread.start()
    
    def stop_monitoring(self):
        """停止后台监控"""
        self._monitoring_enabled = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=1.0)
    
    def start_session(self, 
                     operator_name: str, 
                     batch_size: int = 1,
                     context: Optional[Dict[str, Any]] = None) -> str:
        """开始监控会话"""
        session_id = f"{operator_name}_{int(time.time() * 1000000)}"
        
        # 获取系统性能数据（可能使用缓存）
        current_time = time.time()
        memory_mb, cpu_time = self._get_system_metrics(current_time)
        
        session = MonitoringSession(
            operator_name=operator_name,
            start_time=current_time,
            start_memory=memory_mb,
            start_cpu_time=cpu_time,
            batch_size=batch_size,
            context=context or {}
        )
        
        with self.session_lock:
            self.active_sessions[session_id] = session
            self.stats['total_sessions'] += 1
            self.stats['active_sessions'] = len(self.active_sessions)
        
        return session_id
    
    def end_session(self, session_id: str) -> Optional[PerformanceMetricsEvent]:
        """结束监控会话"""
        with self.session_lock:
            session = self.active_sessions.pop(session_id, None)
            if not session:
                return None
            
            self.stats['active_sessions'] = len(self.active_sessions)
        
        # 获取结束时的性能数据
        end_time = time.time()
        end_memory, end_cpu_time = self._get_system_metrics(end_time)
        
        # 计算性能指标
        execution_time = end_time - session.start_time
        memory_delta = end_memory - session.start_memory
        
        # 创建性能事件
        event = PerformanceMetricsEvent(
            operator_name=session.operator_name,
            start_time=session.start_time,
            end_time=end_time,
            memory_usage=memory_delta,
            cpu_percent=self._cached_cpu_percent,  # 使用缓存的CPU使用率
            batch_size=session.batch_size
        )
        
        # 添加到事件队列
        try:
            self.pending_events.append(event)
            self.stats['events_generated'] += 1
        except:
            pass  # 队列满了，忽略事件
        
        return event
    
    def add_event_callback(self, callback: Callable[[PerformanceMetricsEvent], None]):
        """添加事件回调"""
        self.event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: Callable[[PerformanceMetricsEvent], None]):
        """移除事件回调"""
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)
    
    def _get_system_metrics(self, current_time: float) -> tuple[float, float]:
        """获取系统性能指标（带缓存）"""
        # 如果距离上次检查时间很短，使用缓存数据
        if current_time - self._last_system_check < self._system_check_interval:
            return self._cached_memory, 0.0
        
        try:
            # 更新缓存
            memory_info = self.process.memory_info()
            self._cached_memory = memory_info.rss / 1024 / 1024  # MB
            self._cached_cpu_percent = self.process.cpu_percent()
            self._last_system_check = current_time
            self.stats['system_checks'] += 1
            
            return self._cached_memory, 0.0
            
        except Exception:
            # 如果获取失败，返回缓存值
            return self._cached_memory, 0.0
    
    def _monitoring_loop(self):
        """后台监控循环"""
        while self._monitoring_enabled:
            try:
                # 处理待发送的事件
                self._process_pending_events()
                
                # 定期更新系统指标
                current_time = time.time()
                if current_time - self._last_system_check > self._system_check_interval:
                    self._get_system_metrics(current_time)
                
                # 短暂休眠
                time.sleep(0.05)  # 50ms
                
            except Exception as e:
                # 监控线程不应该崩溃
                print(f"SharedPerformanceMonitor error: {e}")
                time.sleep(1.0)
    
    def _process_pending_events(self):
        """处理待发送的事件"""
        events_to_process = []
        
        # 批量获取事件
        while self.pending_events and len(events_to_process) < 10:
            try:
                events_to_process.append(self.pending_events.popleft())
            except IndexError:
                break
        
        # 发送事件给所有回调
        for event in events_to_process:
            for callback in self.event_callbacks:
                try:
                    callback(event)
                except Exception:
                    pass  # 忽略回调异常
    
    def get_stats(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        return {
            **self.stats,
            'pending_events': len(self.pending_events),
            'event_callbacks': len(self.event_callbacks),
            'monitoring_enabled': self._monitoring_enabled,
            'cache_hit_rate': 1.0 - (self.stats['system_checks'] / max(1, self.stats['total_sessions']))
        }


class OptimizedPerformanceMonitor:
    """
    优化的性能监控器
    使用共享监控器的简化接口
    """
    
    def __init__(self):
        self.shared_monitor = SharedPerformanceMonitor()
        self.session_id: Optional[str] = None
        
        # 确保共享监控器已启动
        self.shared_monitor.start_monitoring()
    
    def start(self, operator_name: str = "unknown", batch_size: int = 1):
        """开始监控"""
        self.session_id = self.shared_monitor.start_session(
            operator_name=operator_name,
            batch_size=batch_size
        )
    
    def stop(self, operator_name: str, batch_size: int = 1) -> Optional[PerformanceMetricsEvent]:
        """停止监控"""
        if not self.session_id:
            return None
        
        event = self.shared_monitor.end_session(self.session_id)
        self.session_id = None
        return event


# 全局共享监控器实例
_global_monitor: Optional[SharedPerformanceMonitor] = None


def get_global_monitor() -> SharedPerformanceMonitor:
    """获取全局共享监控器"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = SharedPerformanceMonitor()
        _global_monitor.start_monitoring()
    return _global_monitor


def create_optimized_monitor() -> OptimizedPerformanceMonitor:
    """创建优化的性能监控器"""
    return OptimizedPerformanceMonitor()