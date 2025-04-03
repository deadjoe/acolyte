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
    """Anthropic Claude客户端"""
    
    def __init__(self, llm_config: LlmConfig):
        """
        初始化Anthropic Claude客户端
        
        Args:
            llm_config: LLM配置对象
        """
        super().__init__(llm_config)
        self.provider = PROVIDER_ANTHROPIC
        
        # 检查API密钥格式
        if self.api_key and not self.api_key.startswith(("sk-", "anthropic-")):
            logger.warning("Anthropic API密钥格式可能不正确，应以'sk-'或'anthropic-'开头")
    
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
        logger.info(f"使用Anthropic Claude处理内容: 模型={self.model_name}")
        
        # 检查API密钥
        if not self._check_api_key():
            return {
                "success": False, 
                "error": "Anthropic API密钥未设置"
            }
        
        # 准备完整提示词
        system_prompt = "你是一个专业的内容分析员，专注于检测文本中的偏见、误导性信息和隐藏意图。"
        user_prompt = self._prepare_prompt(content, prompt)
        
        # 检测API版本
        if "messages" in user_prompt.lower():
            # 使用Messages API
            return await self._process_with_messages_api(system_prompt, user_prompt)
        else:
            # 使用文本完成API
            return await self._process_with_completion_api(system_prompt, user_prompt)
    
    async def _process_with_messages_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        使用Messages API处理内容
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            
        Returns:
            处理结果字典
        """
        logger.debug("使用Anthropic Messages API")
        
        # 准备请求参数
        data = {
            "model": self.model_name,
            "max_tokens": 4000,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3
        }
        
        # 准备请求头
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        try:
            # 发送请求
            response = await self._make_request(
                method="POST",
                endpoint="/v1/messages",
                headers=headers,
                json_data=data,
                timeout=120.0  # 较长的超时时间
            )
            
            # 解析响应
            result = response.json()
            
            # 检查响应中是否有内容
            if "content" not in result or not result["content"]:
                return {
                    "success": False,
                    "error": "Anthropic响应中没有内容",
                    "raw_response": json.dumps(result)
                }
                
            # 提取响应文本
            content_blocks = result["content"]
            response_text = "\n".join(
                block["text"] for block in content_blocks 
                if block["type"] == "text"
            )
            
            # 解析响应
            parsed_result = ResponseParser.parse_anthropic_response(response_text)
            
            return {
                "success": True,
                "raw_response": response_text,
                "processed_result": parsed_result.get("processed_result", {}),
                "result": parsed_result.get("result", {})
            }
            
        except Exception as e:
            logger.error(f"Anthropic Messages API处理失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Anthropic处理失败: {str(e)}"
            }
    
    async def _process_with_completion_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        使用Completion API处理内容
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            
        Returns:
            处理结果字典
        """
        logger.debug("使用Anthropic Completion API")
        
        # 准备请求参数
        data = {
            "model": self.model_name,
            "max_tokens_to_sample": 4000,
            "prompt": f"\n\nHuman: {user_prompt}\n\nAssistant:",
            "temperature": 0.3
        }
        
        # 准备请求头
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        try:
            # 发送请求
            response = await self._make_request(
                method="POST",
                endpoint="/v1/complete",
                headers=headers,
                json_data=data,
                timeout=120.0  # 较长的超时时间
            )
            
            # 解析响应
            result = response.json()
            
            # 检查响应中是否有内容
            if "completion" not in result:
                return {
                    "success": False,
                    "error": "Anthropic响应中没有completion字段",
                    "raw_response": json.dumps(result)
                }
                
            # 提取响应文本
            response_text = result["completion"].strip()
            
            # 解析响应
            parsed_result = ResponseParser.parse_anthropic_response(response_text)
            
            return {
                "success": True,
                "raw_response": response_text,
                "processed_result": parsed_result.get("processed_result", {}),
                "result": parsed_result.get("result", {})
            }
            
        except Exception as e:
            logger.error(f"Anthropic Completion API处理失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Anthropic处理失败: {str(e)}"
            }
    
    async def _test_connection(self) -> Dict[str, Union[bool, str]]:
        """
        测试连接
        
        测试与Anthropic API的连接是否正常。
        
        Returns:
            测试结果字典
        """
        # 准备请求头
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        try:
            # 获取模型列表是最轻量的请求
            response = await self._make_request(
                method="GET",
                endpoint="/v1/models",
                headers=headers
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
                    "models": model_names
                }
            else:
                logger.warning("Anthropic连接测试成功，但响应格式异常")
                return {
                    "success": True,
                    "status": "warning",
                    "message": "连接成功，但响应格式异常"
                }
                
        except Exception as e:
            logger.error(f"Anthropic连接测试失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "status": "error",
                "message": f"连接测试失败: {str(e)}"
            }