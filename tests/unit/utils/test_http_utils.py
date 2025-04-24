"""
HTTP工具测试
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from acolyte.utils.http import HttpClientConfig, HttpClientManager, fetch


class TestHttpClientConfig:
    """测试HTTP客户端配置"""

    def test_init_with_defaults(self):
        """测试使用默认值初始化"""
        config = HttpClientConfig()

        # 验证默认值
        assert config.timeout == 60.0
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.retry_backoff == 2.0
        assert config.max_connections == 100
        assert config.verify_ssl is True
        assert config.follow_redirects is True
        assert config.http2 is False

    def test_init_with_custom_values(self):
        """测试使用自定义值初始化"""
        config = HttpClientConfig(
            timeout=30.0,
            max_retries=5,
            retry_delay=0.5,
            retry_backoff=1.5,
            max_connections=50,
            verify_ssl=False,
            follow_redirects=False,
            http2=True,
        )

        # 验证自定义值
        assert config.timeout == 30.0
        assert config.max_retries == 5
        assert config.retry_delay == 0.5
        assert config.retry_backoff == 1.5
        assert config.max_connections == 50
        assert config.verify_ssl is False
        assert config.follow_redirects is False
        assert config.http2 is True


class TestHttpClientManager:
    """测试HTTP客户端管理器"""

    @pytest.fixture
    def mock_client(self):
        """创建模拟HTTP客户端"""
        with patch("httpx.AsyncClient") as mock_client_class:
            # 创建模拟响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_response.text = '{"success": true}'
            mock_response.is_closed = False

            # 设置模拟客户端方法
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.is_closed = False

            # 设置模拟客户端类
            mock_client_class.return_value = mock_client

            yield mock_client

    def test_get_client(self, mock_client):
        """测试获取客户端"""
        # 清空客户端池
        HttpClientManager._clients = {}
        HttpClientManager._client_configs = {}

        # 获取客户端
        client = HttpClientManager.get_client()

        # 验证客户端
        assert client is not None
        assert "default" in HttpClientManager._clients
        assert "default" in HttpClientManager._client_configs

    def test_get_existing_client(self, mock_client):
        """测试获取已存在的客户端"""
        # 清空客户端池
        HttpClientManager._clients = {}
        HttpClientManager._client_configs = {}

        # 获取客户端
        client1 = HttpClientManager.get_client()
        client2 = HttpClientManager.get_client()

        # 验证客户端
        assert client1 is client2

    def test_get_client_with_custom_config(self, mock_client):
        """测试使用自定义配置获取客户端"""
        # 清空客户端池
        HttpClientManager._clients = {}
        HttpClientManager._client_configs = {}

        # 创建自定义配置
        config = HttpClientConfig(timeout=30.0, max_retries=5)

        # 获取客户端
        client = HttpClientManager.get_client(config=config)

        # 验证客户端配置
        assert HttpClientManager._client_configs["default"] is config
        assert HttpClientManager._client_configs["default"].timeout == 30.0
        assert HttpClientManager._client_configs["default"].max_retries == 5

    def test_get_client_with_name(self, mock_client):
        """测试使用名称获取客户端"""
        # 清空客户端池
        HttpClientManager._clients = {}
        HttpClientManager._client_configs = {}

        # 获取客户端
        client = HttpClientManager.get_client("test")

        # 验证客户端
        assert client is not None
        assert "test" in HttpClientManager._clients
        assert "test" in HttpClientManager._client_configs

    def test_get_closed_client(self, mock_client):
        """测试获取已关闭的客户端"""
        # 清空客户端池
        HttpClientManager._clients = {}
        HttpClientManager._client_configs = {}

        # 获取客户端
        client1 = HttpClientManager.get_client()

        # 使用模拟对象替换客户端池中的客户端
        mock_closed_client = MagicMock()
        mock_closed_client.is_closed = True
        HttpClientManager._clients["default"] = mock_closed_client

        # 再次获取客户端
        client2 = HttpClientManager.get_client()

        # 验证客户端
        assert HttpClientManager._clients["default"] is not mock_closed_client


@pytest.mark.asyncio
async def test_fetch():
    """测试fetch函数"""
    # 创建模拟响应
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    mock_response.text = '{"success": true}'

    # 模拟HttpClientManager.get_client
    with patch("acolyte.utils.http.HttpClientManager.get_client") as mock_get_client:
        # 创建模拟客户端
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        # 执行请求
        response = await fetch("https://api.test.com/resource")

        # 验证响应
        assert response.status_code == 200
        assert response.json() == {"success": True}

        # 验证客户端调用
        mock_client.request.assert_called_once()
