#!/usr/bin/env python3
"""
多进程并行数据处理脚本
使用multiprocessing进行数据并行处理，充分利用多核CPU
"""

import time
import numpy as np
import pandas as pd
import os
import json
import multiprocessing as mp
from functools import partial
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

def generate_data_chunk(args):
    """生成数据块"""
    start_idx, chunk_size, chunk_id = args
    
    # 生成数据
    data = {
        'id': range(start_idx, start_idx + chunk_size),
        'value1': np.random.normal(100, 15, chunk_size),
        'value2': np.random.exponential(2, chunk_size),
        'category': np.random.choice(['A', 'B', 'C', 'D'], chunk_size),
        'chunk_id': chunk_id
    }
    
    df = pd.DataFrame(data)
    
    # 模拟数据生成耗时
    time.sleep(0.01)
    
    return df

def preprocess_chunk(df):
    """预处理数据块"""
    if df is None or df.empty:
        return df
    
    df_processed = df.copy()
    
    # 数据标准化
    df_processed['value1_normalized'] = (df_processed['value1'] - df_processed['value1'].mean()) / df_processed['value1'].std()
    df_processed['value2_log'] = np.log1p(df_processed['value2'])
    
    # 创建特征
    df_processed['value_ratio'] = df_processed['value1'] / (df_processed['value2'] + 1)
    df_processed['value_sum'] = df_processed['value1'] + df_processed['value2']
    
    # 模拟处理耗时
    time.sleep(0.02)
    
    return df_processed

def transform_chunk(df):
    """转换数据块"""
    if df is None or df.empty:
        return df
    
    # 对单个chunk进行本地聚合
    chunk_agg = df.groupby('category').agg({
        'value1': ['mean', 'std', 'count'],
        'value2': ['mean', 'median'],
        'value1_normalized': 'mean',
        'value_ratio': 'mean'
    })
    
    # 扁平化列名
    chunk_agg.columns = ['_'.join(col).strip() if col[1] else col[0] for col in chunk_agg.columns]
    chunk_agg = chunk_agg.reset_index()
    
    # 添加复杂计算
    for i in range(200):
        temp_calc = np.sum(np.random.random(500))
    
    time.sleep(0.015)
    
    return chunk_agg

def compute_chunk_metrics(df):
    """计算数据块指标"""
    if df is None or df.empty:
        return {}
    
    metrics = {}
    
    # 计算统计指标
    for col in df.select_dtypes(include=[np.number]).columns:
        if col != 'category':  # 跳过分类列
            metrics[f"{col}_stats"] = {
                'mean': float(df[col].mean()),
                'std': float(df[col].std()),
                'min': float(df[col].min()),
                'max': float(df[col].max()),
                'count': int(df[col].count())
            }
    
    # 模拟复杂计算
    try:
        complex_matrix = np.random.random((100, 100))
        eigenvalues = np.linalg.eigvals(complex_matrix)
        metrics['complexity_score'] = float(np.mean(eigenvalues))
    except:
        metrics['complexity_score'] = 0.0
    
    time.sleep(0.01)
    
    return metrics

def aggregate_results(results_list):
    """聚合多个结果"""
    if not results_list:
        return pd.DataFrame(), {}
    
    # 聚合数据框
    valid_dfs = [df for df in results_list if isinstance(df, pd.DataFrame) and not df.empty]
    if valid_dfs:
        combined_df = pd.concat(valid_dfs, ignore_index=True)
        # 重新聚合
        final_agg = combined_df.groupby('category').agg({
            'value1_mean': 'mean',
            'value1_std': 'mean',
            'value1_count': 'sum',
            'value2_mean': 'mean',
            'value2_median': 'mean',
            'value1_normalized_mean': 'mean',
            'value_ratio_mean': 'mean'
        }).reset_index()
    else:
        final_agg = pd.DataFrame()
    
    return final_agg

def aggregate_metrics(metrics_list):
    """聚合多个指标"""
    if not metrics_list:
        return {}
    
    aggregated = {}
    
    # 收集所有指标键
    all_keys = set()
    for metrics in metrics_list:
        if isinstance(metrics, dict):
            all_keys.update(metrics.keys())
    
    # 聚合每个指标
    for key in all_keys:
        if key == 'complexity_score':
            # 对复杂度分数求平均
            scores = [m.get(key, 0) for m in metrics_list if isinstance(m, dict)]
            aggregated[key] = float(np.mean(scores)) if scores else 0.0
        elif key.endswith('_stats'):
            # 聚合统计信息
            stats_list = [m.get(key, {}) for m in metrics_list if isinstance(m, dict)]
            if stats_list:
                means = [s.get('mean', 0) for s in stats_list if isinstance(s, dict)]
                counts = [s.get('count', 0) for s in stats_list if isinstance(s, dict)]
                
                total_count = sum(counts)
                if total_count > 0:
                    weighted_mean = sum(m * c for m, c in zip(means, counts)) / total_count
                    aggregated[key] = {
                        'mean': float(weighted_mean),
                        'total_count': int(total_count)
                    }
    
    return aggregated

class MultiprocessProcessor:
    """多进程并行处理器"""
    def __init__(self, n_processes=None):
        self.n_processes = n_processes or mp.cpu_count()
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
            print(f"[多进程] {stage_name}: {elapsed:.2f}秒")
    
    def run_pipeline(self, data_size: int = 100000):
        """运行多进程并行处理流水线"""
        print(f"=== 开始多进程并行处理 (使用{self.n_processes}个进程) ===")
        pipeline_start = time.time()
        self.start_time = pipeline_start
        
        # 计算数据分块
        chunk_size = max(1, data_size // (self.n_processes * 2))  # 创建更多块以平衡负载
        chunks = []
        for i in range(0, data_size, chunk_size):
            actual_chunk_size = min(chunk_size, data_size - i)
            chunks.append((i, actual_chunk_size, len(chunks)))
        
        print(f"数据分为 {len(chunks)} 个块，每块约 {chunk_size} 条记录")
        
        with mp.Pool(self.n_processes) as pool:
            # 阶段1: 并行生成数据
            self.log_time("开始数据生成")
            raw_data_chunks = pool.map(generate_data_chunk, chunks)
            self.log_time("数据生成完成")
            
            # 阶段2: 并行预处理
            self.log_time("开始数据预处理")
            preprocessed_chunks = pool.map(preprocess_chunk, raw_data_chunks)
            self.log_time("数据预处理完成")
            
            # 阶段3: 并行转换
            self.log_time("开始数据转换")
            transformed_chunks = pool.map(transform_chunk, preprocessed_chunks)
            self.log_time("数据转换完成")
            
            # 阶段4: 并行计算指标
            self.log_time("开始指标计算")
            chunk_metrics = pool.map(compute_chunk_metrics, transformed_chunks)
            self.log_time("指标计算完成")
        
        # 阶段5: 聚合结果
        self.log_time("开始结果聚合")
        final_data = aggregate_results(transformed_chunks)
        final_metrics = aggregate_metrics(chunk_metrics)
        self.log_time("结果聚合完成")
        
        # 阶段6: 保存结果
        self.log_time("开始保存结果")
        self.save_results(final_data, final_metrics)
        self.log_time("结果保存完成")
        
        total_time = time.time() - pipeline_start
        print(f"=== 多进程并行处理总耗时: {total_time:.2f}秒 ===")
        
        return {
            'total_time': total_time,
            'stage_times': self.stage_times,
            'processed_chunks': len(chunks),
            'processes_used': self.n_processes
        }
    
    def save_results(self, df: pd.DataFrame, metrics: Dict, output_dir: str = "multiprocess_output"):
        """保存结果"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存数据框
        if not df.empty:
            df.to_csv(f"{output_dir}/processed_data.csv", index=False)
        
        # 保存指标
        with open(f"{output_dir}/metrics.json", 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        
        # 保存时间统计
        with open(f"{output_dir}/timing.json", 'w', encoding='utf-8') as f:
            json.dump(self.stage_times, f, indent=2, ensure_ascii=False)

def run_with_different_process_counts(data_size: int = 100000):
    """使用不同进程数进行测试"""
    cpu_count = mp.cpu_count()
    process_counts = [1, 2, min(4, cpu_count), cpu_count]
    results = {}
    
    print(f"系统CPU核心数: {cpu_count}")
    print("测试不同进程数的性能...")
    
    for n_proc in process_counts:
        print(f"\n--- 测试 {n_proc} 个进程 ---")
        processor = MultiprocessProcessor(n_proc)
        result = processor.run_pipeline(data_size)
        results[f"{n_proc}_processes"] = result
        
        # 清理一下内存
        time.sleep(0.5)
    
    # 保存对比结果
    with open("multiprocess_comparison.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n=== 不同进程数性能对比 ===")
    for proc_count, result in results.items():
        print(f"{proc_count}: {result['total_time']:.2f}秒")
    
    return results

if __name__ == "__main__":
    # 运行单次测试
    processor = MultiprocessProcessor()
    result = processor.run_pipeline()
    print(f"\n处理结果: {result}")
    
    # 运行不同进程数对比测试
    print("\n" + "="*50)
    comparison_results = run_with_different_process_counts()