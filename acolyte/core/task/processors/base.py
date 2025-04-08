"""
基础任务处理器

定义任务处理器的基础类和共享功能。
"""

import json
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from sqlalchemy.orm import Session

from acolyte.core.db.models import LlmConfig, Prompt, Task, TaskResult, TaskStatus
from acolyte.core.db.session import extract_model_data, run_in_session
from acolyte.core.prompt.manager import PromptManager
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class BaseTaskProcessor(ABC):
    """
    任务处理器基类

    提供任务处理的基础功能和共享方法。子类需要实现process方法。
    """

    def __init__(self):
        """初始化基础任务处理器"""
        self.prompt_manager = PromptManager()

    @abstractmethod
    async def process(self, task_id: int) -> Dict:
        """
        处理任务

        Args:
            task_id: 任务ID

        Returns:
            处理结果字典
        """
        pass

    async def _get_task_data(self, task_id: int) -> Optional[Dict]:
        """
        获取任务数据

        Args:
            task_id: 任务ID

        Returns:
            任务数据字典，如果不存在则返回None
        """

        async def _get_task(session: Session):
            task = session.query(Task).filter_by(id=task_id).first()
            if not task:
                return None
            return extract_model_data(task, include_relationships=False)

        try:
            return await run_in_session(_get_task)
        except Exception as e:
            logger.error(f"获取任务数据失败: ID={task_id}, 错误: {str(e)}", exc_info=True)
            return None

    async def _get_task_with_content(self, task_id: int) -> Optional[Dict]:
        """
        获取任务数据，包括内容

        Args:
            task_id: 任务ID

        Returns:
            任务数据字典，如果不存在则返回None
        """

        async def _get_task_content(session: Session):
            task = session.query(Task).filter_by(id=task_id).first()
            if not task:
                return None

            data = extract_model_data(task, include_relationships=False)
            # 确保包含内容
            data["content"] = task.content
            return data

        try:
            return await run_in_session(_get_task_content)
        except Exception as e:
            logger.error(f"获取任务内容失败: ID={task_id}, 错误: {str(e)}", exc_info=True)
            return None

    async def _get_prompt(
        self, prompt_id: Optional[int] = None, model_name: Optional[str] = None
    ) -> Optional[Dict]:
        """
        获取提示词

        Args:
            prompt_id: 指定的提示词ID
            model_name: 模型名称，用于获取特定模型的提示词

        Returns:
            提示词数据字典，如果不存在则返回None
        """

        async def _get_prompt_data(session: Session):
            prompt = None

            # 如果指定了提示词ID，尝试获取
            if prompt_id:
                prompt = session.query(Prompt).filter_by(id=prompt_id).first()
                if prompt:
                    logger.info(f"使用指定的提示词: ID={prompt.id}, 版本={prompt.version}")
                    data = extract_model_data(prompt, include_relationships=False)
                    # 确保包含content字段
                    if prompt.content and not data.get("content"):
                        data["content"] = prompt.content
                        logger.debug(f"提示词内容长度: {len(prompt.content)} 字符")
                    return data
                else:
                    logger.warning(f"未找到指定的提示词: ID={prompt_id}")

            # 尝试获取适用于特定模型的提示词
            if model_name:
                # 直接在当前会话中查询，避免使用prompt_manager
                model_prompt = (
                    session.query(Prompt)
                    .filter(Prompt.model_target == model_name, Prompt.is_active == True)
                    .order_by(Prompt.version.desc())
                    .first()
                )

                if model_prompt:
                    logger.info(
                        f"使用适用于模型 {model_name} 的提示词: ID={model_prompt.id}, 版本={model_prompt.version}"
                    )
                    data = extract_model_data(model_prompt, include_relationships=False)
                    # 确保包含content字段
                    if model_prompt.content and not data.get("content"):
                        data["content"] = model_prompt.content
                        logger.debug(f"提示词内容长度: {len(model_prompt.content)} 字符")
                    return data

            # 获取最新的活跃提示词
            prompt = (
                session.query(Prompt)
                .filter(Prompt.is_active == True)
                .order_by(Prompt.id.desc())
                .first()
            )

            if prompt:
                logger.info(f"使用最新的活跃提示词: ID={prompt.id}, 版本={prompt.version}")
                data = extract_model_data(prompt, include_relationships=False)
                # 确保包含content字段
                if prompt.content and not data.get("content"):
                    data["content"] = prompt.content
                    logger.debug(f"提示词内容长度: {len(prompt.content)} 字符")
                return data

            logger.warning("未找到任何活跃的提示词")

            # 尝试获取任何提示词
            any_prompt = session.query(Prompt).order_by(Prompt.id.desc()).first()
            if any_prompt:
                logger.info(
                    f"使用第一个可用的提示词: ID={any_prompt.id}, 版本={any_prompt.version}"
                )
                data = extract_model_data(any_prompt, include_relationships=False)
                # 确保包含content字段
                if any_prompt.content and not data.get("content"):
                    data["content"] = any_prompt.content
                    logger.debug(f"提示词内容长度: {len(any_prompt.content)} 字符")
                return data

            logger.error("数据库中没有任何提示词")
            return None

        try:
            return await run_in_session(_get_prompt_data)
        except Exception as e:
            logger.error(f"获取提示词失败: 错误: {str(e)}", exc_info=True)
            return None

    async def _get_llm(
        self, llm_id: Optional[int] = None, is_default: bool = False
    ) -> Optional[Dict]:
        """
        获取LLM配置

        Args:
            llm_id: 指定的LLM ID
            is_default: 是否获取默认LLM

        Returns:
            LLM配置数据字典，如果不存在则返回None
        """

        async def _get_llm_data(session: Session):
            llm = None

            # 如果指定了LLM ID，尝试获取
            if llm_id:
                llm = session.query(LlmConfig).filter_by(id=llm_id).first()
                if llm:
                    logger.info(
                        f"使用指定的LLM: ID={llm.id}, 名称={llm.name}, 模型={llm.model_name}"
                    )
                    return extract_model_data(llm, include_relationships=False)
                else:
                    logger.warning(f"未找到指定的LLM: ID={llm_id}")

            # 获取默认LLM
            if is_default:
                llm = session.query(LlmConfig).filter_by(is_default=True).first()
                if llm:
                    logger.info(f"使用默认LLM: ID={llm.id}, 名称={llm.name}, 模型={llm.model_name}")
                    return extract_model_data(llm, include_relationships=False)
                else:
                    logger.warning("未找到默认LLM")

            # 获取任何LLM
            any_llm = session.query(LlmConfig).order_by(LlmConfig.id.asc()).first()
            if any_llm:
                logger.info(
                    f"使用第一个可用的LLM: ID={any_llm.id}, 名称={any_llm.name}, 模型={any_llm.model_name}"
                )
                return extract_model_data(any_llm, include_relationships=False)

            logger.error("数据库中没有任何LLM配置")
            return None

        try:
            return await run_in_session(_get_llm_data)
        except Exception as e:
            logger.error(f"获取LLM配置失败: 错误: {str(e)}", exc_info=True)
            return None

    async def _get_llms_for_task(self, task_id: int) -> List[Dict]:
        """
        获取任务关联的LLM列表

        Args:
            task_id: 任务ID

        Returns:
            LLM配置数据字典列表
        """
        logger.debug(f"开始获取任务 {task_id} 关联的LLM列表")

        async def _get_llm_list(session: Session):
            # 获取任务
            task = session.query(Task).filter_by(id=task_id).first()
            if not task:
                logger.warning(f"任务不存在: ID={task_id}")
                return []

            logger.debug(
                f"找到任务: ID={task_id}, 处理模式={task.processing_mode.value if task.processing_mode else 'None'}, 状态={task.status.value if task.status else 'None'}"
            )

            # 获取关联的LLM
            task_llm_configs = list(task.llm_configs)
            logger.debug(f"任务 {task_id} 关联的LLM数量: {len(task_llm_configs)}")

            if task_llm_configs:
                logger.debug(f"任务关联的LLM IDs: {[llm.id for llm in task_llm_configs]}")
                logger.debug(f"任务关联的LLM名称: {[llm.name for llm in task_llm_configs]}")

            llms = []
            for llm_assoc in task_llm_configs:
                llm_data = extract_model_data(llm_assoc, include_relationships=False)
                llms.append(llm_data)
                logger.debug(
                    f"提取LLM数据: ID={llm_data.get('id')}, 名称={llm_data.get('name')}, 角色={llm_data.get('role')}"
                )

            if not llms:
                logger.debug(f"任务 {task_id} 没有关联的LLM，尝试获取默认角色的LLM")
                # 如果没有关联的LLM，获取所有普通角色的LLM
                normal_llms = session.query(LlmConfig).filter_by(role="normal").all()
                logger.debug(f"从数据库查询到 {len(normal_llms)} 个普通角色的LLM")

                if normal_llms:
                    logger.debug(f"普通角色LLM IDs: {[llm.id for llm in normal_llms]}")
                    logger.debug(f"普通角色LLM名称: {[llm.name for llm in normal_llms]}")

                    llms = []
                    for llm in normal_llms:
                        llm_data = extract_model_data(llm, include_relationships=False)
                        llms.append(llm_data)
                        logger.debug(
                            f"提取普通角色LLM数据: ID={llm_data.get('id')}, 名称={llm_data.get('name')}"
                        )

                    logger.info(f"找到 {len(llms)} 个普通角色的LLM")
                else:
                    logger.warning("未找到普通角色的LLM")

            logger.debug(f"最终返回 {len(llms)} 个LLM数据对象")
            if llms:
                logger.debug(f"返回LLM IDs: {[llm.get('id') for llm in llms]}")

            return llms

        try:
            result = await run_in_session(_get_llm_list)
            return result
        except Exception as e:
            logger.error(f"获取任务关联的LLM列表失败: ID={task_id}, 错误: {str(e)}", exc_info=True)
            return []

    async def _get_reviewers_for_task(self, task_id: int) -> List[Dict]:
        """
        获取任务关联的评议者LLM列表

        Args:
            task_id: 任务ID

        Returns:
            评议者LLM配置数据字典列表
        """

        async def _get_reviewer_list(session: Session):
            # 获取任务
            task = session.query(Task).filter_by(id=task_id).first()
            if not task:
                logger.warning(f"任务不存在: ID={task_id}")
                return []

            # 获取关联的评议者LLM
            reviewers = []
            for llm_assoc in task.llm_configs:
                if llm_assoc.role == "reviewer":
                    reviewers.append(extract_model_data(llm_assoc, include_relationships=False))

            if not reviewers:
                logger.debug(f"任务 {task_id} 没有关联的评议者LLM，尝试获取评议者角色的LLM")
                # 如果没有关联的评议者，获取所有评议者角色的LLM
                all_reviewers = session.query(LlmConfig).filter_by(role="reviewer").all()
                if all_reviewers:
                    reviewers = [
                        extract_model_data(rev, include_relationships=False)
                        for rev in all_reviewers
                    ]
                    logger.info(f"找到 {len(reviewers)} 个评议者角色的LLM")
                else:
                    logger.warning("未找到评议者角色的LLM")

            return reviewers

        try:
            return await run_in_session(_get_reviewer_list)
        except Exception as e:
            logger.error(
                f"获取任务关联的评议者列表失败: ID={task_id}, 错误: {str(e)}", exc_info=True
            )
            return []

    async def _save_result(
        self, task_id: int, llm_id: int, result: Dict, is_review_result: bool = False
    ) -> Optional[int]:
        """
        保存处理结果

        Args:
            task_id: 任务ID
            llm_id: LLM ID
            result: 处理结果
            is_review_result: 是否是评议结果

        Returns:
            结果ID，保存失败则返回None
        """

        async def _save_result_to_db(session: Session):
            import json  # 在函数内部导入json模块

            # 检查任务是否存在
            task = session.query(Task).filter_by(id=task_id).first()
            if not task:
                logger.warning(f"保存结果失败: 任务不存在, ID={task_id}")
                return None

            # 提取分析结果 - 兼容两种结构
            # 1. 直接从result中提取（适用于Gemini）
            # 2. 从result.get("result", {})中提取（适用于旧版本的Claude和OpenAI）
            result_data = result.get("result", {})

            # 首先尝试从result_data中提取
            bias_index = result_data.get("bias_index")
            misleading_index = result_data.get("misleading_index")
            hidden_intent_index = result_data.get("hidden_intent_index")
            credibility_score = result_data.get("credibility_score")

            # 如果从result_data中提取失败，尝试直接从result中提取
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

                # 如果直接从result中提取成功，记录日志
                if any([bias_index, misleading_index, hidden_intent_index, credibility_score]):
                    logger.debug(f"从result顶层提取评分成功: 任务ID={task_id}")

            # 记录提取到的评分
            logger.debug(
                f"从结果中提取评分: 任务ID={task_id}, BI={bias_index}, MI={misleading_index}, HI={hidden_intent_index}, CS={credibility_score}"
            )

            # 检查是否有缺失的评分
            missing_scores = []
            if bias_index is None:
                missing_scores.append("bias_index")
            if misleading_index is None:
                missing_scores.append("misleading_index")
            if hidden_intent_index is None:
                missing_scores.append("hidden_intent_index")
            if credibility_score is None:
                missing_scores.append("credibility_score")

            if missing_scores:
                logger.warning(
                    f"结果中缺失部分评分: 任务ID={task_id}, 缺失: {', '.join(missing_scores)}"
                )

            # 创建结果记录
            # 将字典转换为JSON字符串
            processed_result = result.get("processed_result", "")
            if isinstance(processed_result, dict):
                processed_result = json.dumps(processed_result)

            task_result = TaskResult(
                task_id=task_id,
                llm_id=llm_id,
                raw_response=result.get("raw_response", ""),
                processed_result=processed_result,
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
                task.updated_at = datetime.now(timezone.utc)

                if old_final_result_id:
                    logger.info(
                        f"更新任务最终结果: 任务ID={task_id}, 旧结果ID={old_final_result_id}, 新结果ID={task_result.id}"
                    )
                else:
                    logger.info(f"设置任务最终结果: 任务ID={task_id}, 结果ID={task_result.id}")

            return task_result.id

        try:
            return await run_in_session(_save_result_to_db)
        except Exception as e:
            logger.error(
                f"保存处理结果失败: 任务ID={task_id}, LLM ID={llm_id}, 错误: {str(e)}",
                exc_info=True,
            )
            return None

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

            old_status = task.status
            task.status = status
            task.updated_at = datetime.now(timezone.utc)
            logger.info(f"更新任务状态: 任务ID={task_id}, 旧状态={old_status}, 新状态={status}")
            return True

        try:
            return await run_in_session(_update_status)
        except Exception as e:
            logger.error(
                f"更新任务状态失败: ID={task_id}, 状态={status}, 错误: {str(e)}", exc_info=True
            )
            return False

    async def _handle_error(self, task_id: int, error: Union[str, Exception]) -> Dict:
        """
        处理错误

        Args:
            task_id: 任务ID
            error: 错误对象或错误消息

        Returns:
            错误结果字典
        """
        # 将错误转换为字符串
        error_msg = str(error)

        # 记录错误
        logger.error(f"任务处理错误: ID={task_id}, 错误: {error_msg}")
        if isinstance(error, Exception):
            logger.debug(f"错误详情: {traceback.format_exc()}")

        # 更新任务状态为失败
        await self._update_task_status(task_id, TaskStatus.FAILED)

        # 返回错误结果
        return {"success": False, "error": error_msg, "task_id": task_id}
