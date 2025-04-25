#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 设置环境变量
export PYTHONPATH=.

# 清理旧的覆盖率数据和报告
echo -e "${BLUE}清理旧的覆盖率数据...${NC}"
rm -f .coverage
rm -rf coverage_html_report

# 运行所有单元测试
echo -e "${BLUE}运行所有单元测试并生成覆盖率报告...${NC}"
uv run pytest tests/unit \
    -v \
    --cov=acolyte \
    --cov-report=term-missing \
    --cov-report=html:coverage_html_report \
    --cov-config=.coveragerc

# 检查测试是否成功
if [ $? -eq 0 ]; then
    echo -e "${GREEN}测试完成！${NC}"
    echo -e "${BLUE}HTML覆盖率报告已生成在 coverage_html_report 目录${NC}"
else
    echo -e "\033[0;31m测试失败！${NC}"
    exit 1
fi
