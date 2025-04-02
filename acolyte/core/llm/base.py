"""
LLM客户端基类

定义LLM客户端的基础类和共享功能。
"""
import json
import time
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

import requests
from requests.exceptions import RequestException

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.constants import (DEFAULT_TIMEOUT, MAX_RETRIES,
                                       RETRY_DELAY, RETRY_STATUS_CODES)
from acolyte.core.llm.response import ErrorHandler, ResponseParser
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


def retry_on_error(max_retries: int = MAX_RETRIES, retry_delay: float = RETRY_DELAY):
    """
    错误重试装饰器
    
    对请求方法进行装饰，在失败时自动重试。
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            provider = getattr(self, 'provider', 'unknown')
            
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)
                except requests.HTTPError as e:
                    last_error = e
                    status_code = e.response.status_code if e.response else 0
                    
                    # 检查是否应该重试
                    if attempt < max_retries and ErrorHandler.should_retry(provider, status_code):
                        wait_time = retry_delay * (2 ** attempt)  # 指数退避
                        logger.warning(
                            f"调用{provider} API失败 (HTTP {status_code}), 尝试重试 "
                            f"({attempt+1}/{max_retries})，等待{wait_time:.1f}秒"
                        )
                        time.sleep(wait_time)
                    else:
                        # 处理错误
                        return ErrorHandler.handle_request_error(provider, e)
                except (RequestException, json.JSONDecodeError) as e:
                    last_error = e
                    
                    if attempt < max_retries:
                        wait_time = retry_delay * (2 ** attempt)  # 指数退避
                        logger.warning(
                            f"调用{provider} API失败: {str(e)}, 尝试重试 "
                            f"({attempt+1}/{max_retries})，等待{wait_time:.1f}秒"
                        )
                        time.sleep(wait_time)
                    else:
                        # 处理错误
                        return ErrorHandler.handle_request_error(provider, e)
            
            # 如果所有重试都失败
            if last_error:
                return ErrorHandler.handle_request_error(provider, last_error)
            
            # 这里不应该到达，但为了类型检查
            return {
                "success": False,
                "error": f"调用{provider} API失败，所有重试都失败"
            }
            
        return wrapper
    return decorator


class LlmClient(ABC):
    """
    LLM客户端基类
    
    提供LLM调用的基础功能和共享方法。
    """
    
    def __init__(self, llm_config: LlmConfig):
        """
        初始化LLM客户端
        
        Args:
            llm_config: LLM配置对象
        """
        self.config = llm_config
        self.name = llm_config.name
        self.api_key = llm_config.api_key
        self.base_url = self._normalize_base_url(llm_config.base_url)
        self.model_name = llm_config.model_name
        
        # 设置提供商
        self.provider = getattr(llm_config, 'provider', self._detect_provider())
        
        logger.debug(f"初始化{self.provider.capitalize()}客户端: 模型={self.model_name}")
    
    def _normalize_base_url(self, url: str) -> str:
        """
        标准化基础URL
        
        Args:
            url: 原始URL
            
        Returns:
            标准化后的URL
        """
        # 移除URL末尾的斜杠
        url = url.rstrip('/')
        
        # 检查并添加协议
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        return url
    
    def _detect_provider(self) -> str:
        """
        检测提供商
        
        基于base_url和model_name推断提供商。
        
        Returns:
            提供商名称
        """
        from acolyte.core.llm.constants import (MODEL_NAME_PATTERNS,
                                               PROVIDER_ANTHROPIC,
                                               PROVIDER_GEMINI, PROVIDER_OLLAMA,
                                               PROVIDER_OPENAI,
                                               PROVIDER_URL_PATTERNS)
        
        # 基于URL检测提供商
        base_url_lower = self.base_url.lower()
        for provider, patterns in PROVIDER_URL_PATTERNS.items():
            if any(pattern in base_url_lower for pattern in patterns):
                return provider
                
        # 基于模型名称检测提供商
        model_name_lower = self.model_name.lower()
        for provider, patterns in MODEL_NAME_PATTERNS.items():
            if any(pattern in model_name_lower for pattern in patterns):
                return provider
        
        # 默认使用OpenAI
        logger.warning(f"无法检测提供商，使用默认值: {PROVIDER_OPENAI}")
        return PROVIDER_OPENAI
    
    @abstractmethod
    def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
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
            return f"{prompt}\n\n```\n{content}\n```"
    
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
        if len(self.api_key) < 8:
            logger.warning(f"{self.provider.capitalize()} API密钥格式可能不正确")
            
        return True
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> requests.Response:
        """
        发送请求
        
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
            requests.RequestException: 请求失败
        """
        if timeout is None:
            timeout = DEFAULT_TIMEOUT
            
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # 记录请求信息
        log_data = {
            "method": method,
            "url": url,
            "headers": {k: "..." if k.lower() in ["authorization", "api-key"] else v for k, v in (headers or {}).items()},
            "timeout": timeout
        }
        if json_data:
            # 隐藏敏感信息
            if isinstance(json_data, dict):
                safe_json = json_data.copy()
                if "api_key" in safe_json:
                    safe_json["api_key"] = "..."
                log_data["json"] = safe_json
                
        logger.debug(f"发送{self.provider.capitalize()}请求: {json.dumps(log_data)}")
        
        # 发送请求
        start_time = time.time()
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json_data,
            params=params,
            timeout=timeout
        )
        elapsed_time = time.time() - start_time
        
        # 记录响应信息
        logger.debug(f"{self.provider.capitalize()}响应: 状态码={response.status_code}, 耗时={elapsed_time:.2f}秒")
        
        # 检查响应状态
        response.raise_for_status()
        
        return response
    
    def test_connection(self) -> Dict[str, Union[bool, str]]:
        """
        测试连接
        
        测试与LLM提供商的连接是否正常。
        
        Returns:
            测试结果字典
        """
        try:
            logger.info(f"测试{self.provider.capitalize()}连接")
            
            if not self._check_api_key():
                return {
                    "success": False,
                    "status": "error",
                    "message": f"{self.provider.capitalize()} API密钥未设置"
                }
                
            # 需要子类实现具体的测试方法
            return self._test_connection()
            
        except Exception as e:
            logger.error(f"测试{self.provider.capitalize()}连接失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "status": "error",
                "message": f"连接测试失败: {str(e)}"
            }
    
    def _test_connection(self) -> Dict[str, Union[bool, str]]:
        """
        实际测试连接
        
        子类应该实现此方法，提供特定于提供商的连接测试。
        
        Returns:
            测试结果字典
        """
        # 默认实现，子类应该覆盖
        logger.warning(f"{self.provider.capitalize()}未提供测试连接实现")
        return {
            "success": False,
            "status": "error",
            "message": f"{self.provider.capitalize()}未提供测试连接实现"
        }