"""
LLM响应处理

提供处理LLM响应的工具类和函数，包括解析、错误处理等。
"""
import json
import re
from typing import Dict, List, Optional, Union

from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class ResponseParser:
    """
    响应解析器

    提供解析LLM响应的方法，支持多种格式和解析策略。
    """

    @staticmethod
    def extract_scores(text: str) -> Dict[str, float]:
        """
        从文本中提取评分

        Args:
            text: 响应文本

        Returns:
            包含评分的字典
        """
        logger.debug(f"开始从文本中提取评分, 文本长度: {len(text)}字符")

        # 初始化结果字典
        scores = {
            "bias_index": None,
            "misleading_index": None,
            "hidden_intent_index": None,
            "credibility_score": None
        }

        # 尝试使用多种正则表达式模式提取分数
        # 1. 标准格式: 偏见指数/Bias Index: 7.5
        for score_name, key in [
            (r"偏见指数|Bias Index", "bias_index"),
            (r"误导性指数|Misleading Index", "misleading_index"),
            (r"隐藏意图指数|Hidden Intent Index", "hidden_intent_index"),
            (r"可信度分数|Credibility Score", "credibility_score")
        ]:
            # 标准格式
            pattern = fr"(?:{score_name}):\s*(\d+(?:\.\d+)?)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scores[key] = float(match.group(1))
                continue

            # 备用格式1: 偏见指数/Bias Index - 7.5
            pattern = fr"(?:{score_name})\s*-\s*(\d+(?:\.\d+)?)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scores[key] = float(match.group(1))
                continue

            # 备用格式2: 偏见指数/Bias Index: 7.5/10
            pattern = fr"(?:{score_name}):\s*(\d+(?:\.\d+)?)/10"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scores[key] = float(match.group(1))
                continue

            # 备用格式3: 偏见指数/Bias Index（7.5/10）
            pattern = fr"(?:{score_name})[（(]\s*(\d+(?:\.\d+)?)/10[）)]"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scores[key] = float(match.group(1))
                continue

            # 处理特殊格式的综合可信度，如"100 - 53.5"
            if key == "credibility_score":
                # 尝试匹配"100 - X"格式
                pattern = fr"(?:{score_name}).*?100\s*-\s*(\d+(?:\.\d+)?)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        # 计算100减去匹配的值
                        scores[key] = 100 - float(match.group(1))
                        continue
                    except (ValueError, TypeError) as e:
                        logger.warning(f"解析特殊格式的综合可信度失败: {str(e)}")

                # 尝试匹配计算表达式格式: "CS = 100 - [(BI + MI + HI) × 10 / 3]"
                pattern = fr"(?:{score_name}).*?=\s*100\s*-\s*\[.*?\]\s*=\s*(\d+(?:\.\d+)?)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        scores[key] = float(match.group(1))
                        continue
                    except (ValueError, TypeError) as e:
                        logger.warning(f"解析计算表达式格式的综合可信度失败: {str(e)}")

                # 直接在文本中搜索“最终CS = ”模式
                pattern = fr"最终\s*CS\s*=\s*(\d+(?:\.\d+)?)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        scores[key] = float(match.group(1))
                        continue
                    except (ValueError, TypeError) as e:
                        logger.warning(f"解析最终CS格式的综合可信度失败: {str(e)}")

        # 记录提取结果
        found = sum(1 for v in scores.values() if v is not None)
        missing = [k for k, v in scores.items() if v is None]

        if found == 4:
            logger.info("成功提取所有评分")
        else:
            logger.warning(f"只提取了 {found}/4 个评分，缺少: {', '.join(missing)}")

            # 尝试查找JSON结构
            if found < 4:
                json_scores = ResponseParser._extract_json_scores(text)
                if json_scores:
                    logger.info("从JSON结构中提取了评分")
                    # 只填充缺失的分数
                    for key in missing:
                        if key in json_scores and json_scores[key] is not None:
                            scores[key] = json_scores[key]

        return scores

    @staticmethod
    def _extract_json_scores(text: str) -> Optional[Dict[str, float]]:
        """
        从文本中提取JSON格式的评分

        Args:
            text: 响应文本

        Returns:
            包含评分的字典，如果未找到则返回None
        """
        # 尝试查找JSON代码块
        json_pattern = r"```json\s*(\{.*?\})\s*```"
        match = re.search(json_pattern, text, re.DOTALL)

        if match:
            try:
                json_str = match.group(1)
                data = json.loads(json_str)

                # 查找分数字段
                result = {}

                # 直接查找标准字段名
                for key in ["bias_index", "misleading_index", "hidden_intent_index", "credibility_score"]:
                    if key in data and isinstance(data[key], (int, float)):
                        result[key] = float(data[key])

                # 查找替代字段名（驼峰命名、下划线等）
                field_mappings = {
                    "bias_index": ["biasIndex", "bias", "biasScore"],
                    "misleading_index": ["misleadingIndex", "misleading", "misleadingScore"],
                    "hidden_intent_index": ["hiddenIntentIndex", "hiddenIntent", "intentScore"],
                    "credibility_score": ["credibilityScore", "credibility", "trustScore"]
                }

                for key, alternatives in field_mappings.items():
                    if key not in result or result[key] is None:
                        for alt in alternatives:
                            if alt in data and isinstance(data[alt], (int, float)):
                                result[key] = float(data[alt])
                                break

                if result:
                    return result

            except json.JSONDecodeError:
                logger.warning("JSON解析失败")
            except Exception as e:
                logger.warning(f"从JSON提取评分时出错: {str(e)}")

        # 如果没有找到JSON代码块，尝试在文本中查找任何JSON对象
        try:
            # 查找可能的JSON对象: {....}
            json_candidates = re.findall(r"\{[^\{\}]*\"[^\"]*\"[^\{\}]*\}", text)

            for json_str in json_candidates:
                try:
                    data = json.loads(json_str)

                    # 检查是否包含评分字段
                    result = {}
                    for key in ["bias_index", "misleading_index", "hidden_intent_index", "credibility_score"]:
                        if key in data and isinstance(data[key], (int, float)):
                            result[key] = float(data[key])

                    if result:
                        return result
                except:
                    continue
        except Exception as e:
            logger.debug(f"查找JSON对象时出错: {str(e)}")

        return None

    @staticmethod
    def extract_structured_content(text: str, expected_sections: List[str]) -> Dict[str, str]:
        """
        从文本中提取结构化内容

        Args:
            text: 响应文本
            expected_sections: 预期的章节列表

        Returns:
            包含章节内容的字典
        """
        sections = {}

        # 构建动态正则表达式，匹配Markdown章节
        for i, section in enumerate(expected_sections):
            # 构建模式：查找当前章节标题，直到下一个章节标题或文档结束
            pattern = fr"#+\s*{re.escape(section)}\s*\n+(.*?)"

            # 如果不是最后一个章节，查找到下一个章节；否则查找到文档结束
            if i < len(expected_sections) - 1:
                pattern += fr"(?=#+\s*{re.escape(expected_sections[i+1])})"
            else:
                pattern += r"(?=#+\s*|$)"

            # 提取章节内容
            match = re.search(pattern, text, re.DOTALL)
            if match:
                content = match.group(1).strip()
                sections[section] = content
            else:
                # 尝试查找没有Markdown标记的章节
                alt_pattern = fr"{re.escape(section)}[：:]\s*(.*?)(?={re.escape(expected_sections[i+1]) if i < len(expected_sections) - 1 else '$'})"
                match = re.search(alt_pattern, text, re.DOTALL)
                if match:
                    content = match.group(1).strip()
                    sections[section] = content
                else:
                    sections[section] = ""

        return sections

    @staticmethod
    def parse_anthropic_response(text: str) -> Dict[str, Union[float, str, Dict]]:
        """
        解析Anthropic Claude响应

        Args:
            text: 响应文本

        Returns:
            解析后的结果字典
        """
        # 提取评分
        scores = ResponseParser.extract_scores(text)

        # 提取结构化内容
        expected_sections = [
            "分析摘要", "Summary of Analysis",
            "偏见检测", "Bias Detection",
            "误导性内容检测", "Misleading Content Detection",
            "隐藏意图检测", "Hidden Intent Detection",
            "评分", "Scores"
        ]

        sections = ResponseParser.extract_structured_content(text, expected_sections)

        # 合并结果
        result = {
            "raw_response": text,
            "processed_result": sections,
            "result": scores
        }

        return result

    @staticmethod
    def parse_openai_response(text: str) -> Dict[str, Union[float, str, Dict]]:
        """
        解析OpenAI GPT响应

        Args:
            text: 响应文本

        Returns:
            解析后的结果字典
        """
        # OpenAI响应解析与Anthropic类似
        return ResponseParser.parse_anthropic_response(text)

    @staticmethod
    def parse_gemini_response(text: str) -> Dict[str, Union[float, str, Dict]]:
        """
        解析Google Gemini响应

        Args:
            text: 响应文本

        Returns:
            解析后的结果字典
        """
        # Gemini响应解析与Anthropic类似
        return ResponseParser.parse_anthropic_response(text)

    @staticmethod
    def parse_deepseek_response(text: str) -> Dict[str, Union[float, str, Dict]]:
        """
        解析DeepSeek响应

        Args:
            text: 响应文本

        Returns:
            解析后的结果字典
        """
        # DeepSeek响应解析与Anthropic类似
        return ResponseParser.parse_anthropic_response(text)

    @staticmethod
    def parse_ollama_response(text: str) -> Dict[str, Union[float, str, Dict]]:
        """
        解析Ollama响应

        Args:
            text: 响应文本

        Returns:
            解析后的结果字典
        """
        # Ollama响应解析与Anthropic类似
        return ResponseParser.parse_anthropic_response(text)


class ErrorHandler:
    """
    错误处理器

    提供处理LLM调用错误的方法，包括错误分类、消息格式化等。
    """

    @staticmethod
    def handle_request_error(provider: str, error: Exception) -> Dict[str, Union[bool, str]]:
        """
        处理请求错误

        Args:
            provider: 提供商名称
            error: 错误对象

        Returns:
            错误结果字典
        """
        import requests

        error_type = type(error).__name__
        error_msg = str(error)

        # 记录错误
        logger.error(f"{provider.capitalize()}请求错误: {error_type}: {error_msg}")

        # 尝试提取更多错误细节
        details = "未知错误"

        if isinstance(error, requests.RequestException):
            if error.response:
                # 尝试解析响应JSON
                try:
                    error_data = error.response.json()
                    if isinstance(error_data, dict):
                        # 提取Anthropic错误
                        if provider == "anthropic" and "error" in error_data:
                            anthropic_error = error_data["error"]
                            error_type = anthropic_error.get("type", error_type)
                            error_msg = anthropic_error.get("message", error_msg)

                        # 提取OpenAI错误
                        elif provider == "openai" and "error" in error_data:
                            openai_error = error_data["error"]
                            error_type = openai_error.get("type", error_type)
                            error_msg = openai_error.get("message", error_msg)

                        # 提取Gemini错误
                        elif provider == "gemini" and "error" in error_data:
                            gemini_error = error_data["error"]
                            error_type = gemini_error.get("status", error_type)
                            error_msg = gemini_error.get("message", error_msg)

                        # 其他提供商错误
                        else:
                            for key in ["error", "message", "description"]:
                                if key in error_data and isinstance(error_data[key], str):
                                    error_msg = error_data[key]
                                    break
                except:
                    # 如果JSON解析失败，使用响应文本
                    error_msg = error.response.text[:200] if error.response.text else error_msg

                # 提取HTTP状态码
                status_code = error.response.status_code
                details = f"{error_type} (HTTP {status_code}): {error_msg}"
            else:
                # 连接错误、超时等
                details = f"{error_type}: {error_msg}"
        else:
            # 其他类型的错误
            details = f"{error_type}: {error_msg}"

        return {
            "success": False,
            "error": details
        }

    @staticmethod
    def format_error_message(provider: str, error_type: str, error_msg: str) -> str:
        """
        格式化错误消息

        Args:
            provider: 提供商名称
            error_type: 错误类型
            error_msg: 错误消息

        Returns:
            格式化后的错误消息
        """
        return f"{provider.capitalize()} API错误 - {error_type}: {error_msg}"

    @staticmethod
    def should_retry(provider: str, status_code: int) -> bool:
        """
        判断是否应该重试请求

        Args:
            provider: 提供商名称
            status_code: HTTP状态码

        Returns:
            是否应该重试
        """
        from acolyte.core.llm.constants import MODEL_SPECIFIC_RETRY_CODES, RETRY_STATUS_CODES

        # 使用模型特定的重试码
        if provider in MODEL_SPECIFIC_RETRY_CODES:
            return status_code in MODEL_SPECIFIC_RETRY_CODES[provider]

        # 否则使用通用重试码
        return status_code in RETRY_STATUS_CODES