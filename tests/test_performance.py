import pytest
import time
from src.events.performance import (
    PerformanceMetricsEvent,
    PerformanceMonitor,
    PerformanceEventListener
)
from src.events.events import PipelineEvent

class TestPerformanceMetricsEvent:
    """测试性能指标事件类"""
    
    def test_metrics_event_creation(self):
        """测试性能指标事件创建"""
        event = PerformanceMetricsEvent(
            operator_name="test_op",
            start_time=100.0,
            end_time=105.0,
            memory_usage=50.0,
            cpu_percent=25.0,
            batch_size=10
        )
        
        assert event.operator_name == "test_op"
        assert event.start_time == 100.0
        assert event.end_time == 105.0
        assert event.memory_usage == 50.0
        assert event.cpu_percent == 25.0
        assert event.batch_size == 10
    
    def test_execution_time_calculation(self):
        """测试执行时间计算"""
        event = PerformanceMetricsEvent(
            operator_name="test_op",
            start_time=100.0,
            end_time=105.0,
            memory_usage=50.0,
            cpu_percent=25.0
        )
        
        assert event.execution_time == 5.0
    
    def test_throughput_calculation(self):
        """测试吞吐量计算"""
        event = PerformanceMetricsEvent(
            operator_name="test_op",
            start_time=100.0,
            end_time=105.0,
            memory_usage=50.0,
            cpu_percent=25.0,
            batch_size=10
        )
        
        assert event.throughput == 2.0  # 10 samples / 5 seconds

class TestPerformanceMonitor:
    """测试性能监控器"""
    
    def test_monitor_lifecycle(self):
        """测试监控器的生命周期"""
        monitor = PerformanceMonitor()
        monitor.start()
        
        # 模拟一些操作
        time.sleep(0.1)
        
        event = monitor.stop("test_op", batch_size=5)
        
        assert isinstance(event, PerformanceMetricsEvent)
        assert event.operator_name == "test_op"
        assert event.batch_size == 5
        assert event.execution_time > 0
        assert event.memory_usage >= 0
        assert 0 <= event.cpu_percent <= 100

class TestPerformanceEventListener:
    """测试性能事件监听器"""
    
    def test_event_handling(self):
        """测试事件处理"""
        listener = PerformanceEventListener()
        event = PerformanceMetricsEvent(
            operator_name="test_op",
            start_time=100.0,
            end_time=105.0,
            memory_usage=50.0,
            cpu_percent=25.0
        )
        
        listener.on_event(event)
        
        stats = listener.get_operator_statistics("test_op")
        assert stats["total_time"] == 5.0
        assert stats["avg_memory_usage"] == 50.0
        assert stats["avg_cpu_percent"] == 25.0
    
    def test_multiple_events_statistics(self):
        """测试多个事件的统计"""
        listener = PerformanceEventListener()
        
        # 添加多个事件
        events = [
            PerformanceMetricsEvent(
                operator_name="test_op",
                start_time=100.0,
                end_time=105.0,
                memory_usage=50.0,
                cpu_percent=25.0,
                batch_size=10
            ),
            PerformanceMetricsEvent(
                operator_name="test_op",
                start_time=200.0,
                end_time=207.0,
                memory_usage=60.0,
                cpu_percent=35.0,
                batch_size=10
            )
        ]
        
        for event in events:
            listener.on_event(event)
        
        stats = listener.get_operator_statistics("test_op")
        assert stats["total_time"] == 12.0  # 5.0 + 7.0
        assert stats["avg_memory_usage"] == 55.0  # (50.0 + 60.0) / 2
        assert stats["avg_cpu_percent"] == 30.0  # (25.0 + 35.0) / 2
    
    def test_non_performance_event_handling(self):
        """测试处理非性能事件"""
        listener = PerformanceEventListener()
        event = PipelineEvent("test_op")
        
        # 不应抛出异常
        listener.on_event(event)
        
        # 不应记录任何指标
        stats = listener.get_operator_statistics("test_op")
        assert stats == {}
    
    def test_unknown_operator_statistics(self):
        """测试获取未知算子的统计信息"""
        listener = PerformanceEventListener()
        stats = listener.get_operator_statistics("unknown_op")
        assert stats == {}