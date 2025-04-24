"""
Ollama LLM客户端单元测试

测试OllamaClient类的功能和行为。
"""

from unittest.mock import MagicMock, patch

import pytest
import httpx

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.providers.ollama import OllamaClient
from acolyte.core.llm.constants import PROVIDER_OLLAMA


class TestOllamaClient:
    """OllamaClient类的测试用例"""

    @pytest.fixture
    def llm_config(self):
        """创建测试用的LLM配置"""
        config = MagicMock(spec=LlmConfig)
        config.name = "Test Ollama"
        config.api_key = None  # Ollama通常不需要API密钥
        config.base_url = "http://localhost:11434"
        config.model_name = "llama2"
        return config

    @pytest.fixture
    def client(self, llm_config):
        """创建OllamaClient实例"""
        return OllamaClient(llm_config)

    def test_init(self, client, llm_config):
        """测试初始化"""
        assert client.name == llm_config.name
        assert client.api_key is None
        assert client.base_url == llm_config.base_url
        assert client.provider == PROVIDER_OLLAMA
        assert client.model_name == llm_config.model_name
        assert client.timeout > 0  # 确保超时设置合理

    def test_init_with_default_base_url(self):
        """测试初始化时使用默认基础URL"""
        # 创建配置，不包含基础URL
        config = MagicMock(spec=LlmConfig)
        config.name = "Test Ollama"
        config.api_key = None
        config.base_url = ""
        config.model_name = "llama2"

        # 创建客户端
        client = OllamaClient(config)

        # 验证基础URL已设置为默认值
        assert client.base_url == "http://localhost:11434"

    def test_check_api_key(self, client):
        """测试API密钥检查 - Ollama不需要API密钥"""
        assert client._check_api_key() is True

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.ollama.OllamaClient._make_request")
    async def test_process_content_success(self, mock_make_request, client):
        """测试内容处理成功"""
        # 模拟成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "llama2",
            "response": """
            ## 分析
            这是一个测试分析。

            ## 评分
            偏见指数: 7.5
            误导性指数: 6.2
            隐藏意图指数: 4.8
            可信度分数: 60.5
            """,
            "done": True,
        }
        mock_make_request.return_value = mock_response

        # 模拟ResponseParser
        with patch("acolyte.core.llm.response.ResponseParser.parse_ollama_response") as mock_parser:
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
    @patch("acolyte.core.llm.providers.ollama.OllamaClient._make_request")
    async def test_process_content_invalid_response(self, mock_make_request, client):
        """测试处理无效响应"""
        # 模拟无效响应（缺少response字段）
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"model": "llama2", "done": True}
        mock_make_request.return_value = mock_response

        # 调用方法
        result = await client.process_content("测试内容", "系统提示词")

        # 验证结果
        assert result is not None
        assert result["success"] is False
        assert "error" in result
        assert "Ollama API响应格式无效" in result["error"]

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.ollama.OllamaClient._make_request")
    async def test_process_content_http_error(self, mock_make_request, client):
        """测试HTTP错误"""
        # 模拟HTTP错误
        error = httpx.HTTPStatusError(
            "Bad request", request=MagicMock(), response=MagicMock(status_code=400)
        )
        mock_make_request.side_effect = error

        # 模拟错误处理器
        with patch("acolyte.core.llm.providers.ollama.ErrorHandler") as mock_error_handler:
            mock_error_handler.handle_request_error.return_value = {
                "success": False,
                "error": "Bad request",
            }

            # 调用方法
            result = await client.process_content("测试内容", "系统提示词")

            # 验证结果
            assert result is not None
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.ollama.OllamaClient._make_request")
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
        assert "Ollama API网络错误" in result["error"]

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.ollama.OllamaClient._make_request")
    async def test_test_connection_success_with_model(self, mock_make_request, client):
        """测试连接测试成功 - 找到模型"""
        # 模拟成功响应，包含模型
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "llama2"}, {"name": "mistral"}]}
        mock_make_request.return_value = mock_response

        # 调用方法
        result = await client._test_connection()

        # 验证结果
        assert result["success"] is True
        assert result["status"] == "success"
        assert "message" in result
        assert client.model_name in result["message"]

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.ollama.OllamaClient._make_request")
    async def test_test_connection_success_without_model(self, mock_make_request, client):
        """测试连接测试成功 - 未找到模型"""
        # 模拟成功响应，但不包含所需模型
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "mistral"}, {"name": "phi2"}]}
        mock_make_request.return_value = mock_response

        # 调用方法
        result = await client._test_connection()

        # 验证结果
        assert result["success"] is False
        assert result["status"] == "warning"
        assert "message" in result
        assert client.model_name in result["message"]
        assert "mistral" in result["message"]

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.ollama.OllamaClient._make_request")
    async def test_test_connection_http_error(self, mock_make_request, client):
        """测试连接测试HTTP错误"""
        # 模拟HTTP错误
        error = httpx.HTTPStatusError(
            "Not found",
            request=MagicMock(url="http://localhost:11434/api/tags"),
            response=MagicMock(status_code=404),
        )
        mock_make_request.side_effect = error

        # 调用方法
        result = await client._test_connection()

        # 验证结果
        assert result["success"] is False
        assert result["status"] == "error"
        assert "message" in result
        assert "HTTP错误" in result["message"]
        assert "404" in result["message"]

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.ollama.OllamaClient._make_request")
    async def test_test_connection_exception(self, mock_make_request, client):
        """测试连接测试异常"""
        # 模拟一般异常
        error = Exception("General error")
        mock_make_request.side_effect = error

        # 调用方法
        result = await client._test_connection()

        # 验证结果
        assert result["success"] is False
        assert result["status"] == "error"
        assert "message" in result
        assert "General error" in result["message"]
