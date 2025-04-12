"""
CLI主入口测试
"""

from acolyte.cli.main import cli


def test_cli_import():
    """测试CLI导入"""
    # 验证cli是从commands模块导入的
    from acolyte.cli.commands import cli as commands_cli
    assert cli is commands_cli


def test_main_file_exists():
    """测试main.py文件存在"""
    import os
    # 检查文件是否存在
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                            'acolyte', 'cli', 'main.py')
    assert os.path.isfile(file_path), f"File not found: {file_path}"

    # 检查文件内容
    with open(file_path, 'r') as f:
        content = f.read()
        assert "from acolyte.cli.commands import cli" in content
        assert "if __name__ == \"__main__\"" in content
        assert "cli()" in content
