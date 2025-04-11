"""
SingleTaskProcessor单元测试

测试SingleTaskProcessor的核心功能和业务规则。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from acolyte.core.db.models import ProcessingMode, TaskStatus
from acolyte.core.task.processors.single import SingleLlmProcessor


class TestSingleLlmProcessor:
    """SingleLlmProcessor类的测试用例"""

    @pytest.fixture
    def processor(self):
        """创建SingleLlmProcessor实例"""
        return SingleLlmProcessor()

    @pytest.mark.asyncio
    async def test_process(self, processor):
        """测试process方法"""
        # 模拟_get_task_data方法
        task_data = {
            "id": 1,
            "content": "Test content",
            "processing_mode": ProcessingMode.SINGLE,
            "status": TaskStatus.PENDING,
        }
        processor._get_task_data = AsyncMock(return_value=task_data)

        # 模拟_update_task_status方法
        processor._update_task_status = AsyncMock(return_value=True)

        # 模拟_process_single_mode方法
        result_id = 2
        processor._process_single_mode = AsyncMock(return_value=result_id)

        # 执行测试
        result = await processor.process(1)

        # 验证结果
        assert result["success"] is True
        assert result["task_id"] == 1
        assert result["result_id"] == result_id
        assert result["final_result_id"] == result_id

        # 验证方法调用
        processor._get_task_data.assert_called_once_with(1)
        processor._update_task_status.assert_any_call(1, TaskStatus.PROCESSING)
        processor._update_task_status.assert_any_call(1, TaskStatus.COMPLETED)
        processor._process_single_mode.assert_called_once_with(1, task_data)

    @pytest.mark.asyncio
    async def test_process_error(self, processor):
        """测试process方法处理错误的情况"""
        # 模拟_get_task_data方法抛出异常
        error = Exception("Test error")
        processor._get_task_data = AsyncMock(side_effect=error)

        # 模拟_handle_error方法
        error_result = {
            "success": False,
            "task_id": 1,
            "error": "Test error",
        }
        processor._handle_error = AsyncMock(return_value=error_result)

        # 执行测试
        result = await processor.process(1)

        # 验证结果
        assert result["success"] is False
        assert result["task_id"] == 1
        assert "Test error" in result["error"]

        # 验证方法调用
        processor._get_task_data.assert_called_once_with(1)
        processor._handle_error.assert_called_once_with(1, error)

    @pytest.mark.asyncio
    async def test_process_single_mode(self, processor):
        """测试_process_single_mode方法"""
        # 模拟数据
        task_id = 1
        task_data = {
            "id": task_id,
            "content": "Test content",
            "processing_mode": ProcessingMode.SINGLE,
        }

        # 模拟_get_default_llm方法
        llm = {
            "id": 2,
            "name": "Default LLM",
            "provider": "test",
            "model_name": "test-model",
        }
        processor._get_default_llm = AsyncMock(return_value=llm)

        # 模拟_create_llm_client方法
        mock_client = MagicMock()
        mock_client.process_content = AsyncMock(return_value={
            "raw_response": "Test response",
            "processed_result": "Test processed result",
            "bias_index": 7.5,
            "misleading_index": 6.2,
            "hidden_intent_index": 4.8,
            "credibility_score": 60.5,
        })
        processor._create_llm_client = MagicMock(return_value=mock_client)

        # 模拟_save_result方法
        result_id = 3
        processor._save_result = AsyncMock(return_value=result_id)

        # 模拟_update_task_final_result方法
        processor._update_task_final_result = AsyncMock(return_value=True)

        # 执行测试
        result = await processor._process_single_mode(task_id, task_data)

        # 验证结果
        assert result == result_id

        # 验证方法调用
        processor._get_default_llm.assert_called_once()
        processor._create_llm_client.assert_called_once_with(llm)
        mock_client.process_content.assert_called_once_with(task_data["content"])
        processor._save_result.assert_called_once()
        processor._update_task_final_result.assert_called_once_with(task_id, result_id)

    @pytest.mark.asyncio
    async def test_get_default_llm(self, processor):
        """测试_get_default_llm方法"""
        # 模拟_get_llm_by_id方法
        llm = {
            "id": 1,
            "name": "Default LLM",
            "provider": "test",
            "model_name": "test-model",
            "is_default": True,
        }
        processor._get_llm_by_id = AsyncMock(return_value=llm)

        # 模拟_get_first_llm方法
        processor._get_first_llm = AsyncMock(return_value=llm)

        # 执行测试 - 有指定的LLM ID
        result = await processor._get_default_llm(llm_id=1)

        # 验证结果
        assert result == llm

        # 验证方法调用
        processor._get_llm_by_id.assert_called_once_with(1)
        processor._get_first_llm.assert_not_called()

        # 重置模拟
        processor._get_llm_by_id.reset_mock()
        processor._get_first_llm.reset_mock()

        # 执行测试 - 没有指定的LLM ID
        result = await processor._get_default_llm()

        # 验证结果
        assert result == llm

        # 验证方法调用
        processor._get_llm_by_id.assert_not_called()
        processor._get_first_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_llm_by_id(self, processor):
        """测试_get_llm_by_id方法"""
        # 模拟run_in_session函数
        with patch("acolyte.core.task.processors.single.run_in_session") as mock_run:
            # 模拟数据
            llm_id = 1
            llm = {
                "id": llm_id,
                "name": "Test LLM",
                "provider": "test",
                "model_name": "test-model",
            }

            # 配置mock_run的返回值
            mock_run.return_value = llm

            # 执行测试
            result = await processor._get_llm_by_id(llm_id)

            # 验证结果
            assert result == llm

            # 验证mock_run被调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_first_llm(self, processor):
        """测试_get_first_llm方法"""
        # 模拟run_in_session函数
        with patch("acolyte.core.task.processors.single.run_in_session") as mock_run:
            # 模拟数据
            llm = {
                "id": 1,
                "name": "Default LLM",
                "provider": "test",
                "model_name": "test-model",
                "is_default": True,
            }

            # 配置mock_run的返回值
            mock_run.return_value = llm

            # 执行测试
            result = await processor._get_first_llm()

            # 验证结果
            assert result == llm

            # 验证mock_run被调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_final_result(self, processor):
        """测试_update_task_final_result方法"""
        # 模拟run_in_session函数
        with patch("acolyte.core.task.processors.single.run_in_session") as mock_run:
            # 模拟数据
            task_id = 1
            result_id = 2

            # 配置mock_run的返回值
            mock_run.return_value = True

            # 执行测试
            result = await processor._update_task_final_result(task_id, result_id)

            # 验证结果
            assert result is True

            # 验证mock_run被调用
            mock_run.assert_called_once()
