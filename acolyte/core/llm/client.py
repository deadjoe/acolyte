"""
LLM客户端实现
"""

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.base import LlmClient
from acolyte.utils.logging import get_logger

# 获取模块日志记录器
logger = get_logger(__name__)


def get_client_for_llm(llm_config: LlmConfig) -> LlmClient:
    """根据LLM配置获取对应的客户端

    该函数根据提供的LLM配置对象自动检测并返回适合的LLM客户端实例。
    检测过程按以下顺序进行：
    1. 首先基于LLM名称进行检测（如“Claude”、“GPT”等）
    2. 如果无法确定，则基于基础URL进行检测（如“api.anthropic.com”等）
    3. 如果仍无法确定，则基于模型名称进行检测（如“claude-3”、“gpt-4”等）
    4. 如果仍无法确定，则默认使用OpenAI客户端

    支持的LLM提供商：
    - Anthropic Claude
    - OpenAI GPT
    - Google Gemini
    - DeepSeek
    - Ollama（支持多种开源模型，如Llama、Mistral等）

    Args:
        llm_config: LLM配置对象，包含名称、基础URL、模型名称等信息

    Returns:
        LlmClient: 对应的LLM客户端实例，可用于发送请求和处理响应

    Note:
        如果无法确定客户端类型，将返回OpenAI客户端作为默认值，并记录警告日志。
        这可能导致在使用非OpenAI模型时出现兼容性问题。
    """
    from acolyte.core.llm.constants import (
        MODEL_NAME_PATTERNS,
        PROVIDER_ANTHROPIC,
        PROVIDER_DEEPSEEK,
        PROVIDER_GEMINI,
        PROVIDER_OLLAMA,
        PROVIDER_OPENAI,
        PROVIDER_URL_PATTERNS,
    )
    from acolyte.core.llm.providers.anthropic import AnthropicClient
    from acolyte.core.llm.providers.deepseek import DeepSeekClient
    from acolyte.core.llm.providers.gemini import GeminiClient
    from acolyte.core.llm.providers.ollama import OllamaClient
    from acolyte.core.llm.providers.openai import OpenAIClient

    # 使用模块级别的日志记录器
    logger.debug(
        f"为LLM创建客户端: 名称={llm_config.name}, URL={llm_config.base_url}, 模型={llm_config.model_name}"
    )

    # 基于LLM名称检测提供商
    llm_name = llm_config.name.lower() if llm_config.name else ""
    if "deepseek" in llm_name:
        return DeepSeekClient(llm_config)
    elif "claude" in llm_name or "anthropic" in llm_name:
        return AnthropicClient(llm_config)
    elif "gpt" in llm_name or "openai" in llm_name:
        return OpenAIClient(llm_config)
    elif "gemini" in llm_name or "google" in llm_name:
        return GeminiClient(llm_config)
    elif any(
        name in llm_name
        for name in ["llama", "mistral", "mixtral", "vicuna", "phi", "yi", "ollama"]
    ):
        return OllamaClient(llm_config)

    # 基于URL检测提供商
    base_url = llm_config.base_url.lower() if llm_config.base_url else ""
    for provider, patterns in PROVIDER_URL_PATTERNS.items():
        if any(pattern in base_url for pattern in patterns):
            if provider == PROVIDER_ANTHROPIC:
                return AnthropicClient(llm_config)
            elif provider == PROVIDER_OPENAI:
                return OpenAIClient(llm_config)
            elif provider == PROVIDER_GEMINI:
                return GeminiClient(llm_config)
            elif provider == PROVIDER_DEEPSEEK:
                return DeepSeekClient(llm_config)
            elif provider == PROVIDER_OLLAMA:
                return OllamaClient(llm_config)

    # 基于模型名称检测提供商
    model_name = llm_config.model_name.lower() if llm_config.model_name else ""
    for provider, patterns in MODEL_NAME_PATTERNS.items():
        if any(pattern in model_name for pattern in patterns):
            if provider == PROVIDER_ANTHROPIC:
                return AnthropicClient(llm_config)
            elif provider == PROVIDER_OPENAI:
                return OpenAIClient(llm_config)
            elif provider == PROVIDER_GEMINI:
                return GeminiClient(llm_config)
            elif provider == PROVIDER_DEEPSEEK:
                return DeepSeekClient(llm_config)
            elif provider == PROVIDER_OLLAMA:
                return OllamaClient(llm_config)

    # 如果无法确定，记录警告并默认使用OpenAI客户端
    logger.warning(f"无法确定LLM类型: {llm_config.name}, 使用默认的OpenAI客户端")
    return OpenAIClient(llm_config)
