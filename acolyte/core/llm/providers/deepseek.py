"""
DeepSeek LLM Client implementation for Acolyte.
"""

import json
import time
from typing import Any, Dict, List, Optional, Union

import httpx

from ...db.models import LlmConfig
from ..base import LlmClient
from ..constants import (DEFAULT_TIMEOUT, PROVIDER_DEEPSEEK,
                         RETRY_STATUS_CODES)
from ..response import ResponseParser, ErrorHandler
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class DeepSeekClient(LlmClient):
    """
    Client for DeepSeek API, which is compatible with OpenAI API.
    """

    def __init__(self, llm_config: LlmConfig):
        super().__init__(llm_config)
        self.provider = PROVIDER_DEEPSEEK
        self.base_url = self._normalize_base_url(self.base_url)
        self.timeout = DEFAULT_TIMEOUT
        self.response_parser = ResponseParser()
        self.error_handler = ErrorHandler()
        logger.debug(f"初始化DeepSeek客户端: 模型={self.model_name}, URL={self.base_url}")

    def _check_api_key(self) -> bool:
        """Check if API key is set."""
        return bool(self.api_key)

    async def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """
        Process content with DeepSeek API.
        
        Args:
            content: The content to be analyzed
            prompt: The prompt template to use
            
        Returns:
            Dict with response data or error information
        """
        logger.info(f"使用DeepSeek处理内容: 模型={self.model_name}, 内容长度={len(content)}字符")
        start_time = time.time()
        
        if not self._check_api_key():
            logger.error("DeepSeek API密钥未设置")
            return {"success": False, "error": "API密钥未设置"}
        
        try:
            # Prepare prompt
            system_prompt = "You are a content analyst specializing in detecting bias, misleading information, and hidden intent."
            user_prompt = self._prepare_prompt(content, prompt)
            
            # Call API
            response = await self._process_with_api(system_prompt, user_prompt)
            
            # 记录处理时间和结果
            elapsed_time = time.time() - start_time
            if response.get("success", False):
                scores = response.get("scores", {})
                logger.info(
                    f"DeepSeek处理成功: 耗时={elapsed_time:.2f}秒, "
                    f"BI={scores.get('bias_index')}, "
                    f"MI={scores.get('misleading_index')}, "
                    f"HI={scores.get('hidden_intent_index')}, "
                    f"CS={scores.get('credibility_score')}"
                )
            else:
                logger.error(f"DeepSeek处理失败: 耗时={elapsed_time:.2f}秒, 错误={response.get('error')}")
                
            return response
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"DeepSeek处理内容异常: {str(e)}"
            logger.error(f"{error_msg}, 耗时={elapsed_time:.2f}秒", exc_info=True)
            return {"success": False, "error": error_msg}

    async def _process_with_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Make a request to the DeepSeek API.
        
        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt
            
        Returns:
            Dict with response data or error information
        """
        start_time = time.time()
        try:
            # Prepare API URL
            api_url = f"{self.base_url}/chat/completions"
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Prepare data
            data = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,  # Low temperature for analytical tasks
                "max_tokens": 4096
            }
            
            logger.debug(f"DeepSeek请求: URL={api_url}, 消息数={len(data['messages'])}")
            
            # Make the request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=data
                )
                
                # 记录请求时间
                request_time = time.time() - start_time
                logger.debug(f"DeepSeek请求完成: 状态码={response.status_code}, 耗时={request_time:.2f}秒")
                
                # Check for HTTP errors
                response.raise_for_status()
                
                # Parse response
                response_json = response.json()
                
                # Extract the response text
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    response_text = response_json["choices"][0]["message"]["content"]
                    
                    # Parse scores and structured content
                    scores = self.response_parser.extract_scores(response_text)
                    structured_content = self.response_parser.extract_structured_content(response_text)
                    
                    # 记录响应解析
                    parse_time = time.time() - start_time - request_time
                    logger.debug(f"DeepSeek响应解析完成: 解析耗时={parse_time:.2f}秒, 总耗时={(time.time()-start_time):.2f}秒")
                    
                    return {
                        "success": True,
                        "response": response_text,
                        "scores": scores,
                        "structured_content": structured_content,
                        "raw_response": response_json
                    }
                else:
                    logger.warning(f"DeepSeek响应格式无效: {response_json}")
                    return {
                        "success": False,
                        "error": "DeepSeek API响应格式无效",
                        "raw_response": response_json
                    }
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek HTTP错误: 状态码={e.response.status_code}, URL={e.request.url}, 耗时={(time.time()-start_time):.2f}秒")
            return self.error_handler.handle_request_error(e, "DeepSeek")
            
        except httpx.RequestError as e:
            error_msg = f"DeepSeek API网络错误: {str(e)}"
            logger.error(f"{error_msg}, 耗时={(time.time()-start_time):.2f}秒", exc_info=True)
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = f"DeepSeek API未知错误: {str(e)}"
            logger.error(f"{error_msg}, 耗时={(time.time()-start_time):.2f}秒", exc_info=True)
            return {"success": False, "error": error_msg}

    async def _test_connection(self) -> Dict[str, Union[bool, str]]:
        """
        Test connection to DeepSeek API.
        
        Returns:
            Dict with success status and message
        """
        logger.info(f"测试DeepSeek连接: 模型={self.model_name}, URL={self.base_url}")
        start_time = time.time()
        
        if not self._check_api_key():
            logger.error("DeepSeek API密钥未设置")
            return {"success": False, "message": "API密钥未设置"}
        
        try:
            # Use a minimal prompt to test connection
            system_prompt = "You are a helpful assistant."
            user_prompt = "Hello, this is a connection test. Please respond with 'Connection successful'."
            
            # Make a test request with minimal tokens
            data = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 20,
                "temperature": 0.1
            }
            
            # Prepare API URL and headers
            api_url = f"{self.base_url}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            logger.debug(f"DeepSeek连接测试请求: URL={api_url}")
            
            # Make the request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=data
                )
                
                # Check response status
                response.raise_for_status()
                
                # Record success
                elapsed_time = time.time() - start_time
                logger.info(f"DeepSeek连接测试成功: 状态码={response.status_code}, 耗时={elapsed_time:.2f}秒")
                
                # If we get here, the connection is successful
                return {
                    "success": True, 
                    "message": "成功连接到DeepSeek API",
                    "status": "success"
                }
                
        except httpx.HTTPStatusError as e:
            elapsed_time = time.time() - start_time
            error_details = self.error_handler.format_error_message(e, "DeepSeek")
            logger.error(f"DeepSeek连接测试HTTP错误: 状态码={e.response.status_code}, 耗时={elapsed_time:.2f}秒, 错误={error_details}")
            return {
                "success": False, 
                "message": error_details,
                "status": "error"
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"DeepSeek连接测试失败: {str(e)}"
            logger.error(f"{error_msg}, 耗时={elapsed_time:.2f}秒", exc_info=True)
            return {
                "success": False, 
                "message": error_msg,
                "status": "error"
            }