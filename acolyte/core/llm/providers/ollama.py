"""
Ollama LLM Client implementation for Acolyte.
"""

import time
from typing import Any, Dict, Union

import httpx

from acolyte.utils.logging import get_logger

from ...db.models import LlmConfig
from ..base import LlmClient
from ..constants import DEFAULT_TIMEOUT, PROVIDER_OLLAMA
from ..response import ErrorHandler, ResponseParser

# 获取日志记录器
logger = get_logger(__name__)


class OllamaClient(LlmClient):
    """
    Client for Ollama API, which provides local model hosting.
    """

    def __init__(self, llm_config: LlmConfig):
        super().__init__(llm_config)
        self.provider = PROVIDER_OLLAMA
        self.base_url = self._normalize_base_url(self.base_url)
        # Local models might need more time to respond
        self.timeout = DEFAULT_TIMEOUT * 5  # 增加超时时间到300秒
        self.response_parser = ResponseParser()
        self.error_handler = ErrorHandler()
        logger.debug(f"初始化Ollama客户端: 模型={self.model_name}, URL={self.base_url}")

    def _check_api_key(self) -> bool:
        """
        Check if API key is set.
        Ollama doesn't typically use API keys, so we return True.
        """
        return True

    def _normalize_base_url(self, base_url: str) -> str:
        """
        Normalize the Ollama API base URL.
        Default to http://localhost:11434 if not set.
        """
        if not base_url:
            return "http://localhost:11434"

        # Remove trailing slashes
        base_url = base_url.rstrip("/")

        # Ensure URL has http:// or https:// prefix
        if not base_url.startswith(("http://", "https://")):
            base_url = f"http://{base_url}"

        return base_url

    async def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """
        Process content with Ollama API.

        Args:
            content: The content to be analyzed
            prompt: The prompt template to use

        Returns:
            Dict with response data or error information
        """
        logger.info(f"使用Ollama处理内容: 模型={self.model_name}, 内容长度={len(content)}字符")
        start_time = time.time()

        try:
            # Prepare prompt
            system_prompt = "你是一名内容分析专家。你必须严格按照用户提供的分析框架执行，不得跳过任何步骤或修改框架结构。分析必须完全遵循框架中规定的格式、评分标准和输出要求。特别注意：(1)必须按框架提供的结构化分析；(2)必须使用框架规定的评分标准；(3)最终必须以框架指定的JSON格式输出量化结果。不要添加框架以外的分析方法或评分维度。"
            user_prompt = self._prepare_prompt(content, prompt)

            # Call API
            response = await self._process_with_api(system_prompt, user_prompt)

            # 记录处理时间和结果
            elapsed_time = time.time() - start_time
            if response.get("success", False):
                scores = response.get("scores", {})
                logger.info(
                    f"Ollama处理成功: 耗时={elapsed_time:.2f}秒, "
                    f"BI={scores.get('bias_index')}, "
                    f"MI={scores.get('misleading_index')}, "
                    f"HI={scores.get('hidden_intent_index')}, "
                    f"CS={scores.get('credibility_score')}"
                )
            else:
                logger.error(
                    f"Ollama处理失败: 耗时={elapsed_time:.2f}秒, 错误={response.get('error')}"
                )

            return response

        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Ollama处理内容异常: {str(e)}"
            logger.error(f"{error_msg}, 耗时={elapsed_time:.2f}秒", exc_info=True)
            return {"success": False, "error": error_msg}

    async def _process_with_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Make a request to the Ollama API.

        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt

        Returns:
            Dict with response data or error information
        """
        start_time = time.time()
        try:
            # Prepare API URL for Ollama
            api_url = f"{self.base_url}/generate"

            # Prepare headers
            headers = {"Content-Type": "application/json"}

            # Prepare request data
            # Ollama has a different API format
            data = {
                "model": self.model_name,
                "prompt": user_prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.2,
                    "top_k": 30,
                    "num_predict": 8000,
                },
            }

            logger.debug(f"Ollama请求: URL={api_url}, 模型={self.model_name}")

            # Make the request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(api_url, headers=headers, json=data)

                # 记录请求时间
                request_time = time.time() - start_time
                logger.debug(
                    f"Ollama请求完成: 状态码={response.status_code}, 耗时={request_time:.2f}秒"
                )

                # Check for HTTP errors
                response.raise_for_status()

                # Parse response
                response_json = response.json()

                # Extract the response text from Ollama-specific format
                if "response" in response_json:
                    response_text = response_json["response"]

                    # Parse scores and structured content
                    scores = self.response_parser.extract_scores(response_text)
                    structured_content = self.response_parser.extract_structured_content(
                        response_text
                    )

                    # 记录响应解析
                    parse_time = time.time() - start_time - request_time
                    logger.debug(
                        f"Ollama响应解析完成: 解析耗时={parse_time:.2f}秒, 总耗时={(time.time()-start_time):.2f}秒"
                    )

                    return {
                        "success": True,
                        "response": response_text,
                        "scores": scores,
                        "structured_content": structured_content,
                        "raw_response": response_json,
                    }
                else:
                    logger.warning(f"Ollama响应格式无效: {response_json}")
                    return {
                        "success": False,
                        "error": "Ollama API响应格式无效",
                        "raw_response": response_json,
                    }

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Ollama HTTP错误: 状态码={e.response.status_code}, URL={e.request.url}, 耗时={(time.time()-start_time):.2f}秒"
            )
            return {"success": False, "error": f"Ollama HTTP错误: 状态码={e.response.status_code}, URL={e.request.url}"}

        except httpx.RequestError as e:
            error_msg = f"Ollama API网络错误: {str(e)}"
            logger.error(f"{error_msg}, 耗时={(time.time()-start_time):.2f}秒", exc_info=True)
            return {"success": False, "error": error_msg}

        except Exception as e:
            error_msg = f"Ollama API未知错误: {str(e)}"
            logger.error(f"{error_msg}, 耗时={(time.time()-start_time):.2f}秒", exc_info=True)
            return {"success": False, "error": error_msg}

    async def _test_connection(self) -> Dict[str, Union[bool, str]]:
        """
        Test connection to Ollama API.

        Returns:
            Dict with success status and message
        """
        logger.info(f"测试Ollama连接: 模型={self.model_name}, URL={self.base_url}")
        start_time = time.time()

        try:
            # Use Ollama's models endpoint to check connectivity
            api_url = f"{self.base_url}/api/tags"

            logger.debug(f"Ollama连接测试请求: URL={api_url}")

            # Make the request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(api_url)

                # Record response time
                request_time = time.time() - start_time
                logger.debug(
                    f"Ollama连接测试响应: 状态码={response.status_code}, 耗时={request_time:.2f}秒"
                )

                # Check response status
                response.raise_for_status()

                # Check if the model exists
                models_response = response.json()
                if "models" in models_response:
                    # Check if our model is in the list
                    model_names = [model.get("name") for model in models_response.get("models", [])]
                    if self.model_name in model_names:
                        logger.info(
                            f"Ollama连接测试成功: 找到模型={self.model_name}, 耗时={time.time()-start_time:.2f}秒"
                        )
                        return {
                            "success": True,
                            "message": f"成功连接到Ollama API并找到模型 {self.model_name}",
                            "status": "success",
                        }
                    else:
                        available_models = ", ".join(model_names[:5])
                        logger.warning(
                            f"Ollama连接测试部分成功: 未找到模型={self.model_name}, 可用模型={available_models}, 耗时={time.time()-start_time:.2f}秒"
                        )
                        return {
                            "success": False,
                            "message": f"已连接到Ollama API但未找到模型 {self.model_name}。可用模型: {available_models}...",
                            "status": "warning",
                        }

                # If we get here but can't verify the model, the connection is still successful
                logger.info(f"Ollama连接测试成功: 耗时={time.time()-start_time:.2f}秒")
                return {"success": True, "message": "成功连接到Ollama API", "status": "success"}

        except httpx.HTTPStatusError as e:
            elapsed_time = time.time() - start_time
            error_details = f"HTTP错误: 状态码={e.response.status_code}, URL={e.request.url}"
            logger.error(
                f"Ollama连接测试HTTP错误: 状态码={e.response.status_code}, 耗时={elapsed_time:.2f}秒, 错误={error_details}"
            )
            return {"success": False, "message": error_details, "status": "error"}

        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Ollama连接测试失败: {str(e)}"
            logger.error(f"{error_msg}, 耗时={elapsed_time:.2f}秒", exc_info=True)
            return {"success": False, "message": error_msg, "status": "error"}
