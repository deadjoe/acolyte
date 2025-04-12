"""
LLM客户端基类单元测试

测试LlmClient基类的功能和行为。
"""

import json
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
import httpx

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.base import LlmClient, retry_on_error
from acolyte.core.llm.constants import DEFAULT_TIMEOUT, MAX_RETRIES, RETRY_DELAY, RETRY_STATUS_CODES
from acolyte.core.llm.retry import RetryConfig


# 创建一个具体的LlmClient子类用于测试
class TestLlmClientImpl(LlmClient):
    """用于测试的LlmClient实现"""
    
    def __init__(self, llm_config):
        super().__init__(llm_config)
        self.provider = "test_provider"
    
    def _detect_provider(self):
        return "test_provider"
    
    def _prepare_request(self, prompt, system_prompt=None):
        return {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt or ""},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.parameters.get("temperature", 0.7)
        }
    
    def _process_response(self, response_data):
        if "choices" not in response_data:
            raise ValueError("Invalid response format")
        
        content = response_data["choices"][0]["message"]["content"]
        return {
            "content": content,
            "scores": self.response_parser.extract_scores(content)
        }
    
    def _parse_response(self, response_data):
        return self._process_response(response_data)


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
        assert client.parameters == llm_config.parameters
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
        
        # 验证默认参数
        assert client.parameters is not None
        assert isinstance(client.parameters, dict)
        assert "temperature" in client.parameters

    def test_get_headers(self, client):
        """测试获取请求头"""
        headers = client._get_headers()
        
        assert isinstance(headers, dict)
        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {client.api_key}"
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    @patch("httpx.AsyncClient.post")
    async def test_send_request_success(self, mock_post, client):
        """测试发送请求成功"""
        # 模拟成功响应
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
        mock_post.return_value = mock_response
        
        # 准备请求数据
        request_data = {
            "model": "test-model",
            "messages": [
                {"role": "system", "content": "系统提示词"},
                {"role": "user", "content": "用户提示词"}
            ]
        }
        
        # 调用方法
        response = await client._send_request("/chat/completions", request_data)
        
        # 验证结果
        assert response is not None
        assert "choices" in response
        assert len(response["choices"]) > 0
        assert "message" in response["choices"][0]
        assert "content" in response["choices"][0]["message"]

    @patch("httpx.AsyncClient.post")
    async def test_send_request_error(self, mock_post, client):
        """测试发送请求错误"""
        # 模拟错误响应
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid request"
            }
        }
        mock_post.return_value = mock_response
        
        # 准备请求数据
        request_data = {
            "model": "test-model",
            "messages": [
                {"role": "system", "content": "系统提示词"},
                {"role": "user", "content": "用户提示词"}
            ]
        }
        
        # 调用方法并验证异常
        with pytest.raises(Exception) as excinfo:
            await client._send_request("/chat/completions", request_data)
        
        # 验证异常信息
        assert "Invalid request" in str(excinfo.value)

    @patch("httpx.AsyncClient.post")
    async def test_process_content(self, mock_post, client):
        """测试内容处理"""
        # 模拟成功响应
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
        mock_post.return_value = mock_response
        
        # 调用方法
        result = await client.process_content("测试内容", "系统提示词")
        
        # 验证结果
        assert result is not None
        assert "content" in result
        assert "scores" in result
        assert result["scores"]["bias_index"] == 7.5
        assert result["scores"]["misleading_index"] == 6.2
        assert result["scores"]["hidden_intent_index"] == 4.8
        assert result["scores"]["credibility_score"] == 60.5

    @patch("httpx.AsyncClient.get")
    async def test_test_connection(self, mock_get, client):
        """测试连接测试"""
        # 模拟成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # 调用方法
        result = await client.test_connection()
        
        # 验证结果
        assert result is True
        
        # 模拟错误响应
        mock_response.status_code = 401
        result = await client.test_connection()
        
        # 验证结果
        assert result is False


class TestRetryDecorator:
    """retry_on_error装饰器的测试用例"""

    @pytest.fixture
    def retry_config(self):
        """创建重试配置"""
        return RetryConfig(
            max_retries=3,
            retry_delay=0.01,
            retry_status_codes=[429, 500, 502, 503, 504]
        )

    @pytest.fixture
    def test_class(self, retry_config):
        """创建测试类"""
        class TestClass:
            def __init__(self):
                self.retry_config = retry_config
                self.call_count = 0
            
            @retry_on_error
            async def test_method(self):
                self.call_count += 1
                if self.call_count < 3:
                    raise httpx.HTTPStatusError(
                        "Service unavailable",
                        request=MagicMock(),
                        response=MagicMock(status_code=503)
                    )
                return "success"
            
            @retry_on_error
            async def test_method_permanent_error(self):
                self.call_count += 1
                raise httpx.HTTPStatusError(
                    "Bad request",
                    request=MagicMock(),
                    response=MagicMock(status_code=400)
                )
            
            @retry_on_error
            async def test_method_network_error(self):
                self.call_count += 1
                if self.call_count < 3:
                    raise httpx.ConnectError("Connection error")
                return "success"
        
        return TestClass()

    async def test_retry_success(self, test_class):
        """测试重试成功"""
        # 重置计数器
        test_class.call_count = 0
        
        # 调用方法
        result = await test_class.test_method()
        
        # 验证结果
        assert result == "success"
        assert test_class.call_count == 3  # 前两次失败，第三次成功

    async def test_retry_permanent_error(self, test_class):
        """测试永久错误不重试"""
        # 重置计数器
        test_class.call_count = 0
        
        # 调用方法并验证异常
        with pytest.raises(httpx.HTTPStatusError):
            await test_class.test_method_permanent_error()
        
        # 验证结果
        assert test_class.call_count == 1  # 只调用一次，不重试

    async def test_retry_network_error(self, test_class):
        """测试网络错误重试"""
        # 重置计数器
        test_class.call_count = 0
        
        # 调用方法
        result = await test_class.test_method_network_error()
        
        # 验证结果
        assert result == "success"
        assert test_class.call_count == 3  # 前两次失败，第三次成功

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
