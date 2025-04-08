"""
CLI命令定义
"""

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import click
import httpx
from click import Group
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table

from acolyte.cli.history_show import register_command as register_show_command
from acolyte.utils.logging import get_logger

# 创建日志记录器
logger = get_logger("acolyte.cli")

# 创建控制台对象
console = Console()


class AcolyteClient:
    """Acolyte API客户端"""

    def __init__(self, base_url: Optional[str] = None) -> None:
        """初始化客户端

        Args:
            base_url: API基础URL，默认从环境变量或配置文件获取
        """
        self.base_url = base_url or os.environ.get("ACOLYTE_API_URL", "http://localhost:8000/api")
        logger.info(f"初始化API客户端: {self.base_url}")
        # 确保base_url不为None，避免类型错误
        self.client = httpx.AsyncClient(base_url=str(self.base_url), timeout=60.0)

    async def close(self) -> None:
        """关闭客户端连接"""
        logger.debug("关闭API客户端连接")
        await self.client.aclose()

    async def check_connection(self) -> Tuple[bool, str]:
        """检查API服务连接状态

        Returns:
            (bool, str): 连接状态和错误信息（如果有）
        """
        logger.debug(f"检查API服务连接: {self.base_url}")
        try:
            # 尝试访问API根端点
            # 注意：API的根端点在 http://localhost:8000/，而不是 http://localhost:8000/api/
            # 所以我们需要使用绝对URL而不是相对路径
            # 确保基础URL不为None
            base_url = str(self.base_url)  # 将Optional[str]转换为str
            base_url_parts = base_url.split("/api")
            root_url = base_url_parts[0]  # 获取没有/api的基础URL
            logger.debug(f"访问根端点: {root_url}")

            # 使用httpx直接访问根端点，而不是通过self.client
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(root_url)
                response.raise_for_status()
                logger.debug("API服务连接正常")
                # 返回空字符串而不是None，以符合返回类型注解
                return True, ""
        except httpx.ConnectError as e:
            logger.error(f"无法连接到API服务: {str(e)}")
            return False, "无法连接到API服务，请确保服务已启动（运行 'uv run -m acolyte.main'）"
        except httpx.ConnectTimeout as e:
            logger.error(f"连接API服务超时: {str(e)}")
            return False, "连接API服务超时，请检查服务是否响应正常"
        except httpx.HTTPStatusError as e:
            logger.error(f"API服务返回错误状态: {e.response.status_code}")
            return False, f"API服务返回错误状态: {e.response.status_code}"
        except Exception as e:
            logger.error(f"检查API服务连接时发生未知错误: {str(e)}")
            return False, f"检查API服务连接时发生错误: {str(e)}"

    async def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息

        Returns:
            系统信息字典
        """
        logger.debug("获取系统信息")
        try:
            # 尝试从根端点获取基本信息
            # 确保基础URL不为None
            base_url = str(self.base_url)  # 将Optional[str]转换为str
            base_url_parts = base_url.split("/api")
            root_url = base_url_parts[0]  # 获取没有/api的基础URL
            logger.debug(f"访问根端点获取版本信息: {root_url}")

            # 使用httpx直接访问根端点
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(root_url)
                response.raise_for_status()
                root_info = response.json()
                version = root_info.get("version", "unknown")

            # 获取任务数量
            tasks_response = await self.client.get("/tasks")
            tasks = tasks_response.json() if tasks_response.status_code == 200 else []
            task_count = len(tasks)

            # 获取LLM数量
            llms_response = await self.client.get("/llms")
            llms = llms_response.json() if llms_response.status_code == 200 else []
            llm_count = len(llms)

            # 获取Prompt数量
            prompts_response = await self.client.get("/prompts")
            prompts = prompts_response.json() if prompts_response.status_code == 200 else []
            prompt_count = len(prompts)

            result = {
                "version": version,
                "database_status": "connected",  # 如果API响应正常，数据库应该是连接的
                "task_count": task_count,
                "llm_count": llm_count,
                "prompt_count": prompt_count,
            }

            logger.debug(f"成功获取系统信息: {result}")
            return result
        except Exception as e:
            logger.error(f"获取系统信息失败: {str(e)}")
            # 返回基本信息
            return {
                "version": "unknown",
                "database_status": "unknown",
                "task_count": "unknown",
                "llm_count": "unknown",
                "prompt_count": "unknown",
            }

    async def analyze(
        self,
        content: str,
        mode: str,
        llm_ids: Optional[List[int]] = None,
        prompt_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """分析内容

        Args:
            content: 要分析的文本内容
            mode: 处理模式，single/multiple/multiple_with_review
            llm_ids: LLM ID列表
            prompt_id: Prompt ID

        Returns:
            任务响应
        """
        logger.info(f"提交内容分析任务: 模式={mode}, 内容长度={len(content)}")
        logger.debug(f"LLM IDs: {llm_ids}, Prompt ID: {prompt_id}")

        # 创建请求数据字典，显式指定类型为Dict[str, Any]
        data: Dict[str, Any] = {
            "content": content,
            "processing_mode": mode,
        }
        if llm_ids:
            # 确保类型兼容，将list[int]转换为JSON兼容的列表
            data["llm_ids"] = [int(id) for id in llm_ids]
        if prompt_id:
            # 确保类型兼容，将int转换为JSON兼容的整数
            data["prompt_id"] = int(prompt_id)

        try:
            response = await self.client.post("/tasks", json=data)
            response.raise_for_status()
            result = response.json()
            logger.info(f"任务提交成功: ID={result.get('id')}")
            return result
        except httpx.HTTPStatusError as e:
            logger.error(
                f"提交任务失败: 状态码={e.response.status_code}, 错误={e.response.text}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(f"提交任务时发生异常: {str(e)}", exc_info=True)
            raise

    async def get_task(self, task_id: int) -> Dict[str, Any]:
        """获取任务

        Args:
            task_id: 任务ID

        Returns:
            任务信息
        """
        response = await self.client.get(f"/tasks/{task_id}")
        response.raise_for_status()
        return response.json()

    async def get_task_results(
        self,
        task_id: int,
        include_raw_response: bool = False
    ) -> List[Dict[str, Any]]:
        """获取任务结果

        Args:
            task_id: 任务ID
            include_raw_response: 是否包含原始响应

        Returns:
            任务结果列表
        """
        response = await self.client.get(
            f"/tasks/{task_id}/results", params={"include_raw_response": include_raw_response}
        )
        response.raise_for_status()
        return response.json()

    async def get_task_final_result(
        self,
        task_id: int,
        include_raw_response: bool = True
    ) -> Optional[Dict[str, Any]]:
        """获取任务最终结果

        Args:
            task_id: 任务ID
            include_raw_response: 是否包含原始响应

        Returns:
            任务最终结果
        """
        response = await self.client.get(
            f"/tasks/{task_id}/final-result", params={"include_raw_response": include_raw_response}
        )
        response.raise_for_status()
        return response.json()

    async def get_llms(self) -> List[Dict[str, Any]]:
        """获取LLM列表

        Returns:
            LLM配置列表
        """
        response = await self.client.get("/llms")
        response.raise_for_status()
        return response.json()

    async def get_prompts(self) -> List[Dict[str, Any]]:
        """获取Prompt列表

        Returns:
            Prompt列表
        """
        response = await self.client.get("/prompts")
        response.raise_for_status()
        return response.json()

    async def create_llm(
        self,
        name: str,
        api_key: str,
        base_url: str,
        model_name: str,
        description: Optional[str] = None,
        role: str = "normal",
        is_default: bool = False,
    ) -> Dict[str, Any]:
        """创建LLM配置

        Args:
            name: LLM名称
            api_key: API密钥
            base_url: 基础URL
            model_name: 模型名称
            description: 描述
            role: 角色
            is_default: 是否默认

        Returns:
            创建的LLM配置
        """
        data = {
            "name": name,
            "api_key": api_key,
            "base_url": base_url,
            "model_name": model_name,
            "description": description,
            "role": role,
            "is_default": is_default,
        }
        response = await self.client.post("/llms", json=data)
        response.raise_for_status()
        return response.json()

    async def test_llm(self, llm_id: int) -> Dict[str, Any]:
        """测试LLM连接

        Args:
            llm_id: LLM ID

        Returns:
            测试结果
        """
        response = await self.client.post(f"/llms/{llm_id}/test")
        response.raise_for_status()
        return response.json()

    async def set_default_llm(self, llm_id: int) -> Dict[str, Any]:
        """设置默认LLM

        Args:
            llm_id: LLM ID

        Returns:
            设置结果
        """
        response = await self.client.post(f"/llms/{llm_id}/set-default")
        response.raise_for_status()
        return response.json()

    async def sync_prompts(self, prompt_dir: Optional[str] = None) -> Dict[str, Any]:
        """同步Prompt

        Args:
            prompt_dir: 可选的prompt目录路径

        Returns:
            同步结果
        """
        data = {}
        if prompt_dir:
            data = {"prompt_dir": prompt_dir}
            logger.debug(f"使用prompt_dir参数: {prompt_dir}")

        response = await self.client.post("/prompts/sync", json=data)
        response.raise_for_status()
        return response.json()

    async def get_prompt(self, prompt_id: int) -> Dict[str, Any]:
        """获取特定Prompt内容

        Args:
            prompt_id: Prompt ID

        Returns:
            Prompt信息
        """
        response = await self.client.get(f"/prompts/{prompt_id}")
        response.raise_for_status()
        return response.json()

    async def delete_task(self, task_id: int) -> Dict[str, Any]:
        """删除特定任务

        Args:
            task_id: 任务ID

        Returns:
            删除结果
        """
        response = await self.client.delete(f"/tasks/{task_id}")
        response.raise_for_status()
        return response.json()

    async def clear_tasks(self, confirm: bool = False, status: Optional[str] = None) -> Dict[str, Any]:
        """清空所有任务

        Args:
            confirm: 确认删除
            status: 可选，按状态筛选

        Returns:
            清空结果
        """
        # 确保类型兼容，将bool转换为字符串，显式指定类型为Dict[str, Any]
        params: Dict[str, Any] = {"confirm": str(confirm).lower()}
        if status:
            params["status"] = str(status) if status else ""
        response = await self.client.delete("/tasks", params=params)
        response.raise_for_status()
        return response.json()

    async def export_config(self) -> Dict[str, Any]:
        """导出配置到文件

        Returns:
            导出结果
        """
        response = await self.client.post("/config/export")
        response.raise_for_status()
        return response.json()

    async def import_config(self, name: Optional[str] = None) -> Dict[str, Any]:
        """从配置文件导入LLM配置

        Args:
            name: 可选的LLM名称

        Returns:
            导入结果
        """
        params = {}
        if name:
            params = {"name": name}
        response = await self.client.post("/config/import", params=params)
        response.raise_for_status()
        return response.json()


# 自定义命令组类，用于控制命令的显示顺序
class OrderedGroup(Group):
    """自定义命令组，用于控制命令的显示顺序"""

    def __init__(self, name: Optional[str] = None, commands: Optional[Dict[str, Any]] = None, **attrs) -> None:
        super(OrderedGroup, self).__init__(name, commands, **attrs)
        # 定义命令的显示顺序
        self.command_order: List[str] = []

    def list_commands(self, _: Any) -> List[str]:
        """返回排序后的命令列表"""
        # 获取所有已注册的命令
        commands = self.commands.keys()
        # 按照预定义的顺序排序
        return sorted(
            commands,
            key=lambda x: (
                self.command_order.index(x) if x in self.command_order else len(self.command_order)
            ),
        )

    def get_command(self, _: Any, cmd_name: str) -> Any:
        """获取命令"""
        return self.commands.get(cmd_name)


# CLI命令组
@click.group(cls=OrderedGroup)
def cli() -> None:
    """Acolyte CLI - 内容分析评估系统命令行工具"""
    # 设置主命令组中命令的显示顺序
    cli.command_order = [
        "config",  # 配置管理
        "analyze",  # 分析命令
        "history",  # 历史记录
        "status",  # 状态检查
    ]


@cli.command()
def status() -> None:
    """检查API服务状态

    检查API服务是否正常运行，并显示系统信息。
    """

    async def _check_status() -> None:
        client = AcolyteClient()
        try:
            # 检查API服务连接
            connection_ok, error_message = await client.check_connection()

            if connection_ok:
                console.print("[bold green]状态:[/] API服务运行正常")
                console.print(f"[bold cyan]API地址:[/] {client.base_url}")

                # 获取系统信息
                try:
                    with console.status("[bold green]获取系统信息...[/]"):
                        system_info = await client.get_system_info()

                    # 显示系统信息
                    console.print("\n[bold]系统信息:[/]")
                    table = Table()
                    table.add_column("项目", style="cyan")
                    table.add_column("值", style="green")

                    table.add_row("版本", system_info.get("version", "unknown"))
                    table.add_row("数据库状态", system_info.get("database_status", "unknown"))
                    table.add_row("任务数量", str(system_info.get("task_count", "unknown")))
                    table.add_row("LLM数量", str(system_info.get("llm_count", "unknown")))
                    table.add_row("Prompt数量", str(system_info.get("prompt_count", "unknown")))

                    console.print(table)
                except Exception as e:
                    logger.warning(f"获取系统信息失败: {str(e)}")
                    console.print("[yellow]警告:[/] 无法获取系统详细信息")
            else:
                console.print("[bold red]状态:[/] API服务不可用")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保 API 服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
        finally:
            await client.close()

    # 运行异步函数
    asyncio.run(_check_status())


@cli.command()
@click.argument("file", type=click.Path(exists=True, readable=True), required=False)
@click.option("--text", "-t", help="要分析的文本内容")
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["single", "multiple", "multiple_with_review"]),
    default="single",
    help="处理模式",
)
@click.option("--llm", "-l", multiple=True, type=int, help="LLM ID，可多次指定")
@click.option("--llm-config", "-c", help="从配置文件使用的LLM名称")
@click.option("--prompt", "-p", type=int, help="Prompt ID")
@click.option("--wait/--no-wait", default=True, help="是否等待处理完成")
def analyze(file: Optional[str], text: Optional[str], mode: str, llm: Tuple[int, ...], llm_config: Optional[str], prompt: Optional[int], wait: bool) -> None:
    """分析内容

    可以通过文件或直接提供文本内容进行分析。

    例如: acolyte analyze content.txt --mode=multiple
    """

    async def _analyze() -> None:
        logger.info(f"启动内容分析: 模式={mode}, 等待结果={wait}")
        logger.debug(f"参数: file={file}, llm={llm}, llm_config={llm_config}, prompt={prompt}")

        client = AcolyteClient()
        try:
            # 首先检查API服务连接
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                logger.error(f"API服务连接失败: {error_message}")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保 API 服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
                console.print("[yellow]日志信息:[/] 查看 logs 目录中的日志文件获取更多信息")
                return
            # 获取内容
            content = ""
            if file:
                logger.info(f"从文件读取内容: {file}")
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        content = f.read()
                    logger.debug(f"读取文件成功: {len(content)} 字符")
                except Exception as e:
                    logger.error(f"读取文件失败: {str(e)}", exc_info=True)
                    console.print(f"[bold red]错误:[/] 读取文件 '{file}' 失败: {str(e)}")
                    return
            elif text:
                logger.info("使用直接提供的文本内容")
                content = text
            else:
                # 从标准输入读取
                if not sys.stdin.isatty():
                    logger.info("从标准输入读取内容")
                    content = sys.stdin.read()
                else:
                    logger.error("未提供任何内容来源")
                    console.print("[bold red]错误:[/] 必须提供文件、文本或通过管道输入内容")
                    return

            if not content or not content.strip():
                logger.error("内容为空")
                console.print("[bold red]错误:[/] 内容不能为空")
                return

            # 获取LLM ID列表
            llm_ids = []
            if isinstance(llm, tuple):
                for item in llm:
                    llm_ids.append(item)
            elif llm:  # 其他非空类型
                llm_ids = [llm]
            if llm_config:
                # 导入配置
                logger.info(f"尝试从配置文件导入LLM: {llm_config}")
                with console.status(f"[bold green]从配置导入LLM {llm_config}...[/]"):
                    try:
                        result = await client.import_config(llm_config)

                        if result["status"] == "success" and "llms" in result:
                            # 添加到ID列表
                            for imported_llm in result["llms"]:
                                llm_ids.append(imported_llm["id"])
                            logger.info(f"成功导入LLM: {llm_config}, ID: {llm_ids}")
                            console.print(f"[bold green]已导入LLM配置: {llm_config}[/]")
                        else:
                            logger.warning(f"未找到名为 {llm_config} 的LLM配置")
                            console.print(
                                f"[bold yellow]警告:[/] 未找到名为 {llm_config} 的LLM配置"
                            )
                    except Exception as e:
                        logger.error(f"导入LLM配置失败: {str(e)}", exc_info=True)
                        console.print(f"[bold red]导入LLM配置失败:[/] {str(e)}")
                        return

            # 显示处理中
            logger.info(f"提交任务: 模式={mode}, LLM IDs={llm_ids}, Prompt ID={prompt}")
            try:
                with console.status("[bold green]提交任务中...[/]"):
                    task = await client.analyze(content, mode, llm_ids if llm_ids else None, prompt)
                    task_id = task["id"]
                    logger.info(f"任务已提交: ID={task_id}")
                    console.print(f"[bold green]任务已提交[/] - ID: {task_id}")
            except Exception as e:
                logger.error(f"提交任务失败: {str(e)}", exc_info=True)
                console.print(f"[bold red]提交任务失败:[/] {str(e)}")
                return

            # 等待任务完成
            if wait:
                logger.info(f"等待任务 {task_id} 完成")
                task_status = task["status"]
                check_interval = 2  # 初始检查间隔(秒)
                max_check_interval = 10  # 最大检查间隔(秒)
                max_checks = 60  # 最大检查次数

                with Progress() as progress:
                    task_progress = progress.add_task("[cyan]处理中...", total=None)
                    status_check_count = 0
                    last_status = None

                    while task_status not in ["completed", "failed"]:
                        await asyncio.sleep(check_interval)
                        status_check_count += 1

                        # 超过最大检查次数则放弃等待
                        if status_check_count > max_checks:
                            logger.warning(f"达到最大检查次数({max_checks})，停止等待")
                            console.print(
                                f"[bold yellow]警告:[/] 达到最大等待时间，任务 {task_id} 仍在处理中"
                            )
                            break

                        try:
                            task_info = await client.get_task(task_id)
                            task_status = task_info["status"]

                            # 状态变化时重置检查间隔
                            if task_status != last_status:
                                logger.info(
                                    f"任务状态变更: {last_status or '初始'} -> {task_status}"
                                )
                                last_status = task_status
                                check_interval = 2  # 重置为初始检查间隔
                            else:
                                # 状态未变化时，逐渐增加检查间隔，但不超过最大值
                                # 将浮点数转换为整数
                                check_interval = int(min(check_interval * 1.5, max_check_interval))

                            logger.debug(
                                f"任务状态检查 #{status_check_count}: {task_status}，"
                                f"下次检查间隔: {check_interval:.1f}秒"
                            )

                            # 更新进度条描述
                            progress.update(
                                task_progress, description=f"[cyan]任务处理中 ({task_status})..."
                            )
                        except Exception as e:
                            logger.error(f"获取任务状态失败: {str(e)}", exc_info=True)
                            console.print(f"[bold red]获取任务状态失败:[/] {str(e)}")
                            break

                # 获取结果
                if task_status == "completed":
                    logger.info(f"任务 {task_id} 已完成，尝试获取最终结果")
                    try:
                        final_result = await client.get_task_final_result(task_id)
                        logger.info("成功获取任务最终结果")
                        # 显示结果
                        # 确保结果不为None再显示
                        if final_result is not None:
                            _display_result(final_result)
                        else:
                            console.print("[bold yellow]警告:[/] 未能获取到结果数据")
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 404:
                            logger.warning(f"任务 {task_id} 无最终结果，尝试获取所有结果")
                            # 获取所有结果
                            try:
                                results = await client.get_task_results(
                                    task_id, include_raw_response=True
                                )
                                logger.info(f"获取到 {len(results)} 个任务结果")
                                console.print(
                                    "[bold yellow]任务已完成，但无最终结果，显示所有结果:[/]"
                                )
                                for i, result in enumerate(results, 1):
                                    console.print(f"\n[bold]结果 {i}:[/]")
                                    _display_result(result)
                            except Exception as e2:
                                logger.error(f"获取任务结果失败: {str(e2)}", exc_info=True)
                                console.print(f"[bold red]获取任务结果失败:[/] {str(e2)}")
                        else:
                            logger.error(
                                f"获取任务最终结果失败: 状态码={e.response.status_code}, "
                                f"错误={e.response.text}",
                                exc_info=True,
                            )
                            console.print(f"[bold red]获取任务最终结果失败:[/] {str(e)}")
                else:
                    logger.error(f"任务 {task_id} 处理失败，最终状态: {task_status}")
                    console.print("[bold red]任务处理失败[/]")
        except Exception as e:
            logger.error(f"分析过程中发生异常: {str(e)}", exc_info=True)
            console.print(f"[bold red]执行分析时发生错误:[/] {str(e)}")
        finally:
            await client.close()

    def _display_result(result: Dict[str, Any]) -> None:
        """显示任务结果"""
        logger.debug(f"显示任务结果: ID={result.get('id', 'unknown')}")

        # 检查结果中的指标
        missing_metrics = []
        if result.get("bias_index") is None:
            missing_metrics.append("bias_index")
        if result.get("misleading_index") is None:
            missing_metrics.append("misleading_index")
        if result.get("hidden_intent_index") is None:
            missing_metrics.append("hidden_intent_index")
        if result.get("credibility_score") is None:
            missing_metrics.append("credibility_score")

        if missing_metrics:
            logger.warning(f"任务结果缺少部分指标: {', '.join(missing_metrics)}")

        # 显示评分
        table = Table(title="分析评分")
        table.add_column("指标", style="cyan")
        table.add_column("分数", style="green")

        if result.get("bias_index") is not None:
            bias_index = result["bias_index"]
            table.add_row("偏见指数 (BI)", f"{bias_index:.2f}")
            logger.info(f"偏见指数 (BI): {bias_index:.2f}")
        if result.get("misleading_index") is not None:
            misleading_index = result["misleading_index"]
            table.add_row("误导性指数 (MI)", f"{misleading_index:.2f}")
            logger.info(f"误导性指数 (MI): {misleading_index:.2f}")
        if result.get("hidden_intent_index") is not None:
            hidden_intent_index = result["hidden_intent_index"]
            table.add_row("隐藏意图指数 (HI)", f"{hidden_intent_index:.2f}")
            logger.info(f"隐藏意图指数 (HI): {hidden_intent_index:.2f}")
        if result.get("credibility_score") is not None:
            credibility_score = result["credibility_score"]
            table.add_row("综合可信度 (CS)", f"{credibility_score:.2f}")
            logger.info(f"综合可信度 (CS): {credibility_score:.2f}")

        console.print(table)

        # 显示原始响应
        if result.get("raw_response"):
            logger.debug("结果包含原始响应")
            console.print("\n[bold]详细分析:[/]")
            console.print(Markdown(result["raw_response"]))
        else:
            logger.debug("结果不包含原始响应")

    # 运行异步函数
    asyncio.run(_analyze())


@cli.group(cls=OrderedGroup)
def history() -> None:
    """历史任务记录管理"""
    pass


# 在所有history命令定义完成后设置显示顺序
# 这个函数将在模块定义结束时执行
def _set_history_command_order() -> None:
    # 使用hasattr检查是否有command_order属性，避免类型错误
    if hasattr(history, "command_order"):
        history.command_order = [
        "list",  # 列出历史任务
        "show",  # 显示任务结果
        "delete",  # 删除任务
        "clear",  # 清空任务
    ]


@history.command()
@click.option("--status", "-s", help="按状态筛选")
@click.option("--limit", "-l", type=int, default=10, help="显示数量限制")
def list(status: Optional[str], limit: int) -> None:
    """查看历史任务记录

    例如: acolyte history list --status=completed --limit=5
    """

    async def _list() -> None:
        client = AcolyteClient()
        try:
            # 检查API服务连接
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                logger.error(f"API服务连接失败: {error_message}")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保 API 服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
                return

            # 构建API请求参数，显式指定类型为Dict[str, Any]
            # 确保类型兼容，将参数转换为正确的类型
            params: Dict[str, Any] = {"limit": int(limit)}
            if status:
                # 确保类型兼容，将状态转换为字符串
                params["status"] = str(status)

            # 获取任务列表
            with console.status("[bold green]获取历史记录中...[/]"):
                response = await client.client.get("/tasks", params=params)
                response.raise_for_status()
                tasks = response.json()

            # 显示任务列表
            table = Table(title="任务历史记录")
            table.add_column("ID", style="cyan")
            table.add_column("处理模式", style="green")
            table.add_column("状态", style="yellow")
            table.add_column("创建时间", style="bright_blue")

            # 按ID从小到大排序
            sorted_tasks = sorted(tasks, key=lambda x: x["id"])

            for task in sorted_tasks:
                # 检查created_at字段是否存在
                created_at = task.get("created_at", "未知")

                # 格式化时间为友好的24小时制格式
                if created_at != "未知":
                    try:
                        # 解析ISO格式的时间字符串
                        import time
                        from datetime import datetime, timedelta, timezone

                        # 解析UTC时间
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

                        # 获取本地时区
                        local_tz_offset = -time.timezone // 3600  # 将秒转换为小时
                        local_tz = timezone(timedelta(hours=local_tz_offset))

                        # 将UTC时间转换为本地时间
                        local_dt = dt.replace(tzinfo=timezone.utc).astimezone(local_tz)

                        # 格式化为友好的24小时制格式
                        created_at = local_dt.strftime("%Y-%m-%d %H:%M:%S")

                        logger.debug(f"时间转换: UTC {dt.isoformat()} -> 本地 {created_at}")
                    except Exception as e:
                        logger.warning(f"时间格式化失败: {e}")

                table.add_row(str(task["id"]), task["processing_mode"], task["status"], created_at)

            console.print(table)

        finally:
            await client.close()

    # 运行异步函数
    asyncio.run(_list())


@history.command()
@click.argument("task_id", type=int)
def delete(task_id: int) -> None:
    """删除特定任务

    例如: acolyte history delete 123
    """

    async def _delete() -> None:
        client = AcolyteClient()
        try:
            # 检查API服务连接
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                logger.error(f"API服务连接失败: {error_message}")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保 API 服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
                return

            # 先获取任务信息
            try:
                with console.status(f"[bold green]获取任务 {task_id} 信息...[/]"):
                    task = await client.get_task(task_id)

                # 显示任务信息
                console.print(
                    Panel(
                        f"ID: {task['id']}\n"
                        f"处理模式: {task['processing_mode']}\n"
                        f"状态: {task['status']}\n"
                        f"创建时间: {task.get('created_at', '未知')}",
                        title="将删除以下任务",
                    )
                )

                # 确认删除
                confirm = click.confirm("确认删除?", default=False)
                if not confirm:
                    console.print("[bold yellow]已取消删除[/]")
                    return

                # 执行删除
                with console.status(f"[bold green]删除任务 {task_id}...[/]"):
                    result = await client.delete_task(task_id)

                console.print(f"[bold green]{result['message']}[/]")

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    console.print(f"[bold red]错误:[/] ID为{task_id}的任务不存在")
                else:
                    console.print(f"[bold red]错误:[/] {str(e)}")

        finally:
            await client.close()

    # 运行异步函数
    asyncio.run(_delete())


@history.command()
@click.option("--status", "-s", help="可选，只清空特定状态的任务")
@click.option("--force", "-f", is_flag=True, help="跳过确认直接执行")
def clear(status: Optional[str], force: bool) -> None:
    """清空所有任务历史

    例如: acolyte history clear --status=failed
    """

    async def _clear() -> None:
        client = AcolyteClient()
        try:
            # 检查API服务连接
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                logger.error(f"API服务连接失败: {error_message}")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保 API 服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
                return

            # 提示确认
            if status:
                message = f"将清空所有[bold]{status}[/]状态的任务"
            else:
                message = "将清空[bold]所有[/]任务历史记录"

            console.print(f"[bold yellow]警告:[/] {message}")

            # 如果没有使用--force，请求用户确认
            if not force and not click.confirm("确认清空?", default=False):
                console.print("[bold yellow]已取消操作[/]")
                return

            # 执行清空
            with console.status("[bold green]清空任务历史中...[/]"):
                result = await client.clear_tasks(confirm=True, status=status)

            console.print(f"[bold green]{result['message']}[/]")

        except httpx.HTTPStatusError as e:
            console.print(f"[bold red]错误:[/] {e.response.json().get('detail', str(e))}")
        finally:
            await client.close()

    # 运行异步函数
    asyncio.run(_clear())


# 注册命令
register_show_command(history)


@cli.group(cls=OrderedGroup)
def config() -> None:
    """配置管理"""
    # 设置config命令组中命令的显示顺序
    # 使用hasattr检查是否有command_order属性，避免类型错误
    if hasattr(config, "command_order"):
        config.command_order = [
        # LLM相关命令
        "list-llms",
        "add-llm",
        "set-default",
        "delete-llm",
        # Prompt相关命令
        "list-prompts",
        "show-prompt",
        "sync-prompts",
        "delete-prompt",
        # 配置导入导出命令
        "import-config",
        "export-config",
    ]
    pass


@config.command()
def list_llms() -> None:
    """列出所有LLM配置"""

    async def _list_llms() -> None:
        client = AcolyteClient()
        try:
            # 检查API服务连接
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                logger.error(f"API服务连接失败: {error_message}")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保 API 服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
                return

            with console.status("[bold green]获取LLM配置中...[/]"):
                llms = await client.get_llms()

            # 显示LLM列表
            table = Table(title="LLM配置")
            table.add_column("ID", style="cyan")
            table.add_column("名称", style="green")
            table.add_column("模型", style="bright_blue")
            table.add_column("角色", style="yellow")
            table.add_column("默认", style="magenta")

            for llm in llms:
                table.add_row(
                    str(llm["id"]),
                    llm["name"],
                    llm["model_name"],
                    llm["role"],
                    "✓" if llm["is_default"] else "",
                )

            console.print(table)

        finally:
            await client.close()

    # 运行异步函数
    asyncio.run(_list_llms())


@config.command()
@click.argument("llm_id", type=int)
def set_default(llm_id: int) -> None:
    """设置指定ID的LLM为默认

    例如: acolyte config set-default 1
    """

    async def _set_default() -> None:
        client = AcolyteClient()
        try:
            # 检查API服务连接
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                logger.error(f"API服务连接失败: {error_message}")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保API服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
                return

            with console.status(f"[bold green]设置LLM {llm_id}为默认...[/]"):
                result = await client.set_default_llm(llm_id)

            console.print(
                f"[bold green]成功设置LLM为默认[/] - ID: {result['id']}, 名称: {result['name']}"
            )

        except httpx.HTTPStatusError as e:
            error_message = e.response.json().get("detail", str(e))
            console.print(f"[bold red]错误:[/] {error_message}")
        except Exception as e:
            console.print(f"[bold red]错误:[/] {str(e)}")
        finally:
            await client.close()

    # 运行异步函数
    asyncio.run(_set_default())


@config.command()
@click.argument("llm_id", type=int)
def delete_llm(llm_id: int) -> None:
    """删除指定ID的LLM配置

    例如: acolyte config delete-llm 3
    """

    async def _delete_llm() -> None:
        client = AcolyteClient()
        try:
            # 检查API服务连接
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                logger.error(f"API服务连接失败: {error_message}")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保 API 服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
                return

            # 先获取LLM信息以显示
            try:
                with console.status(f"[bold green]获取LLM {llm_id}信息...[/]"):
                    response = await client.client.get(f"/llms/{llm_id}")
                    response.raise_for_status()
                    llm = response.json()

                # 确认删除
                console.print("将删除以下LLM配置:")
                console.print(
                    Panel(
                        f"ID: {llm['id']}\n"
                        f"名称: {llm['name']}\n"
                        f"模型: {llm['model_name']}\n"
                        f"角色: {llm['role']}\n"
                        f"默认: {'是' if llm['is_default'] else '否'}",
                        title="LLM配置详情",
                    )
                )

                confirm = click.confirm("确认删除?", default=False)
                if not confirm:
                    console.print("[bold yellow]已取消删除[/]")
                    return

                # 执行删除
                with console.status(f"[bold green]删除LLM {llm_id}...[/]"):
                    response = await client.client.delete(f"/llms/{llm_id}")
                    response.raise_for_status()
                    result = response.json()

                console.print(f"[bold green]{result['message']}[/]")

                # 提示用户可以手动导出配置
                console.print(
                    "[bold yellow]提示: 如需更新配置文件，请手动运行 'config export-config' 命令[/]"
                )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    console.print(f"[bold red]错误:[/] ID为{llm_id}的LLM配置不存在")
                else:
                    console.print(f"[bold red]错误:[/] {str(e)}")

        finally:
            await client.close()

    # 运行异步函数
    asyncio.run(_delete_llm())


@config.command()
@click.option("--name", "-n", required=True, help="LLM名称")
@click.option("--api-key", "-k", required=True, help="API密钥")
@click.option("--base-url", "-u", required=True, help="基础URL")
@click.option("--model", "-m", required=True, help="模型名称")
@click.option("--description", "-d", help="描述")
@click.option(
    "--role", "-r", type=click.Choice(["normal", "reviewer"]), default="normal", help="角色"
)
@click.option("--default/--no-default", default=False, help="是否设为默认")
@click.option("--save-to-config/--no-save-to-config", default=True, help="是否保存到配置文件")
def add_llm(name: str, api_key: str, base_url: str, model: str, description: str, role: str, default: bool, save_to_config: bool) -> None:
    """添加LLM配置

    例如: acolyte config add-llm -n "Claude-3" -k "sk-..." \
        -u "https://api.anthropic.com" -m "claude-3-opus-20240229" -r reviewer
    """

    async def _add_llm() -> None:
        client = AcolyteClient()
        try:
            # 检查API服务连接
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                logger.error(f"API服务连接失败: {error_message}")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保 API 服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
                return

            with console.status("[bold green]添加LLM配置中...[/]"):
                llm = await client.create_llm(
                    name=name,
                    api_key=api_key,
                    base_url=base_url,
                    model_name=model,
                    description=description,
                    role=role,
                    is_default=default,
                )

            console.print(f"[bold green]LLM配置添加成功[/] - ID: {llm['id']}")

            # 测试连接
            with console.status("[bold green]测试LLM连接中...[/]"):
                test_result = await client.test_llm(llm["id"])

            if test_result["success"]:
                console.print(
                    f"[bold green]连接测试成功[/] - 响应时间: {test_result['response_time']}秒"
                )
            else:
                console.print(
                    f"[bold red]连接测试失败[/] - {test_result.get('message', '未知错误')}"
                )

            # 提示用户可以手动导出配置
            if save_to_config:
                console.print(
                    "[bold yellow]提示: 如需更新配置文件，请手动运行 'config export-config' 命令[/]"
                )

        finally:
            await client.close()

    # 运行异步函数
    asyncio.run(_add_llm())


@config.command()
def export_config() -> None:
    """将数据库中的LLM配置导出到配置文件"""

    async def _export_config() -> None:
        client = AcolyteClient()
        try:
            # 检查API服务连接
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                logger.error(f"API服务连接失败: {error_message}")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保 API 服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
                return

            with console.status("[bold green]导出配置中...[/]"):
                result = await client.export_config()
            console.print(f"[bold green]{result['message']}[/]")
        finally:
            await client.close()

    # 运行异步函数
    asyncio.run(_export_config())


@config.command()
@click.option("--name", "-n", help="指定要导入的LLM名称")
def import_config(name: Optional[str]) -> None:
    """从配置文件导入LLM配置到数据库

    例如: acolyte config import-config -n "Claude-3"
    """

    async def _import_config() -> None:
        client = AcolyteClient()
        try:
            # 检查API服务连接
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                logger.error(f"API服务连接失败: {error_message}")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保 API 服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
                return

            with console.status("[bold green]导入配置中...[/]"):
                result = await client.import_config(name)

            if result["status"] == "success":
                console.print(f"[bold green]{result['message']}[/]")

                # 显示导入的配置
                imported_llms = result.get("llms", [])
                if imported_llms:
                    table = Table(title="导入的LLM配置")
                    table.add_column("ID", style="cyan")
                    table.add_column("名称", style="green")
                    table.add_column("模型", style="red")
                    table.add_column("角色", style="yellow")

                    for llm in imported_llms:
                        table.add_row(str(llm["id"]), llm["name"], llm["model_name"], llm["role"])

                    console.print(table)
            else:
                console.print(f"[bold yellow]{result['message']}[/]")

        except Exception as e:
            console.print(f"[bold red]导入失败: {str(e)}[/]")
        finally:
            await client.close()

    # 运行异步函数
    asyncio.run(_import_config())


@config.command()
def list_prompts() -> None:
    """列出所有Prompt配置"""

    async def _list_prompts() -> None:
        client = AcolyteClient()
        try:
            # 检查API服务连接
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                logger.error(f"API服务连接失败: {error_message}")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保 API 服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
                return

            with console.status("[bold green]获取Prompt配置中...[/]"):
                prompts = await client.get_prompts()

            # 显示Prompt列表
            table = Table(title="Prompt配置")
            table.add_column("ID", style="cyan")
            table.add_column("版本", style="green")
            table.add_column("目标模型", style="bright_blue")
            table.add_column("状态", style="yellow")

            for prompt in prompts:
                table.add_row(
                    str(prompt["id"]),
                    prompt["version"],
                    prompt["model_target"] or "通用",
                    "激活" if prompt["is_active"] else "禁用",
                )

            console.print(table)

        finally:
            await client.close()

    # 运行异步函数
    asyncio.run(_list_prompts())


@config.command()
@click.option("--prompt-dir", "-d", help="指定prompt目录路径")
def sync_prompts(prompt_dir: Optional[str]) -> None:
    """同步Prompt文件到数据库

    例如: acolyte config sync-prompts --prompt-dir=/path/to/prompts
    """

    async def _sync_prompts() -> None:
        client = AcolyteClient()
        try:
            # 检查API服务连接
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                logger.error(f"API服务连接失败: {error_message}")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保 API 服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
                return

            # 使用环境变量获取prompt_dir
            env_prompt_dir = os.environ.get("ACOLYTE_PROMPT_DIR")

            # 命令行参数优先于环境变量
            final_prompt_dir = prompt_dir or env_prompt_dir
            logger.info(f"使用prompt目录: {final_prompt_dir}")

            with console.status("[bold green]同步Prompt文件中...[/]"):
                result = await client.sync_prompts(prompt_dir=final_prompt_dir)

            console.print(f"[bold green]{result['message']}[/]")

        finally:
            await client.close()

    # 运行异步函数
    asyncio.run(_sync_prompts())


@config.command()
@click.argument("prompt_id", type=int)
def show_prompt(prompt_id: int) -> None:
    """显示特定Prompt内容

    例如: acolyte config show-prompt 1
    """

    async def _show_prompt() -> None:
        client = AcolyteClient()
        try:
            # 检查API服务连接
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                logger.error(f"API服务连接失败: {error_message}")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保 API 服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
                return

            # 获取Prompt内容
            with console.status(f"[bold green]获取Prompt {prompt_id}内容...[/]"):
                prompt = await client.get_prompt(prompt_id)

            # 显示Prompt信息
            panel_content = (
                f"ID: {prompt['id']}\n"
                f"版本: {prompt['version']}\n"
                f"目标模型: {prompt['model_target'] or '通用'}\n"
                f"状态: {'激活' if prompt['is_active'] else '禁用'}"
            )

            # 如果存在创建时间，显示它
            if "created_at" in prompt and prompt["created_at"]:
                panel_content += f"\n创建时间: {prompt['created_at']}"

            console.print(Panel(panel_content, title="Prompt信息"))

            # 显示Prompt内容
            if prompt.get("content"):
                console.print("\n[bold]Prompt内容:[/]")
                console.print(Markdown(prompt["content"]))
            else:
                # 如果没有内容，尝试读取文件
                file_path = prompt.get("file_path")
                if file_path and os.path.exists(file_path):
                    with console.status(f"[bold green]从文件读取Prompt内容: {file_path}[/]"):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                            console.print("\n[bold]Prompt内容 (从文件读取):[/]")
                            console.print(Markdown(content))
                        except Exception as e:
                            console.print(f"[bold red]读取提示词文件失败:[/] {str(e)}")
                else:
                    console.print("[bold yellow]提示词内容不可用[/]")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                console.print(f"[bold red]错误:[/] ID为{prompt_id}的Prompt不存在")
            else:
                console.print(f"[bold red]错误:[/] {str(e)}")
        finally:
            await client.close()

    # 运行异步函数
    asyncio.run(_show_prompt())


@config.command()
@click.argument("prompt_id", type=int)
@click.option("--delete-file", "-f", is_flag=True, help="同时删除提示词文件")
@click.option("--force", is_flag=True, help="跳过确认直接删除")
def delete_prompt(prompt_id: int, delete_file: bool, force: bool) -> None:
    """删除特定提示词

    例如: acolyte config delete-prompt 1 --delete-file
    """

    async def _delete_prompt() -> None:
        client = AcolyteClient()
        try:
            # 检查API服务连接
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                logger.error(f"API服务连接失败: {error_message}")
                console.print(f"[bold red]错误:[/] {error_message}")
                console.print(
                    "[yellow]提示:[/] 请确保 API 服务已启动，"
                    "可以运行 'uv run -m acolyte.main' 启动服务"
                )
                return

            # 先获取提示词信息以显示
            try:
                with console.status(f"[bold green]获取提示词 {prompt_id}信息...[/]"):
                    prompt = await client.get_prompt(prompt_id)

                # 显示提示词信息
                panel_content = (
                    f"ID: {prompt['id']}\n"
                    f"版本: {prompt['version']}\n"
                    f"目标模型: {prompt['model_target'] or '通用'}\n"
                    f"状态: {'激活' if prompt['is_active'] else '禁用'}"
                )

                if "file_path" in prompt and prompt["file_path"]:
                    panel_content += f"\n文件路径: {prompt['file_path']}"

                console.print(Panel(panel_content, title="将删除以下提示词"))

                # 确认删除
                if not force and not click.confirm("确认删除?", default=False):
                    console.print("[bold yellow]已取消删除[/]")
                    return

                # 执行删除
                with console.status(f"[bold green]删除提示词 {prompt_id}...[/]"):
                    # 直接调用API删除提示词
                    params = {"delete_file": delete_file}
                    response = await client.client.delete(f"/prompts/{prompt_id}", params=params)
                    response.raise_for_status()
                    result = response.json()

                console.print(f"[bold green]{result['message']}[/]")

                # 如果同时删除了文件，显示文件删除状态
                if delete_file:
                    file_status = "已删除" if result.get("file_deleted", False) else "未删除"
                    console.print(f"[bold]提示词文件: {file_status}[/]")

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    console.print(f"[bold red]错误:[/] ID为{prompt_id}的提示词不存在")
                else:
                    console.print(f"[bold red]错误:[/] {str(e)}")

        finally:
            await client.close()

    # 运行异步函数
    asyncio.run(_delete_prompt())


# 设置命令组的显示顺序
_set_history_command_order()


# 设置主命令组的显示顺序
def _set_cli_command_order() -> None:
    cli.command_order = [
        "config",  # 配置管理
        "analyze",  # 分析命令
        "history",  # 历史记录
        "status",  # 状态检查
    ]


_set_cli_command_order()

if __name__ == "__main__":
    cli()
