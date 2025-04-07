"""
多LLM处理器

处理使用多个LLM的任务。
"""
import time
from typing import Dict, List, Awaitable

from acolyte.core.db.models import LlmConfig, TaskStatus
from acolyte.core.llm.client import get_client_for_llm
from acolyte.core.task.processors.base import BaseTaskProcessor
from acolyte.core.utils.async_utils import gather_with_concurrency
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class MultipleLlmProcessor(BaseTaskProcessor):
    """
    多LLM处理器

    使用多个LLM并行处理任务。
    """

    async def process(self, task_id: int) -> Dict:
        """
        处理任务

        Args:
            task_id: 任务ID

        Returns:
            处理结果字典
        """
        logger.info(f"开始多LLM处理: 任务ID={task_id}")
        start_time = time.time()

        try:
            # 更新任务状态为处理中
            status_updated = await self._update_task_status(task_id, TaskStatus.PROCESSING)
            if not status_updated:
                return await self._handle_error(task_id, "更新任务状态失败")

            # 获取任务数据
            task_data = await self._get_task_with_content(task_id)
            if not task_data:
                return await self._handle_error(task_id, "任务不存在或内容获取失败")

            # 获取任务内容和提示词ID
            task_content = task_data.get("content")
            prompt_id = task_data.get("prompt_id")

            # 获取任务关联的LLM列表
            llm_list = await self._get_llms_for_task(task_id)
            if not llm_list:
                return await self._handle_error(task_id, "未找到有效的LLM配置")

            # 获取提示词
            prompt_data = await self._get_prompt(prompt_id=prompt_id)
            if not prompt_data:
                return await self._handle_error(task_id, "未找到有效的提示词")

            # 提取必要数据
            prompt_content = prompt_data.get("content")

            # 检查数据完整性
            if not task_content or not prompt_content:
                missing = []
                if not task_content:
                    missing.append("任务内容")
                if not prompt_content:
                    missing.append("提示词内容")

                error_msg = f"缺少必要数据: {', '.join(missing)}"
                return await self._handle_error(task_id, error_msg)

            # 并行处理所有LLM
            logger.info(f"开始并行处理 {len(llm_list)} 个LLM: 任务ID={task_id}")
            llm_results = await self._process_with_multiple_llms(
                task_content=task_content,
                prompt_content=prompt_content,
                llm_list=llm_list
            )

            # 检查结果
            if not llm_results:
                return await self._handle_error(task_id, "所有LLM处理都失败")

            # 保存结果
            result_ids = []
            for llm_id, result in llm_results:
                if result.get("success", False):
                    result_id = await self._save_result(task_id, llm_id, result)
                    if result_id:
                        result_ids.append(result_id)

            # 检查是否有成功的结果
            if not result_ids:
                return await self._handle_error(task_id, "保存结果失败")

            # 更新任务状态为已完成
            await self._update_task_status(task_id, TaskStatus.COMPLETED)

            # 统计处理时间
            elapsed_time = time.time() - start_time
            logger.info(f"多LLM处理完成: 任务ID={task_id}, 成功结果数={len(result_ids)}, 耗时={elapsed_time:.2f}秒")

            # 返回成功结果
            return {
                "success": True,
                "task_id": task_id,
                "result_ids": result_ids,
                "count": len(result_ids),
                "results": [r[1].get("result", {}) for r in llm_results if r[1].get("success", False)]
            }

        except Exception as e:
            # 处理所有未捕获的异常
            return await self._handle_error(task_id, e)

    async def _process_with_multiple_llms(
        self,
        task_content: str,
        prompt_content: str,
        llm_list: List[Dict]
    ) -> List[tuple]:
        """
        使用多个LLM处理内容

        Args:
            task_content: 任务内容
            prompt_content: 提示词内容
            llm_list: LLM配置列表

        Returns:
            处理结果列表，每项为(llm_id, result)元组
        """
        # 创建处理协程
        coroutines = []

        for llm_data in llm_list:
            # 创建协程
            coroutine = self._create_llm_coroutine(
                llm_data=llm_data,
                task_content=task_content,
                prompt_content=prompt_content
            )
            coroutines.append(coroutine)

        # 并行执行所有协程，最多3个并发
        results = await gather_with_concurrency(3, *coroutines, return_exceptions=True)

        # 处理结果
        llm_results = []
        for i, result in enumerate(results):
            llm_id = llm_list[i].get("id")

            # 处理异常
            if isinstance(result, Exception):
                logger.error(f"LLM处理异常: LLM ID={llm_id}, 错误: {str(result)}")
                llm_results.append((llm_id, {
                    "success": False,
                    "error": f"处理异常: {str(result)}",
                    "raw_response": None,
                    "result": {}
                }))
            else:
                llm_results.append((llm_id, result))

        return llm_results

    async def _create_llm_coroutine(self, llm_data: Dict, task_content: str, prompt_content: str) -> Awaitable[Dict]:
        """
        创建LLM处理协程

        Args:
            llm_data: LLM配置数据
            task_content: 任务内容
            prompt_content: 提示词内容

        Returns:
            异步协程对象
        """
        # 重建LLM配置对象
        reconstructed_llm = self._rebuild_llm_config(llm_data)

        # 获取客户端
        client = get_client_for_llm(reconstructed_llm)

        # 处理内容
        llm_id = llm_data.get("id")
        llm_name = llm_data.get("name")
        logger.info(f"开始LLM处理: LLM={llm_name} (ID={llm_id})")

        try:
            # 返回处理协程
            result = await client.process_content(content=task_content, prompt=prompt_content)
            logger.info(f"LLM处理完成: LLM={llm_name} (ID={llm_id}), 成功={result.get('success', False)}")
            return result
        except Exception as e:
            logger.error(f"LLM处理失败: LLM={llm_data.get('name')} (ID={llm_data.get('id')}), 错误: {str(e)}")
            raise

    def _rebuild_llm_config(self, llm_data: Dict) -> LlmConfig:
        """
        重建LLM配置对象

        Args:
            llm_data: LLM配置数据

        Returns:
            LLM配置对象
        """
        reconstructed_llm = LlmConfig(
            id=llm_data.get("id"),
            name=llm_data.get("name"),
            api_key=llm_data.get("api_key"),
            base_url=llm_data.get("base_url"),
            model_name=llm_data.get("model_name"),
            role=llm_data.get("role", "normal"),
            is_default=llm_data.get("is_default", False)
        )

        # 添加provider属性
        provider = llm_data.get("provider")
        if provider:
            setattr(reconstructed_llm, 'provider', provider)

        return reconstructed_llm