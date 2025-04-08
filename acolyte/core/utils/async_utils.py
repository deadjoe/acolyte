"""
异步工具

提供异步操作相关的工具函数和类，简化异步编程。
"""

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, Callable, List, Optional, TypeVar

from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)

# 定义类型变量
T = TypeVar("T")
R = TypeVar("R")


def run_in_executor(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    在线程池中运行同步函数

    将同步函数在线程池中执行，避免阻塞事件循环。

    Args:
        func: 要执行的同步函数
        args: 位置参数
        kwargs: 关键字参数

    Returns:
        函数执行结果
    """
    with ThreadPoolExecutor() as executor:
        return executor.submit(func, *args, **kwargs).result()


async def run_sync_in_async(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    在异步上下文中运行同步函数

    将同步函数在线程池中执行，作为协程返回结果。

    Args:
        func: 要执行的同步函数
        args: 位置参数
        kwargs: 关键字参数

    Returns:
        函数执行结果
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


def to_async(func: Callable[..., T]) -> Callable[..., Awaitable[T]]:
    """
    将同步函数转换为异步函数

    将同步函数转换为返回协程的异步函数。

    Args:
        func: 要转换的同步函数

    Returns:
        异步函数
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        return await run_sync_in_async(func, *args, **kwargs)

    return wrapper


async def gather_with_concurrency(
    n: int, *tasks: Awaitable[Any], return_exceptions: bool = False, timeout: Optional[float] = None
) -> List[Any]:
    """
    限制并发数的异步任务收集

    该函数是对asyncio.gather的增强包装，添加了并发限制功能。
    它确保同时运行的任务数不超过指定的并发数，从而避免资源耗尽。
    当一个任务完成时，会自动开始执行队列中的下一个任务，直到所有任务完成。

    实现原理：
    1. 使用asyncio.Semaphore控制并发数
    2. 将每个任务包装在一个使用信号量的协程中
    3. 使用asyncio.gather收集所有任务的结果
    4. 可选的超时控制可以限制所有任务的总执行时间

    Args:
        n: 最大并发数，限制同时运行的任务数量
        tasks: 要执行的异步任务列表
        return_exceptions: 当为True时，异常会作为结果返回而不是抛出；
            当为False时，第一个异常会终止所有任务
        timeout: 可选的超时时间（秒），如果指定，则所有任务必须在这个时间内完成，否则抛出超时异常

    Returns:
        List[Any]: 任务结果列表，顺序与输入任务相同

    Raises:
        asyncio.TimeoutError: 如果指定了timeout并且任务没有在指定时间内完成
            （当return_exceptions=False时）
        Exception: 如果任一任务抛出异常且return_exceptions=False

    Note:
        当使用return_exceptions=True时，返回的列表中可能包含异常对象。
        调用者应该检查每个结果是否是异常对象，例如使用isinstance(result, Exception)。
    """
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task

    if timeout is not None:
        # 使用wait_for添加超时控制
        return await asyncio.wait_for(
            asyncio.gather(
                *(sem_task(task) for task in tasks), return_exceptions=return_exceptions
            ),
            timeout=timeout,
        )
    else:
        # 无超时控制
        return await asyncio.gather(
            *(sem_task(task) for task in tasks), return_exceptions=return_exceptions
        )


class AsyncTaskManager:
    """
    异步任务管理器

    管理和监控异步任务的执行。
    """

    def __init__(self):
        """初始化异步任务管理器"""
        self.tasks = {}
        self.results = {}
        self.callbacks = {}

    def add_task(
        self,
        task_id: str,
        coro: Awaitable[Any],
        callback: Optional[Callable[[str, Any], None]] = None,
    ) -> None:
        """
        添加异步任务

        Args:
            task_id: 任务ID
            coro: 协程对象
            callback: 完成回调函数
        """
        if task_id in self.tasks:
            logger.warning(f"任务已存在: {task_id}")
            return

        # 创建任务
        task = asyncio.create_task(coro)
        self.tasks[task_id] = task
        self.callbacks[task_id] = callback

        # 添加完成回调
        task.add_done_callback(functools.partial(self._task_done, task_id=task_id))

        logger.info(f"已添加异步任务: {task_id}")

    def _task_done(self, task: asyncio.Task, task_id: str) -> None:
        """
        任务完成回调

        Args:
            task: 完成的任务
            task_id: 任务ID
        """
        try:
            result = task.result()
            self.results[task_id] = result
            logger.info(f"异步任务完成: {task_id}")

            # 调用用户回调
            callback = self.callbacks.get(task_id)
            if callback:
                try:
                    callback(task_id, result)
                except Exception as e:
                    logger.error(f"任务回调执行失败: {task_id}, 错误: {str(e)}", exc_info=True)

        except asyncio.CancelledError:
            logger.warning(f"异步任务已取消: {task_id}")
            self.results[task_id] = {"success": False, "error": "任务已取消"}

        except Exception as e:
            logger.error(f"异步任务执行失败: {task_id}, 错误: {str(e)}", exc_info=True)
            self.results[task_id] = {"success": False, "error": str(e)}

            # 调用用户回调
            callback = self.callbacks.get(task_id)
            if callback:
                try:
                    callback(task_id, {"success": False, "error": str(e)})
                except Exception as cb_error:
                    logger.error(
                        f"任务错误回调执行失败: {task_id}, 错误: {str(cb_error)}", exc_info=True
                    )

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"尝试取消不存在的任务: {task_id}")
            return False

        if task.done():
            logger.warning(f"尝试取消已完成的任务: {task_id}")
            return False

        # 取消任务
        task.cancel()
        logger.info(f"已取消任务: {task_id}")
        return True

    def get_result(self, task_id: str) -> Optional[Any]:
        """
        获取任务结果

        Args:
            task_id: 任务ID

        Returns:
            任务结果，如果任务不存在或未完成则返回None
        """
        return self.results.get(task_id)

    def is_task_done(self, task_id: str) -> bool:
        """
        检查任务是否完成

        Args:
            task_id: 任务ID

        Returns:
            任务是否完成
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        return task.done()

    def clear_task(self, task_id: str) -> None:
        """
        清除任务

        从管理器中移除任务及其结果。

        Args:
            task_id: 任务ID
        """
        self.tasks.pop(task_id, None)
        self.results.pop(task_id, None)
        self.callbacks.pop(task_id, None)
        logger.debug(f"已清除任务: {task_id}")

    def clear_completed_tasks(self) -> None:
        """清除所有已完成的任务"""
        completed_tasks = [task_id for task_id, task in self.tasks.items() if task.done()]

        for task_id in completed_tasks:
            self.clear_task(task_id)

        logger.info(f"已清除 {len(completed_tasks)} 个已完成的任务")


# 创建全局任务管理器实例
task_manager = AsyncTaskManager()
