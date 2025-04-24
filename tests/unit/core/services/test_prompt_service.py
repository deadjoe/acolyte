"""
提示词服务测试
"""

from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from acolyte.core.services.prompt_service import PromptService


class TestPromptService:
    """测试提示词服务"""

    @pytest.fixture(autouse=True)
    def mock_prompt_class(self):
        """模拟Prompt类和其属性

        创建一个完整的Prompt类模拟，包括类属性和实例属性
        """
        with patch("acolyte.core.services.prompt_service.Prompt") as mock_prompt_class:
            # 模拟Prompt类的属性
            mock_prompt_class.id = MagicMock()
            mock_prompt_class.version = MagicMock()
            mock_prompt_class.model_target = MagicMock()
            mock_prompt_class.content = MagicMock()
            mock_prompt_class.description = MagicMock()
            mock_prompt_class.is_active = MagicMock()
            mock_prompt_class.file_path = MagicMock()

            # 创建一个模拟的Prompt实例
            mock_prompt_instance = MagicMock()
            mock_prompt_instance.id = 1
            mock_prompt_instance.version = "1.0"
            mock_prompt_instance.model_target = "general"
            mock_prompt_instance.content = "Test prompt content"
            mock_prompt_instance.description = "Test description"
            mock_prompt_instance.is_active = True
            mock_prompt_instance.file_path = "/path/to/prompt.md"
            mock_prompt_instance.to_dict.return_value = {
                "id": 1,
                "version": "1.0",
                "model_target": "general",
                "content": "Test prompt content",
                "description": "Test description",
                "is_active": True,
                "file_path": "/path/to/prompt.md",
            }

            # 配置类方法返回模拟实例
            mock_prompt_class.return_value = mock_prompt_instance

            yield mock_prompt_class

    @pytest.fixture
    def service(self, mock_prompt_class):
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

            # 添加sync_prompt_files_to_db方法的模拟
            mock_manager.sync_prompt_files_to_db = MagicMock(return_value=True)

            # 添加prompt_dir属性
            mock_manager.prompt_dir = "/fake/path/prompt"

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

    @pytest.mark.asyncio
    async def test_sync_prompts_success(self, service):
        """测试成功同步提示词"""
        # 模拟run_in_session
        with patch(
            "acolyte.core.services.prompt_service.run_in_session", new_callable=AsyncMock
        ) as mock_run:
            # 模拟同步后的提示词数量
            mock_run.return_value = 5

            # 执行测试
            result = await service.sync_prompts()

            # 验证结果
            assert result["success"] is True
            assert result["count"] == 5
            assert "message" in result

            # 验证模拟方法被调用
            service.prompt_manager.sync_prompt_files_to_db.assert_called_once()
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_prompts_with_custom_dir(self, service):
        """测试使用自定义目录同步提示词"""
        # 模拟run_in_session
        with patch(
            "acolyte.core.services.prompt_service.run_in_session", new_callable=AsyncMock
        ) as mock_run:
            # 模拟同步后的提示词数量
            mock_run.return_value = 3

            # 保存原始prompt_dir值
            original_dir = service.prompt_manager.prompt_dir
            custom_dir = "/custom/prompt/dir"

            # 执行测试
            result = await service.sync_prompts(prompt_dir=custom_dir)

            # 验证结果
            assert result["success"] is True
            assert result["count"] == 3

            # 验证prompt_dir被临时更改然后还原
            assert service.prompt_manager.prompt_dir == original_dir

            # 验证模拟方法被调用
            service.prompt_manager.sync_prompt_files_to_db.assert_called_once()
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_prompts_failure(self, service):
        """测试同步提示词失败"""
        # 修改sync_prompt_files_to_db返回值为False
        service.prompt_manager.sync_prompt_files_to_db.return_value = False

        # 执行测试
        result = await service.sync_prompts()

        # 验证结果
        assert result["success"] is False
        assert "error" in result

        # 验证模拟方法被调用
        service.prompt_manager.sync_prompt_files_to_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_prompts_exception(self, service):
        """测试同步提示词发生异常"""
        # 模拟sync_prompt_files_to_db抛出异常
        service.prompt_manager.sync_prompt_files_to_db.side_effect = Exception("测试异常")

        # 执行测试
        result = await service.sync_prompts()

        # 验证结果
        assert result["success"] is False
        assert "error" in result
        assert "测试异常" in result["error"]

        # 验证模拟方法被调用
        service.prompt_manager.sync_prompt_files_to_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_prompt_missing_fields(self, service):
        """测试创建提示词时缺少必要字段"""
        # 缺少content字段的数据
        prompt_data = {
            "version": "1.0",
            "model_target": "general",
        }

        # 执行测试
        result = await service.create_prompt(prompt_data)

        # 验证结果
        assert result["success"] is False
        assert "error" in result
        assert "缺少必要字段" in result["error"]

    @pytest.mark.asyncio
    async def test_create_prompt_with_file(self, service):
        """测试创建提示词并写入文件"""
        # 创建一个真实的临时路径
        test_file_path = "/path/to/custom_file.md"

        # 模拟prompt_data
        prompt_data = {
            "version": "1.0",
            "model_target": "general",
            "content": "Test prompt content",
            "file_path": test_file_path,
        }

        # 创建模拟的Prompt对象
        mock_prompt = MagicMock()
        mock_prompt.id = 1
        mock_prompt.version = "1.0"
        mock_prompt.model_target = "general"
        mock_prompt.content = "Test prompt content"
        mock_prompt.file_path = test_file_path
        mock_prompt.is_active = True

        # 创建模拟的Session
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # 使用一个实际执行内部函数的run_in_session模拟
        async def mock_run_session(func):
            # 实际执行_create_prompt函数，但使用我们控制的session
            try:
                result = await func(mock_session)
                # 模拟成功的结果
                return {
                    "id": mock_prompt.id,
                    "version": mock_prompt.version,
                    "model_target": mock_prompt.model_target,
                    "content": mock_prompt.content,
                    "file_path": mock_prompt.file_path,
                    "is_active": mock_prompt.is_active,
                }
            except Exception as e:
                print(f"执行过程中出错: {str(e)}")
                return None

        # 修改测试结构，确保正确的导入路径和mock
        with (
            patch(
                "acolyte.core.services.prompt_service.run_in_session", side_effect=mock_run_session
            ),
            patch("acolyte.core.services.prompt_service.os.path.dirname") as mock_dirname,
            patch("acolyte.core.services.prompt_service.os.makedirs") as mock_makedirs,
            patch("acolyte.core.services.prompt_service.open", new_callable=mock_open) as mock_file,
            patch(
                "acolyte.core.services.prompt_service.extract_model_data", return_value=mock_prompt
            ),
        ):

            # 设置mock
            mock_dirname.return_value = "/path/to"

            # 执行测试
            result = await service.create_prompt(prompt_data)

            # 验证结果
            assert result["success"] is True
            assert "id" in result

            # 验证函数调用
            mock_dirname.assert_called_once_with(test_file_path)
            mock_makedirs.assert_called_once_with("/path/to", exist_ok=True)

    @pytest.mark.asyncio
    async def test_create_prompt_existing(self, service):
        """测试创建已存在的提示词"""
        # 模拟run_in_session返回None (表示已存在)
        with patch(
            "acolyte.core.services.prompt_service.run_in_session", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = None

            # 执行测试
            prompt_data = {
                "version": "1.0",
                "model_target": "general",
                "content": "Test prompt content",
            }
            result = await service.create_prompt(prompt_data)

            # 验证结果
            assert result["success"] is False
            assert "error" in result
            assert "已存在" in result["error"]

    @pytest.mark.asyncio
    async def test_set_active_status_success(self, service):
        """测试成功设置提示词活跃状态"""
        # 模拟run_in_session
        with patch(
            "acolyte.core.services.prompt_service.run_in_session", new_callable=AsyncMock
        ) as mock_run:
            # 模拟返回的提示词
            mock_run.return_value = {
                "id": 1,
                "version": "1.0",
                "model_target": "general",
                "is_active": False,
            }

            # 执行测试
            result = await service.set_active_status(1, False)

            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1
            assert result["is_active"] is False

            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_active_status_nonexistent(self, service):
        """测试设置不存在的提示词活跃状态"""
        # 模拟run_in_session
        with patch(
            "acolyte.core.services.prompt_service.run_in_session", new_callable=AsyncMock
        ) as mock_run:
            # 模拟返回None (提示词不存在)
            mock_run.return_value = None

            # 执行测试
            result = await service.set_active_status(999, True)

            # 验证结果
            assert result["success"] is False
            assert "error" in result
            assert "不存在" in result["error"]

            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_prompt_nonexistent(self, service):
        """测试更新不存在的提示词"""
        # 模拟run_in_session
        with patch(
            "acolyte.core.services.prompt_service.run_in_session", new_callable=AsyncMock
        ) as mock_run:
            # 模拟返回None (提示词不存在)
            mock_run.return_value = None

            # 执行测试
            result = await service.update_prompt(999, {"version": "2.0"})

            # 验证结果
            assert result["success"] is False
            assert "error" in result
            assert "不存在" in result["error"]

            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_prompt_exception(self, service):
        """测试更新提示词时发生异常"""
        # 模拟run_in_session抛出异常
        with patch(
            "acolyte.core.services.prompt_service.run_in_session", new_callable=AsyncMock
        ) as mock_run:
            mock_run.side_effect = Exception("测试异常")

            # 执行测试
            result = await service.update_prompt(1, {"version": "2.0"})

            # 验证结果
            assert result["success"] is False
            assert "error" in result
            assert "测试异常" in result["error"]
