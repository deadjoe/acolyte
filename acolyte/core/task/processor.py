"""
任务处理模块
"""
import asyncio
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

from acolyte.core.db.database import db
from acolyte.core.db.models import (
    LlmConfig, LlmRole, ProcessingMode, Prompt, 
    ReviewerVote, Task, TaskResult, TaskStatus
)
from acolyte.core.llm.client import get_client_for_llm
from acolyte.core.llm.manager import LlmManager
from acolyte.core.prompt.manager import PromptManager
from acolyte.utils.logging import get_logger

# 获取模块日志记录器
logger = get_logger(__name__)


class TaskProcessor:
    """任务处理器"""

    def __init__(self):
        """初始化任务处理器"""
        self.llm_manager = LlmManager()
        self.prompt_manager = PromptManager()

    async def process_task(self, task_id: int) -> Dict:
        """处理任务

        Args:
            task_id: 任务ID

        Returns:
            处理结果字典
        """
        logger.info(f"开始处理任务: ID={task_id}")
        start_time = time.time()
        
        # 获取任务
        with db.session_scope() as session:
            task = session.query(Task).filter_by(id=task_id).first()
            if not task:
                logger.error(f"任务不存在: ID={task_id}")
                return {"success": False, "error": "任务不存在"}

            logger.info(f"获取到任务信息: 处理模式={task.processing_mode.value}, 当前状态={task.status.value}")
            
            # 更新任务状态为处理中
            task.status = TaskStatus.PROCESSING
            session.commit()
            logger.debug(f"已更新任务状态为处理中")

        try:
            # 根据处理模式选择对应的处理方法
            if task.processing_mode == ProcessingMode.SINGLE:
                logger.info(f"使用单LLM处理模式")
                result = await self._process_single_llm(task_id)
            elif task.processing_mode == ProcessingMode.MULTIPLE:
                logger.info(f"使用多LLM处理模式")
                result = await self._process_multiple_llm(task_id)
            elif task.processing_mode == ProcessingMode.MULTIPLE_WITH_REVIEW:
                logger.info(f"使用多LLM带评议处理模式")
                result = await self._process_multiple_llm_with_review(task_id)
            else:
                logger.error(f"未知的处理模式: {task.processing_mode.value}")
                result = {"success": False, "error": "未知的处理模式"}

            # 记录处理结果
            if result["success"]:
                logger.info(f"任务处理成功: {result.get('final_result_id', '无最终结果ID')}")
            else:
                logger.error(f"任务处理失败: {result.get('error', '未知错误')}")

            # 更新任务状态
            with db.session_scope() as session:
                task = session.query(Task).filter_by(id=task_id).first()
                if task:
                    task.status = TaskStatus.COMPLETED if result["success"] else TaskStatus.FAILED
                    logger.debug(f"已更新任务状态为: {task.status.value}")
                    
                    # 如果处理成功且有最终结果ID，更新任务的最终结果ID
                    if result["success"] and "final_result_id" in result:
                        task.final_result_id = result["final_result_id"]
                        logger.debug(f"已更新任务最终结果ID: {result['final_result_id']}")

            elapsed_time = time.time() - start_time
            logger.info(f"任务处理完成: 耗时={elapsed_time:.2f}秒, 结果={'成功' if result['success'] else '失败'}")
            return result

        except Exception as e:
            # 发生异常，更新任务状态为失败
            error_msg = str(e)
            logger.error(f"任务处理异常: {error_msg}")
            logger.debug(f"异常详情: {traceback.format_exc()}")
            
            with db.session_scope() as session:
                task = session.query(Task).filter_by(id=task_id).first()
                if task:
                    task.status = TaskStatus.FAILED
                    logger.debug(f"已更新任务状态为失败")

            elapsed_time = time.time() - start_time
            logger.info(f"任务处理终止: 耗时={elapsed_time:.2f}秒, 异常导致失败")
            return {"success": False, "error": error_msg}

    async def _process_single_llm(self, task_id: int) -> Dict:
        """使用单个LLM处理任务

        Args:
            task_id: 任务ID

        Returns:
            处理结果字典
        """
        logger.info(f"开始单LLM处理: 任务ID={task_id}")
        
        # 获取任务信息
        with db.session_scope() as session:
            task = session.query(Task).filter_by(id=task_id).first()
            if not task:
                logger.error(f"任务不存在: ID={task_id}")
                return {"success": False, "error": "任务不存在"}

            logger.debug(f"任务内容长度: {len(task.content)} 字符")
            
            # 获取默认LLM
            llm = session.query(LlmConfig).filter_by(is_default=True).first()
            if not llm:
                logger.error("未配置默认LLM")
                return {"success": False, "error": "未配置默认LLM"}
            
            logger.info(f"使用默认LLM: {llm.name} (ID={llm.id}, 模型={llm.model_name})")
            
            # 获取Prompt
            prompt = None
            if task.prompt_id:
                prompt = session.query(Prompt).filter_by(id=task.prompt_id).first()
                if prompt:
                    logger.info(f"使用指定的Prompt: ID={prompt.id}, 版本={prompt.version}")
                else:
                    logger.warning(f"未找到指定的Prompt (ID={task.prompt_id})")
            
            if not prompt:
                # 尝试获取最新的Prompt
                logger.info(f"尝试获取适用于模型 {llm.model_name} 的最新Prompt")
                prompt_obj = self.prompt_manager.get_latest_prompt(llm.model_name)
                if prompt_obj:
                    prompt = prompt_obj
                    logger.info(f"使用最新Prompt: ID={prompt.id}, 版本={prompt.version}")
                else:
                    logger.error("未找到适用的Prompt模板")
                    return {"success": False, "error": "未找到适用的Prompt模板"}
            
            logger.debug(f"Prompt内容长度: {len(prompt.content)} 字符")

        # 处理内容
        logger.info("创建LLM客户端并发送处理请求...")
        client = get_client_for_llm(llm)
        result = client.process_content(task.content, prompt.content)

        # 检查处理结果
        if result["success"]:
            logger.info("API调用成功，保存结果...")
            
            # 记录评分结果
            bias_index = result["result"].get("bias_index")
            misleading_index = result["result"].get("misleading_index")
            hidden_intent_index = result["result"].get("hidden_intent_index")
            credibility_score = result["result"].get("credibility_score")
            
            logger.info(f"评分结果: BI={bias_index}, MI={misleading_index}, "
                      f"HI={hidden_intent_index}, CS={credibility_score}")
            
            # 保存结果
            with db.session_scope() as session:
                task_result = TaskResult(
                    task_id=task_id,
                    llm_id=llm.id,
                    raw_response=result["raw_response"],
                    processed_result=result.get("processed_result"),
                    bias_index=bias_index,
                    misleading_index=misleading_index,
                    hidden_intent_index=hidden_intent_index,
                    credibility_score=credibility_score,
                    is_review_result=False
                )
                session.add(task_result)
                session.flush()
                result_id = task_result.id
                result["final_result_id"] = result_id
                logger.info(f"结果已保存: ID={result_id}")
        else:
            logger.error(f"API调用失败: {result.get('error', '未知错误')}")

        return result

    async def _process_multiple_llm(self, task_id: int) -> Dict:
        """使用多个LLM处理任务

        Args:
            task_id: 任务ID

        Returns:
            处理结果字典，包含所有LLM的处理结果
        """
        # 获取任务信息
        with db.session_scope() as session:
            task = session.query(Task).filter_by(id=task_id).first()
            if not task:
                return {"success": False, "error": "任务不存在"}

            # 获取任务关联的LLM列表
            llms = []
            for llm_assoc in task.llm_configs:
                llms.append(llm_assoc)

            if not llms:
                # 如果没有指定LLM，获取所有普通角色的LLM
                llms = session.query(LlmConfig).filter_by(role=LlmRole.NORMAL).all()

            if not llms:
                return {"success": False, "error": "未找到可用的LLM"}

            # 获取Prompt
            prompt = session.query(Prompt).filter_by(id=task.prompt_id).first()
            if not prompt:
                # 尝试获取最新的通用Prompt
                prompt_obj = self.prompt_manager.get_latest_prompt()
                if not prompt_obj:
                    return {"success": False, "error": "未找到适用的Prompt模板"}
                prompt = prompt_obj

        # 并行处理内容
        # 使用线程池并行处理，避免阻塞事件循环
        results = []
        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            tasks = []
            for llm in llms:
                client = get_client_for_llm(llm)
                task_func = lambda c=client: c.process_content(task.content, prompt.content)
                tasks.append(loop.run_in_executor(executor, task_func))

            # 等待所有任务完成
            llm_results = await asyncio.gather(*tasks)
            results = list(zip(llms, llm_results))

        # 保存所有结果
        result_ids = []
        with db.session_scope() as session:
            for llm, llm_result in results:
                if llm_result["success"]:
                    task_result = TaskResult(
                        task_id=task_id,
                        llm_id=llm.id,
                        raw_response=llm_result["raw_response"],
                        processed_result=llm_result.get("processed_result"),
                        bias_index=llm_result["result"].get("bias_index"),
                        misleading_index=llm_result["result"].get("misleading_index"),
                        hidden_intent_index=llm_result["result"].get("hidden_intent_index"),
                        credibility_score=llm_result["result"].get("credibility_score"),
                        is_review_result=False
                    )
                    session.add(task_result)
                    session.flush()
                    result_ids.append(task_result.id)

        # 返回所有结果
        return {
            "success": True,
            "results": [r[1] for r in results if r[1]["success"]],
            "error": None if all(r[1]["success"] for r in results) else "部分LLM处理失败",
            "result_ids": result_ids
        }

    async def _process_multiple_llm_with_review(self, task_id: int) -> Dict:
        """使用多个LLM处理任务并由评议者进行评议

        Args:
            task_id: 任务ID

        Returns:
            处理结果字典，包含所有LLM的处理结果和评议结果
        """
        # 首先进行多LLM处理
        multi_result = await self._process_multiple_llm(task_id)
        if not multi_result["success"]:
            return multi_result

        # 获取评议者
        with db.session_scope() as session:
            task = session.query(Task).filter_by(id=task_id).first()
            reviewers = []
            
            # 获取任务关联的评议者LLM
            for llm_assoc in task.llm_configs:
                if llm_assoc.role == LlmRole.REVIEWER:
                    reviewers.append(llm_assoc)
            
            # 如果没有指定评议者，获取所有评议者角色的LLM
            if not reviewers:
                reviewers = session.query(LlmConfig).filter_by(role=LlmRole.REVIEWER).all()
            
            if not reviewers:
                # 如果没有评议者，返回多LLM处理结果
                return {
                    "success": True,
                    "results": multi_result["results"],
                    "error": "未找到评议者LLM，返回所有处理结果",
                    "result_ids": multi_result["result_ids"]
                }
            
            # 获取所有处理结果
            task_results = session.query(TaskResult).filter(
                TaskResult.task_id == task_id,
                TaskResult.id.in_(multi_result["result_ids"])
            ).all()
            
            if not task_results:
                return {"success": False, "error": "未找到任务处理结果"}

        # 根据评议者数量选择评议方式
        if len(reviewers) == 1:
            # 单评议者模式
            return await self._single_reviewer_mode(task_id, reviewers[0], task_results)
        else:
            # 多评议者投票模式
            return await self._multiple_reviewer_vote_mode(task_id, reviewers, task_results)

    async def _single_reviewer_mode(self, task_id: int, reviewer: LlmConfig, 
                                 task_results: List[TaskResult]) -> Dict:
        """单评议者模式处理

        Args:
            task_id: 任务ID
            reviewer: 评议者LLM
            task_results: 所有处理结果

        Returns:
            评议结果字典
        """
        # 获取任务内容和评议提示模板
        with db.session_scope() as session:
            task = session.query(Task).filter_by(id=task_id).first()
            # 获取或创建评议prompt
            review_prompt = self._create_review_prompt(task_results)

        # 处理评议
        client = get_client_for_llm(reviewer)
        review_result = client.process_content(task.content, review_prompt)

        # 保存评议结果
        if review_result["success"]:
            with db.session_scope() as session:
                # 创建评议结果
                task_review_result = TaskResult(
                    task_id=task_id,
                    llm_id=reviewer.id,
                    raw_response=review_result["raw_response"],
                    processed_result=review_result.get("processed_result"),
                    bias_index=review_result["result"].get("bias_index"),
                    misleading_index=review_result["result"].get("misleading_index"),
                    hidden_intent_index=review_result["result"].get("hidden_intent_index"),
                    credibility_score=review_result["result"].get("credibility_score"),
                    is_review_result=True
                )
                session.add(task_review_result)
                session.flush()
                review_result["final_result_id"] = task_review_result.id

        return review_result

    async def _multiple_reviewer_vote_mode(self, task_id: int, reviewers: List[LlmConfig], 
                                        task_results: List[TaskResult]) -> Dict:
        """多评议者投票模式处理

        Args:
            task_id: 任务ID
            reviewers: 评议者LLM列表
            task_results: 所有处理结果

        Returns:
            投票结果字典
        """
        # 获取任务内容
        with db.session_scope() as session:
            task = session.query(Task).filter_by(id=task_id).first()
            # 获取投票提示模板
            vote_prompt = self._create_vote_prompt(task_results)

        # 并行处理所有评议者的投票
        votes = []
        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            vote_tasks = []
            for reviewer in reviewers:
                client = get_client_for_llm(reviewer)
                vote_func = lambda c=client: c.process_content(task.content, vote_prompt)
                vote_tasks.append(loop.run_in_executor(executor, vote_func))

            # 等待所有投票完成
            reviewer_votes = await asyncio.gather(*vote_tasks)
            votes = list(zip(reviewers, reviewer_votes))

        # 解析投票结果并统计
        vote_counts = {}
        for reviewer, vote_result in votes:
            if vote_result["success"]:
                # 解析投票，获取评议者选择的结果ID
                voted_result_id = self._parse_vote_result(vote_result["raw_response"], task_results)
                if voted_result_id:
                    vote_counts[voted_result_id] = vote_counts.get(voted_result_id, 0) + 1
                    
                    # 保存投票记录
                    with db.session_scope() as session:
                        reviewer_vote = ReviewerVote(
                            task_id=task_id,
                            reviewer_id=reviewer.id,
                            voted_result_id=voted_result_id,
                            comment=vote_result["raw_response"]
                        )
                        session.add(reviewer_vote)

        # 找出得票最多的结果
        if vote_counts:
            final_result_id = max(vote_counts.items(), key=lambda x: x[1])[0]
            # 获取最终结果
            with db.session_scope() as session:
                final_result = session.query(TaskResult).filter_by(id=final_result_id).first()
                
                if final_result:
                    return {
                        "success": True,
                        "final_result_id": final_result_id,
                        "vote_counts": vote_counts,
                        "votes": [v[1] for v in votes if v[1]["success"]],
                        "result": {
                            "bias_index": final_result.bias_index,
                            "misleading_index": final_result.misleading_index,
                            "hidden_intent_index": final_result.hidden_intent_index,
                            "credibility_score": final_result.credibility_score,
                            "raw_response": final_result.raw_response
                        }
                    }

        # 如果没有有效投票或平局，返回错误
        return {"success": False, "error": "未能确定最终结果，可能是投票失败或平局"}

    def _create_review_prompt(self, task_results: List[TaskResult]) -> str:
        """创建评议提示模板

        Args:
            task_results: 所有处理结果

        Returns:
            评议提示模板
        """
        # 创建包含所有结果的评议提示
        review_prompt = (
            "# 多LLM评估结果评议\n\n"
            "你的任务是评议多个LLM对同一篇文章的分析结果，综合它们的分析，给出最终的评估结果。\n\n"
            "## LLM评估结果\n\n"
        )

        # 添加每个LLM的评估结果
        for i, result in enumerate(task_results, 1):
            review_prompt += f"### LLM {i} 的评估结果\n\n"
            review_prompt += f"```\n{result.raw_response}\n```\n\n"

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

    def _create_vote_prompt(self, task_results: List[TaskResult]) -> str:
        """创建投票提示模板

        Args:
            task_results: 所有处理结果

        Returns:
            投票提示模板
        """
        # 创建包含所有结果的投票提示
        vote_prompt = (
            "# 多LLM评估结果投票\n\n"
            "你的任务是评估多个LLM对同一篇文章的分析结果，并投票选择最准确、最全面的分析结果。\n\n"
            "## LLM评估结果\n\n"
        )

        # 添加每个LLM的评估结果
        for i, result in enumerate(task_results, 1):
            vote_prompt += f"### LLM {i} (ID: {result.id}) 的评估结果\n\n"
            vote_prompt += f"```\n{result.raw_response}\n```\n\n"

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

    def _parse_vote_result(self, vote_text: str, task_results: List[TaskResult]) -> Optional[int]:
        """解析投票结果，获取选择的结果ID

        Args:
            vote_text: 投票文本
            task_results: 所有处理结果

        Returns:
            选择的结果ID，如果未能解析则返回None
        """
        try:
            # 解析投票文本，查找"ID: X"模式
            import re
            id_pattern = re.compile(r"ID:\s*(\d+)")
            match = id_pattern.search(vote_text)
            if match:
                voted_id = int(match.group(1))
                # 验证ID是否在结果列表中
                if any(result.id == voted_id for result in task_results):
                    return voted_id
            
            # 如果未找到ID格式，尝试查找"LLM X"格式
            llm_pattern = re.compile(r"LLM\s*(\d+)")
            match = llm_pattern.search(vote_text)
            if match:
                llm_index = int(match.group(1)) - 1  # 减1因为索引从0开始
                if 0 <= llm_index < len(task_results):
                    return task_results[llm_index].id
            
            return None
        except Exception:
            return None