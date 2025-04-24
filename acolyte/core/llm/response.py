"""
LLM响应处理

提供处理LLM响应的工具类和函数，包括解析、错误处理等。
"""

import json
import re
from typing import Any, Dict, List, Optional

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

    解析策略：
    1. JSON解析：从响应中提取JSON对象，然后从中提取评分
    2. 正则表达式匹配：当JSON解析失败时，使用正则表达式匹配评分
    3. 结构化内容提取：使用正则表达式从响应中提取结构化内容

    特定提供商支持：
    提供了针对不同LLM提供商（Anthropic Claude、OpenAI GPT、Google Gemini、DeepSeek、Ollama）
    的特定解析方法，以处理各自的响应格式特点。

    错误处理：
    内置了强大的错误处理机制，即使在某些提取策略失败时，
    也会尝试其他策略，确保尽可能地提取有用信息。
    """

    @staticmethod
    def extract_scores(text: str) -> Dict[str, float]:
        """
        从文本中提取评分

        该方法使用多种策略从文本中提取评分，确保尽可能地获取完整的评分数据。
        它首先尝试使用JSON解析方式提取评分，如果失败或不完整，则使用正则表达式匹配。
        这种多策略方法可以处理不同格式的LLM响应，提高提取成功率。

        提取的评分包括：
        - bias_index (偏见指数): 0-10的浮点数，表示内容的偏见程度
        - misleading_index (误导性指数): 0-10的浮点数，表示内容的误导性程度
        - hidden_intent_index (隐藏意图指数): 0-10的浮点数，表示内容的隐藏意图程度
        - credibility_score (综合可信度): 0-100的浮点数，表示内容的总体可信度

        Args:
            text: LLM的原始响应文本，包含评分信息

        Returns:
            Dict[str, float]: 包含评分的字典，键为评分名称，值为评分数值。
                            如果某个评分无法提取，则对应的值为None。
        """
        logger.info(f"开始从文本中提取评分, 文本长度: {len(text)}字符")
        logger.info("提取评分策略: 优先使用JSON解析，备用正则表达式匹配")

        # 初始化结果字典
        scores = {
            "bias_index": None,
            "misleading_index": None,
            "hidden_intent_index": None,
            "credibility_score": None,
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

        该方法使用多种策略从文本中提取JSON格式的评分数据。
        它首先尝试定位"6. 量化评分"章节，然后从该章节中提取JSON对象。
        如果在代码块中找到JSON，则直接解析该代码块。
        如果没有找到代码块，则尝试使用括号匹配算法直接提取JSON对象。

        支持的JSON结构格式：
        1. 直接格式: {"\u504f\u89c1\u6307\u6570": 4.0, ...}
        2. 嵌套格式: {"\u504f\u89c1\u6307\u6570": {"\u5206\u6570": 4.0}, ...}

        字段映射：
        - "偏见指数" -> "bias_index"
        - "误导性指数" -> "misleading_index"
        - "隐藏意图指数" -> "hidden_intent_index"
        - "综合可信度" -> "credibility_score"

        Args:
            text: LLM的原始响应文本，包含评分信息

        Returns:
            Optional[Dict[str, float]]: 如果成功提取，返回包含评分的字典，键为标准化的评分名称，
                                    值为评分数值。如果提取失败，则返回None。
        """
        logger.info("开始从文本中提取JSON格式的评分数据")

        # 1. 找到"6. 量化评分"章节
        section_pattern = r"(?:6\.|六、|6\.\s*量化评分|量化评分)[\s\S]*?(?:<JSON_OUTPUT>[\s\S]*?</JSON_OUTPUT>)[\s\S]*?(?:7\.|七、|7\.\s*分析局限|分析局限|$)"
        section_match = re.search(section_pattern, text, re.DOTALL | re.IGNORECASE)

        if not section_match:
            logger.warning("未找到量化评分章节")
            return None

        section_text = section_match.group(0)
        logger.debug(f"找到量化评分章节，长度: {len(section_text)} 字符")
        logger.debug(f"完整的量化评分章节内容:\n{section_text}")

        # 2. 尝试从代码块中提取JSON
        code_block_pattern = r"<JSON_OUTPUT>\s*({[\s\S]*?})\s*</JSON_OUTPUT>"
        code_match = re.search(code_block_pattern, section_text, re.DOTALL)

        json_str = None
        if code_match:
            logger.debug(f"找到的JSON匹配内容:\n{code_match.group(1)}")
            code_content = code_match.group(1).strip()
            # 确保内容以{开始，}结束，这是有效JSON的基本要求
            if code_content.startswith("{") and code_content.endswith("}"):
                json_str = code_content
                logger.debug("从代码块中提取到JSON")
            else:
                logger.warning("代码块内容不是有效的JSON对象")
        # 3. 如果没有找到代码块中的JSON，尝试直接提取JSON对象
        if not json_str:
            logger.debug("未从代码块中找到JSON，尝试直接提取JSON对象")

            # 找到第一个左花括号
            open_brace_index = section_text.find("{")
            if open_brace_index == -1:
                logger.warning("未找到JSON对象的开始标记 '{'")
                return None

            # 使用括号匹配算法找到匹配的右花括号
            brace_count = 0
            for i in range(open_brace_index, len(section_text)):
                if section_text[i] == "{":
                    brace_count += 1
                elif section_text[i] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        # 找到匹配的右花括号
                        json_str = section_text[open_brace_index : i + 1]
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
                    "综合可信度": "credibility_score",
                }

                for zh_key, en_key in field_mappings.items():
                    try:
                        # 尝试提取嵌套结构: {"偏见指数": {"分数": 4.0}}
                        if (
                            zh_key in data
                            and isinstance(data[zh_key], dict)
                            and "分数" in data[zh_key]
                        ):
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
                required_keys = [
                    "bias_index",
                    "misleading_index",
                    "hidden_intent_index",
                    "credibility_score",
                ]
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

        该方法使用一系列正则表达式模式从文本中提取评分。
        它能够匹配多种常见的评分表示方式，包括中文和英文表示、缩写等。
        这是当JSON解析方式失败时的备用提取方法。

        支持的评分格式：
        - 偏见指数 (BI): 4.0
        - 误导性指数 (MI): 3.4
        - 隐藏意图指数 (HI): 3.3
        - 综合可信度 (CS): 66.1

        Args:
            text: LLM的原始响应文本，包含评分信息

        Returns:
            Dict[str, float]: 包含评分的字典，键为标准化的评分名称，值为评分数值。
                            如果某个评分无法提取，则对应的值为None。
        """
        logger.debug("使用正则表达式提取评分")

        scores = {
            "bias_index": None,
            "misleading_index": None,
            "hidden_intent_index": None,
            "credibility_score": None,
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

        该方法使用正则表达式从文本中提取结构化内容，如背景、发现、评估等章节。
        它能够识别不同格式的章节标题，如“1. 背景”、“一、背景”等。
        对于每个预期的章节，它会尝试找到对应的内容，并将其添加到结果字典中。

        提取策略：
        1. 对于每个预期章节，生成多种可能的标题格式（数字、中文数字、纯文本等）
        2. 使用正则表达式匹配这些标题格式，并提取其后的内容直到下一个章节标题
        3. 如果找不到特定章节，则在结果字典中将其值设为空字符串

        Args:
            text: LLM的原始响应文本，包含结构化内容
            expected_sections: 预期的章节列表，如["background", "findings", "evaluation"]

        Returns:
            Dict[str, str]: 包含结构化内容的字典，键为章节名称，值为章节内容。
                           如果某个章节未找到，则对应的值为空字符串。
        """
        logger.debug(f"开始提取结构化内容, 预期章节: {expected_sections}")

        sections = {}

        # 构建动态正则表达式，匹配Markdown章节
        for i, section in enumerate(expected_sections):
            # 构建模式：查找当前章节标题，直到下一个章节标题或文档结束
            pattern = rf"#+\s*{re.escape(section)}\s*\n+(.+?)"

            # 如果不是最后一个章节，查找到下一个章节；否则查找到文档结束
            if i < len(expected_sections) - 1:
                pattern += rf"(?=#+\s*{re.escape(expected_sections[i+1])})"
            else:
                pattern += r"(?=#+\s*|$)"

            # 提取章节内容
            match = re.search(pattern, text, re.DOTALL)
            if match:
                content = match.group(1).strip()
                sections[section] = content
            else:
                # 尝试查找没有Markdown标记的章节
                alt_pattern = rf"{re.escape(section)}[：:]\s*(.+?)(?={re.escape(expected_sections[i+1]) if i < len(expected_sections) - 1 else '$'})"
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

        该方法使用正则表达式从文本中提取分析局限性章节，然后将其分解为单独的条目。
        它能够识别不同格式的局限性章节标题，如“7. 分析局限性”、“七、分析局限性”等。

        提取策略：
        1. 首先尝试定位分析局限性章节
        2. 如果找到章节，则提取其内容并按照列表项分割
        3. 如果找不到章节，则返回空列表

        列表项识别：
        - 数字列表：“1. 局限性一”、“2. 局限性二”等
        - 项目符号列表：“- 局限性一”、“* 局限性二”等
        - 中文数字列表：“一、局限性一”、“二、局限性二”等

        Args:
            text: LLM的原始响应文本，包含分析局限性章节

        Returns:
            List[str]: 分析局限性列表，每个元素是一条局限性描述。
                     如果未找到局限性章节，则返回空列表。
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
        list_items = re.findall(
            r"(?:[-•*]\s*|\d+\.\s*)(.+?)(?=(?:[-•*]|\d+\.)\s*|$)", section_text, re.DOTALL
        )

        if list_items:
            limitations = [item.strip() for item in list_items if item.strip()]
        else:
            # 如果没有找到列表项，尝试按行分割
            lines = [line.strip() for line in section_text.split("\n") if line.strip()]
            limitations = lines

        logger.debug(f"提取到 {len(limitations)} 个分析局限性")
        return limitations

    @staticmethod
    def parse_base_response(text: str) -> Dict[str, Any]:
        """
        基础响应解析方法，适用于所有LLM

        这是一个通用的解析方法，提取评分和结构化内容。
        它是所有特定LLM解析方法的基础，这些方法可以调用这个方法，
        然后根据需要添加自己的特定逻辑。

        解析流程：
        1. 使用extract_scores方法提取评分
        2. 使用extract_structured_content方法提取结构化内容
        3. 使用extract_limitations方法提取分析局限性
        4. 将所有提取的信息合并到一个结果字典中

        Args:
            text: LLM的原始响应文本，包含评分和分析内容

        Returns:
            Dict[str, Any]: 解析后的结果字典，包含以下字段：
                - bias_index (float, 可选): 偏见指数
                - misleading_index (float, 可选): 误导性指数
                - hidden_intent_index (float, 可选): 隐藏意图指数
                - credibility_score (float, 可选): 综合可信度
                - raw_response (str): 原始响应文本
                - processed_result (Dict[str, str]): 结构化的处理结果，包含各个章节的内容
                - limitations (List[str]): 分析局限性列表
        """
        logger.info(f"开始基础响应解析, 文本长度: {len(text)}字符")

        # 提取评分
        scores = ResponseParser.extract_scores(text)

        # 提取结构化内容
        expected_sections = [
            "分析前背景总结",
            "Background Summary",
            "偏见检测发现",
            "Bias Detection Findings",
            "误导性内容检测",
            "Misleading Content Detection",
            "隐藏意图检测",
            "Hidden Intent Detection",
            "整体评估",
            "Overall Assessment",
            "量化评分",
            "Quantitative Scoring",
            "分析局限与不确定性",
            "Analysis Limitations",
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
            "limitations": limitations,
        }

        logger.info("基础响应解析完成")
        return result

    @staticmethod
    def parse_response(text: str) -> Dict[str, Any]:
        """
        通用响应解析方法

        这是一个便捷方法，直接调用基础响应解析方法。
        当不确定使用哪个特定LLM的解析方法时，可以使用这个方法。
        这个方法适用于所有LLM的响应，但不会应用任何特定LLM的自定义解析逻辑。

        使用场景：
        - 当不知道响应来自哪个LLM时
        - 当希望使用通用的解析逻辑而不是特定LLM的自定义逻辑时
        - 当希望对不同LLM的响应使用一致的解析方式时

        Args:
            text: LLM的原始响应文本，包含评分和分析内容

        Returns:
            Dict[str, Any]: 解析后的结果字典，包含与parse_base_response方法相同的字段

        See Also:
            parse_base_response: 基础响应解析方法，提供了详细的返回字段说明
        """
        logger.info("使用通用响应解析方法")
        return ResponseParser.parse_base_response(text)

    @staticmethod
    def parse_anthropic_response(text: str) -> Dict[str, Any]:
        """
        解析Anthropic Claude响应

        该方法专门用于解析Anthropic Claude模型的响应。
        它首先调用parse_base_response方法进行基础解析，
        然后可以根据需要添加Claude特定的解析逻辑。

        Claude模型特点：
        - 通常会生成结构良好的Markdown格式响应
        - 在量化评分部分常使用JSON格式
        - 对指令的遵循度高，通常会按照提示词模板的结构返回结果

        Args:
            text: Claude模型的原始响应文本

        Returns:
            Dict[str, Any]: 解析后的结果字典，包含与parse_base_response方法相同的字段，
                          以及可能的Claude特定字段
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

        该方法专门用于解析OpenAI GPT模型（如GPT-3.5-Turbo、GPT-4等）的响应。
        它首先调用parse_base_response方法进行基础解析，
        然后可以根据需要添加GPT特定的解析逻辑。

        GPT模型特点：
        - 很好地遵循结构化输出的指令，如JSON格式
        - 在量化评分部分通常会按照要求的格式返回
        - 对Markdown格式的支持良好，结构清晰

        Args:
            text: GPT模型的原始响应文本

        Returns:
            Dict[str, Any]: 解析后的结果字典，包含与parse_base_response方法相同的字段，
                          以及可能的GPT特定字段
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

        该方法专门用于解析Google Gemini模型（如Gemini Pro、Gemini Ultra等）的响应。
        它首先调用parse_base_response方法进行基础解析，
        然后可以根据需要添加Gemini特定的解析逻辑。

        Gemini模型特点：
        - 对结构化输出的支持良好，但有时会有细微的格式差异
        - 在量化评分部分可能使用不同的格式表示
        - 对Markdown的支持良好，但可能与OpenAI和Anthropic有细微差异

        Args:
            text: Gemini模型的原始响应文本

        Returns:
            Dict[str, Any]: 解析后的结果字典，包含与parse_base_response方法相同的字段，
                          以及可能的Gemini特定字段
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

        该方法专门用于解析DeepSeek模型（如DeepSeek-V2、DeepSeek-V3等）的响应。
        它首先调用parse_base_response方法进行基础解析，
        然后可以根据需要添加DeepSeek特定的解析逻辑。

        DeepSeek模型特点：
        - 对中文内容的理解和生成能力强
        - 在量化评分部分可能使用不同的格式表示
        - 对结构化输出的支持良好，但可能与其他模型有差异

        Args:
            text: DeepSeek模型的原始响应文本

        Returns:
            Dict[str, Any]: 解析后的结果字典，包含与parse_base_response方法相同的字段，
                          以及可能的DeepSeek特定字段
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

        该方法专门用于解析通过Ollama部署的开源模型（如Llama、Mistral等）的响应。
        它首先调用parse_base_response方法进行基础解析，
        然后可以根据需要添加Ollama特定的解析逻辑。

        Ollama模型特点：
        - 可能会有不同的响应格式，取决于具体使用的基础模型
        - 对结构化输出的支持可能不如商业模型完善
        - 可能需要更强大的错误处理和容错能力

        Args:
            text: Ollama模型的原始响应文本

        Returns:
            Dict[str, Any]: 解析后的结果字典，包含与parse_base_response方法相同的字段，
                          以及可能的Ollama特定字段
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
            "error_details": getattr(error, "details", None),
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
            error_info["status_code"] = error.status_code

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
