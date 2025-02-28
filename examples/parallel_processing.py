from src.pipeline import Pipeline
from src.executors.parallel import ThreadExecutor, ProcessExecutor
from src.operators.map import MapLikeOperator
from src.operators.filter import FilterOperator

def process_image(image):
    # 耗时操作
    return image + 1

def is_valid_tile(image):
    # 检查图像块是否有效
    return image is not None and image.size > 0

# 方式1：通过parallel_degree参数隐式设置执行器
pipeline1 = (Pipeline("example1")
    .read_image("reader", "image.jpg")
    .filter("valid_tiles", is_valid_tile, parallel_degree=4))

# 方式2：显式设置执行器
pipeline2 = (Pipeline("example2")
    .read_image("reader", "image.jpg")
    .filter("valid_tiles", is_valid_tile, 
            parallel_degree=4, 
            executor_type=ProcessExecutor))

# 方式3：对特定算子设置执行器
process_op = (MapLikeOperator("process", process_image)
    .set_executor(ThreadExecutor(max_workers=4)))

pipeline3 = (Pipeline("example3")
    .read_image("reader", "image.jpg")
    .then(process_op))

# 或者直接创建算子时指定
filter_op = FilterOperator(
    "valid_tiles", 
    is_valid_tile, 
    parallel_degree=4,
    executor_type=ProcessExecutor
) 