"""
Prompt模板管理器
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from acolyte.core.db.database import db
from acolyte.core.db.models import Prompt
from acolyte.utils.logging import get_logger

# 获取模块日志记录器
logger = get_logger(__name__)


class PromptManager:
    """Prompt模板管理器"""

    def __init__(self, prompt_dir: str = None):
        """初始化Prompt管理器

        Args:
            prompt_dir: prompt模板目录路径，默认为项目根目录下的prompt目录
        """
        logger.info("初始化Prompt管理器")

        # 如果传入了prompt_dir，直接使用
        if prompt_dir:
            logger.info(f"使用传入的prompt目录: {prompt_dir}")
        else:
            # 否则尝试从其他来源获取
            logger.debug("未提供prompt_dir参数，尝试从其他来源获取")
            # 首先检查环境变量
            env_prompt_dir = os.environ.get("ACOLYTE_PROMPT_DIR")
            if env_prompt_dir:
                logger.info(f"从环境变量获取prompt目录: {env_prompt_dir}")
                prompt_dir = env_prompt_dir
            # 如果没有从环境变量中找到prompt_dir，尝试自动查找
            if not prompt_dir:
                logger.debug("尝试自动查找prompt目录")
                # 获取当前文件所在目录
                current_dir = Path(__file__).resolve().parent
                logger.debug(f"当前目录: {current_dir}")

                # 向上查找，回到上层直到找到项目根目录
                # 从父目录开始查找，避免将当前目录误认为prompt目录
                root_dir = current_dir.parent
                logger.debug(f"开始从父目录查找: {root_dir}")

                # 向上一级一级查找直到找到项目根目录
                # 首先查找项目根目录（包含.git目录或pyproject.toml文件）
                project_root = None
                search_dir = root_dir
                while search_dir != search_dir.parent:
                    # 检查是否是项目根目录
                    if (search_dir / ".git").exists() or (search_dir / "pyproject.toml").exists():
                        project_root = search_dir
                        logger.debug(f"找到项目根目录: {project_root}")
                        break
                    # 否则继续向上查找
                    search_dir = search_dir.parent
                    logger.debug(f"向上查找项目根目录: {search_dir}")

                # 如果找到项目根目录，则在项目根目录下查找prompt目录
                if project_root:
                    root_dir = project_root
                    logger.debug(f"在项目根目录{root_dir}下查找prompt目录")
                else:
                    # 如果没有找到项目根目录，则使用当前目录的父目录
                    logger.warning("未找到项目根目录，将使用当前目录的父目录")

                # 检查项目根目录下是否存在prompt目录
                if (root_dir / "prompt").exists():
                    logger.info(f"找到prompt目录: {root_dir / 'prompt'}")
                    prompt_dir = str(root_dir / "prompt")
                else:
                    logger.warning(f"未找到prompt目录，将使用默认目录并尝试创建")
                    prompt_dir = str(root_dir / "prompt")  # 仍然使用这个路径，但会创建目录

        logger.info(f"最终选择的prompt目录: {prompt_dir}")

        self.prompt_dir = prompt_dir
        self._ensure_prompt_dir_exists()

    def _ensure_prompt_dir_exists(self):
        """确保prompt目录存在"""
        os.makedirs(self.prompt_dir, exist_ok=True)

    def scan_prompt_files(self) -> List[Dict]:
        """扫描prompt文件目录，返回文件信息列表

        Returns:
            包含prompt文件信息的列表，每项包含path, version, model_target
        """
        prompt_files = []
        prompt_pattern = re.compile(
            r"bias-detection-prompt_v(\d+(?:\.\d+)*)(?:_([a-zA-Z0-9]+))?\.md"
        )

        logger.info(f"扫描prompt目录: {self.prompt_dir}")
        all_files = list(Path(self.prompt_dir).glob("*.md"))
        logger.info(f"找到 {len(all_files)} 个MD文件")
        logger.debug(f"文件列表: {[f.name for f in all_files]}")

        for file in all_files:
            logger.debug(f"处理文件: {file.name}")
            match = prompt_pattern.match(file.name)
            if match:
                logger.debug(f"正则匹配成功: {file.name}")
                version = match.group(1)
                model_target = match.group(2) or "general"
                prompt_files.append({
                    "path": str(file),
                    "filename": file.name,
                    "version": version,
                    "model_target": model_target,
                })
                logger.info(f"解析prompt: {file.name}, 版本: {version}, 目标: {model_target}")
            elif file.name == "bias-detection-prompt_v3.md":
                logger.debug(f"特殊格式匹配: {file.name}")
                # Special case for the v3 prompt with different naming format
                prompt_files.append({
                    "path": str(file),
                    "filename": file.name,
                    "version": "3.0",
                    "model_target": "claude",
                })
                logger.info(f"解析特殊prompt: {file.name}, 版本: 3.0, 目标: claude")

        # 按版本号排序，最新版本优先
        prompt_files.sort(key=lambda x: [int(p) for p in x["version"].split(".")], reverse=True)
        logger.debug(f"排序后的prompt列表: {[p['filename'] for p in prompt_files]}")
        return prompt_files

    def sync_prompt_files_to_db(self):
        """将prompt文件同步到数据库"""
        prompt_files = self.scan_prompt_files()
        logger.info(f"找到 {len(prompt_files)} 个prompt文件需要同步")

        try:
            with db.session_scope() as session:
                for prompt_info in prompt_files:
                    logger.info(f"处理prompt: {prompt_info['filename']}, 版本: {prompt_info['version']}, 目标: {prompt_info['model_target']}")

                    try:
                        # 检查是否已存在
                        existing_prompt = session.query(Prompt).filter_by(
                            version=prompt_info["version"],
                            model_target=prompt_info["model_target"]
                        ).first()

                        # 读取文件内容
                        try:
                            with open(prompt_info["path"], "r", encoding="utf-8") as f:
                                content = f.read()
                                logger.debug(f"读取文件内容: {len(content)} 字符")
                        except Exception as e:
                            logger.error(f"读取文件 {prompt_info['path']} 失败: {str(e)}", exc_info=True)
                            continue

                        if existing_prompt:
                            logger.info(f"更新已有prompt记录 (ID: {existing_prompt.id})")
                            # 更新已有记录
                            existing_prompt.content = content
                            existing_prompt.file_path = prompt_info["path"]
                        else:
                            logger.info(f"创建新prompt记录")
                            # 创建新记录
                            new_prompt = Prompt(
                                version=prompt_info["version"],
                                model_target=prompt_info["model_target"],
                                content=content,
                                file_path=prompt_info["path"],
                                description=f"Bias detection prompt v{prompt_info['version']} "
                                           f"for {prompt_info['model_target']}"
                            )
                            session.add(new_prompt)
                    except Exception as e:
                        logger.error(f"处理prompt {prompt_info['filename']} 时发生错误: {str(e)}", exc_info=True)

            logger.info("Prompt同步完成")
            return True
        except Exception as e:
            logger.error(f"同步prompt文件到数据库失败: {str(e)}", exc_info=True)
            return False

    def get_latest_prompt(self, model_target: str = None) -> Optional[Prompt]:
        """获取最新版本的prompt

        Args:
            model_target: 目标模型名称，如果为None则获取通用版本

        Returns:
            最新版本的Prompt对象
        """
        try:
            with db.session_scope() as session:
                # 获取所有活跃的prompts
                logger.info(f"获取最新活跃的prompt模板{' 用于模型 '+model_target if model_target else ''}")
                query = session.query(Prompt).filter(Prompt.is_active == True)

                # 如果指定了模型目标，优先获取针对该模型的prompt
                if model_target:
                    model_specific_prompt = query.filter(Prompt.model_target == model_target).first()
                    if model_specific_prompt:
                        logger.info(f"找到针对模型 {model_target} 的prompt: ID={model_specific_prompt.id}, 版本={model_specific_prompt.version}")
                        return model_specific_prompt
                    logger.info(f"未找到针对模型 {model_target} 的特定prompt，寻找通用prompt")

                # 检查数据库中的prompts
                all_prompts = query.all()
                if all_prompts:
                    for p in all_prompts:
                        logger.debug(f"数据库中的prompt: ID={p.id}, 版本={p.version}, 目标={p.model_target}")
                else:
                    logger.warning("数据库中没有找到任何活跃的prompt模板")

                # 直接获取第一个prompt
                first_prompt = query.first()
                if first_prompt:
                    logger.info(f"找到第一个活跃prompt: ID={first_prompt.id}, 版本={first_prompt.version}, 目标={first_prompt.model_target}")
                    return first_prompt
                else:
                    logger.warning("无法获取任何prompt模板")
                    return None
        except Exception as e:
            logger.error(f"获取最新prompt时出错: {str(e)}", exc_info=True)
            return None

    def get_prompt_by_version(self, version: str, model_target: str = None) -> Optional[Prompt]:
        """根据版本号获取prompt

        Args:
            version: 版本号
            model_target: 目标模型名称

        Returns:
            匹配的Prompt对象
        """
        with db.session_scope() as session:
            query = session.query(Prompt).filter(
                Prompt.version == version,
                Prompt.is_active == True
            )

            if model_target:
                query = query.filter(Prompt.model_target == model_target)

            return query.first()

    def get_all_prompts(self) -> List[Prompt]:
        """获取所有prompt

        Returns:
            所有Prompt对象列表
        """
        with db.session_scope() as session:
            return session.query(Prompt).order_by(
                Prompt.model_target,
                Prompt.version.desc()
            ).all()