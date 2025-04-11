"""
LLM配置单元测试

测试LLM配置的加载、导入和导出功能。
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from acolyte.core.llm.config import (
    export_llm_config_to_file,
    import_llm_config_from_file,
)
from acolyte.config.settings import get_config_path, load_config


class TestLlmConfig:
    """LLM配置测试用例"""

    @pytest.fixture
    def mock_config_file(self, tmp_path):
        """创建模拟的配置文件"""
        config_data = {
            "llm_configs": [
                {
                    "id": 1,
                    "name": "Test LLM",
                    "description": "Test LLM Description",
                    "api_key": "test_api_key",
                    "base_url": "https://api.test.com",
                    "model_name": "test-model",
                    "provider": "test",
                    "role": "normal",
                    "is_default": True,
                    "parameters": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                    },
                },
                {
                    "id": 2,
                    "name": "Test LLM 2",
                    "description": "Test LLM Description 2",
                    "api_key": "test_api_key_2",
                    "base_url": "https://api.test2.com",
                    "model_name": "test-model-2",
                    "provider": "test2",
                    "role": "reviewer",
                    "is_default": False,
                    "parameters": {
                        "temperature": 0.5,
                        "top_p": 0.8,
                    },
                },
            ]
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        return config_file

    def test_get_config_path(self):
        """测试获取配置文件路径"""
        # 模拟Path.home
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path("/mock/home")

            # 模拟Path.exists
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False

                # 模拟Path.mkdir
                with patch("pathlib.Path.mkdir") as mock_mkdir:
                    # 执行测试
                    result = get_config_path()

                    # 验证结果
                    assert str(result) == "/mock/home/.config/acolyte/config.json"

                    # 验证方法调用
                    mock_home.assert_called()
                    mock_exists.assert_called()
                    mock_mkdir.assert_called_once()

    def test_load_config(self, mock_config_file):
        """测试加载配置"""
        # 模拟get_config_path
        with patch("acolyte.config.settings.get_config_path") as mock_get_path:
            mock_get_path.return_value = str(mock_config_file)

            # 执行测试
            config = load_config()

            # 验证结果
            assert config is not None
            assert hasattr(config, "llm_configs")
            assert len(config.llm_configs) == 2
            assert config.llm_configs[0]["name"] == "Test LLM"
            assert config.llm_configs[1]["name"] == "Test LLM 2"

    def test_load_config_file_not_exists(self):
        """测试加载不存在的配置文件"""
        # 模拟get_config_file_path
        with patch("acolyte.core.llm.config.get_config_file_path") as mock_get_path:
            mock_get_path.return_value = "/path/to/nonexistent/config.json"

            # 模拟os.path.exists
            with patch("os.path.exists") as mock_exists:
                mock_exists.return_value = False

                # 执行测试
                config = load_config()

                # 验证结果
                assert config is not None
                assert hasattr(config, "llm_configs")
                assert len(config.llm_configs) == 0

    def test_import_llm_config_from_file(self, mock_config_file):
        """测试从文件导入LLM配置"""
        # 模拟load_config
        with patch("acolyte.core.llm.config.load_config") as mock_load_config:
            # 创建模拟的Config对象
            mock_config = MagicMock()
            mock_config.llm_configs = [
                {
                    "id": 1,
                    "name": "Test LLM",
                    "description": "Test LLM Description",
                    "api_key": "test_api_key",
                    "base_url": "https://api.test.com",
                    "model_name": "test-model",
                    "provider": "test",
                    "role": "normal",
                    "is_default": True,
                    "parameters": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                    },
                },
                {
                    "id": 2,
                    "name": "Test LLM 2",
                    "description": "Test LLM Description 2",
                    "api_key": "test_api_key_2",
                    "base_url": "https://api.test2.com",
                    "model_name": "test-model-2",
                    "provider": "test2",
                    "role": "reviewer",
                    "is_default": False,
                    "parameters": {
                        "temperature": 0.5,
                        "top_p": 0.8,
                    },
                },
            ]
            mock_load_config.return_value = mock_config

            # 执行测试 - 导入所有LLM
            result = import_llm_config_from_file()

            # 验证结果
            assert len(result) == 2
            assert result[0]["name"] == "Test LLM"
            assert result[1]["name"] == "Test LLM 2"

            # 执行测试 - 导入指定名称的LLM
            result = import_llm_config_from_file(llm_name="Test LLM")

            # 验证结果
            assert len(result) == 1
            assert result[0]["name"] == "Test LLM"

    def test_export_llm_config_to_file(self, tmp_path):
        """测试导出LLM配置到文件"""
        # 模拟数据
        llm_configs = [
            {
                "id": 1,
                "name": "Test LLM",
                "description": "Test LLM Description",
                "api_key": "test_api_key",
                "base_url": "https://api.test.com",
                "model_name": "test-model",
                "provider": "test",
                "role": "normal",
                "is_default": True,
                "parameters": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                },
            }
        ]

        # 模拟get_config_path
        config_file = tmp_path / "export_config.json"
        with patch("acolyte.config.settings.get_config_path") as mock_get_path:
            mock_get_path.return_value = str(config_file)

            # 模拟load_config
            with patch("acolyte.core.llm.config.load_config") as mock_load_config:
                # 创建模拟的Config对象
                mock_config = MagicMock()
                mock_config.llm_configs = []
                mock_load_config.return_value = mock_config

                # 执行测试
                result = export_llm_config_to_file(llm_configs)

                # 验证结果
                assert result is True
                assert os.path.exists(config_file)

                # 验证文件内容
                with open(config_file, "r") as f:
                    saved_config = json.load(f)
                    assert "llm_configs" in saved_config
                    assert len(saved_config["llm_configs"]) == 1
                    assert saved_config["llm_configs"][0]["name"] == "Test LLM"
