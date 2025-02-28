import pytest
from src.events.events import (
    PipelineEvent, 
    OperatorStartEvent, 
    OperatorCompleteEvent,
    ProgressEvent
)
from src.events.listener import EventListener, ConsoleEventListener

class TestPipelineEvents:
    """测试流水线事件类"""
    
    def test_pipeline_event_base(self):
        """测试基础事件类"""
        event = PipelineEvent("test_operator")
        assert event.operator_name == "test_operator"
    
    def test_operator_start_event(self):
        """测试算子开始事件"""
        event = OperatorStartEvent("test_operator")
        assert event.operator_name == "test_operator"
        assert isinstance(event, PipelineEvent)
    
    def test_operator_complete_event(self):
        """测试算子完成事件"""
        event = OperatorCompleteEvent("test_operator")
        assert event.operator_name == "test_operator"
        assert isinstance(event, PipelineEvent)
    
    def test_progress_event(self):
        """测试进度事件"""
        event = ProgressEvent("test_operator", 0.5, "处理中...")
        assert event.operator_name == "test_operator"
        assert event.progress == 0.5
        assert event.message == "处理中..."
        assert isinstance(event, PipelineEvent)

class TestEventListener:
    """测试事件监听器"""
    
    def test_event_listener_interface(self):
        """测试事件监听器接口"""
        class CustomListener(EventListener):
            def on_event(self, event):
                pass
                
        listener = CustomListener()
        assert isinstance(listener, EventListener)
    
    def test_console_listener(self, capsys):
        """测试控制台事件监听器"""
        listener = ConsoleEventListener()
        event = OperatorStartEvent("test_operator")
        
        # 测试事件输出
        listener.on_event(event)
        captured = capsys.readouterr()
        assert "事件" in captured.out
        assert "test_operator" in captured.out
    
    def test_multiple_events(self):
        """测试多个事件的处理"""
        events = []
        
        class TestListener(EventListener):
            def on_event(self, event):
                events.append(event)
        
        listener = TestListener()
        
        # 发送多个事件
        listener.on_event(OperatorStartEvent("op1"))
        listener.on_event(ProgressEvent("op1", 0.5, "处理中"))
        listener.on_event(OperatorCompleteEvent("op1"))
        
        # 验证事件处理
        assert len(events) == 3
        assert isinstance(events[0], OperatorStartEvent)
        assert isinstance(events[1], ProgressEvent)
        assert isinstance(events[2], OperatorCompleteEvent)
        assert all(e.operator_name == "op1" for e in events)
    
    def test_progress_event_validation(self):
        """测试进度事件的数值验证"""
        with pytest.raises(ValueError):
            # 进度不能大于1
            ProgressEvent("test", 1.5, "错误的进度")
            
        with pytest.raises(ValueError):
            # 进度不能小于0
            ProgressEvent("test", -0.1, "错误的进度")
            
        # 正常的进度值应该可以创建
        event = ProgressEvent("test", 0.5, "正常进度")
        assert event.progress == 0.5
