"""
提示词服务

处理提示词模板管理的业务逻辑，作为API路由和提示词管理器之间的中间层。
"""
import os
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from acolyte.core.db.models import Prompt
from acolyte.core.db.session import extract_model_data, run_in_session
from acolyte.core.prompt.manager import PromptManager
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class PromptService:
    """
    提示词服务类
    
    提供提示词相关的业务逻辑实现，包括提示词同步、查询和管理。
    """
    
    def __init__(self):
        """初始化提示词服务"""
        self.prompt_manager = PromptManager()
    
    async def get_prompts(self, model_target: Optional[str] = None, version: Optional[str] = None) -> Dict:
        """
        获取提示词列表
        
        Args:
            model_target: 筛选的目标模型
            version: 筛选的版本号
            
        Returns:
            提示词列表
        """
        logger.info(f"获取提示词列表: 目标模型={model_target}, 版本={version}")
        
        async def _get_prompts(session: Session):
            query = session.query(Prompt)
            
            # 应用筛选条件
            if model_target:
                query = query.filter(Prompt.model_target == model_target)
            if version:
                query = query.filter(Prompt.version == version)
            
            # 排序：先按模型目标，再按版本号降序
            query = query.order_by(Prompt.model_target, Prompt.version.desc())
            
            # 执行查询
            results = query.all()
            
            return [extract_model_data(item) for item in results]
        
        try:
            prompts = await run_in_session(_get_prompts)
            return {"prompts": prompts, "count": len(prompts), "success": True}
        except Exception as e:
            logger.error(f"获取提示词列表失败: {str(e)}", exc_info=True)
            return {"error": f"获取提示词列表失败: {str(e)}", "success": False}
    
    async def get_prompt(self, prompt_id: int) -> Dict:
        """
        获取特定提示词
        
        Args:
            prompt_id: 提示词ID
            
        Returns:
            提示词信息
        """
        logger.info(f"获取提示词: ID={prompt_id}")
        
        async def _get_prompt(session: Session):
            prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()
            if not prompt:
                return None
            
            # 直接使用to_dict方法并传入include_content=True确保包含内容
            if hasattr(prompt, 'to_dict') and callable(getattr(prompt, 'to_dict')):
                return prompt.to_dict(include_content=True)
            else:
                # 回退到extract_model_data
                return extract_model_data(prompt)
        
        try:
            prompt = await run_in_session(_get_prompt)
            if not prompt:
                return {"error": "提示词不存在", "success": False}
            return {**prompt, "success": True}
        except Exception as e:
            logger.error(f"获取提示词失败: {str(e)}", exc_info=True)
            return {"error": f"获取提示词失败: {str(e)}", "success": False}
    
    async def get_latest_prompt(self, model_target: Optional[str] = None) -> Dict:
        """
        获取最新版本的提示词
        
        Args:
            model_target: 目标模型名称
            
        Returns:
            最新版本的提示词信息
        """
        logger.info(f"获取最新提示词: 目标模型={model_target}")
        
        try:
            prompt = self.prompt_manager.get_latest_prompt(model_target)
            if not prompt:
                logger.warning(f"未找到{'针对模型 '+model_target+'的' if model_target else ''}最新提示词")
                return {"error": "未找到最新提示词", "success": False}
            
            return {**extract_model_data(prompt), "success": True}
        except Exception as e:
            logger.error(f"获取最新提示词失败: {str(e)}", exc_info=True)
            return {"error": f"获取最新提示词失败: {str(e)}", "success": False}
    
    async def sync_prompts(self, prompt_dir: Optional[str] = None) -> Dict:
        """
        同步提示词文件到数据库
        
        Args:
            prompt_dir: 可选的提示词目录路径，如果指定则使用该路径
            
        Returns:
            同步结果
        """
        logger.info(f"开始同步提示词文件到数据库{f', 使用目录: {prompt_dir}' if prompt_dir else ''}")
        
        try:
            # 如果指定了prompt_dir，先更新PromptManager的prompt_dir属性
            original_prompt_dir = None
            if prompt_dir:
                logger.debug(f"临时设置PromptManager的prompt_dir为: {prompt_dir}")
                original_prompt_dir = self.prompt_manager.prompt_dir
                self.prompt_manager.prompt_dir = prompt_dir
            
            try:
                result = self.prompt_manager.sync_prompt_files_to_db()
                if result:
                    # 查询同步后的提示词数量
                    async def _count_prompts(session: Session):
                        return session.query(Prompt).count()
                    
                    count = await run_in_session(_count_prompts)
                    logger.info(f"提示词同步成功，当前共有 {count} 个提示词模板")
                    return {
                        "message": f"提示词同步成功，当前共有 {count} 个提示词模板",
                        "count": count,
                        "success": True
                    }
                else:
                    logger.error("提示词同步失败")
                    return {"error": "提示词同步失败", "success": False}
            finally:
                # 恢复原始prompt_dir
                if original_prompt_dir:
                    logger.debug(f"恢复PromptManager的prompt_dir为: {original_prompt_dir}")
                    self.prompt_manager.prompt_dir = original_prompt_dir
        except Exception as e:
            logger.error(f"同步提示词文件失败: {str(e)}", exc_info=True)
            return {"error": f"同步提示词文件失败: {str(e)}", "success": False}
    
    async def create_prompt(self, prompt_data: Dict) -> Dict:
        """
        创建提示词
        
        Args:
            prompt_data: 提示词数据
            
        Returns:
            创建的提示词信息
        """
        logger.info(f"创建提示词: 版本={prompt_data.get('version')}, 目标模型={prompt_data.get('model_target')}")
        
        # 检查必要字段
        required_fields = ['version', 'model_target', 'content']
        missing_fields = [field for field in required_fields if field not in prompt_data]
        if missing_fields:
            logger.error(f"创建提示词失败: 缺少必要字段 {missing_fields}")
            return {"error": f"缺少必要字段: {', '.join(missing_fields)}", "success": False}
        
        # 如果指定了file_path，则写入文件
        if 'file_path' in prompt_data:
            file_path = prompt_data['file_path']
        else:
            # 生成默认文件路径 
            model_suffix = f"_{prompt_data['model_target']}" if prompt_data['model_target'] != 'general' else ''
            filename = f"bias-detection-prompt_v{prompt_data['version']}{model_suffix}.md"
            file_path = os.path.join(self.prompt_manager.prompt_dir, filename)
            prompt_data['file_path'] = file_path
        
        # 生成描述（如果没有提供）
        if 'description' not in prompt_data:
            model_name = prompt_data['model_target'] if prompt_data['model_target'] != 'general' else 'general use'
            prompt_data['description'] = f"Bias detection prompt v{prompt_data['version']} for {model_name}"
        
        # 默认为活跃状态
        if 'is_active' not in prompt_data:
            prompt_data['is_active'] = True
        
        async def _create_prompt(session: Session):
            # 检查是否已存在
            existing = session.query(Prompt).filter(
                Prompt.version == prompt_data['version'],
                Prompt.model_target == prompt_data['model_target']
            ).first()
            
            if existing:
                logger.warning(f"已存在相同版本和目标模型的提示词: ID={existing.id}")
                return None
            
            # 创建新记录
            new_prompt = Prompt(**prompt_data)
            session.add(new_prompt)
            session.flush()
            
            # 写入文件
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(prompt_data['content'])
                logger.info(f"已将提示词内容写入文件: {file_path}")
            except Exception as e:
                logger.error(f"写入提示词文件失败: {str(e)}", exc_info=True)
                # 文件写入失败不影响数据库记录创建
            
            return extract_model_data(new_prompt)
        
        try:
            result = await run_in_session(_create_prompt)
            if not result:
                return {"error": "已存在相同版本和目标模型的提示词", "success": False}
            return {**result, "success": True}
        except Exception as e:
            logger.error(f"创建提示词失败: {str(e)}", exc_info=True)
            return {"error": f"创建提示词失败: {str(e)}", "success": False}
    
    async def update_prompt(self, prompt_id: int, update_data: Dict) -> Dict:
        """
        更新提示词
        
        Args:
            prompt_id: 提示词ID
            update_data: 更新数据
            
        Returns:
            更新后的提示词信息
        """
        logger.info(f"更新提示词: ID={prompt_id}")
        
        async def _update_prompt(session: Session):
            prompt = session.query(Prompt).filter_by(id=prompt_id).first()
            if not prompt:
                return None
            
            # 记录原始文件路径，用于判断是否需要更新文件
            original_file_path = prompt.file_path
            original_content = prompt.content
            content_changed = 'content' in update_data and update_data['content'] != original_content
            
            # 更新字段
            for key, value in update_data.items():
                if hasattr(prompt, key):
                    setattr(prompt, key, value)
            
            # 如果内容变化且有文件路径，则更新文件
            if content_changed and prompt.file_path:
                try:
                    with open(prompt.file_path, 'w', encoding='utf-8') as f:
                        f.write(prompt.content)
                    logger.info(f"已更新提示词文件: {prompt.file_path}")
                except Exception as e:
                    logger.error(f"更新提示词文件失败: {str(e)}", exc_info=True)
                    # 文件更新失败不影响数据库记录更新
            
            # 如果文件路径变化，且原路径存在且不同于新路径，则复制到新位置
            if 'file_path' in update_data and update_data['file_path'] != original_file_path:
                if os.path.exists(original_file_path):
                    try:
                        with open(update_data['file_path'], 'w', encoding='utf-8') as f:
                            f.write(prompt.content)
                        logger.info(f"已将提示词内容写入新文件: {update_data['file_path']}")
                    except Exception as e:
                        logger.error(f"写入新提示词文件失败: {str(e)}", exc_info=True)
            
            return extract_model_data(prompt)
        
        try:
            result = await run_in_session(_update_prompt)
            if not result:
                return {"error": "提示词不存在", "success": False}
            return {**result, "success": True}
        except Exception as e:
            logger.error(f"更新提示词失败: {str(e)}", exc_info=True)
            return {"error": f"更新提示词失败: {str(e)}", "success": False}
    
    async def delete_prompt(self, prompt_id: int, delete_file: bool = False) -> Dict:
        """
        删除提示词
        
        Args:
            prompt_id: 提示词ID
            delete_file: 是否同时删除文件
            
        Returns:
            删除结果
        """
        logger.info(f"删除提示词: ID={prompt_id}, 删除文件={delete_file}")
        
        async def _delete_prompt(session: Session):
            prompt = session.query(Prompt).filter_by(id=prompt_id).first()
            if not prompt:
                return None
            
            file_path = prompt.file_path
            session.delete(prompt)
            
            return {
                "file_path": file_path,
                "id": prompt_id,
                "version": prompt.version,
                "model_target": prompt.model_target
            }
        
        try:
            result = await run_in_session(_delete_prompt)
            if not result:
                return {"error": "提示词不存在", "success": False}
            
            # 如果需要删除文件，并且文件存在
            if delete_file and result["file_path"] and os.path.exists(result["file_path"]):
                try:
                    os.remove(result["file_path"])
                    logger.info(f"已删除提示词文件: {result['file_path']}")
                    result["file_deleted"] = True
                except Exception as e:
                    logger.error(f"删除提示词文件失败: {str(e)}", exc_info=True)
                    result["file_deleted"] = False
            
            return {**result, "success": True}
        except Exception as e:
            logger.error(f"删除提示词失败: {str(e)}", exc_info=True)
            return {"error": f"删除提示词失败: {str(e)}", "success": False}
    
    async def set_active_status(self, prompt_id: int, is_active: bool) -> Dict:
        """
        设置提示词活跃状态
        
        Args:
            prompt_id: 提示词ID
            is_active: 是否活跃
            
        Returns:
            更新结果
        """
        logger.info(f"设置提示词活跃状态: ID={prompt_id}, 状态={is_active}")
        
        async def _set_active(session: Session):
            prompt = session.query(Prompt).filter_by(id=prompt_id).first()
            if not prompt:
                return None
            
            prompt.is_active = is_active
            return extract_model_data(prompt)
        
        try:
            result = await run_in_session(_set_active)
            if not result:
                return {"error": "提示词不存在", "success": False}
            
            status_msg = "启用" if is_active else "禁用"
            return {
                **result, 
                "message": f"提示词已{status_msg}",
                "success": True
            }
        except Exception as e:
            logger.error(f"设置提示词活跃状态失败: {str(e)}", exc_info=True)
            return {"error": f"设置提示词活跃状态失败: {str(e)}", "success": False}