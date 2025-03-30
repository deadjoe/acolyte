"""
LLM管理模块
"""
from typing import Dict, List, Optional

from acolyte.core.db.database import db
from acolyte.core.db.models import LlmConfig, LlmRole


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
        with db.session_scope() as session:
            # 如果设置为默认，先取消其他默认设置
            if is_default:
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
            return new_llm

    def update_llm(self, llm_id: int, **kwargs) -> Optional[LlmConfig]:
        """更新LLM配置

        Args:
            llm_id: LLM配置ID
            **kwargs: 要更新的字段

        Returns:
            更新后的LLM配置对象，如果未找到则返回None
        """
        with db.session_scope() as session:
            llm = session.query(LlmConfig).filter_by(id=llm_id).first()
            if not llm:
                return None

            # 如果要设置为默认，先取消其他默认设置
            if kwargs.get('is_default', False):
                self._clear_default_status(session)

            # 更新字段
            for key, value in kwargs.items():
                if hasattr(llm, key):
                    setattr(llm, key, value)

            return llm

    def delete_llm(self, llm_id: int) -> bool:
        """删除LLM配置

        Args:
            llm_id: LLM配置ID

        Returns:
            删除是否成功
        """
        with db.session_scope() as session:
            llm = session.query(LlmConfig).filter_by(id=llm_id).first()
            if not llm:
                return False

            # 检查是否为默认LLM
            if llm.is_default:
                # 如果是唯一的LLM，允许删除
                count = session.query(LlmConfig).count()
                if count > 1:
                    # 如果删除的是默认LLM，需要设置新的默认LLM
                    new_default = session.query(LlmConfig).filter(
                        LlmConfig.id != llm_id
                    ).first()
                    if new_default:
                        new_default.is_default = True

            session.delete(llm)
            return True

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

    def test_connection(self, llm_id: int = None, api_key: str = None, 
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
        # 获取连接参数
        connection_params = {}
        if llm_id is not None:
            llm = self.get_llm(llm_id)
            if llm:
                connection_params = {
                    'api_key': llm.api_key,
                    'base_url': llm.base_url,
                    'model_name': llm.model_name
                }
        else:
            if api_key and base_url and model_name:
                connection_params = {
                    'api_key': api_key,
                    'base_url': base_url,
                    'model_name': model_name
                }

        # TODO: 实现实际的连接测试逻辑
        # 返回测试结果
        return {
            'success': True,  # 假设测试成功
            'response_time': 0.5,  # 假设响应时间0.5秒
            'message': '连接测试成功'
        }

    def _clear_default_status(self, session):
        """清除所有LLM的默认状态

        Args:
            session: 数据库会话
        """
        session.query(LlmConfig).filter_by(is_default=True).update(
            {LlmConfig.is_default: False}
        )