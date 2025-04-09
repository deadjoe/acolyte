"""
Anthropic Claude客户端

Anthropic Claude API的客户端实现。
"""

import json
from typing import Any, Dict, Union

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.base import LlmClient, retry_on_error
from acolyte.core.llm.constants import PROVIDER_ANTHROPIC
from acolyte.core.llm.response import ResponseParser
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class AnthropicClient(LlmClient):
    """
    Anthropic Claude客户端

    该类是LlmClient的实现，专门用于与Anthropic Claude API进行交互。
    它支持Claude系列模型（如Claude 3 Opus、Claude 3 Sonnet等），
    并实现了使用Messages API和旧版Completion API的方法。

    主要功能：
    - 处理内容：使用Claude模型分析文本内容
    - 连接测试：测试与Anthropic API的连通性
    - 错误处理：处理API调用过程中的各种错误
    - 自动重试：对临时错误进行自动重试

    支持的API：
    - Messages API（主要）：新版API，支持系统提示词和用户提示词
    - Completion API（备用）：旧版API，仅在Messages API失败时使用
    """

    def __init__(self, llm_config: LlmConfig):
        """
        初始化Anthropic Claude客户端

        该方法初始化AnthropicClient实例，设置必要的属性和配置。
        它首先调用父类的__init__方法初始化基本属性，然后设置提供商信息。
        它还会检查API密钥的格式，确保其符合Anthropic的要求。

        Args:
            llm_config: LLM配置对象，包含名称、API密钥、基础URL、模型名称等信息

        Note:
            Anthropic API密钥应该以'sk-'或'anthropic-'开头，如果不符合这个格式，会记录警告日志。
        """
        super().__init__(llm_config)
        self.provider = PROVIDER_ANTHROPIC

        # 检查API密钥格式
        if self.api_key and not self.api_key.startswith(("sk-", "anthropic-")):
            logger.warning("Anthropic API密钥格式可能不正确，应以'sk-'或'anthropic-'开头")

    @retry_on_error()
    async def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """
        使用Anthropic Claude处理内容

        该方法实现了LlmClient的抽象方法，用于使用Claude模型处理文本内容。
        它首先检查API密钥，然后准备提示词，最后调用Messages API发送请求。
        如果Messages API失败，它会尝试使用旧版的Completion API。

        处理流程：
        1. 检查API密钥是否设置
        2. 准备系统提示词和用户提示词
        3. 调用_process_with_messages_api方法发送请求
        4. 如果失败，尝试使用_process_with_completion_api方法
        5. 返回处理结果

        Args:
            content: 要处理的文本内容，通常是需要分析的文章或新闻
            prompt: 提示词模板，包含分析指导和输出格式要求

        Returns:
            Dict[str, Any]: 处理结果字典，包含以下字段：
                - success (bool): 处理是否成功
                - raw_response (str, 可选): 成功时包含Claude的原始响应文本
                - result (Dict, 可选): 成功时包含解析后的结构化结果
                - error (str, 可选): 失败时包含错误信息
        """
        logger.info(f"使用Anthropic Claude处理内容: 模型={self.model_name}")

        # 检查API密钥
        if not self._check_api_key():
            return {"success": False, "error": "Anthropic API密钥未设置"}

        # 准备完整提示词
        system_prompt = "你是一名内容分析专家。你必须严格按照用户提供的分析框架执行，不得跳过任何步骤或修改框架结构。分析必须完全遵循框架中规定的格式、评分标准和输出要求。特别注意：(1)必须按框架提供的结构化分析；(2)必须使用框架规定的评分标准；(3)最终必须以框架指定的JSON格式输出量化结果。不要添加框架以外的分析方法或评分维度。"
        user_prompt = self._prepare_prompt(content, prompt)

        # 使用Messages API，因为Completion API已经过时
        return await self._process_with_messages_api(system_prompt, user_prompt)

    async def _process_with_messages_api(
        self, system_prompt: str, user_prompt: str
    ) -> Dict[str, Any]:
        """
        使用Anthropic Messages API处理内容

        该方法使用Anthropic的新版Messages API发送请求并处理响应。
        Messages API是推荐的API，支持系统提示词和用户提示词的分离。

        请求流程：
        1. 准备请求参数（模型、最大输出长度、温度等）
        2. 构建消息列表，包含系统消息和用户消息
        3. 发送HTTP POST请求到Anthropic API
        4. 处理响应并解析结果
        5. 使用ResponseParser解析响应内容

        Args:
            system_prompt: 系统提示词，用于设置模型的行为和角色
            user_prompt: 用户提示词，包含具体的分析内容和指令

        Returns:
            Dict[str, Any]: 处理结果字典，包含以下字段：
                - success (bool): 处理是否成功
                - raw_response (str, 可选): 成功时包含Claude的原始响应文本
                - result (Dict, 可选): 成功时包含解析后的结构化结果
                - error (str, 可选): 失败时包含错误信息
        """
        logger.debug("使用Anthropic Messages API")

        # 准备请求参数
        data = {
            "model": self.model_name,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": 0.1,
            "top_p": 0.2,
            "top_k": 30,
        }

        # 准备请求头
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        try:
            # 发送请求
            # 根据base_url是否已包含/v1来决定端点
            if self.base_url.endswith("/v1"):
                endpoint = "/messages"
            else:
                endpoint = "/v1/messages"

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
            if "content" not in result or not result["content"]:
                return {
                    "success": False,
                    "error": "Anthropic响应中没有内容",
                    "raw_response": json.dumps(result),
                }

            # 提取响应文本
            content_blocks = result["content"]
            response_text = "\n".join(
                block["text"] for block in content_blocks if block["type"] == "text"
            )

            # 解析响应
            parsed_result = ResponseParser.parse_anthropic_response(response_text)

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
            logger.error(f"Anthropic Messages API处理失败: {str(e)}", exc_info=True)
            return {"success": False, "error": f"Anthropic处理失败: {str(e)}"}

    async def _process_with_completion_api(
        self, system_prompt: str, user_prompt: str
    ) -> Dict[str, Any]:
        """
        使用Anthropic Completion API处理内容

        该方法使用Anthropic的旧版Completion API发送请求并处理响应。
        Completion API是旧版API，仅在Messages API失败时作为备用方案。
        该API不支持系统提示词和用户提示词的分离，因此忽略了system_prompt参数。

        请求流程：
        1. 准备请求参数（模型、最大输出长度、温度等）
        2. 构建提示词，使用Human/Assistant格式
        3. 发送HTTP POST请求到Anthropic API
        4. 处理响应并解析结果
        5. 使用ResponseParser解析响应内容

        Args:
            system_prompt: 系统提示词（在Completion API中被忽略）
            user_prompt: 用户提示词，包含具体的分析内容和指令

        Returns:
            Dict[str, Any]: 处理结果字典，包含以下字段：
                - success (bool): 处理是否成功
                - raw_response (str, 可选): 成功时包含Claude的原始响应文本
                - result (Dict, 可选): 成功时包含解析后的结构化结果
                - error (str, 可选): 失败时包含错误信息
        """
        logger.debug("使用Anthropic Completion API")

        # 准备请求参数
        data = {
            "model": self.model_name,
            "max_tokens_to_sample": 4000,
            "prompt": f"\n\nHuman: {user_prompt}\n\nAssistant:",
            "temperature": 0.3,
        }

        # 准备请求头
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        try:
            # 发送请求
            # 根据base_url是否已包含/v1来决定端点
            if self.base_url.endswith("/v1"):
                endpoint = "/complete"
            else:
                endpoint = "/v1/complete"

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
            if "completion" not in result:
                return {
                    "success": False,
                    "error": "Anthropic响应中没有completion字段",
                    "raw_response": json.dumps(result),
                }

            # 提取响应文本
            response_text = result["completion"].strip()

            # 解析响应
            parsed_result = ResponseParser.parse_anthropic_response(response_text)

            return {
                "success": True,
                "raw_response": response_text,
                "processed_result": {},
                "result": parsed_result,
            }

        except Exception as e:
            logger.error(f"Anthropic Completion API处理失败: {str(e)}", exc_info=True)
            return {"success": False, "error": f"Anthropic处理失败: {str(e)}"}

    async def _test_connection(self) -> Dict[str, Union[bool, str]]:
        """
        测试与Anthropic API的连接

        该方法实现了LlmClient的抽象方法，用于测试与Anthropic API的连接是否正常。
        它发送一个轻量级的请求（获取模型列表），以验证API密钥和连接是否有效。

        测试流程：
        1. 准备请求头，包含API密钥和其他必要信息
        2. 发送HTTP GET请求到Anthropic API的模型列表端点
        3. 如果请求成功，返回成功结果
        4. 如果请求失败，返回错误信息

        Returns:
            Dict[str, Union[bool, str]]: 测试结果字典，包含以下字段：
                - success (bool): 测试是否成功
                - message (str): 成功或失败的消息
                - error (str, 可选): 失败时包含错误信息
        """
        # 准备请求头
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        try:
            # 获取模型列表是最轻量的请求
            response = await self._make_request(
                method="GET", endpoint="/v1/models", headers=headers
            )

            # 解析响应
            result = response.json()

            if "models" in result:
                models = result["models"]
                model_names = [m.get("name") for m in models if "name" in m]

                logger.info(f"Anthropic连接测试成功，可用模型: {', '.join(model_names[:3])}等")
                return {
                    "success": True,
                    "status": "success",
                    "message": f"连接成功，可用模型: {len(model_names)}个",
                    "models": model_names,
                }
            else:
                logger.warning("Anthropic连接测试成功，但响应格式异常")
                return {"success": True, "status": "warning", "message": "连接成功，但响应格式异常"}

        except Exception as e:
            logger.error(f"Anthropic连接测试失败: {str(e)}", exc_info=True)
            return {"success": False, "status": "error", "message": f"连接测试失败: {str(e)}"}
