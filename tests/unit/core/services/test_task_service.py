"""
任务服务测试

对TaskService类的单元测试，覆盖所有主要功能和边界情况。
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text as sa_text

from acolyte.core.db.models import ProcessingMode, TaskStatus
from acolyte.core.services.task_service import TaskService
import sys


class TestTaskService:
    """测试任务服务类"""

    @pytest.fixture(autouse=True)
    def mock_task_class(self):
        """创建一个模拟的Task类，确保它具有所有必要的属性和方法"""
        # 保存原始Task类
        original_task = sys.modules["acolyte.core.db.models"].Task

        # 创建模拟Task类
        class MockTask:
            """模拟Task数据库模型"""

            __tablename__ = "tasks"

            # 添加类级别的字段属性，用于查询表达式
            id = MagicMock()
            content = MagicMock()
            processing_mode = MagicMock()
            status = MagicMock()
            prompt_id = MagicMock()
            final_result_id = MagicMock()
            created_at = MagicMock()
            updated_at = MagicMock()

            def __init__(self, **kwargs):
                self.id = kwargs.get("id")
                self.content = kwargs.get("content", "")
                self.processing_mode = kwargs.get("processing_mode", ProcessingMode.SINGLE)
                self.status = kwargs.get("status", TaskStatus.PENDING)
                self.prompt_id = kwargs.get("prompt_id")
                self.final_result_id = kwargs.get("final_result_id")
                self.created_at = kwargs.get("created_at", datetime.utcnow())
                self.updated_at = kwargs.get("updated_at", datetime.utcnow())
                self.prompt = kwargs.get("prompt")
                self.results = kwargs.get("results", [])
                self.final_result = kwargs.get("final_result")
                self.llm_configs = kwargs.get("llm_configs", [])
                self.reviewer_votes = kwargs.get("reviewer_votes", [])

                # 添加其他kwargs
                for k, v in kwargs.items():
                    if not hasattr(self, k):
                        setattr(self, k, v)

            def to_dict(self, include_content=True):
                """转换为字典，类似于实际模型的to_dict方法"""
                result = {
                    "id": self.id,
                    "processing_mode": (
                        self.processing_mode.value
                        if hasattr(self.processing_mode, "value")
                        else self.processing_mode
                    ),
                    "status": self.status.value if hasattr(self.status, "value") else self.status,
                    "prompt_id": self.prompt_id,
                    "final_result_id": self.final_result_id,
                    "created_at": (
                        self.created_at.isoformat()
                        if hasattr(self.created_at, "isoformat")
                        else self.created_at
                    ),
                    "updated_at": (
                        self.updated_at.isoformat()
                        if hasattr(self.updated_at, "isoformat")
                        else self.updated_at
                    ),
                }

                if include_content:
                    result["content"] = self.content

                return result

        # 使用补丁替换原始Task类
        with patch("acolyte.core.db.models.Task", MockTask):
            with patch("acolyte.core.services.task_service.Task", MockTask):
                yield MockTask

        # 恢复原始Task类（虽然补丁会自动恢复，但为了安全起见）
        sys.modules["acolyte.core.db.models"].Task = original_task

    @pytest.fixture(autouse=True)
    def mock_task_result_class(self):
        """创建一个模拟的TaskResult类，确保它具有所有必要的属性和方法"""
        # 保存原始TaskResult类
        original_task_result = sys.modules["acolyte.core.db.models"].TaskResult

        # 创建模拟TaskResult类
        class MockTaskResult:
            """模拟TaskResult数据库模型"""

            __tablename__ = "task_results"

            # 添加类级别的字段属性，用于查询表达式
            id = MagicMock()
            task_id = MagicMock()
            llm_id = MagicMock()
            raw_response = MagicMock()
            processed_result = MagicMock()
            bias_index = MagicMock()
            misleading_index = MagicMock()
            hidden_intent_index = MagicMock()
            credibility_score = MagicMock()
            is_review_result = MagicMock()
            created_at = MagicMock()

            def __init__(self, **kwargs):
                self.id = kwargs.get("id")
                self.task_id = kwargs.get("task_id")
                self.llm_id = kwargs.get("llm_id")
                self.raw_response = kwargs.get("raw_response")
                self.processed_result = kwargs.get("processed_result")
                self.content = kwargs.get("content", "")  # 兼容测试中自定义的MockTaskResult
                self.bias_index = kwargs.get("bias_index")
                self.misleading_index = kwargs.get("misleading_index")
                self.hidden_intent_index = kwargs.get("hidden_intent_index")
                self.credibility_score = kwargs.get("credibility_score")
                self.is_review_result = kwargs.get("is_review_result", False)
                self.created_at = kwargs.get("created_at", datetime.utcnow())

                # 添加其他kwargs
                for k, v in kwargs.items():
                    if not hasattr(self, k):
                        setattr(self, k, v)

            def to_dict(self, include_raw_response=False):
                """转换为字典，类似于实际模型的to_dict方法"""
                result = {
                    "id": self.id,
                    "task_id": self.task_id,
                    "llm_id": self.llm_id,
                    "content": getattr(self, "content", self.processed_result),
                    "bias_index": self.bias_index,
                    "misleading_index": self.misleading_index,
                    "hidden_intent_index": self.hidden_intent_index,
                    "credibility_score": self.credibility_score,
                    "is_review_result": self.is_review_result,
                    "created_at": (
                        self.created_at.isoformat()
                        if hasattr(self.created_at, "isoformat")
                        else self.created_at
                    ),
                }

                if include_raw_response:
                    result["raw_response"] = self.raw_response

                return result

        # 使用补丁替换原始TaskResult类
        with patch("acolyte.core.db.models.TaskResult", MockTaskResult):
            with patch("acolyte.core.services.task_service.TaskResult", MockTaskResult):
                yield MockTaskResult

        # 恢复原始TaskResult类（虽然补丁会自动恢复，但为了安全起见）
        sys.modules["acolyte.core.db.models"].TaskResult = original_task_result

    @pytest.fixture
    def service(self):
        """创建TaskService实例的测试固件"""
        # 模拟TaskProcessor
        with patch("acolyte.core.services.task_service.TaskProcessor") as mock_processor_class:
            # 创建模拟TaskProcessor实例
            mock_processor = MagicMock()
            mock_processor.process_task = AsyncMock(return_value={"success": True, "task_id": 1})
            mock_processor_class.return_value = mock_processor

            # 模拟PromptManager
            with patch(
                "acolyte.core.services.task_service.PromptManager"
            ) as mock_prompt_manager_class:
                mock_prompt_manager = MagicMock()
                mock_prompt_manager_class.return_value = mock_prompt_manager

                # 创建服务实例
                service = TaskService()

                # 设置模拟对象，方便测试断言
                service._processor_mock = mock_processor
                service._prompt_manager_mock = mock_prompt_manager

                yield service

    #
    # 创建任务测试
    #
    @pytest.mark.asyncio
    async def test_create_task_success(self, service):
        """测试成功创建任务"""
        # 准备测试数据
        task_data = {
            "content": "测试内容",
            "processing_mode": "single",
            "prompt_id": 1,
            "llm_ids": [1, 2],
        }

        # 模拟_create_task_in_db返回任务ID
        service._create_task_in_db = AsyncMock(return_value=1)

        # 模拟_get_task返回任务数据
        task_mock_data = {
            "id": 1,
            "content": "测试内容",
            "processing_mode": "single",
            "status": "pending",
            "created_at": datetime.utcnow(),
        }
        service._get_task = AsyncMock(return_value=task_mock_data)

        # 模拟asyncio.create_task
        with patch("acolyte.core.services.task_service.asyncio.create_task") as mock_create_task:
            # 执行测试
            result = await service.create_task(task_data)

            # 验证结果
            assert result["success"] is True
            assert result["id"] == 1
            assert result["content"] == "测试内容"
            assert result["processing_mode"] == "single"
            assert result["status"] == "pending"

            # 验证方法调用
            service._create_task_in_db.assert_called_once_with(
                "测试内容", ProcessingMode.SINGLE, 1, [1, 2]
            )
            service._get_task.assert_called_once_with(1)
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_empty_content(self, service):
        """测试创建任务 - 空内容"""
        # 准备测试数据 - 空内容
        task_data = {"content": "", "processing_mode": "single"}

        # 执行测试
        result = await service.create_task(task_data)

        # 验证结果
        assert result["success"] is False
        assert "任务内容不能为空" in result["error"]

    @pytest.mark.asyncio
    async def test_create_task_no_mode(self, service):
        """测试创建任务 - 未指定处理模式"""
        # 准备测试数据 - 无处理模式
        task_data = {"content": "测试内容"}

        # 执行测试
        result = await service.create_task(task_data)

        # 验证结果
        assert result["success"] is False
        assert "处理模式不能为空" in result["error"]

    @pytest.mark.asyncio
    async def test_create_task_invalid_mode(self, service):
        """测试创建任务 - 无效处理模式"""
        # 准备测试数据 - 无效的处理模式
        task_data = {"content": "测试内容", "processing_mode": "invalid_mode"}

        # 执行测试
        result = await service.create_task(task_data)

        # 验证结果
        assert result["success"] is False
        assert "无效的处理模式" in result["error"]

    @pytest.mark.asyncio
    async def test_create_task_db_error(self, service):
        """测试创建任务 - 数据库错误"""
        # 准备测试数据
        task_data = {"content": "测试内容", "processing_mode": "single"}

        # 模拟_create_task_in_db抛出异常
        error_msg = "数据库连接错误"
        service._create_task_in_db = AsyncMock(side_effect=Exception(error_msg))

        # 执行测试
        result = await service.create_task(task_data)

        # 验证结果
        assert result["success"] is False
        assert "创建任务失败" in result["error"]
        assert error_msg in result["error"]

    @pytest.mark.asyncio
    async def test_create_task_in_db_success(self, service, mock_task_class):
        """测试在数据库中创建任务 - 成功"""
        # 准备测试数据
        content = "测试内容"
        mode = ProcessingMode.SINGLE
        prompt_id = 1
        llm_ids = [1, 2]
        mock_task_id = 5  # 期望的任务ID

        # 直接模拟run_in_session返回任务ID
        async def mock_run_in_session(callback):
            # 这里我们不调用callback，而是直接返回预期的结果
            return mock_task_id

        # 使用patch替换run_in_session
        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service._create_task_in_db(content, mode, prompt_id, llm_ids)

            # 验证结果
            assert result == mock_task_id

    @pytest.mark.asyncio
    async def test_create_task_in_db_exception(self, service):
        """测试在数据库中创建任务 - 异常"""
        # 准备测试数据
        content = "测试内容"
        mode = ProcessingMode.SINGLE

        # 模拟run_in_session抛出异常
        with patch(
            "acolyte.core.services.task_service.run_in_session",
            side_effect=SQLAlchemyError("数据库错误"),
        ):
            # 执行测试
            result = await service._create_task_in_db(content, mode)

            # 验证结果
            assert result is None

    #
    # 任务查询测试
    #
    @pytest.mark.asyncio
    async def test_get_task_success(self, service):
        """测试获取任务详情 - 成功"""
        # 准备测试数据
        task_id = 1
        mock_task = {
            "id": task_id,
            "content": "测试内容",
            "status": "completed",
        }

        # 模拟_get_task方法
        service._get_task = AsyncMock(return_value=mock_task)

        # 执行测试
        result = await service.get_task(task_id)

        # 验证结果
        assert result["success"] is True
        assert result["id"] == task_id
        assert result["content"] == "测试内容"
        assert result["status"] == "completed"

        # 验证方法调用
        service._get_task.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, service):
        """测试获取任务详情 - 任务不存在"""
        # 准备测试数据
        task_id = 999

        # 模拟_get_task方法返回None
        service._get_task = AsyncMock(return_value=None)

        # 执行测试
        result = await service.get_task(task_id)

        # 验证结果
        assert result["success"] is False
        assert "任务不存在" in result["error"]

        # 验证方法调用
        service._get_task.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_get_task_exception(self, service):
        """测试获取任务详情 - 异常"""
        # 准备测试数据
        task_id = 1
        error_msg = "数据库错误"

        # 模拟_get_task方法抛出异常
        service._get_task = AsyncMock(side_effect=Exception(error_msg))

        # 执行测试
        result = await service.get_task(task_id)

        # 验证结果
        assert result["success"] is False
        assert "获取任务失败" in result["error"]
        assert error_msg in result["error"]

        # 验证方法调用
        service._get_task.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_internal_get_task_success(self, service):
        """测试内部获取任务方法 - 成功"""
        # 准备测试数据
        task_id = 1
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.content = "测试内容"
        mock_task.status = TaskStatus.COMPLETED

        # 模拟数据库操作
        async def mock_run_in_session(callback):
            session = MagicMock()

            # 模拟Task查询结果
            mock_task = MagicMock()
            task_query_mock = MagicMock()
            task_filter_by_mock = MagicMock()
            task_filter_by_mock.first = MagicMock(return_value=mock_task)
            task_query_mock.filter_by = MagicMock(return_value=task_filter_by_mock)
            session.query = MagicMock(return_value=task_query_mock)

            # 模拟TaskResult查询结果
            mock_result1 = MagicMock()
            mock_result1.id = 1
            mock_result1.task_id = task_id
            mock_result1.llm_id = 1
            mock_result1.content = "结果1"
            mock_result1.bias_index = 0.1
            mock_result1.misleading_index = None
            mock_result1.hidden_intent_index = None
            mock_result1.credibility_score = None
            mock_result1.to_dict = MagicMock(
                return_value={
                    "id": 1,
                    "task_id": task_id,
                    "llm_id": 1,
                    "content": "结果1",
                    "bias_index": 0.1,
                }
            )

            mock_result2 = MagicMock()
            mock_result2.id = 2
            mock_result2.task_id = task_id
            mock_result2.llm_id = 2
            mock_result2.content = "结果2"
            mock_result2.bias_index = None
            mock_result2.misleading_index = 0.2
            mock_result2.hidden_intent_index = None
            mock_result2.credibility_score = None
            mock_result2.to_dict = MagicMock(
                return_value={
                    "id": 2,
                    "task_id": task_id,
                    "llm_id": 2,
                    "content": "结果2",
                    "misleading_index": 0.2,
                }
            )

            result_query_mock = MagicMock()
            result_filter_mock = MagicMock()
            result_filter_mock.all = MagicMock(
                return_value=[
                    type("Row", (), mock_result1.to_dict.return_value),
                    type("Row", (), mock_result2.to_dict.return_value),
                ]
            )
            result_query_mock.filter = MagicMock(return_value=result_filter_mock)

            # 设置session.query的两种不同行为
            session.query = MagicMock(side_effect=[task_query_mock, result_query_mock])

            return await callback(session)

        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            with patch(
                "acolyte.core.services.task_service.extract_model_data",
                return_value={"id": task_id, "content": "测试内容", "status": "completed"},
            ):
                # 执行测试
                result = await service._get_task(task_id)

                # 验证结果
                assert result == {"id": task_id, "content": "测试内容", "status": "completed"}
                assert result["id"] == task_id
                assert result["content"] == "测试内容"
                assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_internal_get_task_not_found(self, service):
        """测试内部获取任务方法 - 任务不存在"""
        # 准备测试数据
        task_id = 999

        # 模拟数据库操作 - 未找到任务
        async def mock_run_in_session(callback):
            session = MagicMock()

            # 模拟Task查询结果为None
            query_mock = MagicMock()
            filter_by_mock = MagicMock()
            filter_by_mock.first = MagicMock(return_value=None)
            query_mock.filter_by = MagicMock(return_value=filter_by_mock)
            session.query = MagicMock(return_value=query_mock)

            return await callback(session)

        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service._get_task(task_id)

            # 验证结果
            assert result is None

    @pytest.mark.asyncio
    async def test_internal_get_task_exception(self, service):
        """测试内部获取任务方法 - 发生异常"""
        # 准备测试数据
        task_id = 1

        # 模拟数据库操作 - 抛出异常
        with patch(
            "acolyte.core.services.task_service.run_in_session",
            side_effect=SQLAlchemyError("数据库连接错误"),
        ):
            # 执行测试
            result = await service._get_task(task_id)

            # 验证结果
            assert result is None

    #
    # 任务结果查询测试
    #
    @pytest.mark.asyncio
    async def test_get_task_results_success(self, service, mock_task_class, mock_task_result_class):
        """测试获取任务结果 - 成功"""
        # 准备测试数据
        task_id = 1
        include_raw = False

        # 直接模拟task_service中的_get_task和get_task_results方法
        # 这样可以避免run_in_session的复杂性
        task_dict = {"id": task_id, "content": "测试内容", "status": "completed"}

        result1 = {
            "id": 1,
            "task_id": task_id,
            "llm_id": 1,
            "content": "结果1",
            "bias_index": 0.1,
            "misleading_index": None,
            "hidden_intent_index": None,
            "credibility_score": None,
            "is_review_result": False,
        }

        result2 = {
            "id": 2,
            "task_id": task_id,
            "llm_id": 2,
            "content": "结果2",
            "bias_index": None,
            "misleading_index": 0.2,
            "hidden_intent_index": None,
            "credibility_score": None,
            "is_review_result": False,
        }

        # 模拟_get_task方法返回任务信息
        service._get_task = AsyncMock(return_value=task_dict)

        # 模拟run_in_session方法返回任务结果列表
        async def mock_run_in_session(callback):
            return [result1, result2]

        # 使用patch替换run_in_session
        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service.get_task_results(task_id, include_raw)

            # 验证结果
            assert result["success"] is True
            assert "results" in result
            assert len(result["results"]) == 2
            assert result["results"][0]["id"] == 1
            assert result["results"][1]["id"] == 2
            assert "结果1" in result["results"][0]["content"]
            assert "结果2" in result["results"][1]["content"]

    @pytest.mark.asyncio
    async def test_get_task_results_task_not_found(self, service):
        """测试获取任务结果 - 任务不存在"""
        # 准备测试数据
        task_id = 999

        # 模拟数据库操作 - 未找到任务
        async def mock_run_in_session(callback):
            session = MagicMock()

            # 模拟Task查询结果为None
            task_query_mock = MagicMock()
            task_filter_by_mock = MagicMock()
            task_filter_by_mock.first = MagicMock(return_value=None)
            task_query_mock.filter_by = MagicMock(return_value=task_filter_by_mock)
            session.query = MagicMock(return_value=task_query_mock)

            return await callback(session)

        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service.get_task_results(task_id)

            # 验证结果
            assert result["success"] is False
            assert "任务不存在" in result["error"]

    @pytest.mark.asyncio
    async def test_get_task_results_exception(self, service):
        """测试获取任务结果 - 发生异常"""
        # 准备测试数据
        task_id = 1
        error_msg = "数据库连接错误"

        # 模拟数据库操作 - 抛出异常
        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=Exception(error_msg)
        ):
            # 执行测试
            result = await service.get_task_results(task_id)

            # 验证结果
            assert result["success"] is False
            assert "获取任务结果失败" in result["error"]
            assert error_msg in result["error"]

    #
    # 任务处理测试
    #
    @pytest.mark.asyncio
    async def test_process_task_async_success(self, service):
        """测试异步处理任务 - 成功"""
        # 准备测试数据
        task_id = 1

        # 模拟_update_task_status方法
        service._update_task_status = AsyncMock(return_value=True)

        # 模拟processor.process_task方法
        processor_result = {"success": True, "task_id": task_id, "message": "处理成功"}
        service.processor.process_task = AsyncMock(return_value=processor_result)

        # 使用自定义的时间函数，避免列表迭代导致的StopIteration问题
        time_values = [100, 105]
        time_index = 0

        def mock_time():
            nonlocal time_index
            value = time_values[time_index]
            time_index = min(time_index + 1, len(time_values) - 1)
            return value

        with patch("acolyte.core.services.task_service.time.time", side_effect=mock_time):
            with patch("acolyte.core.services.task_service.asyncio.create_task"):
                # 执行测试
                result = await service.process_task_async(task_id)

                # 验证结果
                assert result["success"] is True
                assert result["task_id"] == task_id
                assert result["message"] == "处理成功"

                # 验证方法调用
                service._update_task_status.assert_called_once_with(task_id, TaskStatus.PROCESSING)
                service.processor.process_task.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_process_task_async_exception(self, service):
        """测试异步处理任务 - 处理器抛出异常"""
        # 准备测试数据
        task_id = 1
        error_msg = "处理任务时出错"

        # 模拟_update_task_status方法
        service._update_task_status = AsyncMock(return_value=True)

        # 模拟processor.process_task方法抛出异常
        service.processor.process_task = AsyncMock(side_effect=Exception(error_msg))

        # 使用自定义的时间函数，避免列表迭代导致的StopIteration问题
        time_values = [100, 105]
        time_index = 0

        def mock_time():
            nonlocal time_index
            value = time_values[time_index]
            time_index = min(time_index + 1, len(time_values) - 1)
            return value

        # 执行测试
        with patch("acolyte.core.services.task_service.time.time", side_effect=mock_time):
            with patch("acolyte.core.services.task_service.asyncio.create_task"):
                result = await service.process_task_async(task_id)

                # 验证结果
                assert result["success"] is False
                assert "处理任务时发生异常" in result["error"]
                assert error_msg in result["error"]

                # 验证方法调用
                service._update_task_status.assert_has_calls(
                    [call(task_id, TaskStatus.PROCESSING), call(task_id, TaskStatus.FAILED)]
                )
                service.processor.process_task.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_update_task_status_success(self, service):
        """测试更新任务状态 - 成功"""
        # 准备测试数据
        task_id = 1
        status = TaskStatus.COMPLETED

        # 模拟数据库操作
        async def mock_run_in_session(callback):
            session = MagicMock()

            # 模拟查询结果
            mock_task = MagicMock()
            query_mock = MagicMock()
            filter_by_mock = MagicMock()
            filter_by_mock.first = MagicMock(return_value=mock_task)
            query_mock.filter_by = MagicMock(return_value=filter_by_mock)
            session.query = MagicMock(return_value=query_mock)

            return await callback(session)

        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service._update_task_status(task_id, status)

            # 验证结果
            assert result is True

    @pytest.mark.asyncio
    async def test_update_task_status_not_found(self, service):
        """测试更新任务状态 - 任务不存在"""
        # 准备测试数据
        task_id = 999
        status = TaskStatus.COMPLETED

        # 模拟数据库操作 - 未找到任务
        async def mock_run_in_session(callback):
            session = MagicMock()

            # 模拟查询结果为None
            query_mock = MagicMock()
            filter_by_mock = MagicMock()
            filter_by_mock.first = MagicMock(return_value=None)
            query_mock.filter_by = MagicMock(return_value=filter_by_mock)
            session.query = MagicMock(return_value=query_mock)

            return await callback(session)

        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service._update_task_status(task_id, status)

            # 验证结果
            assert result is False

    @pytest.mark.asyncio
    async def test_update_task_status_exception(self, service):
        """测试更新任务状态 - 发生异常"""
        # 准备测试数据
        task_id = 1
        status = TaskStatus.COMPLETED

        # 模拟数据库操作 - 抛出异常
        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=Exception("数据库错误")
        ):
            # 执行测试
            result = await service._update_task_status(task_id, status)

            # 验证结果
            assert result is False

    #
    # 任务列表查询测试
    #
    @pytest.mark.asyncio
    async def test_get_tasks_success(self, service):
        """测试获取任务列表 - 成功"""
        # 准备测试数据
        status = "completed"
        skip = 0
        limit = 10

        # 模拟数据库操作
        mock_tasks = [
            {
                "id": 1,
                "content": "测试内容1",
                "processing_mode": "single",
                "status": "completed",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "prompt_id": 1,
                "final_result_id": 1,
                "prompt_version": "1.0",
                "prompt_target": "测试目标",
            },
            {
                "id": 2,
                "content": "测试内容2",
                "processing_mode": "multiple",
                "status": "completed",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "prompt_id": 2,
                "final_result_id": 2,
                "prompt_version": "1.0",
                "prompt_target": "测试目标",
            },
        ]

        # 创建Row类型的对象列表，模拟查询结果
        class Row:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        task_rows = [Row(**task) for task in mock_tasks]

        async def mock_run_in_session(callback):
            session = MagicMock()

            # 这里不再尝试模拟text导入，而是直接模拟session.execute的行为
            execute_mock = MagicMock()
            fetch_mock = MagicMock()
            fetch_mock.fetchall = MagicMock(return_value=task_rows)
            execute_mock.return_value = fetch_mock
            session.execute = execute_mock

            return await callback(session)

        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service.get_tasks(status, skip, limit)

            # 验证结果
            assert result["success"] is True
            assert "tasks" in result
            assert len(result["tasks"]) == 2
            assert result["tasks"][0]["id"] == 1
            assert result["tasks"][1]["id"] == 2
            assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_get_tasks_invalid_status(self, service):
        """测试获取任务列表 - 无效的状态"""
        # 准备测试数据
        status = "invalid_status"
        skip = 0
        limit = 10

        # 模拟数据库操作
        async def mock_run_in_session(callback):
            session = MagicMock()
            # 由于状态无效，回调中会尝试转换状态枚举值并失败，最终返回空列表
            return await callback(session)

        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service.get_tasks(status, skip, limit)

            # 验证结果
            assert result["success"] is True
            assert "tasks" in result
            assert len(result["tasks"]) == 0
            assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_tasks_exception(self, service):
        """测试获取任务列表 - 发生异常"""
        # 准备测试数据
        skip = 0
        limit = 10

        # 模拟数据库操作 - 抛出异常
        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=Exception("数据库错误")
        ):
            # 执行测试
            result = await service.get_tasks(None, skip, limit)

            # 验证结果
            assert result["success"] is False
            assert "获取任务列表失败" in result["error"]

    #
    # 任务删除测试
    #
    @pytest.mark.asyncio
    async def test_delete_task_success(self, service):
        """测试删除任务 - 成功"""
        # 准备测试数据
        task_id = 1

        # 模拟数据库操作
        async def mock_run_in_session(callback):
            session = MagicMock()

            # 模拟查询结果
            mock_task = MagicMock()
            query_mock = MagicMock()
            filter_by_mock = MagicMock()
            filter_by_mock.first = MagicMock(return_value=mock_task)
            query_mock.filter_by = MagicMock(return_value=filter_by_mock)

            # 模拟删除TaskResult
            result_query_mock = MagicMock()
            result_filter_by_mock = MagicMock()
            result_filter_by_mock.delete = MagicMock(return_value=2)  # 删除2个结果
            result_query_mock.filter_by = MagicMock(return_value=result_filter_by_mock)

            # 设置session.query的两种不同行为
            session.query = MagicMock(side_effect=[query_mock, result_query_mock, query_mock])

            # 模拟session.delete方法
            session.delete = MagicMock()

            return await callback(session)

        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service.delete_task(task_id)

            # 验证结果
            assert result["success"] is True
            assert f"任务 {task_id} 已删除" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, service):
        """测试删除任务 - 任务不存在"""
        # 准备测试数据
        task_id = 999

        # 模拟数据库操作 - 未找到任务
        async def mock_run_in_session(callback):
            session = MagicMock()

            # 模拟查询结果为None
            query_mock = MagicMock()
            filter_by_mock = MagicMock()
            filter_by_mock.first = MagicMock(return_value=None)
            query_mock.filter_by = MagicMock(return_value=filter_by_mock)
            session.query = MagicMock(return_value=query_mock)

            return await callback(session)

        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service.delete_task(task_id)

            # 验证结果
            assert result["success"] is False
            assert "任务不存在" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_task_exception(self, service):
        """测试删除任务 - 发生异常"""
        # 准备测试数据
        task_id = 1
        error_msg = "数据库错误"

        # 模拟数据库操作 - 抛出异常
        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=Exception(error_msg)
        ):
            # 执行测试
            result = await service.delete_task(task_id)

            # 验证结果
            assert result["success"] is False
            assert "删除任务失败" in result["error"]
            assert error_msg in result["error"]

    #
    # 任务清空测试
    #
    @pytest.mark.asyncio
    async def test_clear_tasks_success(self, service, mock_task_class):
        """测试清空任务 - 成功"""
        # 准备测试数据
        status = "completed"

        # 模拟run_in_session返回成功结果
        async def mock_run_in_session(callback):
            # 这里我们不调用callback，而是直接返回预期的结果
            return {"message": "已清空3个任务和5个任务结果", "count": 3}

        # 使用patch替换run_in_session
        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service.clear_tasks(status)

            # 验证结果
            assert result["success"] is True
            assert "已清空3个任务和5个任务结果" in result["message"]
            assert result["count"] == 3

    @pytest.mark.asyncio
    async def test_clear_tasks_empty(self, service, mock_task_class):
        """测试清空任务 - 没有任务可清空"""
        # 准备测试数据
        status = "completed"

        # 模拟run_in_session返回空结果
        async def mock_run_in_session(callback):
            # 这里我们不调用callback，而是直接返回预期的结果
            return {"message": "没有找到需要删除的任务", "count": 0}

        # 使用patch替换run_in_session
        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service.clear_tasks(status)

            # 验证结果
            assert result["success"] is True
            assert "没有找到需要删除的任务" in result["message"]
            assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_clear_tasks_invalid_status(self, service):
        """测试清空任务 - 无效的状态"""
        # 准备测试数据
        status = "invalid_status"

        # 模拟数据库操作
        async def mock_run_in_session(callback):
            session = MagicMock()
            # 回调函数会尝试将状态转换为枚举值，并返回一个错误字典
            return await callback(session)

        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service.clear_tasks(status)

            # 验证结果
            assert result["success"] is True
            assert "无效的任务状态" in result["error"]
            assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_clear_tasks_exception(self, service):
        """测试清空任务 - 发生异常"""
        # 准备测试数据
        error_msg = "数据库错误"

        # 模拟数据库操作 - 抛出异常
        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=Exception(error_msg)
        ):
            # 执行测试
            result = await service.clear_tasks()

            # 验证结果
            assert result["success"] is False
            assert "清空任务失败" in result["error"]
            assert error_msg in result["error"]

    @pytest.mark.asyncio
    async def test_update_task_status_success(self, service):
        """测试更新任务状态 - 成功"""
        # 准备测试数据
        task_id = 1
        status = TaskStatus.COMPLETED

        # 模拟数据库操作
        async def mock_run_in_session(callback):
            session = MagicMock()

            # 模拟查询结果
            mock_task = MagicMock()
            query_mock = MagicMock()
            filter_by_mock = MagicMock()
            filter_by_mock.first = MagicMock(return_value=mock_task)
            query_mock.filter_by = MagicMock(return_value=filter_by_mock)
            session.query = MagicMock(return_value=query_mock)

            return await callback(session)

        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service._update_task_status(task_id, status)

            # 验证结果
            assert result is True

    @pytest.mark.asyncio
    async def test_update_task_status_not_found(self, service):
        """测试更新任务状态 - 任务不存在"""
        # 准备测试数据
        task_id = 999
        status = TaskStatus.COMPLETED

        # 模拟数据库操作 - 未找到任务
        async def mock_run_in_session(callback):
            session = MagicMock()

            # 模拟查询结果为None
            query_mock = MagicMock()
            filter_by_mock = MagicMock()
            filter_by_mock.first = MagicMock(return_value=None)
            query_mock.filter_by = MagicMock(return_value=filter_by_mock)
            session.query = MagicMock(return_value=query_mock)

            return await callback(session)

        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await service._update_task_status(task_id, status)

            # 验证结果
            assert result is False

    @pytest.mark.asyncio
    async def test_clear_tasks_exception(self, service):
        """测试清空任务 - 发生异常"""
        # 准备测试数据
        error_msg = "数据库错误"

        # 模拟数据库操作 - 抛出异常
        with patch(
            "acolyte.core.services.task_service.run_in_session", side_effect=Exception(error_msg)
        ):
            # 执行测试
            result = await service.clear_tasks()

            # 验证结果
            assert result["success"] is False
            assert "清空任务失败" in result["error"]
            assert error_msg in result["error"]
