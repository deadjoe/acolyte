import asyncio
import json
from typing import Optional

import click
import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from acolyte.cli.commands import AcolyteClient
from acolyte.utils.logging import get_logger

# 初始化日志记录器和控制台
logger = get_logger(__name__)
console = Console()


async def show_task(
    task_id: int,
    all_results: Optional[bool],
    specified_llm_id: Optional[int],
    raw: bool,
    format_type: str,
) -> None:
    """
    显示任务结果的异步函数

    Args:
        task_id: 任务ID
        all_results: 是否显示所有结果
        specified_llm_id: 指定的LLM ID
        raw: 是否显示原始响应
        format_type: 结果显示格式
    """
    client = AcolyteClient()
    try:
        # 检查API服务连接
        connection_ok, error_message = await client.check_connection()
        if not connection_ok:
            logger.error(f"API服务连接失败: {error_message}")
            console.print(f"[bold red]错误:[/] {error_message}")
            console.print(
                "[yellow]提示:[/] 请确保 API 服务已启动，可以运行 'uv run -m acolyte.main' 启动服务"
            )
            return

        # 获取任务信息
        with console.status("[bold green]获取任务信息中...[/]"):
            task = await client.get_task(task_id)
            # 格式化时间为友好的24小时制格式
            created_at = task.get("created_at", "未知")
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
                except Exception as e:
                    logger.warning(f"时间格式化失败: {str(e)}")

            console.print(
                Panel(
                    f"任务ID: {task['id']}\n"
                    f"处理模式: {task['processing_mode']}\n"
                    f"状态: {task['status']}\n"
                    f"创建时间: {created_at}",
                    title="任务信息",
                )
            )

        # 确定是否显示所有结果
        is_multiple_mode = task["processing_mode"] in ["multiple", "multiple_with_review"]

        # 如果用户没有指定--all或--single，根据模式自动决定
        show_all_results = all_results if all_results is not None else is_multiple_mode

        # 如果指定了LLM ID，则只显示该LLM的结果
        if specified_llm_id is not None:
            await show_specific_llm_result(client, task_id, specified_llm_id, raw, is_multiple_mode)
            return

        # 如果是multiple模式或用户要求显示所有结果
        if show_all_results:
            await show_all_llm_results(client, task_id, raw, format_type)
        else:
            await show_final_result(client, task_id, raw, is_multiple_mode)

    except Exception as e:
        logger.error(f"显示任务结果时出错: {str(e)}")
        console.print(f"[bold red]错误:[/] {str(e)}")
    finally:
        await client.close()


async def show_specific_llm_result(
    client: AcolyteClient, task_id: int, llm_id: int, raw: bool, is_multiple_mode: bool
) -> None:
    """显示特定LLM的结果"""
    # 获取所有结果
    results = await client.get_task_results(task_id, include_raw_response=raw)

    if not results:
        console.print("[bold yellow]无任何结果[/]")
        return

    # 获取LLM信息，用于显示名称
    llms = await client.get_llms()
    llm_map = {llm["id"]: llm for llm in llms}

    # 过滤指定的LLM结果
    filtered_results = [result for result in results if result.get("llm_id") == llm_id]
    if not filtered_results:
        console.print(f"[bold yellow]没有找到LLM ID={llm_id}的结果[/]")
        return

    # 显示指定LLM的结果
    result = filtered_results[0]
    llm_name = llm_map.get(llm_id, {}).get("name", f"LLM-{llm_id}")

    # 显示评分
    title = f"分析评分 ({llm_name})"
    table = Table(title=title)
    table.add_column("指标", style="cyan")
    table.add_column("分数", style="green")

    # 安全地格式化指标值
    bi = result.get("bias_index")
    if bi is not None:
        table.add_row("偏见指数 (BI)", f"{bi:.2f}")

    mi = result.get("misleading_index")
    if mi is not None:
        table.add_row("误导性指数 (MI)", f"{mi:.2f}")

    hi = result.get("hidden_intent_index")
    if hi is not None:
        table.add_row("隐藏意图指数 (HI)", f"{hi:.2f}")

    cs = result.get("credibility_score")
    if cs is not None:
        table.add_row("综合可信度 (CS)", f"{cs:.2f}")

    console.print(table)

    # 显示原始响应
    if raw and result.get("raw_response"):
        console.print("\n[bold]详细分析:[/]")
        console.print(Markdown(result["raw_response"]))

    # 如果是multiple模式，提示可以查看所有结果
    if is_multiple_mode:
        console.print("\n[dim]使用 --all 选项查看所有LLM的结果[/]")


async def show_all_llm_results(
    client: AcolyteClient, task_id: int, raw: bool, format_type: str
) -> None:
    """显示所有LLM的结果"""
    # 获取所有结果
    results = await client.get_task_results(task_id, include_raw_response=raw)

    if not results:
        console.print("[bold yellow]无任何结果[/]")
        return

    # 获取LLM信息，用于显示名称
    llms = await client.get_llms()
    llm_map = {llm["id"]: llm for llm in llms}

    # 根据格式显示结果
    if format_type == "json":
        # JSON格式输出
        console.print(json.dumps(results, indent=2, ensure_ascii=False))

    elif format_type == "summary":
        # 概要格式 - 只显示评分
        for result in results:
            llm_id = result.get("llm_id")
            llm_name = llm_map.get(llm_id, {}).get("name", f"LLM-{llm_id}")

            console.print(f"\n[bold cyan]{llm_name} (ID={llm_id}):[/]")

            # 安全地格式化指标值
            bi = result.get("bias_index")
            bi_str = f"{bi:.2f}" if bi is not None else "N/A"

            mi = result.get("misleading_index")
            mi_str = f"{mi:.2f}" if mi is not None else "N/A"

            hi = result.get("hidden_intent_index")
            hi_str = f"{hi:.2f}" if hi is not None else "N/A"

            cs = result.get("credibility_score")
            cs_str = f"{cs:.2f}" if cs is not None else "N/A"

            console.print(f"BI: {bi_str}, MI: {mi_str}, HI: {hi_str}, CS: {cs_str}")

    else:  # 默认表格格式
        # 创建比较表格
        compare_table = Table(title="评分结果比较")
        compare_table.add_column("LLM", style="cyan")
        compare_table.add_column("BI", style="red")
        compare_table.add_column("MI", style="yellow")
        compare_table.add_column("HI", style="magenta")
        compare_table.add_column("CS", style="green")
        compare_table.add_column("类型", style="blue")

        for result in results:
            llm_id = result.get("llm_id")
            llm_name = llm_map.get(llm_id, {}).get("name", f"LLM-{llm_id}")

            # 安全地格式化指标值
            bi = result.get("bias_index")
            bi_str = f"{bi:.2f}" if bi is not None else "N/A"

            mi = result.get("misleading_index")
            mi_str = f"{mi:.2f}" if mi is not None else "N/A"

            hi = result.get("hidden_intent_index")
            hi_str = f"{hi:.2f}" if hi is not None else "N/A"

            cs = result.get("credibility_score")
            cs_str = f"{cs:.2f}" if cs is not None else "N/A"

            # 根据 is_review_result 字段判断结果类型
            result_type = "评议结果" if result.get("is_review_result") else "分析结果"
            compare_table.add_row(f"{llm_name} ({llm_id})", bi_str, mi_str, hi_str, cs_str, result_type)

        console.print(compare_table)

    # 显示原始响应
    if raw:
        for result in results:
            llm_id = result.get("llm_id")
            llm_name = llm_map.get(llm_id, {}).get("name", f"LLM-{llm_id}")

            if result.get("raw_response"):
                console.print(f"\n[bold]=== {llm_name} (ID={llm_id}) 详细分析 ===[/]")
                console.print(Markdown(result["raw_response"]))

    # 提示查看原始响应
    if not raw and results:
        console.print("\n[dim]使用 --raw 选项查看详细分析内容[/]")


async def show_final_result(
    client: AcolyteClient, task_id: int, raw: bool, is_multiple_mode: bool
) -> None:
    """显示最终结果"""
    try:
        # 获取最终结果
        final_result = await client.get_task_final_result(task_id, include_raw_response=raw)

        # 获取LLM信息
        llm_id = final_result.get("llm_id")
        llm_name = ""
        if llm_id:
            llms = await client.get_llms()
            for llm in llms:
                if llm["id"] == llm_id:
                    llm_name = llm["name"]
                    break

        title = "分析评分"
        if llm_name:
            title = f"分析评分 ({llm_name})"

        # 显示评分
        table = Table(title=title)
        table.add_column("指标", style="cyan")
        table.add_column("分数", style="green")

        # 安全地格式化指标值
        bi = final_result.get("bias_index")
        if bi is not None:
            table.add_row("偏见指数 (BI)", f"{bi:.2f}")

        mi = final_result.get("misleading_index")
        if mi is not None:
            table.add_row("误导性指数 (MI)", f"{mi:.2f}")

        hi = final_result.get("hidden_intent_index")
        if hi is not None:
            table.add_row("隐藏意图指数 (HI)", f"{hi:.2f}")

        cs = final_result.get("credibility_score")
        if cs is not None:
            table.add_row("综合可信度 (CS)", f"{cs:.2f}")

        console.print(table)

        # 显示原始响应
        if raw and final_result.get("raw_response"):
            console.print("\n[bold]详细分析:[/]")
            console.print(Markdown(final_result["raw_response"]))

        # 如果是multiple模式，提示可以查看所有结果
        if is_multiple_mode:
            console.print("\n[dim]使用 --all 选项查看所有LLM的结果[/]")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print("[bold yellow]任务无结果[/]")
        else:
            raise e


def register_command(history_group):
    """注册history show命令"""

    @history_group.command()
    @click.argument("task_id", type=int)
    @click.option(
        "--all/--single",
        default=None,
        help="显示所有LLM结果或仅显示最终结果 (multiple模式默认--all)",
    )
    @click.option("--llm", type=int, help="指定要显示的LLM ID，仅在multiple模式下有效")
    @click.option("--raw/--no-raw", default=False, help="是否显示原始响应")
    @click.option(
        "--format",
        type=click.Choice(["table", "summary", "json"]),
        default="table",
        help="结果显示格式",
    )
    def show(task_id, all, llm, raw, format):
        """显示特定任务结果

        例如: acolyte history show 123 --raw
        """
        # 调用异步函数并显式传递参数
        asyncio.run(show_task(task_id, all, llm, raw, format))
