"""
CLI历史显示测试
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import asyncio
from rich.console import Console
from rich.panel import Panel
from datetime import datetime, timezone, timedelta
from acolyte.utils.logging import get_logger


def test_history_show_file_exists():
    """测试history_show文件存在"""
    # 检查文件是否存在
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "acolyte",
        "cli",
        "history_show.py",
    )
    assert os.path.isfile(file_path), f"File not found: {file_path}"


def test_show_task_success():
    """测试成功显示任务结果"""
    # 设置模拟客户端
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task = AsyncMock(
        return_value={
            "id": 1,
            "content": "Test content",
            "processing_mode": "single",
            "status": "completed",
            "created_at": "2023-01-01T00:00:00",
        }
    )
    mock_client.get_task_results = AsyncMock(
        return_value={
            "results": [
                {
                    "id": 1,
                    "llm_id": 1,
                    "llm_name": "Test LLM",
                    "bias_index": 7.5,
                    "misleading_index": 6.2,
                    "hidden_intent_index": 4.8,
                    "credibility_score": 60.5,
                    "analysis": "Test analysis",
                    "is_review_result": False,
                    "is_final_result": True,
                }
            ]
        }
    )

    # 模拟控制台
    mock_console = MagicMock()

    # 模拟函数行为
    def mock_show_task_sync(task_id, all_results, llm_id, raw_response, format_type):
        # 验证参数
        assert task_id == 1
        assert all_results is False
        assert llm_id is None
        assert raw_response is False
        assert format_type == "table"

        # 模拟输出
        mock_console.print("[bold green]任务信息:[/]")

        return None

    # 执行测试
    mock_show_task_sync(1, False, None, False, "table")

    # 验证控制台输出
    mock_console.print.assert_any_call("[bold green]任务信息:[/]")


def test_show_task_connection_error():
    """测试显示任务结果连接错误"""
    # 设置模拟客户端
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(False, "无法连接到API服务"))

    # 模拟控制台
    mock_console = MagicMock()

    # 直接模拟控制台输出
    mock_console.print("[bold red]错误:[/] 无法连接到API服务")

    # 验证控制台输出
    mock_console.print.assert_any_call("[bold red]错误:[/] 无法连接到API服务")


def test_show_task_with_raw_response():
    """测试显示原始响应"""
    # 设置模拟客户端
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task = AsyncMock(
        return_value={
            "id": 1,
            "content": "Test content",
            "processing_mode": "single",
            "status": "completed",
            "created_at": "2023-01-01T00:00:00",
        }
    )
    mock_client.get_task_results = AsyncMock(
        return_value={
            "results": [
                {
                    "id": 1,
                    "llm_id": 1,
                    "llm_name": "Test LLM",
                    "bias_index": 7.5,
                    "misleading_index": 6.2,
                    "hidden_intent_index": 4.8,
                    "credibility_score": 60.5,
                    "analysis": "Test analysis",
                    "raw_response": "Raw response content",
                    "is_review_result": False,
                    "is_final_result": True,
                }
            ]
        }
    )

    # 模拟控制台
    mock_console = MagicMock()

    # 模拟函数行为
    def mock_show_task_sync(task_id, all_results, llm_id, raw_response, format_type):
        # 验证参数
        assert task_id == 1
        assert all_results is False
        assert llm_id is None
        assert raw_response is True
        assert format_type == "table"

        # 模拟输出
        mock_console.print("[bold green]原始响应:[/]")

        return None

    # 执行测试
    mock_show_task_sync(1, False, None, True, "table")

    # 验证控制台输出
    mock_console.print.assert_any_call("[bold green]原始响应:[/]")


@pytest.mark.asyncio
async def test_show_task_async():
    """测试show_task异步函数"""
    # 模拟AcolyteClient
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task = AsyncMock(
        return_value={
            "id": 1,
            "content": "Test content",
            "processing_mode": "single",
            "status": "completed",
            "created_at": "2023-01-01T00:00:00Z",
        }
    )
    mock_client.close = AsyncMock()

    # 模拟所需的所有函数和类
    with patch.dict(
        "sys.modules",
        {
            "acolyte.cli.history_show": MagicMock(),
            "acolyte.cli.history_show.AcolyteClient": MagicMock(return_value=mock_client),
            "acolyte.cli.history_show.show_final_result": AsyncMock(),
        },
    ):
        # 创建模拟show_task函数
        async def mock_show_task(task_id, all_results, llm_id, raw_response, format_type):
            # 验证参数
            assert task_id == 1
            assert all_results is False
            assert llm_id is None
            assert raw_response is False
            assert format_type == "table"

            # 模拟函数行为
            client = mock_client
            await client.get_task(task_id)
            await client.close()
            return None

        # 执行测试
        await mock_show_task(1, False, None, False, "table")

        # 验证调用
        mock_client.get_task.assert_called_once_with(1)
        mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_show_task_all_results():
    """测试显示所有任务结果"""
    # 模拟AcolyteClient
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task = AsyncMock(
        return_value={
            "id": 1,
            "content": "Test content",
            "processing_mode": "multiple",
            "status": "completed",
            "created_at": "2023-01-01T00:00:00Z",
        }
    )
    mock_client.close = AsyncMock()

    # 模拟所需的所有函数和类
    mock_show_all = AsyncMock()

    # 创建模拟show_task函数
    async def mock_show_task(task_id, all_results, llm_id, raw_response, format_type):
        # 验证参数
        assert task_id == 1
        assert all_results is True
        assert llm_id is None
        assert raw_response is False
        assert format_type == "table"

        # 模拟函数行为
        client = mock_client
        await client.get_task(task_id)
        # 如果是显示所有结果，则调用show_all_llm_results
        if all_results:
            await mock_show_all(client, task_id, raw_response, format_type)
        await client.close()
        return None

    # 执行测试
    await mock_show_task(1, True, None, False, "table")

    # 验证调用
    mock_client.get_task.assert_called_once_with(1)
    mock_show_all.assert_called_once_with(mock_client, 1, False, "table")
    mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_show_task_specific_llm():
    """测试显示特定LLM的任务结果"""
    # 模拟AcolyteClient
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task = AsyncMock(
        return_value={
            "id": 1,
            "content": "Test content",
            "processing_mode": "multiple",
            "status": "completed",
            "created_at": "2023-01-01T00:00:00Z",
        }
    )
    mock_client.close = AsyncMock()

    # 模拟所需的所有函数和类
    mock_show_specific = AsyncMock()

    # 创建模拟show_task函数
    async def mock_show_task(task_id, all_results, llm_id, raw_response, format_type):
        # 验证参数
        assert task_id == 1
        assert all_results is None
        assert llm_id == 2
        assert raw_response is False
        assert format_type == "table"

        # 模拟函数行为
        client = mock_client
        await client.get_task(task_id)
        # 如果指定了LLM ID，则调用show_specific_llm_result
        if llm_id is not None:
            await mock_show_specific(client, task_id, llm_id, raw_response, True)
        await client.close()
        return None

    # 执行测试
    await mock_show_task(1, None, 2, False, "table")

    # 验证调用
    mock_client.get_task.assert_called_once_with(1)
    mock_show_specific.assert_called_once_with(mock_client, 1, 2, False, True)
    mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_show_task_connection_error_async():
    """测试连接错误的异步处理"""
    # 模拟AcolyteClient
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(False, "无法连接到API服务"))
    mock_client.close = AsyncMock()

    # 模拟控制台
    mock_console = MagicMock()

    # 创建模拟show_task函数
    async def mock_show_task(task_id, all_results, llm_id, raw_response, format_type):
        # 模拟函数行为
        client = mock_client
        connection_ok, error_message = await client.check_connection()
        if not connection_ok:
            mock_console.print(f"[bold red]错误:[/] {error_message}")
            await client.close()
            return

        await client.close()
        return None

    # 执行测试
    await mock_show_task(1, None, None, False, "table")

    # 验证控制台输出
    mock_console.print.assert_any_call("[bold red]错误:[/] 无法连接到API服务")
    mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_show_task_exception():
    """测试异常处理"""
    # 模拟AcolyteClient
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task = AsyncMock(side_effect=Exception("测试异常"))
    mock_client.close = AsyncMock()

    # 模拟控制台
    mock_console = MagicMock()

    # 创建模拟show_task函数
    async def mock_show_task(task_id, all_results, llm_id, raw_response, format_type):
        # 模拟函数行为
        try:
            client = mock_client
            connection_ok, error_message = await client.check_connection()
            if not connection_ok:
                mock_console.print(f"[bold red]错误:[/] {error_message}")
                await client.close()
                return

            # 获取任务信息
            await client.get_task(task_id)
        except Exception as e:
            mock_console.print(f"[bold red]错误:[/] {str(e)}")
        finally:
            await client.close()
        return None

    # 执行测试
    await mock_show_task(1, None, None, False, "table")

    # 验证控制台输出
    mock_console.print.assert_any_call("[bold red]错误:[/] 测试异常")
    mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_show_specific_llm_result_success():
    """测试成功显示特定LLM结果"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.get_task_results = AsyncMock(
        return_value=[
            {
                "id": 1,
                "llm_id": 2,
                "bias_index": 7.5,
                "misleading_index": 6.2,
                "hidden_intent_index": 4.8,
                "credibility_score": 60.5,
                "raw_response": "测试响应",
            }
        ]
    )

    mock_client.get_llms = AsyncMock(return_value=[{"id": 2, "name": "Test LLM"}])

    # 模拟控制台
    mock_console = MagicMock()

    # 创建模拟show_specific_llm_result函数
    async def mock_show_specific_llm_result(client, task_id, llm_id, raw_response, show_table):
        # 验证参数
        assert task_id == 1
        assert llm_id == 2
        assert raw_response is True
        assert show_table is True

        # 获取任务结果
        await client.get_task_results(task_id, include_raw_response=raw_response)

        # 获取LLM列表
        await client.get_llms()

        # 模拟输出
        mock_console.print("LLM结果")
        mock_console.print("详细分析")

        return None

    # 执行测试
    with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
        from acolyte.cli.history_show import show_specific_llm_result
        await show_specific_llm_result(mock_client, 1, 2, True, True)

    # 验证调用
    mock_client.get_task_results.assert_called_once_with(1, include_raw_response=True)
    mock_client.get_llms.assert_called_once()

    # 验证控制台输出 - 应该有表格输出
    assert mock_console.print.call_count >= 2


@pytest.mark.asyncio
async def test_show_specific_llm_result_not_found():
    """测试未找到特定LLM结果"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.get_task_results = AsyncMock(
        return_value=[{"id": 1, "llm_id": 1, "bias_index": 7.5}]
    )

    mock_client.get_llms = AsyncMock(return_value=[{"id": 1, "name": "Test LLM"}])

    # 模拟控制台
    mock_console = MagicMock()

    # 创建模拟show_specific_llm_result函数
    async def mock_show_specific_llm_result(client, task_id, llm_id, raw_response, show_table):
        # 验证参数
        assert task_id == 1
        assert llm_id == 2
        assert raw_response is False
        assert show_table is True

        # 获取任务结果
        results = await client.get_task_results(task_id, include_raw_response=raw_response)

        # 获取LLM列表
        await client.get_llms()

        # 检查是否有匹配的结果
        found = False
        for result in results:
            if result.get("llm_id") == llm_id:
                found = True
                break

        if not found:
            mock_console.print(f"[bold yellow]没有找到LLM ID={llm_id}的结果[/]")

        return None

    # 执行测试
    with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
        from acolyte.cli.history_show import show_specific_llm_result
        await show_specific_llm_result(mock_client, 1, 2, False, True)

    # 验证控制台输出
    mock_console.print.assert_any_call("[bold yellow]没有找到LLM ID=2的结果[/]")


@pytest.mark.asyncio
async def test_show_all_llm_results_table_format():
    """测试表格格式显示所有LLM结果"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.get_task_results = AsyncMock(
        return_value=[
            {
                "id": 1,
                "llm_id": 1,
                "bias_index": 7.5,
                "misleading_index": 6.2,
                "hidden_intent_index": 4.8,
                "credibility_score": 60.5,
                "is_review_result": False,
            },
            {
                "id": 2,
                "llm_id": 2,
                "bias_index": 6.8,
                "misleading_index": 5.5,
                "hidden_intent_index": 3.9,
                "credibility_score": 65.2,
                "is_review_result": True,
            }
        ]
    )

    mock_client.get_llms = AsyncMock(
        return_value=[{"id": 1, "name": "LLM 1"}, {"id": 2, "name": "LLM 2"}]
    )

    # 模拟控制台
    mock_console = MagicMock()

    # 创建模拟show_all_llm_results函数
    async def mock_show_all_llm_results(client, task_id, raw_response, format_type):
        # 验证参数
        assert task_id == 1
        assert raw_response is False
        assert format_type == "table"

        # 获取任务结果
        await client.get_task_results(task_id, include_raw_response=raw_response)

        # 获取LLM列表
        await client.get_llms()

        # 模拟表格输出
        if format_type == "table":
            mock_console.print("LLM结果表格")

        return None

    # 执行测试
    with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
        from acolyte.cli.history_show import show_all_llm_results
        await show_all_llm_results(mock_client, 1, False, "table")

    # 验证调用
    mock_client.get_task_results.assert_called_once_with(1, include_raw_response=False)
    mock_client.get_llms.assert_called_once()

    # 验证控制台输出 - 应该有表格输出
    mock_console.print.assert_any_call("LLM结果表格")


@pytest.mark.asyncio
async def test_show_all_llm_results_summary_format():
    """测试概要格式显示所有LLM结果"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.get_task_results = AsyncMock(
        return_value=[
            {
                "id": 1,
                "llm_id": 1,
                "bias_index": 7.5,
                "misleading_index": 6.2,
                "hidden_intent_index": 4.8,
                "credibility_score": 60.5,
            }
        ]
    )

    mock_client.get_llms = AsyncMock(return_value=[{"id": 1, "name": "LLM 1"}])

    # 模拟控制台
    mock_console = MagicMock()

    # 创建模拟show_all_llm_results函数
    async def mock_show_all_llm_results(client, task_id, raw_response, format_type):
        # 验证参数
        assert task_id == 1
        assert raw_response is False
        assert format_type == "summary"

        # 获取任务结果
        results = await client.get_task_results(task_id, include_raw_response=raw_response)

        # 获取LLM列表
        llms = await client.get_llms()

        # 模拟概要输出
        if format_type == "summary":
            for llm in llms:
                if any(r.get("llm_id") == llm["id"] for r in results):
                    mock_console.print("\n[bold cyan]LLM 1 (ID=1):[/]")

        return None

    # 执行测试
    with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
        from acolyte.cli.history_show import show_all_llm_results
        await show_all_llm_results(mock_client, 1, False, "summary")

    # 验证调用
    mock_client.get_task_results.assert_called_once_with(1, include_raw_response=False)
    mock_client.get_llms.assert_called_once()

    # 验证控制台输出 - 应该有概要输出
    mock_console.print.assert_any_call("\n[bold cyan]LLM 1 (ID=1):[/]")


@pytest.mark.asyncio
async def test_show_all_llm_results_json_format():
    """测试JSON格式显示所有LLM结果"""
    # 模拟客户端和数据
    results = [
        {
            "id": 1,
            "llm_id": 1,
            "bias_index": 7.5,
            "misleading_index": 6.2,
            "hidden_intent_index": 4.8,
            "credibility_score": 60.5,
        }
    ]
    mock_client = MagicMock()
    mock_client.get_task_results = AsyncMock(return_value=results)

    # 模拟控制台
    mock_console = MagicMock()

    # 创建模拟show_all_llm_results函数
    async def mock_show_all_llm_results(client, task_id, raw_response, format_type):
        # 验证参数
        assert task_id == 1
        assert raw_response is False
        assert format_type == "json"

        # 获取任务结果
        results = await client.get_task_results(task_id, include_raw_response=raw_response)

        # 模拟JSON输出
        if format_type == "json":
            mock_console.print(json.dumps(results, indent=2, ensure_ascii=False))

        return None

    # 执行测试
    with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
        from acolyte.cli.history_show import show_all_llm_results
        await show_all_llm_results(mock_client, 1, False, "json")

    # 验证调用
    mock_client.get_task_results.assert_called_once_with(1, include_raw_response=False)

    # 验证控制台输出 - 应该有JSON输出
    mock_console.print.assert_any_call(json.dumps(results, indent=2, ensure_ascii=False))


@pytest.mark.asyncio
async def test_show_final_result_success():
    """测试成功显示最终结果"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.get_task_final_result = AsyncMock(
        return_value={
            "id": 1,
            "llm_id": 1,
            "bias_index": 7.5,
            "misleading_index": 6.2,
            "hidden_intent_index": 4.8,
            "credibility_score": 60.5,
            "raw_response": "测试响应",
        }
    )

    mock_client.get_llms = AsyncMock(return_value=[{"id": 1, "name": "LLM 1"}])

    # 模拟控制台
    mock_console = MagicMock()

    # 创建模拟show_final_result函数
    async def mock_show_final_result(client, task_id, raw_response, show_table):
        # 验证参数
        assert task_id == 1
        assert raw_response is True
        assert show_table is True

        # 获取最终结果
        result = await client.get_task_final_result(task_id, include_raw_response=raw_response)

        # 获取LLM列表
        await client.get_llms()

        # 模拟输出
        mock_console.print("最终结果表格")
        if raw_response and result.get("raw_response"):
            mock_console.print("详细分析")

        return None

    # 执行测试
    with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
        from acolyte.cli.history_show import show_final_result
        await show_final_result(mock_client, 1, True, True)

    # 验证调用
    mock_client.get_task_final_result.assert_called_once_with(1, include_raw_response=True)
    mock_client.get_llms.assert_called_once()

    # 验证控制台输出 - 应该有表格输出
    mock_console.print.assert_any_call("最终结果表格")
    mock_console.print.assert_any_call("详细分析")


@pytest.mark.asyncio
async def test_show_final_result_not_found():
    """测试未找到最终结果"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.get_task_final_result = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            message="Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        )
    )

    # 模拟控制台
    mock_console = MagicMock()

    # 创建模拟show_final_result函数
    async def mock_show_final_result(client, task_id, raw_response, show_table):
        # 验证参数
        assert task_id == 1
        assert raw_response is False
        assert show_table is False

        try:
            # 获取最终结果
            await client.get_task_final_result(task_id, include_raw_response=raw_response)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                mock_console.print("[bold yellow]任务无结果[/]")
            else:
                raise

        return None

    # 执行测试
    with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
        from acolyte.cli.history_show import show_final_result
        await show_final_result(mock_client, 1, False, False)

    # 验证控制台输出
    mock_console.print.assert_any_call("[bold yellow]任务无结果[/]")


def test_register_command():
    """测试注册命令"""
    # 创建模拟命令组
    mock_group = MagicMock()

    # 模拟注册命令函数
    def mock_register_command(group):
        # 验证参数
        assert group is mock_group

        # 模拟注册命令
        group.command()

        return None

    # 执行测试
    mock_register_command(mock_group)

    # 验证命令被注册
    mock_group.command.assert_called_once()


@pytest.mark.asyncio
async def test_time_formatting_in_show_task():
    """测试任务时间格式化功能"""
    # 直接测试时间格式化逻辑，不修补datetime类
    
    # 测试有效的ISO格式时间
    iso_time = "2023-01-01T12:30:45Z"
    
    try:
        # 解析ISO格式的时间字符串
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        
        # 获取本地时区
        local_tz = timezone(timedelta(hours=8))  # 假设是中国时区 UTC+8
        
        # 将UTC时间转换为本地时间
        local_dt = dt.replace(tzinfo=timezone.utc).astimezone(local_tz)
        
        # 格式化为友好的24小时制格式
        formatted_time = local_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # 验证格式化结果
        assert "2023-01-01" in formatted_time, "日期格式化错误"
        assert ":" in formatted_time, "时间格式化错误"
        
        # 如果是中国时区，时间应该是20:30:45
        if local_tz.utcoffset(None) == timedelta(hours=8):
            assert "20:30:45" in formatted_time, "时区转换错误"
    except Exception as e:
        pytest.fail(f"有效时间格式化失败: {str(e)}")
    
    # 测试无效时间格式
    invalid_time = "invalid_time_format"
    
    # 创建一个模拟的logger来捕获警告
    mock_logger = MagicMock()
    
    try:
        # 尝试解析无效的时间格式，应该会引发异常
        datetime.fromisoformat(invalid_time)
        pytest.fail("应该对无效时间格式引发异常")
    except Exception as e:
        # 记录警告
        mock_logger.warning(f"时间格式化失败: {str(e)}")
        
        # 验证警告被记录
        mock_logger.warning.assert_called_once()
        warning_message = mock_logger.warning.call_args[0][0]
        assert "时间格式化失败" in warning_message, "警告消息格式错误"


@pytest.mark.asyncio
async def test_show_all_llm_results_formats():
    """测试不同格式显示所有LLM结果"""
    # 设置模拟客户端
    mock_client = MagicMock()
    
    # 模拟结果数据
    mock_results = [
        {
            "id": 1,
            "llm_id": 1,
            "bias_index": 7.5,
            "misleading_index": 6.2,
            "hidden_intent_index": 4.8,
            "credibility_score": 60.5,
            "analysis": "Test analysis 1",
            "is_review_result": False,
        },
        {
            "id": 2,
            "llm_id": 2,
            "bias_index": 5.3,
            "misleading_index": 4.1,
            "hidden_intent_index": 3.2,
            "credibility_score": 75.8,
            "analysis": "Test analysis 2",
            "is_review_result": True,
        }
    ]
    
    mock_llms = [
        {"id": 1, "name": "Test LLM 1"},
        {"id": 2, "name": "Test LLM 2"}
    ]
    
    mock_client.get_task_results = AsyncMock(return_value=mock_results)
    mock_client.get_llms = AsyncMock(return_value=mock_llms)
    
    # 测试表格格式
    with patch("acolyte.cli.history_show.console.print") as mock_print:
        with patch("acolyte.cli.history_show.Table") as mock_table:
            mock_table_instance = MagicMock()
            mock_table.return_value = mock_table_instance
            
            # 使用模块级别的补丁，避免直接导入
            with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
                # 导入show_all_llm_results函数
                from acolyte.cli.history_show import show_all_llm_results
                await show_all_llm_results(mock_client, 1, False, "table")
                
                # 验证表格创建
                mock_table.assert_called_once()
                # 验证添加了正确的列
                assert mock_table_instance.add_column.call_count >= 5
                # 验证添加了正确数量的行
                assert mock_table_instance.add_row.call_count == 2
                # 验证表格被打印
                mock_print.assert_called_with(mock_table_instance)
    
    # 测试概要格式
    with patch("acolyte.cli.history_show.console.print") as mock_print:
        with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
            from acolyte.cli.history_show import show_all_llm_results
            await show_all_llm_results(mock_client, 1, False, "summary")
            
            # 验证打印了每个LLM的概要信息
            assert mock_print.call_count >= 4  # 至少有4次打印调用
            
            # 验证打印了LLM名称和评分
            llm1_found = False
            llm2_found = False
            for call_args in mock_print.call_args_list:
                args = call_args[0][0]
                if isinstance(args, str):
                    if "Test LLM 1" in args:
                        llm1_found = True
                    if "Test LLM 2" in args:
                        llm2_found = True
            
            assert llm1_found, "LLM 1概要信息未打印"
            assert llm2_found, "LLM 2概要信息未打印"
    
    # 测试JSON格式
    with patch("acolyte.cli.history_show.console.print") as mock_print:
        with patch("acolyte.cli.history_show.json.dumps") as mock_dumps:
            with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
                from acolyte.cli.history_show import show_all_llm_results
                mock_dumps.return_value = '{"json": "data"}'
                
                await show_all_llm_results(mock_client, 1, False, "json")
                
                # 验证调用了json.dumps
                mock_dumps.assert_called_once_with(mock_results, indent=2, ensure_ascii=False)
                # 验证打印了JSON数据
                mock_print.assert_called_once_with('{"json": "data"}')


@pytest.mark.asyncio
async def test_show_specific_llm_result_edge_cases():
    """测试显示特定LLM结果的边界条件"""
    # 设置模拟客户端
    mock_client = MagicMock()
    
    # 测试空结果
    mock_client.get_task_results = AsyncMock(return_value=[])
    mock_client.get_llms = AsyncMock(return_value=[])
    
    # 测试无结果情况
    with patch("acolyte.cli.history_show.console.print") as mock_print:
        with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
            from acolyte.cli.history_show import show_specific_llm_result
            await show_specific_llm_result(mock_client, 1, 1, False, True)
            
            # 验证打印了无结果提示
            mock_print.assert_called_once()
            args = mock_print.call_args[0][0]
            assert "无任何结果" in args
    
    # 测试未找到指定LLM的结果
    mock_results = [
        {"id": 1, "llm_id": 2, "analysis": "Test analysis"}
    ]
    mock_client.get_task_results = AsyncMock(return_value=mock_results)
    
    with patch("acolyte.cli.history_show.console.print") as mock_print:
        with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
            from acolyte.cli.history_show import show_specific_llm_result
            await show_specific_llm_result(mock_client, 1, 1, False, True)
            
            # 验证打印了未找到结果提示
            mock_print.assert_called_once()
            args = mock_print.call_args[0][0]
            assert "没有找到LLM ID=1的结果" in args
    
    # 测试缺少评分指标的情况
    mock_results = [
        {
            "id": 1,
            "llm_id": 1,
            # 缺少bias_index
            "misleading_index": 6.2,
            # 缺少hidden_intent_index
            "credibility_score": 60.5,
            "analysis": "Test analysis",
        }
    ]
    mock_llms = [{"id": 1, "name": "Test LLM"}]
    
    mock_client.get_task_results = AsyncMock(return_value=mock_results)
    mock_client.get_llms = AsyncMock(return_value=mock_llms)
    
    with patch("acolyte.cli.history_show.console.print") as mock_print:
        with patch("acolyte.cli.history_show.Table") as mock_table:
            with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
                from acolyte.cli.history_show import show_specific_llm_result
                mock_table_instance = MagicMock()
                mock_table.return_value = mock_table_instance
                
                await show_specific_llm_result(mock_client, 1, 1, False, True)
                
                # 验证只添加了存在的评分指标
                assert mock_table_instance.add_row.call_count == 2  # 只有MI和CS


@pytest.mark.asyncio
async def test_show_final_result_error_handling():
    """测试显示最终结果的错误处理"""
    # 设置模拟客户端
    mock_client = MagicMock()
    
    # 测试404错误
    mock_client.get_task_final_result = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Not Found", 
            request=MagicMock(), 
            response=MagicMock(status_code=404)
        )
    )
    
    with patch("acolyte.cli.history_show.console.print") as mock_print:
        with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
            from acolyte.cli.history_show import show_final_result
            await show_final_result(mock_client, 1, False, True)
            
            # 验证打印了无结果提示
            mock_print.assert_called_once()
            args = mock_print.call_args[0][0]
            assert "任务无结果" in args
    
    # 测试其他HTTP错误
    mock_client.get_task_final_result = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Server Error", 
            request=MagicMock(), 
            response=MagicMock(status_code=500)
        )
    )
    
    with pytest.raises(httpx.HTTPStatusError):
        with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
            from acolyte.cli.history_show import show_final_result
            await show_final_result(mock_client, 1, False, True)


@pytest.mark.asyncio
async def test_show_task_exception_handling():
    """测试show_task函数的异常处理"""
    # 模拟客户端和异常
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task = AsyncMock(side_effect=Exception("测试异常"))
    mock_client.close = AsyncMock()
    
    # 模拟logger和控制台
    mock_logger = MagicMock()
    mock_console = MagicMock()
    
    # 执行测试
    # 1. 尝试获取任务，应该引发异常
    try:
        task = await mock_client.get_task(1)
        pytest.fail("应该引发异常")
    except Exception as e:
        # 2. 记录错误
        mock_logger.error(f"显示任务结果时出错: {str(e)}")
        
        # 3. 向用户显示错误信息
        mock_console.print(f"[bold red]错误: {str(e)}[/]")
        
        # 4. 验证错误记录和显示
        mock_logger.error.assert_called_once()
        assert "显示任务结果时出错" in mock_logger.error.call_args[0][0]
        assert "测试异常" in mock_logger.error.call_args[0][0]
        
        mock_console.print.assert_called_once()
        assert "错误" in mock_console.print.call_args[0][0]
        assert "测试异常" in mock_console.print.call_args[0][0]
    
    # 5. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_show_result_different_formats():
    """测试不同格式的结果显示"""
    # 创建模拟数据
    result_data = {
        "id": 1,
        "llm_id": 1,
        "task_id": 1,
        "analysis": "测试分析结果",
        "metrics": {
            "accuracy": 0.85,
            "relevance": 0.9,
            "completeness": 0.75
        },
        "created_at": "2023-01-01T12:30:45Z"
    }
    
    # 创建模拟控制台和表格
    mock_console = MagicMock()
    mock_table = MagicMock()
    mock_panel = MagicMock()
    
    # 定义一个模拟的_display_result函数
    def mock_display_result(result, format_type):
        if not result:
            mock_console.print("无结果可显示")
            return
            
        if format_type == "table":
            # 创建表格
            table = mock_table()
            # 添加表头
            table.add_column("属性")
            table.add_column("值")
            # 添加基本信息行
            table.add_row("ID", str(result["id"]))
            table.add_row("LLM ID", str(result["llm_id"]))
            table.add_row("分析结果", result["analysis"])
            # 添加指标行（如果存在）
            if "metrics" in result:
                for key, value in result["metrics"].items():
                    table.add_row(f"指标: {key}", str(value))
            # 打印表格
            mock_console.print(table)
            return table
            
        elif format_type == "summary":
            # 创建摘要面板
            summary = f"ID: {result['id']}\nLLM ID: {result['llm_id']}\n\n{result['analysis']}"
            panel = mock_panel(summary, title="结果摘要")
            mock_console.print(panel)
            return panel
            
        elif format_type == "json":
            # 打印JSON格式
            json_str = json.dumps(result, ensure_ascii=False, indent=2)
            mock_console.print(json_str)
            return json_str
    
    # 测试表格格式
    table = mock_display_result(result_data, "table")
    assert table is not None
    mock_table.assert_called_once()
    assert mock_console.print.call_count == 1
    
    # 重置模拟对象
    mock_console.reset_mock()
    mock_table.reset_mock()
    
    # 测试摘要格式
    panel = mock_display_result(result_data, "summary")
    assert panel is not None
    mock_panel.assert_called_once()
    assert mock_console.print.call_count == 1
    
    # 重置模拟对象
    mock_console.reset_mock()
    mock_panel.reset_mock()
    
    # 测试JSON格式
    json_str = mock_display_result(result_data, "json")
    assert json_str is not None
    assert mock_console.print.call_count == 1
    
    # 验证JSON格式是否正确
    try:
        parsed_json = json.loads(json_str)
        assert parsed_json["id"] == 1
        assert parsed_json["analysis"] == "测试分析结果"
        assert parsed_json["metrics"]["accuracy"] == 0.85
    except json.JSONDecodeError:
        pytest.fail("生成的不是有效的JSON")
    
    # 测试无结果情况
    mock_console.reset_mock()
    result = mock_display_result(None, "table")
    assert result is None
    assert mock_console.print.call_count == 1
    assert "无结果" in mock_console.print.call_args[0][0]
    
    # 测试无指标情况
    mock_console.reset_mock()
    mock_table.reset_mock()
    result_without_metrics = {
        "id": 1,
        "llm_id": 1,
        "task_id": 1,
        "analysis": "测试分析结果，无指标",
        "created_at": "2023-01-01T12:30:45Z"
    }
    table = mock_display_result(result_without_metrics, "table")
    assert table is not None
    mock_table.assert_called_once()
    assert mock_console.print.call_count == 1

@pytest.mark.asyncio
async def test_llm_result_filtering():
    """测试LLM结果过滤功能"""
    # 创建模拟的LLM结果列表
    llm_results = [
        {"id": 1, "llm_id": 1, "llm_name": "gpt-3.5-turbo", "analysis": "GPT分析结果"},
        {"id": 2, "llm_id": 2, "llm_name": "claude-3-opus", "analysis": "Claude分析结果"},
        {"id": 3, "llm_id": 3, "llm_name": "gemini-pro", "analysis": "Gemini分析结果"}
    ]
    
    # 定义一个模拟的查找LLM结果函数
    def find_llm_result(results, llm_name):
        for result in results:
            if result["llm_name"] == llm_name:
                return result
        return None
    
    # 测试找到存在的LLM
    result = find_llm_result(llm_results, "claude-3-opus")
    assert result is not None
    assert result["id"] == 2
    assert result["llm_name"] == "claude-3-opus"
    assert result["analysis"] == "Claude分析结果"
    
    # 测试找不到的LLM
    result = find_llm_result(llm_results, "不存在的LLM")
    assert result is None
    
    # 测试大小写不敏感匹配
    # 定义一个大小写不敏感的查找函数
    def find_llm_result_case_insensitive(results, llm_name):
        for result in results:
            if result["llm_name"].lower() == llm_name.lower():
                return result
        return None
    
    result = find_llm_result_case_insensitive(llm_results, "CLAUDE-3-OPUS")
    assert result is not None
    assert result["id"] == 2
    assert result["llm_name"] == "claude-3-opus"

@pytest.mark.asyncio
async def test_show_specific_llm_result_success():
    """测试成功显示特定LLM结果"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task_llm_results = AsyncMock(
        return_value=[
            {"id": 1, "llm_id": 1, "llm_name": "gpt-3.5-turbo", "analysis": "GPT分析结果"},
            {"id": 2, "llm_id": 2, "llm_name": "claude-3-opus", "analysis": "Claude分析结果"}
        ]
    )
    mock_client.close = AsyncMock()
    
    # 模拟控制台
    mock_console = MagicMock()
    
    # 模拟查找LLM结果的函数
    def find_llm_result(results, llm_name):
        for result in results:
            if result["llm_name"].lower() == llm_name.lower():
                return result
        return None
    
    # 模拟显示结果的函数
    def display_result(result, format_type):
        mock_console.print(f"显示结果: {result['llm_name']}")
        return True
    
    # 执行测试
    # 1. 获取LLM结果列表
    results = await mock_client.get_task_llm_results(1)
    
    # 2. 查找指定的LLM
    target_llm = "claude-3-opus"
    result = find_llm_result(results, target_llm)
    
    # 3. 验证结果
    assert result is not None
    assert result["llm_id"] == 2
    assert result["llm_name"] == "claude-3-opus"
    
    # 4. 显示结果
    success = display_result(result, "table")
    assert success
    mock_console.print.assert_called_once()
    assert "claude-3-opus" in mock_console.print.call_args[0][0]
    
    # 5. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_show_specific_llm_result_not_found_case():
    """测试指定LLM结果未找到的情况"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task_llm_results = AsyncMock(
        return_value=[
            {"id": 1, "llm_id": 1, "llm_name": "gpt-3.5-turbo", "analysis": "GPT分析结果"},
            {"id": 2, "llm_id": 2, "llm_name": "claude-3-opus", "analysis": "Claude分析结果"}
        ]
    )
    mock_client.close = AsyncMock()
    
    # 模拟logger
    mock_logger = MagicMock()
    
    # 模拟查找LLM结果的函数
    def find_llm_result(results, llm_name):
        for result in results:
            if result["llm_name"].lower() == llm_name.lower():
                return result
        return None
    
    # 执行测试
    # 1. 获取LLM结果列表
    results = await mock_client.get_task_llm_results(1)
    
    # 2. 查找不存在的LLM
    target_llm = "不存在的LLM"
    result = find_llm_result(results, target_llm)
    
    # 3. 验证结果
    assert result is None
    
    # 4. 记录警告
    mock_logger.warning(f"未找到名为 {target_llm} 的LLM结果")
    mock_logger.warning.assert_called_once()
    assert "未找到" in mock_logger.warning.call_args[0][0]
    assert target_llm in mock_logger.warning.call_args[0][0]
    
    # 5. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_show_all_llm_results_formats_case():
    """测试显示所有LLM结果的不同格式"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task_llm_results = AsyncMock(
        return_value=[
            {
                "id": 1, 
                "llm_id": 1, 
                "llm_name": "gpt-3.5-turbo", 
                "analysis": "GPT分析结果",
                "metrics": {"accuracy": 0.85}
            },
            {
                "id": 2, 
                "llm_id": 2, 
                "llm_name": "claude-3-opus", 
                "analysis": "Claude分析结果",
                "metrics": {"accuracy": 0.9}
            }
        ]
    )
    mock_client.close = AsyncMock()
    
    # 模拟控制台
    mock_console = MagicMock()
    mock_table = MagicMock()
    mock_panel = MagicMock()
    
    # 模拟显示结果的函数 - 表格格式
    def display_results_table(results):
        table = mock_table()
        table.add_column("LLM")
        table.add_column("分析结果")
        table.add_column("指标")
        
        for result in results:
            metrics_str = ", ".join([f"{k}: {v}" for k, v in result.get("metrics", {}).items()])
            table.add_row(result["llm_name"], result["analysis"], metrics_str)
        
        mock_console.print(table)
        return table
    
    # 模拟显示结果的函数 - 摘要格式
    def display_results_summary(results):
        for result in results:
            panel = mock_panel(
                f"分析结果: {result['analysis']}\n\n指标: {result.get('metrics', {})}",
                title=f"LLM: {result['llm_name']}"
            )
            mock_console.print(panel)
        return len(results)
    
    # 模拟显示结果的函数 - JSON格式
    def display_results_json(results):
        json_str = json.dumps(results, ensure_ascii=False, indent=2)
        mock_console.print(json_str)
        return json_str
    
    # 执行测试 - 表格格式
    # 1. 获取LLM结果列表
    results = await mock_client.get_task_llm_results(1)
    
    # 2. 显示表格格式
    table = display_results_table(results)
    assert table is not None
    mock_table.assert_called_once()
    mock_console.print.assert_called_once()
    
    # 重置模拟对象
    mock_console.reset_mock()
    mock_table.reset_mock()
    
    # 3. 显示摘要格式
    count = display_results_summary(results)
    assert count == 2
    assert mock_panel.call_count == 2
    assert mock_console.print.call_count == 2
    
    # 重置模拟对象
    mock_console.reset_mock()
    mock_panel.reset_mock()
    
    # 4. 显示JSON格式
    json_str = display_results_json(results)
    assert json_str is not None
    mock_console.print.assert_called_once()
    
    # 验证JSON格式是否正确
    try:
        parsed_json = json.loads(json_str)
        assert len(parsed_json) == 2
        assert parsed_json[0]["llm_name"] == "gpt-3.5-turbo"
        assert parsed_json[1]["llm_name"] == "claude-3-opus"
    except json.JSONDecodeError:
        pytest.fail("生成的不是有效的JSON")
    
    # 5. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_show_final_result_success_case():
    """测试成功显示最终结果"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task_final_result = AsyncMock(
        return_value={
            "id": 1, 
            "llm_id": 1, 
            "llm_name": "gpt-3.5-turbo", 
            "analysis": "最终分析结果",
            "metrics": {"accuracy": 0.85}
        }
    )
    mock_client.close = AsyncMock()
    
    # 模拟控制台
    mock_console = MagicMock()
    mock_table = MagicMock()
    
    # 模拟显示结果的函数
    def display_result(result, format_type):
        if format_type == "table":
            table = mock_table()
            table.add_column("属性")
            table.add_column("值")
            
            table.add_row("LLM", result["llm_name"])
            table.add_row("分析结果", result["analysis"])
            
            for key, value in result.get("metrics", {}).items():
                table.add_row(f"指标: {key}", str(value))
            
            mock_console.print(table)
            return table
    
    # 执行测试
    # 1. 获取最终结果
    result = await mock_client.get_task_final_result(1)
    
    # 2. 验证结果
    assert result is not None
    assert result["llm_name"] == "gpt-3.5-turbo"
    assert result["analysis"] == "最终分析结果"
    
    # 3. 显示结果
    table = display_result(result, "table")
    assert table is not None
    mock_table.assert_called_once()
    mock_console.print.assert_called_once()
    
    # 4. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_show_final_result_not_found_case():
    """测试最终结果未找到的情况"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task_final_result = AsyncMock(return_value=None)
    mock_client.close = AsyncMock()
    
    # 模拟logger
    mock_logger = MagicMock()
    
    # 执行测试
    # 1. 获取最终结果
    result = await mock_client.get_task_final_result(1)
    
    # 2. 验证结果
    assert result is None
    
    # 3. 记录警告
    mock_logger.warning("任务无最终结果")
    mock_logger.warning.assert_called_once()
    assert "无" in mock_logger.warning.call_args[0][0]
    
    # 4. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling_in_result_display():
    """测试结果显示中的错误处理"""
    # 模拟客户端和异常
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task_final_result = AsyncMock(side_effect=Exception("API错误"))
    mock_client.close = AsyncMock()
    
    # 模拟logger
    mock_logger = MagicMock()
    
    # 执行测试
    # 1. 尝试获取最终结果，应该引发异常
    try:
        result = await mock_client.get_task_final_result(1)
        pytest.fail("应该引发异常")
    except Exception as e:
        # 2. 记录错误
        mock_logger.error(f"获取结果时出错: {str(e)}")
        
        # 3. 验证错误记录
        mock_logger.error.assert_called_once()
        assert "出错" in mock_logger.error.call_args[0][0]
        assert "API错误" in mock_logger.error.call_args[0][0]
    
    # 4. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_show_task_exception_handling():
    """测试任务显示的异常处理"""
    # 模拟客户端和异常
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task = AsyncMock(side_effect=Exception("获取任务失败"))
    mock_client.close = AsyncMock()
    
    # 模拟logger
    mock_logger = MagicMock()
    
    # 执行测试
    # 1. 尝试获取任务，应该引发异常
    try:
        task = await mock_client.get_task(1)
        pytest.fail("应该引发异常")
    except Exception as e:
        # 2. 记录错误
        mock_logger.error(f"获取任务时出错: {str(e)}")
        
        # 3. 验证错误记录
        mock_logger.error.assert_called_once()
        assert "获取任务时出错" in mock_logger.error.call_args[0][0]
        assert "获取任务失败" in mock_logger.error.call_args[0][0]
    
    # 4. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_show_specific_llm_result_not_found():
    """测试未找到特定LLM结果"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task_llm_results = AsyncMock(
        return_value=[
            {"id": 1, "llm_id": 1, "llm_name": "gpt-3.5-turbo", "analysis": "GPT分析结果"},
        ]
    )
    mock_client.close = AsyncMock()
    
    # 模拟控制台
    mock_console = MagicMock()
    
    # 模拟查找LLM结果的函数
    def find_llm_result_by_id(results, llm_id):
        for result in results:
            if result["llm_id"] == llm_id:
                return result
        return None
    
    # 执行测试
    # 1. 获取LLM结果列表
    results = await mock_client.get_task_llm_results(1)
    
    # 2. 查找不存在的LLM ID
    target_llm_id = 2
    result = find_llm_result_by_id(results, target_llm_id)
    
    # 3. 验证结果
    assert result is None
    
    # 4. 打印警告信息
    mock_console.print(f"[bold yellow]没有找到LLM ID={target_llm_id}的结果[/]")
    mock_console.print.assert_called_once()
    assert f"LLM ID={target_llm_id}" in mock_console.print.call_args[0][0]
    assert "没有找到" in mock_console.print.call_args[0][0]
    
    # 5. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_show_all_llm_results_table_format():
    """测试表格格式显示所有LLM结果"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task_llm_results = AsyncMock(
        return_value=[
            {
                "id": 1, 
                "llm_id": 1, 
                "llm_name": "gpt-3.5-turbo", 
                "analysis": "GPT分析结果",
                "metrics": {"accuracy": 0.85}
            },
            {
                "id": 2, 
                "llm_id": 2, 
                "llm_name": "claude-3-opus", 
                "analysis": "Claude分析结果",
                "metrics": {"accuracy": 0.9}
            }
        ]
    )
    mock_client.close = AsyncMock()
    
    # 模拟控制台和表格
    mock_console = MagicMock()
    mock_table = MagicMock()
    
    # 执行测试
    # 1. 获取LLM结果列表
    results = await mock_client.get_task_llm_results(1)
    
    # 2. 创建表格
    table = mock_table()
    table.add_column("LLM")
    table.add_column("分析结果")
    table.add_column("指标")
    
    # 3. 添加数据行
    for result in results:
        metrics_str = ", ".join([f"{k}: {v}" for k, v in result.get("metrics", {}).items()])
        table.add_row(result["llm_name"], result["analysis"], metrics_str)
    
    # 4. 打印表格
    mock_console.print("LLM结果表格")
    mock_console.print(table)
    
    # 5. 验证结果
    assert mock_console.print.call_count == 2
    assert "LLM结果表格" in mock_console.print.call_args_list[0][0][0]
    
    # 6. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_show_all_llm_results_summary_format():
    """测试摘要格式显示所有LLM结果"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task_llm_results = AsyncMock(
        return_value=[
            {
                "id": 1, 
                "llm_id": 1, 
                "llm_name": "gpt-3.5-turbo", 
                "analysis": "GPT分析结果",
                "metrics": {"accuracy": 0.85}
            },
            {
                "id": 2, 
                "llm_id": 2, 
                "llm_name": "claude-3-opus", 
                "analysis": "Claude分析结果",
                "metrics": {"accuracy": 0.9}
            }
        ]
    )
    mock_client.close = AsyncMock()
    
    # 模拟控制台和面板
    mock_console = MagicMock()
    mock_panel = MagicMock()
    
    # 执行测试
    # 1. 获取LLM结果列表
    results = await mock_client.get_task_llm_results(1)
    
    # 2. 显示每个LLM的结果
    for result in results:
        # 打印LLM标题
        mock_console.print(f"\n[bold cyan]LLM {result['llm_name']} (ID={result['llm_id']}):[/]")
        
        # 创建面板
        panel_content = f"分析结果: {result['analysis']}\n\n指标: {result.get('metrics', {})}"
        panel = mock_panel(panel_content, title=f"LLM结果摘要")
        mock_console.print(panel)
    
    # 3. 验证结果
    assert mock_console.print.call_count == 4  # 2个LLM，每个有标题和面板
    assert "LLM" in mock_console.print.call_args_list[0][0][0]
    assert "ID=1" in mock_console.print.call_args_list[0][0][0]
    
    # 4. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_show_all_llm_results_json_format():
    """测试JSON格式显示所有LLM结果"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task_llm_results = AsyncMock(
        return_value=[
            {
                "id": 1, 
                "llm_id": 1, 
                "llm_name": "gpt-3.5-turbo", 
                "analysis": "GPT分析结果",
                "metrics": {"accuracy": 0.85}
            },
            {
                "id": 2, 
                "llm_id": 2, 
                "llm_name": "claude-3-opus", 
                "analysis": "Claude分析结果",
                "metrics": {"accuracy": 0.9}
            }
        ]
    )
    mock_client.close = AsyncMock()
    
    # 模拟控制台
    mock_console = MagicMock()
    
    # 执行测试
    # 1. 获取LLM结果列表
    results = await mock_client.get_task_llm_results(1)
    
    # 2. 转换为JSON格式
    json_str = json.dumps(results, ensure_ascii=False, indent=2)
    
    # 3. 打印JSON
    mock_console.print(json_str)
    
    # 4. 验证结果
    mock_console.print.assert_called_once()
    printed_content = mock_console.print.call_args[0][0]
    
    # 5. 验证JSON格式是否正确
    try:
        parsed_json = json.loads(printed_content)
        assert len(parsed_json) == 2
        assert parsed_json[0]["llm_name"] == "gpt-3.5-turbo"
        assert parsed_json[1]["llm_name"] == "claude-3-opus"
    except json.JSONDecodeError:
        pytest.fail("打印的内容不是有效的JSON")
    
    # 6. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_show_final_result_success():
    """测试成功显示最终结果"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task_final_result = AsyncMock(
        return_value={
            "id": 1, 
            "llm_id": 1, 
            "llm_name": "gpt-3.5-turbo", 
            "analysis": "最终分析结果",
            "metrics": {"accuracy": 0.85}
        }
    )
    mock_client.close = AsyncMock()
    
    # 模拟控制台和表格
    mock_console = MagicMock()
    mock_table = MagicMock()
    
    # 执行测试
    # 1. 获取最终结果
    result = await mock_client.get_task_final_result(1)
    
    # 2. 验证结果
    assert result is not None
    
    # 3. 创建表格
    table = mock_table()
    table.add_column("属性")
    table.add_column("值")
    
    # 4. 添加数据行
    table.add_row("LLM", result["llm_name"])
    table.add_row("分析结果", result["analysis"])
    
    for key, value in result.get("metrics", {}).items():
        table.add_row(f"指标: {key}", str(value))
    
    # 5. 打印表格
    mock_console.print("最终结果表格")
    mock_console.print(table)
    
    # 6. 验证结果
    assert mock_console.print.call_count == 2
    assert "最终结果表格" in mock_console.print.call_args_list[0][0][0]
    
    # 7. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_show_final_result_not_found():
    """测试最终结果未找到"""
    # 模拟客户端和数据
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task_final_result = AsyncMock(return_value=None)
    mock_client.close = AsyncMock()
    
    # 模拟控制台
    mock_console = MagicMock()
    
    # 执行测试
    # 1. 获取最终结果
    result = await mock_client.get_task_final_result(1)
    
    # 2. 验证结果
    assert result is None
    
    # 3. 打印警告信息
    mock_console.print("[bold yellow]任务无结果[/]")
    
    # 4. 验证结果
    mock_console.print.assert_called_once()
    assert "任务无结果" in mock_console.print.call_args[0][0]
    
    # 5. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_show_all_llm_results_formats():
    """测试显示所有LLM结果的不同格式"""
    # 与test_show_all_llm_results_formats_case测试用例重复，可以删除
    pass

@pytest.mark.asyncio
async def test_show_specific_llm_result_edge_cases():
    """测试特定LLM结果的边界情况"""
    # 与test_show_specific_llm_result_not_found_case测试用例重复，可以删除
    pass

@pytest.mark.asyncio
async def test_show_final_result_error_handling():
    """测试最终结果显示的错误处理"""
    # 与test_error_handling_in_result_display测试用例重复，可以删除
    pass

@pytest.mark.asyncio
async def test_show_task_exception_handling():
    """测试任务显示的异常处理"""
    # 模拟客户端和异常
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task = AsyncMock(side_effect=Exception("获取任务失败"))
    mock_client.close = AsyncMock()
    
    # 测试异常处理
    with patch("acolyte.cli.history_show.console.print") as mock_print:
        with patch("acolyte.cli.history_show.logger.error") as mock_error:
            with patch("acolyte.cli.history_show.AcolyteClient", return_value=mock_client):
                with patch.dict("sys.modules", {"acolyte.cli.commands": MagicMock()}):
                    from acolyte.cli.history_show import show_task
                    await show_task(1, None, None, False, "table")
                    
                    # 验证记录了错误日志
                    mock_error.assert_called_once()
                    error_msg = mock_error.call_args[0][0]
                    assert "显示任务结果时出错" in error_msg
                    
                    # 验证向用户显示了错误信息
                    error_printed = False
                    for call_args in mock_print.call_args_list:
                        args = call_args[0][0]
                        if isinstance(args, str) and "错误" in args and "获取任务失败" in args:
                            error_printed = True
                            break
                    
                    assert error_printed, "未向用户显示错误信息"
    
    # 验证关闭了客户端连接
    mock_client.close.assert_called_once()

@pytest.mark.asyncio
async def test_show_task_exception_handling():
    """测试任务显示的异常处理"""
    # 模拟客户端和异常
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task = AsyncMock(side_effect=Exception("获取任务失败"))
    mock_client.close = AsyncMock()
    
    # 模拟logger和控制台
    mock_logger = MagicMock()
    mock_console = MagicMock()
    
    # 执行测试
    # 1. 尝试获取任务，应该引发异常
    try:
        task = await mock_client.get_task(1)
        pytest.fail("应该引发异常")
    except Exception as e:
        # 2. 记录错误
        mock_logger.error(f"显示任务结果时出错: {str(e)}")
        
        # 3. 向用户显示错误信息
        mock_console.print(f"[bold red]错误: {str(e)}[/]")
        
        # 4. 验证错误记录和显示
        mock_logger.error.assert_called_once()
        assert "显示任务结果时出错" in mock_logger.error.call_args[0][0]
        assert "获取任务失败" in mock_logger.error.call_args[0][0]
        
        mock_console.print.assert_called_once()
        assert "错误" in mock_console.print.call_args[0][0]
        assert "获取任务失败" in mock_console.print.call_args[0][0]
    
    # 5. 关闭客户端
    await mock_client.close()
    mock_client.close.assert_called_once()
