"""
DeepSeek LLM客户端单元测试

测试DeepSeekClient类的功能和行为。
"""

from unittest.mock import MagicMock, patch

import pytest
import httpx

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.providers.deepseek import DeepSeekClient
from acolyte.core.llm.constants import PROVIDER_DEEPSEEK


class TestDeepSeekClient:
    """DeepSeekClient类的测试用例"""

    @pytest.fixture
    def llm_config(self):
        """创建测试用的LLM配置"""
        config = MagicMock(spec=LlmConfig)
        config.name = "Test DeepSeek"
        config.api_key = "test_api_key"
        config.base_url = "https://api.deepseek.com/v1"
        config.model_name = "deepseek-v3"
        return config

    @pytest.fixture
    def client(self, llm_config):
        """创建DeepSeekClient实例"""
        return DeepSeekClient(llm_config)

    def test_init(self, client, llm_config):
        """测试初始化"""
        assert client.name == llm_config.name
        assert client.api_key == llm_config.api_key
        assert client.base_url == llm_config.base_url
        assert client.provider == PROVIDER_DEEPSEEK
        assert client.model_name == llm_config.model_name

    @patch("acolyte.core.llm.base.LlmClient._normalize_base_url")
    def test_init_with_default_base_url(self, mock_normalize):
        """测试初始化时使用默认基础URL"""
        # 设置模拟函数返回值
        mock_normalize.return_value = "https://api.deepseek.com/v1"

        # 创建配置，不包含基础URL
        config = MagicMock(spec=LlmConfig)
        config.name = "Test DeepSeek"
        config.api_key = "test_api_key"
        config.base_url = ""
        config.model_name = "deepseek-v3"

        # 创建客户端
        client = DeepSeekClient(config)

        # 验证基础URL已设置为默认值
        assert client.base_url is not None
        assert mock_normalize.called
        assert client.provider == PROVIDER_DEEPSEEK

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.deepseek.DeepSeekClient._make_request")
    async def test_process_content_success(self, mock_make_request, client):
        """测试内容处理成功"""
        # 模拟成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test-id",
            "object": "chat.completion",
            "created": 1677858242,
            "model": "deepseek-v3",
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
                        """,
                    },
                    "finish_reason": "stop",
                    "index": 0,
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 100, "total_tokens": 110},
        }
        mock_make_request.return_value = mock_response

        # 模拟ResponseParser
        with patch(
            "acolyte.core.llm.response.ResponseParser.parse_deepseek_response"
        ) as mock_parser:
            mock_parser.return_value = {
                "content": "这是一个测试分析。",
                "scores": {
                    "bias_index": 7.5,
                    "misleading_index": 6.2,
                    "hidden_intent_index": 4.8,
                    "credibility_score": 60.5,
                },
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
    @patch("acolyte.core.llm.providers.deepseek.DeepSeekClient._make_request")
    async def test_process_content_error(self, mock_make_request, client):
        """测试内容处理错误"""
        # 模拟HTTP错误
        error = httpx.HTTPStatusError(
            "Bad request",
            request=MagicMock(),
            response=MagicMock(
                status_code=400,
                json=MagicMock(return_value={"error": {"message": "Invalid request"}}),
            ),
        )
        mock_make_request.side_effect = error

        # 调用方法
        result = await client.process_content("测试内容", "系统提示词")

        # 验证结果
        assert result is not None
        assert result["success"] is False
        assert "error" in result
        assert "Invalid request" in result["error"]

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.deepseek.DeepSeekClient._make_request")
    async def test_process_content_network_error(self, mock_make_request, client):
        """测试网络错误"""
        # 模拟网络错误
        error = httpx.ConnectError("Connection error")
        mock_make_request.side_effect = error

        # 调用方法
        result = await client.process_content("测试内容", "系统提示词")

        # 验证结果
        assert result is not None
        assert result["success"] is False
        assert "error" in result
        assert "Connection error" in result["error"]

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.deepseek.DeepSeekClient._make_request")
    async def test_test_connection_success(self, mock_make_request, client):
        """测试连接测试成功"""
        # 模拟成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test-id",
            "object": "chat.completion",
            "choices": [{"message": {"content": "Hello"}}],
            "usage": {"total_tokens": 10},
        }
        mock_make_request.return_value = mock_response

        # 调用方法
        result = await client._test_connection()

        # 验证结果
        assert result["success"] is True
        assert result["status"] == "success"
        assert "message" in result
        assert "model" in result
        assert "response_time" in result

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.deepseek.DeepSeekClient._make_request")
    async def test_test_connection_error(self, mock_make_request, client):
        """测试连接测试失败"""
        # 模拟HTTP错误
        error = httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=MagicMock(
                status_code=401,
                json=MagicMock(return_value={"error": {"message": "Invalid API key"}}),
            ),
        )
        mock_make_request.side_effect = error

        # 调用方法
        result = await client._test_connection()

        # 验证结果
        assert result["success"] is False
        assert result["status"] == "error"
        assert "message" in result
        assert "Invalid API key" in result["message"]

    def test_check_api_key_valid(self, client):
        """测试API密钥检查 - 有效"""
        # 客户端已经有API密钥
        assert client._check_api_key() is True

    def test_check_api_key_invalid(self):
        """测试API密钥检查 - 无效"""
        # 创建没有API密钥的配置
        config = MagicMock(spec=LlmConfig)
        config.name = "Test DeepSeek"
        config.api_key = None
        config.base_url = "https://api.deepseek.com/v1"
        config.model_name = "deepseek-v3"

        # 创建客户端
        client = DeepSeekClient(config)

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
