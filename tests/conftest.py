import pytest
import numpy as np
import cv2

@pytest.fixture
def sample_image_data():
    """创建一个测试用的示例图像"""
    return np.zeros((100, 100, 3), dtype=np.uint8)

@pytest.fixture
def temp_image_path(tmp_path, sample_image_data):
    """创建一个临时图像文件"""
    image_path = tmp_path / "test_image.jpg"
    cv2.imwrite(str(image_path), sample_image_data)
    return str(image_path) 