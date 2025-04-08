#!/usr/bin/env python
"""
检查版本号一致性

此脚本检查项目中所有地方的版本号是否一致。
"""

import os
import re
import sys
from pathlib import Path

# 获取项目根目录
project_root = Path(__file__).parent.parent

# 检查 acolyte/__init__.py
init_path = project_root / "acolyte" / "__init__.py"
with open(init_path, "r", encoding="utf-8") as f:
    init_content = f.read()
    init_version_match = re.search(r'__version__ = "(.*?)"', init_content)
    if not init_version_match:
        print(f"错误: 在 {init_path} 中未找到版本号")
        sys.exit(1)
    init_version = init_version_match.group(1)
    print(f"acolyte/__init__.py 版本号: {init_version}")

# 检查 pyproject.toml
pyproject_path = project_root / "pyproject.toml"
with open(pyproject_path, "r", encoding="utf-8") as f:
    pyproject_content = f.read()
    pyproject_version_match = re.search(r'version = "(.*?)"', pyproject_content)
    if not pyproject_version_match:
        print(f"错误: 在 {pyproject_path} 中未找到版本号")
        sys.exit(1)
    pyproject_version = pyproject_version_match.group(1)
    print(f"pyproject.toml 版本号: {pyproject_version}")

# 检查 setup.py (应该从 __init__.py 导入，但我们仍然检查一下)
setup_path = project_root / "setup.py"
with open(setup_path, "r", encoding="utf-8") as f:
    setup_content = f.read()
    if "version=version" not in setup_content:
        print(f"警告: setup.py 可能没有从 __init__.py 导入版本号")

# 检查 acolyte/api/app.py
app_path = project_root / "acolyte" / "api" / "app.py"
with open(app_path, "r", encoding="utf-8") as f:
    app_content = f.read()
    if "from acolyte import __version__" not in app_content:
        print(f"警告: {app_path} 可能没有导入 __version__")
    if "version=__version__" not in app_content:
        print(f"警告: {app_path} 中的 FastAPI 应用可能没有使用 __version__")
    if "\"version\": __version__" not in app_content:
        print(f"警告: {app_path} 中的根路径响应可能没有使用 __version__")

# 检查 acolyte/main.py
main_path = project_root / "acolyte" / "main.py"
with open(main_path, "r", encoding="utf-8") as f:
    main_content = f.read()
    if "from acolyte import __version__" not in main_content:
        print(f"警告: {main_path} 可能没有导入 __version__")
    if "应用版本: {__version__}" not in main_content:
        print(f"警告: {main_path} 中的日志可能没有使用 __version__")

# 版本号一致性检查
if init_version != pyproject_version:
    print(f"错误: 版本号不一致")
    print(f"  acolyte/__init__.py: {init_version}")
    print(f"  pyproject.toml: {pyproject_version}")
    sys.exit(1)

print("版本号检查通过!")
