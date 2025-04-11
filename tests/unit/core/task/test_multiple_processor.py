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
    def mock_session_run(self):
        """模拟run_in_session函数"""
        with patch("acolyte.core.task.processors.multiple.run_in_session") as mock:
            # 配置mock以异步执行传入的函数
            async def side_effect(func):
                # 创建一个模拟的session
                session = MagicMock()
                # 调用传入的函数并返回结果
                return await func(session)

            mock.side_effect = side_effect
            yield mock

    @pytest.mark.asyncio
    async def test_process(self, processor):
        """测试process方法"""
        # 模拟_get_task_data方法
        task_data = {
            "id": 1,
            "content": "Test content",
            "processing_mode": ProcessingMode.MULTIPLE,
            "status": TaskStatus.PENDING,
        }
        processor._get_task_data = AsyncMock(return_value=task_data)

        # 模拟_update_task_status方法
        processor._update_task_status = AsyncMock(return_value=True)

        # 模拟_process_multiple_mode方法
        result_ids = [2, 3, 4]
        processor._process_multiple_mode = AsyncMock(return_value=result_ids)

        # 模拟_calculate_final_result方法
        final_result_id = 5
        processor._calculate_final_result = AsyncMock(return_value=final_result_id)

        # 执行测试
        result = await processor.process(1)

        # 验证结果
        assert result["success"] is True
        assert result["task_id"] == 1
        assert result["result_ids"] == result_ids
        assert result["final_result_id"] == final_result_id

        # 验证方法调用
        processor._get_task_data.assert_called_once_with(1)
        processor._update_task_status.assert_any_call(1, TaskStatus.PROCESSING)
        processor._update_task_status.assert_any_call(1, TaskStatus.COMPLETED)
        processor._process_multiple_mode.assert_called_once_with(1, task_data)
        processor._calculate_final_result.assert_called_once_with(1, result_ids)

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
    async def test_process_multiple_mode(self, processor):
        """测试_process_multiple_mode方法"""
        # 模拟数据
        task_id = 1
        task_data = {
            "id": task_id,
            "content": "Test content",
            "processing_mode": ProcessingMode.MULTIPLE,
        }

        # 模拟_get_llms_for_task方法
        llms = [
            {"id": 2, "name": "LLM 1"},
            {"id": 3, "name": "LLM 2"},
        ]
        processor._get_llms_for_task = AsyncMock(return_value=llms)

        # 模拟_process_with_llm方法
        result_ids = [4, 5]
        processor._process_with_llm = AsyncMock(side_effect=result_ids)

        # 执行测试
        result = await processor._process_multiple_mode(task_id, task_data)

        # 验证结果
        assert result == result_ids

        # 验证方法调用
        processor._get_llms_for_task.assert_called_once_with(task_id, task_data)
        assert processor._process_with_llm.call_count == 2
        processor._process_with_llm.assert_any_call(task_id, task_data, llms[0])
        processor._process_with_llm.assert_any_call(task_id, task_data, llms[1])

    @pytest.mark.asyncio
    async def test_process_with_llm(self, processor):
        """测试_process_with_llm方法"""
        # 模拟数据
        task_id = 1
        task_data = {
            "id": task_id,
            "content": "Test content",
        }
        llm = {
            "id": 2,
            "name": "Test LLM",
            "provider": "test",
            "model_name": "test-model",
        }

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

        # 执行测试
        result = await processor._process_with_llm(task_id, task_data, llm)

        # 验证结果
        assert result == result_id

        # 验证方法调用
        processor._create_llm_client.assert_called_once_with(llm)
        mock_client.process_content.assert_called_once_with(task_data["content"])
        processor._save_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_llms_for_task(self, processor, mock_session_run):
        """测试_get_llms_for_task方法"""
        # 模拟数据
        task_id = 1
        task_data = {
            "id": task_id,
            "content": "Test content",
        }

        # 模拟查询结果
        mock_llm1 = MagicMock()
        mock_llm1.id = 2
        mock_llm1.name = "LLM 1"
        mock_llm1.role = "normal"

        mock_llm2 = MagicMock()
        mock_llm2.id = 3
        mock_llm2.name = "LLM 2"
        mock_llm2.role = "normal"

        # 模拟TaskLlm关联
        mock_task_llm1 = MagicMock()
        mock_task_llm1.llm = mock_llm1
        mock_task_llm2 = MagicMock()
        mock_task_llm2.llm = mock_llm2

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.all.return_value = [mock_task_llm1, mock_task_llm2]

        # 配置session
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value = mock_query

        # 配置extract_model_data
        with patch("acolyte.core.task.processors.multiple.extract_model_data") as mock_extract:
            mock_extract.side_effect = lambda obj, **kwargs: {
                "id": obj.id,
                "name": obj.name,
                "role": obj.role,
            }

            # 配置mock_session_run的返回值
            expected_llms = [
                {"id": 2, "name": "LLM 1", "role": "normal"},
                {"id": 3, "name": "LLM 2", "role": "normal"},
            ]
            mock_session_run.return_value = expected_llms

            # 执行测试
            result = await processor._get_llms_for_task(task_id, task_data)

            # 验证结果
            assert result == expected_llms
            # 验证mock_session_run被调用
            mock_session_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_final_result(self, processor):
        """测试_calculate_final_result方法"""
        # 模拟数据
        task_id = 1
        result_ids = [2, 3, 4]

        # 模拟_get_best_result方法
        best_result_id = 3
        processor._get_best_result = AsyncMock(return_value=best_result_id)

        # 模拟_update_task_final_result方法
        processor._update_task_final_result = AsyncMock(return_value=True)

        # 执行测试
        result = await processor._calculate_final_result(task_id, result_ids)

        # 验证结果
        assert result == best_result_id

        # 验证方法调用
        processor._get_best_result.assert_called_once_with(result_ids)
        processor._update_task_final_result.assert_called_once_with(task_id, best_result_id)

    @pytest.mark.asyncio
    async def test_get_best_result(self, processor, mock_session_run):
        """测试_get_best_result方法"""
        # 模拟数据
        result_ids = [2, 3, 4]

        # 模拟查询结果
        mock_result1 = MagicMock()
        mock_result1.id = 2
        mock_result1.credibility_score = 60.5

        mock_result2 = MagicMock()
        mock_result2.id = 3
        mock_result2.credibility_score = 75.2  # 最高分

        mock_result3 = MagicMock()
        mock_result3.id = 4
        mock_result3.credibility_score = 45.8

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.all.return_value = [mock_result1, mock_result2, mock_result3]

        # 配置session
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value = mock_query

        # 配置mock_session_run的返回值
        mock_session_run.return_value = 3  # 返回最高分结果的ID

        # 执行测试
        result = await processor._get_best_result(result_ids)

        # 验证结果
        assert result == 3
        # 验证mock_session_run被调用
        mock_session_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_final_result(self, processor, mock_session_run):
        """测试_update_task_final_result方法"""
        # 模拟数据
        task_id = 1
        result_id = 2

        # 模拟查询结果
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.final_result_id = None

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_task

        # 配置session
        mock_session = MagicMock()
        mock_session.query.return_value = mock_query

        # 配置mock_session_run的返回值
        mock_session_run.return_value = True

        # 执行测试
        result = await processor._update_task_final_result(task_id, result_id)

        # 验证结果
        assert result is True
        # 验证mock_session_run被调用
        mock_session_run.assert_called_once()
