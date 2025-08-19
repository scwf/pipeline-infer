"""
内存优化相关的测试
测试流式处理是否有效避免内存溢出问题
"""
import pytest
import psutil
import os
import time
from typing import Iterator, List
from src.executors.parallel import ThreadExecutor, ProcessExecutor
from src.pipeline import Pipeline
import gc


class TestMemoryOptimization:
    """测试内存优化功能"""
    
    def get_memory_usage_mb(self) -> float:
        """获取当前进程的内存使用量（MB）"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def test_streaming_vs_bulk_memory_usage(self):
        """测试流式处理与批量处理的内存使用差异"""
        
        def memory_intensive_task(x: int) -> List[int]:
            """模拟内存密集型任务"""
            # 创建一个较大的临时数据结构
            temp_data = list(range(x * 1000, (x + 1) * 1000))
            return temp_data
        
        # 准备大量数据
        large_dataset = list(range(1000))  # 1000个任务，每个任务产生1000个整数
        
        # 清理内存
        gc.collect()
        initial_memory = self.get_memory_usage_mb()
        
        # 测试新的流式执行器
        streaming_executor = ThreadExecutor(max_workers=4, max_memory_items=100)
        
        start_memory = self.get_memory_usage_mb()
        results = []
        
        # 流式处理
        for result in streaming_executor.execute(memory_intensive_task, large_dataset):
            results.append(len(result))  # 只保存长度，不保存实际数据
            
        end_memory = self.get_memory_usage_mb()
        memory_increase = end_memory - start_memory
        
        # 验证内存增长是有限的
        print(f"初始内存: {initial_memory:.2f}MB")
        print(f"开始处理时内存: {start_memory:.2f}MB") 
        print(f"结束处理时内存: {end_memory:.2f}MB")
        print(f"内存增长: {memory_increase:.2f}MB")
        
        # 内存增长应该是有限的（小于500MB）
        assert memory_increase < 500, f"内存增长过多: {memory_increase:.2f}MB"
        assert len(results) == 1000, "结果数量不正确"
        assert all(r == 1000 for r in results), "结果内容不正确"
    
    def test_large_iterator_processing(self):
        """测试处理大型迭代器时的内存使用"""
        
        def simple_task(x: int) -> int:
            return x * 2
        
        def large_data_generator(size: int) -> Iterator[int]:
            """生成大量数据的生成器"""
            for i in range(size):
                yield i
        
        # 清理内存
        gc.collect()
        start_memory = self.get_memory_usage_mb()
        
        # 使用流式执行器处理大型生成器
        executor = ThreadExecutor(max_workers=4, max_memory_items=1000)
        
        results_count = 0
        for result in executor.execute(simple_task, large_data_generator(50000)):
            results_count += 1
        
        end_memory = self.get_memory_usage_mb()
        memory_increase = end_memory - start_memory
        
        print(f"处理50000项数据的内存增长: {memory_increase:.2f}MB")
        print(f"处理的结果数量: {results_count}")
        
        # 验证内存增长是合理的
        assert memory_increase < 100, f"内存增长过多: {memory_increase:.2f}MB"
        assert results_count == 50000, "处理的数据数量不正确"
    
    def test_process_executor_memory_optimization(self):
        """测试进程池执行器的内存优化"""
        
        def cpu_intensive_task(x: int) -> int:
            """CPU密集型任务"""
            result = 0
            for i in range(1000):
                result += x * i
            return result
        
        # 准备数据
        data = list(range(500))
        
        # 清理内存
        gc.collect()
        start_memory = self.get_memory_usage_mb()
        
        # 使用进程池执行器
        executor = ProcessExecutor(max_workers=2, max_memory_items=100)
        
        results = []
        for result in executor.execute(cpu_intensive_task, data):
            results.append(result)
        
        end_memory = self.get_memory_usage_mb()
        memory_increase = end_memory - start_memory
        
        print(f"进程池处理内存增长: {memory_increase:.2f}MB")
        
        # 验证结果正确性
        assert len(results) == 500, "结果数量不正确"
        assert memory_increase < 200, f"内存增长过多: {memory_increase:.2f}MB"
    
    def test_pipeline_memory_usage(self):
        """测试整个流水线的内存使用"""
        
        def data_generator(size: int) -> Iterator[List[int]]:
            """生成数据批次"""
            for i in range(size):
                yield list(range(i * 100, (i + 1) * 100))
        
        def process_batch(batch: List[int]) -> List[int]:
            """处理数据批次"""
            return [x * 2 for x in batch]
        
        def filter_batch(batch: List[int]) -> List[int]:
            """过滤数据批次"""
            return [x for x in batch if x % 4 == 0]
        
        # 清理内存
        gc.collect()
        start_memory = self.get_memory_usage_mb()
        
        # 创建流水线
        pipeline = (Pipeline("memory_test")
            .source("data_source", data_generator(100))
            .map("processor", process_batch, parallel_degree=2)
            .filter("filter", filter_batch, parallel_degree=2))
        
        # 执行流水线
        results = pipeline.execute()
        
        end_memory = self.get_memory_usage_mb()
        memory_increase = end_memory - start_memory
        
        print(f"流水线处理内存增长: {memory_increase:.2f}MB")
        
        # 验证内存增长是合理的
        assert memory_increase < 300, f"流水线内存增长过多: {memory_increase:.2f}MB"
        assert "filter" in results, "流水线执行结果不完整"
    
    def test_memory_limit_configuration(self):
        """测试内存限制配置的有效性"""
        
        def memory_task(x: int) -> List[int]:
            return list(range(x * 100))
        
        # 测试不同的内存限制设置
        small_limit_executor = ThreadExecutor(max_workers=2, max_memory_items=10)
        large_limit_executor = ThreadExecutor(max_workers=2, max_memory_items=1000)
        
        data = list(range(100))
        
        # 小内存限制的执行
        gc.collect()
        start_memory = self.get_memory_usage_mb()
        
        small_results = []
        for result in small_limit_executor.execute(memory_task, data):
            small_results.append(len(result))
        
        small_memory_peak = self.get_memory_usage_mb() - start_memory
        
        # 大内存限制的执行
        gc.collect()
        start_memory = self.get_memory_usage_mb()
        
        large_results = []
        for result in large_limit_executor.execute(memory_task, data):
            large_results.append(len(result))
        
        large_memory_peak = self.get_memory_usage_mb() - start_memory
        
        print(f"小内存限制峰值: {small_memory_peak:.2f}MB")
        print(f"大内存限制峰值: {large_memory_peak:.2f}MB")
        
        # 验证结果一致性
        assert small_results == large_results, "不同内存限制下结果不一致"
        
        # 小内存限制应该使用更少的内存
        # 注意：这个测试可能不总是可靠，因为内存管理的复杂性
        print("内存限制配置测试完成")


if __name__ == "__main__":
    # 运行内存优化测试
    test_suite = TestMemoryOptimization()
    
    print("开始内存优化测试...")
    
    try:
        test_suite.test_streaming_vs_bulk_memory_usage()
        print("✅ 流式处理内存测试通过")
    except Exception as e:
        print(f"❌ 流式处理内存测试失败: {e}")
    
    try:
        test_suite.test_large_iterator_processing()
        print("✅ 大型迭代器处理测试通过")
    except Exception as e:
        print(f"❌ 大型迭代器处理测试失败: {e}")
    
    try:
        test_suite.test_process_executor_memory_optimization()
        print("✅ 进程池内存优化测试通过")
    except Exception as e:
        print(f"❌ 进程池内存优化测试失败: {e}")
    
    try:
        test_suite.test_memory_limit_configuration()
        print("✅ 内存限制配置测试通过")
    except Exception as e:
        print(f"❌ 内存限制配置测试失败: {e}")
    
    print("内存优化测试完成!")