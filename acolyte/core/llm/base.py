"""
LLM客户端基类

定义LLM客户端的基础类和共享功能。
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

import httpx

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.constants import DEFAULT_TIMEOUT, MAX_RETRIES, RETRY_DELAY, RETRY_STATUS_CODES
from acolyte.core.llm.response import ResponseParser
from acolyte.core.llm.retry import ErrorHandler, RetryConfig, retry_on_error
from acolyte.utils.http import HttpClientManager
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class LlmClient(ABC):
    """
    LLM客户端基类

    这是所有LLM客户端的抽象基类，提供LLM调用的基础功能和共享方法。
    它定义了与LLM交互的标准接口，包括初始化、发送请求、处理响应等。

    主要功能：
    - 支持异步操作，使用asyncio进行非阻塞调用
    - 内置自动重试机制，处理临时错误和网络问题
    - 提供统一的错误处理和日志记录
    - 实现响应解析和结果格式化

    子类需要实现的抽象方法：
    - _detect_provider: 检测当前客户端的提供商
    - _prepare_request: 准备请求数据
    - _process_response: 处理响应数据
    - _parse_response: 解析响应数据
    """

    def __init__(self, llm_config: LlmConfig):
        """
        初始化LLM客户端

        该方法初始化LLM客户端的基本属性和组件，包括配置、API密钥、基础URL、模型名称等。
        它还初始化了响应解析器、错误处理器和重试配置等共享组件。

        初始化流程：
        1. 设置基本配置属性（名称、API密钥、URL、模型等）
        2. 检测或设置提供商信息
        3. 初始化超时、响应解析器、错误处理器等
        4. 设置重试配置

        Args:
            llm_config: LLM配置对象，包含名称、API密钥、基础URL、模型名称等信息
        """
        self.config = llm_config
        self.name = llm_config.name
        self.api_key = llm_config.api_key
        self.base_url = self._normalize_base_url(llm_config.base_url)
        self.model_name = llm_config.model_name

        # 设置提供商
        self.provider = getattr(llm_config, "provider", self._detect_provider())

        # 设置默认超时
        self.timeout = DEFAULT_TIMEOUT

        # 初始化响应解析器
        self.response_parser = ResponseParser()

        # 初始化错误处理器
        self.error_handler = ErrorHandler()

        # 初始化重试配置
        self.retry_config = RetryConfig(
            max_retries=MAX_RETRIES,
            initial_delay=RETRY_DELAY,
            retry_status_codes=RETRY_STATUS_CODES,
        )

        logger.debug(f"初始化{self.provider.capitalize()}客户端: 模型={self.model_name}")

    def _normalize_base_url(self, url: str) -> str:
        """
        标准化基础URL

        Args:
            url: 原始URL

        Returns:
            标准化后的URL
        """
        if not url:
            # 对于空URL，使用默认值
            from acolyte.core.llm.constants import DEFAULT_API_URLS

            url = DEFAULT_API_URLS.get(self.provider, "")
            if not url:
                logger.warning(f"未提供base_url且无法找到{self.provider}的默认URL")

        # 移除URL末尾的斜杠
        url = url.rstrip("/")

        # 检查并添加协议
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url

        return url

    def _detect_provider(self) -> str:
        """
        检测提供商

        基于name、base_url和model_name推断提供商。

        Returns:
            提供商名称
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

        # 基于LLM名称检测提供商
        llm_name_lower = self.name.lower() if self.name else ""
        if "deepseek" in llm_name_lower:
            return PROVIDER_DEEPSEEK
        elif "claude" in llm_name_lower or "anthropic" in llm_name_lower:
            return PROVIDER_ANTHROPIC
        elif "gpt" in llm_name_lower or "openai" in llm_name_lower:
            return PROVIDER_OPENAI
        elif "gemini" in llm_name_lower or "google" in llm_name_lower:
            return PROVIDER_GEMINI
        elif any(
            name in llm_name_lower
            for name in ["llama", "mistral", "mixtral", "vicuna", "phi", "yi", "ollama"]
        ):
            return PROVIDER_OLLAMA

        # 基于URL检测提供商
        base_url_lower = self.base_url.lower() if self.base_url else ""
        for provider, patterns in PROVIDER_URL_PATTERNS.items():
            if any(pattern in base_url_lower for pattern in patterns):
                return provider

        # 基于模型名称检测提供商
        model_name_lower = self.model_name.lower() if self.model_name else ""
        for provider, patterns in MODEL_NAME_PATTERNS.items():
            if any(pattern in model_name_lower for pattern in patterns):
                return provider

        # 默认使用OpenAI
        logger.warning(f"无法检测提供商，使用默认值: {PROVIDER_OPENAI}")
        return PROVIDER_OPENAI

    @abstractmethod
    async def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """
        处理内容

        Args:
            content: 要处理的内容
            prompt: 提示模板

        Returns:
            处理结果字典
        """
        pass

    def _prepare_prompt(self, content: str, prompt: str) -> str:
        """
        准备完整提示词

        将内容插入到提示模板中。

        Args:
            content: 要处理的内容
            prompt: 提示模板

        Returns:
            完整提示词
        """
        # 检查提示模板中是否有待替换的内容标记
        if "{content}" in prompt:
            # 替换内容标记
            return prompt.format(content=content)
        else:
            # 如果没有标记，简单拼接
            return f"{prompt}\n\n要分析的文章：\n\n{content}"

    def _check_api_key(self) -> bool:
        """
        检查API密钥是否有效

        Returns:
            API密钥是否有效
        """
        if not self.api_key:
            logger.error(f"{self.provider.capitalize()} API密钥未设置")
            return False

        # 简单格式校验
        if len(self.api_key) < 8 and self.provider != "ollama":  # Ollama不需要API密钥
            logger.warning(f"{self.provider.capitalize()} API密钥格式可能不正确")

        return True

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> httpx.Response:
        """
        发送异步请求

        Args:
            method: 请求方法（GET、POST等）
            endpoint: 接口路径
            headers: 请求头
            json_data: JSON数据
            params: 查询参数
            timeout: 超时设置（秒）

        Returns:
            HTTP响应对象

        Raises:
            httpx.HTTPError: 请求失败
        """
        if timeout is None:
            timeout = self.timeout

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # 记录请求信息（隐藏敏感信息）
        log_headers = None
        if headers:
            log_headers = {
                k: "***" if k.lower() in ["authorization", "x-api-key", "api-key"] else v
                for k, v in headers.items()
            }

        log_data = {"method": method, "url": url, "headers": log_headers, "timeout": timeout}

        if json_data:
            # 隐藏敏感信息
            if isinstance(json_data, dict):
                safe_json = json_data.copy()
                if "api_key" in safe_json:
                    safe_json["api_key"] = "***"
                if "messages" in safe_json and isinstance(safe_json["messages"], list):
                    # 记录消息数量和长度，而不是内容
                    log_data["messages_count"] = len(safe_json["messages"])
                    log_data["messages_total_length"] = sum(
                        len(str(m.get("content", ""))) for m in safe_json["messages"]
                    )
                else:
                    log_data["json"] = "包含敏感内容，已省略"

        logger.debug(f"发送{self.provider.capitalize()}请求: {log_data}")

        # 获取HTTP客户端
        client = HttpClientManager.get_client(self.provider)

        # 发送请求
        start_time = time.time()
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=timeout,
            )
            elapsed_time = time.time() - start_time

            # 记录响应信息
            logger.debug(
                f"{self.provider.capitalize()}响应: 状态码={response.status_code}, "
                f"耗时={elapsed_time:.2f}秒"
            )

            # 检查响应状态
            response.raise_for_status()

            return response

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(
                f"{self.provider.capitalize()}请求失败: {type(e).__name__}: {str(e)}, "
                f"耗时={elapsed_time:.2f}秒"
            )
            raise

    @retry_on_error()
    async def _test_connection(self) -> Dict[str, Union[bool, str]]:
        """
        实际测试连接

        子类应该实现此方法，提供特定于提供商的连接测试。

        Returns:
            测试结果字典
        """
        # 默认实现，子类应该覆盖
        logger.warning(f"{self.provider.capitalize()}未提供测试连接实现")
        return {"success": False, "message": f"{self.provider.capitalize()}未提供测试连接实现"}
