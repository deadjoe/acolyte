"""
异步工具函数测试

对async_utils模块中定义的异步相关工具函数和类进行单元测试。
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

import pytest

from acolyte.core.utils.async_utils import (
    AsyncTaskManager,
    gather_with_concurrency,
    run_in_executor,
    run_sync_in_async,
    task_manager,
    to_async,
)


class TestRunInExecutor:
    """测试run_in_executor函数"""

    def test_run_sync_function(self):
        """测试在线程池中运行同步函数"""

        # 创建一个模拟的同步函数
        def mock_sync_func(a, b, c=3):
            return a + b + c

        # 执行测试
        result = run_in_executor(mock_sync_func, 1, 2, c=5)

        # 验证结果
        assert result == 8  # 1 + 2 + 5

    def test_run_function_with_exception(self):
        """测试在线程池中运行抛出异常的函数"""

        # 创建一个抛出异常的函数
        def mock_error_func():
            raise ValueError("测试异常")

        # 验证异常被正确传递
        with pytest.raises(ValueError, match="测试异常"):
            run_in_executor(mock_error_func)


class TestRunSyncInAsync:
    """测试run_sync_in_async函数"""

    @pytest.mark.asyncio
    async def test_run_sync_in_async_context(self):
        """测试在异步上下文中运行同步函数"""

        # 创建一个模拟的同步函数
        def mock_sync_func(a, b):
            return a * b

        # 执行测试
        result = await run_sync_in_async(mock_sync_func, 5, 7)

        # 验证结果
        assert result == 35  # 5 * 7

    @pytest.mark.asyncio
    async def test_run_sync_in_async_with_exception(self):
        """测试在异步上下文中运行抛出异常的函数"""

        # 创建一个抛出异常的函数
        def mock_error_func():
            raise RuntimeError("运行时错误")

        # 验证异常被正确传递
        with pytest.raises(RuntimeError, match="运行时错误"):
            await run_sync_in_async(mock_error_func)


class TestToAsync:
    """测试to_async装饰器"""

    def test_to_async_converts_function(self):
        """测试to_async正确转换同步函数为异步函数"""

        # 创建一个模拟的同步函数
        def mock_sync_func(x, y):
            return x + y

        # 转换为异步函数
        async_func = to_async(mock_sync_func)

        # 验证函数签名被保留
        assert async_func.__name__ == mock_sync_func.__name__
        assert "awaitable" not in mock_sync_func.__doc__ if mock_sync_func.__doc__ else True

        # 验证返回的是协程函数
        assert asyncio.iscoroutinefunction(async_func)

    @pytest.mark.asyncio
    async def test_converted_function_execution(self):
        """测试转换后的异步函数执行结果正确"""

        # 创建一个模拟的同步函数
        def mock_sync_func(x, y):
            return x - y

        # 转换为异步函数
        async_func = to_async(mock_sync_func)

        # 执行异步函数
        result = await async_func(10, 3)

        # 验证结果
        assert result == 7  # 10 - 3


class TestGatherWithConcurrency:
    """测试gather_with_concurrency函数"""

    @pytest.mark.asyncio
    async def test_gather_tasks_with_limit(self):
        """测试限制并发数的任务收集"""

        # 创建测试协程
        async def mock_task(task_id, delay):
            await asyncio.sleep(delay)
            return f"Task {task_id} completed"

        # 创建要执行的任务
        tasks = [mock_task(i, 0.1) for i in range(5)]

        # 设置并发数为3
        results = await gather_with_concurrency(3, *tasks)

        # 验证结果数量和内容
        assert len(results) == 5
        assert all(f"Task {i} completed" == results[i] for i in range(5))

    @pytest.mark.asyncio
    async def test_gather_with_exceptions_not_returned(self):
        """测试当return_exceptions=False时，异常会导致任务终止"""

        # 创建测试协程，其中一个会抛出异常
        async def success_task(task_id):
            await asyncio.sleep(0.1)
            return f"Task {task_id} completed"

        async def error_task():
            await asyncio.sleep(0.1)
            raise ValueError("Task error")

        # 创建要执行的任务
        tasks = [success_task(0), error_task(), success_task(2)]

        # 执行测试，设置return_exceptions=False
        with pytest.raises(ValueError, match="Task error"):
            await gather_with_concurrency(2, *tasks, return_exceptions=False)

    @pytest.mark.asyncio
    async def test_gather_with_exceptions_returned(self):
        """测试当return_exceptions=True时，异常会作为结果返回"""

        # 创建测试协程，其中一个会抛出异常
        async def success_task(task_id):
            await asyncio.sleep(0.1)
            return f"Task {task_id} completed"

        async def error_task():
            await asyncio.sleep(0.1)
            raise ValueError("Task error")

        # 创建要执行的任务
        tasks = [success_task(0), error_task(), success_task(2)]

        # 执行测试，设置return_exceptions=True
        results = await gather_with_concurrency(2, *tasks, return_exceptions=True)

        # 验证结果
        assert len(results) == 3
        assert results[0] == "Task 0 completed"
        assert isinstance(results[1], ValueError)
        assert str(results[1]) == "Task error"
        assert results[2] == "Task 2 completed"

    @pytest.mark.asyncio
    async def test_gather_with_timeout(self):
        """测试设置超时的效果"""

        # 创建测试协程，一个会超时
        async def fast_task():
            await asyncio.sleep(0.1)
            return "Fast task completed"

        async def slow_task():
            await asyncio.sleep(1.0)
            return "Slow task completed"

        # 创建要执行的任务
        tasks = [fast_task(), slow_task()]

        # 执行测试，设置超时时间为0.3秒
        with pytest.raises(asyncio.TimeoutError):
            await gather_with_concurrency(2, *tasks, timeout=0.3)


class TestAsyncTaskManager:
    """测试AsyncTaskManager类"""

    @pytest.fixture
    def task_manager_instance(self):
        """创建AsyncTaskManager实例的测试固件"""
        return AsyncTaskManager()

    @pytest.mark.asyncio
    async def test_add_task(self, task_manager_instance):
        """测试添加任务功能"""

        # 创建模拟协程
        async def mock_coro():
            await asyncio.sleep(0.1)
            return "Task result"

        # 添加任务
        task_id = "test_task_1"
        task_manager_instance.add_task(task_id, mock_coro())

        # 验证任务添加成功
        assert task_id in task_manager_instance.tasks
        assert task_id in task_manager_instance.callbacks
        assert task_manager_instance.callbacks[task_id] is None

    @pytest.mark.asyncio
    async def test_add_existing_task(self, task_manager_instance):
        """测试添加已存在的任务"""

        # 创建模拟协程
        async def mock_coro():
            return "Task result"

        # 先添加一次任务
        task_id = "test_task_2"
        task_manager_instance.add_task(task_id, mock_coro())

        # 获取已添加的任务对象
        original_task = task_manager_instance.tasks[task_id]

        # 尝试再次添加同ID的任务
        with patch("acolyte.core.utils.async_utils.logger") as mock_logger:
            task_manager_instance.add_task(task_id, mock_coro())

            # 验证记录了警告日志
            mock_logger.warning.assert_called_once_with(f"任务已存在: {task_id}")

        # 验证任务未被替换
        assert task_manager_instance.tasks[task_id] is original_task

    @pytest.mark.asyncio
    async def test_add_task_with_callback(self, task_manager_instance):
        """测试添加带回调的任务"""

        # 创建模拟协程和回调
        async def mock_coro():
            return "Task result with callback"

        callback_mock = Mock()

        # 添加带回调的任务
        task_id = "test_task_with_callback"
        task_manager_instance.add_task(task_id, mock_coro(), callback_mock)

        # 验证回调被正确设置
        assert task_manager_instance.callbacks[task_id] is callback_mock

    @pytest.mark.asyncio
    async def test_task_done_success(self, task_manager_instance):
        """测试任务成功完成后的回调处理"""
        # 创建模拟任务和回调
        task_id = "success_task"
        task_result = "Success result"

        task_mock = MagicMock()
        task_mock.result.return_value = task_result

        callback_mock = Mock()

        # 设置回调
        task_manager_instance.callbacks[task_id] = callback_mock

        # 调用任务完成处理
        task_manager_instance._task_done(task_mock, task_id)

        # 验证结果和回调
        assert task_manager_instance.results[task_id] == task_result
        callback_mock.assert_called_once_with(task_id, task_result)

    @pytest.mark.asyncio
    async def test_task_done_cancelled(self, task_manager_instance):
        """测试任务被取消后的处理"""
        # 创建模拟任务和回调
        task_id = "cancelled_task"

        task_mock = MagicMock()
        task_mock.result.side_effect = asyncio.CancelledError()

        callback_mock = Mock()
        task_manager_instance.callbacks[task_id] = callback_mock

        # 调用任务完成处理
        with patch("acolyte.core.utils.async_utils.logger") as mock_logger:
            task_manager_instance._task_done(task_mock, task_id)

            # 验证记录了警告日志
            mock_logger.warning.assert_called_once_with(f"异步任务已取消: {task_id}")

        # 验证结果和回调
        assert task_manager_instance.results[task_id] == {"success": False, "error": "任务已取消"}
        callback_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_task_done_exception(self, task_manager_instance):
        """测试任务执行异常后的处理"""
        # 创建模拟任务和回调
        task_id = "error_task"
        error_msg = "Task execution error"

        task_mock = MagicMock()
        task_mock.result.side_effect = ValueError(error_msg)

        callback_mock = Mock()
        task_manager_instance.callbacks[task_id] = callback_mock

        # 调用任务完成处理
        with patch("acolyte.core.utils.async_utils.logger") as mock_logger:
            task_manager_instance._task_done(task_mock, task_id)

            # 验证记录了错误日志
            mock_logger.error.assert_called_once()

        # 验证结果和回调
        assert task_manager_instance.results[task_id] == {"success": False, "error": error_msg}
        callback_mock.assert_called_once_with(task_id, {"success": False, "error": error_msg})

    @pytest.mark.asyncio
    async def test_task_done_callback_exception(self, task_manager_instance):
        """测试当回调函数抛出异常时的处理"""
        # 创建模拟任务和抛出异常的回调
        task_id = "callback_error_task"

        task_mock = MagicMock()
        task_mock.result.return_value = "Callback will error"

        callback_error = ValueError("Callback exception")
        callback_mock = Mock(side_effect=callback_error)
        task_manager_instance.callbacks[task_id] = callback_mock

        # 调用任务完成处理
        with patch("acolyte.core.utils.async_utils.logger") as mock_logger:
            task_manager_instance._task_done(task_mock, task_id)

            # 验证记录了错误日志
            mock_logger.error.assert_called_once_with(
                f"任务回调执行失败: {task_id}, 错误: {str(callback_error)}", exc_info=True
            )

    @pytest.mark.asyncio
    async def test_error_task_callback_exception(self, task_manager_instance):
        """测试当任务出错且错误回调抛出异常时的处理"""
        # 创建模拟任务和抛出异常的回调
        task_id = "error_task_callback_error"
        task_error = ValueError("Task error")
        callback_error = RuntimeError("Error callback exception")

        task_mock = MagicMock()
        task_mock.result.side_effect = task_error

        callback_mock = Mock(side_effect=callback_error)
        task_manager_instance.callbacks[task_id] = callback_mock

        # 调用任务完成处理
        with patch("acolyte.core.utils.async_utils.logger") as mock_logger:
            task_manager_instance._task_done(task_mock, task_id)

            # 验证记录了错误日志，应有两次调用
            assert mock_logger.error.call_count == 2
            mock_logger.error.assert_has_calls(
                [
                    call(f"异步任务执行失败: {task_id}, 错误: {str(task_error)}", exc_info=True),
                    call(
                        f"任务错误回调执行失败: {task_id}, 错误: {str(callback_error)}",
                        exc_info=True,
                    ),
                ]
            )

    def test_cancel_task_success(self, task_manager_instance):
        """测试成功取消任务"""
        # 创建模拟任务
        task_id = "task_to_cancel"
        task_mock = MagicMock()
        task_mock.done.return_value = False

        # 添加任务到管理器
        task_manager_instance.tasks[task_id] = task_mock

        # 执行取消操作
        with patch("acolyte.core.utils.async_utils.logger") as mock_logger:
            result = task_manager_instance.cancel_task(task_id)

            # 验证记录了信息日志
            mock_logger.info.assert_called_once_with(f"已取消任务: {task_id}")

        # 验证结果
        assert result is True
        task_mock.cancel.assert_called_once()

    def test_cancel_nonexistent_task(self, task_manager_instance):
        """测试取消不存在的任务"""
        # 尝试取消不存在的任务
        with patch("acolyte.core.utils.async_utils.logger") as mock_logger:
            result = task_manager_instance.cancel_task("nonexistent_task")

            # 验证记录了警告日志
            mock_logger.warning.assert_called_once_with("尝试取消不存在的任务: nonexistent_task")

        # 验证结果
        assert result is False

    def test_cancel_completed_task(self, task_manager_instance):
        """测试取消已完成的任务"""
        # 创建模拟的已完成任务
        task_id = "completed_task"
        task_mock = MagicMock()
        task_mock.done.return_value = True

        # 添加任务到管理器
        task_manager_instance.tasks[task_id] = task_mock

        # 尝试取消已完成的任务
        with patch("acolyte.core.utils.async_utils.logger") as mock_logger:
            result = task_manager_instance.cancel_task(task_id)

            # 验证记录了警告日志
            mock_logger.warning.assert_called_once_with(f"尝试取消已完成的任务: {task_id}")

        # 验证结果
        assert result is False
        task_mock.cancel.assert_not_called()

    def test_get_result(self, task_manager_instance):
        """测试获取任务结果"""
        # 准备测试数据
        task_id = "result_task"
        task_result = {"data": "task result data"}

        # 设置任务结果
        task_manager_instance.results[task_id] = task_result

        # 测试获取结果
        result = task_manager_instance.get_result(task_id)

        # 验证结果
        assert result == task_result

    def test_get_nonexistent_result(self, task_manager_instance):
        """测试获取不存在任务的结果"""
        # 测试获取不存在的任务结果
        result = task_manager_instance.get_result("nonexistent_task")

        # 验证结果
        assert result is None

    def test_is_task_done_for_completed(self, task_manager_instance):
        """测试检查已完成任务的状态"""
        # 创建模拟的已完成任务
        task_id = "done_task"
        task_mock = MagicMock()
        task_mock.done.return_value = True

        # 添加任务到管理器
        task_manager_instance.tasks[task_id] = task_mock

        # 测试检查任务状态
        is_done = task_manager_instance.is_task_done(task_id)

        # 验证结果
        assert is_done is True

    def test_is_task_done_for_running(self, task_manager_instance):
        """测试检查运行中任务的状态"""
        # 创建模拟的运行中任务
        task_id = "running_task"
        task_mock = MagicMock()
        task_mock.done.return_value = False

        # 添加任务到管理器
        task_manager_instance.tasks[task_id] = task_mock

        # 测试检查任务状态
        is_done = task_manager_instance.is_task_done(task_id)

        # 验证结果
        assert is_done is False

    def test_is_task_done_nonexistent(self, task_manager_instance):
        """测试检查不存在任务的状态"""
        # 测试检查不存在的任务状态
        is_done = task_manager_instance.is_task_done("nonexistent_task")

        # 验证结果
        assert is_done is False

    def test_clear_task(self, task_manager_instance):
        """测试清除单个任务"""
        # 创建测试数据
        task_id = "task_to_clear"
        task_mock = MagicMock()
        result_mock = {"data": "some data"}
        callback_mock = Mock()

        # 添加数据到管理器
        task_manager_instance.tasks[task_id] = task_mock
        task_manager_instance.results[task_id] = result_mock
        task_manager_instance.callbacks[task_id] = callback_mock

        # 执行清除操作
        with patch("acolyte.core.utils.async_utils.logger") as mock_logger:
            task_manager_instance.clear_task(task_id)

            # 验证记录了调试日志
            mock_logger.debug.assert_called_once_with(f"已清除任务: {task_id}")

        # 验证数据被清除
        assert task_id not in task_manager_instance.tasks
        assert task_id not in task_manager_instance.results
        assert task_id not in task_manager_instance.callbacks

    def test_clear_nonexistent_task(self, task_manager_instance):
        """测试清除不存在的任务"""
        # 执行清除操作
        with patch("acolyte.core.utils.async_utils.logger") as mock_logger:
            task_manager_instance.clear_task("nonexistent_task")

            # 验证记录了调试日志
            mock_logger.debug.assert_called_once_with("已清除任务: nonexistent_task")

    def test_clear_completed_tasks(self, task_manager_instance):
        """测试清除所有已完成的任务"""
        # 创建测试数据
        completed_tasks = ["task1", "task3"]
        running_tasks = ["task2", "task4"]

        # 添加已完成的任务
        for task_id in completed_tasks:
            task_mock = MagicMock()
            task_mock.done.return_value = True
            task_manager_instance.tasks[task_id] = task_mock
            task_manager_instance.results[task_id] = {"data": f"{task_id} result"}
            task_manager_instance.callbacks[task_id] = Mock()

        # 添加运行中的任务
        for task_id in running_tasks:
            task_mock = MagicMock()
            task_mock.done.return_value = False
            task_manager_instance.tasks[task_id] = task_mock
            task_manager_instance.callbacks[task_id] = Mock()

        # 执行清除操作
        with patch("acolyte.core.utils.async_utils.logger") as mock_logger:
            task_manager_instance.clear_completed_tasks()

            # 验证记录了信息日志
            mock_logger.info.assert_called_once_with(
                f"已清除 {len(completed_tasks)} 个已完成的任务"
            )

        # 验证已完成的任务被清除，运行中的任务保留
        for task_id in completed_tasks:
            assert task_id not in task_manager_instance.tasks
            assert task_id not in task_manager_instance.results
            assert task_id not in task_manager_instance.callbacks

        for task_id in running_tasks:
            assert task_id in task_manager_instance.tasks


class TestGlobalTaskManager:
    """测试全局任务管理器实例"""

    def test_global_task_manager_is_singleton(self):
        """测试全局任务管理器是单例"""
        # 导入两次模块，验证获取的是同一个实例
        from acolyte.core.utils.async_utils import task_manager as task_manager1
        from acolyte.core.utils.async_utils import task_manager as task_manager2

        assert task_manager1 is task_manager2
        assert task_manager1 is task_manager
