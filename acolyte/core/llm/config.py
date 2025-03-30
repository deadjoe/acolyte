"""
LLM配置加载和保存
"""
from typing import Dict, List, Optional

from acolyte.config.settings import AppConfig, LlmConfigModel, config, save_config
from acolyte.core.db.database import db
from acolyte.core.db.models import LlmConfig, LlmRole


def import_llm_config_from_file(llm_name: Optional[str] = None) -> List[Dict]:
    """从配置文件导入LLM配置

    Args:
        llm_name: 可选，指定要导入的LLM名称

    Returns:
        导入的LLM配置信息列表（字典格式）
    """
    from acolyte.core.llm.manager import LlmManager
    
    llm_manager = LlmManager()
    imported_llms = []
    
    # 筛选配置
    llm_configs = config.llm_configs
    print(f"从配置文件中读取到 {len(llm_configs)} 个LLM配置")
    
    if llm_name:
        llm_configs = [cfg for cfg in llm_configs if cfg.name == llm_name]
        print(f"按名称筛选后剩余 {len(llm_configs)} 个LLM配置 (查找名称: {llm_name})")
    
    if not llm_configs:
        print("没有找到可导入的LLM配置")
        return []
        
    # 导入配置
    with db.session_scope() as session:
        for llm_config in llm_configs:
            role = LlmRole.REVIEWER if llm_config.role.lower() == "reviewer" else LlmRole.NORMAL
            
            # 检查是否已存在
            existing_llm = None
            llm_query = session.query(LlmConfig).filter(LlmConfig.name == llm_config.name)
            if llm_query.count() > 0:
                existing_llm = llm_query.first()
            
            if existing_llm:
                # 更新已有配置
                for attr, value in [
                    ('api_key', llm_config.api_key),
                    ('base_url', llm_config.base_url),
                    ('model_name', llm_config.model_name),
                    ('description', llm_config.description),
                    ('role', role),
                    ('is_default', llm_config.is_default),
                ]:
                    setattr(existing_llm, attr, value)
                
                # 如果设为默认，取消其他默认设置
                if llm_config.is_default:
                    session.query(LlmConfig).filter(
                        LlmConfig.id != existing_llm.id
                    ).update({LlmConfig.is_default: False})
                
                imported_llms.append({
                    "id": existing_llm.id,
                    "name": existing_llm.name,
                    "model_name": existing_llm.model_name,
                    "role": existing_llm.role.value,
                    "is_default": existing_llm.is_default
                })
            else:
                # 如果设为默认，取消其他默认设置
                if llm_config.is_default:
                    session.query(LlmConfig).update({LlmConfig.is_default: False})
                
                # 创建新配置
                new_llm = LlmConfig(
                    name=llm_config.name,
                    api_key=llm_config.api_key,
                    base_url=llm_config.base_url,
                    model_name=llm_config.model_name,
                    description=llm_config.description,
                    role=role,
                    is_default=llm_config.is_default
                )
                session.add(new_llm)
                session.flush()  # 获取新ID
                
                imported_llms.append({
                    "id": new_llm.id,
                    "name": new_llm.name,
                    "model_name": new_llm.model_name,
                    "role": new_llm.role.value,
                    "is_default": new_llm.is_default
                })
        
        # 提交会话中的所有更改
        session.commit()
            
    return imported_llms


def export_llm_config_to_file() -> bool:
    """将数据库中的LLM配置导出到配置文件

    Returns:
        是否导出成功
    """
    with db.session_scope() as session:
        llm_configs = session.query(LlmConfig).all()
        
        # 转换为配置模型
        config_models = []
        for llm in llm_configs:
            config_models.append(LlmConfigModel(
                name=llm.name,
                api_key=llm.api_key,
                base_url=llm.base_url,
                model_name=llm.model_name,
                description=llm.description,
                role=llm.role.value,
                is_default=llm.is_default
            ))
        
        # 更新配置
        app_config = config
        app_config.llm_configs = config_models
        
        # 保存配置
        return save_config(app_config)