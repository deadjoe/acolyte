"""
LLM客户端工厂函数单元测试

测试get_client_for_llm函数的功能和行为。
"""

from unittest.mock import MagicMock, patch

import pytest

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.client import get_client_for_llm
from acolyte.core.llm.constants import (
    PROVIDER_ANTHROPIC,
    PROVIDER_DEEPSEEK,
    PROVIDER_GEMINI,
    PROVIDER_OLLAMA,
    PROVIDER_OPENAI,
)


class TestGetClientForLlm:
    """get_client_for_llm函数的测试用例"""

    @pytest.fixture
    def llm_config(self):
        """创建基本的LLM配置"""
        config = MagicMock(spec=LlmConfig)
        config.name = "Test LLM"
        config.api_key = "test_api_key"
        config.base_url = "https://api.test.com"
        config.model_name = "test-model"
        return config

    @patch("acolyte.core.llm.providers.anthropic.AnthropicClient")
    def test_detect_anthropic_by_name(self, mock_anthropic_client, llm_config):
        """测试通过名称检测Anthropic"""
        # 设置名称
        llm_config.name = "Claude"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_anthropic_client.called
        mock_anthropic_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.openai.OpenAIClient")
    def test_detect_openai_by_name(self, mock_openai_client, llm_config):
        """测试通过名称检测OpenAI"""
        # 设置名称
        llm_config.name = "GPT-4"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_openai_client.called
        mock_openai_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.gemini.GeminiClient")
    def test_detect_gemini_by_name(self, mock_gemini_client, llm_config):
        """测试通过名称检测Gemini"""
        # 设置名称
        llm_config.name = "Gemini"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_gemini_client.called
        mock_gemini_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.deepseek.DeepSeekClient")
    def test_detect_deepseek_by_name(self, mock_deepseek_client, llm_config):
        """测试通过名称检测DeepSeek"""
        # 设置名称
        llm_config.name = "DeepSeek"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_deepseek_client.called
        mock_deepseek_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.ollama.OllamaClient")
    def test_detect_ollama_by_name(self, mock_ollama_client, llm_config):
        """测试通过名称检测Ollama"""
        # 设置名称
        llm_config.name = "Ollama"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_ollama_client.called
        mock_ollama_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.anthropic.AnthropicClient")
    def test_detect_anthropic_by_url(self, mock_anthropic_client, llm_config):
        """测试通过URL检测Anthropic"""
        # 设置URL
        llm_config.name = "Generic LLM"
        llm_config.base_url = "https://api.anthropic.com"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_anthropic_client.called
        mock_anthropic_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.openai.OpenAIClient")
    def test_detect_openai_by_url(self, mock_openai_client, llm_config):
        """测试通过URL检测OpenAI"""
        # 设置URL
        llm_config.name = "Generic LLM"
        llm_config.base_url = "https://api.openai.com"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_openai_client.called
        mock_openai_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.gemini.GeminiClient")
    def test_detect_gemini_by_url(self, mock_gemini_client, llm_config):
        """测试通过URL检测Gemini"""
        # 设置URL
        llm_config.name = "Generic LLM"
        llm_config.base_url = "https://generativelanguage.googleapis.com"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_gemini_client.called
        mock_gemini_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.deepseek.DeepSeekClient")
    def test_detect_deepseek_by_url(self, mock_deepseek_client, llm_config):
        """测试通过URL检测DeepSeek"""
        # 设置URL
        llm_config.name = "Generic LLM"
        llm_config.base_url = "https://api.deepseek.ai"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_deepseek_client.called
        mock_deepseek_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.ollama.OllamaClient")
    def test_detect_ollama_by_url(self, mock_ollama_client, llm_config):
        """测试通过URL检测Ollama"""
        # 设置URL
        llm_config.name = "Generic LLM"
        llm_config.base_url = "http://localhost:11434/ollama"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_ollama_client.called
        mock_ollama_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.anthropic.AnthropicClient")
    def test_detect_anthropic_by_model(self, mock_anthropic_client, llm_config):
        """测试通过模型名称检测Anthropic"""
        # 设置模型名称
        llm_config.name = "Generic LLM"
        llm_config.base_url = "https://api.generic.com"
        llm_config.model_name = "claude-3-opus"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_anthropic_client.called
        mock_anthropic_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.openai.OpenAIClient")
    def test_detect_openai_by_model(self, mock_openai_client, llm_config):
        """测试通过模型名称检测OpenAI"""
        # 设置模型名称
        llm_config.name = "Generic LLM"
        llm_config.base_url = "https://api.generic.com"
        llm_config.model_name = "gpt-4"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_openai_client.called
        mock_openai_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.gemini.GeminiClient")
    def test_detect_gemini_by_model(self, mock_gemini_client, llm_config):
        """测试通过模型名称检测Gemini"""
        # 设置模型名称
        llm_config.name = "Generic LLM"
        llm_config.base_url = "https://api.generic.com"
        llm_config.model_name = "gemini-pro"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_gemini_client.called
        mock_gemini_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.deepseek.DeepSeekClient")
    def test_detect_deepseek_by_model(self, mock_deepseek_client, llm_config):
        """测试通过模型名称检测DeepSeek"""
        # 设置模型名称
        llm_config.name = "Generic LLM"
        llm_config.base_url = "https://api.generic.com"
        llm_config.model_name = "deepseek-v3"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_deepseek_client.called
        mock_deepseek_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.ollama.OllamaClient")
    def test_detect_ollama_by_model(self, mock_ollama_client, llm_config):
        """测试通过模型名称检测Ollama"""
        # 设置模型名称
        llm_config.name = "Generic LLM"
        llm_config.base_url = "https://api.generic.com"
        llm_config.model_name = "llama2"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_ollama_client.called
        mock_ollama_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.providers.openai.OpenAIClient")
    def test_default_to_openai(self, mock_openai_client, llm_config):
        """测试默认使用OpenAI"""
        # 设置通用名称和URL
        llm_config.name = "Generic LLM"
        llm_config.base_url = "https://api.generic.com"
        llm_config.model_name = "generic-model"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_openai_client.called
        mock_openai_client.assert_called_once_with(llm_config)

    @patch("acolyte.core.llm.client.logger")
    @patch("acolyte.core.llm.providers.openai.OpenAIClient")
    def test_default_logs_warning(self, mock_openai_client, mock_logger, llm_config):
        """测试默认使用OpenAI时记录警告"""
        # 设置通用名称和URL
        llm_config.name = "Generic LLM"
        llm_config.base_url = "https://api.generic.com"
        llm_config.model_name = "generic-model"

        # 调用函数
        client = get_client_for_llm(llm_config)

        # 验证结果
        assert mock_logger.warning.called
