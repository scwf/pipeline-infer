import time  # 添加time模块导入
import pytest
import numpy as np
from src.operators.source import ImageSourceOperator
from src.operators.map import MapLikeOperator
from src.events.listener import EventListener
from src.events.events import OperatorStartEvent, OperatorCompleteEvent

@pytest.fixture  # 将TestEventListener改为fixture
def test_event_listener():
    """创建测试用的事件监听器"""
    class TestEventListener(EventListener):
        def __init__(self):
            self.events = []
            
        def on_event(self, event):
            self.events.append(event)
    
    return TestEventListener()

class TestOperators:
    def test_source_operator(self, temp_image_path, test_event_listener):
        """测试源算子"""
        # 准备
        operator = ImageSourceOperator("test_source", temp_image_path)
        operator.add_listener(test_event_listener)
        
        # 执行
        result = next(operator.process(None))
        
        # 验证
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert len(test_event_listener.events) == 2
        assert isinstance(test_event_listener.events[0], OperatorStartEvent)
        assert isinstance(test_event_listener.events[1], OperatorCompleteEvent)
        
    def test_source_operator_invalid_path(self):
        """测试源算子处理无效路径"""
        operator = ImageSourceOperator("test_source", "invalid_path.jpg")
        
        with pytest.raises(ValueError):
            next(operator.process(None))
            
    def test_map_operator(self, sample_image_data, test_event_listener):
        """测试Map算子"""
        # 准备
        def transform_fn(data):
            return data * 2
            
        operator = MapLikeOperator("test_map", transform_fn)
        operator.add_listener(test_event_listener)
        
        # 执行
        result = next(operator.process(sample_image_data))
        
        # 验证
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, sample_image_data * 2)
        assert len(test_event_listener.events) == 2
        
    def test_map_operator_parallel(self, sample_image_data):
        """测试Map算子并行处理"""
        # 准备
        def slow_transform(data):
            time.sleep(0.1)  # 模拟耗时操作
            return data
            
        operator = MapLikeOperator("test_map", slow_transform, parallel_degree=4)
        
        # 创建多个输入数据
        input_data = [sample_image_data for _ in range(4)]
        
        # 执行
        start_time = time.time()
        results = next(operator.process(input_data))  # 一次性处理所有数据
        end_time = time.time()
        
        # 验证
        assert len(results) == 4
        assert all(isinstance(r, np.ndarray) for r in results)
        # 由于并行处理，总时间应该小于串行处理的时间（串行需要0.4秒）
        assert end_time - start_time < 0.2  # 给一些余量，设为0.2秒 