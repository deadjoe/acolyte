"""
CLI命令测试
"""

import pytest
from click.testing import CliRunner

from acolyte.cli.commands import cli


class TestCliCommands:
    """测试CLI命令"""

    @pytest.fixture
    def runner(self):
        """创建CLI测试运行器"""
        return CliRunner()

    def test_cli_group(self):
        """测试CLI命令组"""
        # 验证cli是一个命令组
        assert cli.name == "cli"
        assert "Acolyte" in cli.help

    def test_config_command_group(self):
        """测试配置命令组"""
        # 获取config命令组
        config_cmd = cli.commands.get("config")

        # 验证config是一个命令组
        assert config_cmd is not None
        assert config_cmd.name == "config"

        # 验证子命令
        subcommands = config_cmd.commands
        assert "set-default" in subcommands
        assert "delete-llm" in subcommands

    def test_history_command_group(self):
        """测试历史命令组"""
        # 获取history命令组
        history_cmd = cli.commands.get("history")

        # 验证history是一个命令组
        assert history_cmd is not None
        assert history_cmd.name == "history"

        # 验证子命令
        subcommands = history_cmd.commands
        assert "list" in subcommands
        assert "delete" in subcommands

    def test_analyze_command(self):
        """测试分析命令"""
        # 获取analyze命令
        analyze_cmd = cli.commands.get("analyze")

        # 验证analyze是一个命令
        assert analyze_cmd is not None
        assert analyze_cmd.name == "analyze"

        # 验证命令选项
        params = {param.name: param for param in analyze_cmd.params}
        assert "mode" in params
        assert "llm" in params
        assert "wait" in params

    def test_status_command(self):
        """测试状态命令"""
        # 获取status命令
        status_cmd = cli.commands.get("status")

        # 验证status是一个命令
        assert status_cmd is not None
        assert status_cmd.name == "status"
