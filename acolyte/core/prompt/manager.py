"""
Prompt模板管理器
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from acolyte.core.db.database import db
from acolyte.core.db.models import Prompt
from acolyte.utils.logging import get_logger

# 获取模块日志记录器
logger = get_logger(__name__)


class PromptManager:
    """
    Prompt模板管理器

    该类负责管理提示词模板，包括扫描文件、同步到数据库、获取模板等功能。
    它支持从文件系统加载提示词模板，并将其同步到数据库中便于管理和使用。

    主要功能：
    - 扫描提示词模板文件，自动提取版本、目标模型等信息
    - 将提示词模板同步到数据库，便于管理和查询
    - 获取最新版本或指定版本的提示词模板
    - 支持按目标模型筛选提示词模板

    提示词模板命名规范：
    - 格式：`prompt_v{version}[_{model_target}].txt`
    - 示例：`prompt_v1.0.txt`、`prompt_v2.1_claude.txt`
    """

    def __init__(self, prompt_dir: str = None):
        """
        初始化Prompt管理器

        该方法初始化PromptManager实例，设置提示词模板目录路径。
        如果未指定目录路径，它会尝试自动查找项目根目录下的prompt目录。
        如果找不到，则创建一个新的prompt目录。

        查找流程：
        1. 如果指定了prompt_dir，直接使用
        2. 否则，尝试查找项目根目录（包含.git目录或pyproject.toml文件）
        3. 如果找到项目根目录，则在其下查找prompt目录
        4. 如果找不到项目根目录，则使用当前目录的父目录
        5. 如果找不到prompt目录，则创建一个新的prompt目录

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
                    logger.warning("未找到prompt目录，将使用默认目录并尝试创建")
                    prompt_dir = str(root_dir / "prompt")  # 仍然使用这个路径，但会创建目录

        logger.info(f"最终选择的prompt目录: {prompt_dir}")

        self.prompt_dir = prompt_dir
        self._ensure_prompt_dir_exists()

    def _ensure_prompt_dir_exists(self) -> None:
        """确保prompt目录存在"""
        os.makedirs(self.prompt_dir, exist_ok=True)

    def scan_prompt_files(self) -> List[Dict]:
        """
        扫描prompt文件目录，返回文件信息列表

        该方法扫描提示词模板目录，查找符合命名规范的提示词模板文件。
        它使用正则表达式匹配文件名，提取版本号和目标模型信息。
        如果文件名中没有指定目标模型，则默认为"general"。

        扫描流程：
        1. 确保提示词模板目录存在
        2. 使用正则表达式匹配文件名，格式为`bias-detection-prompt_v{version}[_{model_target}].md`
        3. 提取版本号和目标模型信息
        4. 对于特殊格式的文件名，进行特殊处理

        Returns:
            List[Dict]: 包含prompt文件信息的列表，每项是一个字典，包含以下字段：
                - path (str): 文件路径
                - filename (str): 文件名
                - version (str): 版本号
                - model_target (str): 目标模型，如果未指定则为"general"
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
                prompt_files.append(
                    {
                        "path": str(file),
                        "filename": file.name,
                        "version": version,
                        "model_target": model_target,
                    }
                )
                logger.info(f"解析prompt: {file.name}, 版本: {version}, 目标: {model_target}")
            elif file.name == "bias-detection-prompt_v3.md":
                logger.debug(f"特殊格式匹配: {file.name}")
                # Special case for the v3 prompt with different naming format
                prompt_files.append(
                    {
                        "path": str(file),
                        "filename": file.name,
                        "version": "3.0",
                        "model_target": "claude",
                    }
                )
                logger.info(f"解析特殊prompt: {file.name}, 版本: 3.0, 目标: claude")

        # 按版本号排序，最新版本优先
        prompt_files.sort(key=lambda x: [int(p) for p in x["version"].split(".")], reverse=True)
        logger.debug(f"排序后的prompt列表: {[p['filename'] for p in prompt_files]}")
        return prompt_files

    def sync_prompt_files_to_db(self) -> Dict[str, Any]:
        """
        将prompt文件同步到数据库

        该方法扫描提示词模板文件，并将其同步到数据库中。
        它会检查数据库中是否已存在相同版本和目标模型的提示词模板，
        如果不存在，则创建新的提示词模板记录。

        同步流程：
        1. 扫描提示词模板文件，获取文件信息列表
        2. 遍历每个文件，读取文件内容
        3. 检查数据库中是否已存在相同版本和目标模型的提示词模板
        4. 如果不存在，则创建新的提示词模板记录
        5. 如果存在但内容不同，则更新现有记录

        Returns:
            None
        """
        prompt_files = self.scan_prompt_files()
        logger.info(f"找到 {len(prompt_files)} 个prompt文件需要同步")

        try:
            with db.session_scope() as session:
                for prompt_info in prompt_files:
                    logger.info(
                        f"处理prompt: {prompt_info['filename']}, "
                        f"版本: {prompt_info['version']}, 目标: {prompt_info['model_target']}"
                    )

                    try:
                        # 检查是否已存在
                        existing_prompt = (
                            session.query(Prompt)
                            .filter_by(
                                version=prompt_info["version"],
                                model_target=prompt_info["model_target"],
                            )
                            .first()
                        )

                        # 读取文件内容
                        try:
                            with open(prompt_info["path"], "r", encoding="utf-8") as f:
                                content = f.read()
                                logger.debug(f"读取文件内容: {len(content)} 字符")
                        except Exception as e:
                            logger.error(
                                f"读取文件 {prompt_info['path']} 失败: {str(e)}", exc_info=True
                            )
                            continue

                        if existing_prompt:
                            logger.info(f"更新已有prompt记录 (ID: {existing_prompt.id})")
                            # 更新已有记录
                            existing_prompt.content = content
                            existing_prompt.file_path = prompt_info["path"]
                        else:
                            logger.info("创建新prompt记录")
                            # 创建新记录
                            new_prompt = Prompt(
                                version=prompt_info["version"],
                                model_target=prompt_info["model_target"],
                                content=content,
                                file_path=prompt_info["path"],
                                description=f"Bias detection prompt v{prompt_info['version']} "
                                f"for {prompt_info['model_target']}",
                            )
                            session.add(new_prompt)
                    except Exception as e:
                        logger.error(
                            f"处理prompt {prompt_info['filename']} 时发生错误: {str(e)}",
                            exc_info=True,
                        )

            logger.info("Prompt同步完成")
            return True
        except Exception as e:
            logger.error(f"同步prompt文件到数据库失败: {str(e)}", exc_info=True)
            return False

    def get_latest_prompt(self, model_target: str = None) -> Optional[Prompt]:
        """
        获取最新版本的prompt

        该方法从数据库中获取最新版本的提示词模板。
        如果指定了目标模型，则获取针对该模型的最新版本。
        如果未指定目标模型，则获取通用版本（model_target为"general"）的最新版本。

        查询流程：
        1. 首先查询所有活跃的提示词模板（is_active=True）
        2. 如果指定了目标模型，则过滤出针对该模型的模板
        3. 如果未指定目标模型，则过滤出通用版本的模板
        4. 按版本号降序排序，获取第一个结果（最新版本）

        Args:
            model_target: 目标模型名称，如果为None则获取通用版本（model_target="general"）

        Returns:
            Optional[Prompt]: 最新版本的Prompt对象，如果未找到则返回None
        """
        try:
            with db.session_scope() as session:
                # 获取所有活跃的prompts
                logger.info(
                    f"获取最新活跃的prompt模板{' 用于模型 '+model_target if model_target else ''}"
                )
                query = session.query(Prompt).filter(Prompt.is_active)

                # 如果指定了模型目标，优先获取针对该模型的prompt
                if model_target:
                    model_specific_prompt = query.filter(
                        Prompt.model_target == model_target
                    ).first()
                    if model_specific_prompt:
                        logger.info(
                            f"找到针对模型 {model_target} 的prompt: "
                            f"ID={model_specific_prompt.id}, 版本={model_specific_prompt.version}"
                        )
                        return model_specific_prompt
                    logger.info(f"未找到针对模型 {model_target} 的特定prompt，寻找通用prompt")

                # 检查数据库中的prompts
                all_prompts = query.all()
                if all_prompts:
                    for p in all_prompts:
                        logger.debug(
                            f"数据库中的prompt: ID={p.id}, 版本={p.version}, 目标={p.model_target}"
                        )
                else:
                    logger.warning("数据库中没有找到任何活跃的prompt模板")

                # 直接获取第一个prompt
                first_prompt = query.first()
                if first_prompt:
                    logger.info(
                        f"找到第一个活跃prompt: ID={first_prompt.id}, "
                        f"版本={first_prompt.version}, 目标={first_prompt.model_target}"
                    )
                    return first_prompt
                else:
                    logger.warning("无法获取任何prompt模板")
                    return None
        except Exception as e:
            logger.error(f"获取最新prompt时出错: {str(e)}", exc_info=True)
            return None

    def get_prompt_by_version(self, version: str, model_target: str = None) -> Optional[Prompt]:
        """
        根据版本号获取prompt

        该方法从数据库中获取指定版本的提示词模板。
        如果指定了目标模型，则获取针对该模型的指定版本。
        如果未指定目标模型，则获取任意目标模型的指定版本。

        查询流程：
        1. 首先查询所有活跃的提示词模板（is_active=True）
        2. 过滤出指定版本的模板
        3. 如果指定了目标模型，则过滤出针对该模型的模板
        4. 返回第一个匹配的结果

        Args:
            version: 要获取的提示词模板版本号，如"1.0"、"2.1"等
            model_target: 目标模型名称，如果为None则不过滤目标模型

        Returns:
            Optional[Prompt]: 匹配的Prompt对象，如果未找到则返回None
        """
        with db.session_scope() as session:
            query = session.query(Prompt).filter(Prompt.version == version, Prompt.is_active)

            if model_target:
                query = query.filter(Prompt.model_target == model_target)

            return query.first()

    def get_all_prompts(self) -> List[Prompt]:
        """
        获取所有prompt

        该方法从数据库中获取所有的提示词模板。
        结果先按目标模型排序，然后按版本号降序排序，
        便于查看每个目标模型的最新版本。

        查询流程：
        1. 查询所有提示词模板（不过滤活跃状态）
        2. 按目标模型和版本号降序排序
        3. 返回所有结果

        Returns:
            List[Prompt]: 所有Prompt对象的列表，按目标模型和版本号降序排序
        """
        with db.session_scope() as session:
            return session.query(Prompt).order_by(Prompt.model_target, Prompt.version.desc()).all()
