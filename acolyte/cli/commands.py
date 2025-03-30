"""
CLI命令定义
"""
import asyncio
import json
import os
import sys
from typing import List, Optional

import click
import httpx
import rich
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table

from acolyte.core.llm.config import export_llm_config_to_file, import_llm_config_from_file

# 创建控制台对象
console = Console()


class AcolyteClient:
    """Acolyte API客户端"""

    def __init__(self, base_url=None):
        """初始化客户端

        Args:
            base_url: API基础URL，默认从环境变量或配置文件获取
        """
        self.base_url = base_url or os.environ.get("ACOLYTE_API_URL", "http://localhost:8000/api")
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)

    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()

    async def analyze(self, content: str, mode: str, llm_ids: List[int] = None, prompt_id: int = None):
        """分析内容

        Args:
            content: 要分析的文本内容
            mode: 处理模式，single/multiple/multiple_with_review
            llm_ids: LLM ID列表
            prompt_id: Prompt ID

        Returns:
            任务响应
        """
        data = {
            "content": content,
            "processing_mode": mode,
        }
        if llm_ids:
            data["llm_ids"] = llm_ids
        if prompt_id:
            data["prompt_id"] = prompt_id

        response = await self.client.post("/tasks", json=data)
        response.raise_for_status()
        return response.json()

    async def get_task(self, task_id: int):
        """获取任务

        Args:
            task_id: 任务ID

        Returns:
            任务信息
        """
        response = await self.client.get(f"/tasks/{task_id}")
        response.raise_for_status()
        return response.json()

    async def get_task_results(self, task_id: int, include_raw_response: bool = False):
        """获取任务结果

        Args:
            task_id: 任务ID
            include_raw_response: 是否包含原始响应

        Returns:
            任务结果列表
        """
        response = await self.client.get(
            f"/tasks/{task_id}/results", 
            params={"include_raw_response": include_raw_response}
        )
        response.raise_for_status()
        return response.json()

    async def get_task_final_result(self, task_id: int, include_raw_response: bool = True):
        """获取任务最终结果

        Args:
            task_id: 任务ID
            include_raw_response: 是否包含原始响应

        Returns:
            任务最终结果
        """
        response = await self.client.get(
            f"/tasks/{task_id}/final-result",
            params={"include_raw_response": include_raw_response}
        )
        response.raise_for_status()
        return response.json()

    async def get_llms(self):
        """获取LLM列表

        Returns:
            LLM配置列表
        """
        response = await self.client.get("/llms")
        response.raise_for_status()
        return response.json()

    async def get_prompts(self):
        """获取Prompt列表

        Returns:
            Prompt列表
        """
        response = await self.client.get("/prompts")
        response.raise_for_status()
        return response.json()

    async def create_llm(self, name: str, api_key: str, base_url: str, model_name: str, 
                         description: str = None, role: str = "normal", is_default: bool = False):
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
            "is_default": is_default
        }
        response = await self.client.post("/llms", json=data)
        response.raise_for_status()
        return response.json()

    async def test_llm(self, llm_id: int):
        """测试LLM连接

        Args:
            llm_id: LLM ID

        Returns:
            测试结果
        """
        response = await self.client.post(f"/llms/{llm_id}/test")
        response.raise_for_status()
        return response.json()

    async def sync_prompts(self):
        """同步Prompt

        Returns:
            同步结果
        """
        response = await self.client.post("/prompts/sync")
        response.raise_for_status()
        return response.json()
        
    async def get_prompt(self, prompt_id: int):
        """获取特定Prompt内容
        
        Args:
            prompt_id: Prompt ID
            
        Returns:
            Prompt信息
        """
        response = await self.client.get(f"/prompts/{prompt_id}")
        response.raise_for_status()
        return response.json()


# CLI命令组
@click.group()
def cli():
    """Acolyte CLI - 内容分析评估系统命令行工具"""
    pass


@cli.command()
@click.argument("file", type=click.Path(exists=True, readable=True), required=False)
@click.option("--text", "-t", help="要分析的文本内容")
@click.option("--mode", "-m", type=click.Choice(["single", "multiple", "multiple_with_review"]), 
              default="single", help="处理模式")
@click.option("--llm", "-l", multiple=True, type=int, help="LLM ID，可多次指定")
@click.option("--llm-config", "-c", help="从配置文件使用的LLM名称")
@click.option("--prompt", "-p", type=int, help="Prompt ID")
@click.option("--wait/--no-wait", default=True, help="是否等待处理完成")
def analyze(file, text, mode, llm, llm_config, prompt, wait):
    """分析内容

    可以通过文件或直接提供文本内容进行分析。
    
    例如: acolyte analyze content.txt --mode=multiple
    """
    async def _analyze():
        client = AcolyteClient()
        try:
            # 获取内容
            content = ""
            if file:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
            elif text:
                content = text
            else:
                # 从标准输入读取
                if not sys.stdin.isatty():
                    content = sys.stdin.read()
                else:
                    console.print("[bold red]错误:[/] 必须提供文件、文本或通过管道输入内容")
                    return

            # 如果指定了配置文件中的LLM名称，导入它
            llm_ids = list(llm)
            if llm_config:
                # 导入配置
                with console.status(f"[bold green]从配置导入LLM {llm_config}...[/]"):
                    imported_llms = import_llm_config_from_file(llm_config)
                    
                if imported_llms:
                    # 添加到ID列表
                    for imported_llm in imported_llms:
                        llm_ids.append(imported_llm.id)
                    console.print(f"[bold green]已导入LLM配置: {llm_config}[/]")
                else:
                    console.print(f"[bold yellow]警告:[/] 未找到名为 {llm_config} 的LLM配置")

            # 显示处理中
            with console.status("[bold green]提交任务中...[/]"):
                task = await client.analyze(content, mode, llm_ids if llm_ids else None, prompt)
                task_id = task["id"]
                console.print(f"[bold green]任务已提交[/] - ID: {task_id}")

            # 等待任务完成
            if wait:
                task_status = task["status"]
                with Progress() as progress:
                    task_progress = progress.add_task("[cyan]处理中...", total=None)
                    while task_status not in ["completed", "failed"]:
                        await asyncio.sleep(2)
                        task_info = await client.get_task(task_id)
                        task_status = task_info["status"]

                # 获取结果
                if task_status == "completed":
                    try:
                        final_result = await client.get_task_final_result(task_id)
                        # 显示结果
                        _display_result(final_result)
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 404:
                            # 获取所有结果
                            results = await client.get_task_results(task_id, include_raw_response=True)
                            console.print("[bold yellow]任务已完成，但无最终结果，显示所有结果:[/]")
                            for i, result in enumerate(results, 1):
                                console.print(f"\n[bold]结果 {i}:[/]")
                                _display_result(result)
                        else:
                            raise e
                else:
                    console.print("[bold red]任务处理失败[/]")
        finally:
            await client.close()

    def _display_result(result):
        """显示任务结果"""
        # 显示评分
        table = Table(title="分析评分")
        table.add_column("指标", style="cyan")
        table.add_column("分数", style="green")
        
        if result.get("bias_index") is not None:
            table.add_row("偏见指数 (BI)", f"{result['bias_index']:.2f}")
        if result.get("misleading_index") is not None:
            table.add_row("误导性指数 (MI)", f"{result['misleading_index']:.2f}")
        if result.get("hidden_intent_index") is not None:
            table.add_row("隐藏意图指数 (HI)", f"{result['hidden_intent_index']:.2f}")
        if result.get("credibility_score") is not None:
            table.add_row("综合可信度 (CS)", f"{result['credibility_score']:.2f}")
            
        console.print(table)
        
        # 显示原始响应
        if result.get("raw_response"):
            console.print("\n[bold]详细分析:[/]")
            console.print(Markdown(result["raw_response"]))

    # 运行异步函数
    asyncio.run(_analyze())


@cli.command()
@click.option("--status", "-s", help="按状态筛选")
@click.option("--limit", "-l", type=int, default=10, help="显示数量限制")
def history(status, limit):
    """查看历史任务记录
    
    例如: acolyte history --status=completed --limit=5
    """
    async def _history():
        client = AcolyteClient()
        try:
            # 构建API请求参数
            params = {"limit": limit}
            if status:
                params["status"] = status
                
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
            table.add_column("创建时间", style="blue")
            
            for task in tasks:
                table.add_row(
                    str(task["id"]),
                    task["processing_mode"],
                    task["status"],
                    task["created_at"]
                )
                
            console.print(table)
            
        finally:
            await client.close()
            
    # 运行异步函数
    asyncio.run(_history())


@cli.command()
@click.argument("task_id", type=int)
@click.option("--raw/--no-raw", default=False, help="是否显示原始响应")
def show(task_id, raw):
    """显示特定任务结果
    
    例如: acolyte show 123 --raw
    """
    async def _show():
        client = AcolyteClient()
        try:
            # 获取任务信息
            with console.status("[bold green]获取任务信息中...[/]"):
                task = await client.get_task(task_id)
                console.print(Panel(f"任务ID: {task['id']}\n"
                                  f"处理模式: {task['processing_mode']}\n"
                                  f"状态: {task['status']}\n"
                                  f"创建时间: {task['created_at']}",
                                  title="任务信息"))
            
            # 获取最终结果
            try:
                final_result = await client.get_task_final_result(task_id, include_raw_response=raw)
                
                # 显示评分
                table = Table(title="分析评分")
                table.add_column("指标", style="cyan")
                table.add_column("分数", style="green")
                
                if final_result.get("bias_index") is not None:
                    table.add_row("偏见指数 (BI)", f"{final_result['bias_index']:.2f}")
                if final_result.get("misleading_index") is not None:
                    table.add_row("误导性指数 (MI)", f"{final_result['misleading_index']:.2f}")
                if final_result.get("hidden_intent_index") is not None:
                    table.add_row("隐藏意图指数 (HI)", f"{final_result['hidden_intent_index']:.2f}")
                if final_result.get("credibility_score") is not None:
                    table.add_row("综合可信度 (CS)", f"{final_result['credibility_score']:.2f}")
                    
                console.print(table)
                
                # 显示原始响应
                if raw and final_result.get("raw_response"):
                    console.print("\n[bold]详细分析:[/]")
                    console.print(Markdown(final_result["raw_response"]))
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    console.print("[bold yellow]任务无最终结果[/]")
                    
                    # 如果是multiple模式，显示所有结果
                    if task["processing_mode"] in ["multiple", "multiple_with_review"]:
                        results = await client.get_task_results(task_id, include_raw_response=raw)
                        if results:
                            console.print("[bold]所有结果:[/]")
                            for i, result in enumerate(results, 1):
                                console.print(f"\n[bold cyan]结果 {i}:[/]")
                                # 显示评分
                                table = Table()
                                table.add_column("指标", style="cyan")
                                table.add_column("分数", style="green")
                                
                                if result.get("bias_index") is not None:
                                    table.add_row("偏见指数 (BI)", f"{result['bias_index']:.2f}")
                                if result.get("misleading_index") is not None:
                                    table.add_row("误导性指数 (MI)", f"{result['misleading_index']:.2f}")
                                if result.get("hidden_intent_index") is not None:
                                    table.add_row("隐藏意图指数 (HI)", f"{result['hidden_intent_index']:.2f}")
                                if result.get("credibility_score") is not None:
                                    table.add_row("综合可信度 (CS)", f"{result['credibility_score']:.2f}")
                                    
                                console.print(table)
                                
                                # 显示原始响应
                                if raw and result.get("raw_response"):
                                    console.print("\n[bold]详细分析:[/]")
                                    console.print(Markdown(result["raw_response"]))
                        else:
                            console.print("[bold yellow]无任何结果[/]")
                else:
                    raise e
                    
        finally:
            await client.close()
            
    # 运行异步函数
    asyncio.run(_show())


@cli.group()
def config():
    """配置管理"""
    pass


@config.command()
def list_llms():
    """列出所有LLM配置"""
    async def _list_llms():
        client = AcolyteClient()
        try:
            with console.status("[bold green]获取LLM配置中...[/]"):
                llms = await client.get_llms()
                
            # 显示LLM列表
            table = Table(title="LLM配置")
            table.add_column("ID", style="cyan")
            table.add_column("名称", style="green")
            table.add_column("模型", style="blue")
            table.add_column("角色", style="yellow")
            table.add_column("默认", style="magenta")
            
            for llm in llms:
                table.add_row(
                    str(llm["id"]),
                    llm["name"],
                    llm["model_name"],
                    llm["role"],
                    "✓" if llm["is_default"] else ""
                )
                
            console.print(table)
                
        finally:
            await client.close()
            
    # 运行异步函数
    asyncio.run(_list_llms())


@config.command()
@click.argument("llm_id", type=int)
def delete_llm(llm_id):
    """删除指定ID的LLM配置
    
    例如: acolyte config delete-llm 3
    """
    async def _delete_llm():
        client = AcolyteClient()
        try:
            # 先获取LLM信息以显示
            try:
                with console.status(f"[bold green]获取LLM {llm_id}信息...[/]"):
                    response = await client.client.get(f"/llms/{llm_id}")
                    response.raise_for_status()
                    llm = response.json()
                    
                # 确认删除
                console.print(f"将删除以下LLM配置:")
                console.print(Panel(
                    f"ID: {llm['id']}\n"
                    f"名称: {llm['name']}\n"
                    f"模型: {llm['model_name']}\n"
                    f"角色: {llm['role']}\n"
                    f"默认: {'是' if llm['is_default'] else '否'}",
                    title="LLM配置详情"
                ))
                
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
                
                # 导出更新后的配置到文件
                with console.status("[bold green]更新配置文件...[/]"):
                    from acolyte.core.llm.config import export_llm_config_to_file
                    if export_llm_config_to_file():
                        console.print("[bold green]配置文件已更新[/]")
                    else:
                        console.print("[bold yellow]配置文件更新失败[/]")
                    
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
@click.option("--role", "-r", type=click.Choice(["normal", "reviewer"]), default="normal", help="角色")
@click.option("--default/--no-default", default=False, help="是否设为默认")
@click.option("--save-to-config/--no-save-to-config", default=True, help="是否保存到配置文件")
def add_llm(name, api_key, base_url, model, description, role, default, save_to_config):
    """添加LLM配置
    
    例如: acolyte config add-llm -n "Claude-3" -k "sk-..." -u "https://api.anthropic.com" -m "claude-3-opus-20240229" -r reviewer
    """
    async def _add_llm():
        client = AcolyteClient()
        try:
            with console.status("[bold green]添加LLM配置中...[/]"):
                llm = await client.create_llm(
                    name=name,
                    api_key=api_key,
                    base_url=base_url,
                    model_name=model,
                    description=description,
                    role=role,
                    is_default=default
                )
                
            console.print(f"[bold green]LLM配置添加成功[/] - ID: {llm['id']}")
            
            # 测试连接
            with console.status("[bold green]测试LLM连接中...[/]"):
                test_result = await client.test_llm(llm["id"])
                
            if test_result["success"]:
                console.print(f"[bold green]连接测试成功[/] - 响应时间: {test_result['response_time']}秒")
            else:
                console.print(f"[bold red]连接测试失败[/] - {test_result.get('message', '未知错误')}")
                
            # 导出配置
            if save_to_config:
                with console.status("[bold green]保存配置到文件...[/]"):
                    if export_llm_config_to_file():
                        console.print("[bold green]配置已保存到文件[/]")
                    else:
                        console.print("[bold yellow]配置保存失败[/]")
                
        finally:
            await client.close()
            
    # 运行异步函数
    asyncio.run(_add_llm())


@config.command()
def export_config():
    """将数据库中的LLM配置导出到配置文件"""
    if export_llm_config_to_file():
        console.print("[bold green]LLM配置已成功导出到配置文件[/]")
    else:
        console.print("[bold red]导出LLM配置失败[/]")


@config.command()
@click.option("--name", "-n", help="指定要导入的LLM名称")
def import_config(name):
    """从配置文件导入LLM配置到数据库
    
    例如: acolyte config import-config -n "Claude-3"
    """
    try:
        imported_llms = import_llm_config_from_file(name)
        if imported_llms:
            console.print(f"[bold green]已导入 {len(imported_llms)} 个LLM配置[/]")
            
            # 显示导入的配置
            table = Table(title="导入的LLM配置")
            table.add_column("ID", style="cyan")
            table.add_column("名称", style="green")
            table.add_column("模型", style="blue")
            table.add_column("角色", style="yellow")
            
            for llm in imported_llms:
                table.add_row(
                    str(llm["id"]),
                    llm["name"],
                    llm["model_name"],
                    llm["role"]
                )
                
            console.print(table)
        else:
            console.print("[bold yellow]未导入任何LLM配置[/]")
    except Exception as e:
        console.print(f"[bold red]导入失败: {str(e)}[/]")


@config.command()
def list_prompts():
    """列出所有Prompt配置"""
    async def _list_prompts():
        client = AcolyteClient()
        try:
            with console.status("[bold green]获取Prompt配置中...[/]"):
                prompts = await client.get_prompts()
                
            # 显示Prompt列表
            table = Table(title="Prompt配置")
            table.add_column("ID", style="cyan")
            table.add_column("版本", style="green")
            table.add_column("目标模型", style="blue")
            table.add_column("状态", style="yellow")
            table.add_column("创建时间", style="magenta")
            
            for prompt in prompts:
                table.add_row(
                    str(prompt["id"]),
                    prompt["version"],
                    prompt["model_target"] or "通用",
                    "激活" if prompt["is_active"] else "禁用",
                    prompt["created_at"]
                )
                
            console.print(table)
                
        finally:
            await client.close()
            
    # 运行异步函数
    asyncio.run(_list_prompts())


@config.command()
def sync_prompts():
    """同步Prompt文件到数据库"""
    async def _sync_prompts():
        client = AcolyteClient()
        try:
            with console.status("[bold green]同步Prompt文件中...[/]"):
                result = await client.sync_prompts()
                
            console.print(f"[bold green]{result['message']}[/]")
                
        finally:
            await client.close()
            
    # 运行异步函数
    asyncio.run(_sync_prompts())


@config.command()
@click.argument("prompt_id", type=int)
def show_prompt(prompt_id):
    """显示特定Prompt内容
    
    例如: acolyte config show-prompt 1
    """
    async def _show_prompt():
        client = AcolyteClient()
        try:
            # 获取Prompt内容
            with console.status(f"[bold green]获取Prompt {prompt_id}内容...[/]"):
                prompt = await client.get_prompt(prompt_id)
                
            # 显示Prompt信息
            console.print(Panel(
                f"ID: {prompt['id']}\n"
                f"版本: {prompt['version']}\n"
                f"目标模型: {prompt['model_target'] or '通用'}\n"
                f"状态: {'激活' if prompt['is_active'] else '禁用'}\n"
                f"创建时间: {prompt['created_at']}",
                title="Prompt信息"
            ))
            
            # 显示Prompt内容
            if prompt.get("content"):
                console.print("\n[bold]Prompt内容:[/]")
                console.print(Markdown(prompt["content"]))
            else:
                # 如果返回的prompt对象中没有content，单独获取content
                with console.status(f"[bold green]获取Prompt内容...[/]"):
                    response = await client.client.get(f"/prompts/{prompt_id}/content")
                    response.raise_for_status()
                    content_data = response.json()
                    console.print("\n[bold]Prompt内容:[/]")
                    console.print(Markdown(content_data["content"]))
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                console.print(f"[bold red]错误:[/] ID为{prompt_id}的Prompt不存在")
            else:
                console.print(f"[bold red]错误:[/] {str(e)}")
        finally:
            await client.close()
            
    # 运行异步函数
    asyncio.run(_show_prompt())


if __name__ == "__main__":
    cli()