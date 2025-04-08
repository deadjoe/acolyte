"""
评议处理器

处理使用多个LLM并进行评议的任务。
"""

import asyncio
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from acolyte.core.db.models import LlmConfig, ReviewerVote, Task, TaskResult, TaskStatus
from acolyte.core.db.session import run_in_session
from acolyte.core.llm.client import get_client_for_llm
from acolyte.core.task.processors.base import BaseTaskProcessor
from acolyte.core.task.processors.multiple import MultipleLlmProcessor
from acolyte.core.utils.async_utils import gather_with_concurrency
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class ReviewProcessor(BaseTaskProcessor):
    """
    评议处理器

    该处理器用于处理需要多个LLM协作评议的任务。它是一种高级的任务处理器，
    结合了MultipleLlmProcessor的功能，并添加了评议机制。

    评议流程：
    1. 首先使用多个LLM并行处理内容（使用MultipleLlmProcessor）
    2. 然后使用评议者LLM对这些结果进行评估和投票
    3. 根据投票结果选出最佳结果
    4. 将所有结果和评议信息保存到数据库

    与multiple模式的区别：
    - 不仅并行使用多个LLM，还使用额外的评议者LLM进行结果评估
    - 包含投票机制，可以选出最佳结果
    - 提供更全面的结果分析和比较
    - 资源消耗更大，处理时间更长
    """

    def __init__(self) -> None:
        """初始化评议处理器"""
        super().__init__()
        self.multiple_processor = MultipleLlmProcessor()

    async def process(self, task_id: int) -> Dict:
        """
        处理评议任务

        该方法是评议处理器的主要入口点，实现了BaseTaskProcessor的抽象方法。
        它负责协调多个LLM处理内容，然后使用评议者LLM进行结果评估和投票，
        最终选出最佳结果并返回完整的评议信息。

        处理流程：
        1. 更新任务状态为处理中
        2. 使用MultipleLlmProcessor并行处理内容
        3. 如果多个LLM处理成功，获取评议者LLM配置
        4. 使用评议者LLM对结果进行评估和投票
        5. 根据投票结果选出最佳结果
        6. 保存评议结果和投票信息到数据库
        7. 更新任务状态为已完成
        8. 返回完整的评议结果

        错误处理：
        - 如果任务状态更新失败，调用_handle_error方法处理
        - 如果多个LLM处理失败，返回错误信息
        - 如果没有足够的结果进行评议，返回多个LLM的处理结果
        - 如果评议者处理失败，返回多个LLM的处理结果
        - 捕获并处理所有未预期的异常

        Args:
            task_id: 要处理的任务的ID

        Returns:
            Dict: 包含处理结果的字典，包含以下字段：
                - success (bool): 处理是否成功
                - task_id (int): 任务ID
                - result_ids (List[int], 可选): 所有结果记录ID列表
                - best_result_id (int, 可选): 最佳结果记录ID
                - results (List[Dict], 可选): 所有处理结果
                - votes (List[Dict], 可选): 评议者投票信息
                - error (str, 可选): 失败时包含错误信息
        """
        logger.info(f"开始多LLM评议处理: 任务ID={task_id}")

        try:
            # 更新任务状态为处理中
            status_updated = await self._update_task_status(task_id, TaskStatus.PROCESSING)
            if not status_updated:
                return await self._handle_error(task_id, "更新任务状态失败")

            # 首先使用多LLM处理器获取结果
            multi_result = await self.multiple_processor.process(task_id)

            # 检查多LLM处理是否成功
            if not multi_result.get("success", False):
                return await self._handle_error(
                    task_id, f"多LLM处理失败: {multi_result.get('error', '未知错误')}"
                )

            # 获取处理结果ID列表
            result_ids = multi_result.get("result_ids", [])
            if not result_ids:
                return await self._handle_error(task_id, "多LLM处理未产生有效结果")

            # 获取任务内容
            task_data = await self._get_task_with_content(task_id)
            if not task_data:
                return await self._handle_error(task_id, "任务不存在或内容获取失败")

            # 获取任务内容
            task_content = task_data.get("content")

            # 获取评议者
            reviewers = await self._get_reviewers_for_task(task_id)

            # 根据评议者数量选择评议方式
            if not reviewers:
                logger.warning("未找到评议者LLM，返回多LLM处理结果")
                # 如果没有评议者，直接返回多LLM处理结果
                return multi_result
            elif len(reviewers) == 1:
                # 单评议者模式
                logger.info(f"使用单评议者模式: 评议者={reviewers[0].get('name')}")
                return await self._single_reviewer_mode(
                    task_id=task_id,
                    task_content=task_content,
                    reviewer=reviewers[0],
                    result_ids=result_ids,
                )
            else:
                # 多评议者投票模式
                logger.info(f"使用多评议者投票模式: 评议者数量={len(reviewers)}")
                return await self._multiple_reviewer_vote_mode(
                    task_id=task_id,
                    task_content=task_content,
                    reviewers=reviewers,
                    result_ids=result_ids,
                )

        except Exception as e:
            # 处理所有未捕获的异常
            return await self._handle_error(task_id, e)

    async def _single_reviewer_mode(
        self, task_id: int, task_content: str, reviewer: Dict, result_ids: List[int]
    ) -> Dict:
        """
        单评议者模式处理

        Args:
            task_id: 任务ID
            task_content: 任务内容
            reviewer: 评议者LLM配置
            result_ids: 结果ID列表

        Returns:
            处理结果字典
        """
        try:
            # 获取任务结果
            results = await self._get_task_results(task_id, result_ids)
            if not results:
                return await self._handle_error(task_id, "获取任务结果失败")

            # 创建评议提示词
            review_prompt = self._create_review_prompt(results)

            # 重建评议者LLM配置
            reconstructed_reviewer = self._rebuild_llm_config(reviewer)
            reviewer_id = reviewer.get("id")

            # 获取客户端
            client = get_client_for_llm(reconstructed_reviewer)

            # 处理评议
            logger.info(
                f"开始评议处理: 任务ID={task_id}, 评议者={reviewer.get('name')} (ID={reviewer_id})"
            )

            # 运行处理
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                review_result = await loop.run_in_executor(
                    executor,
                    lambda: client.process_content(content=task_content, prompt=review_prompt),
                )

            logger.info(
                f"评议处理完成: 任务ID={task_id}, 成功={review_result.get('success', False)}"
            )

            # 检查处理结果
            if not review_result.get("success", False):
                return await self._handle_error(
                    task_id, f"评议处理失败: {review_result.get('error', '未知错误')}"
                )

            # 保存评议结果
            result_id = await self._save_result(
                task_id=task_id, llm_id=reviewer_id, result=review_result, is_review_result=True
            )

            if not result_id:
                return await self._handle_error(task_id, "保存评议结果失败")

            # 更新任务状态为已完成
            await self._update_task_status(task_id, TaskStatus.COMPLETED)

            # 返回成功结果
            return {
                "success": True,
                "task_id": task_id,
                "final_result_id": result_id,
                "reviewer_id": reviewer_id,
                "result": review_result.get("result", {}),
            }

        except Exception as e:
            return await self._handle_error(task_id, f"单评议者模式处理失败: {str(e)}")

    async def _multiple_reviewer_vote_mode(
        self, task_id: int, task_content: str, reviewers: List[Dict], result_ids: List[int]
    ) -> Dict:
        """
        多评议者投票模式处理

        Args:
            task_id: 任务ID
            task_content: 任务内容
            reviewers: 评议者LLM配置列表
            result_ids: 结果ID列表

        Returns:
            处理结果字典
        """
        try:
            # 获取任务结果
            results = await self._get_task_results(task_id, result_ids)
            if not results:
                return await self._handle_error(task_id, "获取任务结果失败")

            # 创建投票提示词
            vote_prompt = self._create_vote_prompt(results)

            # 创建处理任务
            vote_tasks = []
            for reviewer in reviewers:
                # 包装处理任务
                task = self._create_reviewer_task(
                    reviewer=reviewer, task_content=task_content, prompt_content=vote_prompt
                )
                vote_tasks.append(task)

            # 并行执行所有任务，最多3个并发
            vote_results = await gather_with_concurrency(3, *vote_tasks, return_exceptions=True)

            # 处理投票结果
            votes = []
            for i, result in enumerate(vote_results):
                reviewer = reviewers[i]
                reviewer_id = reviewer.get("id")

                # 处理异常
                if isinstance(result, Exception):
                    logger.error(f"评议者处理异常: 评议者ID={reviewer_id}, 错误: {str(result)}")
                    votes.append((reviewer_id, None))
                else:
                    votes.append((reviewer_id, result))

            # 过滤出成功的投票
            valid_votes = [
                (r_id, result) for r_id, result in votes if result and result.get("success", False)
            ]

            if not valid_votes:
                return await self._handle_error(task_id, "所有评议者处理都失败")

            # 保存投票记录
            await self._save_votes(task_id, results, valid_votes)

            # 统计投票结果
            vote_counts = await self._count_votes(task_id, result_ids)

            # 如果没有有效投票，返回错误
            if not vote_counts:
                return await self._handle_error(task_id, "未能收集到有效投票")

            # 找出得票最多的结果
            final_result_id = max(vote_counts.items(), key=lambda x: x[1])[0]

            # 将此结果设为最终结果
            await self._set_final_result(task_id, final_result_id)

            # 更新任务状态为已完成
            await self._update_task_status(task_id, TaskStatus.COMPLETED)

            # 返回成功结果
            return {
                "success": True,
                "task_id": task_id,
                "final_result_id": final_result_id,
                "vote_counts": vote_counts,
                "valid_votes": len(valid_votes),
            }

        except Exception as e:
            return await self._handle_error(task_id, f"多评议者投票模式处理失败: {str(e)}")

    async def _get_task_results(self, task_id: int, result_ids: List[int]) -> List[Dict]:
        """
        获取任务结果

        Args:
            task_id: 任务ID
            result_ids: 结果ID列表

        Returns:
            结果字典列表
        """

        async def _get_results(session: Session) -> List[TaskResult]:
            results = (
                session.query(TaskResult)
                .filter(TaskResult.task_id == task_id, TaskResult.id.in_(result_ids))
                .all()
            )

            if not results:
                logger.warning(f"未找到任务结果: 任务ID={task_id}, 结果ID列表={result_ids}")
                return []

            # 按照传入的结果ID顺序排序
            sorted_results = sorted(results, key=lambda r: result_ids.index(r.id))

            # 转换为字典列表
            return [
                {
                    "id": r.id,
                    "llm_id": r.llm_id,
                    "raw_response": r.raw_response,
                    "bias_index": r.bias_index,
                    "misleading_index": r.misleading_index,
                    "hidden_intent_index": r.hidden_intent_index,
                    "credibility_score": r.credibility_score,
                }
                for r in sorted_results
            ]

        try:
            return await run_in_session(_get_results)
        except Exception as e:
            logger.error(f"获取任务结果失败: ID={task_id}, 错误: {str(e)}", exc_info=True)
            return []

    def _create_review_prompt(self, results: List[Dict]) -> str:
        """
        创建评议提示词

        Args:
            results: 结果列表

        Returns:
            评议提示词
        """
        # 创建包含所有结果的评议提示
        review_prompt = (
            "# 多LLM评估结果评议\n\n"
            "你的任务是评议多个LLM对同一篇文章的分析结果，综合它们的分析，给出最终的评估结果。\n\n"
            "## LLM评估结果\n\n"
        )

        # 添加每个LLM的评估结果
        for i, result in enumerate(results, 1):
            review_prompt += f"### LLM {i} 的评估结果\n\n"
            review_prompt += f"```\n{result.get('raw_response', '未提供原始响应')}\n```\n\n"

        # 添加评议要求
        review_prompt += (
            "## 评议要求\n\n"
            "1. 分析比较上述LLM的评估结果，找出它们的共同点和差异\n"
            "2. 对于分歧点，评估哪些观点更有说服力，并说明理由\n"
            "3. 综合所有LLM的评分，给出最终的偏见指数、误导性指数、隐藏意图指数和综合可信度分数\n"
            "4. 按照与原始评估相同的格式给出完整的评估报告\n\n"
            "## 输出格式\n\n"
            "请严格按照原始评估报告的格式给出评议结果，必须包含完整的量化评分。"
        )

        return review_prompt

    def _create_vote_prompt(self, results: List[Dict]) -> str:
        """
        创建投票提示词

        Args:
            results: 结果列表

        Returns:
            投票提示词
        """
        # 创建包含所有结果的投票提示
        vote_prompt = (
            "# 多LLM评估结果投票\n\n"
            "你的任务是评估多个LLM对同一篇文章的分析结果，并投票选择最准确、最全面的分析结果。\n\n"
            "## LLM评估结果\n\n"
        )

        # 添加每个LLM的评估结果
        for i, result in enumerate(results, 1):
            vote_prompt += f"### LLM {i} (ID: {result.get('id')}) 的评估结果\n\n"
            vote_prompt += f"```\n{result.get('raw_response', '未提供原始响应')}\n```\n\n"

        # 添加投票要求
        vote_prompt += (
            "## 投票要求\n\n"
            "1. 分析比较上述LLM的评估结果，找出它们的共同点和差异\n"
            "2. 评估每个结果的全面性、准确性和深度\n"
            "3. 投票选择一个你认为最好的结果\n\n"
            "## 输出格式\n\n"
            "你必须明确指出你的投票，格式如下：\n\n"
            "```\n我投票给 LLM X (ID: Y)，因为...\n```\n\n"
            "其中X是LLM序号，Y是对应的ID。请确保正确引用ID，这对投票统计至关重要。"
        )

        return vote_prompt

    async def _create_reviewer_task(
        self, reviewer: Dict, task_content: str, prompt_content: str
    ) -> asyncio.Task:
        """
        创建评议者处理任务

        Args:
            reviewer: 评议者LLM配置
            task_content: 任务内容
            prompt_content: 提示词内容

        Returns:
            异步任务对象
        """
        # 重建LLM配置对象
        reconstructed_reviewer = self._rebuild_llm_config(reviewer)

        # 创建处理函数
        async def process_with_reviewer() -> Dict[str, Any]:
            try:
                # 获取客户端
                client = get_client_for_llm(reconstructed_reviewer)

                # 处理内容
                reviewer_id = reviewer.get("id")
                reviewer_name = reviewer.get("name")
                logger.info(f"开始评议者处理: 评议者={reviewer_name} (ID={reviewer_id})")

                # 运行处理
                # 直接使用异步方式调用process_content方法
                result = await client.process_content(content=task_content, prompt=prompt_content)

                logger.info(
                    f"评议者处理完成: 评议者={reviewer_name} (ID={reviewer_id}), "
                    f"成功={result.get('success', False)}"
                )
                return result

            except Exception as e:
                logger.error(
                    f"评议者处理失败: 评议者={reviewer.get('name')} (ID={reviewer.get('id')}), "
                    f"错误: {str(e)}"
                )
                raise

        # 创建任务
        return asyncio.create_task(process_with_reviewer())

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
            role=llm_data.get("role", "reviewer"),
            is_default=llm_data.get("is_default", False),
        )

        # 添加provider属性
        provider = llm_data.get("provider")
        if provider:
            reconstructed_llm.provider = provider

        return reconstructed_llm

    async def _save_votes(self, task_id: int, results: List[Dict], votes: List[tuple]) -> None:
        """
        保存投票记录

        Args:
            task_id: 任务ID
            results: 结果列表
            votes: 投票列表，每项为(reviewer_id, vote_result)元组
        """

        async def _save_vote_records(session: Session) -> List[ReviewerVote]:
            for reviewer_id, vote_result in votes:
                if not vote_result:
                    continue

                # 解析投票，获取评议者选择的结果ID
                raw_response = vote_result.get("raw_response", "")
                voted_result_id = self._parse_vote_result(raw_response, results)

                if voted_result_id:
                    # 保存投票记录
                    reviewer_vote = ReviewerVote(
                        task_id=task_id,
                        reviewer_id=reviewer_id,
                        voted_result_id=voted_result_id,
                        comment=raw_response,
                    )
                    session.add(reviewer_vote)
                    logger.info(
                        f"已保存投票记录: 评议者ID={reviewer_id}, 投票结果ID={voted_result_id}"
                    )

        try:
            await run_in_session(_save_vote_records)
        except Exception as e:
            logger.error(f"保存投票记录失败: 任务ID={task_id}, 错误: {str(e)}", exc_info=True)

    def _parse_vote_result(self, vote_text: str, results: List[Dict]) -> Optional[int]:
        """
        解析投票结果

        Args:
            vote_text: 投票文本
            results: 结果列表

        Returns:
            投票选择的结果ID，如果未能解析则返回None
        """
        if not vote_text:
            return None

        logger.debug(f"开始解析投票结果文本: {len(vote_text)} 字符")
        try:
            # 解析投票文本，查找"ID: X"模式
            id_pattern = re.compile(r"ID:\s*(\d+)")
            match = id_pattern.search(vote_text)
            if match:
                voted_id = int(match.group(1))
                logger.debug(f"找到ID格式投票: {voted_id}")
                # 验证ID是否在结果列表中
                if any(result.get("id") == voted_id for result in results):
                    logger.info(f"投票结果解析成功: 投票ID={voted_id}")
                    return voted_id
                else:
                    logger.warning(f"投票ID {voted_id} 不在有效结果列表中")

            # 如果未找到ID格式，尝试查找"LLM X"格式
            llm_pattern = re.compile(r"LLM\s*(\d+)")
            match = llm_pattern.search(vote_text)
            if match:
                llm_index = int(match.group(1)) - 1  # 减1因为索引从0开始
                logger.debug(f"找到LLM索引格式投票: 索引={llm_index}")
                if 0 <= llm_index < len(results):
                    voted_id = results[llm_index].get("id")
                    logger.info(f"投票结果解析成功: 索引={llm_index}, 投票ID={voted_id}")
                    return voted_id
                else:
                    logger.warning(f"LLM索引 {llm_index} 超出范围 [0-{len(results)-1}]")

            logger.warning(f"无法从投票文本中解析出有效的投票ID: {vote_text[:100]}...")
            return None
        except Exception as e:
            logger.error(f"解析投票结果时发生异常: {str(e)}", exc_info=True)
            return None

    async def _count_votes(self, task_id: int, result_ids: List[int]) -> Dict[int, int]:
        """
        统计投票

        Args:
            task_id: 任务ID
            result_ids: 结果ID列表

        Returns:
            投票统计字典，键为结果ID，值为票数
        """

        async def _count_vote_records(session: Session) -> Dict[int, int]:
            # 查询所有投票记录
            votes = session.query(ReviewerVote).filter_by(task_id=task_id).all()

            # 统计票数
            vote_counts: Dict[int, int] = {}
            for vote in votes:
                if vote.voted_result_id in result_ids:  # 确保投票的是有效结果
                    vote_counts[vote.voted_result_id] = vote_counts.get(vote.voted_result_id, 0) + 1

            return vote_counts

        try:
            return await run_in_session(_count_vote_records)
        except Exception as e:
            logger.error(f"统计投票失败: 任务ID={task_id}, 错误: {str(e)}", exc_info=True)
            return {}

    async def _set_final_result(self, task_id: int, result_id: int) -> bool:
        """
        设置最终结果

        Args:
            task_id: 任务ID
            result_id: 最终结果ID

        Returns:
            设置是否成功
        """

        async def _update_final_result(session: Session) -> bool:
            # 获取任务
            task = session.query(Task).filter_by(id=task_id).first()
            if not task:
                logger.warning(f"设置最终结果失败: 任务不存在, ID={task_id}")
                return False

            # 更新最终结果ID
            task.final_result_id = result_id
            task.updated_at = time.time()
            return True

        try:
            return await run_in_session(_update_final_result)
        except Exception as e:
            logger.error(
                f"设置最终结果失败: 任务ID={task_id}, 结果ID={result_id}, 错误: {str(e)}",
                exc_info=True,
            )
            return False
