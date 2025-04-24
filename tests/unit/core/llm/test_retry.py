"""
LLM重试机制单元测试

测试ErrorHandler和RetryConfig类的功能和行为。
"""

from unittest.mock import MagicMock

import pytest
import httpx
import asyncio
import json

from acolyte.core.llm.retry import ErrorHandler, RetryConfig, calculate_delay


class TestRetryConfig:
    """RetryConfig类的测试用例"""

    def test_init_with_defaults(self):
        """测试使用默认值初始化"""
        config = RetryConfig()

        assert config.max_retries > 0
        assert config.initial_delay > 0
        assert len(config.retry_status_codes) > 0
        assert 429 in config.retry_status_codes  # 应该包含常见的重试状态码

    def test_init_with_custom_values(self):
        """测试使用自定义值初始化"""
        config = RetryConfig(max_retries=5, initial_delay=0.5, retry_status_codes=[500, 502])

        assert config.max_retries == 5
        assert config.initial_delay == 0.5
        assert config.retry_status_codes == [500, 502]

    def test_retry_exceptions(self):
        """测试重试异常列表"""
        config = RetryConfig()

        # 验证默认重试异常
        assert httpx.TimeoutException in config.retry_exceptions
        assert httpx.ConnectError in config.retry_exceptions
        assert asyncio.TimeoutError in config.retry_exceptions

    def test_calculate_delay(self):
        """测试计算重试延迟"""
        config = RetryConfig(
            initial_delay=1.0,
            backoff_factor=2.0,
            max_delay=10.0,
            jitter=False,  # 关闭抖动以便于测试
        )

        # 第一次重试 (attempt=0)
        delay = calculate_delay(0, config)
        assert delay == 1.0

        # 第二次重试 (attempt=1)
        delay = calculate_delay(1, config)
        assert delay == 2.0

        # 第三次重试 (attempt=2)
        delay = calculate_delay(2, config)
        assert delay == 4.0

        # 第四次重试 (attempt=3)，但受到max_delay限制
        delay = calculate_delay(3, config)
        assert delay == 8.0

        # 第五次重试 (attempt=4)，超过max_delay
        delay = calculate_delay(4, config)
        assert delay == 10.0  # 被限制为max_delay


class TestErrorHandler:
    """ErrorHandler类的测试用例"""

    @pytest.fixture
    def handler(self):
        """创建ErrorHandler实例"""
        return ErrorHandler()

    def test_handle_httpx_error(self):
        """测试处理HTTP状态错误"""
        # 创建HTTP错误
        response = MagicMock()
        response.status_code = 429
        response.json.return_value = {
            "error": {"message": "Too many requests", "type": "rate_limit_error"}
        }
        response.headers = {"retry-after": "30"}
        response.text = '{"error": {"message": "Too many requests", "type": "rate_limit_error"}}'

        request = MagicMock()
        request.url = "https://api.example.com/v1/chat/completions"
        request.method = "POST"

        error = httpx.HTTPStatusError("Too many requests", request=request, response=response)

        # 处理错误
        error_info = ErrorHandler.handle_httpx_error(error, provider="openai")

        # 验证结果
        assert error_info.error_type == "速率限制"
        assert "Too many requests" in error_info.message
        assert error_info.status_code == 429
        assert error_info.should_retry is True
        assert error_info.retry_after == 30

    def test_handle_request_error_connect_error(self):
        """测试处理连接错误"""
        # 创建连接错误
        error = httpx.ConnectError("Failed to establish a connection")

        # 处理错误
        error_info = ErrorHandler.handle_request_error(error, provider="anthropic")

        # 验证结果
        assert error_info.error_type == "连接错误"
        assert "无法连接到anthropic API" in error_info.message
        assert error_info.should_retry is True
        assert error_info.retry_after == 5

    def test_handle_request_error_timeout(self):
        """测试处理超时错误"""
        # 创建超时错误
        error = httpx.TimeoutException("Request timed out")

        # 处理错误
        error_info = ErrorHandler.handle_request_error(error, provider="gemini")

        # 验证结果
        assert error_info.error_type == "超时错误"
        assert "gemini API请求超时" in error_info.message
        assert error_info.should_retry is True
        assert error_info.retry_after == 10

    def test_handle_request_error_json_decode(self):
        """测试处理JSON解析错误"""
        # 创建JSON解析错误
        error = json.JSONDecodeError(
            "Expecting property name enclosed in double quotes", "{invalid", 1
        )

        # 处理错误
        error_info = ErrorHandler.handle_request_error(error, provider="deepseek")

        # 验证结果
        assert error_info.error_type == "未知错误"
        assert "deepseek API请求失败" in error_info.message
        assert error_info.should_retry is False

    def test_error_info_to_dict(self):
        """测试ErrorInfo转换为字典"""
        # 创建HTTP错误
        response = MagicMock()
        response.status_code = 429
        response.json.return_value = {"error": {"message": "Rate limit exceeded"}}
        response.headers = {}
        response.text = '{"error": {"message": "Rate limit exceeded"}}'

        error = httpx.HTTPStatusError("Rate limit exceeded", request=MagicMock(), response=response)

        # 处理错误
        error_info = ErrorHandler.handle_httpx_error(error, provider="openai")

        # 转换为字典
        error_dict = error_info.to_dict()

        # 验证结果
        assert isinstance(error_dict, dict)
        assert error_dict["error_type"] == "速率限制"
        assert "Rate limit exceeded" in error_dict["message"]
        assert error_dict["status_code"] == 429
        assert error_dict["should_retry"] is True

    def test_error_info_str(self):
        """测试ErrorInfo字符串表示"""
        # 创建HTTP错误
        response = MagicMock()
        response.status_code = 401
        response.json.return_value = {"error": {"message": "Invalid API key"}}
        response.headers = {}
        response.text = '{"error": {"message": "Invalid API key"}}'

        error = httpx.HTTPStatusError("Invalid API key", request=MagicMock(), response=response)

        # 处理错误
        error_info = ErrorHandler.handle_httpx_error(error, provider="openai")

        # 获取字符串表示
        error_str = str(error_info)

        # 验证结果
        assert "认证错误" in error_str
        assert "Invalid API key" in error_str
        assert "Status: 401" in error_str
