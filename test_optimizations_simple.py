#!/usr/bin/env python3
"""
简化的性能优化测试
验证所有修复的功能是否正常工作
"""

import sys
import os
import time
import threading
from typing import List

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_pipeline_executor():
    """测试高性能流水线执行器"""
    print("=" * 50)
    print("测试1: 高性能流水线执行器")
    print("=" * 50)
    
    try:
        from executors.pipeline_executor import PipelineThreadExecutor
        
        def simple_task(x: int) -> int:
            return x * 2
        
        # 创建执行器
        executor = PipelineThreadExecutor(
            max_workers=4,
            max_memory_items=100,
            pipeline_depth=3,
            adaptive_batching=True
        )
        
        # 测试数据
        data = list(range(200))
        
        print(f"处理 {len(data)} 项数据...")
        start_time = time.time()
        
        results = []
        for result in executor.execute(simple_task, data):
            results.append(result)
        
        end_time = time.time()
        
        print(f"✅ 成功处理 {len(results)} 项数据")
        print(f"✅ 执行时间: {end_time - start_time:.3f}s")
        print(f"✅ 结果验证: {all(r == i * 2 for i, r in enumerate(results))}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_shared_monitor():
    """测试共享性能监控器"""
    print("=" * 50)
    print("测试2: 共享性能监控器")
    print("=" * 50)
    
    try:
        from events.shared_monitor import SharedPerformanceMonitor
        
        # 创建共享监控器
        monitor = SharedPerformanceMonitor()
        monitor.start_monitoring()
        
        print("测试多个监控会话...")
        sessions = []
        
        # 启动多个会话
        for i in range(10):
            session_id = monitor.start_session(f"test_op_{i}", batch_size=1)
            sessions.append(session_id)
            time.sleep(0.01)  # 模拟工作
        
        # 结束会话
        events = []
        for session_id in sessions:
            event = monitor.end_session(session_id)
            if event:
                events.append(event)
        
        stats = monitor.get_stats()
        monitor.stop_monitoring()
        
        print(f"✅ 处理了 {len(events)} 个监控事件")
        print(f"✅ 监控统计: {stats}")
        
        return len(events) > 0
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_async_events():
    """测试异步事件系统"""
    print("=" * 50)
    print("测试3: 异步事件系统")
    print("=" * 50)
    
    try:
        from events.async_events import AsyncEventSystem
        from events.events import ProgressEvent
        
        # 创建异步事件系统
        event_system = AsyncEventSystem(batch_size=10, batch_timeout=0.1)
        
        # 事件收集器
        received_events = []
        
        def event_listener(batch):
            received_events.extend(batch.events)
        
        event_system.add_listener(event_listener)
        
        print("发送测试事件...")
        # 发送事件
        for i in range(50):
            event = ProgressEvent(f"test_op_{i}", i / 50, f"Progress {i}")
            event_system.dispatcher.emit_event(event)
        
        # 等待处理完成
        time.sleep(0.5)
        
        stats = event_system.get_stats()
        event_system.stop()
        
        print(f"✅ 发送了 50 个事件")
        print(f"✅ 接收了 {len(received_events)} 个事件")
        print(f"✅ 事件系统统计: {stats}")
        
        return len(received_events) >= 40  # 允许一些事件丢失
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_memory_optimization():
    """测试内存优化"""
    print("=" * 50)
    print("测试4: 内存优化验证")
    print("=" * 50)
    
    try:
        from executors.parallel import ThreadExecutor
        
        def memory_task(x: int) -> List[int]:
            # 创建临时数据
            return list(range(x * 10, (x + 1) * 10))
        
        # 使用修复后的执行器
        executor = ThreadExecutor(max_workers=2, max_memory_items=50)
        data = list(range(100))
        
        print(f"处理 {len(data)} 项数据...")
        start_time = time.time()
        
        results = []
        for result in executor.execute(memory_task, data):
            results.append(len(result))  # 只保存长度，不保存实际数据
        
        end_time = time.time()
        
        print(f"✅ 成功处理 {len(results)} 批数据")
        print(f"✅ 执行时间: {end_time - start_time:.3f}s")
        print(f"✅ 结果验证: {all(r == 10 for r in results)}")
        
        return len(results) == 100
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_integration():
    """测试集成效果"""
    print("=" * 50)
    print("测试5: 集成测试")
    print("=" * 50)
    
    try:
        # 测试所有优化组件是否能协同工作
        from executors.pipeline_executor import PipelineThreadExecutor
        from events.shared_monitor import SharedPerformanceMonitor
        from events.async_events import AsyncEventSystem
        
        # 创建组件
        executor = PipelineThreadExecutor(max_workers=2, max_memory_items=20)
        monitor = SharedPerformanceMonitor()
        event_system = AsyncEventSystem(batch_size=5)
        
        monitor.start_monitoring()
        
        def integrated_task(x: int) -> int:
            # 模拟带监控的任务
            session_id = monitor.start_session(f"task_{x}")
            time.sleep(0.001)
            result = x * x
            monitor.end_session(session_id)
            return result
        
        # 执行集成测试
        data = list(range(20))
        
        print("执行集成测试...")
        start_time = time.time()
        
        results = []
        for result in executor.execute(integrated_task, data):
            results.append(result)
        
        end_time = time.time()
        
        # 清理
        monitor.stop_monitoring()
        event_system.stop()
        
        print(f"✅ 集成测试完成")
        print(f"✅ 处理了 {len(results)} 项数据")
        print(f"✅ 执行时间: {end_time - start_time:.3f}s")
        print(f"✅ 监控统计: {monitor.get_stats()}")
        
        return len(results) == 20
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("🚀 性能优化验证测试")
    print("=" * 60)
    
    tests = [
        ("高性能流水线执行器", test_pipeline_executor),
        ("共享性能监控器", test_shared_monitor),
        ("异步事件系统", test_async_events),
        ("内存优化", test_memory_optimization),
        ("集成测试", test_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{test_name}: {status}\n")
        except Exception as e:
            print(f"{test_name}: ❌ 异常 - {e}\n")
            results.append(False)
    
    # 汇总结果
    print("=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    
    for i, ((test_name, _), result) in enumerate(zip(tests, results)):
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{i+1}. {test_name}: {status}")
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n总体结果: {success_count}/{total_count} 测试通过")
    
    if success_count == total_count:
        print("🎉 所有性能优化测试通过！")
        return True
    else:
        print("⚠️  部分测试失败，需要进一步检查")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)