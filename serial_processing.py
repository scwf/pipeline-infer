#!/usr/bin/env python3
"""
串行数据处理脚本 - 作为性能对比的基准
模拟一个包含多个阶段的数据处理流水线：
1. 数据读取和预处理
2. 数据转换
3. 数据计算
4. 结果写入
"""

import time
import numpy as np
import pandas as pd
import os
from typing import List, Dict
import json

class SerialProcessor:
    def __init__(self):
        self.start_time = None
        self.stage_times = {}
    
    def log_time(self, stage_name: str):
        """记录每个阶段的耗时"""
        current_time = time.time()
        if self.start_time is None:
            self.start_time = current_time
            self.stage_times['start'] = 0
        else:
            elapsed = current_time - self.start_time
            self.stage_times[stage_name] = elapsed
            print(f"[串行] {stage_name}: {elapsed:.2f}秒")
    
    def generate_data(self, size: int = 100000) -> pd.DataFrame:
        """生成测试数据"""
        self.log_time("开始数据生成")
        
        # 模拟较重的数据生成过程
        data = {
            'id': range(size),
            'value1': np.random.normal(100, 15, size),
            'value2': np.random.exponential(2, size),
            'category': np.random.choice(['A', 'B', 'C', 'D'], size),
            'timestamp': pd.date_range('2024-01-01', periods=size, freq='1min')
        }
        df = pd.DataFrame(data)
        
        # 添加一些计算密集的操作
        time.sleep(0.1)  # 模拟IO操作
        
        self.log_time("数据生成完成")
        return df
    
    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据预处理"""
        self.log_time("开始数据预处理")
        
        # 数据清洗和标准化
        df_processed = df.copy()
        df_processed['value1_normalized'] = (df_processed['value1'] - df_processed['value1'].mean()) / df_processed['value1'].std()
        df_processed['value2_log'] = np.log1p(df_processed['value2'])
        
        # 创建一些特征
        df_processed['value_ratio'] = df_processed['value1'] / (df_processed['value2'] + 1)
        df_processed['value_sum'] = df_processed['value1'] + df_processed['value2']
        
        # 模拟一些耗时操作
        time.sleep(0.2)
        
        self.log_time("数据预处理完成")
        return df_processed
    
    def transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据转换"""
        self.log_time("开始数据转换")
        
        # 按类别分组并进行聚合
        df_transformed = df.groupby('category').agg({
            'value1': ['mean', 'std', 'count'],
            'value2': ['mean', 'median'],
            'value1_normalized': 'mean',
            'value_ratio': 'mean'
        }).reset_index()
        
        # 扁平化列名
        df_transformed.columns = ['_'.join(col).strip() if col[1] else col[0] for col in df_transformed.columns]
        
        # 添加一些复杂计算
        for i in range(1000):
            temp_calc = np.sum(np.random.random(1000))
        
        time.sleep(0.15)
        
        self.log_time("数据转换完成")
        return df_transformed
    
    def compute_metrics(self, df: pd.DataFrame) -> Dict:
        """计算指标"""
        self.log_time("开始指标计算")
        
        metrics = {}
        
        # 计算各种统计指标
        for col in df.select_dtypes(include=[np.number]).columns:
            metrics[f"{col}_stats"] = {
                'mean': float(df[col].mean()),
                'std': float(df[col].std()),
                'min': float(df[col].min()),
                'max': float(df[col].max())
            }
        
        # 模拟复杂计算
        complex_matrix = np.random.random((500, 500))
        eigenvalues = np.linalg.eigvals(complex_matrix)
        metrics['complexity_score'] = float(np.mean(eigenvalues))
        
        time.sleep(0.1)
        
        self.log_time("指标计算完成")
        return metrics
    
    def save_results(self, df: pd.DataFrame, metrics: Dict, output_dir: str = "serial_output"):
        """保存结果"""
        self.log_time("开始保存结果")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存数据框
        df.to_csv(f"{output_dir}/processed_data.csv", index=False)
        
        # 保存指标
        with open(f"{output_dir}/metrics.json", 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        
        # 保存时间统计
        with open(f"{output_dir}/timing.json", 'w', encoding='utf-8') as f:
            json.dump(self.stage_times, f, indent=2, ensure_ascii=False)
        
        time.sleep(0.05)
        
        self.log_time("结果保存完成")
    
    def run_pipeline(self, data_size: int = 100000):
        """运行完整的串行处理流水线"""
        print("=== 开始串行处理 ===")
        pipeline_start = time.time()
        
        # 步骤1: 生成数据
        raw_data = self.generate_data(data_size)
        
        # 步骤2: 预处理
        preprocessed_data = self.preprocess_data(raw_data)
        
        # 步骤3: 数据转换
        transformed_data = self.transform_data(preprocessed_data)
        
        # 步骤4: 计算指标
        metrics = self.compute_metrics(transformed_data)
        
        # 步骤5: 保存结果
        self.save_results(transformed_data, metrics)
        
        total_time = time.time() - pipeline_start
        print(f"=== 串行处理总耗时: {total_time:.2f}秒 ===")
        
        return {
            'total_time': total_time,
            'stage_times': self.stage_times,
            'processed_records': len(transformed_data)
        }

if __name__ == "__main__":
    processor = SerialProcessor()
    result = processor.run_pipeline()
    print(f"\n处理结果: {result}")