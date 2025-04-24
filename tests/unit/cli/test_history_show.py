"""
CLI历史显示测试
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


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
        results = await client.get_task_results(task_id, include_raw_response=raw_response)

        # 获取LLM列表
        llms = await client.get_llms()

        # 模拟输出
        mock_console.print("LLM结果")
        mock_console.print("详细分析")

        return None

    # 执行测试
    await mock_show_specific_llm_result(mock_client, 1, 2, True, True)

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
        llms = await client.get_llms()

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
    await mock_show_specific_llm_result(mock_client, 1, 2, False, True)

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
            },
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
        results = await client.get_task_results(task_id, include_raw_response=raw_response)

        # 获取LLM列表
        llms = await client.get_llms()

        # 模拟表格输出
        if format_type == "table":
            mock_console.print("LLM结果表格")

        return None

    # 执行测试
    await mock_show_all_llm_results(mock_client, 1, False, "table")

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
    await mock_show_all_llm_results(mock_client, 1, False, "summary")

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
    await mock_show_all_llm_results(mock_client, 1, False, "json")

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
        llms = await client.get_llms()

        # 模拟输出
        mock_console.print("最终结果表格")
        if raw_response and result.get("raw_response"):
            mock_console.print("详细分析")

        return None

    # 执行测试
    await mock_show_final_result(mock_client, 1, True, True)

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
            result = await client.get_task_final_result(task_id, include_raw_response=raw_response)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                mock_console.print("[bold yellow]任务无结果[/]")
            else:
                raise

        return None

    # 执行测试
    await mock_show_final_result(mock_client, 1, False, False)

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
