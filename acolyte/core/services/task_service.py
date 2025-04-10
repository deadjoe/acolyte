"""
任务服务

处理任务创建、处理和查询的业务逻辑，作为API路由和任务处理器之间的中间层。
"""

import asyncio
import time
import traceback
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from acolyte.core.db.models import LlmConfig, LlmRole, ProcessingMode, ReviewerVote, Task, TaskResult, TaskStatus
from acolyte.core.db.session import extract_model_data, run_in_session
from acolyte.core.prompt.manager import PromptManager
from acolyte.core.task.processor import TaskProcessor
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class TaskService:
    """
    任务服务类

    该服务类提供任务相关的业务逻辑实现，包括任务的创建、处理、查询和管理等功能。
    它作为API路由和任务处理器之间的中间层，封装了数据库操作和任务处理的复杂性。

    主要功能：
    - 任务创建：创建新的分析任务，可指定处理模式、LLM和提示词
    - 任务处理：异步处理任务，支持单个LLM、多个LLM和评议模式
    - 任务查询：获取任务列表、任务详情和处理结果
    - 任务管理：取消任务、删除任务等

    与其他组件的关系：
    - 使用TaskProcessor进行任务处理
    - 使用PromptManager管理提示词模板
    - 使用数据库会话进行数据存取
    """

    def __init__(self):
        """
        初始化任务服务

        初始化TaskService实例，创建TaskProcessor实例用于处理任务，
        创建PromptManager实例用于管理提示词模板。
        """
        self.processor = TaskProcessor()
        self.prompt_manager = PromptManager()

    async def create_task(self, task_data: Dict) -> Dict:
        """
        创建任务

        该方法创建一个新的分析任务并将其保存到数据库中。它验证输入数据，
        创建Task对象，并可选地将任务与指定的LLM关联。

        创建流程：
        1. 验证输入数据（内容、处理模式等必要字段）
        2. 调用_create_task_in_db方法在数据库中创建Task对象
        3. 如果指定了wait=True，立即开始处理任务
        4. 返回创建的任务信息

        支持的处理模式：
        - single: 使用单个LLM处理任务
        - multiple: 使用多个LLM并行处理任务
        - review: 使用多个LLM处理任务，然后进行评议

        Args:
            task_data: 任务数据字典，包含以下字段：
                - content: 要分析的文本内容
                - processing_mode: 处理模式（single、multiple或review）
                - prompt_id: 提示词模板ID（可选）
                - llm_ids: 要使用的LLM ID列表（可选）
                - wait: 是否等待任务处理完成（可选，默认为False）

        Returns:
            Dict: 创建的任务信息字典，包含以下字段：
                - success (bool): 创建是否成功
                - task_id (int): 任务ID
                - processing_mode (str): 处理模式
                - status (str): 任务状态
                - result (Dict, 可选): 如果wait=True且处理成功，包含处理结果
                - error (str, 可选): 如果创建或处理失败，包含错误信息
        """
        logger.info(f"创建新任务，处理模式: {task_data.get('processing_mode')}")

        # 提取任务数据
        content = task_data.get("content")
        processing_mode = task_data.get("processing_mode")
        prompt_id = task_data.get("prompt_id")
        llm_ids = task_data.get("llm_ids", [])

        if not content:
            logger.error("任务内容不能为空")
            return {"error": "任务内容不能为空", "success": False}

        if not processing_mode:
            logger.error("处理模式不能为空")
            return {"error": "处理模式不能为空", "success": False}

        # 转换处理模式字符串为枚举
        try:
            if isinstance(processing_mode, str):
                processing_mode_enum = ProcessingMode(processing_mode)
            else:
                processing_mode_enum = processing_mode
        except ValueError:
            logger.error(f"无效的处理模式: {processing_mode}")
            return {"error": f"无效的处理模式: {processing_mode}", "success": False}

        # 在会话中创建任务
        try:
            task_id = await self._create_task_in_db(
                content, processing_mode_enum, prompt_id, llm_ids
            )

            if not task_id:
                return {"error": "创建任务失败", "success": False}

            # 启动异步处理
            task = await self._get_task(task_id)
            if not task:
                return {"error": "获取创建的任务失败", "success": False}

            # 异步处理任务
            asyncio.create_task(self.process_task_async(task_id))

            return {"id": task_id, **task, "success": True}
        except Exception as e:
            logger.error(f"创建任务时发生错误: {str(e)}", exc_info=True)
            return {"error": f"创建任务失败: {str(e)}", "success": False}

    async def _create_task_in_db(
        self,
        content: str,
        processing_mode: ProcessingMode,
        prompt_id: Optional[int] = None,
        llm_ids: Optional[List[int]] = None,
    ) -> Optional[int]:
        """
        在数据库中创建任务

        Args:
            content: 任务内容
            processing_mode: 处理模式
            prompt_id: 提示词ID
            llm_ids: LLM ID列表

        Returns:
            创建的任务ID，创建失败则返回None
        """

        async def _create_task(session: Session):
            # 创建任务对象
            new_task = Task(
                content=content,
                processing_mode=processing_mode,
                prompt_id=prompt_id,
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow(),
            )
            session.add(new_task)
            session.flush()
            task_id = new_task.id

            # 记录new_task创建后llm_configs的初始状态
            initial_llm_configs = list(new_task.llm_configs)
            logger.debug(f"任务 {task_id} 创建后的初始LLM关联数量: {len(initial_llm_configs)}")
            if initial_llm_configs:
                logger.debug(f"初始关联的LLM IDs: {[llm.id for llm in initial_llm_configs]}")
                logger.debug(f"初始关联的LLM名称: {[llm.name for llm in initial_llm_configs]}")

            # 清空初始关联的LLM
            initial_llm_count = len(new_task.llm_configs)
            if initial_llm_count > 0:
                logger.debug(f"清空初始关联的LLM，数量: {initial_llm_count}")
                logger.debug(f"清空前关联的LLM IDs: {[llm.id for llm in new_task.llm_configs]}")
                new_task.llm_configs = []
                logger.debug(f"清空后关联的LLM数量: {len(new_task.llm_configs)}")

            # 如果指定了LLM，关联任务与指定的LLM
            if llm_ids:
                # 去除重复的LLM ID
                unique_llm_ids = list(set(llm_ids))
                logger.debug(f"关联LLM(去重后): {unique_llm_ids}")

                # 查询数据库获取LLM对象
                llms = session.query(LlmConfig).filter(LlmConfig.id.in_(unique_llm_ids)).all()
                logger.debug(f"从数据库查询到 {len(llms)} 个LLM对象")
                if llms:
                    logger.debug(f"查询到的LLM IDs: {[llm.id for llm in llms]}")
                    logger.debug(f"查询到的LLM名称: {[llm.name for llm in llms]}")

                if len(llms) != len(unique_llm_ids):
                    missing_ids = set(unique_llm_ids) - set(llm.id for llm in llms)
                    logger.warning(
                        f"请求的LLM数量 ({len(unique_llm_ids)}) 与找到的LLM数量 ({len(llms)}) 不匹配"
                    )
                    logger.warning(f"未找到的LLM IDs: {missing_ids}")
            else:
                # 如果没有指定llm_ids，获取所有normal角色的LLM
                logger.debug(f"未指定LLM IDs，获取所有normal角色的LLM")

                # 查询数据库获取所有normal角色的LLM
                llms = session.query(LlmConfig).filter_by(role=LlmRole.NORMAL).all()
                logger.debug(f"从数据库查询到 {len(llms)} 个normal角色的LLM")

                if llms:
                    logger.debug(f"查询到的normal角色LLM IDs: {[llm.id for llm in llms]}")
                    logger.debug(f"查询到的normal角色LLM名称: {[llm.name for llm in llms]}")
                else:
                    logger.warning("未找到任何normal角色的LLM")

            # 直接设置llm_configs，而不是使用extend
            new_task.llm_configs = llms if 'llms' in locals() and llms else []
            logger.debug(f"直接设置LLM关联，数量: {len(new_task.llm_configs)}")
            if new_task.llm_configs:
                logger.debug(f"设置的LLM IDs: {[llm.id for llm in new_task.llm_configs]}")

            # 记录最终的llm_configs状态
            final_llm_configs = list(new_task.llm_configs)
            logger.debug(f"最终LLM关联数量: {len(final_llm_configs)}")
            if final_llm_configs:
                logger.debug(f"最终关联的LLM IDs: {[llm.id for llm in final_llm_configs]}")

            logger.debug(f"成功关联 {len(new_task.llm_configs)} 个LLM")

            return task_id

        try:
            return await run_in_session(_create_task)
        except Exception as e:
            logger.error(f"在数据库中创建任务失败: {str(e)}", exc_info=True)
            return None

    async def get_task(self, task_id: int) -> Dict:
        """
        获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务信息字典
        """
        logger.info(f"获取任务信息: ID={task_id}")
        try:
            task = await self._get_task(task_id)
            if not task:
                logger.warning(f"任务不存在: ID={task_id}")
                return {"error": "任务不存在", "success": False}
            return {**task, "success": True}
        except Exception as e:
            logger.error(f"获取任务失败: {str(e)}", exc_info=True)
            return {"error": f"获取任务失败: {str(e)}", "success": False}

    async def _get_task(self, task_id: int) -> Optional[Dict]:
        """
        从数据库获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务信息字典，如果不存在则返回None
        """

        async def _get_task_data(session: Session):
            task = session.query(Task).filter_by(id=task_id).first()
            if not task:
                return None
            return extract_model_data(task)

        try:
            return await run_in_session(_get_task_data)
        except Exception as e:
            logger.error(f"从数据库获取任务信息失败: {str(e)}", exc_info=True)
            return None

    async def get_task_results(self, task_id: int, include_raw_response: bool = False) -> Dict:
        """
        获取任务结果

        Args:
            task_id: 任务ID
            include_raw_response: 是否包含原始响应

        Returns:
            任务结果字典
        """
        logger.info(f"获取任务结果: ID={task_id}, 包含原始响应={include_raw_response}")

        async def _get_results(session: Session):
            task = session.query(Task).filter_by(id=task_id).first()
            if not task:
                return None

            results = session.query(TaskResult).filter(TaskResult.task_id == task_id).all()

            # 检查是否有缺失指标
            for idx, result in enumerate(results):
                missing_metrics = []
                if result.bias_index is None:
                    missing_metrics.append("bias_index")
                if result.misleading_index is None:
                    missing_metrics.append("misleading_index")
                if result.hidden_intent_index is None:
                    missing_metrics.append("hidden_intent_index")
                if result.credibility_score is None:
                    missing_metrics.append("credibility_score")

                if missing_metrics:
                    logger.warning(
                        f"任务结果 #{idx+1} (ID={result.id}) 缺少以下指标: {', '.join(missing_metrics)}"
                    )

            return [r.to_dict(include_raw_response=include_raw_response) for r in results]

        try:
            results = await run_in_session(_get_results)
            if results is None:
                return {"error": "任务不存在", "success": False}
            return {"results": results, "success": True}
        except Exception as e:
            logger.error(f"获取任务结果失败: {str(e)}", exc_info=True)
            return {"error": f"获取任务结果失败: {str(e)}", "success": False}

    async def get_task_votes(self, task_id: int, include_raw_response: bool = False) -> Dict:
        """
        获取任务的评议者投票信息

        Args:
            task_id: 任务ID
            include_raw_response: 是否包含原始响应

        Returns:
            投票信息字典
        """
        logger.info(f"获取任务投票信息: ID={task_id}, 包含原始响应={include_raw_response}")

        async def _get_votes(session: Session):
            task = session.query(Task).filter_by(id=task_id).first()
            if not task:
                return None

            # 获取投票记录
            votes_query = (
                session.query(
                    ReviewerVote,
                    LlmConfig.name.label("reviewer_name")
                )
                .join(LlmConfig, ReviewerVote.reviewer_id == LlmConfig.id)
                .filter(ReviewerVote.task_id == task_id)
            )

            votes = votes_query.all()

            # 转换为字典列表
            vote_list = []
            for vote, reviewer_name in votes:
                vote_dict = {
                    "id": vote.id,
                    "task_id": vote.task_id,
                    "reviewer_id": vote.reviewer_id,
                    "reviewer_name": reviewer_name,
                    "voted_result_id": vote.voted_result_id,
                    "created_at": vote.created_at.isoformat() if vote.created_at else None,
                }
                if include_raw_response and hasattr(vote, "raw_response"):
                    vote_dict["raw_response"] = vote.raw_response

                vote_list.append(vote_dict)

            return vote_list

        try:
            votes = await run_in_session(_get_votes)
            if votes is None:
                return {"error": "任务不存在", "success": False}
            return {"votes": votes, "success": True}
        except Exception as e:
            logger.error(f"获取任务投票信息失败: {str(e)}", exc_info=True)
            return {"error": f"获取任务投票信息失败: {str(e)}", "success": False}

    async def process_task_async(self, task_id: int) -> Dict:
        """
        异步处理任务

        Args:
            task_id: 任务ID

        Returns:
            处理结果
        """
        logger.info(f"开始异步处理任务 {task_id}")
        start_time = time.time()

        try:
            # 更新任务状态为处理中
            await self._update_task_status(task_id, TaskStatus.PROCESSING)

            # 使用任务处理器处理任务
            result = await self.processor.process_task(task_id)

            # 处理完成后记录时间
            elapsed_time = time.time() - start_time
            logger.info(
                f"任务处理完成: ID={task_id}, 耗时={elapsed_time:.2f}秒, 结果: {result.get('success', False)}"
            )

            return result
        except Exception as e:
            # 处理异常
            elapsed_time = time.time() - start_time
            error_msg = str(e)
            logger.error(
                f"任务处理异常: ID={task_id}, 耗时={elapsed_time:.2f}秒, 错误: {error_msg}"
            )
            logger.debug(f"异常详情: {traceback.format_exc()}")

            # 更新任务状态为失败
            await self._update_task_status(task_id, TaskStatus.FAILED)

            return {"success": False, "error": f"处理任务时发生异常: {error_msg}"}

    async def _update_task_status(self, task_id: int, status: TaskStatus) -> bool:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态

        Returns:
            更新是否成功
        """

        async def _update_status(session: Session):
            task = session.query(Task).filter_by(id=task_id).first()
            if not task:
                logger.warning(f"更新状态失败: 任务不存在, ID={task_id}")
                return False

            task.status = status
            task.updated_at = datetime.utcnow()
            return True

        try:
            return await run_in_session(_update_status)
        except Exception as e:
            logger.error(
                f"更新任务状态失败: ID={task_id}, 状态={status}, 错误: {str(e)}", exc_info=True
            )
            return False

    async def get_tasks(
        self, status: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> Dict:
        """
        获取任务列表

        Args:
            status: 过滤的任务状态
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            任务列表
        """
        logger.info(f"获取任务列表: 状态筛选={status}, 跳过={skip}, 限制={limit}")

        async def _get_tasks(session: Session):
            query = session.query(Task)

            # 如果指定了状态，进行筛选
            if status:
                try:
                    status_enum = TaskStatus(status)
                    query = query.filter(Task.status == status_enum)
                except ValueError:
                    logger.warning(f"无效的任务状态值: {status}")
                    return []

            # 获取分页结果
            results = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
            logger.debug(f"找到 {len(results)} 个任务")

            return [task.to_dict() for task in results]

        try:
            tasks = await run_in_session(_get_tasks)
            return {"tasks": tasks, "total": len(tasks), "success": True}
        except Exception as e:
            logger.error(f"获取任务列表失败: {str(e)}", exc_info=True)
            return {"error": f"获取任务列表失败: {str(e)}", "success": False}

    async def delete_task(self, task_id: int) -> Dict:
        """
        删除任务

        Args:
            task_id: 任务ID

        Returns:
            删除结果
        """
        logger.info(f"删除任务: ID={task_id}")

        async def _delete_task(session: Session):
            # 检查任务是否存在
            task = session.query(Task).filter_by(id=task_id).first()
            if not task:
                return False

            # 先清除任务与LLM的关联
            if task.llm_configs:
                logger.debug(f"清除任务与LLM的关联, 数量: {len(task.llm_configs)}")
                task.llm_configs = []

            # 删除关联的评审投票
            from acolyte.core.db.models import ReviewerVote
            vote_count = session.query(ReviewerVote).filter_by(task_id=task_id).delete()
            logger.debug(f"已删除 {vote_count} 个关联评审投票")

            # 删除关联的任务结果
            result_count = session.query(TaskResult).filter_by(task_id=task_id).delete()
            logger.debug(f"已删除 {result_count} 个关联结果")

            # 删除任务
            session.delete(task)
            return True

        try:
            success = await run_in_session(_delete_task)
            if not success:
                return {"error": "任务不存在", "success": False}
            return {"message": f"任务 {task_id} 已删除", "success": True}
        except Exception as e:
            logger.error(f"删除任务失败: ID={task_id}, 错误: {str(e)}", exc_info=True)
            return {"error": f"删除任务失败: {str(e)}", "success": False}

    async def clear_tasks(self, status: Optional[str] = None) -> Dict:
        """
        清空任务

        Args:
            status: 可选的状态筛选

        Returns:
            清空结果
        """
        logger.info(f"清空任务, 状态筛选: {status}")

        async def _clear_tasks(session: Session):
            # 创建任务查询
            task_query = session.query(Task)

            # 如果指定了状态，先筛选
            if status:
                try:
                    status_enum = TaskStatus(status)
                    task_query = task_query.filter(Task.status == status_enum)
                except ValueError:
                    return {"error": f"无效的任务状态: {status}", "count": 0}

            # 获取要删除的任务ID列表
            task_ids = [task.id for task in task_query.all()]

            # 如果没有任务，直接返回
            if not task_ids:
                return {"message": "没有找到需要删除的任务", "count": 0}

            # 先删除关联的任务结果
            result_count = (
                session.query(TaskResult).filter(TaskResult.task_id.in_(task_ids)).delete()
            )

            # 然后删除任务
            task_count = task_query.delete()

            return {
                "message": f"已清空{task_count}个任务和{result_count}个任务结果",
                "count": task_count,
            }

        try:
            result = await run_in_session(_clear_tasks)
            return {**result, "success": True}
        except Exception as e:
            logger.error(f"清空任务失败: {str(e)}", exc_info=True)
            return {"error": f"清空任务失败: {str(e)}", "success": False}
