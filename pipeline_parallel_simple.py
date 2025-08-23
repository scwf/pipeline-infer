#!/usr/bin/env python3
"""
简化的流水线并行数据处理脚本
使用更简单的方法实现流水线并行处理
"""

import time
import numpy as np
import pandas as pd
import os
import json
import threading
import queue
from typing import List, Dict

class SimplePipelineProcessor:
    """简化的流水线并行处理器"""
    
    def __init__(self):
        self.start_time = None
        self.stage_times = {}
    
    def log_time(self, stage_name):
        """记录阶段时间"""
        current_time = time.time()
        if self.start_time is None:
            self.start_time = current_time
            self.stage_times['start'] = 0
        else:
            elapsed = current_time - self.start_time
            self.stage_times[stage_name] = elapsed
            print(f"[流水线] {stage_name}: {elapsed:.2f}秒")
    
    def generate_batch(self, batch_id: int, batch_size: int, start_idx: int):
        """生成一批数据"""
        actual_size = min(batch_size, 100000 - start_idx)
        data = {
            'id': range(start_idx, start_idx + actual_size),
            'value1': np.random.normal(100, 15, actual_size),
            'value2': np.random.exponential(2, actual_size),
            'category': np.random.choice(['A', 'B', 'C', 'D'], actual_size),
            'batch_id': batch_id
        }
        df = pd.DataFrame(data)
        time.sleep(0.01)  # 模拟数据生成耗时
        return df
    
    def preprocess_batch(self, df):
        """预处理批次"""
        if df is None or df.empty:
            return df
        
        df_processed = df.copy()
        df_processed['value1_normalized'] = (df_processed['value1'] - df_processed['value1'].mean()) / df_processed['value1'].std()
        df_processed['value2_log'] = np.log1p(df_processed['value2'])
        df_processed['value_ratio'] = df_processed['value1'] / (df_processed['value2'] + 1)
        df_processed['value_sum'] = df_processed['value1'] + df_processed['value2']
        
        time.sleep(0.02)  # 模拟预处理耗时
        return df_processed
    
    def transform_batch(self, df):
        """转换批次"""
        if df is None or df.empty:
            return df
        
        # 简单的批次级聚合
        batch_agg = df.groupby('category').agg({
            'value1': ['mean', 'count'],
            'value2': ['mean'],
            'value1_normalized': 'mean',
            'value_ratio': 'mean'
        }).reset_index()
        
        # 扁平化列名
        batch_agg.columns = ['_'.join(col).strip() if col[1] else col[0] for col in batch_agg.columns]
        
        # 添加一些计算
        for i in range(100):
            temp_calc = np.sum(np.random.random(100))
        
        time.sleep(0.015)
        return batch_agg
    
    def producer(self, data_queue: queue.Queue, batch_size: int = 10000, total_size: int = 100000):
        """数据生成线程"""
        print("[流水线] 数据生成器开始")
        num_batches = (total_size + batch_size - 1) // batch_size
        
        for batch_id in range(num_batches):
            start_idx = batch_id * batch_size
            batch_data = self.generate_batch(batch_id, batch_size, start_idx)
            data_queue.put(('raw', batch_data))
        
        data_queue.put(('end', None))
        print(f"[流水线] 数据生成器完成，生成了 {num_batches} 个批次")
    
    def processor_stage(self, input_queue: queue.Queue, output_queue: queue.Queue, stage_name: str, process_func):
        """通用处理阶段"""
        print(f"[流水线] {stage_name}开始")
        processed_count = 0
        
        while True:
            try:
                item = input_queue.get(timeout=2)
                item_type, data = item
                
                if item_type == 'end':
                    output_queue.put(('end', None))
                    break
                
                # 处理数据
                result = process_func(data)
                output_queue.put((item_type, result))
                processed_count += 1
                
            except queue.Empty:
                break
            except Exception as e:
                print(f"[流水线] {stage_name}处理错误: {e}")
        
        print(f"[流水线] {stage_name}完成，处理了 {processed_count} 个项目")
    
    def consumer(self, input_queue: queue.Queue):
        """结果收集线程"""
        print("[流水线] 结果收集器开始")
        all_results = []
        
        while True:
            try:
                item = input_queue.get(timeout=2)
                item_type, data = item
                
                if item_type == 'end':
                    break
                
                if data is not None and not data.empty:
                    all_results.append(data)
                    
            except queue.Empty:
                break
        
        # 聚合所有结果
        if all_results:
            combined_df = pd.concat(all_results, ignore_index=True)
            final_agg = combined_df.groupby('category').agg({
                'value1_mean': 'mean',
                'value1_count': 'sum',
                'value2_mean': 'mean',
                'value1_normalized_mean': 'mean',
                'value_ratio_mean': 'mean'
            }).reset_index()
            
            # 保存结果
            os.makedirs("pipeline_output", exist_ok=True)
            final_agg.to_csv("pipeline_output/processed_data.csv", index=False)
            
            # 计算指标
            metrics = {}
            for col in final_agg.select_dtypes(include=[np.number]).columns:
                metrics[f"{col}_stats"] = {
                    'mean': float(final_agg[col].mean()),
                    'std': float(final_agg[col].std()),
                    'min': float(final_agg[col].min()),
                    'max': float(final_agg[col].max())
                }
            
            # 复杂计算
            complex_matrix = np.random.random((200, 200))
            eigenvalues = np.linalg.eigvals(complex_matrix)
            metrics['complexity_score'] = float(np.mean(eigenvalues.real))
            
            with open("pipeline_output/metrics.json", 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)
        
        print(f"[流水线] 结果收集器完成，聚合了 {len(all_results)} 个批次")
        return len(all_results)
    
    def run_pipeline(self, data_size: int = 100000, batch_size: int = 10000):
        """运行流水线并行处理"""
        print("=== 开始流水线并行处理 ===")
        self.start_time = time.time()
        
        # 创建队列
        data_queue = queue.Queue(maxsize=5)
        preprocess_queue = queue.Queue(maxsize=5)
        transform_queue = queue.Queue(maxsize=5)
        
        # 创建线程
        producer_thread = threading.Thread(
            target=self.producer, 
            args=(data_queue, batch_size, data_size)
        )
        
        preprocess_thread = threading.Thread(
            target=self.processor_stage,
            args=(data_queue, preprocess_queue, "预处理器", self.preprocess_batch)
        )
        
        transform_thread = threading.Thread(
            target=self.processor_stage,
            args=(preprocess_queue, transform_queue, "转换器", self.transform_batch)
        )
        
        consumer_thread = threading.Thread(
            target=self.consumer,
            args=(transform_queue,)
        )
        
        # 启动所有线程
        threads = [producer_thread, preprocess_thread, transform_thread, consumer_thread]
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        total_time = time.time() - self.start_time
        self.stage_times['total_time'] = total_time
        
        print(f"=== 流水线并行处理总耗时: {total_time:.2f}秒 ===")
        
        # 保存时间统计
        with open("pipeline_output/timing.json", 'w', encoding='utf-8') as f:
            json.dump(self.stage_times, f, indent=2, ensure_ascii=False)
        
        return {
            'total_time': total_time,
            'stage_times': self.stage_times
        }

if __name__ == "__main__":
    processor = SimplePipelineProcessor()
    result = processor.run_pipeline()
    print(f"\n处理结果: {result}")