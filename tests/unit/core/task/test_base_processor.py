"""
基础任务处理器单元测试

测试BaseTaskProcessor的核心功能和业务规则。
"""

from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from acolyte.core.db.models import ProcessingMode, TaskStatus
from acolyte.core.task.processors.base import BaseTaskProcessor


class TestBaseTaskProcessor:
    """BaseTaskProcessor类的测试用例"""

    @pytest.fixture
    def mock_session_run(self) -> Generator[MagicMock, None, None]:
        """模拟run_in_session函数"""
        with patch("acolyte.core.task.processors.base.run_in_session") as mock:
            # 配置mock以异步执行传入的函数
            async def side_effect(func: Any) -> Any:
                # 创建一个模拟的session
                session = MagicMock()
                # 调用传入的函数并返回结果
                return await func(session)

            mock.side_effect = side_effect
            yield mock

    @pytest.fixture
    def processor(self) -> BaseTaskProcessor:
        """创建BaseTaskProcessor的子类实例"""

        class TestProcessor(BaseTaskProcessor):
            async def process(self, task_id: int) -> Any:
                # 实现抽象方法
                return await self._get_task_data(task_id)

        return TestProcessor()

    @pytest.mark.asyncio
    async def test_get_task_data(self, processor: BaseTaskProcessor, mock_session_run: MagicMock) -> None:
        """测试获取任务数据"""
        # 模拟任务数据
        task_data = {
            "id": 1,
            "content": "Test content",
            "processing_mode": ProcessingMode.SINGLE,
            "status": TaskStatus.PENDING,
        }

        # 配置模拟session的查询行为
        mock_task = MagicMock()
        mock_task.id = task_data["id"]
        mock_task.content = task_data["content"]
        mock_task.processing_mode = task_data["processing_mode"]
        mock_task.status = task_data["status"]

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_task

        # 配置session
        mock_session = MagicMock()
        mock_session.query.return_value = mock_query

        # 配置extract_model_data
        with patch("acolyte.core.task.processors.base.extract_model_data") as mock_extract:
            mock_extract.return_value = task_data

            # 配置mock_session_run的返回值
            mock_session_run.return_value = task_data

            # 执行测试
            result = await processor._get_task_data(1)

            # 验证结果
            assert result == task_data
            # 验证mock_session_run被调用
            mock_session_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_result(self, processor: BaseTaskProcessor, mock_session_run: MagicMock) -> None:
        """测试保存处理结果"""
        # 模拟数据
        task_id = 1
        llm_id = 2
        result = {
            "raw_response": "Test response",
            "processed_result": "Test processed result",
            "bias_index": 7.5,
            "misleading_index": 6.2,
            "hidden_intent_index": 4.8,
            "credibility_score": 60.5,
        }

        # 模拟任务和结果
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.final_result_id = None

        mock_task_result = MagicMock()
        mock_task_result.id = 3

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_task

        # 配置session
        mock_session = MagicMock()
        mock_session.query.return_value = mock_query

        # 配置TaskResult类
        with patch("acolyte.core.task.processors.base.TaskResult") as MockTaskResult:
            MockTaskResult.return_value = mock_task_result

            # 配置mock_session_run的返回值
            mock_session_run.return_value = mock_task_result.id

            # 执行测试
            result_id = await processor._save_result(task_id, llm_id, result)

            # 验证结果
            assert result_id == mock_task_result.id
            # 验证mock_session_run被调用
            mock_session_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_status(self, processor: BaseTaskProcessor, mock_session_run: MagicMock) -> None:
        """测试更新任务状态"""
        # 模拟任务
        task_id = 1
        old_status = TaskStatus.PENDING
        new_status = TaskStatus.PROCESSING

        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.status = old_status

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_task

        # 配置session
        mock_session = MagicMock()
        mock_session.query.return_value = mock_query

        # 配置mock_session_run的返回值
        mock_session_run.return_value = True

        # 执行测试
        result = await processor._update_task_status(task_id, new_status)

        # 验证结果
        assert result is True
        # 验证mock_session_run被调用
        mock_session_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_error(self, processor: BaseTaskProcessor) -> None:
        """测试错误处理"""
        # 模拟数据
        task_id = 1
        error = Exception("Test error")

        # 模拟_update_task_status方法
        processor._update_task_status = AsyncMock()
        processor._update_task_status.return_value = True

        # 执行测试
        result = await processor._handle_error(task_id, error)

        # 验证结果
        assert result["success"] is False
        assert "Test error" in result["error"]
        assert result["task_id"] == task_id
        processor._update_task_status.assert_called_once_with(task_id, TaskStatus.FAILED)
