"""
TaskProcessor单元测试

测试TaskProcessor的核心功能和业务规则。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from acolyte.core.db.models import ProcessingMode, TaskStatus
from acolyte.core.task.processor import TaskProcessor
from acolyte.core.task.processors.single import SingleLlmProcessor
from acolyte.core.task.processors.multiple import MultipleLlmProcessor
from acolyte.core.task.processors.review import ReviewProcessor


class TestTaskProcessor:
    """TaskProcessor类的测试用例"""

    @pytest.fixture
    def processor(self):
        """创建TaskProcessor实例"""
        return TaskProcessor()

    def test_init(self, processor):
        """测试初始化方法"""
        # 验证处理器字典是否正确创建
        assert ProcessingMode.SINGLE in processor.processors
        assert ProcessingMode.MULTIPLE in processor.processors
        assert ProcessingMode.MULTIPLE_WITH_REVIEW in processor.processors

        # 验证处理器类型
        assert isinstance(processor.processors[ProcessingMode.SINGLE], SingleLlmProcessor)
        assert isinstance(processor.processors[ProcessingMode.MULTIPLE], MultipleLlmProcessor)
        assert isinstance(
            processor.processors[ProcessingMode.MULTIPLE_WITH_REVIEW], ReviewProcessor
        )

    @pytest.mark.asyncio
    async def test_process_task_success(self, processor):
        """测试process_task方法 - 成功路径"""
        # 模拟数据
        task_id = 1
        processing_mode = ProcessingMode.SINGLE

        # 模拟_get_task_mode方法
        processor._get_task_mode = AsyncMock(return_value=processing_mode)

        # 模拟SingleLlmProcessor处理器
        mock_processor = MagicMock()
        mock_processor.process = AsyncMock(
            return_value={"success": True, "task_id": task_id, "result_id": 123}
        )

        # 替换处理器字典中的处理器
        original_processor = processor.processors[ProcessingMode.SINGLE]
        processor.processors[ProcessingMode.SINGLE] = mock_processor

        try:
            # 执行测试
            result = await processor.process_task(task_id)

            # 验证结果
            assert result["success"] is True
            assert result["task_id"] == task_id
            assert result["result_id"] == 123

            # 验证方法调用
            processor._get_task_mode.assert_called_once_with(task_id)
            mock_processor.process.assert_called_once_with(task_id)
        finally:
            # 恢复原始处理器
            processor.processors[ProcessingMode.SINGLE] = original_processor

    @pytest.mark.asyncio
    async def test_process_task_invalid_mode(self, processor):
        """测试process_task方法 - 无效处理模式"""
        # 模拟数据
        task_id = 1

        # 模拟_get_task_mode方法返回None
        processor._get_task_mode = AsyncMock(return_value=None)

        # 执行测试
        result = await processor.process_task(task_id)

        # 验证结果
        assert result["success"] is False
        assert result["task_id"] == task_id
        assert "任务不存在或模式无效" in result["error"]

        # 验证方法调用
        processor._get_task_mode.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_process_task_unsupported_mode(self, processor):
        """测试process_task方法 - 不支持的处理模式"""
        # 模拟数据
        task_id = 1
        processing_mode = "UNSUPPORTED_MODE"

        # 模拟_get_task_mode方法
        processor._get_task_mode = AsyncMock(return_value=processing_mode)

        # 执行测试
        result = await processor.process_task(task_id)

        # 验证结果
        assert result["success"] is False
        assert result["task_id"] == task_id
        assert "无效的处理模式" in result["error"]

        # 验证方法调用
        processor._get_task_mode.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_process_task_exception(self, processor):
        """测试process_task方法 - 处理异常"""
        # 模拟数据
        task_id = 1
        processing_mode = ProcessingMode.SINGLE

        # 模拟_get_task_mode方法
        processor._get_task_mode = AsyncMock(return_value=processing_mode)

        # 模拟SingleLlmProcessor处理器抛出异常
        mock_processor = MagicMock()
        error = Exception("Test error")
        mock_processor.process = AsyncMock(side_effect=error)

        # 替换处理器字典中的处理器
        original_processor = processor.processors[ProcessingMode.SINGLE]
        processor.processors[ProcessingMode.SINGLE] = mock_processor

        # 模拟SingleLlmProcessor用于更新状态
        mock_status_processor = MagicMock()
        mock_status_processor._update_task_status = AsyncMock()

        try:
            # 使用patch替换SingleLlmProcessor
            with patch(
                "acolyte.core.task.processor.SingleLlmProcessor", return_value=mock_status_processor
            ):
                # 执行测试
                result = await processor.process_task(task_id)

                # 验证结果
                assert result["success"] is False
                assert result["task_id"] == task_id
                assert "处理任务时发生异常" in result["error"]
                assert "Test error" in result["error"]

                # 验证方法调用
                processor._get_task_mode.assert_called_once_with(task_id)
                mock_processor.process.assert_called_once_with(task_id)
                mock_status_processor._update_task_status.assert_called_once_with(
                    task_id, TaskStatus.FAILED
                )
        finally:
            # 恢复原始处理器
            processor.processors[ProcessingMode.SINGLE] = original_processor

    @pytest.mark.asyncio
    async def test_process_task_update_status_exception(self, processor):
        """测试process_task方法 - 更新状态异常"""
        # 模拟数据
        task_id = 1
        processing_mode = ProcessingMode.SINGLE

        # 模拟_get_task_mode方法
        processor._get_task_mode = AsyncMock(return_value=processing_mode)

        # 模拟SingleLlmProcessor处理器抛出异常
        mock_processor = MagicMock()
        error = Exception("Test error")
        mock_processor.process = AsyncMock(side_effect=error)

        # 替换处理器字典中的处理器
        original_processor = processor.processors[ProcessingMode.SINGLE]
        processor.processors[ProcessingMode.SINGLE] = mock_processor

        # 模拟SingleLlmProcessor用于更新状态也抛出异常
        mock_status_processor = MagicMock()
        status_error = Exception("Status update error")
        mock_status_processor._update_task_status = AsyncMock(side_effect=status_error)

        try:
            # 使用patch替换SingleLlmProcessor
            with patch(
                "acolyte.core.task.processor.SingleLlmProcessor", return_value=mock_status_processor
            ):
                # 执行测试
                result = await processor.process_task(task_id)

                # 验证结果
                assert result["success"] is False
                assert result["task_id"] == task_id
                assert "处理任务时发生异常" in result["error"]
                assert "Test error" in result["error"]

                # 验证方法调用
                processor._get_task_mode.assert_called_once_with(task_id)
                mock_processor.process.assert_called_once_with(task_id)
                mock_status_processor._update_task_status.assert_called_once_with(
                    task_id, TaskStatus.FAILED
                )
        finally:
            # 恢复原始处理器
            processor.processors[ProcessingMode.SINGLE] = original_processor

    @pytest.mark.asyncio
    async def test_get_task_mode_success(self, processor):
        """测试_get_task_mode方法 - 成功路径"""
        # 模拟数据
        task_id = 1
        processing_mode = ProcessingMode.SINGLE

        # 模拟SingleLlmProcessor
        mock_processor = MagicMock()
        mock_processor._get_task_data = AsyncMock(
            return_value={"id": task_id, "processing_mode": processing_mode}
        )

        # 使用patch替换SingleLlmProcessor
        with patch("acolyte.core.task.processor.SingleLlmProcessor", return_value=mock_processor):
            # 执行测试
            result = await processor._get_task_mode(task_id)

            # 验证结果
            assert result == processing_mode

            # 验证方法调用
            mock_processor._get_task_data.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_get_task_mode_task_not_found(self, processor):
        """测试_get_task_mode方法 - 任务不存在"""
        # 模拟数据
        task_id = 1

        # 模拟SingleLlmProcessor
        mock_processor = MagicMock()
        mock_processor._get_task_data = AsyncMock(return_value=None)

        # 使用patch替换SingleLlmProcessor
        with patch("acolyte.core.task.processor.SingleLlmProcessor", return_value=mock_processor):
            # 执行测试
            result = await processor._get_task_mode(task_id)

            # 验证结果
            assert result is None

            # 验证方法调用
            mock_processor._get_task_data.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_get_task_mode_no_mode(self, processor):
        """测试_get_task_mode方法 - 没有处理模式"""
        # 模拟数据
        task_id = 1

        # 模拟SingleLlmProcessor
        mock_processor = MagicMock()
        mock_processor._get_task_data = AsyncMock(
            return_value={
                "id": task_id,
                # 没有 processing_mode 字段
            }
        )

        # 使用patch替换SingleLlmProcessor
        with patch("acolyte.core.task.processor.SingleLlmProcessor", return_value=mock_processor):
            # 执行测试
            result = await processor._get_task_mode(task_id)

            # 验证结果
            assert result is None

            # 验证方法调用
            mock_processor._get_task_data.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_get_task_mode_invalid_mode(self, processor):
        """测试_get_task_mode方法 - 无效的处理模式值"""
        # 模拟数据
        task_id = 1

        # 模拟SingleLlmProcessor
        mock_processor = MagicMock()
        mock_processor._get_task_data = AsyncMock(
            return_value={"id": task_id, "processing_mode": "INVALID_MODE"}
        )

        # 使用patch替换SingleLlmProcessor
        with patch("acolyte.core.task.processor.SingleLlmProcessor", return_value=mock_processor):
            # 执行测试
            result = await processor._get_task_mode(task_id)

            # 验证结果
            assert result is None

            # 验证方法调用
            mock_processor._get_task_data.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_get_task_mode_exception(self, processor):
        """测试_get_task_mode方法 - 异常处理"""
        # 模拟数据
        task_id = 1

        # 模拟SingleLlmProcessor
        mock_processor = MagicMock()
        error = Exception("Test error")
        mock_processor._get_task_data = AsyncMock(side_effect=error)

        # 使用patch替换SingleLlmProcessor
        with patch("acolyte.core.task.processor.SingleLlmProcessor", return_value=mock_processor):
            # 执行测试
            result = await processor._get_task_mode(task_id)

            # 验证结果
            assert result is None

            # 验证方法调用
            mock_processor._get_task_data.assert_called_once_with(task_id)
