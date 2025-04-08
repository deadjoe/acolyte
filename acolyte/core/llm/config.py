"""
LLM配置加载和保存
"""

from typing import Dict, List, Optional

from acolyte.config.settings import LlmConfigModel, config, save_config
from acolyte.core.db.database import db
from acolyte.core.db.models import LlmConfig, LlmRole
from acolyte.utils.logging import get_logger

# 获取模块日志记录器
logger = get_logger("acolyte.core.llm.config")


def import_llm_config_from_file(llm_name: Optional[str] = None) -> List[Dict]:
    """从配置文件导入LLM配置

    Args:
        llm_name: 可选，指定要导入的LLM名称
        verbose: 是否输出详细日志

    Returns:
        导入的LLM配置信息列表（字典格式）
    """
    logger.info(f"从配置文件导入LLM配置{' (' + llm_name + ')' if llm_name else ''}")

    try:
        # 初始化导入结果列表
        imported_llms = []

        # 筛选配置
        llm_configs = config.llm_configs
        logger.info(f"从配置文件中读取到 {len(llm_configs)} 个LLM配置")

        if llm_name:
            llm_configs = [cfg for cfg in llm_configs if cfg.name == llm_name]
            logger.info(f"按名称 '{llm_name}' 筛选后剩余 {len(llm_configs)} 个LLM配置")

        if not llm_configs:
            logger.warning("没有找到可导入的LLM配置")
            return []

        # 导入配置
        with db.session_scope() as session:
            for llm_config in llm_configs:
                logger.debug(f"处理LLM配置: {llm_config.name}, 模型: {llm_config.model_name}")
                role = LlmRole.REVIEWER if llm_config.role.lower() == "reviewer" else LlmRole.NORMAL

                # 检查是否已存在
                existing_llm = None
                llm_query = session.query(LlmConfig).filter(LlmConfig.name == llm_config.name)
                if llm_query.count() > 0:
                    existing_llm = llm_query.first()

                if existing_llm:
                    logger.info(f"更新已有LLM配置: ID={existing_llm.id}, 名称={existing_llm.name}")
                    # 更新已有配置
                    for attr, value in [
                        ("api_key", llm_config.api_key),
                        ("base_url", llm_config.base_url),
                        ("model_name", llm_config.model_name),
                        ("description", llm_config.description),
                        ("role", role),
                        ("is_default", llm_config.is_default),
                    ]:
                        setattr(existing_llm, attr, value)

                    # 如果设为默认，取消其他默认设置
                    if llm_config.is_default:
                        logger.debug("清除其他默认LLM状态")
                        session.query(LlmConfig).filter(LlmConfig.id != existing_llm.id).update(
                            {LlmConfig.is_default: False}
                        )

                    imported_llms.append(
                        {
                            "id": existing_llm.id,
                            "name": existing_llm.name,
                            "model_name": existing_llm.model_name,
                            "role": existing_llm.role.value,
                            "is_default": existing_llm.is_default,
                        }
                    )
                else:
                    logger.info(f"创建新的LLM配置: {llm_config.name}")
                    # 如果设为默认，取消其他默认设置
                    if llm_config.is_default:
                        logger.debug("清除其他默认LLM状态")
                        session.query(LlmConfig).update({LlmConfig.is_default: False})

                    # 创建新配置
                    new_llm = LlmConfig(
                        name=llm_config.name,
                        api_key=llm_config.api_key,
                        base_url=llm_config.base_url,
                        model_name=llm_config.model_name,
                        description=llm_config.description,
                        role=role,
                        is_default=llm_config.is_default,
                    )
                    session.add(new_llm)
                    session.flush()  # 获取新ID

                    imported_llms.append(
                        {
                            "id": new_llm.id,
                            "name": new_llm.name,
                            "model_name": new_llm.model_name,
                            "role": new_llm.role.value,
                            "is_default": new_llm.is_default,
                        }
                    )

            # 提交会话中的所有更改
            session.commit()
            logger.info(f"成功导入 {len(imported_llms)} 个LLM配置")

        return imported_llms
    except Exception as e:
        logger.error(f"导入LLM配置失败: {str(e)}", exc_info=True)
        raise


def export_llm_config_to_file() -> bool:
    """将数据库中的LLM配置导出到配置文件

    Returns:
        是否导出成功
    """
    logger.info("开始导出LLM配置到配置文件")

    try:
        with db.session_scope() as session:
            llm_configs = session.query(LlmConfig).all()
            logger.info(f"从数据库中获取到 {len(llm_configs)} 个LLM配置")

            # 转换为配置模型
            config_models = []
            for llm in llm_configs:
                logger.debug(f"处理LLM配置: ID={llm.id}, 名称={llm.name}, 模型={llm.model_name}")
                config_models.append(
                    LlmConfigModel(
                        name=llm.name,
                        api_key=llm.api_key,
                        base_url=llm.base_url,
                        model_name=llm.model_name,
                        description=llm.description,
                        role=llm.role.value,
                        is_default=llm.is_default,
                    )
                )

            # 更新配置
            app_config = config
            logger.debug("更新应用配置对象")
            app_config.llm_configs = config_models

            # 保存配置
            result = save_config(app_config)
            if result:
                logger.info("配置导出成功")
            else:
                logger.error("配置导出失败")
            return result
    except Exception as e:
        logger.error(f"导出LLM配置失败: {str(e)}", exc_info=True)
        return False
