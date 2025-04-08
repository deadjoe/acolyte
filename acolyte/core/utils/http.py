"""
HTTP工具

提供HTTP请求相关的工具函数和类，简化HTTP操作。
"""

import asyncio
import json
import time
from typing import Any, Dict, Optional

import httpx
from httpx import Response

from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class HttpClient:
    """
    HTTP客户端

    提供HTTP请求功能，支持重试、超时和错误处理。
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        初始化HTTP客户端

        Args:
            base_url: 基础URL
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟时间（秒）
            headers: 请求头
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.headers = headers or {}

        # 创建客户端
        self.client = httpx.Client(base_url=base_url, timeout=timeout, headers=self.headers)

        # 创建异步客户端
        self.async_client = httpx.AsyncClient(
            base_url=base_url, timeout=timeout, headers=self.headers
        )

    def close(self):
        """关闭客户端"""
        self.client.close()

    async def aclose(self):
        """关闭异步客户端"""
        await self.async_client.aclose()

    def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[Any] = None,
        retry_on_status: Optional[list] = None,
    ) -> Response:
        """
        发送HTTP请求

        Args:
            method: 请求方法（GET、POST等）
            url: 请求URL
            params: 查询参数
            data: 请求体数据
            json_data: JSON数据
            headers: 请求头
            auth: 认证信息
            retry_on_status: 重试的状态码列表

        Returns:
            HTTP响应
        """
        if retry_on_status is None:
            retry_on_status = [429, 500, 502, 503, 504]

        # 合并请求头
        request_headers = {**self.headers}
        if headers:
            request_headers.update(headers)

        # 记录请求信息
        log_url = f"{self.base_url or ''}{url}"
        logger.debug(f"HTTP请求: {method} {log_url}")

        # 重试逻辑
        retry_count = 0
        last_exception = None

        while retry_count <= self.max_retries:
            try:
                start_time = time.time()

                response = self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json_data,
                    headers=request_headers,
                    auth=auth,
                )

                elapsed_time = time.time() - start_time
                logger.debug(
                    f"HTTP响应: {method} {log_url} - 状态码: {response.status_code}, "
                    f"耗时: {elapsed_time:.2f}秒"
                )

                # 检查是否需要重试
                if response.status_code in retry_on_status and retry_count < self.max_retries:
                    retry_count += 1
                    wait_time = self.retry_delay * (2 ** (retry_count - 1))  # 指数退避

                    logger.warning(
                        f"HTTP请求重试 ({retry_count}/{self.max_retries}): {method} {log_url} - "
                        f"状态码: {response.status_code}, 等待时间: {wait_time:.2f}秒"
                    )

                    time.sleep(wait_time)
                    continue

                return response

            except (httpx.HTTPError, httpx.TimeoutException) as e:
                elapsed_time = time.time() - start_time
                last_exception = e

                if retry_count < self.max_retries:
                    retry_count += 1
                    wait_time = self.retry_delay * (2 ** (retry_count - 1))  # 指数退避

                    logger.warning(
                        f"HTTP请求异常重试 ({retry_count}/{self.max_retries}): "
                        f"{method} {log_url} - "
                        f"错误: {str(e)}, 等待时间: {wait_time:.2f}秒, 耗时: {elapsed_time:.2f}秒"
                    )

                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"HTTP请求失败: {method} {log_url} - "
                        f"错误: {str(e)}, 耗时: {elapsed_time:.2f}秒",
                        exc_info=True,
                    )
                    raise

        # 如果所有重试都失败
        if last_exception:
            raise last_exception

        # 这里不应该到达，但为了类型检查
        raise httpx.HTTPError("所有HTTP请求重试都失败")

    async def arequest(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[Any] = None,
        retry_on_status: Optional[list] = None,
    ) -> Response:
        """
        发送异步HTTP请求

        Args:
            method: 请求方法（GET、POST等）
            url: 请求URL
            params: 查询参数
            data: 请求体数据
            json_data: JSON数据
            headers: 请求头
            auth: 认证信息
            retry_on_status: 重试的状态码列表

        Returns:
            HTTP响应
        """
        if retry_on_status is None:
            retry_on_status = [429, 500, 502, 503, 504]

        # 合并请求头
        request_headers = {**self.headers}
        if headers:
            request_headers.update(headers)

        # 记录请求信息
        log_url = f"{self.base_url or ''}{url}"
        logger.debug(f"异步HTTP请求: {method} {log_url}")

        # 重试逻辑
        retry_count = 0
        last_exception = None

        while retry_count <= self.max_retries:
            try:
                start_time = time.time()

                response = await self.async_client.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json_data,
                    headers=request_headers,
                    auth=auth,
                )

                elapsed_time = time.time() - start_time
                logger.debug(
                    f"异步HTTP响应: {method} {log_url} - "
                    f"状态码: {response.status_code}, 耗时: {elapsed_time:.2f}秒"
                )

                # 检查是否需要重试
                if response.status_code in retry_on_status and retry_count < self.max_retries:
                    retry_count += 1
                    wait_time = self.retry_delay * (2 ** (retry_count - 1))  # 指数退避

                    logger.warning(
                        f"异步HTTP请求重试 ({retry_count}/{self.max_retries}): "
                        f"{method} {log_url} - "
                        f"状态码: {response.status_code}, 等待时间: {wait_time:.2f}秒"
                    )

                    await asyncio.sleep(wait_time)
                    continue

                return response

            except (httpx.HTTPError, httpx.TimeoutException) as e:
                elapsed_time = time.time() - start_time
                last_exception = e

                if retry_count < self.max_retries:
                    retry_count += 1
                    wait_time = self.retry_delay * (2 ** (retry_count - 1))  # 指数退避

                    logger.warning(
                        f"异步HTTP请求异常重试 ({retry_count}/{self.max_retries}): "
                        f"{method} {log_url} - "
                        f"错误: {str(e)}, 等待时间: {wait_time:.2f}秒, 耗时: {elapsed_time:.2f}秒"
                    )

                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"异步HTTP请求失败: {method} {log_url} - "
                        f"错误: {str(e)}, 耗时: {elapsed_time:.2f}秒",
                        exc_info=True,
                    )
                    raise

        # 如果所有重试都失败
        if last_exception:
            raise last_exception

        # 这里不应该到达，但为了类型检查
        raise httpx.HTTPError("所有异步HTTP请求重试都失败")

    def get(self, url: str, **kwargs) -> Response:
        """
        发送GET请求

        Args:
            url: 请求URL
            kwargs: 其他参数

        Returns:
            HTTP响应
        """
        return self.request("GET", url, **kwargs)

    async def aget(self, url: str, **kwargs) -> Response:
        """
        发送异步GET请求

        Args:
            url: 请求URL
            kwargs: 其他参数

        Returns:
            HTTP响应
        """
        return await self.arequest("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> Response:
        """
        发送POST请求

        Args:
            url: 请求URL
            kwargs: 其他参数

        Returns:
            HTTP响应
        """
        return self.request("POST", url, **kwargs)

    async def apost(self, url: str, **kwargs) -> Response:
        """
        发送异步POST请求

        Args:
            url: 请求URL
            kwargs: 其他参数

        Returns:
            HTTP响应
        """
        return await self.arequest("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> Response:
        """
        发送PUT请求

        Args:
            url: 请求URL
            kwargs: 其他参数

        Returns:
            HTTP响应
        """
        return self.request("PUT", url, **kwargs)

    async def aput(self, url: str, **kwargs) -> Response:
        """
        发送异步PUT请求

        Args:
            url: 请求URL
            kwargs: 其他参数

        Returns:
            HTTP响应
        """
        return await self.arequest("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> Response:
        """
        发送DELETE请求

        Args:
            url: 请求URL
            kwargs: 其他参数

        Returns:
            HTTP响应
        """
        return self.request("DELETE", url, **kwargs)

    async def adelete(self, url: str, **kwargs) -> Response:
        """
        发送异步DELETE请求

        Args:
            url: 请求URL
            kwargs: 其他参数

        Returns:
            HTTP响应
        """
        return await self.arequest("DELETE", url, **kwargs)


def parse_json_response(response: Response, default: Optional[Dict] = None) -> Dict:
    """
    解析JSON响应

    Args:
        response: HTTP响应
        default: 默认值

    Returns:
        解析后的JSON数据
    """
    if default is None:
        default = {}

    try:
        # 检查响应是否有内容
        if not response.content:
            logger.warning("HTTP响应无内容")
            return default

        # 尝试解析JSON
        return response.json()
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {str(e)}, 响应内容: {response.text[:200]}...", exc_info=True)
        return default
    except Exception as e:
        logger.error(f"响应处理失败: {str(e)}", exc_info=True)
        return default


def handle_http_error(response: Response, error_msg: str = "HTTP请求失败") -> Dict:
    """
    处理HTTP错误

    Args:
        response: HTTP响应
        error_msg: 错误消息

    Returns:
        错误信息字典
    """
    # 尝试从响应中提取错误信息
    error_detail = error_msg
    try:
        error_data = response.json()
        if isinstance(error_data, dict):
            if "error" in error_data:
                error_detail = error_data["error"]
            elif "message" in error_data:
                error_detail = error_data["message"]
    except Exception:
        error_detail = response.text[:200] if response.text else error_msg

    # 记录错误
    logger.error(
        f"{error_msg}: 状态码={response.status_code}, URL={response.url}, 错误详情={error_detail}"
    )

    # 构建错误响应
    return {"success": False, "error": error_detail, "status_code": response.status_code}
