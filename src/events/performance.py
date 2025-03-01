import time
from dataclasses import dataclass
from typing import Dict, Any
from .events import PipelineEvent
from .listener import EventListener
import logging
import psutil
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetricsEvent(PipelineEvent):
    """性能指标事件"""
    start_time: float
    end_time: float
    memory_usage: float
    cpu_percent: float
    batch_size: int = 1
    
    @property
    def execution_time(self) -> float:
        """计算执行时间（秒）"""
        return self.end_time - self.start_time
    
    @property
    def throughput(self) -> float:
        """计算吞吐量（样本/秒）"""
        return self.batch_size / self.execution_time if self.execution_time > 0 else 0

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_time = 0
        self.start_memory = 0
    
    def start(self):
        """开始监控"""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
    
    def stop(self, operator_name: str, batch_size: int = 1) -> PerformanceMetricsEvent:
        """停止监控并生成性能事件"""
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        cpu_percent = self.process.cpu_percent()
        
        return PerformanceMetricsEvent(
            operator_name=operator_name,
            start_time=self.start_time,
            end_time=end_time,
            memory_usage=end_memory - self.start_memory,
            cpu_percent=cpu_percent,
            batch_size=batch_size
        )

class PerformanceEventListener(EventListener):
    """性能事件监听器"""
    
    def __init__(self):
        self.operator_metrics: Dict[str, list] = {}
    
    def on_event(self, event: PipelineEvent) -> None:
        """处理性能事件"""
        if isinstance(event, PerformanceMetricsEvent):
            metrics = event
            self.operator_metrics.setdefault(metrics.operator_name, [])
            self.operator_metrics[metrics.operator_name].append(metrics)
            
            # 记录性能指标
            logger.info(
                f"性能指标 - 算子: {metrics.operator_name}\n"
                f"  执行时间: {metrics.execution_time:.3f}秒\n"
                f"  吞吐量: {metrics.throughput:.2f}样本/秒\n"
                f"  内存使用: {metrics.memory_usage:.2f}MB\n"
                f"  CPU使用率: {metrics.cpu_percent:.1f}%"
            )
    
    def get_operator_statistics(self, operator_name: str) -> Dict[str, float]:
        """获取算子的统计信息"""
        if operator_name not in self.operator_metrics:
            return {}
            
        metrics = self.operator_metrics[operator_name]
        total_time = sum(m.execution_time for m in metrics)
        avg_throughput = sum(m.throughput for m in metrics) / len(metrics)
        avg_memory = sum(m.memory_usage for m in metrics) / len(metrics)
        avg_cpu = sum(m.cpu_percent for m in metrics) / len(metrics)
        
        return {
            "total_time": total_time,
            "avg_throughput": avg_throughput,
            "avg_memory_usage": avg_memory,
            "avg_cpu_percent": avg_cpu
        }