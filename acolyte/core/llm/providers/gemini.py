"""
Google Gemini客户端

Google Gemini API的客户端实现。
"""
import json
from typing import Any, Dict, Union

import httpx

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
    async def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """
        处理内容

        Args:
            content: 要处理的内容
            prompt: 提示模板

        Returns:
            处理结果字典
        """
        logger.info(f"使用Google Gemini处理内容: 模型={self.model_name}, 内容长度={len(content)}字符")

        # 检查API密钥
        if not self._check_api_key():
            logger.error("Google Gemini API密钥未设置")
            return {
                "success": False,
                "error": "Google Gemini API密钥未设置"
            }

        # 准备完整提示词
        system_prompt = "你是一个专业的内容分析员，专注于检测文本中的偏见、误导性信息和隐藏意图。"
        user_prompt = self._prepare_prompt(content, prompt)
        logger.debug(f"最终提示词长度: {len(user_prompt)}字符")

        return await self._process_with_gemini_api(system_prompt, user_prompt)

    async def _process_with_gemini_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        使用Gemini API处理内容

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词

        Returns:
            处理结果字典
        """
        logger.debug("使用Google Gemini API")

        # 准备请求参数 - 使用最新的Gemini API格式
        # 根据Gemini官方REST示例更新请求格式
        data = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": f"{system_prompt}\n\n{user_prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 4000,
                "topP": 0.95,
                "topK": 40,
                "responseMimeType": "text/plain"
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]
        }

        logger.debug(f"Gemini API请求数据: {json.dumps(data, ensure_ascii=False)[:500]}...")

        logger.debug(f"Gemini API请求参数: system_prompt长度={len(system_prompt)}字符, user_prompt长度={len(user_prompt)}字符")

        # 准备请求头
        headers = {
            "Content-Type": "application/json"
        }

        # 根据Gemini官方REST示例更新API端点格式
        # 使用v1beta路径和generateContent操作
        endpoint = f"{self.full_model_name}:generateContent?key={self.api_key}"

        try:
            # 使用异步方式发送请求，与OpenAI和Claude保持一致
            # 发送请求
            response = await self._make_request(
                method="POST",
                endpoint=endpoint,
                headers=headers,
                json_data=data,
                timeout=120.0  # 较长的超时时间
            )

            # 解析响应
            try:
                result = response.json()
                logger.debug(f"Gemini API响应状态码: {response.status_code}")
                logger.debug(f"Gemini API响应内容类型: {response.headers.get('Content-Type', '未知')}")
                logger.debug(f"Gemini API响应内容长度: {len(response.text)}字符")
                logger.debug(f"Gemini API响应JSON键: {list(result.keys()) if isinstance(result, dict) else '非字典'}")
            except json.JSONDecodeError as e:
                logger.error(f"Gemini API响应不是有效的JSON: {str(e)}")
                logger.debug(f"响应内容: {response.text[:500]}...")
                return {
                    "success": False,
                    "error": f"Gemini响应不是有效的JSON: {str(e)}",
                    "raw_response": response.text
                }

            # 检查响应中是否有错误信息
            if "error" in result:
                error_info = result["error"]
                error_message = error_info.get("message", "未知错误")
                error_code = error_info.get("code", 0)
                error_status = error_info.get("status", "")
                error_details = error_info.get("details", [])

                # 记录详细错误信息
                logger.error(f"Gemini API返回错误: 代码={error_code}, 状态={error_status}, 消息={error_message}")
                if error_details:
                    logger.error(f"Gemini API错误详情: {json.dumps(error_details, ensure_ascii=False)}")

                # 根据错误类型提供不同的错误信息
                if "API key not valid" in error_message or "API key expired" in error_message:
                    logger.error("Gemini API密钥无效或已过期")
                    return {
                        "success": False,
                        "error": "Gemini API密钥无效或已过期",
                        "raw_response": json.dumps(result)
                    }
                elif "quota exceeded" in error_message.lower() or "rate limit" in error_message.lower():
                    logger.error("Gemini API配额超限或请求频率过高")
                    return {
                        "success": False,
                        "error": "Gemini API配额超限或请求频率过高",
                        "raw_response": json.dumps(result)
                    }
                elif "model not found" in error_message.lower() or "model is not supported" in error_message.lower():
                    logger.error(f"Gemini模型不存在或不支持: {self.full_model_name}")
                    return {
                        "success": False,
                        "error": f"Gemini模型不存在或不支持: {self.full_model_name}",
                        "raw_response": json.dumps(result)
                    }
                else:
                    # 其他错误
                    return {
                        "success": False,
                        "error": f"Gemini API错误: {error_message} (代码: {error_code}, 状态: {error_status})",
                        "raw_response": json.dumps(result)
                    }

            # 检查响应中是否有内容
            # 记录完整的响应以便调试
            logger.debug(f"Gemini完整响应: {json.dumps(result, ensure_ascii=False)[:1000]}...")

            # 检查响应中是否有candidates字段
            if "candidates" not in result:
                logger.error(f"Gemini响应中没有candidates字段, 响应键: {list(result.keys())}")

                # 如果有text字段，直接使用
                if "text" in result:
                    logger.info("Gemini响应中有text字段，直接使用")
                    response_text = result["text"]
                    # 跳过后面的响应提取逻辑
                else:
                    # 检查是否有配额限制或其他隐含错误
                    if "usageMetadata" in result and "modelVersion" in result and len(result.keys()) == 2:
                        logger.error("Gemini API可能遇到了配额限制或内容过滤: 响应中只有usageMetadata和modelVersion")
                        return {
                            "success": False,
                            "error": "Gemini API可能遇到了配额限制或内容过滤",
                            "raw_response": json.dumps(result)
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Gemini响应中没有candidates字段",
                            "raw_response": json.dumps(result)
                        }

            # 如果有candidates字段，检查是否为空
            elif not result["candidates"]:
                logger.error("Gemini响应中candidates列表为空")
                return {
                    "success": False,
                    "error": "Gemini响应中candidates列表为空",
                    "raw_response": json.dumps(result)
                }

            # 初始化变量
            response_text = ""

            # 检查响应中是否有text字段，如果有则直接使用
            if "text" in result:
                logger.info("Gemini响应中有text字段，直接使用")
                response_text = result["text"]
            else:
                # 尝试使用candidates格式提取文本
                try:
                    if "candidates" not in result:
                        logger.error(f"Gemini响应中没有candidates字段, 响应键: {list(result.keys())}")
                        return {
                            "success": False,
                            "error": "Gemini响应中没有candidates字段",
                            "raw_response": json.dumps(result)
                        }

                    candidates = result["candidates"]
                    if not candidates:
                        logger.error("Gemini响应中candidates列表为空")
                        return {
                            "success": False,
                            "error": "Gemini响应中candidates列表为空",
                            "raw_response": json.dumps(result)
                        }

                    candidate = candidates[0]
                    logger.debug(f"Gemini候选项键: {list(candidate.keys()) if isinstance(candidate, dict) else '非字典'}")

                    if "content" not in candidate:
                        logger.error(f"Gemini响应中没有content字段, 候选项键: {list(candidate.keys())}")
                        return {
                            "success": False,
                            "error": "Gemini响应中没有content字段",
                            "raw_response": json.dumps(result)
                        }

                    content = candidate["content"]
                    logger.debug(f"Gemini内容键: {list(content.keys()) if isinstance(content, dict) else '非字典'}")

                    if "parts" not in content:
                        logger.error(f"Gemini响应中没有parts字段, 内容键: {list(content.keys())}")
                        return {
                            "success": False,
                            "error": "Gemini响应中没有parts字段",
                            "raw_response": json.dumps(result)
                        }

                    # 合并所有文本部分
                    parts = content["parts"]
                    logger.debug(f"Gemini parts数量: {len(parts)}")

                    for i, part in enumerate(parts):
                        if "text" in part:
                            response_text += part["text"]
                        else:
                            logger.warning(f"Gemini响应中第{i+1}个part没有text字段, 键: {list(part.keys())}")
                except Exception as e:
                    logger.error(f"Gemini响应解析异常: {str(e)}")
                    logger.debug(f"Gemini响应内容: {json.dumps(result, ensure_ascii=False)[:500]}...")
                    return {
                        "success": False,
                        "error": f"Gemini响应解析异常: {str(e)}",
                        "raw_response": json.dumps(result)
                    }

            response_text = response_text.strip()

            if not response_text:
                logger.error("Gemini响应中没有文本内容")
                return {
                    "success": False,
                    "error": "Gemini响应中没有文本内容",
                    "raw_response": json.dumps(result)
                }

            logger.info(f"成功获取Gemini响应文本, 长度: {len(response_text)}字符")
            logger.debug(f"Gemini响应文本前500字符: {response_text[:500]}...")

            # 解析响应
            parsed_result = ResponseParser.parse_gemini_response(response_text)

            # 确保即使解析失败也能返回有效的结果
            if parsed_result is None:
                parsed_result = {}

            # 将解析结果直接作为result返回，而不是嵌套在result字段中
            return {
                "success": True,
                "raw_response": response_text,
                "processed_result": {},
                "result": parsed_result
            }

        except httpx.RequestError as e:
            logger.error(f"Gemini API请求失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Gemini API请求失败: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Gemini API处理失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Gemini处理失败: {str(e)}"
            }

    @retry_on_error()
    async def _test_connection(self) -> Dict[str, Union[bool, str]]:
        """
        测试连接

        测试与Google Gemini API的连接是否正常。

        Returns:
            测试结果字典
        """
        logger.info(f"测试Google Gemini连接: 模型={self.model_name}, URL={self.base_url}")

        # 检查API密钥
        if not self._check_api_key():
            logger.error("Google Gemini API密钥未设置")
            return {
                "success": False,
                "status": "error",
                "message": "API密钥未设置"
            }

        # 准备请求头
        headers = {
            "Content-Type": "application/json"
        }

        # 获取模型信息
        endpoint = f"models?key={self.api_key}"

        try:
            # 使用异步方式发送请求，与OpenAI和Claude保持一致
            # 发送请求
            response = await self._make_request(
                method="GET",
                endpoint=endpoint,
                headers=headers,
                timeout=30.0
            )

            # 解析响应
            try:
                result = response.json()
                logger.debug(f"Gemini API测试连接响应状态码: {response.status_code}")
                logger.debug(f"Gemini API测试连接响应JSON键: {list(result.keys()) if isinstance(result, dict) else '非字典'}")
            except json.JSONDecodeError as e:
                logger.error(f"Gemini API测试连接响应不是有效的JSON: {str(e)}")
                return {
                    "success": False,
                    "status": "error",
                    "message": f"API响应不是有效的JSON: {str(e)}"
                }

            # 检查响应中是否有错误信息
            if "error" in result:
                error_info = result["error"]
                error_message = error_info.get("message", "未知错误")
                error_code = error_info.get("code", 0)
                logger.error(f"Gemini API测试连接返回错误: 代码={error_code}, 消息={error_message}")
                return {
                    "success": False,
                    "status": "error",
                    "message": f"API错误: {error_message} (代码: {error_code})"
                }

            # 检查响应中是否有模型信息
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
                logger.warning(f"Google Gemini连接测试成功，但响应中没有models字段, 响应键: {list(result.keys())}")
                return {
                    "success": True,
                    "status": "warning",
                    "message": "连接成功，但响应格式异常"
                }

        except httpx.RequestError as e:
            logger.error(f"Google Gemini连接测试失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "status": "error",
                "message": f"连接测试失败: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Google Gemini连接测试未知错误: {str(e)}", exc_info=True)
            return {
                "success": False,
                "status": "error",
                "message": f"连接测试未知错误: {str(e)}"
            }