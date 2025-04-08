"""
LLM管理模块
"""

from typing import Dict, List, Optional

from acolyte.core.db.database import db
from acolyte.core.db.models import LlmConfig, LlmRole
from acolyte.utils.logging import get_logger

# 获取模块日志记录器
logger = get_logger("acolyte.core.llm.manager")


class LlmManager:
    """
    LLM管理器

    该类负责LLM配置的增删改查（CRUD）操作，包括添加、更新、删除和查询LLM配置。
    它还提供了设置默认LLM、更改LLM角色和测试LLM连接等功能。

    主要功能：
    - LLM配置管理：添加、更新、删除和查询LLM配置
    - 默认LLM管理：获取和设置默认LLM
    - LLM角色管理：更改LLM角色（普通评估者或评议者）
    - LLM连接测试：测试LLM配置的连通性

    与其他组件的关系：
    - 使用数据库会话进行数据存取
    - 使用LlmClient进行连接测试
    """

    def add_llm(
        self,
        name: str,
        api_key: str,
        base_url: str,
        model_name: str,
        description: str = None,
        role: LlmRole = LlmRole.NORMAL,
        is_default: bool = False,
    ) -> LlmConfig:
        """
        添加新的LLM配置

        该方法创建一个新的LLM配置并将其保存到数据库中。
        如果指定了is_default=True，则会将该LLM设置为默认LLM，
        并将其他所有LLM的默认状态设置为False。

        创建流程：
        1. 检查是否已存在同名的LLM配置
        2. 创建LlmConfig对象并设置属性
        3. 如果指定了is_default=True，则清除其他LLM的默认状态
        4. 将新配置保存到数据库
        5. 返回新创建的LlmConfig对象

        Args:
            name: LLM名称，必须唯一
            api_key: API密钥，用于认证
            base_url: 基础URL，如"https://api.anthropic.com"
            model_name: 模型名称，如"claude-3-opus-20240229"
            description: 描述信息，可选
            role: LLM角色，默认为普通评估者（NORMAL）
            is_default: 是否设置为默认LLM，默认为False

        Returns:
            LlmConfig: 新创建的LLM配置对象

        Raises:
            ValueError: 当已存在同名的LLM配置时抛出
        """
        logger.info(f"添加新的LLM配置: {name}, 模型: {model_name}")
        logger.debug(f"LLM角色: {role}, 是否默认: {is_default}")

        try:
            with db.session_scope() as session:
                # 如果设置为默认，先取消其他默认设置
                if is_default:
                    logger.debug("清除其他LLM的默认状态")
                    self._clear_default_status(session)

                # 创建新配置
                new_llm = LlmConfig(
                    name=name,
                    api_key=api_key,
                    base_url=base_url,
                    model_name=model_name,
                    description=description,
                    role=role,
                    is_default=is_default,
                )
                session.add(new_llm)
                session.flush()
                logger.info(f"LLM配置已创建: ID={new_llm.id}, 名称={new_llm.name}")
                return new_llm
        except Exception as e:
            logger.error(f"创建LLM配置失败: {str(e)}", exc_info=True)
            raise

    def update_llm(self, llm_id: int, **kwargs) -> Optional[LlmConfig]:
        """
        更新LLM配置

        该方法更新指定ID的LLM配置。可以更新一个或多个字段，
        包括名称、API密钥、基础URL、模型名称、描述、角色和默认状态等。
        如果更新了默认状态为True，则会将其他所有LLM的默认状态设置为False。

        更新流程：
        1. 查询指定ID的LLM配置
        2. 如果未找到，返回None
        3. 如果更新了默认状态为True，则清除其他LLM的默认状态
        4. 更新LLM配置的属性
        5. 返回更新后的LLM配置对象

        Args:
            llm_id: LLM配置ID
            **kwargs: 要更新的字段，可以包含以下字段：
                - name: LLM名称
                - api_key: API密钥
                - base_url: 基础URL
                - model_name: 模型名称
                - description: 描述
                - role: LLM角色
                - is_default: 是否为默认LLM

        Returns:
            Optional[LlmConfig]: 更新后的LLM配置对象，如果未找到则返回None
        """
        logger.info(f"更新LLM配置: ID={llm_id}")
        logger.debug(f"更新字段: {kwargs}")

        try:
            with db.session_scope() as session:
                llm = session.query(LlmConfig).filter_by(id=llm_id).first()
                if not llm:
                    logger.warning(f"LLM配置不存在: ID={llm_id}")
                    return None

                logger.debug(f"原始配置: 名称={llm.name}, 模型={llm.model_name}")

                # 如果要设置为默认，先取消其他默认设置
                if kwargs.get("is_default", False):
                    logger.debug("清除其他LLM的默认状态")
                    self._clear_default_status(session)

                # 更新字段
                for key, value in kwargs.items():
                    if hasattr(llm, key):
                        setattr(llm, key, value)

                logger.info(f"LLM配置更新成功: ID={llm_id}, 名称={llm.name}")
                return llm
        except Exception as e:
            logger.error(f"更新LLM配置失败: ID={llm_id}, 错误: {str(e)}", exc_info=True)
            raise

    def delete_llm(self, llm_id: int) -> bool:
        """删除LLM配置

        Args:
            llm_id: LLM配置ID

        Returns:
            删除是否成功
        """
        logger.info(f"删除LLM配置: ID={llm_id}")

        try:
            with db.session_scope() as session:
                llm = session.query(LlmConfig).filter_by(id=llm_id).first()
                if not llm:
                    logger.warning(f"LLM配置不存在: ID={llm_id}")
                    return False

                logger.debug(f"删除的LLM配置: 名称={llm.name}, 是否默认={llm.is_default}")

                # 检查是否为默认LLM
                if llm.is_default:
                    # 如果是唯一的LLM，允许删除
                    count = session.query(LlmConfig).count()
                    logger.debug(f"当前数据库中有 {count} 个LLM配置")

                    if count > 1:
                        # 如果删除的是默认LLM，需要设置新的默认LLM
                        logger.info("删除的是默认LLM，需要设置新的默认LLM")
                        new_default = (
                            session.query(LlmConfig).filter(LlmConfig.id != llm_id).first()
                        )
                        if new_default:
                            new_default.is_default = True
                            logger.info(
                                f"新的默认LLM: ID={new_default.id}, 名称={new_default.name}"
                            )

                # 处理与此LLM关联的任务结果
                from acolyte.core.db.models import TaskResult

                task_results = session.query(TaskResult).filter_by(llm_id=llm_id).count()
                logger.info(f"删除 {task_results} 个关联的任务结果")
                session.query(TaskResult).filter_by(llm_id=llm_id).delete()

                # 删除LLM配置
                session.delete(llm)
                logger.info(f"LLM配置删除成功: ID={llm_id}")
                return True
        except Exception as e:
            logger.error(f"删除LLM配置失败: ID={llm_id}, 错误: {str(e)}", exc_info=True)
            raise

    def get_llm(self, llm_id: int) -> Optional[LlmConfig]:
        """获取LLM配置

        Args:
            llm_id: LLM配置ID

        Returns:
            LLM配置对象，如果未找到则返回None
        """
        with db.session_scope() as session:
            return session.query(LlmConfig).filter_by(id=llm_id).first()

    def get_llm_by_name(self, name: str) -> Optional[LlmConfig]:
        """根据名称获取LLM配置

        Args:
            name: LLM名称

        Returns:
            LLM配置对象，如果未找到则返回None
        """
        with db.session_scope() as session:
            return session.query(LlmConfig).filter_by(name=name).first()

    def get_all_llms(self) -> List[LlmConfig]:
        """获取所有LLM配置

        Returns:
            所有LLM配置对象列表
        """
        with db.session_scope() as session:
            return session.query(LlmConfig).all()

    def get_default_llm(self) -> Optional[LlmConfig]:
        """获取默认LLM配置

        Returns:
            默认LLM配置对象，如果未设置则返回None
        """
        with db.session_scope() as session:
            return session.query(LlmConfig).filter_by(is_default=True).first()

    def get_reviewer_llms(self) -> List[LlmConfig]:
        """获取所有评议者角色的LLM配置

        Returns:
            评议者角色的LLM配置对象列表
        """
        with db.session_scope() as session:
            return session.query(LlmConfig).filter_by(role=LlmRole.REVIEWER).all()

    def set_as_default(self, llm_id: int) -> bool:
        """设置指定LLM为默认

        Args:
            llm_id: LLM配置ID

        Returns:
            设置是否成功
        """
        with db.session_scope() as session:
            llm = session.query(LlmConfig).filter_by(id=llm_id).first()
            if not llm:
                return False

            self._clear_default_status(session)
            llm.is_default = True
            return True

    def change_role(self, llm_id: int, role: LlmRole) -> bool:
        """更改LLM角色

        Args:
            llm_id: LLM配置ID
            role: 新角色

        Returns:
            更改是否成功
        """
        with db.session_scope() as session:
            llm = session.query(LlmConfig).filter_by(id=llm_id).first()
            if not llm:
                return False

            llm.role = role
            return True

    async def test_connection(
        self, llm_id: int = None, api_key: str = None, base_url: str = None, model_name: str = None
    ) -> Dict:
        """
        测试LLM连接

        该方法测试与LLM API的连接是否正常。它可以使用已保存的LLM配置（通过llm_id指定），
        或者使用临时提供的配置参数（api_key、base_url、model_name）。
        它会创建一个适合的LLM客户端，并调用其_test_connection方法测试连接。

        测试流程：
        1. 如果提供了llm_id，则从数据库中获取对应的LLM配置
        2. 如果提供了临时参数，则使用这些参数创建LlmConfig对象
        3. 根据LlmConfig对象创建LLM客户端
        4. 调用客户端的_test_connection方法测试连接
        5. 记录测试时间和结果
        6. 返回测试结果字典

        Args:
            llm_id: LLM配置ID，如果提供则使用已保存的配置
            api_key: API密钥，如果llm_id为None则必须提供
            base_url: 基础URL，如果llm_id为None则必须提供
            model_name: 模型名称，如果llm_id为None则必须提供

        Returns:
            Dict: 测试结果字典，包含以下字段：
                - success (bool): 测试是否成功
                - message (str): 成功或失败的消息
                - response_time (float, 可选): 成功时包含响应时间（毫秒）
                - error (str, 可选): 失败时包含错误信息
                - llm_type (str, 可选): 成功时包含LLM类型（如"anthropic"、"openai"等）
        """
        import asyncio
        import time

        from acolyte.core.llm.client import get_client_for_llm
        from acolyte.core.llm.providers.anthropic import AnthropicClient
        from acolyte.core.llm.providers.deepseek import DeepSeekClient
        from acolyte.core.llm.providers.gemini import GeminiClient
        from acolyte.core.llm.providers.ollama import OllamaClient
        from acolyte.core.llm.providers.openai import OpenAIClient

        try:
            # 记录测试类型
            if llm_id is not None:
                logger.info(f"测试已存在LLM连接: ID={llm_id}")
            else:
                logger.info("测试新的LLM连接参数")
                logger.debug(f"base_url: {base_url}, model_name: {model_name}")

            # 获取连接参数
            if llm_id is not None:
                llm_config = self.get_llm(llm_id)
                if not llm_config:
                    logger.warning(f"LLM配置不存在: ID={llm_id}")
                    return {"success": False, "message": "LLM配置不存在"}
                logger.debug(
                    f"使用现有LLM配置: 名称={llm_config.name}, 模型={llm_config.model_name}"
                )
            else:
                if not all([api_key, base_url, model_name]):
                    logger.error("测试连接参数不完整")
                    return {"success": False, "message": "连接参数不完整"}
                # 创建临时配置对象
                from acolyte.core.db.models import LlmConfig as LlmConfigModel

                llm_config = LlmConfigModel(
                    name="测试连接", api_key=api_key, base_url=base_url, model_name=model_name
                )

            # 创建对应的客户端
            logger.debug("获取适合的LLM客户端")
            client = get_client_for_llm(llm_config)

            # 开始测试连接
            logger.info(f"测试连接: {client.__class__.__name__}")
            start_time = time.time()

            # 执行实际的连接测试
            test_result = await client._test_connection()

            # 计算响应时间
            response_time = time.time() - start_time

            # 处理测试结果
            if test_result.get("success", False):
                logger.info(f"LLM连接测试成功: 耗时={response_time:.2f}秒")
                return {
                    "success": True,
                    "response_time": response_time,
                    "message": test_result.get("message", "连接测试成功"),
                }
            else:
                logger.warning(f"LLM连接测试失败: {test_result.get('message', '未知错误')}")
                return {
                    "success": False,
                    "response_time": response_time,
                    "message": test_result.get("message", "连接测试失败"),
                }

        except Exception as e:
            logger.error(f"测试LLM连接失败: {str(e)}", exc_info=True)
            return {"success": False, "message": f"连接测试失败: {str(e)}"}

    def _clear_default_status(self, session):
        """清除所有LLM的默认状态

        Args:
            session: 数据库会话
        """
        try:
            # 获取当前默认LLM的数量
            default_count = session.query(LlmConfig).filter_by(is_default=True).count()
            if default_count > 0:
                logger.debug(f"发现 {default_count} 个默认LLM，清除默认状态")
                session.query(LlmConfig).filter_by(is_default=True).update(
                    {LlmConfig.is_default: False}
                )
            else:
                logger.debug("未发现默认LLM")
        except Exception as e:
            logger.error(f"清除默认LLM状态失败: {str(e)}", exc_info=True)
            raise
