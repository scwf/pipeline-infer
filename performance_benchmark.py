#!/usr/bin/env python3
"""
性能基准测试脚本
对比串行处理、流水线并行和多进程并行的性能
"""

import time
import json
import os
import sys
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from typing import Dict, List
import subprocess
import multiprocessing as mp

# 导入我们的处理器
from serial_processing import SerialProcessor
from pipeline_parallel import PipelineProcessor
from multiprocess_parallel import MultiprocessProcessor

class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self):
        self.results = {}
        self.test_sizes = [10000, 50000, 100000, 200000]
        self.cpu_count = mp.cpu_count()
        
    def run_serial_test(self, data_size: int) -> Dict:
        """运行串行处理测试"""
        print(f"\n--- 串行处理测试 (数据大小: {data_size}) ---")
        processor = SerialProcessor()
        start_time = time.time()
        result = processor.run_pipeline(data_size)
        end_time = time.time()
        
        return {
            'total_time': end_time - start_time,
            'stage_times': result['stage_times'],
            'method': 'serial',
            'data_size': data_size
        }
    
    def run_pipeline_test(self, data_size: int) -> Dict:
        """运行流水线并行测试"""
        print(f"\n--- 流水线并行测试 (数据大小: {data_size}) ---")
        processor = PipelineProcessor()
        batch_size = max(1000, data_size // 20)  # 动态调整批次大小
        start_time = time.time()
        result = processor.run_pipeline(data_size, batch_size)
        end_time = time.time()
        
        return {
            'total_time': end_time - start_time,
            'stage_times': result['stage_times'],
            'method': 'pipeline',
            'data_size': data_size,
            'batch_size': batch_size
        }
    
    def run_multiprocess_test(self, data_size: int, n_processes: int = None) -> Dict:
        """运行多进程并行测试"""
        if n_processes is None:
            n_processes = self.cpu_count
        
        print(f"\n--- 多进程并行测试 (数据大小: {data_size}, 进程数: {n_processes}) ---")
        processor = MultiprocessProcessor(n_processes)
        start_time = time.time()
        result = processor.run_pipeline(data_size)
        end_time = time.time()
        
        return {
            'total_time': end_time - start_time,
            'stage_times': result['stage_times'],
            'method': 'multiprocess',
            'data_size': data_size,
            'processes': n_processes
        }
    
    def run_comprehensive_test(self):
        """运行综合性能测试"""
        print("="*60)
        print("开始综合性能基准测试")
        print(f"系统CPU核心数: {self.cpu_count}")
        print(f"测试数据大小: {self.test_sizes}")
        print("="*60)
        
        all_results = []
        
        for data_size in self.test_sizes:
            print(f"\n{'='*20} 测试数据大小: {data_size} {'='*20}")
            
            # 串行处理测试
            try:
                serial_result = self.run_serial_test(data_size)
                all_results.append(serial_result)
                print(f"串行处理耗时: {serial_result['total_time']:.2f}秒")
            except Exception as e:
                print(f"串行处理测试失败: {e}")
            
            # 流水线并行测试
            try:
                pipeline_result = self.run_pipeline_test(data_size)
                all_results.append(pipeline_result)
                print(f"流水线并行耗时: {pipeline_result['total_time']:.2f}秒")
                
                # 计算加速比
                if 'serial_result' in locals():
                    speedup = serial_result['total_time'] / pipeline_result['total_time']
                    print(f"流水线并行加速比: {speedup:.2f}x")
            except Exception as e:
                print(f"流水线并行测试失败: {e}")
            
            # 多进程并行测试
            try:
                multiprocess_result = self.run_multiprocess_test(data_size)
                all_results.append(multiprocess_result)
                print(f"多进程并行耗时: {multiprocess_result['total_time']:.2f}秒")
                
                # 计算加速比
                if 'serial_result' in locals():
                    speedup = serial_result['total_time'] / multiprocess_result['total_time']
                    print(f"多进程并行加速比: {speedup:.2f}x")
            except Exception as e:
                print(f"多进程并行测试失败: {e}")
            
            # 清理内存
            time.sleep(1)
        
        self.results = all_results
        return all_results
    
    def run_scaling_test(self):
        """测试不同进程数的扩展性"""
        print("\n" + "="*60)
        print("多进程扩展性测试")
        print("="*60)
        
        data_size = 100000
        process_counts = [1, 2, 4, min(8, self.cpu_count), self.cpu_count]
        scaling_results = []
        
        for n_proc in process_counts:
            if n_proc <= self.cpu_count:
                try:
                    result = self.run_multiprocess_test(data_size, n_proc)
                    scaling_results.append(result)
                    print(f"{n_proc} 进程: {result['total_time']:.2f}秒")
                except Exception as e:
                    print(f"{n_proc} 进程测试失败: {e}")
        
        return scaling_results
    
    def analyze_results(self):
        """分析测试结果"""
        if not self.results:
            print("没有测试结果可供分析")
            return
        
        print("\n" + "="*60)
        print("性能分析结果")
        print("="*60)
        
        # 按数据大小分组结果
        grouped_results = {}
        for result in self.results:
            data_size = result['data_size']
            if data_size not in grouped_results:
                grouped_results[data_size] = {}
            grouped_results[data_size][result['method']] = result
        
        # 计算加速比
        print("\n加速比分析:")
        print("数据大小\t串行耗时\t流水线并行\t多进程并行\t流水线加速比\t多进程加速比")
        print("-" * 80)
        
        speedup_data = []
        
        for data_size in sorted(grouped_results.keys()):
            group = grouped_results[data_size]
            
            serial_time = group.get('serial', {}).get('total_time', 0)
            pipeline_time = group.get('pipeline', {}).get('total_time', 0)
            multiprocess_time = group.get('multiprocess', {}).get('total_time', 0)
            
            pipeline_speedup = serial_time / pipeline_time if pipeline_time > 0 else 0
            multiprocess_speedup = serial_time / multiprocess_time if multiprocess_time > 0 else 0
            
            print(f"{data_size}\t\t{serial_time:.2f}s\t\t{pipeline_time:.2f}s\t\t{multiprocess_time:.2f}s\t\t{pipeline_speedup:.2f}x\t\t{multiprocess_speedup:.2f}x")
            
            speedup_data.append({
                'data_size': data_size,
                'serial_time': serial_time,
                'pipeline_time': pipeline_time,
                'multiprocess_time': multiprocess_time,
                'pipeline_speedup': pipeline_speedup,
                'multiprocess_speedup': multiprocess_speedup
            })
        
        return speedup_data
    
    def generate_report(self, output_file: str = "performance_report.json"):
        """生成详细报告"""
        report = {
            'system_info': {
                'cpu_count': self.cpu_count,
                'test_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'test_sizes': self.test_sizes
            },
            'test_results': self.results,
            'analysis': self.analyze_results()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n详细报告已保存到: {output_file}")
        return report
    
    def plot_results(self):
        """绘制性能对比图表"""
        try:
            import matplotlib.pyplot as plt
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 准备数据
            data_sizes = []
            serial_times = []
            pipeline_times = []
            multiprocess_times = []
            
            grouped_results = {}
            for result in self.results:
                data_size = result['data_size']
                if data_size not in grouped_results:
                    grouped_results[data_size] = {}
                grouped_results[data_size][result['method']] = result
            
            for data_size in sorted(grouped_results.keys()):
                group = grouped_results[data_size]
                if all(method in group for method in ['serial', 'pipeline', 'multiprocess']):
                    data_sizes.append(data_size)
                    serial_times.append(group['serial']['total_time'])
                    pipeline_times.append(group['pipeline']['total_time'])
                    multiprocess_times.append(group['multiprocess']['total_time'])
            
            if not data_sizes:
                print("没有足够的数据生成图表")
                return
            
            # 创建图表
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # 左图: 执行时间对比
            x = np.arange(len(data_sizes))
            width = 0.25
            
            ax1.bar(x - width, serial_times, width, label='Serial', alpha=0.8)
            ax1.bar(x, pipeline_times, width, label='Pipeline Parallel', alpha=0.8)
            ax1.bar(x + width, multiprocess_times, width, label='Multiprocess Parallel', alpha=0.8)
            
            ax1.set_xlabel('Data Size')
            ax1.set_ylabel('Execution Time (seconds)')
            ax1.set_title('Performance Comparison: Execution Time')
            ax1.set_xticks(x)
            ax1.set_xticklabels([f'{size//1000}K' for size in data_sizes])
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 右图: 加速比
            pipeline_speedup = [s/p for s, p in zip(serial_times, pipeline_times)]
            multiprocess_speedup = [s/m for s, m in zip(serial_times, multiprocess_times)]
            
            ax2.plot(data_sizes, pipeline_speedup, 'o-', label='Pipeline Speedup', linewidth=2, markersize=8)
            ax2.plot(data_sizes, multiprocess_speedup, 's-', label='Multiprocess Speedup', linewidth=2, markersize=8)
            ax2.axhline(y=1, color='r', linestyle='--', alpha=0.5, label='Baseline')
            
            ax2.set_xlabel('Data Size')
            ax2.set_ylabel('Speedup (x)')
            ax2.set_title('Performance Comparison: Speedup')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig('performance_comparison.png', dpi=300, bbox_inches='tight')
            print("性能对比图表已保存到: performance_comparison.png")
            
            # 显示图表（如果在交互环境中）
            try:
                plt.show()
            except:
                pass
            
        except ImportError:
            print("matplotlib 未安装，跳过图表生成")
        except Exception as e:
            print(f"生成图表时出错: {e}")

def main():
    """主函数"""
    print("并行处理性能基准测试")
    print("这个测试将比较串行处理、流水线并行和多进程并行的性能")
    
    benchmark = PerformanceBenchmark()
    
    # 运行综合测试
    results = benchmark.run_comprehensive_test()
    
    # 运行扩展性测试
    scaling_results = benchmark.run_scaling_test()
    
    # 分析结果
    analysis = benchmark.analyze_results()
    
    # 生成报告
    report = benchmark.generate_report()
    
    # 绘制图表
    benchmark.plot_results()
    
    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)
    print("\n总结:")
    
    if analysis:
        avg_pipeline_speedup = np.mean([item['pipeline_speedup'] for item in analysis if item['pipeline_speedup'] > 0])
        avg_multiprocess_speedup = np.mean([item['multiprocess_speedup'] for item in analysis if item['multiprocess_speedup'] > 0])
        
        print(f"平均流水线并行加速比: {avg_pipeline_speedup:.2f}x")
        print(f"平均多进程并行加速比: {avg_multiprocess_speedup:.2f}x")
        
        if avg_multiprocess_speedup > avg_pipeline_speedup:
            print("多进程并行在这个测试中表现更好")
        else:
            print("流水线并行在这个测试中表现更好")
    
    print(f"\n详细结果请查看: performance_report.json")
    print(f"性能图表请查看: performance_comparison.png")

if __name__ == "__main__":
    main()