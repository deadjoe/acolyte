"""
OpenAI GPT LLM客户端单元测试

测试OpenAIClient类的功能和行为。
"""

from unittest.mock import MagicMock, patch

import pytest
import httpx

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.providers.openai import OpenAIClient
from acolyte.core.llm.constants import PROVIDER_OPENAI


class TestOpenAIClient:
    """OpenAIClient类的测试用例"""

    @pytest.fixture
    def llm_config(self):
        """创建测试用的LLM配置"""
        config = MagicMock(spec=LlmConfig)
        config.name = "Test GPT"
        config.api_key = "sk-test123"
        config.base_url = "https://api.openai.com/v1"
        config.model_name = "gpt-4"
        return config

    @pytest.fixture
    def client(self, llm_config):
        """创建OpenAIClient实例"""
        return OpenAIClient(llm_config)

    def test_init(self, client, llm_config):
        """测试初始化"""
        assert client.name == llm_config.name
        assert client.api_key == llm_config.api_key
        assert client.base_url == llm_config.base_url
        assert client.provider == PROVIDER_OPENAI
        assert client.model_name == llm_config.model_name
        assert client.is_azure is False

    def test_init_with_default_base_url(self):
        """测试初始化时使用默认基础URL"""
        # 创建配置，不包含基础URL
        config = MagicMock(spec=LlmConfig)
        config.name = "Test GPT"
        config.api_key = "sk-test123"
        config.base_url = ""
        config.model_name = "gpt-4"

        # 创建客户端
        with patch("acolyte.core.llm.base.LlmClient._normalize_base_url") as mock_normalize:
            mock_normalize.return_value = "https://api.openai.com/v1"
            client = OpenAIClient(config)

            # 验证基础URL已设置为默认值
            assert client.base_url is not None
            assert mock_normalize.called
            assert client.provider == PROVIDER_OPENAI
            assert client.is_azure is False

    def test_init_with_azure_openai(self, caplog):
        """测试初始化Azure OpenAI"""
        # 创建Azure OpenAI配置
        config = MagicMock(spec=LlmConfig)
        config.name = "Test Azure GPT"
        config.api_key = "apikey-test123"
        config.base_url = "https://example.openai.azure.com/openai/deployments/gpt4"
        config.model_name = "gpt-4"

        # 创建客户端
        client = OpenAIClient(config)

        # 验证Azure检测
        assert client.is_azure is True

    def test_init_with_invalid_azure_api_key(self, caplog):
        """测试初始化时Azure API密钥格式不正确"""
        # 创建配置，API密钥格式不正确
        config = MagicMock(spec=LlmConfig)
        config.name = "Test Azure GPT"
        config.api_key = "invalid-key"
        config.base_url = "https://example.openai.azure.com/openai/deployments/gpt4"
        config.model_name = "gpt-4"

        # 创建客户端
        client = OpenAIClient(config)

        # 验证警告日志
        assert "API密钥格式可能不正确" in caplog.text

    def test_check_api_key_valid(self, client):
        """测试API密钥检查 - 有效"""
        # 客户端已经有API密钥
        assert client._check_api_key() is True

    def test_check_api_key_invalid(self):
        """测试API密钥检查 - 无效"""
        # 创建没有API密钥的配置
        config = MagicMock(spec=LlmConfig)
        config.name = "Test GPT"
        config.api_key = None
        config.base_url = "https://api.openai.com/v1"
        config.model_name = "gpt-4"

        # 创建客户端
        client = OpenAIClient(config)

        # 验证API密钥检查失败
        assert client._check_api_key() is False

    def test_prepare_prompt(self, client):
        """测试提示词准备"""
        content = "这是测试内容"
        prompt = "这是提示词模板 {content}"

        # 调用方法
        result = client._prepare_prompt(content, prompt)

        # 验证结果
        assert content in result
        assert "这是提示词模板" in result

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.openai.OpenAIClient._make_request")
    async def test_process_content_success(self, mock_make_request, client):
        """测试内容处理成功"""
        # 模拟成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "chatcmpl-test123",
            "object": "chat.completion",
            "created": 1677858242,
            "model": "gpt-4",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": """
                        ## 分析
                        这是一个测试分析。

                        ## 评分
                        偏见指数: 7.5
                        误导性指数: 6.2
                        隐藏意图指数: 4.8
                        可信度分数: 60.5
                        """
                    },
                    "finish_reason": "stop",
                    "index": 0
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 100,
                "total_tokens": 110
            }
        }
        mock_make_request.return_value = mock_response

        # 模拟ResponseParser
        with patch("acolyte.core.llm.response.ResponseParser.parse_openai_response") as mock_parser:
            mock_parser.return_value = {
                "content": "这是一个测试分析。",
                "scores": {
                    "bias_index": 7.5,
                    "misleading_index": 6.2,
                    "hidden_intent_index": 4.8,
                    "credibility_score": 60.5
                }
            }

            # 调用方法
            result = await client.process_content("测试内容", "系统提示词")

            # 验证结果
            assert result is not None
            assert result["success"] is True
            assert "raw_response" in result
            assert "result" in result
            assert result["result"]["scores"]["bias_index"] == 7.5
            assert result["result"]["scores"]["misleading_index"] == 6.2
            assert result["result"]["scores"]["hidden_intent_index"] == 4.8
            assert result["result"]["scores"]["credibility_score"] == 60.5

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.openai.OpenAIClient._make_request")
    async def test_process_content_azure(self, mock_make_request):
        """测试Azure OpenAI内容处理"""
        # 创建Azure OpenAI配置
        config = MagicMock(spec=LlmConfig)
        config.name = "Test Azure GPT"
        config.api_key = "apikey-test123"
        config.base_url = "https://example.openai.azure.com/openai/deployments/gpt4"
        config.model_name = "gpt-4"

        # 创建客户端
        client = OpenAIClient(config)
        assert client.is_azure is True

        # 模拟成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "chatcmpl-test123",
            "object": "chat.completion",
            "created": 1677858242,
            "model": "gpt-4",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "这是一个测试分析。"
                    },
                    "finish_reason": "stop",
                    "index": 0
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 100,
                "total_tokens": 110
            }
        }
        mock_make_request.return_value = mock_response

        # 模拟ResponseParser
        with patch("acolyte.core.llm.response.ResponseParser.parse_openai_response") as mock_parser:
            mock_parser.return_value = {
                "content": "这是一个测试分析。",
                "scores": {
                    "bias_index": 7.5,
                    "misleading_index": 6.2,
                    "hidden_intent_index": 4.8,
                    "credibility_score": 60.5
                }
            }

            # 调用方法
            result = await client.process_content("测试内容", "系统提示词")

            # 验证结果
            assert result is not None
            assert result["success"] is True
            assert "raw_response" in result
            assert "result" in result

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.openai.OpenAIClient._make_request")
    async def test_process_content_error(self, mock_make_request, client):
        """测试内容处理错误"""
        # 模拟HTTP错误
        error = httpx.HTTPStatusError(
            "Bad request",
            request=MagicMock(),
            response=MagicMock(
                status_code=400,
                json=MagicMock(return_value={"error": {"message": "Invalid request"}})
            )
        )
        mock_make_request.side_effect = error

        # 模拟错误处理器
        with patch("acolyte.core.llm.retry.ErrorHandler") as mock_error_handler:
            mock_error_handler.handle_httpx_error.return_value = MagicMock(
                message="Invalid request",
                error_type="请求错误",
                should_retry=False,
                status_code=400
            )

            # 调用方法
            result = await client.process_content("测试内容", "系统提示词")

            # 验证结果
            assert result is not None
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.openai.OpenAIClient._make_request")
    async def test_process_content_network_error(self, mock_make_request, client):
        """测试网络错误"""
        # 模拟网络错误
        error = httpx.ConnectError("Connection error")
        mock_make_request.side_effect = error

        # 模拟错误处理器
        with patch("acolyte.core.llm.retry.ErrorHandler") as mock_error_handler:
            mock_error_handler.handle_request_error.return_value = MagicMock(
                message="无法连接到OpenAI API: Connection error",
                error_type="连接错误",
                should_retry=True,
                retry_after=5
            )

            # 调用方法
            result = await client.process_content("测试内容", "系统提示词")

            # 验证结果
            assert result is not None
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.openai.OpenAIClient._make_request")
    async def test_test_connection_success(self, mock_make_request, client):
        """测试连接测试成功"""
        # 模拟成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "gpt-4",
                    "object": "model",
                    "created": 1677610602,
                    "owned_by": "openai"
                },
                {
                    "id": "gpt-3.5-turbo",
                    "object": "model",
                    "created": 1677610602,
                    "owned_by": "openai"
                }
            ]
        }
        mock_make_request.return_value = mock_response

        # 调用方法
        result = await client._test_connection()

        # 验证结果
        assert result["success"] is True
        assert result["status"] == "success"
        assert "message" in result
        assert "models" in result

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.openai.OpenAIClient._make_request")
    async def test_test_connection_error(self, mock_make_request, client):
        """测试连接测试失败"""
        # 模拟HTTP错误
        error = httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=MagicMock(
                status_code=401,
                json=MagicMock(return_value={"error": {"message": "Invalid API key"}})
            )
        )
        mock_make_request.side_effect = error

        # 模拟错误处理器
        with patch("acolyte.core.llm.retry.ErrorHandler") as mock_error_handler:
            mock_error_handler.handle_httpx_error.return_value = MagicMock(
                message="OpenAI API认证失败: Invalid API key",
                error_type="认证错误",
                should_retry=False,
                status_code=401
            )

            # 调用方法
            result = await client._test_connection()

            # 验证结果
            assert result["success"] is False
            assert result["status"] == "error"
            assert "message" in result
