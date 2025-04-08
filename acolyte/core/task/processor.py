"""
任务处理主模块

提供任务处理的入口点，使用策略模式选择具体的处理器。
"""

import time
import traceback
from typing import Dict, Optional

from acolyte.core.db.models import ProcessingMode, TaskStatus
from acolyte.core.task.processors.multiple import MultipleLlmProcessor
from acolyte.core.task.processors.review import ReviewProcessor
from acolyte.core.task.processors.single import SingleLlmProcessor
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class TaskProcessor:
    """
    任务处理器

    使用策略模式选择适合的处理器处理任务。
    """

    def __init__(self):
        """初始化任务处理器"""
        # 创建处理器
        self.processors = {
            ProcessingMode.SINGLE: SingleLlmProcessor(),
            ProcessingMode.MULTIPLE: MultipleLlmProcessor(),
            ProcessingMode.MULTIPLE_WITH_REVIEW: ReviewProcessor(),
        }

    async def process_task(self, task_id: int) -> Dict:
        """
        处理任务

        Args:
            task_id: 任务ID

        Returns:
            处理结果字典
        """
        logger.info(f"开始处理任务: ID={task_id}")
        start_time = time.time()

        try:
            # 获取处理模式
            processing_mode = await self._get_task_mode(task_id)
            if not processing_mode:
                return {"success": False, "error": "任务不存在或模式无效", "task_id": task_id}

            # 获取对应的处理器
            processor = self.processors.get(processing_mode)
            if not processor:
                logger.error(f"无效的处理模式: {processing_mode}")
                return {
                    "success": False,
                    "error": f"无效的处理模式: {processing_mode}",
                    "task_id": task_id,
                }

            # 使用处理器处理任务
            result = await processor.process(task_id)

            # 记录执行时间
            elapsed_time = time.time() - start_time
            if result.get("success", False):
                logger.info(
                    f"任务处理成功: ID={task_id}, 模式={processing_mode}, 耗时={elapsed_time:.2f}秒"
                )
            else:
                logger.error(
                    f"任务处理失败: ID={task_id}, 模式={processing_mode}, 耗时={elapsed_time:.2f}秒, 错误: {result.get('error', '未知错误')}"
                )

            # 返回结果
            return result

        except Exception as e:
            # 处理所有未捕获的异常
            elapsed_time = time.time() - start_time
            error_msg = str(e)
            logger.error(
                f"任务处理异常: ID={task_id}, 耗时={elapsed_time:.2f}秒, 错误: {error_msg}"
            )
            logger.debug(f"异常详情: {traceback.format_exc()}")

            # 更新任务状态为失败
            try:
                processor = SingleLlmProcessor()  # 使用基础处理器来更新状态
                await processor._update_task_status(task_id, TaskStatus.FAILED)
            except Exception as status_error:
                logger.error(f"更新任务状态失败: {str(status_error)}")

            return {
                "success": False,
                "error": f"处理任务时发生异常: {error_msg}",
                "task_id": task_id,
            }

    async def _get_task_mode(self, task_id: int) -> Optional[ProcessingMode]:
        """
        获取任务处理模式

        Args:
            task_id: 任务ID

        Returns:
            处理模式枚举，如果任务不存在则返回None
        """
        try:
            # 使用单LLM处理器的方法获取任务数据
            processor = SingleLlmProcessor()
            task_data = await processor._get_task_data(task_id)
            if not task_data:
                logger.warning(f"任务不存在: ID={task_id}")
                return None

            # 获取处理模式
            mode_str = task_data.get("processing_mode")
            if not mode_str:
                logger.warning(f"任务没有处理模式: ID={task_id}")
                return None

            try:
                # 转换为枚举
                if isinstance(mode_str, str):
                    return ProcessingMode(mode_str)
                return mode_str
            except ValueError:
                logger.error(f"无效的处理模式值: {mode_str}")
                return None

        except Exception as e:
            logger.error(f"获取任务处理模式失败: ID={task_id}, 错误: {str(e)}", exc_info=True)
            return None
