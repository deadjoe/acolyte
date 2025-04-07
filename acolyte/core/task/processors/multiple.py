"""
多LLM处理器

处理使用多个LLM的任务。
"""
import time
from typing import Dict, List

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

    使用多个LLM并行处理任务。该处理器会同时调用多个LLM对同一内容进行分析，
    并将所有结果保存到数据库。可以选择其中一个结果作为最终结果，或者将所有结果一起返回。

    该处理器使用asyncio并发执行多个LLM调用，以提高效率。它会等待所有LLM处理完成，
    然后收集结果并返回。如果某个LLM处理失败，它会记录错误但不会影响其他LLM的处理。
    """

    async def process(self, task_id: int) -> Dict:
        """
        使用多个LLM并行处理指定任务

        该方法是多LLM处理器的主要入口点。它会从数据库中获取任务信息，
        然后并行调用多个LLM对任务内容进行分析。它会等待所有LLM处理完成，
        然后收集结果并保存到数据库。如果某个LLM处理失败，它会记录错误但不会影响其他LLM的处理。

        流程：
        1. 从数据库中获取任务信息
        2. 获取指定的LLM列表
        3. 获取提示词模板
        4. 并行调用所有LLM处理任务
        5. 收集结果并保存到数据库
        6. 更新任务状态并返回结果

        Args:
            task_id: 要处理的任务的ID

        Returns:
            Dict: 包含处理结果的字典，包含以下字段：
                - success (bool): 处理是否成功
                - task_id (int): 任务ID
                - result_ids (List[int]): 结果记录ID列表
                - count (int): 结果数量
                - results (List[Dict]): 所有LLM的处理结果

        Raises:
            TaskNotFoundError: 当指定的任务不存在时抛出
            LlmConfigError: 当LLM配置有问题时抛出
            PromptNotFoundError: 当提示词模板不存在时抛出
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
        并行使用多个LLM处理内容

        该方法是多LLM并行处理的核心实现。它会为每个LLM创建一个处理协程，
        然后使用asyncio.gather并行执行这些协程。它会等待所有LLM处理完成，
        然后收集结果并返回。如果某个LLM处理失败，它会记录错误但不会影响其他LLM的处理。

        注意：该方法使用return_exceptions=True参数，因此即使某个LLM处理失败，
        也不会影响其他LLM的处理。失败的LLM处理会返回异常对象，而不是处理结果。

        Args:
            task_content: 需要分析的文本内容
            prompt_content: 用于分析的提示词模板内容
            llm_list: 要使用的LLM配置列表，每项包含标识符、名称、API密钥等信息

        Returns:
            List[tuple]: 处理结果列表，每项为(llm_id, result)元组。
            如果某个LLM处理失败，对应的result将是一个包含错误信息的字典。
        """
        # 创建处理任务列表
        coroutines = []

        for llm_data in llm_list:
            # 创建处理任务
            process_task = self._process_with_llm(
                llm_data=llm_data,
                task_content=task_content,
                prompt_content=prompt_content
            )
            coroutines.append(process_task)

        # 并行执行所有任务，最多3个并发
        logger.debug(f"开始并行执行 {len(coroutines)} 个LLM处理任务")
        results = await gather_with_concurrency(3, *coroutines, return_exceptions=True)
        logger.debug(f"完成并行执行 {len(results)} 个LLM处理任务")

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

    async def _process_with_llm(self, llm_data: Dict, task_content: str, prompt_content: str) -> Dict:
        """
        使用指定LLM处理内容并返回结果

        此方法是异步的，它会等待LLM处理完成并返回处理结果。
        它负责创建LLM客户端，发送请求，并处理响应。

        Args:
            llm_data: LLM配置数据，包含标识符、名称、API密钥等信息
            task_content: 需要分析的文本内容
            prompt_content: 用于分析的提示词模板内容

        Returns:
            Dict: LLM处理结果，包含原始响应、处理结果和成功状态

        Raises:
            Exception: 当LLM处理过程中发生错误时抛出异常
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
        从字典数据重建LlmConfig对象

        该方法将从数据库中获取的LLM配置字典转换为LlmConfig对象。
        LlmConfig对象是系统中表示LLM配置的标准对象，包含所有必要的属性，
        如ID、名称、描述、API密钥、基础URL、模型名称、提供商等。

        Args:
            llm_data: 包含LLM配置数据的字典，通常来自数据库查询结果

        Returns:
            LlmConfig: 重建LLM配置对象，可用于创建LLM客户端

        Raises:
            LlmConfigError: 当配置数据不完整或无效时抛出
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