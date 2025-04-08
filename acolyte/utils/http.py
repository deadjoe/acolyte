"""
HTTP客户端工具

提供HTTP客户端配置、连接池管理和请求工具。
"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx
from httpx import AsyncClient, Response

from acolyte.utils.logging import get_logger

logger = get_logger(__name__)


class HttpClientConfig:
    """HTTP客户端配置类"""

    def __init__(
        self,
        timeout: float = 60.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_backoff: float = 2.0,
        max_connections: int = 100,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
        http2: bool = False,
    ):
        """初始化HTTP客户端配置

        Args:
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 初始重试延迟（秒）
            retry_backoff: 重试退避因子
            max_connections: 最大连接数
            verify_ssl: 是否验证SSL证书
            follow_redirects: 是否自动跟随重定向
            http2: 是否启用HTTP/2
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_backoff = retry_backoff
        self.max_connections = max_connections
        self.verify_ssl = verify_ssl
        self.follow_redirects = follow_redirects
        self.http2 = http2


class HttpClientManager:
    """HTTP客户端管理器，提供客户端池管理"""

    # 类变量，用于存储客户端池
    _clients: Dict[str, AsyncClient] = {}
    _client_configs: Dict[str, HttpClientConfig] = {}

    @classmethod
    def get_client(
        cls, name: str = "default", config: Optional[HttpClientConfig] = None
    ) -> AsyncClient:
        """获取或创建HTTP客户端

        Args:
            name: 客户端名称
            config: 客户端配置，如果不提供则使用默认配置或已存在的配置

        Returns:
            异步HTTP客户端
        """
        # 如果客户端已存在，直接返回
        if name in cls._clients:
            client = cls._clients[name]
            # 如果客户端已关闭，重新创建
            if client.is_closed:
                logger.debug(f"HTTP客户端 {name} 已关闭，重新创建")
                client = cls._create_client(
                    name, config or cls._client_configs.get(name) or HttpClientConfig()
                )
                cls._clients[name] = client
            return client

        # 否则创建新客户端
        config = config or HttpClientConfig()
        client = cls._create_client(name, config)
        cls._clients[name] = client
        cls._client_configs[name] = config
        logger.debug(f"创建新的HTTP客户端: {name}")
        return client

    @classmethod
    def _create_client(cls, name: str, config: HttpClientConfig) -> AsyncClient:
        """创建HTTP客户端

        Args:
            name: 客户端名称
            config: 客户端配置

        Returns:
            异步HTTP客户端
        """
        limits = httpx.Limits(
            max_connections=config.max_connections,
            max_keepalive_connections=min(config.max_connections, 20),
        )

        timeout = httpx.Timeout(
            config.timeout,
            connect=min(config.timeout / 4, 10.0),
            read=config.timeout,
            write=config.timeout,
        )

        return AsyncClient(
            timeout=timeout,
            limits=limits,
            verify=config.verify_ssl,
            follow_redirects=config.follow_redirects,
            http2=config.http2,
        )

    @classmethod
    async def close_all(cls) -> None:
        """关闭所有HTTP客户端"""
        for name, client in cls._clients.items():
            if not client.is_closed:
                logger.debug(f"关闭HTTP客户端: {name}")
                await client.aclose()
        cls._clients.clear()

    @classmethod
    async def close_client(cls, name: str) -> None:
        """关闭指定的HTTP客户端

        Args:
            name: 客户端名称
        """
        if name in cls._clients:
            client = cls._clients[name]
            if not client.is_closed:
                logger.debug(f"关闭HTTP客户端: {name}")
                await client.aclose()
            del cls._clients[name]
            if name in cls._client_configs:
                del cls._client_configs[name]


async def fetch(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Any] = None,
    json_data: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
    client_name: str = "default",
    retry_codes: Optional[List[int]] = None,
    max_retries: Optional[int] = None,
) -> Response:
    """执行HTTP请求

    Args:
        url: 请求URL
        method: HTTP方法
        headers: 请求头
        params: URL参数
        data: 请求体数据
        json_data: JSON请求体数据
        timeout: 请求超时（秒）
        client_name: 客户端名称
        retry_codes: 需要重试的状态码
        max_retries: 最大重试次数

    Returns:
        HTTP响应
    """
    # 获取客户端
    client = HttpClientManager.get_client(client_name)

    # 设置默认的重试状态码
    retry_codes = retry_codes or [408, 425, 429, 500, 502, 503, 504]

    # 获取配置中的最大重试次数（如果没有指定）
    if max_retries is None and client_name in HttpClientManager._client_configs:
        max_retries = HttpClientManager._client_configs[client_name].max_retries
    else:
        max_retries = max_retries or 3

    # 执行请求，带重试机制
    attempt = 0
    last_error = None

    while attempt <= max_retries:
        try:
            # 执行请求
            response = await client.request(
                method,
                url,
                headers=headers,
                params=params,
                data=data,
                json=json_data,
                timeout=timeout,
            )

            # 如果状态码需要重试，且还有重试次数
            if response.status_code in retry_codes and attempt < max_retries:
                attempt += 1

                # 获取Retry-After头
                retry_after = response.headers.get("retry-after")
                if retry_after:
                    try:
                        retry_delay = float(retry_after)
                    except (ValueError, TypeError):
                        # 如果无法解析，使用默认延迟
                        retry_delay = 1.0 * (2 ** (attempt - 1))  # 指数退避
                else:
                    # 使用指数退避
                    retry_delay = 1.0 * (2 ** (attempt - 1))

                # 对于429（Too Many Requests），使用更长的延迟
                if response.status_code == 429:
                    retry_delay = max(retry_delay, 5.0 * attempt)

                logger.warning(
                    f"请求失败，状态码: {response.status_code}，将在 {retry_delay:.2f} 秒后"
                    f"进行第 {attempt}/{max_retries} 次重试"
                )

                # 等待延迟时间
                await asyncio.sleep(retry_delay)
                continue

            # 对于其他状态码，直接返回响应
            return response

        except (httpx.RequestError, httpx.TimeoutException) as e:
            # 记录错误
            last_error = e
            attempt += 1

            # 如果已达到最大重试次数，则抛出异常
            if attempt > max_retries:
                break

            # 计算退避延迟
            retry_delay = 1.0 * (2 ** (attempt - 1))

            logger.warning(
                f"请求异常: {type(e).__name__}: {str(e)}，将在 {retry_delay:.2f} 秒后"
                f"进行第 {attempt}/{max_retries} 次重试"
            )

            # 等待延迟时间
            await asyncio.sleep(retry_delay)

    # 如果所有重试都失败，抛出最后的异常
    if last_error:
        logger.error(
            f"请求在 {max_retries} 次重试后仍然失败: {type(last_error).__name__}: {str(last_error)}"
        )
        raise last_error

    # 这行理论上不会执行，但为了类型检查完整性
    raise httpx.RequestError("所有重试失败，但没有记录异常")
