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

    Args:
        llm_config: LLM配置对象

    Returns:
        对应的LLM客户端实例
    """
    from acolyte.core.llm.providers.anthropic import AnthropicClient
    from acolyte.core.llm.providers.openai import OpenAIClient
    from acolyte.core.llm.providers.gemini import GeminiClient
    from acolyte.core.llm.providers.deepseek import DeepSeekClient
    from acolyte.core.llm.providers.ollama import OllamaClient

    # 使用模块级别的日志记录器
    logger.debug(f"为LLM创建客户端: 名称={llm_config.name}, URL={llm_config.base_url}, 模型={llm_config.model_name}")

    # 根据base_url或其他参数判断LLM类型
    base_url = llm_config.base_url.lower() if llm_config.base_url else ""

    # 检查LLM名称是否包含"deepseek"（不区分大小写）
    llm_name = llm_config.name.lower() if llm_config.name else ""
    if "deepseek" in llm_name:
        return DeepSeekClient(llm_config)

    # 根据base_url判断
    if "anthropic" in base_url:
        return AnthropicClient(llm_config)
    elif "openai" in base_url or "azure" in base_url:
        return OpenAIClient(llm_config)
    elif "googleapis" in base_url or "google" in base_url:
        return GeminiClient(llm_config)
    elif "deepseek" in base_url:
        return DeepSeekClient(llm_config)
    elif "ollama" in base_url or "localhost:11434" in base_url:
        return OllamaClient(llm_config)
    else:
        # 尝试基于模型名称进行判断
        model_name = llm_config.model_name.lower() if llm_config.model_name else ""
        if any(name in model_name for name in ["claude", "anthropic"]):
            return AnthropicClient(llm_config)
        elif any(name in model_name for name in ["gpt", "davinci", "openai"]):
            return OpenAIClient(llm_config)
        elif any(name in model_name for name in ["gemini", "google"]):
            return GeminiClient(llm_config)
        elif any(name in model_name for name in ["deepseek"]):
            return DeepSeekClient(llm_config)
        elif any(name in model_name for name in ["llama", "mistral", "mixtral", "vicuna", "phi", "yi"]):
            return OllamaClient(llm_config)
        else:
            # 如果无法确定，记录警告并默认使用OpenAI客户端
            logger.warning(f"无法确定LLM类型: {llm_config.name}, 使用默认的OpenAI客户端")
            return OpenAIClient(llm_config)