"""
LLM管理模块

此模块提供LLM客户端的接口和实现，支持多种LLM提供商：
- Anthropic Claude
- OpenAI GPT
- Google Gemini
- DeepSeek
- Ollama
"""

from acolyte.core.llm.base import LlmClient
from acolyte.core.llm.client import get_client_for_llm
from acolyte.core.llm.constants import (
    PROVIDER_ANTHROPIC,
    PROVIDER_OPENAI,
    PROVIDER_GEMINI,
    PROVIDER_DEEPSEEK,
    PROVIDER_OLLAMA,
    DEFAULT_API_URLS,
)
from acolyte.core.llm.manager import LlmManager
from acolyte.core.llm.providers import (
    AnthropicClient,
    DeepSeekClient,
    GeminiClient,
    OllamaClient,
    OpenAIClient,
)
from acolyte.core.llm.response import ResponseParser, ErrorHandler

__all__ = [
    # 基础类
    "LlmClient",
    "ResponseParser",
    "ErrorHandler",

    # 客户端工厂
    "get_client_for_llm",

    # 提供商客户端
    "AnthropicClient",
    "OpenAIClient",
    "GeminiClient",
    "DeepSeekClient",
    "OllamaClient",

    # 管理器
    "LlmManager",

    # 常量
    "PROVIDER_ANTHROPIC",
    "PROVIDER_OPENAI",
    "PROVIDER_GEMINI",
    "PROVIDER_DEEPSEEK",
    "PROVIDER_OLLAMA",
    "DEFAULT_API_URLS",
]