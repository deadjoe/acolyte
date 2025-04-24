"""
API测试的共享测试夹具
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from acolyte.api.app import app


@pytest.fixture
def test_client():
    """创建测试客户端"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_llm_service():
    """模拟LLM服务"""
    with patch("acolyte.api.routes.LlmService") as mock_service_class:
        # 创建模拟服务实例
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # 设置异步方法的返回值
        mock_service.get_llms = AsyncMock(
            return_value={
                "success": True,
                "llms": [
                    {
                        "id": 1,
                        "name": "Test LLM",
                        "base_url": "https://api.test.com",
                        "model_name": "test-model",
                        "role": "normal",
                        "is_default": True,
                    }
                ],
            }
        )

        mock_service.get_llm = AsyncMock(
            return_value={
                "success": True,
                "id": 1,
                "name": "Test LLM",
                "base_url": "https://api.test.com",
                "model_name": "test-model",
                "role": "normal",
                "is_default": True,
            }
        )

        mock_service.add_llm = AsyncMock(
            return_value={
                "success": True,
                "id": 1,
                "name": "Test LLM",
                "base_url": "https://api.test.com",
                "model_name": "test-model",
                "role": "normal",
                "is_default": True,
            }
        )

        mock_service.update_llm = AsyncMock(
            return_value={
                "success": True,
                "id": 1,
                "name": "Updated LLM",
                "base_url": "https://api.test.com",
                "model_name": "test-model",
                "role": "normal",
                "is_default": True,
            }
        )

        mock_service.delete_llm = AsyncMock(return_value={"success": True, "id": 1})

        mock_service.set_default_llm = AsyncMock(
            return_value={"success": True, "id": 1, "name": "Test LLM"}
        )

        mock_service.test_connection = AsyncMock(
            return_value={"success": True, "message": "连接测试成功", "elapsed_time": 0.5}
        )

        yield mock_service


@pytest.fixture
def mock_task_service():
    """模拟任务服务"""
    with patch("acolyte.api.routes.TaskService") as mock_service_class:
        # 创建模拟服务实例
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # 设置异步方法的返回值
        mock_service.create_task = AsyncMock(
            return_value={
                "success": True,
                "id": 1,
                "content": "Test content",
                "processing_mode": "single",
                "status": "pending",
            }
        )

        mock_service.get_task = AsyncMock(
            return_value={
                "success": True,
                "id": 1,
                "content": "Test content",
                "processing_mode": "single",
                "status": "completed",
            }
        )

        mock_service.get_tasks = AsyncMock(
            return_value={
                "success": True,
                "tasks": [
                    {
                        "id": 1,
                        "content": "Test content",
                        "processing_mode": "single",
                        "status": "completed",
                    }
                ],
            }
        )

        mock_service.get_task_results = AsyncMock(
            return_value={
                "success": True,
                "results": [
                    {
                        "id": 1,
                        "task_id": 1,
                        "llm_id": 1,
                        "bias_index": 5.0,
                        "misleading_index": 3.0,
                        "hidden_intent_index": 2.0,
                        "credibility_score": 80.0,
                        "is_review_result": False,
                    }
                ],
            }
        )

        mock_service.process_task_async = AsyncMock(
            return_value={"success": True, "id": 1, "status": "processing"}
        )

        mock_service.delete_task = AsyncMock(return_value={"success": True, "id": 1})

        yield mock_service


@pytest.fixture
def mock_prompt_service():
    """模拟提示词服务"""
    with patch("acolyte.api.routes.PromptService") as mock_service_class:
        # 创建模拟服务实例
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # 设置异步方法的返回值
        mock_service.get_prompts = AsyncMock(
            return_value={
                "success": True,
                "prompts": [
                    {
                        "id": 1,
                        "version": "1.0",
                        "model_target": "general",
                        "is_active": True,
                        "content": "Test prompt content",
                    }
                ],
            }
        )

        mock_service.get_prompt = AsyncMock(
            return_value={
                "success": True,
                "id": 1,
                "version": "1.0",
                "model_target": "general",
                "is_active": True,
                "content": "Test prompt content",
            }
        )

        mock_service.create_prompt = AsyncMock(
            return_value={
                "success": True,
                "id": 1,
                "version": "1.0",
                "model_target": "general",
                "is_active": True,
            }
        )

        mock_service.update_prompt = AsyncMock(
            return_value={
                "success": True,
                "id": 1,
                "version": "1.1",
                "model_target": "general",
                "is_active": True,
            }
        )

        mock_service.delete_prompt = AsyncMock(return_value={"success": True, "id": 1})

        yield mock_service
