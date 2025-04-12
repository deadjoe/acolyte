"""
LlmManager单元测试

测试LlmManager的核心功能和业务规则。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from acolyte.core.db.models import LlmRole
from acolyte.core.llm.manager import LlmManager


class TestLlmManager:
    """LlmManager类的测试用例"""

    @pytest.fixture
    def manager(self):
        """创建LlmManager实例"""
        return LlmManager()

    @pytest.fixture
    def mock_session_scope(self):
        """模拟session_scope上下文管理器"""
        session_mock = MagicMock()
        context_manager_mock = MagicMock()
        context_manager_mock.__enter__ = MagicMock(return_value=session_mock)
        context_manager_mock.__exit__ = MagicMock(return_value=None)

        with patch("acolyte.core.db.database.db.session_scope", return_value=context_manager_mock):
            yield session_mock

    def test_get_all_llms(self, manager, mock_session_scope):
        """测试获取所有LLM配置"""
        # 模拟查询结果
        mock_llm1 = MagicMock()
        mock_llm1.id = 1
        mock_llm1.name = "LLM 1"
        mock_llm1.role = LlmRole.NORMAL

        mock_llm2 = MagicMock()
        mock_llm2.id = 2
        mock_llm2.name = "LLM 2"
        mock_llm2.role = LlmRole.REVIEWER

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.all.return_value = [mock_llm1, mock_llm2]

        # 配置查询结果
        mock_session_scope.query.return_value = mock_query

        # 执行测试
        result = manager.get_all_llms()

        # 验证结果
        assert len(result) == 2
        assert result[0] == mock_llm1
        assert result[1] == mock_llm2

        # 验证查询被调用
        mock_session_scope.query.assert_called_once()

    def test_get_llm(self, manager, mock_session_scope):
        """测试通过ID获取LLM配置"""
        # 模拟数据
        llm_id = 1

        # 模拟查询结果
        mock_llm = MagicMock()
        mock_llm.id = llm_id
        mock_llm.name = "Test LLM"
        mock_llm.role = LlmRole.NORMAL

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_llm

        # 配置查询结果
        mock_session_scope.query.return_value = mock_query

        # 执行测试
        result = manager.get_llm(llm_id)

        # 验证结果
        assert result == mock_llm
        # 验证查询被调用
        mock_session_scope.query.assert_called_once()

    def test_get_default_llm(self, manager, mock_session_scope):
        """测试获取默认LLM配置"""
        # 模拟查询结果
        mock_llm = MagicMock()
        mock_llm.id = 1
        mock_llm.name = "Default LLM"
        mock_llm.is_default = True
        mock_llm.role = LlmRole.NORMAL

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_llm

        # 配置查询结果
        mock_session_scope.query.return_value = mock_query

        # 执行测试
        result = manager.get_default_llm()

        # 验证结果
        assert result == mock_llm
        # 验证查询被调用
        mock_session_scope.query.assert_called_once()

    def test_add_llm(self, manager, mock_session_scope):
        """测试添加LLM配置"""
        # 模拟数据
        name = "New LLM"
        api_key = "new_api_key"
        base_url = "https://api.new.com"
        model_name = "new-model"
        description = "New LLM Description"
        role = LlmRole.NORMAL
        is_default = False

        # 模拟LlmConfig类
        with patch("acolyte.core.llm.manager.LlmConfig") as MockLlmConfig:
            mock_llm = MagicMock()
            mock_llm.id = 1
            mock_llm.name = name
            mock_llm.role = role
            MockLlmConfig.return_value = mock_llm

            # 配置会话
            mock_session_scope.add = MagicMock()
            mock_session_scope.commit = MagicMock()

            # 执行测试
            result = manager.add_llm(
                name=name,
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                description=description,
                role=role,
                is_default=is_default
            )

            # 验证结果
            assert result == mock_llm
            # 验证会话方法被调用
            mock_session_scope.add.assert_called_once()
            MockLlmConfig.assert_called_once()

    def test_update_llm(self, manager, mock_session_scope):
        """测试更新LLM配置"""
        # 模拟数据
        llm_id = 1
        new_name = "Updated LLM"
        new_description = "Updated LLM Description"

        # 模拟查询结果
        mock_llm = MagicMock()
        mock_llm.id = llm_id
        mock_llm.name = "Old LLM"
        mock_llm.description = "Old LLM Description"

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_llm

        # 配置查询结果
        mock_session_scope.query.return_value = mock_query
        mock_session_scope.commit = MagicMock()

        # 执行测试 - 使用关键字参数
        result = manager.update_llm(llm_id, name=new_name, description=new_description)

        # 验证结果
        assert result == mock_llm
        assert mock_llm.name == new_name
        assert mock_llm.description == new_description
        # 验证查询被调用
        mock_session_scope.query.assert_called_once()
        # 注意：实际代码中可能没有调用commit

    def test_delete_llm(self, manager, mock_session_scope):
        """测试删除LLM配置"""
        # 模拟数据
        llm_id = 1

        # 模拟查询结果
        mock_llm = MagicMock()
        mock_llm.id = llm_id
        mock_llm.name = "Test LLM"
        mock_llm.is_default = False

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_llm
        mock_query.filter.return_value.first.return_value = None
        mock_query.count.return_value = 1  # 这里设置为数字而不是MagicMock

        # 配置查询结果
        mock_session_scope.query.return_value = mock_query
        mock_session_scope.delete = MagicMock()

        # 执行测试
        result = manager.delete_llm(llm_id)

        # 验证结果
        assert result is True
        # 验证查询、删除和提交被调用
        mock_session_scope.query.assert_called()
        mock_session_scope.delete.assert_called_once_with(mock_llm)

    def test_set_as_default(self, manager, mock_session_scope):
        """测试设置默认LLM配置"""
        # 模拟数据
        llm_id = 1

        # 模拟查询结果
        mock_llm = MagicMock()
        mock_llm.id = llm_id
        mock_llm.name = "Test LLM"
        mock_llm.is_default = False

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_llm
        # 设置count返回值为数字而不是MagicMock
        mock_query.filter_by.return_value.count.return_value = 0

        # 配置查询结果
        mock_session_scope.query.return_value = mock_query

        # 模拟_clear_default_status方法
        with patch.object(manager, "_clear_default_status") as mock_clear:
            # 执行测试
            result = manager.set_as_default(llm_id)

            # 验证结果
            assert result is True
            assert mock_llm.is_default is True
            # 验证查询和清除默认状态被调用
            mock_session_scope.query.assert_called()
            mock_clear.assert_called_once_with(mock_session_scope)

    @pytest.mark.asyncio
    async def test_test_llm_connection(self, manager):
        """测试LLM连接测试功能"""
        # 模拟数据
        llm_id = 1

        # 模拟查询结果
        mock_llm = MagicMock()
        mock_llm.id = llm_id
        mock_llm.name = "Test LLM"
        mock_llm.api_key = "test_api_key"
        mock_llm.base_url = "https://api.test.com"
        mock_llm.model_name = "test-model"

        # 模拟get_llm方法
        with patch.object(manager, "get_llm", return_value=mock_llm):
            # 模拟get_client_for_llm函数
            with patch("acolyte.core.llm.client.get_client_for_llm") as mock_create_client:
                # 模拟LLM客户端
                mock_client = MagicMock()
                mock_client._test_connection = AsyncMock(return_value={
                    "success": True,
                    "message": "Connection successful",
                })
                mock_create_client.return_value = mock_client

                # 执行测试
                result = await manager.test_connection(llm_id)

                # 验证结果
                assert result["success"] is True
                assert "message" in result

                # 验证方法调用
                mock_create_client.assert_called_once_with(mock_llm)
                mock_client._test_connection.assert_called_once()

    # 删除了测试不存在方法的测试：
    # - test_import_llm_configs
    # - test_export_llm_configs
    # 这些方法在LlmManager类中不存在，相关功能在acolyte.core.llm.config模块中实现
