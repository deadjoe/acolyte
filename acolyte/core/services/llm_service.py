"""
LLM服务

处理LLM配置管理和使用的业务逻辑，作为API路由和LLM客户端之间的中间层。
"""

import time
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from acolyte.core.db.models import LlmConfig, LlmRole
from acolyte.core.db.session import extract_model_data, run_in_session
from acolyte.core.llm.client import get_client_for_llm
from acolyte.core.llm.manager import LlmManager
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class LlmService:
    """
    LLM服务类

    该服务类提供LLM相关的业务逻辑实现，包括LLM配置的创建、查询、更新、删除等管理功能，
    以及使用LLM处理内容的功能。它作为API路由和LLM客户端之间的中间层，封装了数据库操作和LLM调用的复杂性。

    主要功能：
    - LLM配置管理：创建、查询、更新、删除LLM配置
    - LLM内容处理：使用LLM处理文本内容
    - LLM测试：测试LLM配置的连通性和可用性
    - LLM管理：获取默认LLM、设置默认LLM等

    与其他组件的关系：
    - 使用LlmManager进行内存中的LLM配置管理
    - 使用SessionManager进行数据库会话管理
    - 使用get_client_for_llm获取适合的LLM客户端
    """

    def __init__(self):
        """
        初始化LLM服务

        初始化LlmService实例，创建LlmManager实例用于管理内存中的LLM配置。
        LlmManager负责缓存默认LLM和其他常用的LLM配置，提高访问效率。
        """
        self.llm_manager = LlmManager()

    async def add_llm(self, llm_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        添加LLM配置

        该方法将新的LLM配置添加到数据库中。它首先验证输入数据，然后创建LlmConfig对象并保存到数据库。
        如果配置中指定了该LLM为默认LLM，还会更新默认LLM设置。

        添加流程：
        1. 验证输入数据（名称、API密钥等必要字段）
        2. 创建LlmConfig对象并设置属性
        3. 将对象保存到数据库
        4. 如果指定为默认LLM，更新默认LLM设置
        5. 刷新LlmManager中的缓存
        6. 返回新添加的LLM配置信息

        Args:
            llm_data: LLM配置数据字典，包含名称、API密钥、基础URL、模型名称等信息

        Returns:
            Dict: 添加的LLM配置信息字典，包含id、名称等字段

        Raises:
            ValueError: 当输入数据不完整或无效时抛出
        """
        logger.info(f"添加LLM配置: {llm_data.get('name')}")

        try:
            # 提取LLM数据
            name = llm_data.get("name")
            api_key = llm_data.get("api_key")
            base_url = llm_data.get("base_url")
            model_name = llm_data.get("model_name")
            description = llm_data.get("description")
            role = llm_data.get("role", LlmRole.NORMAL)
            is_default = llm_data.get("is_default", False)

            # 验证必要字段
            if not name or not api_key or not base_url or not model_name:
                logger.error("添加LLM配置失败: 缺少必要字段")
                return {"error": "缺少必要字段", "success": False}

            # 使用LLM管理器添加LLM
            if isinstance(role, str):
                try:
                    role = LlmRole(role)
                except ValueError:
                    logger.error(f"无效的LLM角色: {role}")
                    return {"error": f"无效的LLM角色: {role}", "success": False}

            new_llm = self.llm_manager.add_llm(
                name=name,
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                description=description,
                role=role,
                is_default=is_default,
            )

            if not new_llm:
                return {"error": "添加LLM配置失败", "success": False}

            return {**extract_model_data(new_llm), "success": True}

        except Exception as e:
            logger.error(f"添加LLM配置失败: {str(e)}", exc_info=True)
            return {"error": f"添加LLM配置失败: {str(e)}", "success": False}

    async def get_llms(self, role: Optional[str] = None, is_default: Optional[bool] = None) -> Dict[str, Any]:
        """
        获取LLM配置列表

        Args:
            role: 筛选的LLM角色
            is_default: 是否只返回默认LLM

        Returns:
            LLM配置列表
        """
        logger.info(f"获取LLM配置列表: 角色={role}, 是否默认={is_default}")

        async def _get_llms(session: Session):
            query = session.query(LlmConfig)

            # 应用筛选条件
            if role is not None:
                try:
                    role_enum = LlmRole(role)
                    query = query.filter(LlmConfig.role == role_enum)
                except ValueError:
                    logger.warning(f"无效的LLM角色值: {role}")
                    return []

            if is_default is not None:
                query = query.filter(LlmConfig.is_default == is_default)

            # 执行查询
            results = query.all()

            return [item.to_dict() for item in results]

        try:
            llms = await run_in_session(_get_llms)
            return {"llms": llms, "count": len(llms), "success": True}
        except Exception as e:
            logger.error(f"获取LLM配置列表失败: {str(e)}", exc_info=True)
            return {"error": f"获取LLM配置列表失败: {str(e)}", "success": False}

    async def get_llm(self, llm_id: int) -> Dict[str, Any]:
        """
        获取特定LLM配置

        Args:
            llm_id: LLM配置ID

        Returns:
            LLM配置信息
        """
        logger.info(f"获取LLM配置: ID={llm_id}")

        async def _get_llm(session: Session):
            llm = session.query(LlmConfig).filter(LlmConfig.id == llm_id).first()
            if not llm:
                return None
            return extract_model_data(llm)

        try:
            llm = await run_in_session(_get_llm)
            if not llm:
                return {"error": "LLM配置不存在", "success": False}
            return {**llm, "success": True}
        except Exception as e:
            logger.error(f"获取LLM配置失败: {str(e)}", exc_info=True)
            return {"error": f"获取LLM配置失败: {str(e)}", "success": False}

    async def update_llm(self, llm_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新LLM配置

        Args:
            llm_id: LLM配置ID
            update_data: 更新数据

        Returns:
            更新后的LLM配置信息
        """
        logger.info(f"更新LLM配置: ID={llm_id}")

        try:
            # 处理role字段，如果存在
            if "role" in update_data and isinstance(update_data["role"], str):
                try:
                    update_data["role"] = LlmRole(update_data["role"])
                except ValueError:
                    logger.error(f"无效的LLM角色: {update_data['role']}")
                    return {"error": f"无效的LLM角色: {update_data['role']}", "success": False}

            # 使用LLM管理器更新LLM
            updated_llm = self.llm_manager.update_llm(llm_id, **update_data)

            if not updated_llm:
                return {"error": "LLM配置不存在", "success": False}

            return {**extract_model_data(updated_llm), "success": True}

        except Exception as e:
            logger.error(f"更新LLM配置失败: {str(e)}", exc_info=True)
            return {"error": f"更新LLM配置失败: {str(e)}", "success": False}

    async def delete_llm(self, llm_id: int) -> Dict:
        """
        删除LLM配置

        Args:
            llm_id: LLM配置ID

        Returns:
            删除结果
        """
        logger.info(f"删除LLM配置: ID={llm_id}")

        try:
            # 使用LLM管理器删除LLM
            success = self.llm_manager.delete_llm(llm_id)

            if not success:
                return {"error": "LLM配置不存在", "success": False}

            return {"message": "LLM配置已删除", "success": True}

        except Exception as e:
            logger.error(f"删除LLM配置失败: {str(e)}", exc_info=True)
            return {"error": f"删除LLM配置失败: {str(e)}", "success": False}

    async def test_connection(self, llm_id: int) -> Dict[str, Any]:
        """
        测试LLM连接

        Args:
            llm_id: LLM配置ID

        Returns:
            测试结果
        """
        logger.info(f"测试LLM连接: ID={llm_id}")

        try:
            # 获取LLM配置
            async def _get_llm(session: Session):
                return session.query(LlmConfig).filter_by(id=llm_id).first()

            llm_config = await run_in_session(_get_llm)
            if not llm_config:
                logger.warning(f"LLM配置不存在: ID={llm_id}")
                return {"success": False, "message": "LLM配置不存在"}

            # 创建LLM客户端
            from acolyte.core.llm.client import get_client_for_llm

            client = get_client_for_llm(llm_config)

            # 测试连接
            result = await client._test_connection()

            logger.info(f"LLM连接测试结果: ID={llm_id}, 成功={result.get('success', False)}")
            return result

        except Exception as e:
            logger.error(f"LLM连接测试失败: {str(e)}", exc_info=True)
            return {"success": False, "message": f"连接测试失败: {str(e)}"}

    async def process_content(self, llm_id: int, content: str, prompt: str) -> Dict[str, Any]:
        """
        使用特定LLM处理内容

        Args:
            llm_id: LLM配置ID
            content: 要处理的内容
            prompt: 提示词

        Returns:
            处理结果
        """
        logger.info(f"使用LLM处理内容: LLM ID={llm_id}, 内容长度={len(content)}字符")

        async def _get_llm(session: Session):
            return session.query(LlmConfig).filter(LlmConfig.id == llm_id).first()

        try:
            # 获取LLM配置
            llm_config = await run_in_session(_get_llm)

            if not llm_config:
                logger.warning(f"LLM配置不存在: ID={llm_id}")
                return {"error": "LLM配置不存在", "success": False}

            # 获取LLM客户端
            client = get_client_for_llm(llm_config)

            # 处理内容
            start_time = time.time()
            result = await client.process_content(content=content, prompt=prompt)
            elapsed_time = time.time() - start_time

            # 记录处理结果
            if result.get("success", False):
                logger.info(f"内容处理成功: LLM={llm_config.name}, 耗时={elapsed_time:.2f}秒")

                # 添加处理时间
                if isinstance(result.get("result"), dict):
                    result["result"]["processing_time"] = elapsed_time

                # 记录评分结果
                scores = result.get("result", {})
                logger.info(
                    f"评分结果: "
                    f"BI={scores.get('bias_index')}, "
                    f"MI={scores.get('misleading_index')}, "
                    f"HI={scores.get('hidden_intent_index')}, "
                    f"CS={scores.get('credibility_score')}"
                )
            else:
                logger.warning(f"内容处理失败: {result.get('error', '未知错误')}")

            return result

        except Exception as e:
            logger.error(f"使用LLM处理内容失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"处理内容失败: {str(e)}",
                "raw_response": None,
                "result": {},
            }

    async def set_default_llm(self, llm_id: int) -> Dict:
        """
        设置指定LLM为默认

        Args:
            llm_id: LLM配置ID

        Returns:
            设置结果
        """
        logger.info(f"设置默认LLM: ID={llm_id}")

        try:
            # 使用LLM管理器设置默认LLM
            success = self.llm_manager.set_as_default(llm_id)

            if not success:
                logger.warning(f"设置默认LLM失败: LLM不存在, ID={llm_id}")
                return {"error": f"LLM配置不存在: ID={llm_id}", "success": False}

            # 获取更新后的LLM信息
            llm = await self.get_llm(llm_id)

            if not llm.get("success", False):
                return {"error": "获取LLM信息失败", "success": False}

            return {**llm, "success": True}

        except Exception as e:
            logger.error(f"设置默认LLM失败: {str(e)}", exc_info=True)
            return {"error": f"设置默认LLM失败: {str(e)}", "success": False}
