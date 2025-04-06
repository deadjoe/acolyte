"""
DeepSeek LLM客户端

DeepSeek API的客户端实现，基于OpenAI兼容的API接口。
"""
import json
import time
from typing import Any, Dict, List, Optional, Union

import httpx

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.base import LlmClient, retry_on_error
from acolyte.core.llm.constants import PROVIDER_DEEPSEEK
from acolyte.core.llm.response import ResponseParser
from acolyte.core.llm.retry import ErrorHandler
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class DeepSeekClient(LlmClient):
    """DeepSeek LLM客户端"""

    def __init__(self, llm_config: LlmConfig):
        """
        初始化DeepSeek客户端

        Args:
            llm_config: LLM配置对象
        """
        super().__init__(llm_config)
        self.provider = PROVIDER_DEEPSEEK
        # 设置API基础URL，DeepSeek可能使用不同的基础URL
        self.base_url = self.base_url or "https://api.deepseek.com/v1"

    @retry_on_error()
    async def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """
        处理内容

        Args:
            content: 要处理的内容
            prompt: 提示模板

        Returns:
            处理结果字典
        """
        start_time = time.time()
        logger.info(f"使用DeepSeek处理内容: 模型={self.model_name}, 内容长度={len(content)}")

        # 检查API密钥
        if not self._check_api_key():
            logger.error("DeepSeek API密钥未设置")
            return {
                "success": False,
                "error": "DeepSeek API密钥未设置"
            }

        # 准备完整提示词
        system_prompt = "你是一个专业的内容分析员，专注于检测文本中的偏见、误导性信息和隐藏意图。"
        user_prompt = self._prepare_prompt(content, prompt)
        logger.debug(f"DeepSeek提示词准备完成: 系统提示词长度={len(system_prompt)}, 用户提示词长度={len(user_prompt)}")

        # 处理内容
        result = await self._process_with_chat_api(system_prompt, user_prompt)

        # 记录处理时间
        elapsed_time = time.time() - start_time
        if result.get("success", False):
            logger.info(f"DeepSeek处理成功: 耗时={elapsed_time:.2f}秒")
        else:
            logger.error(f"DeepSeek处理失败: 耗时={elapsed_time:.2f}秒, 错误={result.get('error', '未知错误')}")

        return result

    async def _process_with_chat_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        使用Chat API处理内容

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词

        Returns:
            处理结果字典
        """
        logger.debug(f"使用DeepSeek Chat API: 模型={self.model_name}")

        # 准备请求参数
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4000
        }

        # 记录请求参数（排除敏感信息）
        log_data = data.copy()
        logger.debug(f"DeepSeek请求参数: {json.dumps(log_data)}")

        # 准备请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # 设置API端点
        endpoint = "/chat/completions"
        full_url = f"{self.base_url}{endpoint}"
        logger.debug(f"DeepSeek API请求URL: {full_url}")

        try:
            # 记录请求开始时间
            request_start_time = time.time()

            # 发送请求
            response = await self._make_request(
                method="POST",
                endpoint=endpoint,
                headers=headers,
                json_data=data,
                timeout=120.0  # 较长的超时时间
            )

            # 记录请求耗时
            request_time = time.time() - request_start_time
            logger.debug(f"DeepSeek API请求耗时: {request_time:.2f}秒")

            # 解析响应
            result = response.json()
            logger.debug(f"DeepSeek API响应状态码: {response.status_code}")

            # 记录响应头（可能包含速率限制信息）
            rate_limit_headers = {k: v for k, v in response.headers.items() if 'rate' in k.lower() or 'limit' in k.lower()}
            if rate_limit_headers:
                logger.debug(f"DeepSeek API速率限制信息: {rate_limit_headers}")

            # 检查响应中是否有内容
            if "choices" not in result or not result["choices"]:
                error_msg = "DeepSeek响应中没有choices字段"
                logger.error(f"{error_msg}: {json.dumps(result)}")
                return {
                    "success": False,
                    "error": error_msg,
                    "raw_response": json.dumps(result)
                }

            # 提取响应文本
            response_text = result["choices"][0].get("message", {}).get("content", "").strip()

            if not response_text:
                error_msg = "DeepSeek响应中没有内容"
                logger.error(f"{error_msg}: {json.dumps(result)}")
                return {
                    "success": False,
                    "error": error_msg,
                    "raw_response": json.dumps(result)
                }

            # 记录响应长度
            logger.debug(f"DeepSeek响应长度: {len(response_text)} 字符")

            # 记录使用的tokens
            if "usage" in result:
                usage = result["usage"]
                logger.debug(f"DeepSeek Tokens使用情况: 提示={usage.get('prompt_tokens', 0)}, "
                           f"完成={usage.get('completion_tokens', 0)}, "
                           f"总计={usage.get('total_tokens', 0)}")

            # 解析响应开始时间
            parse_start_time = time.time()

            # 解析响应
            parsed_result = ResponseParser.parse_deepseek_response(response_text)

            # 记录解析耗时
            parse_time = time.time() - parse_start_time
            logger.debug(f"DeepSeek响应解析耗时: {parse_time:.2f}秒")

            # 确保即使解析失败也能返回有效的结果
            if parsed_result is None:
                logger.warning("DeepSeek响应解析返回None，使用空字典替代")
                parsed_result = {}

            # 将解析结果直接作为result返回，而不是嵌套在result字段中
            return {
                "success": True,
                "raw_response": response_text,
                "processed_result": {},
                "result": parsed_result
            }

        except httpx.HTTPStatusError as e:
            # 处理HTTP状态错误
            error_info = ErrorHandler.handle_http_error(e, self.provider)
            logger.error(f"DeepSeek API HTTP错误: {error_info.message}", exc_info=True)

            return {
                "success": False,
                "error": error_info.message,
                "error_type": error_info.error_type,
                "status_code": error_info.status_code,
                "should_retry": error_info.should_retry
            }

        except httpx.RequestError as e:
            # 处理请求错误（网络问题等）
            error_info = ErrorHandler.handle_request_error(e, self.provider)
            logger.error(f"DeepSeek API请求错误: {error_info.message}", exc_info=True)

            return {
                "success": False,
                "error": error_info.message,
                "error_type": error_info.error_type,
                "should_retry": error_info.should_retry
            }

        except json.JSONDecodeError as e:
            # 处理JSON解析错误
            error_msg = f"DeepSeek响应JSON解析失败: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return {
                "success": False,
                "error": error_msg,
                "error_type": "JSON解析错误"
            }

        except Exception as e:
            # 处理其他所有异常
            error_msg = f"DeepSeek处理失败: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return {
                "success": False,
                "error": error_msg,
                "error_type": "未知错误"
            }

    async def _test_connection(self) -> Dict[str, Union[bool, str]]:
        """
        测试连接

        测试与DeepSeek API的连接是否正常。

        Returns:
            测试结果字典
        """
        logger.info(f"开始测试DeepSeek连接: 模型={self.model_name}")

        # 检查API密钥
        if not self._check_api_key():
            logger.error("DeepSeek API密钥未设置")
            return {
                "success": False,
                "status": "error",
                "message": "API密钥未设置"
            }

        # 准备请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # DeepSeek API可能没有专门的模型列表接口，使用简单的聊天请求测试连接
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, this is a connection test."}
            ],
            "max_tokens": 10,
            "temperature": 0.1
        }

        endpoint = "/chat/completions"
        full_url = f"{self.base_url}{endpoint}"
        logger.debug(f"DeepSeek连接测试URL: {full_url}")

        try:
            # 记录请求开始时间
            test_start_time = time.time()

            # 发送请求
            response = await self._make_request(
                method="POST",
                endpoint=endpoint,
                headers=headers,
                json_data=data,
                timeout=30.0  # 较短的超时时间，因为只是测试连接
            )

            # 记录请求耗时
            test_time = time.time() - test_start_time
            logger.debug(f"DeepSeek连接测试耗时: {test_time:.2f}秒")

            # 解析响应
            result = response.json()
            logger.debug(f"DeepSeek连接测试响应状态码: {response.status_code}")

            if "choices" in result and len(result["choices"]) > 0:
                # 记录模型版本信息（如果有）
                model_info = ""
                if "model" in result:
                    model_info = f", 模型={result['model']}"

                # 记录使用的tokens
                usage_info = ""
                if "usage" in result:
                    usage = result["usage"]
                    usage_info = f", Tokens: 提示={usage.get('prompt_tokens', 0)}, " \
                               f"完成={usage.get('completion_tokens', 0)}, " \
                               f"总计={usage.get('total_tokens', 0)}"

                logger.info(f"DeepSeek连接测试成功{model_info}{usage_info}")
                return {
                    "success": True,
                    "status": "success",
                    "message": "连接成功",
                    "model": self.model_name,
                    "response_time": f"{test_time:.2f}秒"
                }
            else:
                logger.warning(f"DeepSeek连接测试成功，但响应格式异常: {json.dumps(result)}")
                return {
                    "success": True,
                    "status": "warning",
                    "message": "连接成功，但响应格式异常",
                    "response_time": f"{test_time:.2f}秒"
                }

        except httpx.HTTPStatusError as e:
            # 处理HTTP状态错误
            error_info = ErrorHandler.handle_http_error(e, self.provider)
            logger.error(f"DeepSeek连接测试失败 - HTTP错误: {error_info.message}", exc_info=True)

            return {
                "success": False,
                "status": "error",
                "message": f"连接测试失败: {error_info.message}",
                "error_type": error_info.error_type,
                "status_code": error_info.status_code
            }

        except httpx.RequestError as e:
            # 处理请求错误（网络问题等）
            error_info = ErrorHandler.handle_request_error(e, self.provider)
            logger.error(f"DeepSeek连接测试失败 - 请求错误: {error_info.message}", exc_info=True)

            return {
                "success": False,
                "status": "error",
                "message": f"连接测试失败: {error_info.message}",
                "error_type": error_info.error_type
            }

        except Exception as e:
            # 处理其他所有异常
            error_msg = f"DeepSeek连接测试失败: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return {
                "success": False,
                "status": "error",
                "message": error_msg
            }
