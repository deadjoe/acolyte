"""
Gemini LLM客户端单元测试

测试GeminiClient类的功能和行为。
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.constants import PROVIDER_GEMINI
from acolyte.core.llm.providers.gemini import GeminiClient


class TestGeminiClient:
    """GeminiClient类的测试用例"""

    @pytest.fixture
    def llm_config(self):
        """创建测试用的LLM配置"""
        config = MagicMock(spec=LlmConfig)
        config.name = "Test Gemini"
        config.api_key = "test_api_key"
        config.base_url = "https://generativelanguage.googleapis.com"
        config.model_name = "gemini-pro"
        config.parameters = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
        return config

    @pytest.fixture
    def client(self, llm_config):
        """创建GeminiClient实例"""
        return GeminiClient(llm_config)

    def test_init(self, client, llm_config):
        """测试初始化"""
        assert client.name == llm_config.name
        assert client.api_key == llm_config.api_key
        assert client.base_url == llm_config.base_url
        assert client.provider == PROVIDER_GEMINI
        assert client.model_name == llm_config.model_name
        assert client.config == llm_config

    def test_full_model_name(self):
        """测试完整模型名称生成"""
        # 创建配置，模型名称不包含前缀
        config = MagicMock(spec=LlmConfig)
        config.name = "Test Gemini"
        config.model_name = "pro"
        config.api_key = "test_api_key"  # 添加api_key属性
        config.base_url = "https://generativelanguage.googleapis.com"  # 添加base_url属性

        # 创建客户端
        client = GeminiClient(config)

        # 验证完整模型名称已添加前缀
        assert client.full_model_name == "models/gemini-pro"

        # 测试已有前缀的情况
        config.model_name = "gemini-pro"
        client = GeminiClient(config)
        assert client.full_model_name == "models/gemini-pro"

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.gemini.GeminiClient._make_request")
    async def test_process_with_gemini_api(self, mock_make_request, client):
        """测试使用Gemini API处理内容"""
        # 准备测试数据
        system_prompt = "你是一个助手"
        user_prompt = "测试提示词"

        # 模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": """
                                ## 分析
                                这是一个测试分析。

                                ## 评分
                                偏见指数: 7.5
                                误导性指数: 6.2
                                隐藏意图指数: 4.8
                                可信度分数: 60.5
                                """
                            }
                        ]
                    },
                    "finishReason": "STOP",
                }
            ]
        }
        mock_make_request.return_value = mock_response

        # 调用方法
        result = await client._process_with_gemini_api(system_prompt, user_prompt)

        # 验证结果
        assert result is not None
        assert "success" in result
        assert result["success"] is True
        assert "raw_response" in result
        assert "result" in result

        # 验证请求参数
        mock_make_request.assert_called_once()
        call_args = mock_make_request.call_args[1]
        assert "json_data" in call_args
        json_data = call_args["json_data"]

        # 验证请求格式
        assert "contents" in json_data
        assert "generationConfig" in json_data
        assert "safetySettings" in json_data

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.gemini.GeminiClient._process_with_gemini_api")
    async def test_process_content_success(self, mock_process_with_gemini_api, client):
        """测试内容处理成功"""
        # 模拟成功响应
        mock_process_with_gemini_api.return_value = {
            "success": True,
            "content": """
            ## 分析
            这是一个测试分析。

            ## 评分
            偏见指数: 7.5
            误导性指数: 6.2
            隐藏意图指数: 4.8
            可信度分数: 60.5
            """,
        }

        # 调用方法
        result = await client.process_content("测试内容", "系统提示词")

        # 验证结果
        assert result is not None
        assert "success" in result
        assert result["success"] is True

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.gemini.GeminiClient._process_with_gemini_api")
    async def test_process_content_error(self, mock_process_with_gemini_api, client):
        """测试内容处理错误"""
        # 模拟错误响应
        mock_process_with_gemini_api.return_value = {"success": False, "error": "Invalid request"}

        # 调用方法
        result = await client.process_content("测试内容", "系统提示词")

        # 验证结果
        assert result is not None
        assert "success" in result
        assert result["success"] is False
        assert "error" in result
        assert "Invalid request" in result["error"]

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.gemini.GeminiClient._process_with_gemini_api")
    async def test_process_content_network_error(self, mock_process_with_gemini_api, client):
        """测试网络错误"""
        # 模拟网络错误
        mock_process_with_gemini_api.side_effect = httpx.ConnectError("Connection error")

        # 调用方法并验证异常
        with pytest.raises(Exception) as excinfo:
            await client.process_content("测试内容", "系统提示词")

        # 验证异常信息
        assert "Connection error" in str(excinfo.value)

    def test_prepare_prompt(self, client):
        """测试准备提示词"""
        # 准备测试数据
        content = "这是测试内容"
        prompt = "分析以下内容: {content}"

        # 调用方法
        result = client._prepare_prompt(content, prompt)

        # 验证结果
        assert result is not None
        assert content in result

        # 测试没有占位符的情况
        prompt_without_placeholder = "分析以下内容"
        result = client._prepare_prompt(content, prompt_without_placeholder)

        # 验证结果
        assert result is not None
        assert content in result
        assert prompt_without_placeholder in result

    def test_check_api_key(self, client):
        """测试API密钥检查"""
        # 测试有效的API密钥
        assert client._check_api_key() is True

        # 测试无效的API密钥
        client.api_key = ""
        assert client._check_api_key() is False

        # 测试短的API密钥
        client.api_key = "short"
        assert client._check_api_key() is True  # 仍然返回true，但会记录警告

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.gemini.GeminiClient._make_request")
    async def test_test_connection_success(self, mock_make_request, client):
        """测试连接测试成功"""
        # 模拟成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "gemini-pro"}]}
        mock_make_request.return_value = mock_response

        # 调用方法
        result = await client._test_connection()

        # 验证结果
        assert result["success"] is True

    @pytest.mark.asyncio
    @patch("acolyte.core.llm.providers.gemini.GeminiClient._make_request")
    async def test_test_connection_error(self, mock_make_request, client):
        """测试连接测试失败"""
        # 模拟错误响应
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        mock_make_request.return_value = mock_response

        # 调用方法
        result = await client._test_connection()

        # 验证结果
        assert result["success"] is False
