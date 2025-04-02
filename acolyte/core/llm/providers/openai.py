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
    """OpenAI GPT客户端"""
    
    def __init__(self, llm_config: LlmConfig):
        """
        初始化OpenAI GPT客户端
        
        Args:
            llm_config: LLM配置对象
        """
        super().__init__(llm_config)
        self.provider = PROVIDER_OPENAI
        
        # 检查是否是Azure OpenAI
        self.is_azure = "azure" in self.base_url.lower() or "azure" in self.model_name.lower()
        
        # 如果使用Azure OpenAI，确保API密钥格式正确
        if self.is_azure and self.api_key and not self.api_key.startswith(("sk-", "apikey-")):
            logger.warning("Azure OpenAI API密钥格式可能不正确")
    
    @retry_on_error()
    def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """
        处理内容
        
        Args:
            content: 要处理的内容
            prompt: 提示模板
            
        Returns:
            处理结果字典
        """
        logger.info(f"使用OpenAI GPT处理内容: 模型={self.model_name}")
        
        # 检查API密钥
        if not self._check_api_key():
            return {
                "success": False, 
                "error": "OpenAI API密钥未设置"
            }
        
        # 准备完整提示词
        system_prompt = "你是一个专业的内容分析员，专注于检测文本中的偏见、误导性信息和隐藏意图。"
        user_prompt = self._prepare_prompt(content, prompt)
        
        return self._process_with_chat_api(system_prompt, user_prompt)
    
    def _process_with_chat_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
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
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4000
        }
        
        # 准备请求头
        headers = {
            "Content-Type": "application/json"
        }
        
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
            response = self._make_request(
                method="POST",
                endpoint=endpoint,
                headers=headers,
                json_data=data,
                timeout=120.0  # 较长的超时时间
            )
            
            # 解析响应
            result = response.json()
            
            # 检查响应中是否有内容
            if "choices" not in result or not result["choices"]:
                return {
                    "success": False,
                    "error": "OpenAI响应中没有choices字段",
                    "raw_response": json.dumps(result)
                }
                
            # 提取响应文本
            response_text = result["choices"][0].get("message", {}).get("content", "").strip()
            
            if not response_text:
                return {
                    "success": False,
                    "error": "OpenAI响应中没有内容",
                    "raw_response": json.dumps(result)
                }
                
            # 解析响应
            parsed_result = ResponseParser.parse_openai_response(response_text)
            
            return {
                "success": True,
                "raw_response": response_text,
                "processed_result": parsed_result.get("processed_result", {}),
                "result": parsed_result.get("result", {})
            }
            
        except Exception as e:
            logger.error(f"OpenAI Chat API处理失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"OpenAI处理失败: {str(e)}"
            }
    
    def _test_connection(self) -> Dict[str, Union[bool, str]]:
        """
        测试连接
        
        测试与OpenAI API的连接是否正常。
        
        Returns:
            测试结果字典
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
            response = self._make_request(
                method="GET",
                endpoint=endpoint,
                headers=headers
            )
            
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
                    "models": model_names
                }
            else:
                logger.warning("OpenAI连接测试成功，但响应格式异常")
                return {
                    "success": True,
                    "status": "warning",
                    "message": "连接成功，但响应格式异常"
                }
                
        except Exception as e:
            logger.error(f"OpenAI连接测试失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "status": "error",
                "message": f"连接测试失败: {str(e)}"
            }