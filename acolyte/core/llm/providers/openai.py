"""
OpenAI GPT客户端

OpenAI GPT API的客户端实现。
"""

import json
from typing import Any, Dict, Union

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.base import LlmClient, retry_on_error
from acolyte.core.llm.constants import PROVIDER_OPENAI
from acolyte.core.llm.response import ResponseParser
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class OpenAIClient(LlmClient):
    """
    OpenAI GPT客户端

    该类是LlmClient的实现，专门用于与OpenAI GPT API进行交互。
    它支持GPT系列模型（如GPT-3.5-Turbo、GPT-4等），
    并支持标准OpenAI API和Azure OpenAI API。

    主要功能：
    - 处理内容：使用GPT模型分析文本内容
    - 连接测试：测试与OpenAI API的连通性
    - 错误处理：处理API调用过程中的各种错误
    - 自动重试：对临时错误进行自动重试

    支持的API：
    - 标准OpenAI API：直接调用OpenAI的API端点
    - Azure OpenAI API：通过Azure部署的OpenAI模型
    """

    def __init__(self, llm_config: LlmConfig):
        """
        初始化OpenAI GPT客户端

        该方法初始化OpenAIClient实例，设置必要的属性和配置。
        它首先调用父类的__init__方法初始化基本属性，然后设置提供商信息。
        它还会检测是否使用Azure OpenAI，并验证API密钥格式。

        Args:
            llm_config: LLM配置对象，包含名称、API密钥、基础URL、模型名称等信息

        Note:
            如果使用Azure OpenAI，则通过检查base_url或model_name中是否包含"azure"来识别。
            Azure OpenAI API密钥应该以'sk-'或'apikey-'开头，如果不符合这个格式，会记录警告日志。
        """
        super().__init__(llm_config)
        self.provider = PROVIDER_OPENAI

        # 检查是否是Azure OpenAI
        self.is_azure = "azure" in self.base_url.lower() or "azure" in self.model_name.lower()

        # 如果使用Azure OpenAI，确保API密钥格式正确
        if self.is_azure and self.api_key and not self.api_key.startswith(("sk-", "apikey-")):
            logger.warning("Azure OpenAI API密钥格式可能不正确")

    @retry_on_error()
    async def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """
        使用OpenAI GPT处理内容

        该方法实现了LlmClient的抽象方法，用于使用GPT模型处理文本内容。
        它首先检查API密钥，然后准备提示词，最后发送请求并处理响应。
        它支持标准OpenAI API和Azure OpenAI API，并会根据配置自动选择适合的API端点。

        处理流程：
        1. 检查API密钥是否设置
        2. 准备系统提示词和用户提示词
        3. 根据是否使用Azure准备不同的请求参数
        4. 发送HTTP POST请求到OpenAI API
        5. 处理响应并解析结果
        6. 使用ResponseParser解析响应内容

        Args:
            content: 要处理的文本内容，通常是需要分析的文章或新闻
            prompt: 提示词模板，包含分析指导和输出格式要求

        Returns:
            Dict[str, Any]: 处理结果字典，包含以下字段：
                - success (bool): 处理是否成功
                - raw_response (str, 可选): 成功时包含GPT的原始响应文本
                - result (Dict, 可选): 成功时包含解析后的结构化结果
                - error (str, 可选): 失败时包含错误信息
        """
        logger.info(f"使用OpenAI GPT处理内容: 模型={self.model_name}")

        # 检查API密钥
        if not self._check_api_key():
            return {"success": False, "error": "OpenAI API密钥未设置"}

        # 准备完整提示词
        system_prompt = "你是一名内容分析专家。你必须严格按照用户提供的分析框架执行，不得跳过任何步骤或修改框架结构。分析必须完全遵循框架中规定的格式、评分标准和输出要求。特别注意：(1)必须按框架提供的结构化分析；(2)必须使用框架规定的评分标准；(3)最终必须以框架指定的JSON格式输出量化结果。不要添加框架以外的分析方法或评分维度。"
        user_prompt = self._prepare_prompt(content, prompt)

        return await self._process_with_chat_api(system_prompt, user_prompt)

    async def _process_with_chat_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        使用Chat API处理内容

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词

        Returns:
            处理结果字典
        """
        logger.debug(f"使用OpenAI Chat API (Azure={self.is_azure})")

        # 准备请求参数
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "top_p": 0.2,
            "top_k": 30,
        }

        # 准备请求头
        headers = {"Content-Type": "application/json"}

        # 设置认证信息
        if self.is_azure:
            # Azure OpenAI
            headers["api-key"] = self.api_key
            endpoint = "/openai/deployments/{deployment}/chat/completions?api-version=2023-05-15"
            endpoint = endpoint.format(deployment=self.model_name)
        else:
            # 标准OpenAI
            headers["Authorization"] = f"Bearer {self.api_key}"
            endpoint = "/chat/completions"

        try:
            # 发送请求
            response = await self._make_request(
                method="POST",
                endpoint=endpoint,
                headers=headers,
                json_data=data,
                timeout=120.0,  # 较长的超时时间
            )

            # 解析响应
            result = response.json()

            # 检查响应中是否有内容
            if "choices" not in result or not result["choices"]:
                return {
                    "success": False,
                    "error": "OpenAI响应中没有choices字段",
                    "raw_response": json.dumps(result),
                }

            # 提取响应文本
            response_text = result["choices"][0].get("message", {}).get("content", "").strip()

            if not response_text:
                return {
                    "success": False,
                    "error": "OpenAI响应中没有内容",
                    "raw_response": json.dumps(result),
                }

            # 解析响应
            parsed_result = ResponseParser.parse_openai_response(response_text)

            # 确保即使解析失败也能返回有效的结果
            if parsed_result is None:
                parsed_result = {}

            # 将解析结果直接作为result返回，而不是嵌套在result字段中
            return {
                "success": True,
                "raw_response": response_text,
                "processed_result": {},
                "result": parsed_result,
            }

        except Exception as e:
            logger.error(f"OpenAI Chat API处理失败: {str(e)}", exc_info=True)
            return {"success": False, "error": f"OpenAI处理失败: {str(e)}"}

    async def _test_connection(self) -> Dict[str, Union[bool, str]]:
        """
        测试与OpenAI API的连接

        该方法实现了LlmClient的抽象方法，用于测试与OpenAI API的连接是否正常。
        它发送一个轻量级的请求（获取模型列表），以验证API密钥和连接是否有效。
        它支持标准OpenAI API和Azure OpenAI API，并会根据配置自动选择适合的API端点。

        测试流程：
        1. 根据是否使用Azure准备不同的请求头和端点
        2. 发送HTTP GET请求到OpenAI API的模型列表端点
        3. 如果请求成功，返回成功结果
        4. 如果请求失败，返回错误信息

        Returns:
            Dict[str, Union[bool, str]]: 测试结果字典，包含以下字段：
                - success (bool): 测试是否成功
                - message (str): 成功或失败的消息
                - error (str, 可选): 失败时包含错误信息
        """
        # 准备请求头
        headers = {}

        if self.is_azure:
            # Azure OpenAI
            headers["api-key"] = self.api_key
            endpoint = "/openai/models?api-version=2023-05-15"
        else:
            # 标准OpenAI
            headers["Authorization"] = f"Bearer {self.api_key}"
            endpoint = "/models"

        try:
            # 获取模型列表是最轻量的请求
            response = await self._make_request(method="GET", endpoint=endpoint, headers=headers)

            # 解析响应
            result = response.json()

            if "data" in result:
                models = result["data"]
                model_names = [m.get("id") for m in models if "id" in m]

                logger.info(f"OpenAI连接测试成功，可用模型: {', '.join(model_names[:3])}等")
                return {
                    "success": True,
                    "status": "success",
                    "message": f"连接成功，可用模型: {len(model_names)}个",
                    "models": model_names,
                }
            else:
                logger.warning("OpenAI连接测试成功，但响应格式异常")
                return {"success": True, "status": "warning", "message": "连接成功，但响应格式异常"}

        except Exception as e:
            logger.error(f"OpenAI连接测试失败: {str(e)}", exc_info=True)
            return {"success": False, "status": "error", "message": f"连接测试失败: {str(e)}"}
