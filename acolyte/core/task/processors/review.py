"""
评议处理器

处理使用多个LLM并进行评议的任务。
"""

import re
import time
from typing import Dict, List, Optional

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

    def __init__(self):
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
        start_time = time.time()

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
                elapsed_time = time.time() - start_time
                logger.info(f"多LLM评议处理完成(无评议者): 任务ID={task_id}, 耗时={elapsed_time:.2f}秒")
                return multi_result
            elif len(reviewers) == 1:
                # 单评议者模式
                logger.info(f"使用单评议者模式: 评议者={reviewers[0].get('name')}")
                result = await self._single_reviewer_mode(
                    task_id=task_id,
                    task_content=task_content,
                    reviewer=reviewers[0],
                    result_ids=result_ids,
                )
                elapsed_time = time.time() - start_time
                logger.info(f"多LLM评议处理完成(单评议者模式): 任务ID={task_id}, 耗时={elapsed_time:.2f}秒")
                return result
            else:
                # 多评议者投票模式
                logger.info(f"使用多评议者投票模式: 评议者数量={len(reviewers)}")
                result = await self._multiple_reviewer_vote_mode(
                    task_id=task_id,
                    task_content=task_content,
                    reviewers=reviewers,
                    result_ids=result_ids,
                )
                elapsed_time = time.time() - start_time
                logger.info(f"多LLM评议处理完成(多评议者投票模式): 任务ID={task_id}, 耗时={elapsed_time:.2f}秒")
                return result

        except Exception as e:
            # 处理所有未捕获的异常
            elapsed_time = time.time() - start_time
            logger.error(f"评议处理异常: ID={task_id}, 耗时={elapsed_time:.2f}秒, 错误: {str(e)}")
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
            review_result = await client.process_content(content=task_content, prompt=review_prompt)

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

            # 将此结果设为最终结果
            await self._set_final_result(task_id, result_id)

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

            # 创建处理协程
            vote_coroutines = []
            for reviewer in reviewers:
                # 重建评议者LLM配置
                reconstructed_reviewer = self._rebuild_llm_config(reviewer)
                reviewer_id = reviewer.get("id")

                # 获取客户端
                client = get_client_for_llm(reconstructed_reviewer)

                # 创建处理协程
                logger.info(f"创建评议者处理协程: 评议者={reviewer.get('name')} (ID={reviewer_id})")
                coroutine = client.process_content(content=task_content, prompt=vote_prompt)
                vote_coroutines.append((reviewer_id, coroutine))

            # 并行执行所有协程，最多3个并发
            logger.info(f"开始并行执行 {len(vote_coroutines)} 个评议者处理协程")

            # 使用gather_with_concurrency并行执行协程
            reviewer_ids = [r_id for r_id, _ in vote_coroutines]
            coroutines = [coro for _, coro in vote_coroutines]
            results_with_exceptions = await gather_with_concurrency(3, *coroutines, return_exceptions=True)

            # 处理投票结果
            votes = []
            for i, result in enumerate(results_with_exceptions):
                reviewer_id = reviewer_ids[i]
                reviewer_name = next((r.get("name") for r in reviewers if r.get("id") == reviewer_id), f"ID={reviewer_id}")

                # 处理异常
                if isinstance(result, Exception):
                    logger.error(f"评议者处理异常: 评议者={reviewer_name}, 错误: {str(result)}")
                    continue

                # 检查处理成功
                if not result.get("success", False):
                    logger.error(f"评议者处理失败: 评议者={reviewer_name}, 错误: {result.get('error', '未知错误')}")
                    continue

                # 解析投票结果
                raw_response = result.get("raw_response", "")
                voted_result_id = self._parse_vote_result(raw_response, results)

                if voted_result_id:
                    logger.info(f"评议者投票成功: 评议者={reviewer_name}, 投票结果ID={voted_result_id}")
                    votes.append((reviewer_id, voted_result_id, raw_response))
                else:
                    logger.warning(f"评议者投票解析失败: 评议者={reviewer_name}")

            # 检查是否有有效投票
            if not votes:
                return await self._handle_error(task_id, "所有评议者投票都失败")

            # 保存投票记录
            await self._save_votes(task_id, votes)

            # 统计投票结果
            vote_counts = self._count_votes(votes)

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
                "valid_votes": len(votes),
            }

        except Exception as e:
            return await self._handle_error(task_id, f"多评议者投票模式处理失败: {str(e)}")

    def _create_review_prompt(self, results: List[Dict]) -> str:
        """
        创建评议提示词

        Args:
            results: 多LLM处理结果列表

        Returns:
            评议提示词
        """
        prompt = """你是一个客观公正的评议者，负责评估多个LLM对同一内容的分析结果。

下面是多个LLM对同一内容的分析结果，请你仔细阅读并进行全面评估，然后给出你的分析意见。

要求：
1. 客观评估每个LLM的分析结果
2. 比较不同结果的强项和弱项
3. 指出哪个结果最全面、最准确
4. 给出你的综合分析和建议

请按照以下格式输出你的评估：

## 各结果评估

[对每个结果的评估]

## 比较分析

[各结果的比较分析]

## 最佳结果

[指出最佳结果及原因]

## 综合建议

[你的综合建议]

现在，请开始评估以下结果：

"""

        # 添加每个LLM的处理结果
        for i, result in enumerate(results, 1):
            llm_name = result.get("llm_name", f"LLM {i}")
            result_content = result.get("result", {})

            # 提取关键字段
            bias = result_content.get("bias", "")
            misleading = result_content.get("misleading", "")
            hidden_intent = result_content.get("hidden_intent", "")
            analysis = result_content.get("analysis", "")

            prompt += f"""

### 结果 {i} - {llm_name}

**偏见分析**：
{bias}

**误导性分析**：
{misleading}

**隐藏意图分析**：
{hidden_intent}

**总体分析**：
{analysis}
"""

        return prompt

    def _create_vote_prompt(self, results: List[Dict]) -> str:
        """
        创建投票提示词

        Args:
            results: 多LLM处理结果列表

        Returns:
            投票提示词
        """
        prompt = """你是一个客观公正的评议者，负责评估多个LLM对同一内容的分析结果，并选出最佳结果。

下面是多个LLM对同一内容的分析结果，请你仔细阅读并选出最全面、最准确的结果。

要求：
1. 客观评估每个LLM的分析结果
2. 选出你认为最佳的结果
3. 给出选择的理由

请按照以下格式输出你的选择：

## 最佳结果

我选择结果 [X] 作为最佳结果。

## 选择理由

[你的选择理由]

现在，请开始评估以下结果：

"""

        # 添加每个LLM的处理结果
        for i, result in enumerate(results, 1):
            llm_name = result.get("llm_name", f"LLM {i}")
            result_id = result.get("id")
            result_content = result.get("result", {})

            # 提取关键字段
            bias = result_content.get("bias", "")
            misleading = result_content.get("misleading", "")
            hidden_intent = result_content.get("hidden_intent", "")
            analysis = result_content.get("analysis", "")

            prompt += f"""

### 结果 {i} - {llm_name} (ID: {result_id})

**偏见分析**：
{bias}

**误导性分析**：
{misleading}

**隐藏意图分析**：
{hidden_intent}

**总体分析**：
{analysis}
"""

        return prompt

    def _parse_vote_result(self, raw_response: str, results: List[Dict]) -> Optional[int]:
        """
        解析投票结果

        Args:
            raw_response: LLM原始响应
            results: 多LLM处理结果列表

        Returns:
            投票结果ID，如果解析失败则返回None
        """
        try:
            # 尝试使用正则表达式匹配“我选择结果 [X]”或“结果 [X]”模式
            pattern = r"我选择结果\s*[\[\(]?\s*(\d+)\s*[\]\)]?"|r"结果\s*[\[\(]?\s*(\d+)\s*[\]\)]?"
            match = re.search(pattern, raw_response)

            if match:
                # 获取结果编号
                result_number = int(match.group(1))

                # 结果编号是从1开始的，需要转换为索引
                if 1 <= result_number <= len(results):
                    # 返回对应的结果ID
                    return results[result_number - 1].get("id")

            # 如果上面的方法失败，尝试直接匹配ID
            id_pattern = r"ID:\s*(\d+)"
            id_matches = re.findall(id_pattern, raw_response)

            if id_matches:
                # 检查每个匹配到的ID是否在结果列表中
                for id_str in id_matches:
                    result_id = int(id_str)
                    # 检查这个ID是否在结果列表中
                    if any(result.get("id") == result_id for result in results):
                        return result_id

            # 如果上述方法都失败，返回None
            logger.warning(f"无法解析投票结果: {raw_response[:100]}...")
            return None

        except Exception as e:
            logger.error(f"解析投票结果异常: {str(e)}")
            return None

    def _count_votes(self, votes: List[tuple]) -> Dict[int, int]:
        """
        统计投票结果

        Args:
            votes: 投票列表，每项为 (reviewer_id, voted_result_id, raw_response) 的元组

        Returns:
            投票统计结果，键为结果ID，值为得票数
        """
        vote_counts = {}

        for _, voted_result_id, _ in votes:
            if voted_result_id in vote_counts:
                vote_counts[voted_result_id] += 1
            else:
                vote_counts[voted_result_id] = 1

        return vote_counts

    async def _get_task_with_content(self, task_id: int) -> Optional[Dict]:
        """
        获取任务及其内容

        Args:
            task_id: 任务ID

        Returns:
            任务信息字典，如果任务不存在则返回None
        """
        try:
            # 使用run_in_session在数据库会话中执行查询
            async def _get_task(session):
                task = session.query(Task).filter(Task.id == task_id).first()
                if not task:
                    return None
                return {
                    "id": task.id,
                    "content": task.content,
                    "status": task.status,
                    "created_at": task.created_at,
                }

            return await run_in_session(_get_task)
        except Exception as e:
            logger.error(f"获取任务异常: ID={task_id}, 错误: {str(e)}")
            return None

    async def _get_task_results(self, task_id: int, result_ids: List[int]) -> List[Dict]:
        """
        获取任务结果

        Args:
            task_id: 任务ID
            result_ids: 结果ID列表

        Returns:
            结果列表
        """
        try:
            # 使用run_in_session在数据库会话中执行查询
            async def _get_results(session):
                results = (
                    session.query(TaskResult)
                    .filter(TaskResult.task_id == task_id)
                    .filter(TaskResult.id.in_(result_ids))
                    .all()
                )

                # 将结果转换为字典列表
                result_list = []
                for result in results:
                    # 获取LLM名称
                    llm = session.query(LlmConfig).filter(LlmConfig.id == result.llm_id).first()
                    llm_name = llm.name if llm else f"LLM {result.llm_id}"

                    result_list.append({
                        "id": result.id,
                        "llm_id": result.llm_id,
                        "llm_name": llm_name,
                        "result": result.result,
                        "created_at": result.created_at,
                    })

                return result_list

            return await run_in_session(_get_results)
        except Exception as e:
            logger.error(f"获取任务结果异常: ID={task_id}, 错误: {str(e)}")
            return []

    async def _get_reviewers_for_task(self, task_id: int) -> List[Dict]:
        """
        获取任务的评议者LLM配置

        Args:
            task_id: 任务ID

        Returns:
            评议者LLM配置列表
        """
        try:
            # 使用run_in_session在数据库会话中执行查询
            async def _get_reviewers(session):
                # 获取所有reviewer角色的LLM配置
                reviewers = session.query(LlmConfig).filter(LlmConfig.role.ilike("reviewer")).all()

                # 将结果转换为字典列表
                reviewer_list = []
                for reviewer in reviewers:
                    reviewer_list.append({
                        "id": reviewer.id,
                        "name": reviewer.name,
                        "provider": reviewer.provider,
                        "model": reviewer.model,
                        "role": reviewer.role,
                        "parameters": reviewer.parameters,
                        "system_prompt": reviewer.system_prompt,
                    })

                return reviewer_list

            return await run_in_session(_get_reviewers)
        except Exception as e:
            logger.error(f"获取评议者异常: 任务ID={task_id}, 错误: {str(e)}")
            return []

    def _rebuild_llm_config(self, llm_data: Dict) -> LlmConfig:
        """
        从字典数据重建 LlmConfig 对象

        Args:
            llm_data: 包含LLM配置数据的字典，通常来自数据库查询结果

        Returns:
            LlmConfig: 重建的LLM配置对象，可用于创建LLM客户端
        """
        reconstructed_llm = LlmConfig(
            id=llm_data.get("id"),
            name=llm_data.get("name"),
            provider=llm_data.get("provider"),
            model=llm_data.get("model"),
            role=llm_data.get("role", "reviewer"),
            parameters=llm_data.get("parameters", {}),
            system_prompt=llm_data.get("system_prompt", ""),
        )

        return reconstructed_llm

    async def _save_result(
        self, task_id: int, llm_id: int, result: Dict, is_review_result: bool = False
    ) -> Optional[int]:
        """
        保存处理结果

        Args:
            task_id: 任务ID
            llm_id: LLM ID
            result: 处理结果
            is_review_result: 是否为评议结果

        Returns:
            结果ID，如果保存失败则返回None
        """
        try:
            # 使用run_in_session在数据库会话中执行操作
            async def _save(session):
                # 获取任务
                task = session.query(Task).filter(Task.id == task_id).first()
                if not task:
                    logger.warning(f"保存结果失败: 任务不存在, ID={task_id}")
                    return None

                # 提取评分
                result_data = result.get("result", {})

                # 尝试从结果中提取评分
                bias_index = result_data.get("bias_index")
                misleading_index = result_data.get("misleading_index")
                hidden_intent_index = result_data.get("hidden_intent_index")
                credibility_score = result_data.get("credibility_score")

                # 如果从 result_data 中提取失败，尝试直接从 result 中提取
                if (
                    bias_index is None
                    and misleading_index is None
                    and hidden_intent_index is None
                    and credibility_score is None
                ):
                    bias_index = result.get("bias_index")
                    misleading_index = result.get("misleading_index")
                    hidden_intent_index = result.get("hidden_intent_index")
                    credibility_score = result.get("credibility_score")

                # 记录提取到的评分
                logger.debug(
                    f"从结果中提取评分: 任务ID={task_id}, BI={bias_index}, MI={misleading_index}, HI={hidden_intent_index}, CS={credibility_score}"
                )

                # 创建新的结果记录
                task_result = TaskResult(
                    task_id=task_id,
                    llm_id=llm_id,
                    result=result_data,
                    raw_response=result.get("raw_response", ""),
                    bias_index=bias_index,
                    misleading_index=misleading_index,
                    hidden_intent_index=hidden_intent_index,
                    credibility_score=credibility_score,
                    is_review_result=is_review_result,
                )

                session.add(task_result)
                session.flush()

                # 如果是评议结果或单LLM结果，更新任务的最终结果
                if is_review_result or not task.final_result_id:
                    old_final_result_id = task.final_result_id
                    task.final_result_id = task_result.id

                    if old_final_result_id:
                        logger.info(
                            f"更新任务最终结果: 任务ID={task_id}, 旧结果ID={old_final_result_id}, 新结果ID={task_result.id}"
                        )
                    else:
                        logger.info(f"设置任务最终结果: 任务ID={task_id}, 结果ID={task_result.id}")

                return task_result.id

            return await run_in_session(_save)
        except Exception as e:
            logger.error(f"保存结果异常: 任务ID={task_id}, LLM ID={llm_id}, 错误: {str(e)}")
            return None

    async def _save_votes(self, task_id: int, votes: List[tuple]) -> bool:
        """
        保存投票记录

        Args:
            task_id: 任务ID
            votes: 投票列表，每项为 (reviewer_id, voted_result_id, raw_response) 的元组

        Returns:
            是否保存成功
        """
        try:
            # 使用run_in_session在数据库会话中执行操作
            async def _save(session):
                for reviewer_id, voted_result_id, raw_response in votes:
                    # 创建新的投票记录
                    vote = ReviewerVote(
                        task_id=task_id,
                        reviewer_id=reviewer_id,
                        result_id=voted_result_id,
                        raw_response=raw_response,
                    )

                    session.add(vote)

                return True

            return await run_in_session(_save)
        except Exception as e:
            logger.error(f"保存投票记录异常: 任务ID={task_id}, 错误: {str(e)}")
            return False

    async def _set_final_result(self, task_id: int, result_id: int) -> bool:
        """
        设置最终结果

        Args:
            task_id: 任务ID
            result_id: 结果ID

        Returns:
            是否设置成功
        """
        try:
            # 使用run_in_session在数据库会话中执行操作
            async def _update(session):
                task = session.query(Task).filter(Task.id == task_id).first()
                if not task:
                    return False

                task.final_result_id = result_id
                return True

            return await run_in_session(_update)
        except Exception as e:
            logger.error(f"设置最终结果异常: 任务ID={task_id}, 结果ID={result_id}, 错误: {str(e)}")
            return False

    async def _update_task_status(self, task_id: int, status: TaskStatus) -> bool:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态

        Returns:
            是否更新成功
        """
        try:
            # 使用run_in_session在数据库会话中执行操作
            async def _update(session):
                task = session.query(Task).filter(Task.id == task_id).first()
                if not task:
                    return False

                task.status = status
                return True

            return await run_in_session(_update)
        except Exception as e:
            logger.error(f"更新任务状态异常: ID={task_id}, 状态={status}, 错误: {str(e)}")
            return False

    async def _handle_error(self, task_id: int, error) -> Dict:
        """
        处理错误

        Args:
            task_id: 任务ID
            error: 错误信息

        Returns:
            错误结果字典
        """
        # 将错误转换为字符串
        error_message = str(error)
        logger.error(f"评议处理错误: ID={task_id}, 错误: {error_message}")

        # 更新任务状态为失败
        await self._update_task_status(task_id, TaskStatus.FAILED)

        # 返回错误结果
        return {
            "success": False,
            "task_id": task_id,
            "error": error_message,
        }