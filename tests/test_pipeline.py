import pytest
import numpy as np
from src.pipeline import Pipeline
from src.operators.source import SourceOperator, ImageSourceOperator
from src.operators.map import MapLikeOperator
from src.events.listener import ConsoleEventListener, EventListener
from src.events.events import ProgressEvent
import time
from src.executors.parallel import ThreadExecutor, ProcessExecutor

class TestPipeline:
    def test_pipeline_basic_flow(self, temp_image_path):
        """测试基本的流水线流程"""
        # 准备
        def split_fn(image):
            assert image is not None, "输入图像不能为None"
            return [image[0:50, 0:50], image[50:100, 50:100]]
            
        def process_fn(tiles):
            if isinstance(tiles, list):
                return [tile + 1 for tile in tiles]
            return tiles + 1
            
        # 创建流水线
        pipeline = (Pipeline("test_pipeline")
            .read_image("source", temp_image_path)
            .map("splitter", split_fn)
            .map("processor", process_fn, parallel_degree=2))
        
        # 执行流水线
        results = pipeline.execute()
        
        # 验证结果
        assert "processor" in results
        assert isinstance(results["processor"], list)
        assert len(results["processor"]) == 2
        assert all(isinstance(r, np.ndarray) for r in results["processor"])
        assert all(r.shape == (50, 50, 3) for r in results["processor"])
    
    def test_pipeline_branching(self, temp_image_path):
        """测试流水线分支功能"""
        def process_fn1(x): 
            assert x is not None, "输入不能为None"
            return x + 1
        def process_fn2(x): return x + 2
        def merge_fn(x): return x
        
        # 创建带分支的流水线
        pipeline = (Pipeline("branch_test")
            .read_image("source", temp_image_path)
            .branch(
                MapLikeOperator("processor1", process_fn1),
                MapLikeOperator("processor2", process_fn2)
            )
            .map("merger", merge_fn))
        
        results = pipeline.execute()
        
        # 验证分支执行结果
        assert "processor1" in results
        assert "processor2" in results
        assert "merger" in results
    
    def test_pipeline_events(self, temp_image_path):
        """测试流水线事件通知"""
        events = []
        
        class TestListener(EventListener):
            def on_event(self, event):
                events.append(event)
        
        # 创建流水线
        pipeline = (Pipeline("event_test")
            .read_image("source", temp_image_path)
            .map("processor", lambda x: x))  # 修复语法错误
        
        # 添加监听器
        listener = TestListener()
        pipeline.add_listener(listener)
        
        # 执行流水线
        pipeline.execute()
        
        # 验证事件
        assert len(events) > 0
        assert any(isinstance(e, ProgressEvent) for e in events)
        
    def test_pipeline_validation(self):
        """测试流水线验证"""
        pipeline = Pipeline("validation_test")
        
        # 测试重复添加算子
        with pytest.raises(ValueError):
            pipeline.read_image("op1", "test.jpg").read_image("op1", "test.jpg")  # 修复语法错误
        
        # 测试在没有前置算子的情况下创建分支
        empty_pipeline = Pipeline("empty")
        with pytest.raises(ValueError):
            empty_pipeline.branch(
                MapLikeOperator("b1", lambda x: x),
                MapLikeOperator("b2", lambda x: x)
            )
    
    def test_pipeline_empty(self):
        """测试空流水线"""
        pipeline = Pipeline("empty")
        with pytest.raises(ValueError):
            pipeline.execute()
    
    def test_pipeline_complex_dag(self, temp_image_path):
        """测试复杂DAG结构"""
        def noop(x): return x
        
        # 创建一个复杂的DAG结构
        pipeline = (Pipeline("complex_dag")
            .read_image("source", temp_image_path)
            .branch(
                MapLikeOperator("branch1", noop),
                MapLikeOperator("branch2", noop)
            )
            .map("join1", noop)  # 使用map替代join
            .branch(
                MapLikeOperator("final1", noop),
                MapLikeOperator("final2", noop)
            ))
        
        results = pipeline.execute()
        
        # 验证所有节点都被执行
        expected_nodes = {"source", "branch1", "branch2", "join1", "final1", "final2"}
        assert set(results.keys()) == expected_nodes

    def test_pipeline_filter(self, temp_image_path):
        """测试过滤算子"""
        def split_fn(image):
            assert image is not None, "输入图像不能为None"
            return [image[i:i+10, :] for i in range(0, 100, 10)]
            
        def size_filter(tiles):
            if not isinstance(tiles, list):
                tiles = [tiles]
            return [tile for tile in tiles if tile.shape[0] * tile.shape[1] >= 500]
            
        def process_fn(tiles):
            if not isinstance(tiles, list):
                return tiles + 1
            return [tile + 1 for tile in tiles]
            
        # 创建带过滤的流水线
        pipeline = (Pipeline("filter_test")
            .read_image("source", temp_image_path)
            .map("splitter", split_fn)
            .filter("size_filter", size_filter)
            .map("processor", process_fn))
            
        results = pipeline.execute()
        
        # 验证结果
        assert "processor" in results
        filtered_results = results["processor"]
        assert isinstance(filtered_results, list)
        assert all(r.shape[0] * r.shape[1] >= 500 for r in filtered_results)

# 将函数定义移到测试函数外部
def slow_process(data):
    """模拟耗时操作"""
    time.sleep(0.1)
    return data + 1

def process_number(x):
    """数字处理函数"""
    time.sleep(0.01)
    return x * 2

def test_pipeline_sequential_vs_parallel(sample_image_data):
    """测试流水线的顺序执行和并发执行性能对比"""
    # 准备测试数据
    batch_size = 10
    input_data = [sample_image_data for _ in range(batch_size)]
    expected_result = [data + 1 for data in input_data]  # 预期结果
    
    # 1. 顺序执行
    sequential_pipeline = (Pipeline("sequential")
        .source("input", iter([input_data]))
        .map("process", slow_process))
    
    start_time = time.time()
    sequential_results = sequential_pipeline.execute()
    sequential_time = time.time() - start_time
    
    # 2. 并发执行 - 线程池
    thread_pipeline = (Pipeline("thread_parallel")
        .source("input", iter([input_data]))
        .map("process", slow_process, parallel_degree=4))
    
    start_time = time.time()
    thread_results = thread_pipeline.execute()
    thread_time = time.time() - start_time
    
    # 3. 并发执行 - 进程池
    process_pipeline = (Pipeline("process_parallel")
        .source("input", iter([input_data]))
        .map("process", slow_process, 
             parallel_degree=4, 
             executor_type=ProcessExecutor))
    
    start_time = time.time()
    process_results = process_pipeline.execute()
    process_time = time.time() - start_time
    
    # 验证结果正确性
    assert len(sequential_results["process"]) == batch_size
    assert len(thread_results["process"]) == batch_size
    assert len(process_results["process"]) == batch_size
    
    # 验证结果值正确性
    np.testing.assert_array_equal(sequential_results["process"], expected_result)
    np.testing.assert_array_equal(thread_results["process"], expected_result)
    np.testing.assert_array_equal(process_results["process"], expected_result)
    
    # 验证并发执行更快
    assert thread_time < sequential_time * 0.5  # 至少快一倍
    assert process_time < sequential_time * 0.8  # 进程有额外开销，
    
    # 打印执行时间对比
    print(f"\n执行时间对比:")
    print(f"顺序执行: {sequential_time:.2f}s")
    print(f"线程池执行: {thread_time:.2f}s")
    print(f"进程池执行: {process_time:.2f}s")

def test_pipeline_large_data_processing():
    """测试流水线处理大量数据的性能"""
    # 生成大量数据
    data_size = 1000
    input_data = list(range(data_size))
    expected_result = [x * 2 for x in input_data]  # 预期结果
    
    # 1. 顺序处理
    sequential_pipeline = (Pipeline("sequential")
        .source("input", iter([input_data]))
        .map("process", process_number))
    
    start_time = time.time()
    sequential_results = sequential_pipeline.execute()
    sequential_time = time.time() - start_time
    
    # 2. 并发处理 - 4个线程
    parallel_pipeline = (Pipeline("parallel")
        .source("input", iter([input_data]))
        .map("process", process_number, parallel_degree=4))
    
    start_time = time.time()
    parallel_results = parallel_pipeline.execute()
    parallel_time = time.time() - start_time
    
    # 验证结果数量
    assert len(sequential_results["process"]) == data_size
    assert len(parallel_results["process"]) == data_size
    
    # 验证结果值正确性
    assert sequential_results["process"] == expected_result
    assert parallel_results["process"] == expected_result
    
    # 验证结果顺序一致性
    assert sequential_results["process"] == parallel_results["process"]
    
    # 验证性能提升
    assert parallel_time < sequential_time * 0.5
    
    print(f"\n大数据处理时间对比:")
    print(f"顺序处理: {sequential_time:.2f}s")
    print(f"并发处理: {parallel_time:.2f}s") 