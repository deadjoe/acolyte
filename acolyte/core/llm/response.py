"""
LLM响应处理

提供处理LLM响应的工具类和函数，包括解析、错误处理等。
"""
import json
import re
from typing import Any, Dict, List, Optional, Union

from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class ResponseParser:
    """
    响应解析器

    提供解析LLM响应的方法，支持多种格式和解析策略。
    负责从文本中提取评分和结构化内容，使用多种策略确保提取的可靠性。

    主要功能：
    1. 提取评分（偏见指数、误导性指数、隐藏意图指数、综合可信度）
    2. 提取结构化内容（背景、发现、评估等）
    3. 提供多种提取策略，适应不同的响应格式
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
        logger.debug(f"提取评分策略: 使用多种模式匹配尝试提取偏见指数、误导性指数、隐藏意图指数和综合可信度分数")

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
            (r"偏见指数|Bias Index|BI|加权BI", "bias_index"),
            (r"误导性指数|Misleading Index|MI|加权MI", "misleading_index"),
            (r"隐藏意图指数|Hidden Intent Index|HI|加权HI", "hidden_intent_index"),
            (r"可信度分数|Credibility Score|CS", "credibility_score")
        ]:
            # 标准格式: 偏见指数/Bias Index: 7.5
            pattern = fr"(?:{score_name}):\s*(\d+(?:\.\d+)?)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scores[key] = float(match.group(1))
                logger.debug(f"标准格式成功提取{key}: {scores[key]}")
                continue

            # 备用格式1: 偏见指数/Bias Index - 7.5
            pattern = fr"(?:{score_name})\s*-\s*(\d+(?:\.\d+)?)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scores[key] = float(match.group(1))
                logger.debug(f"备用格式1成功提取{key}: {scores[key]}")
                continue

            # 备用格式2: 偏见指数/Bias Index: 7.5/10
            pattern = fr"(?:{score_name}):\s*(\d+(?:\.\d+)?)/10"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scores[key] = float(match.group(1))
                logger.debug(f"备用格式2成功提取{key}: {scores[key]}")
                continue

            # 备用格式3: 偏见指数/Bias Index（7.5/10）
            pattern = fr"(?:{score_name})[（(]\s*(\d+(?:\.\d+)?)/10[）)]"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scores[key] = float(match.group(1))
                logger.debug(f"备用格式3成功提取{key}: {scores[key]}")
                continue

            # 备用格式4: 加权BI = 5.95
            pattern = fr"(?:{score_name})\s*=\s*(\d+(?:\.\d+)?)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scores[key] = float(match.group(1))
                logger.debug(f"备用格式4成功提取{key}: {scores[key]}")
                continue

            # 处理特殊格式的综合可信度，如"100 - 53.5"
            if key == "credibility_score":
                # 尝试匹配"100 - X"格式
                pattern = fr"(?:{score_name}).*?100\s*-\s*(\d+(?:\.\d+)?)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        # 计算100减去匹配的值
                        value = float(match.group(1))
                        scores[key] = 100 - value
                        logger.debug(f"特殊格式'100 - X'成功提取{key}: 100 - {value} = {scores[key]}")
                        continue
                    except (ValueError, TypeError) as e:
                        logger.warning(f"解析特殊格式的综合可信度失败: {str(e)}")

                # 尝试匹配计算表达式格式: "CS = 100 - [(BI + MI + HI) × 10 / 3]"
                pattern = fr"(?:{score_name}).*?=\s*100\s*-\s*\[.*?\]\s*=\s*(\d+(?:\.\d+)?)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        scores[key] = float(match.group(1))
                        logger.debug(f"计算表达式格式成功提取{key}: {scores[key]}")
                        continue
                    except (ValueError, TypeError) as e:
                        logger.warning(f"解析计算表达式格式的综合可信度失败: {str(e)}")

                # 直接在文本中搜索“最终CS = ”模式
                # 匹配格式：最终CS = 56.17
                pattern = fr"最终\s*CS\s*=\s*(\d+(?:\.\d+)?)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        scores[key] = float(match.group(1))
                        logger.debug(f"最终CS格式成功提取{key}: {scores[key]}")
                        continue
                    except (ValueError, TypeError) as e:
                        logger.warning(f"解析最终CS格式的综合可信度失败: {str(e)}")

                # 匹配格式：最终CS = 100 - 43.83 = 56.17
                pattern = fr"最终\s*CS\s*=\s*\d+\s*-\s*\d+(?:\.\d+)?\s*=\s*(\d+(?:\.\d+)?)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        scores[key] = float(match.group(1))
                        logger.debug(f"最终CS计算格式成功提取{key}: {scores[key]}")
                        continue
                    except (ValueError, TypeError) as e:
                        logger.warning(f"解析最终CS计算格式的综合可信度失败: {str(e)}")

        # 记录提取结果
        found = sum(1 for v in scores.values() if v is not None)
        missing = [k for k, v in scores.items() if v is None]

        # 记录当前提取到的评分
        for key, value in scores.items():
            if value is not None:
                logger.debug(f"成功提取{key}: {value}")

        if found == 4:
            logger.info("成功提取所有评分")
        else:
            logger.warning(f"只提取了 {found}/4 个评分，缺少: {', '.join(missing)}")

            # 记录文本中包含的关键词
            keywords = ["偏见指数", "Bias Index", "BI",
                       "误导性指数", "Misleading Index", "MI",
                       "隐藏意图指数", "Hidden Intent Index", "HI",
                       "可信度分数", "Credibility Score", "CS", "最终CS"]

            for keyword in keywords:
                if keyword in text:
                    logger.debug(f"文本中包含关键词: {keyword}")

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
    def parse_response(text: str) -> Dict[str, Any]:
        """
        解析LLM响应，提取评分和结构化内容

        这是一个综合方法，它使用extract_scores和其他辅助方法来提取所有需要的信息。

        Args:
            text: 响应文本

        Returns:
            包含评分和结构化内容的字典
        """
        logger.debug(f"开始解析LLM响应, 文本长度: {len(text)}字符")
        logger.debug(f"解析策略: 首先提取评分，然后提取结构化内容")

        # 提取评分
        scores = ResponseParser.extract_scores(text)

        # 初始化结果字典
        result = {
            "bias_index": scores.get("bias_index"),
            "misleading_index": scores.get("misleading_index"),
            "hidden_intent_index": scores.get("hidden_intent_index"),
            "credibility_score": scores.get("credibility_score"),
            "analysis": {
                "background": None,
                "bias_findings": [],
                "misleading_findings": [],
                "hidden_intent_findings": [],
                "overall_assessment": None,
                "credibility_classification": None,
                "limitations": []
            }
        }

        # 提取分析前背景部分
        background = ResponseParser._extract_section(text,
            ["分析前背景", "背景总结", "Background"],
            ["偏见检测", "误导性内容", "隐藏意图"])
        if background:
            result["analysis"]["background"] = background.strip()
            logger.debug(f"成功提取分析前背景部分, 长度: {len(background)}字符")
        else:
            logger.warning("未找到分析前背景部分")

        # 提取偏见检测发现部分
        bias_findings = ResponseParser._extract_findings(text,
            ["偏见检测发现", "Bias Findings"],
            ["误导性内容检测", "隐藏意图检测"])
        if bias_findings:
            result["analysis"]["bias_findings"] = bias_findings
            logger.debug(f"成功提取偏见检测发现, 数量: {len(bias_findings)}项")
        else:
            logger.warning("未找到偏见检测发现部分")

        # 提取误导性内容检测部分
        misleading_findings = ResponseParser._extract_findings(text,
            ["误导性内容检测", "Misleading Content"],
            ["隐藏意图检测", "整体评估"])
        if misleading_findings:
            result["analysis"]["misleading_findings"] = misleading_findings
            logger.debug(f"成功提取误导性内容检测, 数量: {len(misleading_findings)}项")
        else:
            logger.warning("未找到误导性内容检测部分")

        # 提取隐藏意图检测部分
        hidden_intent_findings = ResponseParser._extract_findings(text,
            ["隐藏意图检测", "Hidden Intent"],
            ["整体评估", "量化评分"])
        if hidden_intent_findings:
            result["analysis"]["hidden_intent_findings"] = hidden_intent_findings
            logger.debug(f"成功提取隐藏意图检测, 数量: {len(hidden_intent_findings)}项")
        else:
            logger.warning("未找到隐藏意图检测部分")

        # 提取整体评估部分
        overall_assessment = ResponseParser._extract_section(text,
            ["整体评估", "Overall Assessment"],
            ["量化评分", "可信度分类", "分析局限"])
        if overall_assessment:
            result["analysis"]["overall_assessment"] = overall_assessment.strip()
            logger.debug(f"成功提取整体评估部分, 长度: {len(overall_assessment)}字符")
        else:
            logger.warning("未找到整体评估部分")

        # 提取可信度分类
        credibility_classification = ResponseParser._extract_credibility_classification(text)
        if credibility_classification:
            result["analysis"]["credibility_classification"] = credibility_classification
            logger.debug(f"成功提取可信度分类: {credibility_classification}")
        else:
            logger.warning("未找到可信度分类标记")

        # 提取分析局限与不确定性部分
        limitations = ResponseParser._extract_limitations(text)
        if limitations:
            result["analysis"]["limitations"] = limitations
            logger.debug(f"成功提取分析局限项, 数量: {len(limitations)}项")
        else:
            logger.warning("未找到分析局限与不确定性部分")

        return result

    @staticmethod
    def _extract_section(text: str, section_markers: List[str], end_markers: List[str]) -> Optional[str]:
        """
        从文本中提取特定章节

        Args:
            text: 响应文本
            section_markers: 章节开始标记列表
            end_markers: 章节结束标记列表

        Returns:
            提取到的章节内容，如果未找到则返回None
        """
        # 将文本按行分割
        lines = text.split('\n')

        # 初始化变量
        section_start = -1
        section_end = len(lines)
        section_content = None

        # 查找章节开始
        for i, line in enumerate(lines):
            for marker in section_markers:
                if marker in line:
                    section_start = i + 1  # 从下一行开始
                    break
            if section_start > -1:
                break

        # 如果找到了章节开始，查找章节结束
        if section_start > -1:
            for i in range(section_start, len(lines)):
                for marker in end_markers:
                    if marker in lines[i]:
                        section_end = i
                        break
                if section_end < len(lines):
                    break

            # 提取章节内容
            section_content = '\n'.join(lines[section_start:section_end])

        return section_content

    @staticmethod
    def _extract_findings(text: str, section_markers: List[str], end_markers: List[str]) -> List[Dict[str, str]]:
        """
        从文本中提取发现项

        Args:
            text: 响应文本
            section_markers: 章节开始标记列表
            end_markers: 章节结束标记列表

        Returns:
            发现项列表，每个发现项是一个字典，包含标题和描述
        """
        # 提取章节内容
        section_content = ResponseParser._extract_section(text, section_markers, end_markers)
        if not section_content:
            return []

        # 尝试提取发现项
        findings = []

        # 尝试使用标题和描述格式提取
        pattern = r"\s*([^\n]+)\s*\n\s*(.+?)(?=\n\s*\n|$)"
        matches = re.findall(pattern, section_content, re.DOTALL)

        if matches:
            for title, description in matches:
                findings.append({
                    "title": title.strip(),
                    "description": description.strip()
                })
        else:
            # 如果没有找到标准格式，尝试按段落分割
            paragraphs = re.split(r"\n\s*\n", section_content)
            for paragraph in paragraphs:
                if paragraph.strip():
                    findings.append({
                        "title": "",
                        "description": paragraph.strip()
                    })

        return findings

    @staticmethod
    def _extract_credibility_classification(text: str) -> Optional[str]:
        """
        从文本中提取可信度分类

        Args:
            text: 响应文本

        Returns:
            可信度分类，如果未找到则返回None
        """
        # 尝试匹配可信度分类
        patterns = [
            r"可信度分类\s*[:\uff1a]\s*([^\n]+)",
            r"可信度分类[^\n]*?([\u4e00-\u9fa5]+\u53ef信度)",
            r"Credibility Classification\s*[:\uff1a]\s*([^\n]+)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    @staticmethod
    def _extract_limitations(text: str) -> List[str]:
        """
        从文本中提取分析局限项

        Args:
            text: 响应文本

        Returns:
            分析局限项列表
        """
        # 提取分析局限与不确定性部分
        section_content = ResponseParser._extract_section(text,
            ["分析局限", "不确定性", "Limitations"],
            [])
        if not section_content:
            return []

        # 尝试提取列表项
        limitations = []

        # 尝试匹配列表项
        patterns = [
            r"[\u3010\u3011\[\]\u3008\u3009\u300a\u300b\u300c\u300d\u300e\u300f\u3010\u3011\u3014\u3015\u3016\u3017\u3018\u3019\u301a\u301b\u301c\u301d\u301e\u301f\u3008\u3009]([^\n]+)[\u3010\u3011\[\]\u3008\u3009\u300a\u300b\u300c\u300d\u300e\u300f\u3010\u3011\u3014\u3015\u3016\u3017\u3018\u3019\u301a\u301b\u301c\u301d\u301e\u301f\u3008\u3009]",
            r"[\u2022\u2023\u25e6\u2043\u2219\u2981\u2b25\u2b26\u2b27\u2b28\u2b29]\s*([^\n]+)",
            r"[\-\*\+]\s+([^\n]+)"
        ]

        for pattern in patterns:
            matches = re.findall(pattern, section_content)
            if matches:
                for match in matches:
                    limitations.append(match.strip())
                break

        # 如果没有找到列表项，尝试按段落分割
        if not limitations:
            paragraphs = re.split(r"\n\s*\n", section_content)
            for paragraph in paragraphs:
                if paragraph.strip():
                    limitations.append(paragraph.strip())

        return limitations

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