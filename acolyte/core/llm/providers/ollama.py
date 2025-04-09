"""
Ollama客户端

Ollama API的客户端实现，用于与本地或远程部署的Ollama服务进行交互。
支持通过Ollama部署的各种开源模型（如Llama、Mistral、Mixtral等）。
"""

import time
from typing import Any, Dict, Union

import httpx

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.base import LlmClient, retry_on_error
from acolyte.core.llm.constants import DEFAULT_TIMEOUT, PROVIDER_OLLAMA
from acolyte.core.llm.response import ResponseParser, ErrorHandler
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class OllamaClient(LlmClient):
    """
    Ollama客户端

    该类是LlmClient的实现，专门用于与Ollama API进行交互。
    它支持通过Ollama部署的各种开源模型（如Llama、Mistral、Mixtral等），
    并实现了使用Generate API的方法。

    主要功能：
    - 处理内容：使用Ollama模型分析文本内容
    - 连接测试：测试与Ollama API的连通性
    - 错误处理：处理API调用过程中的各种错误
    - 自动重试：对临时错误进行自动重试

    支持的API：
    - Generate API：用于生成文本，支持系统提示词和用户提示词
    - Chat API：（计划中）用于发送聊天消息并获取响应，是Ollama推荐的API
    """

    def __init__(self, llm_config: LlmConfig):
        """
        初始化Ollama客户端

        该方法初始化OllamaClient实例，设置必要的属性和配置。
        它首先调用父类的__init__方法初始化基本属性，然后设置提供商信息。

        Args:
            llm_config: LLM配置对象，包含名称、API密钥、基础URL、模型名称等信息

        Note:
            Ollama通常不需要API密钥，但如果部署在远程服务器上可能需要配置认证。
            默认情况下，Ollama服务运行在本地的11434端口。
        """
        super().__init__(llm_config)
        self.provider = PROVIDER_OLLAMA
        self.base_url = self._normalize_base_url(self.base_url)
        # 本地模型可能需要更多时间响应
        self.timeout = DEFAULT_TIMEOUT * 2
        self.response_parser = ResponseParser()
        self.error_handler = ErrorHandler()
        logger.debug(f"初始化Ollama客户端: 模型={self.model_name}, URL={self.base_url}")

    def _check_api_key(self) -> bool:
        """
        检查API密钥是否有效

        该方法实现了LlmClient的_check_api_key方法，用于检查API密钥是否有效。
        由于Ollama通常不需要API密钥，因此始终返回True。

        Returns:
            bool: 始终返回True，因为Ollama不需要API密钥
        """
        return True

    def _normalize_base_url(self, base_url: str) -> str:
        """
        标准化Ollama API基础URL

        该方法将输入的URL标准化，确保其格式正确。
        如果未提供URL，则使用默认的本地地址。

        处理流程：
        1. 如果URL为空，返回默认的本地地址
        2. 移除URL末尾的斜杠
        3. 确保URL包含http://或https://前缀

        Args:
            base_url: 原始URL字符串

        Returns:
            标准化后的URL字符串
        """
        if not base_url:
            return "http://localhost:11434"

        # Remove trailing slashes
        base_url = base_url.rstrip("/")

        # Ensure URL has http:// or https:// prefix
        if not base_url.startswith(("http://", "https://")):
            base_url = f"http://{base_url}"

        return base_url

    @retry_on_error()
    async def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """
        使用Ollama处理内容

        该方法实现了LlmClient的抽象方法，用于使用Ollama模型处理文本内容。
        它准备系统提示词和用户提示词，然后调用Generate API发送请求。
        如果将来需要，可以添加对Chat API的支持。

        处理流程：
        1. 准备系统提示词和用户提示词
        2. 调用_process_with_api方法发送请求
        3. 返回处理结果

        Args:
            content: 要处理的文本内容，通常是需要分析的文章或新闻
            prompt: 提示词模板，包含分析指导和输出格式要求

        Returns:
            Dict[str, Any]: 处理结果字典，包含以下字段：
                - success (bool): 处理是否成功
                - raw_response (str, 可选): 成功时包含Ollama的原始响应文本
                - result (Dict, 可选): 成功时包含解析后的结构化结果
                - error (str, 可选): 失败时包含错误信息
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
        使用Ollama API发送请求

        该方法使用Ollama的Generate API发送请求并处理响应。
        Generate API支持系统提示词和用户提示词的分离。

        请求流程：
        1. 准备请求参数（模型、提示词、温度等）
        2. 发送HTTP POST请求到Ollama API
        3. 处理响应并解析结果
        4. 使用ResponseParser解析响应内容

        Args:
            system_prompt: 系统提示词，用于设置模型的行为和角色
            user_prompt: 用户提示词，包含具体的分析内容和指令

        Returns:
            Dict[str, Any]: 处理结果字典，包含以下字段：
                - success (bool): 处理是否成功
                - raw_response (str, 可选): 成功时包含Ollama的原始响应文本
                - result (Dict, 可选): 成功时包含解析后的结构化结果
                - error (str, 可选): 失败时包含错误信息
        """
        start_time = time.time()
        try:
            # Prepare API URL for Ollama
            # 根据Ollama API文档，正确的端点是/generate
            api_url = f"{self.base_url}/generate"

            # Prepare headers
            headers = {"Content-Type": "application/json"}

            # Prepare request data
            # 根据Ollama API文档准备请求参数
            # https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-completion
            data = {
                "model": self.model_name,
                "prompt": user_prompt,
                "system": system_prompt,
                "stream": False,
                "format": "json",  # 请求JSON格式的响应，提高解析成功率
                "options": {
                    "temperature": 0.1,  # 温度参数
                    "top_p": 0.2,       # 累积概率阈值
                    "top_k": 30,        # 考虑的最高概率词汇数量
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

                    # 解析响应
                    parsed_result = ResponseParser.parse_ollama_response(response_text)

                    # 确保即使解析失败也能返回有效的结果
                    if parsed_result is None:
                        parsed_result = {}

                    # 记录响应解析
                    parse_time = time.time() - start_time - request_time
                    logger.debug(
                        f"Ollama响应解析完成: 解析耗时={parse_time:.2f}秒, 总耗时={(time.time()-start_time):.2f}秒"
                    )

                    return {
                        "success": True,
                        "raw_response": response_text,
                        "processed_result": {},
                        "result": parsed_result,
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
        测试与Ollama API的连接

        该方法实现了LlmClient的抽象方法，用于测试与Ollama API的连接是否正常。
        它发送一个轻量级的请求（获取模型列表），以验证连接是否有效。

        测试流程：
        1. 发送HTTP GET请求到Ollama API的模型列表端点
        2. 如果请求成功，检查指定的模型是否存在
        3. 返回测试结果

        Returns:
            Dict[str, Union[bool, str]]: 测试结果字典，包含以下字段：
                - success (bool): 测试是否成功
                - message (str): 成功或失败的消息
                - status (str): 状态标识（success、warning或error）
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
