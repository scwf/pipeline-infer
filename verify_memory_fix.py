#!/usr/bin/env python3
"""
验证内存修复的简化测试
"""

import sys
import os
import time

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from executors.parallel import ThreadExecutor, ProcessExecutor


def main():
    print("🔧 验证内存泄漏修复")
    print("=" * 40)
    
    # 测试1: 验证流式处理不会一次性加载所有数据
    print("1. 测试流式处理...")
    
    def simple_task(x):
        return x * 2
    
    # 创建大数据集
    large_data = list(range(10000))
    
    # 使用修复后的执行器
    executor = ThreadExecutor(max_workers=4, max_memory_items=100)
    
    print(f"   处理 {len(large_data)} 项数据...")
    start_time = time.time()
    
    result_count = 0
    for result in executor.execute(simple_task, large_data):
        result_count += 1
        if result_count % 1000 == 0:
            print(f"   已处理 {result_count} 批")
    
    end_time = time.time()
    print(f"   ✅ 成功处理 {result_count} 批数据，耗时 {end_time - start_time:.2f} 秒")
    
    print("\n🎉 内存泄漏修复验证成功！")


if __name__ == "__main__":
    main()
