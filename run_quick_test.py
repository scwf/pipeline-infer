#!/usr/bin/env python3
"""
快速测试脚本
用于快速验证所有处理方法的基本功能和性能
"""

import time
import sys
import os

def test_serial():
    """测试串行处理"""
    print("=" * 50)
    print("测试串行处理...")
    try:
        from serial_processing import SerialProcessor
        processor = SerialProcessor()
        start_time = time.time()
        result = processor.run_pipeline(50000)  # 使用较小的数据集
        end_time = time.time()
        print(f"✓ 串行处理成功完成，耗时: {end_time - start_time:.2f}秒")
        return end_time - start_time
    except Exception as e:
        print(f"✗ 串行处理失败: {e}")
        return None

def test_pipeline():
    """测试流水线并行"""
    print("=" * 50)
    print("测试流水线并行...")
    try:
        from pipeline_parallel_simple import SimplePipelineProcessor
        processor = SimplePipelineProcessor()
        start_time = time.time()
        result = processor.run_pipeline(50000, 5000)
        end_time = time.time()
        print(f"✓ 流水线并行成功完成，耗时: {end_time - start_time:.2f}秒")
        return end_time - start_time
    except Exception as e:
        print(f"✗ 流水线并行失败: {e}")
        return None

def test_multiprocess():
    """测试多进程并行"""
    print("=" * 50)
    print("测试多进程并行...")
    try:
        from multiprocess_parallel import MultiprocessProcessor
        processor = MultiprocessProcessor()
        start_time = time.time()
        result = processor.run_pipeline(50000)
        end_time = time.time()
        print(f"✓ 多进程并行成功完成，耗时: {end_time - start_time:.2f}秒")
        return end_time - start_time
    except Exception as e:
        print(f"✗ 多进程并行失败: {e}")
        return None

def main():
    """主函数"""
    print("流水线并行性能快速测试")
    print("这个测试使用较小的数据集快速验证所有方法")
    print()
    
    results = {}
    
    # 测试所有方法
    serial_time = test_serial()
    if serial_time:
        results['serial'] = serial_time
    
    pipeline_time = test_pipeline()
    if pipeline_time:
        results['pipeline'] = pipeline_time
    
    multiprocess_time = test_multiprocess()
    if multiprocess_time:
        results['multiprocess'] = multiprocess_time
    
    # 显示结果对比
    print("=" * 50)
    print("快速测试结果汇总:")
    print("=" * 50)
    
    if results:
        print(f"{'方法':<15} {'耗时(秒)':<10} {'加速比':<10}")
        print("-" * 35)
        
        baseline = results.get('serial', 1)
        
        for method, exec_time in results.items():
            speedup = baseline / exec_time if exec_time > 0 else 0
            speedup_str = f"{speedup:.2f}x" if method != 'serial' else "基准"
            method_name = {
                'serial': '串行处理',
                'pipeline': '流水线并行',
                'multiprocess': '多进程并行'
            }.get(method, method)
            
            print(f"{method_name:<15} {exec_time:<10.2f} {speedup_str:<10}")
        
        # 显示最佳性能
        fastest_method = min(results.items(), key=lambda x: x[1])
        fastest_name = {
            'serial': '串行处理',
            'pipeline': '流水线并行', 
            'multiprocess': '多进程并行'
        }.get(fastest_method[0], fastest_method[0])
        
        print(f"\n最快方法: {fastest_name} ({fastest_method[1]:.2f}秒)")
        
        if len(results) > 1:
            print(f"\n建议:")
            if 'multiprocess' in results and 'serial' in results:
                mp_speedup = results['serial'] / results['multiprocess']
                if mp_speedup > 1.5:
                    print("- 多进程并行在你的系统上表现良好，适合CPU密集型任务")
                else:
                    print("- 多进程并行加速效果有限，可能受到数据大小或系统限制")
            
            if 'pipeline' in results and 'serial' in results:
                pl_speedup = results['serial'] / results['pipeline']
                if pl_speedup > 1.2:
                    print("- 流水线并行有效，适合IO密集型或阶段性处理任务")
                else:
                    print("- 流水线并行加速有限，可能受到阶段间同步开销影响")
    else:
        print("没有成功的测试结果")
    
    print("\n运行完整基准测试:")
    print("python performance_benchmark.py")

if __name__ == "__main__":
    main()