"""
Google Gemini客户端

Google Gemini API的客户端实现。
"""
import json
from typing import Any, Dict, Union

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.base import LlmClient, retry_on_error
from acolyte.core.llm.constants import PROVIDER_GEMINI
from acolyte.core.llm.response import ResponseParser
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class GeminiClient(LlmClient):
    """Google Gemini客户端"""
    
    def __init__(self, llm_config: LlmConfig):
        """
        初始化Google Gemini客户端
        
        Args:
            llm_config: LLM配置对象
        """
        super().__init__(llm_config)
        self.provider = PROVIDER_GEMINI
        
        # 修正模型名称，确保含有gemini
        if not "gemini" in self.model_name.lower():
            self.full_model_name = f"models/gemini-{self.model_name}"
        else:
            self.full_model_name = f"models/{self.model_name}"
            
        # 修正未包含"models/"前缀的情况
        if not self.full_model_name.startswith("models/"):
            self.full_model_name = f"models/{self.full_model_name}"
    
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
        logger.info(f"使用Google Gemini处理内容: 模型={self.model_name}")
        
        # 检查API密钥
        if not self._check_api_key():
            return {
                "success": False, 
                "error": "Google Gemini API密钥未设置"
            }
        
        # 准备完整提示词
        user_prompt = self._prepare_prompt(content, prompt)
        
        return self._process_with_gemini_api(user_prompt)
    
    def _process_with_gemini_api(self, user_prompt: str) -> Dict[str, Any]:
        """
        使用Gemini API处理内容
        
        Args:
            user_prompt: 用户提示词
            
        Returns:
            处理结果字典
        """
        logger.debug("使用Google Gemini API")
        
        # 准备请求参数
        data = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 4000,
                "topP": 0.95,
                "topK": 40
            }
        }
        
        # 准备请求头
        headers = {
            "Content-Type": "application/json"
        }
        
        # Gemini使用URL参数传递API密钥
        endpoint = f"{self.full_model_name}:generateContent?key={self.api_key}"
        
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
            if "candidates" not in result or not result["candidates"]:
                return {
                    "success": False,
                    "error": "Gemini响应中没有candidates字段",
                    "raw_response": json.dumps(result)
                }
                
            # 提取响应文本
            candidate = result["candidates"][0]
            if "content" not in candidate or "parts" not in candidate["content"]:
                return {
                    "success": False,
                    "error": "Gemini响应格式异常",
                    "raw_response": json.dumps(result)
                }
                
            # 合并所有文本部分
            parts = candidate["content"]["parts"]
            response_text = "".join(
                part.get("text", "") for part in parts if "text" in part
            ).strip()
            
            if not response_text:
                return {
                    "success": False,
                    "error": "Gemini响应中没有文本内容",
                    "raw_response": json.dumps(result)
                }
                
            # 解析响应
            parsed_result = ResponseParser.parse_gemini_response(response_text)
            
            return {
                "success": True,
                "raw_response": response_text,
                "processed_result": parsed_result.get("processed_result", {}),
                "result": parsed_result.get("result", {})
            }
            
        except Exception as e:
            logger.error(f"Gemini API处理失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Gemini处理失败: {str(e)}"
            }
    
    def _test_connection(self) -> Dict[str, Union[bool, str]]:
        """
        测试连接
        
        测试与Google Gemini API的连接是否正常。
        
        Returns:
            测试结果字典
        """
        # 准备请求头
        headers = {
            "Content-Type": "application/json"
        }
        
        # 获取模型信息
        endpoint = f"models?key={self.api_key}"
        
        try:
            # 发送请求
            response = self._make_request(
                method="GET",
                endpoint=endpoint,
                headers=headers
            )
            
            # 解析响应
            result = response.json()
            
            if "models" in result:
                models = result["models"]
                model_names = [m.get("name", "").split("/")[-1] for m in models if "name" in m]
                
                logger.info(f"Google Gemini连接测试成功，可用模型: {', '.join(model_names[:3])}等")
                return {
                    "success": True,
                    "status": "success",
                    "message": f"连接成功，可用模型: {len(model_names)}个",
                    "models": model_names
                }
            else:
                logger.warning("Google Gemini连接测试成功，但响应格式异常")
                return {
                    "success": True,
                    "status": "warning",
                    "message": "连接成功，但响应格式异常"
                }
                
        except Exception as e:
            logger.error(f"Google Gemini连接测试失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "status": "error",
                "message": f"连接测试失败: {str(e)}"
            }