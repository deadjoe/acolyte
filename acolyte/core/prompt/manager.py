"""
Prompt模板管理器
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from acolyte.core.db.database import db
from acolyte.core.db.models import Prompt


class PromptManager:
    """Prompt模板管理器"""

    def __init__(self, prompt_dir: str = None):
        """初始化Prompt管理器

        Args:
            prompt_dir: prompt模板目录路径，默认为项目根目录下的prompt目录
        """
        # 默认使用项目根目录下的prompt目录
        if prompt_dir is None:
            # 获取当前文件所在目录
            current_dir = Path(__file__).resolve().parent
            # 打印当前目录
            print(f"当前目录: {current_dir}")
            
            # 向上查找到项目根目录
            root_dir = current_dir
            
            # 查找到项目根目录
            while not (root_dir / "prompt").exists() and root_dir != root_dir.parent:
                root_dir = root_dir.parent
                print(f"向上查找: {root_dir}")
                
            if (root_dir / "prompt").exists():
                print(f"找到prompt目录: {root_dir / 'prompt'}")
            else:
                print(f"未找到prompt目录，使用默认目录")
                
            prompt_dir = str(root_dir / "prompt")
            print(f"最终prompt目录: {prompt_dir}")

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

        print(f"扫描prompt目录: {self.prompt_dir}")
        all_files = list(Path(self.prompt_dir).glob("*.md"))
        print(f"找到 {len(all_files)} 个MD文件: {[f.name for f in all_files]}")

        for file in all_files:
            print(f"处理文件: {file.name}")
            match = prompt_pattern.match(file.name)
            if match:
                print(f"  - 正则匹配成功: {file.name}")
                version = match.group(1)
                model_target = match.group(2) or "general"
                prompt_files.append({
                    "path": str(file),
                    "filename": file.name,
                    "version": version,
                    "model_target": model_target,
                })
            elif file.name == "bias-detection-prompt_v3.md":
                print(f"  - 特殊格式匹配: {file.name}")
                # Special case for the v3 prompt with different naming format
                prompt_files.append({
                    "path": str(file),
                    "filename": file.name,
                    "version": "3.0",
                    "model_target": "claude",
                })

        # 按版本号排序，最新版本优先
        prompt_files.sort(key=lambda x: [int(p) for p in x["version"].split(".")], reverse=True)
        return prompt_files

    def sync_prompt_files_to_db(self):
        """将prompt文件同步到数据库"""
        prompt_files = self.scan_prompt_files()
        print(f"找到 {len(prompt_files)} 个prompt文件需要同步")

        with db.session_scope() as session:
            for prompt_info in prompt_files:
                print(f"处理prompt: {prompt_info['filename']}, 版本: {prompt_info['version']}, 目标: {prompt_info['model_target']}")
                # 检查是否已存在
                existing_prompt = session.query(Prompt).filter_by(
                    version=prompt_info["version"],
                    model_target=prompt_info["model_target"]
                ).first()

                # 读取文件内容
                with open(prompt_info["path"], "r", encoding="utf-8") as f:
                    content = f.read()
                    print(f"  - 读取文件内容: {len(content)} 字符")

                if existing_prompt:
                    print(f"  - 更新已有prompt记录 (ID: {existing_prompt.id})")
                    # 更新已有记录
                    existing_prompt.content = content
                    existing_prompt.file_path = prompt_info["path"]
                else:
                    print(f"  - 创建新prompt记录")
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

    def get_latest_prompt(self, model_target: str = None) -> Optional[Prompt]:
        """获取最新版本的prompt

        Args:
            model_target: 目标模型名称，如果为None则获取通用版本

        Returns:
            最新版本的Prompt对象
        """
        with db.session_scope() as session:
            query = session.query(Prompt).filter(Prompt.is_active == True)

            if model_target:
                query = query.filter(Prompt.model_target == model_target)
            else:
                # 如果没有指定model_target，优先获取通用版本
                query = query.filter(Prompt.model_target == "general")

            # 按版本号排序，获取最新版本
            # 注意：这里假设版本号格式为"x.y.z"，需要按数字大小而非字符串排序
            # SQLite不支持复杂的字符串排序，这里简化处理仅按字符串排序
            # 在实际实现中可能需要更复杂的排序逻辑
            return query.order_by(Prompt.version.desc()).first()

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