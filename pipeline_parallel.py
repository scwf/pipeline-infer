#!/usr/bin/env python3
"""
流水线并行数据处理脚本
使用threading和queue实现流水线并行处理，不同阶段可以同时执行
"""

import time
import numpy as np
import pandas as pd
import os
import json
import threading
import queue
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

class PipelineStage:
    """流水线阶段基类"""
    def __init__(self, name: str, input_queue: queue.Queue = None, output_queue: queue.Queue = None):
        self.name = name
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.processed_count = 0
        self.start_time = None
        self.end_time = None
    
    def process_item(self, item):
        """处理单个数据项，需要子类实现"""
        raise NotImplementedError
    
    def run(self):
        """运行阶段处理"""
        self.start_time = time.time()
        print(f"[流水线] {self.name} 开始运行")
        
        # 如果没有输入队列，说明这是数据生成阶段，直接调用子类的run方法
        if self.input_queue is None:
            return
        
        while True:
            try:
                # 从输入队列获取数据
                item = self.input_queue.get(timeout=1)
                if item is None:  # 结束信号
                    print(f"[流水线] {self.name} 接收到结束信号")
                    break
                
                # 处理数据
                result = self.process_item(item)
                
                # 将结果放入输出队列
                if result is not None:
                    self.output_queue.put(result)
                
                self.processed_count += 1
                self.input_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[流水线] {self.name} 处理错误: {e}")
                self.input_queue.task_done()
        
        # 传递结束信号
        if self.output_queue:
            self.output_queue.put(None)
        self.end_time = time.time()
        print(f"[流水线] {self.name} 完成，处理了 {self.processed_count} 个项目，耗时 {self.end_time - self.start_time:.2f}秒")

class DataGeneratorStage(PipelineStage):
    """数据生成阶段"""
    def __init__(self, output_queue: queue.Queue, batch_size: int = 10000, total_size: int = 100000):
        super().__init__("数据生成器", None, output_queue)
        self.batch_size = batch_size
        self.total_size = total_size
    
    def run(self):
        """生成数据批次"""
        self.start_time = time.time()
        print(f"[流水线] {self.name} 开始生成数据")
        
        num_batches = (self.total_size + self.batch_size - 1) // self.batch_size
        
        for batch_idx in range(num_batches):
            start_idx = batch_idx * self.batch_size
            end_idx = min(start_idx + self.batch_size, self.total_size)
            current_batch_size = end_idx - start_idx
            
            # 生成一批数据
            batch_data = {
                'id': range(start_idx, end_idx),
                'value1': np.random.normal(100, 15, current_batch_size),
                'value2': np.random.exponential(2, current_batch_size),
                'category': np.random.choice(['A', 'B', 'C', 'D'], current_batch_size),
                'batch_id': batch_idx
            }
            
            batch_df = pd.DataFrame(batch_data)
            self.output_queue.put(batch_df)
            self.processed_count += 1
            
            # 模拟数据生成耗时
            time.sleep(0.01)
        
        # 发送结束信号
        self.output_queue.put(None)
        self.end_time = time.time()
        print(f"[流水线] {self.name} 完成，生成了 {self.processed_count} 个批次，耗时 {self.end_time - self.start_time:.2f}秒")

class PreprocessStage(PipelineStage):
    """数据预处理阶段"""
    def process_item(self, item):
        if item is None:
            return None
        
        df = item.copy()
        
        # 数据标准化
        df['value1_normalized'] = (df['value1'] - df['value1'].mean()) / df['value1'].std()
        df['value2_log'] = np.log1p(df['value2'])
        df['value_ratio'] = df['value1'] / (df['value2'] + 1)
        df['value_sum'] = df['value1'] + df['value2']
        
        # 模拟处理耗时
        time.sleep(0.02)
        
        return df

class TransformStage(PipelineStage):
    """数据转换阶段"""
    def __init__(self, input_queue: queue.Queue, output_queue: queue.Queue):
        super().__init__("数据转换", input_queue, output_queue)
        self.all_batches = []
    
    def process_item(self, item):
        if item is None:
            return None
        
        # 收集所有批次，在最后进行聚合
        self.all_batches.append(item)
        
        # 对当前批次进行一些转换
        df = item.copy()
        
        # 添加一些复杂计算
        for i in range(100):  # 减少计算量以适应批处理
            temp_calc = np.sum(np.random.random(100))
        
        time.sleep(0.015)
        
        return df
    
    def run(self):
        """重写run方法以处理聚合逻辑"""
        self.start_time = time.time()
        print(f"[流水线] {self.name} 开始运行")
        
        while True:
            try:
                item = self.input_queue.get(timeout=1)
                if item is None:
                    break
                
                processed_item = self.process_item(item)
                if processed_item is not None:
                    self.output_queue.put(processed_item)
                
                self.processed_count += 1
                self.input_queue.task_done()
                
            except queue.Empty:
                continue
        
        # 所有批次处理完成后，进行聚合
        if self.all_batches:
            print(f"[流水线] {self.name} 开始聚合 {len(self.all_batches)} 个批次")
            combined_df = pd.concat(self.all_batches, ignore_index=True)
            
            # 按类别聚合
            aggregated = combined_df.groupby('category').agg({
                'value1': ['mean', 'std', 'count'],
                'value2': ['mean', 'median'],
                'value1_normalized': 'mean',
                'value_ratio': 'mean'
            }).reset_index()
            
            aggregated.columns = ['_'.join(col).strip() if col[1] else col[0] for col in aggregated.columns]
            self.output_queue.put(('aggregated', aggregated))
        
        self.output_queue.put(None)
        self.end_time = time.time()
        print(f"[流水线] {self.name} 完成，处理了 {self.processed_count} 个批次，耗时 {self.end_time - self.start_time:.2f}秒")

class MetricsStage(PipelineStage):
    """指标计算阶段"""
    def __init__(self, input_queue: queue.Queue, output_queue: queue.Queue):
        super().__init__("指标计算", input_queue, output_queue)
        self.all_metrics = {}
    
    def process_item(self, item):
        if item is None:
            return None
        
        if isinstance(item, tuple) and item[0] == 'aggregated':
            # 处理聚合数据
            df = item[1]
            metrics = {}
            
            for col in df.select_dtypes(include=[np.number]).columns:
                metrics[f"{col}_stats"] = {
                    'mean': float(df[col].mean()),
                    'std': float(df[col].std()),
                    'min': float(df[col].min()),
                    'max': float(df[col].max())
                }
            
            # 复杂计算
            complex_matrix = np.random.random((200, 200))
            eigenvalues = np.linalg.eigvals(complex_matrix)
            metrics['complexity_score'] = float(np.mean(eigenvalues))
            
            self.all_metrics.update(metrics)
            return ('final_metrics', metrics)
        
        return item

class SaveStage(PipelineStage):
    """结果保存阶段"""
    def __init__(self, input_queue: queue.Queue, output_dir: str = "pipeline_output"):
        super().__init__("结果保存", input_queue, None)
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.saved_files = []
    
    def process_item(self, item):
        if item is None:
            return None
        
        if isinstance(item, tuple):
            if item[0] == 'aggregated':
                # 保存聚合数据
                df = item[1]
                filepath = f"{self.output_dir}/aggregated_data.csv"
                df.to_csv(filepath, index=False)
                self.saved_files.append(filepath)
                
            elif item[0] == 'final_metrics':
                # 保存最终指标
                metrics = item[1]
                filepath = f"{self.output_dir}/metrics.json"
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(metrics, f, indent=2, ensure_ascii=False)
                self.saved_files.append(filepath)
        
        time.sleep(0.005)
        return None

class PipelineProcessor:
    """流水线并行处理器"""
    def __init__(self):
        self.stages = []
        self.threads = []
        self.start_time = None
        self.end_time = None
    
    def run_pipeline(self, data_size: int = 100000, batch_size: int = 10000):
        """运行流水线并行处理"""
        print("=== 开始流水线并行处理 ===")
        self.start_time = time.time()
        
        # 创建队列
        data_queue = queue.Queue(maxsize=10)
        preprocess_queue = queue.Queue(maxsize=10)
        transform_queue = queue.Queue(maxsize=10)
        metrics_queue = queue.Queue(maxsize=10)
        
        # 创建各个阶段
        generator = DataGeneratorStage(data_queue, batch_size, data_size)
        preprocessor = PreprocessStage(data_queue, preprocess_queue)
        transformer = TransformStage(preprocess_queue, transform_queue)
        metrics_calculator = MetricsStage(transform_queue, metrics_queue)
        saver = SaveStage(metrics_queue)
        
        # 创建线程
        threads = [
            threading.Thread(target=generator.run, name="Generator"),
            threading.Thread(target=preprocessor.run, name="Preprocessor"),
            threading.Thread(target=transformer.run, name="Transformer"),
            threading.Thread(target=metrics_calculator.run, name="Metrics"),
            threading.Thread(target=saver.run, name="Saver")
        ]
        
        # 启动所有线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        
        print(f"=== 流水线并行处理总耗时: {total_time:.2f}秒 ===")
        
        # 保存时间统计
        timing_stats = {
            'total_time': total_time,
            'generator_time': generator.end_time - generator.start_time if generator.end_time else 0,
            'preprocessor_time': preprocessor.end_time - preprocessor.start_time if preprocessor.end_time else 0,
            'transformer_time': transformer.end_time - transformer.start_time if transformer.end_time else 0,
            'metrics_time': metrics_calculator.end_time - metrics_calculator.start_time if metrics_calculator.end_time else 0,
            'saver_time': saver.end_time - saver.start_time if saver.end_time else 0,
        }
        
        with open("pipeline_output/timing.json", 'w', encoding='utf-8') as f:
            json.dump(timing_stats, f, indent=2, ensure_ascii=False)
        
        return {
            'total_time': total_time,
            'stage_times': timing_stats,
            'processed_batches': generator.processed_count
        }

if __name__ == "__main__":
    processor = PipelineProcessor()
    result = processor.run_pipeline()
    print(f"\n处理结果: {result}")