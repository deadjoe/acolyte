"""
LLM服务测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from acolyte.core.db.models import LlmConfig, LlmRole
from acolyte.core.services.llm_service import LlmService


class TestLlmService:
    """测试LLM服务"""

    @pytest.fixture
    def service(self):
        """创建LLM服务实例"""
        with patch("acolyte.core.services.llm_service.LlmManager") as mock_manager_class:
            # 创建模拟LLM管理器
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            
            # 设置方法返回值
            mock_manager.get_all_llms = MagicMock(return_value=[
                {
                    "id": 1,
                    "name": "Test LLM",
                    "base_url": "https://api.test.com",
                    "model_name": "test-model",
                    "role": LlmRole.NORMAL,
                    "is_default": True
                }
            ])
            
            mock_manager.get_llm = MagicMock(return_value={
                "id": 1,
                "name": "Test LLM",
                "base_url": "https://api.test.com",
                "model_name": "test-model",
                "role": LlmRole.NORMAL,
                "is_default": True
            })
            
            mock_manager.add_llm = MagicMock(return_value={
                "id": 1,
                "name": "Test LLM",
                "base_url": "https://api.test.com",
                "model_name": "test-model",
                "role": LlmRole.NORMAL,
                "is_default": True
            })
            
            mock_manager.update_llm = MagicMock(return_value={
                "id": 1,
                "name": "Updated LLM",
                "base_url": "https://api.test.com",
                "model_name": "test-model",
                "role": LlmRole.NORMAL,
                "is_default": True
            })
            
            mock_manager.delete_llm = MagicMock(return_value=True)
            
            mock_manager.set_as_default = MagicMock(return_value=True)
            
            # 创建服务实例
            service = LlmService()
            service.llm_manager = mock_manager
            
            yield service

    @pytest.mark.asyncio
    async def test_get_all_llms(self, service):
        """测试获取所有LLM配置"""
        # 模拟run_in_session
        with patch("acolyte.core.services.llm_service.run_in_session", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = service.llm_manager.get_all_llms()
            
            # 执行测试
            result = await service.get_all_llms()
            
            # 验证结果
            assert result["success"] is True
            assert len(result["llms"]) == 1
            assert result["llms"][0]["id"] == 1
            assert result["llms"][0]["name"] == "Test LLM"
            
            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_llm(self, service):
        """测试获取单个LLM配置"""
        # 模拟run_in_session
        with patch("acolyte.core.services.llm_service.run_in_session", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = service.llm_manager.get_llm()
            
            # 执行测试
            result = await service.get_llm(1)
            
            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1
            assert result["name"] == "Test LLM"
            
            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_llm(self, service):
        """测试添加LLM配置"""
        # 模拟run_in_session
        with patch("acolyte.core.services.llm_service.run_in_session", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = service.llm_manager.add_llm()
            
            # 执行测试
            llm_data = {
                "name": "Test LLM",
                "api_key": "test_key",
                "base_url": "https://api.test.com",
                "model_name": "test-model",
                "role": "NORMAL",
                "is_default": True
            }
            result = await service.add_llm(llm_data)
            
            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1
            assert result["name"] == "Test LLM"
            
            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_llm(self, service):
        """测试更新LLM配置"""
        # 模拟run_in_session
        with patch("acolyte.core.services.llm_service.run_in_session", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = service.llm_manager.update_llm()
            
            # 执行测试
            update_data = {
                "name": "Updated LLM"
            }
            result = await service.update_llm(1, update_data)
            
            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1
            assert result["name"] == "Updated LLM"
            
            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_llm(self, service):
        """测试删除LLM配置"""
        # 模拟run_in_session
        with patch("acolyte.core.services.llm_service.run_in_session", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = service.llm_manager.delete_llm()
            
            # 执行测试
            result = await service.delete_llm(1)
            
            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1
            
            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_as_default(self, service):
        """测试设置默认LLM"""
        # 模拟run_in_session
        with patch("acolyte.core.services.llm_service.run_in_session", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = service.llm_manager.set_as_default()
            
            # 执行测试
            result = await service.set_as_default(1)
            
            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1
            
            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection(self, service):
        """测试LLM连接测试"""
        # 模拟get_client_for_llm
        with patch("acolyte.core.services.llm_service.get_client_for_llm") as mock_get_client:
            # 模拟LLM客户端
            mock_client = MagicMock()
            mock_client.test_connection = AsyncMock(return_value=True)
            mock_get_client.return_value = mock_client
            
            # 模拟run_in_session
            with patch("acolyte.core.services.llm_service.run_in_session", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = service.llm_manager.get_llm()
                
                # 执行测试
                result = await service.test_connection(1)
                
                # 验证结果
                assert result["success"] is True
                assert "message" in result
                assert "elapsed_time" in result
                
                # 验证调用
                mock_run.assert_called_once()
                mock_client.test_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_nonexistent_llm(self, service):
        """测试获取不存在的LLM配置"""
        # 模拟run_in_session
        with patch("acolyte.core.services.llm_service.run_in_session", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = None
            
            # 执行测试
            result = await service.get_llm(999)
            
            # 验证结果
            assert result["success"] is False
            assert "error" in result
            
            # 验证调用
            mock_run.assert_called_once()
