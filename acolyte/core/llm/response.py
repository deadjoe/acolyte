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

        优先使用JSON解析方式提取评分，如果失败则使用正则表达式匹配。

        Args:
            text: 响应文本

        Returns:
            包含评分的字典
        """
        logger.info(f"开始从文本中提取评分, 文本长度: {len(text)}字符")
        logger.info(f"提取评分策略: 优先使用JSON解析，备用正则表达式匹配")

        # 初始化结果字典
        scores = {
            "bias_index": None,
            "misleading_index": None,
            "hidden_intent_index": None,
            "credibility_score": None
        }

        # 1. 首先尝试使用JSON解析方式提取评分
        json_scores = ResponseParser._extract_json_scores(text)
        if json_scores:
            logger.info("成功使用JSON解析方式提取评分")
            for key, value in json_scores.items():
                if value is not None:
                    scores[key] = value

            # 检查是否所有评分都已提取
            all_scores_extracted = all(scores.values())
            if all_scores_extracted:
                logger.info("已成功提取所有评分")
                return scores

        # 2. 如果JSON解析失败或不完整，尝试使用正则表达式匹配
        logger.info("尝试使用正则表达式匹配提取评分")
        regex_scores = ResponseParser._extract_regex_scores(text)
        if regex_scores:
            logger.info("成功使用正则表达式匹配提取评分")
            for key, value in regex_scores.items():
                if scores.get(key) is None and value is not None:
                    scores[key] = value

        # 3. 记录最终结果
        extracted_keys = [k for k, v in scores.items() if v is not None]
        missing_keys = [k for k, v in scores.items() if v is None]
        
        if extracted_keys:
            logger.info(f"成功提取的评分: {', '.join(extracted_keys)}")
        if missing_keys:
            logger.warning(f"未能提取的评分: {', '.join(missing_keys)}")

        return scores

    @staticmethod
    def _extract_json_scores(text: str) -> Optional[Dict[str, float]]:
        """
        从文本中提取JSON格式的评分

        优先从"6. 量化评分"章节中提取JSON格式的评分数据，支持新版本prompt中定义的JSON结构。

        Args:
            text: 响应文本

        Returns:
            包含评分的字典，如果未找到则返回None
        """
        logger.info("开始从文本中提取JSON格式的评分数据")
        
        # 1. 找到"6. 量化评分"章节
        section_pattern = r"(?:6\.|六、|6\.\s*量化评分|量化评分)[\s\S]*?(?:7\.|七、|7\.\s*分析局限|分析局限|$)"
        section_match = re.search(section_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if not section_match:
            logger.warning("未找到量化评分章节")
            return None
        
        section_text = section_match.group(0)
        logger.debug(f"找到量化评分章节，长度: {len(section_text)} 字符")
        
        # 2. 尝试从代码块中提取JSON
        code_block_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        code_match = re.search(code_block_pattern, section_text, re.DOTALL)
        
        json_str = None
        if code_match:
            code_content = code_match.group(1).strip()
            # 确保内容以{开始，}结束，这是有效JSON的基本要求
            if code_content.startswith('{') and code_content.endswith('}'):
                json_str = code_content
                logger.debug("从代码块中提取到JSON")
            else:
                logger.warning("代码块内容不是有效的JSON对象")
        
        # 3. 如果没有找到代码块中的JSON，尝试直接提取JSON对象
        if not json_str:
            logger.debug("未从代码块中找到JSON，尝试直接提取JSON对象")
            
            # 找到第一个左花括号
            open_brace_index = section_text.find('{')
            if open_brace_index == -1:
                logger.warning("未找到JSON对象的开始标记 '{'")
                return None
            
            # 使用括号匹配算法找到匹配的右花括号
            brace_count = 0
            for i in range(open_brace_index, len(section_text)):
                if section_text[i] == '{':
                    brace_count += 1
                elif section_text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # 找到匹配的右花括号
                        json_str = section_text[open_brace_index:i+1]
                        logger.debug(f"直接提取到JSON对象，长度: {len(json_str)} 字符")
                        break
            
            if brace_count != 0:
                logger.warning("JSON对象不完整，花括号不匹配")
                return None
        
        # 4. 解析JSON并提取评分
        if json_str:
            try:
                data = json.loads(json_str)
                logger.debug(f"成功解析JSON数据: {json.dumps(data, ensure_ascii=False)[:100]}...")
                
                # 处理JSON数据
                result = {}
                field_mappings = {
                    "偏见指数": "bias_index",
                    "误导性指数": "misleading_index",
                    "隐藏意图指数": "hidden_intent_index",
                    "综合可信度": "credibility_score"
                }
                
                for zh_key, en_key in field_mappings.items():
                    try:
                        # 尝试提取嵌套结构: {"偏见指数": {"分数": 4.0}}
                        if zh_key in data and isinstance(data[zh_key], dict) and "分数" in data[zh_key]:
                            score_value = data[zh_key]["分数"]
                            result[en_key] = float(score_value)
                            logger.debug(f"从嵌套JSON结构提取{en_key}: {result[en_key]}")
                        # 尝试提取直接结构: {"偏见指数": 4.0}
                        elif zh_key in data and isinstance(data[zh_key], (int, float)):
                            result[en_key] = float(data[zh_key])
                            logger.debug(f"从直接JSON结构提取{en_key}: {result[en_key]}")
                        else:
                            logger.debug(f"未找到{en_key}对应的JSON字段")
                    except (KeyError, TypeError, ValueError) as e:
                        logger.warning(f"从JSON格式提取{zh_key}时出错: {str(e)}")
                
                # 最终验证
                required_keys = ["bias_index", "misleading_index", "hidden_intent_index", "credibility_score"]
                missing = [k for k in required_keys if k not in result]
                if missing:
                    logger.warning(f"JSON数据中缺少必要字段: {', '.join(missing)}")
                    logger.debug(f"成功提取的字段: {', '.join(result.keys())}")
                
                if len(result) >= 3:  # 允许一个字段缺失
                    logger.info("成功从JSON格式提取评分数据")
                    return result
                else:
                    logger.warning("JSON数据中关键字段不足")
                    return None
                    
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析失败: {str(e)}")
                logger.debug(f"尝试解析的JSON字符串: {json_str[:100]}...")
                return None
            except Exception as e:
                logger.warning(f"处理JSON数据时出错: {str(e)}")
                return None
        
        logger.warning("未能从文本中提取JSON格式的评分数据")
        return None

    @staticmethod
    def _extract_regex_scores(text: str) -> Dict[str, float]:
        """
        使用正则表达式从文本中提取评分

        Args:
            text: 响应文本

        Returns:
            包含评分的字典
        """
        logger.debug("使用正则表达式提取评分")
        
        scores = {
            "bias_index": None,
            "misleading_index": None,
            "hidden_intent_index": None,
            "credibility_score": None
        }
        
        # 偏见指数 (BI): 4.0
        bi_pattern = r"(?:偏见指数|Bias Index|BI)[：:]\s*(\d+(?:\.\d+)?)"
        bi_match = re.search(bi_pattern, text, re.IGNORECASE)
        if bi_match:
            try:
                scores["bias_index"] = float(bi_match.group(1))
                logger.debug(f"提取到偏见指数: {scores['bias_index']}")
            except (ValueError, IndexError):
                logger.warning("提取偏见指数时出错")
        
        # 误导性指数 (MI): 3.4
        mi_pattern = r"(?:误导性指数|Misleading Index|MI)[：:]\s*(\d+(?:\.\d+)?)"
        mi_match = re.search(mi_pattern, text, re.IGNORECASE)
        if mi_match:
            try:
                scores["misleading_index"] = float(mi_match.group(1))
                logger.debug(f"提取到误导性指数: {scores['misleading_index']}")
            except (ValueError, IndexError):
                logger.warning("提取误导性指数时出错")
        
        # 隐藏意图指数 (HI): 3.3
        hi_pattern = r"(?:隐藏意图指数|Hidden Intent Index|HI)[：:]\s*(\d+(?:\.\d+)?)"
        hi_match = re.search(hi_pattern, text, re.IGNORECASE)
        if hi_match:
            try:
                scores["hidden_intent_index"] = float(hi_match.group(1))
                logger.debug(f"提取到隐藏意图指数: {scores['hidden_intent_index']}")
            except (ValueError, IndexError):
                logger.warning("提取隐藏意图指数时出错")
        
        # 综合可信度 (CS): 66.1
        cs_pattern = r"(?:综合可信度|Credibility Score|CS)[：:]\s*(\d+(?:\.\d+)?)"
        cs_match = re.search(cs_pattern, text, re.IGNORECASE)
        if cs_match:
            try:
                scores["credibility_score"] = float(cs_match.group(1))
                logger.debug(f"提取到综合可信度: {scores['credibility_score']}")
            except (ValueError, IndexError):
                logger.warning("提取综合可信度时出错")
        
        return scores

    @staticmethod
    def extract_structured_content(text: str, expected_sections: List[str]) -> Dict[str, str]:
        """
        从文本中提取结构化内容

        Args:
            text: 响应文本
            expected_sections: 预期的章节列表

        Returns:
            包含结构化内容的字典
        """
        logger.debug(f"开始提取结构化内容, 预期章节: {expected_sections}")
        
        sections = {}
        
        # 构建动态正则表达式，匹配Markdown章节
        for i, section in enumerate(expected_sections):
            # 构建模式：查找当前章节标题，直到下一个章节标题或文档结束
            pattern = fr"#+\s*{re.escape(section)}\s*\n+(.+?)"
            
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
                alt_pattern = fr"{re.escape(section)}[：:]\s*(.+?)(?={re.escape(expected_sections[i+1]) if i < len(expected_sections) - 1 else '$'})"
                match = re.search(alt_pattern, text, re.DOTALL)
                if match:
                    content = match.group(1).strip()
                    sections[section] = content
                else:
                    logger.debug(f"未找到章节: {section}")
        
        logger.debug(f"提取到 {len(sections)} 个章节")
        return sections

    @staticmethod
    def extract_limitations(text: str) -> List[str]:
        """
        从文本中提取分析局限性

        Args:
            text: 响应文本

        Returns:
            分析局限性列表
        """
        logger.debug("开始提取分析局限性")
        
        # 查找分析局限性章节
        section_pattern = r"(?:7\.|七、|7\.\s*分析局限|分析局限)[^\n]*\n+([\s\S]*?)(?:$|(?:\d+\.|[一二三四五六七八九十]+、))"
        match = re.search(section_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if not match:
            logger.debug("未找到分析局限性章节")
            return []
        
        section_text = match.group(1).strip()
        logger.debug(f"找到分析局限性章节，长度: {len(section_text)} 字符")
        
        # 提取列表项
        limitations = []
        
        # 尝试匹配Markdown列表项
        list_items = re.findall(r"(?:[-•*]\s*|\d+\.\s*)(.+?)(?=(?:[-•*]|\d+\.)\s*|$)", section_text, re.DOTALL)
        
        if list_items:
            limitations = [item.strip() for item in list_items if item.strip()]
        else:
            # 如果没有找到列表项，尝试按行分割
            lines = [line.strip() for line in section_text.split('\n') if line.strip()]
            limitations = lines
        
        logger.debug(f"提取到 {len(limitations)} 个分析局限性")
        return limitations

    @staticmethod
    def parse_base_response(text: str) -> Dict[str, Any]:
        """
        基础响应解析方法，适用于所有LLM

        这是一个通用的解析方法，提取评分和结构化内容。
        特定LLM的解析方法可以调用这个方法，然后添加自己的特定逻辑。

        Args:
            text: 响应文本

        Returns:
            解析后的结果字典
        """
        logger.info(f"开始基础响应解析, 文本长度: {len(text)}字符")
        
        # 提取评分
        scores = ResponseParser.extract_scores(text)
        
        # 提取结构化内容
        expected_sections = [
            "分析前背景总结", "Background Summary",
            "偏见检测发现", "Bias Detection Findings",
            "误导性内容检测", "Misleading Content Detection",
            "隐藏意图检测", "Hidden Intent Detection",
            "整体评估", "Overall Assessment",
            "量化评分", "Quantitative Scoring",
            "分析局限与不确定性", "Analysis Limitations"
        ]
        
        sections = ResponseParser.extract_structured_content(text, expected_sections)
        
        # 提取分析局限性
        limitations = ResponseParser.extract_limitations(text)
        
        # 合并结果
        result = {
            "bias_index": scores.get("bias_index"),
            "misleading_index": scores.get("misleading_index"),
            "hidden_intent_index": scores.get("hidden_intent_index"),
            "credibility_score": scores.get("credibility_score"),
            "raw_response": text,
            "processed_result": sections,
            "limitations": limitations
        }
        
        logger.info("基础响应解析完成")
        return result

    @staticmethod
    def parse_response(text: str) -> Dict[str, Any]:
        """
        通用响应解析方法

        这是一个便捷方法，直接调用基础响应解析方法。
        当不确定使用哪个特定LLM的解析方法时，可以使用这个方法。

        Args:
            text: 响应文本

        Returns:
            解析后的结果字典
        """
        logger.info("使用通用响应解析方法")
        return ResponseParser.parse_base_response(text)

    @staticmethod
    def parse_anthropic_response(text: str) -> Dict[str, Any]:
        """
        解析Anthropic Claude响应

        Args:
            text: 响应文本

        Returns:
            解析后的结果字典
        """
        logger.info("开始解析Anthropic Claude响应")
        result = ResponseParser.parse_base_response(text)
        
        # 这里可以添加Anthropic特定的解析逻辑
        
        logger.info("Anthropic Claude响应解析完成")
        return result

    @staticmethod
    def parse_openai_response(text: str) -> Dict[str, Any]:
        """
        解析OpenAI GPT响应

        Args:
            text: 响应文本

        Returns:
            解析后的结果字典
        """
        logger.info("开始解析OpenAI GPT响应")
        result = ResponseParser.parse_base_response(text)
        
        # 这里可以添加OpenAI特定的解析逻辑
        
        logger.info("OpenAI GPT响应解析完成")
        return result

    @staticmethod
    def parse_gemini_response(text: str) -> Dict[str, Any]:
        """
        解析Google Gemini响应

        Args:
            text: 响应文本

        Returns:
            解析后的结果字典
        """
        logger.info("开始解析Google Gemini响应")
        result = ResponseParser.parse_base_response(text)
        
        # 这里可以添加Gemini特定的解析逻辑
        
        logger.info("Google Gemini响应解析完成")
        return result

    @staticmethod
    def parse_deepseek_response(text: str) -> Dict[str, Any]:
        """
        解析DeepSeek响应

        Args:
            text: 响应文本

        Returns:
            解析后的结果字典
        """
        logger.info("开始解析DeepSeek响应")
        result = ResponseParser.parse_base_response(text)
        
        # 这里可以添加DeepSeek特定的解析逻辑
        
        logger.info("DeepSeek响应解析完成")
        return result

    @staticmethod
    def parse_ollama_response(text: str) -> Dict[str, Any]:
        """
        解析Ollama响应

        Args:
            text: 响应文本

        Returns:
            解析后的结果字典
        """
        logger.info("开始解析Ollama响应")
        result = ResponseParser.parse_base_response(text)
        
        # 这里可以添加Ollama特定的解析逻辑
        
        logger.info("Ollama响应解析完成")
        return result


class ErrorHandler:
    """错误处理器"""

    @staticmethod
    def format_error(error: Exception) -> Dict[str, Any]:
        """
        格式化错误信息

        Args:
            error: 异常对象

        Returns:
            格式化后的错误信息字典
        """
        return {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_details": getattr(error, "details", None)
        }

    @staticmethod
    def handle_api_error(error: Exception) -> Dict[str, Any]:
        """
        处理API错误

        Args:
            error: 异常对象

        Returns:
            处理后的错误信息字典
        """
        error_info = ErrorHandler.format_error(error)
        
        # 添加API错误特定的处理逻辑
        if hasattr(error, "status_code"):
            error_info["status_code"] = getattr(error, "status_code")
        
        return error_info

    @staticmethod
    def handle_parsing_error(error: Exception, text: str) -> Dict[str, Any]:
        """
        处理解析错误

        Args:
            error: 异常对象
            text: 原始文本

        Returns:
            处理后的错误信息字典
        """
        error_info = ErrorHandler.format_error(error)
        
        # 添加解析错误特定的处理逻辑
        error_info["text_length"] = len(text)
        error_info["text_preview"] = text[:100] + "..." if len(text) > 100 else text
        
        return error_info
