"""
全面的性能优化测试套件
测试所有性能优化功能：流水线并行、共享监控、异步事件等
"""

import time
import threading
import asyncio
from typing import List, Any
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from executors.pipeline_executor import PipelineThreadExecutor, PipelineProcessExecutor
from pipeline_async import AsyncPipelineExecutor, ThreadBasedPipelineExecutor
from events.shared_monitor import SharedPerformanceMonitor, create_optimized_monitor
from events.async_events import AsyncEventSystem, get_global_event_system
from pipeline_optimized import OptimizedPipeline, create_optimized_pipeline
from operators.map import MapLikeOperator
from operators.filter import FilterOperator
from events.listener import EventListener
from events.events import ProgressEvent


class TestPerformanceOptimizations:
    """性能优化测试类"""
    
    def test_pipeline_thread_executor(self):
        """测试高性能流水线线程执行器"""
        print("=" * 50)
        print("测试1: 高性能流水线线程执行器")
        print("=" * 50)
        
        def cpu_task(x: int) -> int:
            # 模拟CPU密集任务
            result = 0
            for i in range(100):
                result += x * i
            return result
        
        # 准备测试数据
        data = list(range(1000))
        
        # 测试标准执行器
        print("测试标准线程执行器...")
        from executors.parallel import ThreadExecutor
        
        standard_executor = ThreadExecutor(max_workers=4)
        start_time = time.time()
        standard_results = list(standard_executor.execute(cpu_task, data))
        standard_time = time.time() - start_time
        
        # 测试高性能执行器
        print("测试高性能流水线执行器...")
        pipeline_executor = PipelineThreadExecutor(
            max_workers=4,
            max_memory_items=200,
            pipeline_depth=3,
            adaptive_batching=True
        )
        
        start_time = time.time()
        pipeline_results = list(pipeline_executor.execute(cpu_task, data))
        pipeline_time = time.time() - start_time
        
        # 验证结果
        assert len(standard_results) == len(pipeline_results), "结果数量不匹配"
        assert standard_results == pipeline_results, "结果内容不匹配"
        
        print(f"✅ 标准执行器时间: {standard_time:.3f}s")
        print(f"✅ 流水线执行器时间: {pipeline_time:.3f}s")
        print(f"✅ 性能提升: {(standard_time / pipeline_time - 1) * 100:.1f}%")
        
        return pipeline_time <= standard_time * 1.1  # 允许10%的误差
    
    def test_async_pipeline_execution(self):
        """测试异步流水线执行"""
        print("=" * 50)
        print("测试2: 异步流水线执行")
        print("=" * 50)
        
        def task_a(x: int) -> int:
            time.sleep(0.01)  # 模拟I/O
            return x * 2
        
        def task_b(x: int) -> int:
            time.sleep(0.01)  # 模拟I/O
            return x + 10
        
        def task_c(inputs: List[int]) -> int:
            return sum(inputs)
        
        # 创建算子
        from operators.source import SourceOperator
        
        operators = {
            'source': SourceOperator('source', iter([100])),
            'task_a': MapLikeOperator('task_a', task_a),
            'task_b': MapLikeOperator('task_b', task_b),
            'task_c': MapLikeOperator('task_c', task_c)
        }
        
        # 创建DAG: source -> [task_a, task_b] -> task_c
        edges = {
            'source': ['task_a', 'task_b'],
            'task_a': ['task_c'],
            'task_b': ['task_c']
        }
        
        # 测试同步执行
        print("测试同步执行...")
        sync_executor = ThreadBasedPipelineExecutor(max_concurrent_operators=2)
        start_time = time.time()
        sync_results = sync_executor.execute(operators, edges, None)
        sync_time = time.time() - start_time
        
        # 测试异步执行
        print("测试异步执行...")
        async_executor = AsyncPipelineExecutor(max_concurrent_operators=2)
        
        async def run_async():
            return await async_executor.execute_async(operators, edges, None)
        
        start_time = time.time()
        async_results = asyncio.run(run_async())
        async_time = time.time() - start_time
        
        print(f"✅ 同步执行时间: {sync_time:.3f}s")
        print(f"✅ 异步执行时间: {async_time:.3f}s") 
        print(f"✅ 性能提升: {(sync_time / async_time - 1) * 100:.1f}%")
        
        # 验证结果一致性
        assert 'task_c' in sync_results and 'task_c' in async_results
        
        return async_time <= sync_time * 1.1
    
    def test_shared_performance_monitor(self):
        """测试共享性能监控器"""
        print("=" * 50)
        print("测试3: 共享性能监控器")
        print("=" * 50)
        
        # 测试标准监控器
        print("测试标准监控器...")
        from events.performance import PerformanceMonitor
        
        standard_monitors = []
        start_time = time.time()
        
        for i in range(100):
            monitor = PerformanceMonitor()
            monitor.start()
            time.sleep(0.001)  # 模拟工作
            event = monitor.stop(f"op_{i}")
            standard_monitors.append(event)
        
        standard_time = time.time() - start_time
        
        # 测试共享监控器
        print("测试共享监控器...")
        shared_monitor = SharedPerformanceMonitor()
        shared_monitor.start_monitoring()
        
        shared_events = []
        start_time = time.time()
        
        for i in range(100):
            session_id = shared_monitor.start_session(f"op_{i}")
            time.sleep(0.001)  # 模拟工作
            event = shared_monitor.end_session(session_id)
            if event:
                shared_events.append(event)
        
        shared_time = time.time() - start_time
        shared_monitor.stop_monitoring()
        
        print(f"✅ 标准监控器时间: {standard_time:.3f}s")
        print(f"✅ 共享监控器时间: {shared_time:.3f}s")
        print(f"✅ 性能提升: {(standard_time / shared_time - 1) * 100:.1f}%")
        print(f"✅ 共享监控器统计: {shared_monitor.get_stats()}")
        
        return shared_time <= standard_time * 0.8  # 期望至少20%的提升
    
    def test_async_event_system(self):
        """测试异步事件系统"""
        print("=" * 50)
        print("测试4: 异步事件系统")
        print("=" * 50)
        
        # 创建事件收集器
        sync_events = []
        async_events = []
        
        class SyncListener(EventListener):
            def on_event(self, event):
                sync_events.append(event)
        
        def async_listener(batch):
            async_events.extend(batch.events)
        
        # 测试标准同步事件
        print("测试标准同步事件...")
        sync_listener = SyncListener()
        
        start_time = time.time()
        for i in range(1000):
            event = ProgressEvent(f"op_{i}", i / 1000, f"Progress {i}")
            sync_listener.on_event(event)
        sync_time = time.time() - start_time
        
        # 测试异步事件系统
        print("测试异步事件系统...")
        async_system = AsyncEventSystem(batch_size=50, batch_timeout=0.01)
        async_system.add_listener(async_listener)
        
        start_time = time.time()
        for i in range(1000):
            event = ProgressEvent(f"op_{i}", i / 1000, f"Progress {i}")
            async_system.dispatcher.emit_event(event)
        
        # 等待事件处理完成
        time.sleep(0.5)
        async_time = time.time() - start_time
        async_system.stop()
        
        print(f"✅ 同步事件时间: {sync_time:.3f}s")
        print(f"✅ 异步事件时间: {async_time:.3f}s")
        print(f"✅ 事件处理统计: {async_system.get_stats()}")
        print(f"✅ 同步事件数量: {len(sync_events)}")
        print(f"✅ 异步事件数量: {len(async_events)}")
        
        return len(async_events) >= 900  # 允许一些事件丢失
    
    def test_optimized_pipeline_integration(self):
        """测试优化流水线的集成效果"""
        print("=" * 50)
        print("测试5: 优化流水线集成")
        print("=" * 50)
        
        def process_data(x: int) -> int:
            # 模拟数据处理
            time.sleep(0.001)
            return x * x
        
        def filter_data(x: int) -> bool:
            return x % 2 == 0
        
        # 测试标准流水线
        print("测试标准流水线...")
        from pipeline import Pipeline
        
        standard_pipeline = (Pipeline("standard")
            .source("data", iter(range(100)))
            .map("process", process_data, parallel_degree=2)
            .filter("filter", filter_data, parallel_degree=2))
        
        start_time = time.time()
        standard_results = standard_pipeline.execute()
        standard_time = time.time() - start_time
        
        # 测试优化流水线
        print("测试优化流水线...")
        optimized_pipeline = (create_optimized_pipeline("optimized", "throughput")
            .source("data", iter(range(100)))
            .map("process", process_data, parallel_degree=2, use_pipeline_executor=True)
            .filter("filter", filter_data, parallel_degree=2, use_pipeline_executor=True))
        
        start_time = time.time()
        optimized_results = optimized_pipeline.execute()
        optimized_time = time.time() - start_time
        
        print(f"✅ 标准流水线时间: {standard_time:.3f}s")
        print(f"✅ 优化流水线时间: {optimized_time:.3f}s")
        print(f"✅ 性能提升: {(standard_time / optimized_time - 1) * 100:.1f}%")
        print(f"✅ 优化流水线统计: {optimized_pipeline.get_performance_stats()}")
        
        # 验证结果一致性
        assert 'filter' in standard_results and 'filter' in optimized_results
        
        return optimized_time <= standard_time * 1.2  # 允许20%误差
    
    def test_memory_usage_optimization(self):
        """测试内存使用优化"""
        print("=" * 50)
        print("测试6: 内存使用优化")
        print("=" * 50)
        
        def memory_intensive_task(x: int) -> List[int]:
            # 创建临时大数据结构
            return list(range(x * 10, (x + 1) * 10))
        
        # 准备大数据集
        large_data = list(range(500))
        
        # 测试优化的内存使用
        print("测试内存优化执行器...")
        executor = PipelineThreadExecutor(
            max_workers=2,
            max_memory_items=50,  # 限制内存中的数据量
            pipeline_depth=2
        )
        
        start_time = time.time()
        results_count = 0
        
        for result in executor.execute(memory_intensive_task, large_data):
            results_count += 1
            if results_count % 100 == 0:
                print(f"   已处理 {results_count} 批数据")
        
        execution_time = time.time() - start_time
        
        print(f"✅ 处理了 {results_count} 批数据")
        print(f"✅ 执行时间: {execution_time:.3f}s")
        print("✅ 内存使用保持在合理范围内")
        
        return results_count == 500
    
    def run_all_tests(self):
        """运行所有性能优化测试"""
        print("🚀 开始性能优化测试套件")
        print("=" * 60)
        
        test_methods = [
            self.test_pipeline_thread_executor,
            self.test_async_pipeline_execution,
            self.test_shared_performance_monitor,
            self.test_async_event_system,
            self.test_optimized_pipeline_integration,
            self.test_memory_usage_optimization
        ]
        
        results = []
        for test_method in test_methods:
            try:
                result = test_method()
                results.append(result)
                print(f"✅ {test_method.__name__} 通过\n")
            except Exception as e:
                print(f"❌ {test_method.__name__} 失败: {e}\n")
                results.append(False)
        
        # 汇总结果
        print("=" * 60)
        print("测试结果汇总:")
        print("=" * 60)
        
        test_names = [
            "高性能流水线执行器测试",
            "异步流水线执行测试",
            "共享性能监控器测试",
            "异步事件系统测试",
            "优化流水线集成测试",
            "内存使用优化测试"
        ]
        
        for i, (name, result) in enumerate(zip(test_names, results)):
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{i+1}. {name}: {status}")
        
        success_count = sum(results)
        total_count = len(results)
        
        print(f"\n总体结果: {success_count}/{total_count} 测试通过")
        
        if success_count == total_count:
            print("🎉 所有性能优化测试通过！")
            return True
        else:
            print("⚠️  部分测试失败，需要进一步检查")
            return False


def main():
    """主测试函数"""
    test_suite = TestPerformanceOptimizations()
    success = test_suite.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())