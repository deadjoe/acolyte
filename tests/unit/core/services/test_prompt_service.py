"""
提示词服务测试
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from acolyte.core.services.prompt_service import PromptService


class TestPromptService:
    """测试提示词服务"""

    @pytest.fixture
    def service(self):
        """创建提示词服务实例"""
        with patch("acolyte.core.services.prompt_service.PromptManager") as mock_manager_class:
            # 创建模拟提示词管理器
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            # 设置方法返回值
            mock_manager.get_all_prompts = MagicMock(
                return_value=[
                    {
                        "id": 1,
                        "version": "1.0",
                        "model_target": "general",
                        "content": "Test prompt content",
                        "is_active": True,
                    }
                ]
            )

            # 添加get_prompts方法的模拟
            mock_manager.get_prompts = MagicMock(
                return_value=[
                    {
                        "id": 1,
                        "version": "1.0",
                        "model_target": "general",
                        "content": "Test prompt content",
                        "is_active": True,
                    }
                ]
            )

            mock_manager.get_prompt = MagicMock(
                return_value={
                    "id": 1,
                    "version": "1.0",
                    "model_target": "general",
                    "content": "Test prompt content",
                    "is_active": True,
                }
            )

            # 创建服务实例
            service = PromptService()
            service.prompt_manager = mock_manager

            yield service

    @pytest.mark.asyncio
    async def test_get_all_prompts(self, service):
        """测试获取所有提示词"""
        # 模拟run_in_session
        with patch(
            "acolyte.core.services.prompt_service.run_in_session", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = service.prompt_manager.get_all_prompts()

            # 执行测试
            result = await service.get_prompts()

            # 验证结果
            assert result["success"] is True
            assert len(result["prompts"]) == 1
            assert result["prompts"][0]["id"] == 1
            assert result["prompts"][0]["version"] == "1.0"

            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_prompt(self, service):
        """测试获取单个提示词"""
        # 模拟run_in_session
        with patch(
            "acolyte.core.services.prompt_service.run_in_session", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = service.prompt_manager.get_prompt()

            # 执行测试
            result = await service.get_prompt(1)

            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1
            assert result["version"] == "1.0"
            assert result["content"] == "Test prompt content"

            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_prompt(self, service):
        """测试创建提示词"""
        # 模拟run_in_session
        with patch(
            "acolyte.core.services.prompt_service.run_in_session", new_callable=AsyncMock
        ) as mock_run:
            # 模拟创建的提示词
            mock_run.return_value = {
                "id": 1,
                "version": "1.0",
                "model_target": "general",
                "is_active": True,
                "content": "Test prompt content",
            }

            # 执行测试
            prompt_data = {
                "version": "1.0",
                "model_target": "general",
                "content": "Test prompt content",
                "is_active": True,
            }
            result = await service.create_prompt(prompt_data)

            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1
            assert result["version"] == "1.0"

            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_prompt(self, service):
        """测试更新提示词"""
        # 模拟run_in_session
        with patch(
            "acolyte.core.services.prompt_service.run_in_session", new_callable=AsyncMock
        ) as mock_run:
            # 模拟更新的提示词
            mock_run.return_value = {
                "id": 1,
                "version": "1.1",
                "model_target": "general",
                "is_active": True,
                "content": "Test prompt content",
            }

            # 执行测试
            update_data = {"version": "1.1"}
            result = await service.update_prompt(1, update_data)

            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1
            assert result["version"] == "1.1"

            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_prompt(self, service):
        """测试删除提示词"""
        # 模拟run_in_session
        with patch(
            "acolyte.core.services.prompt_service.run_in_session", new_callable=AsyncMock
        ) as mock_run:
            # 模拟返回值
            mock_run.return_value = {
                "file_path": "/path/to/prompt.md",
                "id": 1,
                "version": "1.0",
                "model_target": "general",
            }

            # 执行测试
            result = await service.delete_prompt(1)

            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1

            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_nonexistent_prompt(self, service):
        """测试获取不存在的提示词"""
        # 模拟run_in_session
        with patch(
            "acolyte.core.services.prompt_service.run_in_session", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = None

            # 执行测试
            result = await service.get_prompt(999)

            # 验证结果
            assert result["success"] is False
            assert "error" in result

            # 验证调用
            mock_run.assert_called_once()
