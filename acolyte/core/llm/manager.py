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
    """LLM管理器，负责LLM配置的CRUD操作"""

    def add_llm(self, name: str, api_key: str, base_url: str, model_name: str, 
                description: str = None, role: LlmRole = LlmRole.NORMAL, 
                is_default: bool = False) -> LlmConfig:
        """添加新的LLM配置

        Args:
            name: LLM名称
            api_key: API密钥
            base_url: 基础URL
            model_name: 模型名称
            description: 描述
            role: LLM角色
            is_default: 是否为默认LLM

        Returns:
            新创建的LLM配置对象
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
                    is_default=is_default
                )
                session.add(new_llm)
                session.flush()
                logger.info(f"LLM配置已创建: ID={new_llm.id}, 名称={new_llm.name}")
                return new_llm
        except Exception as e:
            logger.error(f"创建LLM配置失败: {str(e)}", exc_info=True)
            raise

    def update_llm(self, llm_id: int, **kwargs) -> Optional[LlmConfig]:
        """更新LLM配置

        Args:
            llm_id: LLM配置ID
            **kwargs: 要更新的字段

        Returns:
            更新后的LLM配置对象，如果未找到则返回None
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
                if kwargs.get('is_default', False):
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
                        new_default = session.query(LlmConfig).filter(
                            LlmConfig.id != llm_id
                        ).first()
                        if new_default:
                            new_default.is_default = True
                            logger.info(f"新的默认LLM: ID={new_default.id}, 名称={new_default.name}")
                
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

    async def test_connection(self, llm_id: int = None, api_key: str = None, 
                        base_url: str = None, model_name: str = None) -> Dict:
        """测试LLM连接

        Args:
            llm_id: LLM配置ID，如果提供则使用已保存的配置
            api_key: API密钥
            base_url: 基础URL
            model_name: 模型名称

        Returns:
            测试结果字典，包含是否成功、响应时间等信息
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
                    return {
                        'success': False,
                        'message': 'LLM配置不存在'
                    }
                logger.debug(f"使用现有LLM配置: 名称={llm_config.name}, 模型={llm_config.model_name}")
            else:
                if not all([api_key, base_url, model_name]):
                    logger.error("测试连接参数不完整")
                    return {
                        'success': False,
                        'message': '连接参数不完整'
                    }
                # 创建临时配置对象
                from acolyte.core.db.models import LlmConfig as LlmConfigModel
                llm_config = LlmConfigModel(
                    name="测试连接",
                    api_key=api_key,
                    base_url=base_url,
                    model_name=model_name
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
            if test_result.get('success', False):
                logger.info(f"LLM连接测试成功: 耗时={response_time:.2f}秒")
                return {
                    'success': True,
                    'response_time': response_time,
                    'message': test_result.get('message', '连接测试成功')
                }
            else:
                logger.warning(f"LLM连接测试失败: {test_result.get('message', '未知错误')}")
                return {
                    'success': False,
                    'response_time': response_time,
                    'message': test_result.get('message', '连接测试失败')
                }
                
        except Exception as e:
            logger.error(f"测试LLM连接失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'连接测试失败: {str(e)}'
            }

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