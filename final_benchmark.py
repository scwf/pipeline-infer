#!/usr/bin/env python3
"""
最终性能基准测试脚本
使用简化版本对比串行处理、流水线并行和多进程并行的性能
"""

import time
import json
import os
import sys
import numpy as np
import multiprocessing as mp

# 导入处理器
from serial_processing import SerialProcessor
from pipeline_parallel_simple import SimplePipelineProcessor
from multiprocess_parallel import MultiprocessProcessor

class FinalBenchmark:
    """最终性能基准测试类"""
    
    def __init__(self):
        self.results = []
        self.cpu_count = mp.cpu_count()
        
    def run_test(self, processor_class, method_name: str, data_size: int = 50000, **kwargs):
        """运行单个测试"""
        print(f"\n{'='*60}")
        print(f"测试 {method_name} (数据大小: {data_size})")
        print(f"{'='*60}")
        
        try:
            processor = processor_class(**kwargs)
            start_time = time.time()
            
            # 根据不同的处理器调用不同的方法
            if hasattr(processor, 'run_pipeline'):
                if method_name == "流水线并行":
                    result = processor.run_pipeline(data_size, data_size // 10)
                else:
                    result = processor.run_pipeline(data_size)
            else:
                raise AttributeError("处理器没有run_pipeline方法")
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print(f"✓ {method_name}成功完成，耗时: {total_time:.2f}秒")
            
            return {
                'method': method_name,
                'total_time': total_time,
                'data_size': data_size,
                'success': True
            }
            
        except Exception as e:
            print(f"✗ {method_name}失败: {e}")
            return {
                'method': method_name,
                'total_time': float('inf'),
                'data_size': data_size,
                'success': False,
                'error': str(e)
            }
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        print("流水线并行性能综合测试")
        print(f"系统CPU核心数: {self.cpu_count}")
        print(f"测试开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        test_cases = [
            # 小数据集测试
            (25000, "小数据集"),
            # 中等数据集测试
            (50000, "中等数据集"),
            # 大数据集测试
            (100000, "大数据集")
        ]
        
        for data_size, size_desc in test_cases:
            print(f"\n{'='*80}")
            print(f"{size_desc}测试 (数据大小: {data_size})")
            print(f"{'='*80}")
            
            # 串行处理测试
            serial_result = self.run_test(SerialProcessor, "串行处理", data_size)
            self.results.append(serial_result)
            
            # 流水线并行测试
            pipeline_result = self.run_test(SimplePipelineProcessor, "流水线并行", data_size)
            self.results.append(pipeline_result)
            
            # 多进程并行测试
            multiprocess_result = self.run_test(
                MultiprocessProcessor, "多进程并行", data_size, 
                n_processes=self.cpu_count
            )
            self.results.append(multiprocess_result)
            
            # 显示当前测试的对比结果
            if all(r['success'] for r in [serial_result, pipeline_result, multiprocess_result]):
                self.display_comparison([serial_result, pipeline_result, multiprocess_result], size_desc)
    
    def display_comparison(self, results, size_desc):
        """显示对比结果"""
        print(f"\n{size_desc}性能对比:")
        print(f"{'方法':<15} {'耗时(秒)':<12} {'加速比':<10}")
        print("-" * 40)
        
        baseline = None
        for result in results:
            if result['method'] == '串行处理' and result['success']:
                baseline = result['total_time']
                break
        
        for result in results:
            if result['success']:
                method = result['method']
                exec_time = result['total_time']
                
                if baseline and baseline > 0:
                    speedup = baseline / exec_time
                    speedup_str = f"{speedup:.2f}x" if method != '串行处理' else "基准"
                else:
                    speedup_str = "N/A"
                
                print(f"{method:<15} {exec_time:<12.2f} {speedup_str:<10}")
    
    def analyze_all_results(self):
        """分析所有测试结果"""
        print(f"\n{'='*80}")
        print("综合性能分析")
        print(f"{'='*80}")
        
        # 按方法分组
        method_results = {}
        for result in self.results:
            if result['success']:
                method = result['method']
                if method not in method_results:
                    method_results[method] = []
                method_results[method].append(result)
        
        # 计算平均性能
        print("\n平均性能统计:")
        print(f"{'方法':<15} {'平均耗时(秒)':<15} {'测试次数':<10}")
        print("-" * 45)
        
        baseline_avg = None
        method_averages = {}
        
        for method, results in method_results.items():
            avg_time = np.mean([r['total_time'] for r in results])
            method_averages[method] = avg_time
            count = len(results)
            
            if method == '串行处理':
                baseline_avg = avg_time
            
            print(f"{method:<15} {avg_time:<15.2f} {count:<10}")
        
        # 计算平均加速比
        print("\n平均加速比:")
        print(f"{'方法':<15} {'平均加速比':<15}")
        print("-" * 35)
        
        for method, avg_time in method_averages.items():
            if baseline_avg and baseline_avg > 0:
                speedup = baseline_avg / avg_time
                speedup_str = f"{speedup:.2f}x" if method != '串行处理' else "基准"
            else:
                speedup_str = "N/A"
            
            print(f"{method:<15} {speedup_str:<15}")
        
        # 找出最佳方法
        if method_averages:
            best_method = min(method_averages.items(), key=lambda x: x[1])
            print(f"\n总体最佳性能: {best_method[0]} (平均耗时: {best_method[1]:.2f}秒)")
        
        # 生成建议
        self.generate_recommendations(method_averages, baseline_avg)
    
    def generate_recommendations(self, method_averages, baseline_avg):
        """生成性能建议"""
        print(f"\n{'='*60}")
        print("性能优化建议")
        print(f"{'='*60}")
        
        if not baseline_avg or baseline_avg <= 0:
            print("无法生成建议：缺少有效的基准数据")
            return
        
        pipeline_speedup = baseline_avg / method_averages.get('流水线并行', baseline_avg)
        multiprocess_speedup = baseline_avg / method_averages.get('多进程并行', baseline_avg)
        
        print(f"1. 并行处理效果评估:")
        print(f"   - 流水线并行平均加速比: {pipeline_speedup:.2f}x")
        print(f"   - 多进程并行平均加速比: {multiprocess_speedup:.2f}x")
        
        print(f"\n2. 适用场景建议:")
        if multiprocess_speedup > 1.5:
            print("   ✓ 多进程并行表现良好，推荐用于CPU密集型任务")
        else:
            print("   ⚠ 多进程并行加速有限，可能受到GIL或数据传输开销影响")
        
        if pipeline_speedup > 1.2:
            print("   ✓ 流水线并行有效，推荐用于IO密集型或阶段性处理任务")
        else:
            print("   ⚠ 流水线并行加速有限，考虑优化阶段间同步或减少队列开销")
        
        print(f"\n3. 系统相关建议:")
        print(f"   - 当前系统有 {self.cpu_count} 个CPU核心")
        if self.cpu_count >= 4:
            print("   ✓ 多核系统，适合使用多进程并行")
        else:
            print("   ⚠ 核心数较少，流水线并行可能更适合")
        
        print(f"\n4. 优化方向:")
        if multiprocess_speedup < pipeline_speedup:
            print("   - 考虑增大数据块大小以减少进程间通信开销")
            print("   - 优化数据序列化和传输效率")
        if pipeline_speedup < 1.5:
            print("   - 尝试调整批次大小和队列大小")
            print("   - 考虑使用异步IO来提高流水线效率")
    
    def save_report(self, filename: str = "final_performance_report.json"):
        """保存详细报告"""
        report = {
            'system_info': {
                'cpu_count': self.cpu_count,
                'test_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'python_version': sys.version
            },
            'test_results': self.results,
            'summary': {
                'total_tests': len(self.results),
                'successful_tests': len([r for r in self.results if r['success']]),
                'failed_tests': len([r for r in self.results if not r['success']])
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n详细报告已保存到: {filename}")

def main():
    """主函数"""
    benchmark = FinalBenchmark()
    
    # 运行综合测试
    benchmark.run_comprehensive_test()
    
    # 分析所有结果
    benchmark.analyze_all_results()
    
    # 保存报告
    benchmark.save_report()
    
    print(f"\n{'='*80}")
    print("测试完成!")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()