"""
LLM客户端基类单元测试

测试LlmClient基类的功能和行为。
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.base import LlmClient, retry_on_error
from acolyte.core.llm.retry import RetryConfig


# 创建一个具体的LlmClient子类用于测试
class TestLlmClientImpl(LlmClient):
    """用于测试的LlmClient实现"""

    def __init__(self, llm_config):
        super().__init__(llm_config)
        self.provider = "test_provider"

    def _detect_provider(self):
        return "test_provider"

    async def _send_request(self, endpoint, json_data):
        """Compat wrapper — calls _make_request and returns parsed JSON."""
        response = await self._make_request("POST", endpoint, json_data=json_data)
        return response.json()

    async def _test_connection(self):
        """Override for testing — delegates to mocked _make_request."""
        try:
            await self._make_request("GET", "/test")
            return True
        except Exception:
            return False

    def _get_headers(self):
        """获取请求头"""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        return headers

    def _prepare_request(self, prompt, system_prompt=None):
        return {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt or ""},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,  # 使用固定值而不是从不存在的parameters属性获取
        }

    def _process_response(self, response_data):
        if "choices" not in response_data:
            raise ValueError("Invalid response format")

        content = response_data["choices"][0]["message"]["content"]
        return {"content": content, "scores": self.response_parser.extract_scores(content)}

    def _parse_response(self, response_data):
        return self._process_response(response_data)

    async def process_content(self, content, prompt):
        """实现抽象方法process_content"""
        # 准备提示词
        full_prompt = self._prepare_prompt(content, prompt)

        # 准备请求数据
        request_data = self._prepare_request(full_prompt)

        # 发送请求
        response_data = await self._send_request("/chat/completions", request_data)

        # 解析响应
        result = self._parse_response(response_data)

        return {
            "success": True,
            "raw_response": response_data["choices"][0]["message"]["content"],
            "result": result,
        }


class TestLlmClient:
    """LlmClient基类的测试用例"""

    @pytest.fixture
    def llm_config(self):
        """创建测试用的LLM配置"""
        config = MagicMock(spec=LlmConfig)
        config.name = "Test LLM"
        config.api_key = "test_api_key"
        config.base_url = "https://api.test.com"
        config.model_name = "test-model"
        config.parameters = {
            "temperature": 0.7,
            "top_p": 0.9,
        }
        return config

    @pytest.fixture
    def client(self, llm_config):
        """创建LlmClient实例"""
        return TestLlmClientImpl(llm_config)

    def test_init(self, client, llm_config):
        """测试初始化"""
        assert client.name == llm_config.name
        assert client.api_key == llm_config.api_key
        assert client.base_url == llm_config.base_url
        assert client.model_name == llm_config.model_name
        # 不再检查parameters属性，因为LlmClient类中没有这个属性
        assert client.provider == "test_provider"
        assert client.response_parser is not None
        assert client.error_handler is not None
        assert client.retry_config is not None

    def test_init_with_default_parameters(self):
        """测试使用默认参数初始化"""
        # 创建最小配置
        config = MagicMock(spec=LlmConfig)
        config.name = "Test LLM"
        config.api_key = "test_api_key"
        config.base_url = "https://api.test.com"
        config.model_name = "test-model"
        config.parameters = None

        # 创建客户端
        client = TestLlmClientImpl(config)

        # 验证客户端初始化成功
        assert client.name == "Test LLM"
        assert client.api_key == "test_api_key"
        assert client.model_name == "test-model"

    def test_get_headers(self, client):
        """测试获取请求头"""
        headers = client._get_headers()

        assert isinstance(headers, dict)
        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {client.api_key}"
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_send_request_success(self, client):
        """测试发送请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": """
                        ## 分析
                        这是一个测试分析。

                        ## 评分
                        偏见指数: 7.5
                        误导性指数: 6.2
                        隐藏意图指数: 4.8
                        可信度分数: 60.5
                        """
                    }
                }
            ]
        }

        request_data = {
            "model": "test-model",
            "messages": [
                {"role": "system", "content": "系统提示词"},
                {"role": "user", "content": "用户提示词"},
            ],
        }

        with patch.object(LlmClient, "_make_request", return_value=mock_response):
            response = await client._send_request("/chat/completions", request_data)

        assert response is not None
        assert "choices" in response
        assert len(response["choices"]) > 0
        assert "message" in response["choices"][0]
        assert "content" in response["choices"][0]["message"]

    @pytest.mark.asyncio
    async def test_send_request_error(self, client):
        """测试发送请求错误"""
        request_data = {
            "model": "test-model",
            "messages": [
                {"role": "system", "content": "系统提示词"},
                {"role": "user", "content": "用户提示词"},
            ],
        }

        error_response = MagicMock()
        error_response.status_code = 400
        http_error = httpx.HTTPStatusError(
            "Invalid request", request=MagicMock(), response=error_response
        )

        with patch.object(LlmClient, "_make_request", side_effect=http_error):
            with pytest.raises(Exception) as excinfo:
                await client._send_request("/chat/completions", request_data)

        assert "Invalid request" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_process_content(self, client):
        """测试内容处理"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": """
                        ## 分析
                        这是一个测试分析。

                        ## 评分
                        偏见指数: 7.5
                        误导性指数: 6.2
                        隐藏意图指数: 4.8
                        可信度分数: 60.5
                        """
                    }
                }
            ]
        }

        with patch.object(LlmClient, "_make_request", return_value=mock_response):
            result = await client.process_content("测试内容", "系统提示词")

        assert result is not None
        assert result["success"] is True
        assert "raw_response" in result
        assert "result" in result
        assert "scores" in result["result"]

    @pytest.mark.asyncio
    async def test_test_connection(self, client):
        """测试连接测试"""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(LlmClient, "_make_request", return_value=mock_response):
            result = await client._test_connection()
        assert result is True

        error_response = MagicMock()
        error_response.status_code = 401
        http_error = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=error_response
        )
        with patch.object(LlmClient, "_make_request", side_effect=http_error):
            result = await client._test_connection()
        assert result is False


class TestRetryDecorator:
    """retry_on_error装饰器的测试用例"""

    @pytest.fixture
    def retry_config(self):
        """创建重试配置"""
        return RetryConfig(
            max_retries=3,
            initial_delay=0.01,  # 修改为initial_delay
            retry_status_codes=[429, 500, 502, 503, 504],
        )

    @pytest.fixture
    def test_class(self, retry_config):
        """创建测试类"""

        class TestClass:
            def __init__(self):
                self.retry_config = retry_config
                self.call_count = 0

            # 使用显式的重试配置
            @retry_on_error(config=retry_config)
            async def test_method(self):
                self.call_count += 1
                if self.call_count < 3:
                    mock_response = MagicMock()
                    mock_response.status_code = 503
                    mock_response.headers = {}
                    raise httpx.HTTPStatusError(
                        "Service unavailable", request=MagicMock(), response=mock_response
                    )
                return "success"

            @retry_on_error(config=retry_config)
            async def test_method_permanent_error(self):
                self.call_count += 1
                mock_response = MagicMock()
                mock_response.status_code = 400
                mock_response.headers = {}
                raise httpx.HTTPStatusError(
                    "Bad request", request=MagicMock(), response=mock_response
                )

            @retry_on_error(config=retry_config)
            async def test_method_network_error(self):
                self.call_count += 1
                if self.call_count < 3:
                    raise httpx.ConnectError("Connection error")
                return "success"

        return TestClass()

    @pytest.mark.asyncio
    async def test_retry_success(self, test_class):
        """测试重试成功"""
        # 重置计数器
        test_class.call_count = 0

        # 调用方法
        result = await test_class.test_method()

        # 验证结果
        assert result == "success"
        assert test_class.call_count == 3  # 前两次失败，第三次成功

    @pytest.mark.asyncio
    async def test_retry_permanent_error(self, test_class):
        """测试永久错误不重试"""
        # 重置计数器
        test_class.call_count = 0

        # 调用方法并验证异常
        with pytest.raises(httpx.HTTPStatusError):
            await test_class.test_method_permanent_error()

        # 验证结果
        assert test_class.call_count == 1  # 只调用一次，不重试

    @pytest.mark.asyncio
    async def test_retry_network_error(self, test_class):
        """测试网络错误重试"""
        # 重置计数器
        test_class.call_count = 0

        # 调用方法
        result = await test_class.test_method_network_error()

        # 验证结果
        assert result == "success"
        assert test_class.call_count == 3  # 前两次失败，第三次成功

    @pytest.mark.asyncio
    async def test_retry_max_exceeded(self, test_class):
        """测试超过最大重试次数"""
        # 修改重试配置
        test_class.retry_config.max_retries = 1

        # 重置计数器
        test_class.call_count = 0

        # 调用方法并验证异常
        with pytest.raises(httpx.HTTPStatusError):
            await test_class.test_method()

        # 验证结果
        assert test_class.call_count == 2  # 初始调用 + 1次重试
