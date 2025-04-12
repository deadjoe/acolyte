"""
CLI历史显示测试
"""

import os
import pytest


def test_history_show_file_exists():
    """测试history_show文件存在"""
    # 检查文件是否存在
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                            'acolyte', 'cli', 'history_show.py')
    assert os.path.isfile(file_path), f"File not found: {file_path}"
