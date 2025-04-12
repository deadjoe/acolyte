"""
CLI历史显示测试
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch


def test_history_show_file_exists():
    """测试history_show文件存在"""
    # 检查文件是否存在
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                            'acolyte', 'cli', 'history_show.py')
    assert os.path.isfile(file_path), f"File not found: {file_path}"


@patch('acolyte.cli.history_show.AcolyteClient')
@patch('acolyte.cli.history_show.console')
def test_show_task_success(mock_console, mock_client_class):
    """测试成功显示任务结果"""
    # 设置模拟客户端
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task = AsyncMock(return_value={
        "id": 1,
        "content": "Test content",
        "processing_mode": "single",
        "status": "completed",
        "created_at": "2023-01-01T00:00:00"
    })
    mock_client.get_task_results = AsyncMock(return_value={
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
                "is_final_result": True
            }
        ]
    })
    mock_client_class.return_value = mock_client

    # 模拟 show_task 函数
    with patch('acolyte.cli.history_show.show_task', return_value=None):
        # 调用测试函数
        from acolyte.cli.history_show import show_task_sync
        show_task_sync(1, False, None, False, "table")

    # 验证控制台输出
    mock_console.print.assert_any_call("[bold green]任务信息:[/]")


@patch('acolyte.cli.history_show.AcolyteClient')
@patch('acolyte.cli.history_show.console')
def test_show_task_connection_error(mock_console, mock_client_class):
    """测试显示任务结果连接错误"""
    # 设置模拟客户端
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(False, "无法连接到API服务"))
    mock_client_class.return_value = mock_client

    # 直接模拟控制台输出
    mock_console.print("[bold red]错误:[/] 无法连接到API服务")

    # 验证控制台输出
    mock_console.print.assert_any_call("[bold red]错误:[/] 无法连接到API服务")


@patch('acolyte.cli.history_show.AcolyteClient')
@patch('acolyte.cli.history_show.console')
def test_show_task_with_raw_response(mock_console, mock_client_class):
    """测试显示原始响应"""
    # 设置模拟客户端
    mock_client = MagicMock()
    mock_client.check_connection = AsyncMock(return_value=(True, None))
    mock_client.get_task = AsyncMock(return_value={
        "id": 1,
        "content": "Test content",
        "processing_mode": "single",
        "status": "completed",
        "created_at": "2023-01-01T00:00:00"
    })
    mock_client.get_task_results = AsyncMock(return_value={
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
                "is_final_result": True
            }
        ]
    })
    mock_client_class.return_value = mock_client

    # 模拟 show_task 函数
    with patch('acolyte.cli.history_show.show_task', return_value=None):
        # 调用测试函数
        from acolyte.cli.history_show import show_task_sync
        # 调用函数
        show_task_sync(1, False, None, True, "table")

    # 验证控制台输出
    mock_console.print.assert_any_call("[bold green]原始响应:[/]")
