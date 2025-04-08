"""
重试机制和错误处理框架

提供用于LLM API请求的重试策略、退避算法和错误处理。
"""

import asyncio
import functools
import json
import random
import time
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, cast

import httpx

from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)

# 类型变量，用于装饰器返回类型注解
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


class RetryConfig:
    """重试配置类，包含重试策略参数"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retry_status_codes: List[int] = None,
        retry_exceptions: List[Type[Exception]] = None,
    ):
        """初始化重试配置

        Args:
            max_retries: 最大重试次数
            initial_delay: 初始延迟（秒）
            max_delay: 最大延迟（秒）
            backoff_factor: 退避因子（每次重试延迟增加的倍数）
            jitter: 是否添加随机抖动
            retry_status_codes: 需要重试的HTTP状态码列表
            retry_exceptions: 需要重试的异常类型列表
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

        # 默认重试状态码
        self.retry_status_codes = retry_status_codes or [
            408,  # 请求超时
            429,  # 速率限制
            500,  # 服务器内部错误
            502,  # 网关错误
            503,  # 服务不可用
            504,  # 网关超时
        ]

        # 默认重试异常
        self.retry_exceptions = retry_exceptions or [
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            httpx.ReadError,
            httpx.RemoteProtocolError,
            asyncio.TimeoutError,
        ]


class ErrorInfo:
    """错误信息类，包含标准化错误信息"""

    def __init__(
        self,
        error_type: str,
        message: str,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        should_retry: bool = False,
        original_exception: Optional[Exception] = None,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """初始化错误信息

        Args:
            error_type: 错误类型
            message: 错误消息
            code: 错误代码
            status_code: HTTP状态码（如适用）
            should_retry: 是否应该重试
            original_exception: 原始异常
            retry_after: 建议的重试延迟（秒）
            details: 附加的错误详情
        """
        self.error_type = error_type
        self.message = message
        self.code = code
        self.status_code = status_code
        self.should_retry = should_retry
        self.original_exception = original_exception
        self.retry_after = retry_after
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            错误信息字典
        """
        return {
            "error_type": self.error_type,
            "message": self.message,
            "code": self.code,
            "status_code": self.status_code,
            "should_retry": self.should_retry,
            "retry_after": self.retry_after,
            **self.details,
        }

    def __str__(self) -> str:
        """错误信息字符串表示

        Returns:
            格式化的错误消息
        """
        parts = [f"{self.error_type}: {self.message}"]
        if self.code:
            parts.append(f"Code: {self.code}")
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.should_retry:
            retry_info = "可重试"
            if self.retry_after:
                retry_info += f", 建议{self.retry_after}秒后重试"
            parts.append(retry_info)
        return " | ".join(parts)


class ErrorHandler:
    """错误处理类，用于处理和分类错误"""

    @staticmethod
    def handle_httpx_error(error: httpx.HTTPStatusError, provider: str = "unknown") -> ErrorInfo:
        """处理HTTPX HTTP状态错误

        Args:
            error: HTTPX HTTP状态错误
            provider: LLM提供商名称

        Returns:
            标准化的错误信息
        """
        response = error.response
        status_code = response.status_code

        # 尝试解析响应JSON
        error_json = {}
        try:
            error_json = response.json()
        except Exception:
            pass

        # 从响应中提取错误消息
        error_message = str(error)
        error_code = None
        retry_after = None
        should_retry = status_code in [408, 429, 500, 502, 503, 504]
        error_type = "API错误"

        # 提取提供商特定的错误信息
        if provider == "anthropic":
            error_type = error_json.get("type", "API错误")
            error_message = error_json.get("message", error_message)
            error_code = error_json.get("error_type") or error_json.get("code")
            # Anthropic特定header
            retry_after = response.headers.get("retry-after")
        elif provider == "openai":
            error_type = error_json.get("error", {}).get("type", "API错误")
            error_message = error_json.get("error", {}).get("message", error_message)
            error_code = error_json.get("error", {}).get("code")
            # OpenAI特定header
            retry_after = response.headers.get("retry-after") or response.headers.get(
                "x-ratelimit-reset-tokens"
            )
        elif provider == "gemini":
            error_message = error_json.get("error", {}).get("message", error_message)
            error_code = error_json.get("error", {}).get("code") or error_json.get("error", {}).get(
                "status"
            )
        elif provider == "deepseek":
            error_type = error_json.get("error", {}).get("type", "API错误")
            error_message = error_json.get("error", {}).get("message", error_message)
            error_code = error_json.get("error", {}).get("code")
        elif provider == "ollama":
            error_message = error_json.get("error", error_message)

        # 处理特定状态码
        if status_code == 401:
            error_type = "认证错误"
            error_message = f"{provider} API认证失败: {error_message}"
        elif status_code == 403:
            error_type = "权限错误"
            error_message = f"{provider} API权限不足: {error_message}"
        elif status_code == 404:
            error_type = "资源不存在"
            error_message = f"{provider} API资源不存在: {error_message}"
        elif status_code == 429:
            error_type = "速率限制"
            error_message = f"{provider} API请求次数过多: {error_message}"
            if not retry_after and "retry after" in error_message.lower():
                # 尝试从错误消息中提取retry-after
                try:
                    import re

                    match = re.search(r"retry after (\d+)", error_message.lower())
                    if match:
                        retry_after = int(match.group(1))
                except Exception:
                    pass

        # 如果没有解析到retry_after但应该重试，设置默认值
        if should_retry and not retry_after:
            if status_code == 429:
                retry_after = 60  # 对于速率限制默认60秒
            else:
                retry_after = 5  # 对于其他错误默认5秒

        # 如果retry_after是字符串，转换为整数
        if isinstance(retry_after, str):
            try:
                retry_after = int(retry_after)
            except ValueError:
                retry_after = 30  # 默认30秒

        return ErrorInfo(
            error_type=error_type,
            message=error_message,
            code=error_code,
            status_code=status_code,
            should_retry=should_retry,
            original_exception=error,
            retry_after=retry_after,
            details={
                "provider": provider,
                "response_headers": dict(response.headers),
                "response_text": response.text,
                "request_url": str(response.request.url),
                "request_method": response.request.method,
            },
        )

    @staticmethod
    def handle_request_error(error: Exception, provider: str = "unknown") -> ErrorInfo:
        """处理通用请求错误

        Args:
            error: 异常对象
            provider: LLM提供商名称

        Returns:
            标准化的错误信息
        """
        # 处理HTTP状态错误
        if isinstance(error, httpx.HTTPStatusError):
            return ErrorHandler.handle_httpx_error(error, provider)

        # 处理连接错误
        if isinstance(error, httpx.ConnectError):
            return ErrorInfo(
                error_type="连接错误",
                message=f"无法连接到{provider} API: {str(error)}",
                should_retry=True,
                original_exception=error,
                retry_after=5,
                details={"provider": provider},
            )

        # 处理超时错误
        if isinstance(error, (httpx.TimeoutException, asyncio.TimeoutError)):
            return ErrorInfo(
                error_type="超时错误",
                message=f"{provider} API请求超时: {str(error)}",
                should_retry=True,
                original_exception=error,
                retry_after=10,
                details={"provider": provider},
            )

        # 处理JSON解析错误
        if isinstance(error, (json.JSONDecodeError, ValueError)) and "json" in str(error).lower():
            return ErrorInfo(
                error_type="解析错误",
                message=f"无法解析{provider} API响应: {str(error)}",
                should_retry=False,
                original_exception=error,
                details={"provider": provider},
            )

        # 通用错误
        return ErrorInfo(
            error_type="未知错误",
            message=f"{provider} API请求失败: {str(error)}",
            should_retry=False,
            original_exception=error,
            details={"provider": provider},
        )


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """计算重试延迟时间

    Args:
        attempt: 当前重试次数 (0-based)
        config: 重试配置

    Returns:
        延迟时间（秒）
    """
    # 计算基本延迟（指数退避）
    delay = config.initial_delay * (config.backoff_factor**attempt)

    # 限制为最大延迟
    delay = min(delay, config.max_delay)

    # 添加随机抖动
    if config.jitter:
        jitter_factor = random.uniform(0.8, 1.2)
        delay *= jitter_factor

    return delay


def retry_on_error(config: Optional[RetryConfig] = None) -> Callable[[F], F]:
    """重试装饰器，用于函数调用失败后自动重试

    Args:
        config: 重试配置，如果不提供则使用默认配置

    Returns:
        装饰后的函数
    """
    # 使用默认配置
    if config is None:
        config = RetryConfig()

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # 获取函数名称和调用信息
            func_name = func.__qualname__

            # 重试逻辑
            last_error = None
            attempt = 0

            while attempt <= config.max_retries:
                try:
                    # 执行函数
                    result = await func(*args, **kwargs)

                    # 如果这是一个重试成功，记录日志
                    if attempt > 0:
                        logger.info(f"函数 {func_name} 在第 {attempt} 次重试后成功执行")

                    return result

                except Exception as e:
                    last_error = e
                    attempt += 1

                    # 检查是否是需要重试的异常
                    should_retry = False
                    retry_after = None

                    # 处理HTTP状态错误
                    if isinstance(e, httpx.HTTPStatusError):
                        status_code = e.response.status_code
                        should_retry = status_code in config.retry_status_codes
                        # 检查X-RateLimit-Reset-Tokens或Retry-After头
                        retry_after = e.response.headers.get("retry-after")
                        if retry_after:
                            try:
                                retry_after = int(retry_after)
                            except ValueError:
                                retry_after = None
                    # 处理其他异常
                    else:
                        should_retry = any(
                            isinstance(e, exc_type) for exc_type in config.retry_exceptions
                        )

                    # 如果不应该重试或已达到最大重试次数，则抛出异常
                    if not should_retry or attempt > config.max_retries:
                        logger.warning(
                            f"函数 {func_name} 失败，不再重试: {type(e).__name__}: {str(e)}"
                        )
                        raise

                    # 计算延迟时间
                    if retry_after:
                        delay = float(retry_after)
                    else:
                        delay = calculate_delay(attempt - 1, config)

                    logger.info(
                        f"函数 {func_name} 调用失败，将在 {delay:.2f} 秒后进行第 {attempt}/{config.max_retries} 次重试: "
                        f"{type(e).__name__}: {str(e)}"
                    )

                    # 等待延迟时间
                    await asyncio.sleep(delay)

            # 如果执行到这里，表示所有重试都失败了
            logger.error(
                f"函数 {func_name} 在 {config.max_retries} 次重试后仍然失败: "
                f"{type(last_error).__name__}: {str(last_error)}"
            )
            raise last_error

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # 获取函数名称和调用信息
            func_name = func.__qualname__

            # 重试逻辑
            last_error = None
            attempt = 0

            while attempt <= config.max_retries:
                try:
                    # 执行函数
                    result = func(*args, **kwargs)

                    # 如果这是一个重试成功，记录日志
                    if attempt > 0:
                        logger.info(f"函数 {func_name} 在第 {attempt} 次重试后成功执行")

                    return result

                except Exception as e:
                    last_error = e
                    attempt += 1

                    # 检查是否是需要重试的异常
                    should_retry = False
                    retry_after = None

                    # 处理HTTP状态错误
                    if isinstance(e, httpx.HTTPStatusError):
                        status_code = e.response.status_code
                        should_retry = status_code in config.retry_status_codes
                        # 检查X-RateLimit-Reset-Tokens或Retry-After头
                        retry_after = e.response.headers.get("retry-after")
                        if retry_after:
                            try:
                                retry_after = int(retry_after)
                            except ValueError:
                                retry_after = None
                    # 处理其他异常
                    else:
                        should_retry = any(
                            isinstance(e, exc_type) for exc_type in config.retry_exceptions
                        )

                    # 如果不应该重试或已达到最大重试次数，则抛出异常
                    if not should_retry or attempt > config.max_retries:
                        logger.warning(
                            f"函数 {func_name} 失败，不再重试: {type(e).__name__}: {str(e)}"
                        )
                        raise

                    # 计算延迟时间
                    if retry_after:
                        delay = float(retry_after)
                    else:
                        delay = calculate_delay(attempt - 1, config)

                    logger.info(
                        f"函数 {func_name} 调用失败，将在 {delay:.2f} 秒后进行第 {attempt}/{config.max_retries} 次重试: "
                        f"{type(e).__name__}: {str(e)}"
                    )

                    # 等待延迟时间
                    time.sleep(delay)

            # 如果执行到这里，表示所有重试都失败了
            logger.error(
                f"函数 {func_name} 在 {config.max_retries} 次重试后仍然失败: "
                f"{type(last_error).__name__}: {str(last_error)}"
            )
            raise last_error

        # 根据函数是同步还是异步选择适当的包装器
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)

    return decorator
