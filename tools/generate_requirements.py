#!/usr/bin/env python
"""
生成精确的 requirements.txt 文件

此脚本从 setup.py 中提取依赖项，并生成精确的 requirements.txt 文件。
"""

import re
import subprocess
import sys
from pathlib import Path

# 获取项目根目录
project_root = Path(__file__).parent.parent

# 从 setup.py 中提取依赖项
setup_path = project_root / "setup.py"
with open(setup_path, "r", encoding="utf-8") as f:
    setup_content = f.read()

# 提取 install_requires 部分
install_requires_match = re.search(r"install_requires=\[(.*?)\]", setup_content, re.DOTALL)
if not install_requires_match:
    print("错误: 在 setup.py 中未找到 install_requires")
    sys.exit(1)

install_requires_content = install_requires_match.group(1)
# 提取依赖项
dependencies = re.findall(r'"([^"]+)"', install_requires_content)

# 提取 extras_require 部分
extras_require_match = re.search(r"extras_require=\{(.*?)\}", setup_content, re.DOTALL)
if extras_require_match:
    extras_require_content = extras_require_match.group(1)
    # 提取 dev 依赖项
    dev_match = re.search(r'"dev":\s*\[(.*?)\]', extras_require_content, re.DOTALL)
    if dev_match:
        dev_content = dev_match.group(1)
        dev_dependencies = re.findall(r'"([^"]+)"', dev_content)
    else:
        dev_dependencies = []
else:
    dev_dependencies = []

print(f"主要依赖项: {len(dependencies)}")
for dep in dependencies:
    print(f"  - {dep}")

print(f"\n开发依赖项: {len(dev_dependencies)}")
for dep in dev_dependencies:
    print(f"  - {dep}")

# 获取已安装包的精确版本
result = subprocess.run(["uv", "pip", "list", "--format=json"], capture_output=True, text=True)
if result.returncode != 0:
    print(f"错误: 无法获取已安装的包: {result.stderr}")
    sys.exit(1)

import json

installed_packages = json.loads(result.stdout)
installed_dict = {pkg["name"].lower(): pkg["version"] for pkg in installed_packages}

print("\n已安装的主要依赖项:")
for dep in dependencies:
    match = re.match(r"([^>=<~!]+)(.+)?", dep)
    if match:
        package_name = match.group(1).strip().lower()
        if package_name in installed_dict:
            print(f"  - {package_name}=={installed_dict[package_name]}")
        else:
            print(f"  - {dep} (未安装)")

# 生成精确版本的 requirements.txt
requirements_path = project_root / "requirements.txt"
with open(requirements_path, "w", encoding="utf-8") as f:
    for dep in dependencies:
        # 提取包名和版本约束
        match = re.match(r"([^>=<~!]+)(.+)?", dep)
        if not match:
            continue

        package_name = match.group(1).strip().lower()

        # 查找已安装的精确版本
        if package_name in installed_dict:
            exact_version = installed_dict[package_name]
            f.write(f"{package_name}=={exact_version}\n")
        else:
            f.write(f"{dep}\n")

# 生成兼容版本约束的 requirements.txt
requirements_compat_path = project_root / "requirements-compat.txt"
with open(requirements_compat_path, "w", encoding="utf-8") as f:
    for dep in dependencies:
        f.write(f"{dep}\n")

# 生成 dev-requirements.txt
dev_requirements_path = project_root / "dev-requirements.txt"
with open(dev_requirements_path, "w", encoding="utf-8") as f:
    for dep in dev_dependencies:
        # 提取包名和版本约束
        match = re.match(r"([^>=<~!]+)(.+)?", dep)
        if not match:
            continue

        package_name = match.group(1).strip().lower()
        version_constraint = match.group(2) if match.group(2) else ""

        # 查找已安装的精确版本
        if package_name in installed_dict:
            exact_version = installed_dict[package_name]
            f.write(f"{package_name}=={exact_version}\n")
        else:
            f.write(f"{dep}\n")

print(f"\n已生成文件:\n- {requirements_path} (精确版本)\n- {requirements_compat_path} (兼容版本约束)\n- {dev_requirements_path} (开发依赖)")
