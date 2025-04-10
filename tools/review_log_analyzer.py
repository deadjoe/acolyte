#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
评议模式日志分析工具

该工具用于分析multiple_with_review模式的日志，提取关键信息，
帮助开发者快速定位问题。
"""

import argparse
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# 定义颜色代码
COLORS = {
    "RESET": "\033[0m",
    "RED": "\033[31m",
    "GREEN": "\033[32m",
    "YELLOW": "\033[33m",
    "BLUE": "\033[34m",
    "MAGENTA": "\033[35m",
    "CYAN": "\033[36m",
    "WHITE": "\033[37m",
    "BOLD": "\033[1m",
}


def colorize(text: str, color: str) -> str:
    """为文本添加颜色"""
    return f"{COLORS.get(color.upper(), '')}{text}{COLORS['RESET']}"


class ReviewLogAnalyzer:
    """评议模式日志分析器"""

    def __init__(self, log_file: str, task_id: Optional[int] = None):
        """
        初始化分析器

        Args:
            log_file: 日志文件路径
            task_id: 要分析的任务ID，如果为None则分析所有任务
        """
        self.log_file = log_file
        self.task_id = task_id
        self.log_lines = []
        self.task_logs = {}  # 按任务ID组织的日志
        self.keywords = [
            # 处理流程关键字
            "开始多LLM评议处理: 任务ID=",
            "多LLM处理失败",
            "未找到评议者LLM",
            "使用单评议者模式: 评议者=",
            "使用多评议者投票模式: 评议者数量=",
            "多LLM评议处理完成(单评议者模式)",
            "多LLM评议处理完成(多评议者投票模式)",
            "多LLM评议处理完成(无评议者)",
            "获取任务结果失败",
            "无法从结果中提取关键字段，使用原始响应",
            "开始评议处理: 任务ID=",
            "评议处理完成: 任务ID=",
            "无法将review_result字符串解析为JSON",
            "评议者选择结果: 评议者",
            "无法解析评议者选择: 评议者=",
            "保存投票记录失败: 任务ID=",
            "正则表达式匹配成功但没有捕获到结果编号",
            "无法解析投票结果: ",
            "解析投票结果异常: ",
            "保存投票记录异常: 任务ID=",
            "设置任务最终结果: 任务ID=",
            "更新任务最终结果: 任务ID=",
            "设置最终结果异常: 任务ID=",
            "更新任务状态异常: ID=",
            "评议处理错误: ID=",
            # 其他相关关键字
            "voted_result_id",
            "raw_response",
            "保存投票记录成功: 任务ID=",
        ]

    def load_log(self) -> None:
        """加载日志文件"""
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                self.log_lines = f.readlines()
            print(f"已加载日志文件: {self.log_file}, 共 {len(self.log_lines)} 行")
        except Exception as e:
            print(f"加载日志文件失败: {str(e)}")
            sys.exit(1)

    def extract_task_id(self, line: str) -> Optional[int]:
        """从日志行中提取任务ID"""
        match = re.search(r"任务ID=(\d+)", line)
        if match:
            return int(match.group(1))
        return None

    def extract_timestamp(self, line: str) -> Optional[datetime]:
        """从日志行中提取时间戳"""
        match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})", line)
        if match:
            timestamp_str = match.group(1)
            try:
                return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
            except ValueError:
                return None
        return None

    def extract_log_level(self, line: str) -> Optional[str]:
        """从日志行中提取日志级别"""
        match = re.search(r"\[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]", line)
        if match:
            return match.group(1)
        return None

    def organize_logs_by_task(self) -> None:
        """按任务ID组织日志"""
        for line in self.log_lines:
            task_id = self.extract_task_id(line)
            if task_id is not None:
                if task_id not in self.task_logs:
                    self.task_logs[task_id] = []
                self.task_logs[task_id].append(line)
            elif "multiple_with_review" in line:
                # 对于没有任务ID但包含multiple_with_review的行，添加到所有任务中
                for task_id in self.task_logs:
                    self.task_logs[task_id].append(line)

    def filter_logs_by_keywords(self, lines: List[str]) -> List[Tuple[str, datetime, str, str]]:
        """
        根据关键字过滤日志行

        Args:
            lines: 日志行列表

        Returns:
            过滤后的日志行列表，每项为 (行内容, 时间戳, 日志级别, 匹配的关键字)
        """
        filtered_lines = []
        for line in lines:
            timestamp = self.extract_timestamp(line)
            log_level = self.extract_log_level(line)

            for keyword in self.keywords:
                if keyword in line:
                    filtered_lines.append((line, timestamp, log_level, keyword))
                    break

        # 按时间戳排序
        filtered_lines.sort(key=lambda x: x[1] if x[1] else datetime.min)
        return filtered_lines

    def colorize_log_level(self, level: Optional[str]) -> str:
        """为日志级别添加颜色"""
        if level == "DEBUG":
            return colorize(level, "BLUE")
        elif level == "INFO":
            return colorize(level, "GREEN")
        elif level == "WARNING":
            return colorize(level, "YELLOW")
        elif level == "ERROR":
            return colorize(level, "RED")
        elif level == "CRITICAL":
            return colorize(level, "MAGENTA")
        return level or ""

    def highlight_keywords(self, line: str) -> str:
        """高亮关键字"""
        for keyword in self.keywords:
            if keyword in line:
                line = line.replace(keyword, colorize(keyword, "BOLD"))
        return line

    def analyze(self) -> None:
        """分析日志"""
        self.load_log()
        self.organize_logs_by_task()

        if self.task_id is not None:
            # 分析特定任务
            if self.task_id in self.task_logs:
                self.analyze_task(self.task_id)
            else:
                print(f"未找到任务ID={self.task_id}的日志")
        else:
            # 分析所有任务
            if not self.task_logs:
                print("未找到任何任务的日志")
                return

            for task_id in sorted(self.task_logs.keys()):
                self.analyze_task(task_id)

    def analyze_task(self, task_id: int) -> None:
        """分析特定任务的日志"""
        print(f"\n{colorize('='*80, 'BOLD')}")
        print(f"{colorize(f'任务ID: {task_id}', 'BOLD')}")
        print(f"{colorize('='*80, 'BOLD')}")

        filtered_lines = self.filter_logs_by_keywords(self.task_logs[task_id])

        if not filtered_lines:
            print(f"未找到任务ID={task_id}的相关日志")
            return

        # 打印过滤后的日志
        for line, timestamp, level, _ in filtered_lines:
            timestamp_str = timestamp.strftime("%H:%M:%S.%f")[:-3] if timestamp else ""
            level_str = self.colorize_log_level(level)
            highlighted_line = self.highlight_keywords(line.strip())
            print(f"{colorize(timestamp_str, 'CYAN')} {level_str}: {highlighted_line}")

        # 分析任务处理流程
        self.analyze_task_flow(filtered_lines, task_id)

    def analyze_task_flow(self, filtered_lines: List[Tuple[str, datetime, str, str]], task_id: int = None) -> None:
        """分析任务处理流程"""
        print(f"\n{colorize('任务处理流程分析', 'BOLD')}")
        print(f"{colorize('-'*80, 'BOLD')}")

        # 检查是否有错误或警告
        errors = [line for line, _, level, _ in filtered_lines if level in ["ERROR", "WARNING"]]
        if errors:
            print(f"{colorize('发现错误或警告:', 'RED')}")
            for error in errors:
                print(f"  {colorize('•', 'RED')} {error.strip()}")
            print()

        # 检查评议者选择结果
        # 使用外部grep命令搜索
        import subprocess
        try:
            cmd = f"grep -i '评议者选择结果' {self.log_file} | grep -i '任务ID={task_id}' || grep -i '评议者选择结果' {self.log_file}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            vote_results = result.stdout.strip().split('\n') if result.stdout.strip() else []
        except Exception as e:
            print(f"grep命令执行失败: {str(e)}")
            vote_results = []
        if vote_results:
            print(f"{colorize('评议者选择结果:', 'GREEN')}")
            for result in vote_results:
                print(f"  {colorize('•', 'GREEN')} {result.strip()}")
        else:
            print(f"{colorize('未找到评议者选择结果', 'YELLOW')}")

        # 检查投票记录保存
        vote_saves = [line for line, _, _, keyword in filtered_lines if "保存投票记录" in keyword and "异常" not in keyword and "失败" not in keyword]
        if vote_saves:
            print(f"{colorize('投票记录保存成功', 'GREEN')}")
        else:
            print(f"{colorize('未找到投票记录保存成功的日志', 'YELLOW')}")

        # 检查最终结果设置
        final_results = [line for line, _, _, keyword in filtered_lines if "最终结果" in keyword and "异常" not in keyword]
        if final_results:
            print(f"{colorize('最终结果设置:', 'GREEN')}")
            for result in final_results:
                print(f"  {colorize('•', 'GREEN')} {result.strip()}")
        else:
            print(f"{colorize('未找到最终结果设置的日志', 'YELLOW')}")

        # 检查处理完成
        completions = [line for line, _, _, keyword in filtered_lines if "多LLM评议处理完成" in keyword]
        if completions:
            print(f"{colorize('处理完成:', 'GREEN')}")
            for completion in completions:
                print(f"  {colorize('•', 'GREEN')} {completion.strip()}")
        else:
            print(f"{colorize('未找到处理完成的日志', 'YELLOW')}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="评议模式日志分析工具")
    parser.add_argument("log_file", help="日志文件路径")
    parser.add_argument("-t", "--task-id", type=int, help="要分析的任务ID")
    parser.add_argument("-l", "--latest", action="store_true", help="分析最新的日志文件")
    args = parser.parse_args()

    log_file = args.log_file

    # 如果指定了--latest参数，则使用最新的日志文件
    if args.latest:
        log_dir = os.path.dirname(log_file) or "."
        log_files = [f for f in os.listdir(log_dir) if f.startswith("acolyte_") and f.endswith(".log")]
        if log_files:
            log_files.sort(reverse=True)
            log_file = os.path.join(log_dir, log_files[0])
            print(f"使用最新的日志文件: {log_file}")
        else:
            print(f"在 {log_dir} 目录下未找到任何日志文件")
            sys.exit(1)

    analyzer = ReviewLogAnalyzer(log_file, args.task_id)
    analyzer.analyze()


if __name__ == "__main__":
    main()
