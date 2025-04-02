"""
LLM服务

处理LLM配置管理和使用的业务逻辑，作为API路由和LLM客户端之间的中间层。
"""
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from acolyte.core.db.models import LlmConfig, LlmRole
from acolyte.core.db.session import SessionManager, extract_model_data, run_in_session
from acolyte.core.llm.client import get_client_for_llm
from acolyte.core.llm.manager import LlmManager
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class LlmService:
    """
    LLM服务类
    
    提供LLM相关的业务逻辑实现，包括LLM配置管理和使用。
    """
    
    def __init__(self):
        """初始化LLM服务"""
        self.llm_manager = LlmManager()
    
    async def add_llm(self, llm_data: Dict) -> Dict:
        """
        添加LLM配置
        
        Args:
            llm_data: LLM配置数据
            
        Returns:
            添加的LLM配置信息
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
                is_default=is_default
            )
            
            if not new_llm:
                return {"error": "添加LLM配置失败", "success": False}
                
            return {**extract_model_data(new_llm), "success": True}
            
        except Exception as e:
            logger.error(f"添加LLM配置失败: {str(e)}", exc_info=True)
            return {"error": f"添加LLM配置失败: {str(e)}", "success": False}
    
    async def get_llms(self, role: Optional[str] = None, is_default: Optional[bool] = None) -> Dict:
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
    
    async def get_llm(self, llm_id: int) -> Dict:
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
    
    async def update_llm(self, llm_id: int, update_data: Dict) -> Dict:
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
    
    async def test_connection(self, llm_id: int) -> Dict:
        """
        测试LLM连接
        
        Args:
            llm_id: LLM配置ID
            
        Returns:
            测试结果
        """
        logger.info(f"测试LLM连接: ID={llm_id}")
        
        try:
            # 使用LLM管理器测试连接
            result = self.llm_manager.test_connection(llm_id=llm_id)
            
            logger.info(f"LLM连接测试结果: ID={llm_id}, 状态={result.get('status', 'unknown')}")
            return {**result, "success": result.get("status") == "success"}
            
        except Exception as e:
            logger.error(f"LLM连接测试失败: {str(e)}", exc_info=True)
            return {
                "status": "error", 
                "message": f"连接测试失败: {str(e)}", 
                "success": False
            }
    
    async def process_content(self, llm_id: int, content: str, prompt: str) -> Dict:
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
                return {"error": "LLM配置不存在", "success": False}
            
            # 获取LLM客户端
            client = get_client_for_llm(llm_config)
            
            # 处理内容
            result = client.process_content(content=content, prompt=prompt)
            
            return result
            
        except Exception as e:
            logger.error(f"使用LLM处理内容失败: {str(e)}", exc_info=True)
            return {
                "success": False, 
                "error": f"处理内容失败: {str(e)}", 
                "raw_response": None, 
                "result": {}
            }