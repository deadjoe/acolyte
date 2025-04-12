"""
任务服务测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from acolyte.core.db.models import ProcessingMode, Task, TaskStatus
from acolyte.core.services.task_service import TaskService


class TestTaskService:
    """测试任务服务"""

    @pytest.fixture
    def service(self):
        """创建任务服务实例"""
        with patch("acolyte.core.services.task_service.TaskProcessor") as mock_processor_class:
            # 创建模拟任务处理器
            mock_processor = MagicMock()
            mock_processor_class.return_value = mock_processor
            
            # 设置方法返回值
            mock_processor.process = AsyncMock(return_value=True)
            
            # 创建服务实例
            service = TaskService()
            service.task_processor = mock_processor
            
            yield service

    @pytest.mark.asyncio
    async def test_create_task(self, service):
        """测试创建任务"""
        # 模拟run_in_session
        with patch("acolyte.core.services.task_service.run_in_session", new_callable=AsyncMock) as mock_run:
            # 模拟创建的任务
            mock_task = MagicMock()
            mock_task.id = 1
            mock_task.content = "Test content"
            mock_task.processing_mode = ProcessingMode.SINGLE
            mock_task.status = TaskStatus.PENDING
            
            mock_run.return_value = mock_task
            
            # 执行测试
            task_data = {
                "content": "Test content",
                "processing_mode": "SINGLE",
                "llm_ids": [1]
            }
            result = await service.create_task(task_data)
            
            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1
            assert result["content"] == "Test content"
            assert result["processing_mode"] == "single"
            assert result["status"] == "pending"
            
            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tasks(self, service):
        """测试获取任务列表"""
        # 模拟run_in_session
        with patch("acolyte.core.services.task_service.run_in_session", new_callable=AsyncMock) as mock_run:
            # 模拟任务列表
            mock_task = MagicMock()
            mock_task.id = 1
            mock_task.content = "Test content"
            mock_task.processing_mode = ProcessingMode.SINGLE
            mock_task.status = TaskStatus.COMPLETED
            
            mock_run.return_value = [mock_task]
            
            # 执行测试
            result = await service.get_tasks()
            
            # 验证结果
            assert result["success"] is True
            assert len(result["tasks"]) == 1
            assert result["tasks"][0]["id"] == 1
            assert result["tasks"][0]["content"] == "Test content"
            
            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task(self, service):
        """测试获取单个任务"""
        # 模拟run_in_session
        with patch("acolyte.core.services.task_service.run_in_session", new_callable=AsyncMock) as mock_run:
            # 模拟任务
            mock_task = MagicMock()
            mock_task.id = 1
            mock_task.content = "Test content"
            mock_task.processing_mode = ProcessingMode.SINGLE
            mock_task.status = TaskStatus.COMPLETED
            
            mock_run.return_value = mock_task
            
            # 执行测试
            result = await service.get_task(1)
            
            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1
            assert result["content"] == "Test content"
            assert result["status"] == "completed"
            
            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_results(self, service):
        """测试获取任务结果"""
        # 模拟run_in_session
        with patch("acolyte.core.services.task_service.run_in_session", new_callable=AsyncMock) as mock_run:
            # 模拟任务结果
            mock_result = MagicMock()
            mock_result.id = 1
            mock_result.task_id = 1
            mock_result.llm_id = 1
            mock_result.bias_index = 5.0
            mock_result.misleading_index = 3.0
            mock_result.hidden_intent_index = 2.0
            mock_result.credibility_score = 80.0
            mock_result.is_review_result = False
            
            mock_run.return_value = [mock_result]
            
            # 执行测试
            result = await service.get_task_results(1)
            
            # 验证结果
            assert result["success"] is True
            assert len(result["results"]) == 1
            assert result["results"][0]["task_id"] == 1
            assert result["results"][0]["llm_id"] == 1
            assert result["results"][0]["bias_index"] == 5.0
            
            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_task(self, service):
        """测试处理任务"""
        # 模拟run_in_session
        with patch("acolyte.core.services.task_service.run_in_session", new_callable=AsyncMock) as mock_run:
            # 模拟任务
            mock_task = MagicMock()
            mock_task.id = 1
            mock_task.content = "Test content"
            mock_task.processing_mode = ProcessingMode.SINGLE
            mock_task.status = TaskStatus.PENDING
            
            mock_run.return_value = mock_task
            
            # 执行测试
            result = await service.process_task(1)
            
            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1
            assert result["status"] == "pending"
            
            # 验证调用
            mock_run.assert_called_once()
            service.task_processor.process.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_task(self, service):
        """测试删除任务"""
        # 模拟run_in_session
        with patch("acolyte.core.services.task_service.run_in_session", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = True
            
            # 执行测试
            result = await service.delete_task(1)
            
            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1
            
            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, service):
        """测试获取不存在的任务"""
        # 模拟run_in_session
        with patch("acolyte.core.services.task_service.run_in_session", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = None
            
            # 执行测试
            result = await service.get_task(999)
            
            # 验证结果
            assert result["success"] is False
            assert "error" in result
            
            # 验证调用
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_completed_task(self, service):
        """测试处理已完成的任务"""
        # 模拟run_in_session
        with patch("acolyte.core.services.task_service.run_in_session", new_callable=AsyncMock) as mock_run:
            # 模拟任务
            mock_task = MagicMock()
            mock_task.id = 1
            mock_task.content = "Test content"
            mock_task.processing_mode = ProcessingMode.SINGLE
            mock_task.status = TaskStatus.COMPLETED
            
            mock_run.return_value = mock_task
            
            # 模拟处理器抛出异常
            service.task_processor.process = AsyncMock(side_effect=ValueError("任务已完成，无法再次处理"))
            
            # 执行测试
            result = await service.process_task(1)
            
            # 验证结果
            assert result["success"] is False
            assert "error" in result
            
            # 验证调用
            mock_run.assert_called_once()
            service.task_processor.process.assert_called_once_with(1)
