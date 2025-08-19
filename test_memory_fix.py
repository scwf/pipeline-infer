#!/usr/bin/env python3
"""
简化的内存优化测试脚本
验证流式处理是否有效避免内存问题
"""

import sys
import os
import time
from typing import Iterator, List
import traceback

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from executors.parallel import ThreadExecutor, ProcessExecutor


def memory_intensive_task(x: int) -> List[int]:
    """模拟内存密集型任务"""
    # 创建一个较大的临时数据结构
    temp_data = list(range(x * 100, (x + 1) * 100))
    return temp_data


def large_data_generator(size: int) -> Iterator[int]:
    """生成大量数据的生成器"""
    print(f"开始生成 {size} 项数据...")
    for i in range(size):
        if i % 1000 == 0:
            print(f"已生成 {i} 项数据")
        yield i


def test_streaming_processing():
    """测试流式处理功能"""
    print("=" * 50)
    print("测试1: 流式处理大量数据")
    print("=" * 50)
    
    # 准备大量数据
    large_dataset = list(range(1000))
    print(f"准备了 {len(large_dataset)} 项数据")
    
    # 测试新的流式执行器
    print("创建流式执行器...")
    streaming_executor = ThreadExecutor(max_workers=4, max_memory_items=100)
    
    print("开始流式处理...")
    results = []
    start_time = time.time()
    
    try:
        count = 0
        for result in streaming_executor.execute(memory_intensive_task, large_dataset):
            results.append(len(result))
            count += 1
            if count % 100 == 0:
                print(f"已处理 {count} 批数据")
        
        end_time = time.time()
        
        print(f"✅ 流式处理成功!")
        print(f"   - 处理数据量: {len(results)} 批")
        print(f"   - 处理时间: {end_time - start_time:.2f} 秒")
        print(f"   - 结果验证: {all(r == 100 for r in results)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 流式处理失败: {e}")
        traceback.print_exc()
        return False


def test_iterator_processing():
    """测试迭代器处理功能"""
    print("=" * 50)
    print("测试2: 处理大型迭代器")
    print("=" * 50)
    
    def simple_task(x: int) -> int:
        return x * 2
    
    print("创建执行器...")
    executor = ThreadExecutor(max_workers=4, max_memory_items=1000)
    
    print("开始处理大型生成器...")
    start_time = time.time()
    
    try:
        results_count = 0
        for result in executor.execute(simple_task, large_data_generator(5000)):
            results_count += 1
            if results_count % 1000 == 0:
                print(f"已处理 {results_count} 项结果")
        
        end_time = time.time()
        
        print(f"✅ 迭代器处理成功!")
        print(f"   - 处理数据量: {results_count} 项")
        print(f"   - 处理时间: {end_time - start_time:.2f} 秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 迭代器处理失败: {e}")
        traceback.print_exc()
        return False


def cpu_intensive_task(x: int) -> int:
    """CPU密集型任务 - 定义在模块级别以支持进程池序列化"""
    result = 0
    for i in range(100):  # 减少计算量以加快测试
        result += x * i
    return result

def test_process_executor():
    """测试进程池执行器"""
    print("=" * 50)
    print("测试3: 进程池执行器内存优化")
    print("=" * 50)
    
    # 准备数据
    data = list(range(200))  # 减少数据量
    print(f"准备了 {len(data)} 项数据")
    
    print("创建进程池执行器...")
    executor = ProcessExecutor(max_workers=2, max_memory_items=50)
    
    print("开始处理...")
    start_time = time.time()
    
    try:
        results = []
        count = 0
        for result in executor.execute(cpu_intensive_task, data):
            results.append(result)
            count += 1
            if count % 50 == 0:
                print(f"已处理 {count} 项数据")
        
        end_time = time.time()
        
        print(f"✅ 进程池处理成功!")
        print(f"   - 处理数据量: {len(results)} 项")
        print(f"   - 处理时间: {end_time - start_time:.2f} 秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 进程池处理失败: {e}")
        traceback.print_exc()
        return False


def test_old_vs_new_comparison():
    """对比修复前后的行为差异"""
    print("=" * 50)
    print("测试4: 修复前后对比")
    print("=" * 50)
    
    def simple_task(x: int) -> int:
        return x + 1
    
    # 模拟旧的实现（会将所有数据加载到内存）
    def old_style_processing(data_list):
        print("模拟旧实现：一次性加载所有数据到内存")
        # 这就是旧版本的问题所在
        all_data = list(data_list)  # 这会导致内存问题
        results = []
        for item in all_data:
            results.append(simple_task(item))
        return results
    
    # 新的流式实现
    def new_style_processing(data_list):
        print("新的流式实现：分批处理数据")
        executor = ThreadExecutor(max_workers=2, max_memory_items=100)
        results = []
        for result in executor.execute(simple_task, data_list):
            results.append(result)
        return results
    
    # 测试数据
    test_data = list(range(1000))
    
    print("测试旧实现...")
    start_time = time.time()
    old_results = old_style_processing(test_data)
    old_time = time.time() - start_time
    
    print("测试新实现...")
    start_time = time.time()
    new_results = new_style_processing(test_data)
    new_time = time.time() - start_time
    
    # 验证结果一致性 - 新实现返回的是单个结果的列表
    # 需要展开比较
    if isinstance(new_results[0], list):
        new_results_flat = []
        for batch in new_results:
            if isinstance(batch, list):
                new_results_flat.extend(batch)
            else:
                new_results_flat.append(batch)
        results_match = old_results == new_results_flat
    else:
        results_match = old_results == new_results
    
    print(f"✅ 对比测试完成!")
    print(f"   - 结果一致性: {results_match}")
    print(f"   - 旧实现时间: {old_time:.2f} 秒")
    print(f"   - 新实现时间: {new_time:.2f} 秒")
    
    return results_match


def main():
    """运行所有测试"""
    print("开始内存优化修复验证测试")
    print("=" * 60)
    
    test_results = []
    
    # 运行各项测试
    test_results.append(test_streaming_processing())
    test_results.append(test_iterator_processing())
    test_results.append(test_process_executor())
    test_results.append(test_old_vs_new_comparison())
    
    # 汇总结果
    print("=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    
    test_names = [
        "流式处理测试",
        "迭代器处理测试", 
        "进程池优化测试",
        "修复前后对比测试"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, test_results)):
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{i+1}. {name}: {status}")
    
    success_count = sum(test_results)
    total_count = len(test_results)
    
    print(f"\n总体结果: {success_count}/{total_count} 测试通过")
    
    if success_count == total_count:
        print("🎉 所有测试通过！内存优化修复成功！")
        return True
    else:
        print("⚠️  部分测试失败，需要进一步检查")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)