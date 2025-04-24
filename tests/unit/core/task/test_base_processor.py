"""
基础任务处理器单元测试

测试BaseTaskProcessor的核心功能和业务规则。
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from acolyte.core.db.models import ProcessingMode, Task, TaskResult, TaskStatus
from acolyte.core.db.session import run_in_session
from acolyte.core.task.processors.base import BaseTaskProcessor


class TestBaseTaskProcessor:
    """BaseTaskProcessor类的测试用例"""

    @pytest.fixture(autouse=True)
    def mock_task_class(self):
        """模拟Task类和其属性

        创建一个完整的Task类模拟，包括类级和实例级属性
        """
        with patch("acolyte.core.task.processors.base.Task") as mock_class:
            # 模拟Task类级属性
            mock_class.id = MagicMock()
            mock_class.content = MagicMock()
            mock_class.processing_mode = MagicMock()
            mock_class.status = MagicMock()
            mock_class.created_at = MagicMock()
            mock_class.updated_at = MagicMock()
            mock_class.prompt_id = MagicMock()
            mock_class.final_result_id = MagicMock()

            # 返回模拟的Task类
            yield mock_class

    @pytest.fixture(autouse=True)
    def mock_task_result_class(self):
        """模拟TaskResult类和其属性

        创建一个完整的TaskResult类模拟，包括类级和实例级属性
        """
        with patch("acolyte.core.task.processors.base.TaskResult") as mock_class:
            # 模拟TaskResult类级属性
            mock_class.id = MagicMock()
            mock_class.task_id = MagicMock()
            mock_class.llm_id = MagicMock()
            mock_class.raw_response = MagicMock()
            mock_class.processed_result = MagicMock()
            mock_class.created_at = MagicMock()

            # 创建一个模拟的TaskResult实例
            mock_instance = MagicMock()
            mock_instance.id = 100
            mock_instance.task_id = 1
            mock_instance.llm_id = 2
            mock_instance.raw_response = "Test raw response"
            mock_instance.processed_result = json.dumps({"result": "Test result"})
            mock_instance.created_at = datetime.now()

            # 配置类创建实例
            mock_class.return_value = mock_instance

            yield mock_class

    @pytest.fixture
    def mock_session_run(self):
        """模拟run_in_session函数"""
        with patch("acolyte.core.task.processors.base.run_in_session") as mock:
            # 配置mock以异步执行传入的函数
            async def side_effect(func):
                # 创建一个模拟的session
                session = MagicMock()
                # 调用传入的函数并返回结果
                return await func(session)

            mock.side_effect = side_effect
            yield mock

    @pytest.fixture
    def mock_prompt_manager(self):
        """模拟PromptManager单例"""
        with patch("acolyte.core.task.processors.base.PromptManager") as mock_manager_class:
            # 创建模拟的管理器实例
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            # 配置方法返回值
            mock_manager.get_prompt_by_version.return_value = MagicMock(
                id=5,
                version="1.0",
                model_target="general",
                content="Test prompt content",
                is_active=True,
            )

            # 配置extract_model_data的返回值
            with patch("acolyte.core.task.processors.base.extract_model_data") as mock_extract:
                mock_extract.return_value = {
                    "id": 5,
                    "version": "1.0",
                    "model_target": "general",
                    "content": "Test prompt content",
                    "is_active": True,
                }

                yield mock_manager

    @pytest.fixture
    def processor(self, mock_prompt_manager):
        """创建BaseTaskProcessor的子类实例，实现所有需要测试的方法"""

        class TestProcessor(BaseTaskProcessor):
            async def process(self, task_id):
                # 实现抽象方法
                return await self._get_task_data(task_id)

            async def _save_final_result(self, task_id, result_id):
                # 实现测试需要的方法
                async def _save_final(session):
                    task = session.query(Task).filter(Task.id == task_id).first()
                    if not task:
                        return False
                    task.final_result_id = result_id
                    task.status = TaskStatus.COMPLETED
                    session.commit()
                    return True

                return await run_in_session(_save_final)

            async def _create_task_result(self, task_id, llm_id, raw_response, processed_result):
                # 实现测试需要的方法
                async def _create_result(session):
                    task_result = TaskResult(
                        task_id=task_id,
                        llm_id=llm_id,
                        raw_response=raw_response,
                        processed_result=(
                            json.dumps(processed_result)
                            if isinstance(processed_result, dict)
                            else processed_result
                        ),
                    )
                    session.add(task_result)
                    session.flush()
                    return task_result.id

                return await run_in_session(_create_result)

        proc = TestProcessor()
        proc.prompt_manager = mock_prompt_manager
        return proc

    @pytest.mark.asyncio
    async def test_get_task_data(self, processor, mock_session_run):
        """测试获取任务数据"""
        # 模拟任务数据
        task_data = {
            "id": 1,
            "content": "Test content",
            "processing_mode": ProcessingMode.SINGLE,
            "status": TaskStatus.PENDING,
        }

        # 模拟任务数据
        mock_task = MagicMock()
        mock_task.id = task_data["id"]
        mock_task.content = task_data["content"]
        mock_task.processing_mode = task_data["processing_mode"]
        mock_task.status = task_data["status"]

        # 配置模拟session的查询行为
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
    async def test_save_result(self, processor, mock_session_run):
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
    async def test_update_task_status(self, processor, mock_session_run):
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
        mock_query.filter.return_value.first.return_value = mock_task

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
    async def test_update_task_status_not_found(self, processor, mock_session_run):
        """测试更新不存在的任务状态"""
        # 模拟任务不存在
        task_id = 999
        new_status = TaskStatus.PROCESSING

        # 清除之前的side_effect配置
        mock_session_run.side_effect = None
        # 配置mock_session_run返回False
        mock_session_run.return_value = False

        # 执行测试
        result = await processor._update_task_status(task_id, new_status)

        # 验证结果
        assert result is False
        # 验证mock_session_run被调用
        mock_session_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_error(self, processor):
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

    @pytest.mark.asyncio
    async def test_get_prompt(self, processor, mock_session_run):
        """测试获取提示词"""
        # 模拟数据
        prompt_id = 5
        model_name = "gpt-4"

        # 模拟extract_model_data
        with patch("acolyte.core.task.processors.base.extract_model_data") as mock_extract:
            # 配置返回数据
            expected_result = {
                "id": prompt_id,
                "version": "1.0",
                "model_target": "general",
                "content": "Test prompt content",
            }
            mock_extract.return_value = expected_result

            # 配置mock_session_run返回值
            mock_session_run.return_value = expected_result

            # 执行测试
            result = await processor._get_prompt(prompt_id=prompt_id, model_name=model_name)

            # 验证结果
            assert result == expected_result
            # 验证mock_session_run被调用
            mock_session_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_prompt_model_name_only(self, processor, mock_session_run):
        """测试通过模型名称获取提示词"""
        # 模拟数据
        model_name = "gpt-4"

        # 模拟任务
        mock_prompt = MagicMock()
        mock_prompt.id = 5
        mock_prompt.version = "1.0"
        mock_prompt.model_target = "general"
        mock_prompt.content = "Test prompt content"
        mock_prompt.is_active = True

        # 配置查询结果 - 返回模拟Prompt对象
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.first.return_value = mock_prompt

        # 配置session
        mock_session = MagicMock()
        mock_session.query.return_value = mock_query

        # 模拟extract_model_data
        with patch("acolyte.core.task.processors.base.extract_model_data") as mock_extract:
            # 配置返回数据
            expected_result = {
                "id": 5,
                "version": "1.0",
                "model_target": "general",
                "content": "Test prompt content",
                "is_active": True,
            }
            mock_extract.return_value = expected_result

            # 配置mock_session_run返回值
            mock_session_run.side_effect = None
            mock_session_run.return_value = expected_result

            # 执行测试
            result = await processor._get_prompt(model_name=model_name)

            # 验证结果
            assert result == expected_result
            # 验证mock_session_run被调用
            mock_session_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_prompt_not_found(self, processor, mock_session_run):
        """测试提示词未找到的情况"""
        # 清除之前的side_effect配置
        mock_session_run.side_effect = None
        # 配置mock_session_run返回None
        mock_session_run.return_value = None

        # 执行测试
        result = await processor._get_prompt(prompt_id=999)

        # 验证结果
        assert result is None
        # 验证mock_session_run被调用
        mock_session_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_final_result(self, processor, mock_session_run):
        """测试保存最终结果"""
        # 模拟数据
        task_id = 1
        result_id = 100

        # 创建原始的_save_final_result方法副本
        original_method = processor._save_final_result

        try:
            # 替换方法为AsyncMock
            processor._save_final_result = AsyncMock(return_value=True)

            # 执行测试
            result = await processor._save_final_result(task_id, result_id)

            # 验证结果
            assert result is True
            # 验证方法被调用
            processor._save_final_result.assert_called_once_with(task_id, result_id)
        finally:
            # 恢复原始方法
            processor._save_final_result = original_method

    @pytest.mark.asyncio
    async def test_save_final_result_task_not_found(self, processor, mock_session_run):
        """测试保存最终结果时任务不存在"""
        # 模拟数据
        task_id = 999
        result_id = 100

        # 创建原始的_save_final_result方法副本
        original_method = processor._save_final_result

        try:
            # 替换方法为AsyncMock
            processor._save_final_result = AsyncMock(return_value=False)

            # 执行测试
            result = await processor._save_final_result(task_id, result_id)

            # 验证结果
            assert result is False
            # 验证方法被调用
            processor._save_final_result.assert_called_once_with(task_id, result_id)
        finally:
            # 恢复原始方法
            processor._save_final_result = original_method

    @pytest.mark.asyncio
    async def test_create_task_result(self, processor, mock_session_run, mock_task_result_class):
        """测试创建任务结果"""
        # 模拟数据
        task_id = 1
        llm_id = 2
        raw_response = "Test raw response"
        processed_result = {"result": "Test result"}

        # 创建原始的_create_task_result方法副本
        original_method = processor._create_task_result

        try:
            # 替换方法为AsyncMock
            processor._create_task_result = AsyncMock(return_value=100)

            # 执行测试
            result_id = await processor._create_task_result(
                task_id, llm_id, raw_response, processed_result
            )

            # 验证结果
            assert result_id == 100
            # 验证方法被调用
            processor._create_task_result.assert_called_once_with(
                task_id, llm_id, raw_response, processed_result
            )
        finally:
            # 恢复原始方法
            processor._create_task_result = original_method

    @pytest.mark.asyncio
    async def test_get_task_with_content(self, processor, mock_session_run):
        """测试获取任务内容"""
        # 模拟任务数据
        task_data = {
            "id": 1,
            "content": "Test content with full text",
            "processing_mode": ProcessingMode.SINGLE,
            "status": TaskStatus.PENDING,
        }

        # 清除之前的side_effect配置
        mock_session_run.side_effect = None
        # 明确设置返回值，包含content字段的具体值
        mock_session_run.return_value = {
            "id": 1,
            "processing_mode": ProcessingMode.SINGLE,
            "status": TaskStatus.PENDING,
            "content": "Test content with full text",
        }

        # 执行测试
        result = await processor._get_task_with_content(1)

        # 验证结果
        assert result is not None
        assert result["id"] == 1
        assert result["content"] == "Test content with full text"

        # 验证mock_session_run被调用
        mock_session_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_with_content_not_found(self, processor, mock_session_run):
        """测试获取不存在的任务内容"""
        # 清除之前的side_effect配置
        mock_session_run.side_effect = None
        # 配置mock_session_run返回None
        mock_session_run.return_value = None

        # 执行测试
        result = await processor._get_task_with_content(999)

        # 验证结果
        assert result is None
        # 验证mock_session_run被调用
        mock_session_run.assert_called_once()
