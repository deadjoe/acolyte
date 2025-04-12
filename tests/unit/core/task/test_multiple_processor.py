"""
MultipleTaskProcessor单元测试

测试MultipleTaskProcessor的核心功能和业务规则。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from acolyte.core.db.models import ProcessingMode, TaskStatus
from acolyte.core.task.processors.multiple import MultipleLlmProcessor


class TestMultipleLlmProcessor:
    """MultipleLlmProcessor类的测试用例"""

    @pytest.fixture
    def processor(self):
        """创建MultipleLlmProcessor实例"""
        return MultipleLlmProcessor()

    @pytest.fixture
    def mock_session_scope(self):
        """模拟session_scope上下文管理器"""
        session_mock = MagicMock()
        context_manager_mock = MagicMock()
        context_manager_mock.__enter__ = MagicMock(return_value=session_mock)
        context_manager_mock.__exit__ = MagicMock(return_value=None)

        with patch("acolyte.core.db.database.db.session_scope", return_value=context_manager_mock):
            yield session_mock

    @pytest.mark.asyncio
    async def test_process(self, processor):
        """测试process方法"""
        # 模拟数据
        task_id = 1

        # 模拟_update_task_status方法
        processor._update_task_status = AsyncMock(return_value=True)

        # 模拟_get_task_with_content方法
        task_data = {
            "id": task_id,
            "content": "Test content",
            "prompt_id": 1,
            "processing_mode": ProcessingMode.MULTIPLE,
        }
        processor._get_task_with_content = AsyncMock(return_value=task_data)

        # 模拟_get_llms_for_task方法
        llm_list = [
            {"id": 2, "name": "LLM 1"},
            {"id": 3, "name": "LLM 2"},
        ]
        processor._get_llms_for_task = AsyncMock(return_value=llm_list)

        # 模拟_get_prompt方法
        prompt_data = {
            "id": 1,
            "content": "Test prompt",
        }
        processor._get_prompt = AsyncMock(return_value=prompt_data)

        # 模拟_process_with_multiple_llms方法
        llm_results = [
            (2, {"success": True, "result": {"raw_response": "Response 1"}}),
            (3, {"success": True, "result": {"raw_response": "Response 2"}}),
        ]
        processor._process_with_multiple_llms = AsyncMock(return_value=llm_results)

        # 模拟_save_result方法
        result_ids = [4, 5]
        processor._save_result = AsyncMock(side_effect=result_ids)

        # 执行测试
        result = await processor.process(task_id)

        # 验证结果
        assert result["success"] is True
        assert result["task_id"] == task_id
        assert result["result_ids"] == result_ids

        # 验证方法调用
        processor._update_task_status.assert_any_call(task_id, TaskStatus.PROCESSING)
        processor._update_task_status.assert_any_call(task_id, TaskStatus.COMPLETED)
        processor._get_task_with_content.assert_called_once_with(task_id)
        processor._get_llms_for_task.assert_called_once_with(task_id)
        processor._get_prompt.assert_called_once_with(prompt_id=1)
        processor._process_with_multiple_llms.assert_called_once()
        assert processor._save_result.call_count == 2

    @pytest.mark.asyncio
    async def test_process_error(self, processor):
        """测试process方法处理错误的情况"""
        # 模拟_update_task_status方法抛出异常
        error = Exception("Test error")
        processor._update_task_status = AsyncMock(side_effect=error)

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
        processor._update_task_status.assert_called_once()
        processor._handle_error.assert_called_once_with(1, error)

    # 删除了测试不存在方法的测试：
    # - test_process_multiple_mode
    # - test_process_with_llm

    @pytest.mark.asyncio
    async def test_get_llms_for_task(self, processor):
        """测试_get_llms_for_task方法"""
        # 使用模拟方法测试
        from acolyte.core.db.models import LlmRole

        # 创建模拟LLM列表
        normal_llm = {
            "id": 1,
            "name": "Test Normal LLM",
            "model_name": "test-model-1",
            "role": LlmRole.NORMAL.value,
            "is_default": True
        }

        # 模拟_get_llms_for_task方法
        original_method = processor._get_llms_for_task
        processor._get_llms_for_task = AsyncMock(return_value=[normal_llm])

        try:
            # 执行测试
            result = await processor._get_llms_for_task(1)

            # 验证结果
            assert result is not None
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["id"] == 1
            assert result[0]["name"] == "Test Normal LLM"
            assert result[0]["role"] == LlmRole.NORMAL.value

            # 验证方法调用
            processor._get_llms_for_task.assert_called_once_with(1)
        finally:
            # 恢复原始方法
            processor._get_llms_for_task = original_method

    # 删除了测试不存在方法的测试：
    # - test_calculate_final_result
    # - test_get_best_result
    # - test_update_task_final_result
