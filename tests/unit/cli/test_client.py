"""
CLI客户端测试
"""

import os
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from acolyte.cli.commands import AcolyteClient


class TestAcolyteClient:
    """测试Acolyte API客户端"""

    def test_init_with_default_url(self):
        """测试使用默认URL初始化客户端"""
        # 模拟环境变量
        with patch.dict(os.environ, {}, clear=True):
            client = AcolyteClient()
            assert client.base_url == "http://localhost:8000/api"

    def test_init_with_env_url(self):
        """测试使用环境变量URL初始化客户端"""
        # 模拟环境变量
        with patch.dict(os.environ, {"ACOLYTE_API_URL": "http://test-api:9000/api"}, clear=True):
            client = AcolyteClient()
            assert client.base_url == "http://test-api:9000/api"

    def test_init_with_custom_url(self):
        """测试使用自定义URL初始化客户端"""
        client = AcolyteClient(base_url="http://custom-api:8080/api")
        assert client.base_url == "http://custom-api:8080/api"

    @pytest.mark.asyncio
    async def test_close(self):
        """测试关闭客户端连接"""
        client = AcolyteClient()
        # 模拟客户端
        client.client = AsyncMock()

        # 调用close方法
        await client.close()

        # 验证aclose被调用
        client.client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_success(self):
        """测试成功检查API服务连接"""
        client = AcolyteClient()

        # 模拟 httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            # 模拟响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}

            # 设置模拟客户端
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__.return_value = mock_client
            mock_client_class.return_value = mock_client

            # 调用check_connection方法
            status, message = await client.check_connection()

            # 验证结果
            assert status is True
            assert message is None

    @pytest.mark.asyncio
    async def test_check_connection_failure(self):
        """测试API服务连接失败"""
        client = AcolyteClient()

        # 模拟 httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            # 设置模拟客户端
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection error"))
            mock_client.__aenter__.return_value = mock_client
            mock_client_class.return_value = mock_client

            # 调用check_connection方法
            status, message = await client.check_connection()

            # 验证结果
            assert status is False
            assert "无法连接到API服务" in message

    @pytest.mark.asyncio
    async def test_check_connection_error_response(self):
        """测试API服务返回错误响应"""
        client = AcolyteClient()

        # 模拟 httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            # 模拟响应
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            # 创建一个带有响应的HTTPStatusError
            http_error = httpx.HTTPStatusError(
                "HTTP Error", request=MagicMock(), response=mock_response
            )

            # 设置模拟客户端
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=http_error)
            mock_client.__aenter__.return_value = mock_client
            mock_client_class.return_value = mock_client

            # 调用check_connection方法
            status, message = await client.check_connection()

            # 验证结果
            assert status is False
            assert "API服务返回错误状态" in message
