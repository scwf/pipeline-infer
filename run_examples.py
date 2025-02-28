import sys
import os
import argparse

# 添加项目根目录到 PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def run_data_augmentation():
    print("\n运行数据增强示例...")
    from examples import data_augmentation
    data_augmentation.main()

def run_multi_model():
    print("\n运行多模型推理示例...")
    from examples import multi_model_inference
    multi_model_inference.main()

def run_multi_scale():
    print("\n运行多尺度处理示例...")
    from examples import multi_scale_processing
    multi_scale_processing.main()

def run_quality_control():
    print("\n运行质量控制示例...")
    from examples import quality_control
    quality_control.main()

def run_image_inference():
    print("\n运行图像推理示例...")
    from examples import image_inference
    image_inference.main()

def main():
    """运行所有示例"""
    examples = [
        run_data_augmentation,
        run_multi_model,
        run_multi_scale,
        run_quality_control,
        run_image_inference
    ]
    
    print("开始运行所有示例...")
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"运行示例 {example.__name__} 时出错: {str(e)}")
    print("\n所有示例运行完成!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行流水线示例")
    parser.add_argument('example', nargs='?', choices=[
        'all',
        'augmentation',
        'multi_model',
        'multi_scale',
        'quality',
        'inference'
    ], default='all', help='选择要运行的示例')

    args = parser.parse_args()

    # 示例映射
    examples = {
        'all': main,
        'augmentation': run_data_augmentation,
        'multi_model': run_multi_model,
        'multi_scale': run_multi_scale,
        'quality': run_quality_control,
        'inference': run_image_inference
    }

    # 运行选择的示例
    examples[args.example]() 