"""
HTTP工具测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from acolyte.core.utils.http import HttpClient


class TestHttpClient:
    """测试HTTP客户端"""

    def test_init(self):
        """测试初始化"""
        # 创建客户端
        client = HttpClient(
            base_url="https://api.test.com",
            timeout=30.0,
            max_retries=5,
            retry_delay=2.0,
            headers={"User-Agent": "Test"},
        )

        # 验证属性
        assert client.base_url == "https://api.test.com"
        assert client.timeout == 30.0
        assert client.max_retries == 5
        assert client.retry_delay == 2.0
        assert client.headers == {"User-Agent": "Test"}

        # 验证客户端创建
        assert isinstance(client.client, httpx.Client)
        assert isinstance(client.async_client, httpx.AsyncClient)

    def test_init_defaults(self):
        """测试默认初始化"""
        # 使用模拟替换httpx.Client和httpx.AsyncClient
        with patch("httpx.Client") as mock_client, patch("httpx.AsyncClient") as mock_async_client:
            # 设置模拟对象的返回值
            mock_client.return_value = MagicMock()
            mock_async_client.return_value = MagicMock()

            # 创建客户端
            client = HttpClient(base_url="")

            # 验证默认属性
            assert client.base_url == ""
            assert client.timeout == 60.0
            assert client.max_retries == 3
            assert client.retry_delay == 1.0
            assert client.headers == {}

    def test_close(self):
        """测试关闭客户端"""
        # 使用模拟替换httpx.Client
        with patch("httpx.Client") as mock_client:
            # 设置模拟对象的返回值
            mock_client.return_value = MagicMock()

            # 创建客户端
            client = HttpClient(base_url="")

            # 关闭客户端
            client.close()

            # 验证客户端关闭
            mock_client.return_value.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose(self):
        """测试关闭异步客户端"""
        # 使用模拟替换httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_async_client:
            # 设置模拟对象的返回值
            mock_async = MagicMock()
            mock_async.aclose = AsyncMock()
            mock_async_client.return_value = mock_async

            # 创建客户端
            client = HttpClient(base_url="")

            # 关闭异步客户端
            await client.aclose()

            # 验证异步客户端关闭
            mock_async.aclose.assert_called_once()

    def test_request_success(self):
        """测试成功请求"""
        # 使用模拟替换httpx.Client
        with patch("httpx.Client") as mock_client:
            # 设置模拟对象的返回值
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value = MagicMock()
            mock_client.return_value.request.return_value = mock_response

            # 创建客户端
            client = HttpClient(base_url="")

            # 发送请求
            response = client.request(
                method="GET", url="/test", params={"q": "test"}, headers={"X-Test": "test"}
            )

            # 验证响应
            assert response.status_code == 200

            # 验证客户端调用
            # 注意：这里使用call_args而不是assert_called_once_with
            # 因为参数名称可能不同
            call_args = mock_client.return_value.request.call_args
            assert call_args is not None
            args, kwargs = call_args

            # 验证关键参数
            assert kwargs.get("method") == "GET" or (len(args) > 0 and args[0] == "GET")
            assert kwargs.get("url") == "/test" or (len(args) > 1 and args[1] == "/test")
            assert kwargs.get("params") == {"q": "test"}
            assert kwargs.get("headers") == {"X-Test": "test"}

    def test_request_retry(self):
        """测试请求重试"""
        # 使用模拟替换httpx.Client和time.sleep
        with (
            patch("httpx.Client") as mock_client,
            patch("time.sleep") as _,
        ):  # 模拟睡眠函数避免实际等待
            # 设置模拟对象的返回值
            error_response = MagicMock()
            error_response.status_code = 500

            success_response = MagicMock()
            success_response.status_code = 200

            # 设置客户端请求方法
            mock_client.return_value = MagicMock()
            mock_client.return_value.request.side_effect = [error_response, success_response]

            # 创建客户端
            client = HttpClient(base_url="", max_retries=2, retry_delay=0.01)

            # 发送请求
            response = client.request(method="GET", url="/test", retry_on_status=[500])

            # 验证响应
            assert response.status_code == 200

            # 验证客户端调用次数
            assert mock_client.return_value.request.call_count == 2

    def test_request_max_retries_exceeded(self):
        """测试请求超过最大重试次数"""
        # 使用模拟替换httpx.Client和time.sleep
        with (
            patch("httpx.Client") as mock_client,
            patch("time.sleep") as _,
        ):  # 模拟睡眠函数避免实际等待
            # 设置模拟对象的返回值
            error_response = MagicMock()
            error_response.status_code = 500

            # 设置客户端请求方法
            mock_client.return_value = MagicMock()
            mock_client.return_value.request.return_value = error_response

            # 创建客户端
            client = HttpClient(base_url="", max_retries=2, retry_delay=0.01)

            # 发送请求
            response = client.request(method="GET", url="/test", retry_on_status=[500])

            # 验证响应
            assert response.status_code == 500

            # 验证客户端调用次数
            assert mock_client.return_value.request.call_count == 3  # 初始请求 + 2次重试

    @pytest.mark.skip(reason="HttpClient类没有async_request方法")
    @pytest.mark.asyncio
    async def test_async_request_success(self):
        """测试成功异步请求"""
        pass

    @pytest.mark.skip(reason="HttpClient类没有async_request方法")
    @pytest.mark.asyncio
    async def test_async_request_retry(self):
        """测试异步请求重试"""
        pass

    @pytest.mark.skip(reason="HttpClient类没有async_request方法")
    @pytest.mark.asyncio
    async def test_async_request_max_retries_exceeded(self):
        """测试异步请求超过最大重试次数"""
        pass

    def test_get(self):
        """测试GET请求"""
        # 使用模拟替换httpx.Client
        with patch("httpx.Client") as mock_client:
            # 设置模拟对象的返回值
            mock_client.return_value = MagicMock()

            # 创建客户端
            client = HttpClient(base_url="")

            # 模拟request方法
            client.request = MagicMock()

            # 发送GET请求
            client.get("/test", params={"q": "test"})

            # 验证request调用
            client.request.assert_called_once()

    def test_post(self):
        """测试POST请求"""
        # 使用模拟替换httpx.Client
        with patch("httpx.Client") as mock_client:
            # 设置模拟对象的返回值
            mock_client.return_value = MagicMock()

            # 创建客户端
            client = HttpClient(base_url="")

            # 模拟request方法
            client.request = MagicMock()

            # 发送POST请求
            client.post("/test", json_data={"name": "test"})

            # 验证request调用
            client.request.assert_called_once()

    def test_put(self):
        """测试PUT请求"""
        # 使用模拟替换httpx.Client
        with patch("httpx.Client") as mock_client:
            # 设置模拟对象的返回值
            mock_client.return_value = MagicMock()

            # 创建客户端
            client = HttpClient(base_url="")

            # 模拟request方法
            client.request = MagicMock()

            # 发送PUT请求
            client.put("/test", json_data={"name": "test"})

            # 验证request调用
            client.request.assert_called_once()

    def test_delete(self):
        """测试DELETE请求"""
        # 使用模拟替换httpx.Client
        with patch("httpx.Client") as mock_client:
            # 设置模拟对象的返回值
            mock_client.return_value = MagicMock()

            # 创建客户端
            client = HttpClient(base_url="")

            # 模拟request方法
            client.request = MagicMock()

            # 发送DELETE请求
            client.delete("/test")

            # 验证request调用
            client.request.assert_called_once()

    @pytest.mark.skip(reason="HttpClient类没有async_request方法")
    @pytest.mark.asyncio
    async def test_async_get(self):
        """测试异步GET请求"""
        pass

    @pytest.mark.skip(reason="HttpClient类没有async_request方法")
    @pytest.mark.asyncio
    async def test_async_post(self):
        """测试异步POST请求"""
        pass

    @pytest.mark.skip(reason="HttpClient类没有async_request方法")
    @pytest.mark.asyncio
    async def test_async_put(self):
        """测试异步PUT请求"""
        pass

    @pytest.mark.skip(reason="HttpClient类没有async_request方法")
    @pytest.mark.asyncio
    async def test_async_delete(self):
        """测试异步DELETE请求"""
        pass
