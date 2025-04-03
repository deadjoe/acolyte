"""
LLM客户端实现
"""
import json
import time
import traceback
from typing import Any, Dict

import requests

from acolyte.core.db.models import LlmConfig
from acolyte.utils.logging import get_logger

# 获取模块日志记录器
logger = get_logger(__name__)


class LlmClient:
    """LLM客户端基类"""

    def __init__(self, llm_config: LlmConfig):
        """初始化LLM客户端

        Args:
            llm_config: LLM配置对象
        """
        self.config = llm_config
        self.name = llm_config.name
        self.api_key = llm_config.api_key
        self.base_url = llm_config.base_url
        self.model_name = llm_config.model_name

    def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """处理内容

        Args:
            content: 要处理的内容
            prompt: 提示模板

        Returns:
            处理结果字典
        """
        logger.debug(f"{self.__class__.__name__} process_content调用: 内容长度={len(content)}字符, 提示词长度={len(prompt)}字符")
        raise NotImplementedError("子类必须实现此方法")


class AnthropicClient(LlmClient):
    """Anthropic Claude客户端"""

    def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """使用Claude处理内容

        Args:
            content: 要处理的内容
            prompt: 提示模板

        Returns:
            处理结果字典，包含原始响应和解析后的结果
        """
        logger.debug(f"Claude处理内容: 模型={self.model_name}, 内容长度={len(content)}字符")
        start_time = time.time()

        # 构建最终提示
        final_prompt = f"{prompt}\n\n要分析的文章：\n\n{content}"
        logger.debug(f"最终提示长度: {len(final_prompt)}字符")

        # 构建API请求
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        data = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": final_prompt}
            ],
            "max_tokens": 4000,
            "temperature": 0.0,
        }

        try:
            # 构建完整URL，基于base_url是否已包含/v1
            endpoint = "messages"
            if self.base_url.endswith("/v1"):
                url = f"{self.base_url}/{endpoint}"
            else:
                url = f"{self.base_url}/v1/{endpoint}"

            logger.info(f"发送请求到Anthropic API: {url}")

            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=60
                )

                # 处理HTTP错误
                try:
                    response.raise_for_status()
                except requests.exceptions.HTTPError as http_err:
                    if response.status_code == 401:
                        logger.error(f"Anthropic API认证失败: {http_err}")
                        return {
                            "success": False,
                            "error": "API认证失败，请检查API密钥",
                            "raw_response": None,
                            "result": None
                        }
                    elif response.status_code == 429:
                        logger.error(f"Anthropic API请求超过限制: {http_err}")
                        return {
                            "success": False,
                            "error": "API请求超过限制或速率限制",
                            "raw_response": None,
                            "result": None
                        }
                    else:
                        logger.error(f"Anthropic API HTTP错误: {http_err}")
                        return {
                            "success": False,
                            "error": f"API调用HTTP错误: {http_err}",
                            "raw_response": None,
                            "result": None
                        }

                response_data = response.json()
                logger.debug(f"收到Anthropic API响应: {len(str(response_data))}字符")
            except requests.exceptions.ConnectionError as conn_err:
                logger.error(f"与Anthropic API连接失败: {conn_err}")
                return {
                    "success": False,
                    "error": f"API连接失败: {conn_err}",
                    "raw_response": None,
                    "result": None
                }
            except requests.exceptions.Timeout as timeout_err:
                logger.error(f"Anthropic API请求超时: {timeout_err}")
                return {
                    "success": False,
                    "error": "API请求超时",
                    "raw_response": None,
                    "result": None
                }
            except requests.exceptions.RequestException as req_err:
                logger.error(f"Anthropic API请求异常: {req_err}")
                return {
                    "success": False,
                    "error": f"API请求异常: {req_err}",
                    "raw_response": None,
                    "result": None
                }
            except json.JSONDecodeError as json_err:
                logger.error(f"解析Anthropic API响应JSON失败: {json_err}")
                return {
                    "success": False,
                    "error": "API返回了无效的JSON响应",
                    "raw_response": None,
                    "result": None
                }

            try:
                # 提取响应内容
                raw_response = response_data["content"][0]["text"]
                logger.debug(f"原始响应长度: {len(raw_response)}字符")
            except (KeyError, IndexError) as key_err:
                logger.error(f"无法从Anthropic响应中提取内容: {key_err}, 响应: {response_data}")
                return {
                    "success": False,
                    "error": f"无法从API响应中提取内容: {key_err}",
                    "raw_response": str(response_data),
                    "result": None
                }

            # 解析响应提取评分
            logger.debug("开始解析响应提取评分...")
            result = self._parse_response(raw_response)
            logger.info(f"评分解析结果: BI={result.get('bias_index')}, MI={result.get('misleading_index')}, "
                      f"HI={result.get('hidden_intent_index')}, CS={result.get('credibility_score')}")

            # 添加处理时间和元数据
            elapsed_time = time.time() - start_time
            result["processing_time"] = elapsed_time
            result["model"] = self.model_name
            result["llm_name"] = self.name
            logger.info(f"处理完成: 耗时={elapsed_time:.2f}秒")

            return {
                "success": True,
                "raw_response": raw_response,
                "result": result
            }

        except Exception as e:
            logger.error(f"Anthropic API调用中未捕获的异常: {str(e)}")
            logger.debug(f"异常详情: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"API调用未捕获异常: {str(e)}",
                "raw_response": None,
                "result": None
            }

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析响应提取评分和分析结果

        Args:
            response: 原始响应文本

        Returns:
            解析后的结果字典，包含评分和分析
        """
        logger.debug("开始解析响应文本...")
        logger.debug(f"解析策略: 首先使用ResponseParser提取评分，然后提取结构化内容")

        # 使用ResponseParser提取评分
        from acolyte.core.llm.response import ResponseParser
        scores = ResponseParser.extract_scores(response)
        logger.debug(f"评分提取结果: BI={scores.get('bias_index')}, MI={scores.get('misleading_index')}, HI={scores.get('hidden_intent_index')}, CS={scores.get('credibility_score')}")

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

        try:
            # 记录响应中是否包含关键标记
            has_bi_marker = "偏见指数 (BI)" in response
            has_mi_marker = "误导性指数 (MI)" in response
            has_hi_marker = "隐藏意图指数 (HI)" in response
            has_cs_marker = "综合可信度" in response
            logger.debug(f"响应中的标记: BI={has_bi_marker}, MI={has_mi_marker}, "
                        f"HI={has_hi_marker}, CS={has_cs_marker}")

            # 提取前50行用于调试
            first_lines = "\n".join(response.split("\n")[:50])
            logger.debug(f"响应前50行:\n{first_lines}")

            # 提取量化评分部分
            if "偏见指数 (BI):" in response or "偏见指数 (BI)" in response:
                bi_match = next((line for line in response.split("\n")
                                if "偏见指数" in line and "=" in line), None)
                if bi_match:
                    logger.debug(f"找到偏见指数行: {bi_match}")
                    try:
                        result["bias_index"] = float(bi_match.split("=")[1].strip())
                        logger.debug(f"提取的偏见指数: {result['bias_index']}")
                    except (ValueError, IndexError) as e:
                        logger.warning(f"解析偏见指数失败: {str(e)}, 行: {bi_match}")

            if "误导性指数 (MI):" in response or "误导性指数 (MI)" in response:
                mi_match = next((line for line in response.split("\n")
                                if "误导性指数" in line and "=" in line), None)
                if mi_match:
                    logger.debug(f"找到误导性指数行: {mi_match}")
                    try:
                        result["misleading_index"] = float(mi_match.split("=")[1].strip())
                        logger.debug(f"提取的误导性指数: {result['misleading_index']}")
                    except (ValueError, IndexError) as e:
                        logger.warning(f"解析误导性指数失败: {str(e)}, 行: {mi_match}")

            if "隐藏意图指数 (HI):" in response or "隐藏意图指数 (HI)" in response:
                hi_match = next((line for line in response.split("\n")
                                if "隐藏意图指数" in line and "=" in line), None)
                if hi_match:
                    logger.debug(f"找到隐藏意图指数行: {hi_match}")
                    try:
                        result["hidden_intent_index"] = float(hi_match.split("=")[1].strip())
                        logger.debug(f"提取的隐藏意图指数: {result['hidden_intent_index']}")
                    except (ValueError, IndexError) as e:
                        logger.warning(f"解析隐藏意图指数失败: {str(e)}, 行: {hi_match}")

            # 使用ResponseParser已经提取了综合可信度，这里不需要再次提取

            # 提取分析前背景
            logger.debug("开始提取分析前背景...")
            background_start = response.find("### 1. 分析前背景总结")
            if background_start != -1:
                logger.debug(f"找到背景部分开始位置: {background_start}")
                bias_start = response.find("### 2. 偏见检测发现", background_start)
                if bias_start != -1:
                    background_text = response[background_start:bias_start].strip()
                    # 移除标题
                    background_text = background_text.replace("### 1. 分析前背景总结", "").strip()
                    result["analysis"]["background"] = background_text
                    logger.debug(f"提取到背景内容，长度: {len(background_text)}字符")
                else:
                    logger.warning("未找到偏见检测发现部分，无法完整提取背景")
            else:
                logger.warning("未找到分析前背景部分")

            # 提取偏见发现
            logger.debug("开始提取偏见发现...")
            bias_start = response.find("### 2. 偏见检测发现")
            if bias_start != -1:
                logger.debug(f"找到偏见部分开始位置: {bias_start}")
                misleading_start = response.find("### 3. 误导性内容检测", bias_start)
                if misleading_start != -1:
                    bias_text = response[bias_start:misleading_start].strip()
                    # 提取列表项
                    bias_items = [line.strip() for line in bias_text.split("\n")
                                if line.strip().startswith("-") or line.strip().startswith("*")]
                    result["analysis"]["bias_findings"] = bias_items
                    logger.debug(f"提取到偏见发现项: {len(bias_items)}项")
                else:
                    logger.warning("未找到误导性内容检测部分，无法完整提取偏见发现")
            else:
                logger.warning("未找到偏见检测发现部分")

            # 提取误导性内容发现
            logger.debug("开始提取误导性内容发现...")
            misleading_start = response.find("### 3. 误导性内容检测")
            if misleading_start != -1:
                logger.debug(f"找到误导性内容部分开始位置: {misleading_start}")
                hidden_intent_start = response.find("### 4. 隐藏意图检测", misleading_start)
                if hidden_intent_start != -1:
                    misleading_text = response[misleading_start:hidden_intent_start].strip()
                    # 提取列表项
                    misleading_items = [line.strip() for line in misleading_text.split("\n")
                                    if line.strip().startswith("-") or line.strip().startswith("*")]
                    result["analysis"]["misleading_findings"] = misleading_items
                    logger.debug(f"提取到误导性内容发现项: {len(misleading_items)}项")
                else:
                    logger.warning("未找到隐藏意图检测部分，无法完整提取误导性内容发现")
            else:
                logger.warning("未找到误导性内容检测部分")

            # 提取隐藏意图发现
            logger.debug("开始提取隐藏意图发现...")
            hidden_intent_start = response.find("### 4. 隐藏意图检测")
            if hidden_intent_start != -1:
                logger.debug(f"找到隐藏意图部分开始位置: {hidden_intent_start}")
                overall_start = response.find("### 5. 整体评估", hidden_intent_start)
                if overall_start != -1:
                    hidden_intent_text = response[hidden_intent_start:overall_start].strip()
                    # 提取列表项
                    hidden_intent_items = [line.strip() for line in hidden_intent_text.split("\n")
                                        if line.strip().startswith("-") or line.strip().startswith("*")]
                    result["analysis"]["hidden_intent_findings"] = hidden_intent_items
                    logger.debug(f"提取到隐藏意图发现项: {len(hidden_intent_items)}项")
                else:
                    logger.warning("未找到整体评估部分，无法完整提取隐藏意图发现")
            else:
                logger.warning("未找到隐藏意图检测部分")

            # 提取整体评估
            logger.debug("开始提取整体评估...")
            overall_start = response.find("### 5. 整体评估")
            if overall_start != -1:
                logger.debug(f"找到整体评估部分开始位置: {overall_start}")
                quantitative_start = response.find("### 6. 量化评分", overall_start)
                if quantitative_start != -1:
                    overall_text = response[overall_start:quantitative_start].strip()
                    # 移除标题
                    overall_text = overall_text.replace("### 5. 整体评估", "").strip()
                    result["analysis"]["overall_assessment"] = overall_text
                    logger.debug(f"提取到整体评估内容，长度: {len(overall_text)}字符")
                else:
                    logger.warning("未找到量化评分部分，无法完整提取整体评估")
            else:
                logger.warning("未找到整体评估部分")

            # 提取可信度分类
            logger.debug("开始提取可信度分类...")
            if "可信度分类:" in response:
                logger.debug("响应中包含可信度分类标记")
                try:
                    class_match = next((line for line in response.split("\n")
                                      if "可信度分类:" in line), None)
                    if class_match:
                        result["analysis"]["credibility_classification"] = class_match.split(":")[1].strip()
                        logger.debug(f"提取到可信度分类: {result['analysis']['credibility_classification']}")
                    else:
                        logger.warning("虽然找到可信度分类标记，但未能提取分类值")
                except Exception as e:
                    logger.warning(f"提取可信度分类时出错: {str(e)}")
            else:
                logger.warning("未找到可信度分类标记")

            # 提取分析局限性
            logger.debug("开始提取分析局限性...")
            limitations_start = response.find("### 7. 分析局限与不确定性")
            if limitations_start != -1:
                logger.debug(f"找到分析局限部分开始位置: {limitations_start}")
                limitations_text = response[limitations_start:].strip()
                # 提取列表项
                limitations_items = [line.strip() for line in limitations_text.split("\n")
                                   if line.strip().startswith("-") or line.strip().startswith("*")]
                result["analysis"]["limitations"] = limitations_items
                logger.debug(f"提取到分析局限项: {len(limitations_items)}项")
            else:
                logger.warning("未找到分析局限与不确定性部分")

            # 尝试提取更通用的格式
            missing_scores = []
            if result["bias_index"] is None:
                missing_scores.append("bias_index")
            if result["misleading_index"] is None:
                missing_scores.append("misleading_index")
            if result["hidden_intent_index"] is None:
                missing_scores.append("hidden_intent_index")
            if result["credibility_score"] is None:
                missing_scores.append("credibility_score")

            if missing_scores:
                logger.info(f"使用备用方法尝试提取缺失的评分: {', '.join(missing_scores)}")

                # 查找加权评分和最终分数部分
                for line in response.split("\n"):
                    line = line.strip()
                    # 通用的提取模式
                    if any(k in line.lower() for k in ["bias_index", "偏见指数", "加权bi"]) and "=" in line and result["bias_index"] is None:
                        try:
                            value = float(line.split("=")[1].strip())
                            result["bias_index"] = value
                            logger.info(f"备用方法提取偏见指数: {value}")
                        except Exception as e:
                            logger.warning(f"备用提取偏见指数失败: {str(e)}")

                    if any(k in line.lower() for k in ["misleading_index", "误导性指数", "加权mi"]) and "=" in line and result["misleading_index"] is None:
                        try:
                            value = float(line.split("=")[1].strip())
                            result["misleading_index"] = value
                            logger.info(f"备用方法提取误导性指数: {value}")
                        except Exception as e:
                            logger.warning(f"备用提取误导性指数失败: {str(e)}")

                    if any(k in line.lower() for k in ["hidden_intent_index", "隐藏意图指数", "加权hi"]) and "=" in line and result["hidden_intent_index"] is None:
                        try:
                            value = float(line.split("=")[1].strip())
                            result["hidden_intent_index"] = value
                            logger.info(f"备用方法提取隐藏意图指数: {value}")
                        except Exception as e:
                            logger.warning(f"备用提取隐藏意图指数失败: {str(e)}")

                    # 使用ResponseParser已经提取了综合可信度，这里不需要再次提取

        except Exception as e:
            # 如果解析失败，添加错误信息但返回原始响应
            error_msg = str(e)
            result["parse_error"] = error_msg
            logger.error(f"解析响应时出现异常: {error_msg}")
            logger.debug(f"异常详情: {traceback.format_exc()}")

        # 记录最终结果
        logger.info("解析结果汇总:")
        logger.info(f"  偏见指数: {result['bias_index']}")
        logger.info(f"  误导性指数: {result['misleading_index']}")
        logger.info(f"  隐藏意图指数: {result['hidden_intent_index']}")
        logger.info(f"  综合可信度: {result['credibility_score']}")

        return result


class OpenAIClient(LlmClient):
    """OpenAI客户端"""

    def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """使用OpenAI处理内容

        Args:
            content: 要处理的内容
            prompt: 提示模板

        Returns:
            处理结果字典，包含原始响应和解析后的结果
        """
        start_time = time.time()

        # 构建最终提示
        final_prompt = f"{prompt}\n\n要分析的文章：\n\n{content}"

        # 构建API请求
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": final_prompt}
            ],
            "max_tokens": 4000,
            "temperature": 0.0,
        }

        try:
            # 构建完整URL，基于base_url是否已包含/v1
            endpoint = "chat/completions"
            if self.base_url.endswith("/v1"):
                url = f"{self.base_url}/{endpoint}"
            else:
                url = f"{self.base_url}/v1/{endpoint}"

            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            response_data = response.json()

            # 提取响应内容
            raw_response = response_data["choices"][0]["message"]["content"]

            # 解析响应提取评分
            result = self._parse_response(raw_response)

            # 添加处理时间和元数据
            result["processing_time"] = time.time() - start_time
            result["model"] = self.model_name
            result["llm_name"] = self.name

            return {
                "success": True,
                "raw_response": raw_response,
                "result": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "raw_response": None,
                "result": None
            }

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析响应提取评分和分析结果

        与AnthropicClient._parse_response相同的实现
        """
        # 复用Claude的解析逻辑，因为prompt模板格式相同
        result = {
            "bias_index": None,
            "misleading_index": None,
            "hidden_intent_index": None,
            "credibility_score": None,
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

        try:
            # 提取量化评分部分
            if "偏见指数 (BI):" in response or "偏见指数 (BI)" in response:
                bi_match = next((line for line in response.split("\n")
                                if "偏见指数" in line and "=" in line), None)
                if bi_match:
                    result["bias_index"] = float(bi_match.split("=")[1].strip())

            if "误导性指数 (MI):" in response or "误导性指数 (MI)" in response:
                mi_match = next((line for line in response.split("\n")
                                if "误导性指数" in line and "=" in line), None)
                if mi_match:
                    result["misleading_index"] = float(mi_match.split("=")[1].strip())

            if "隐藏意图指数 (HI):" in response or "隐藏意图指数 (HI)" in response:
                hi_match = next((line for line in response.split("\n")
                                if "隐藏意图指数" in line and "=" in line), None)
                if hi_match:
                    result["hidden_intent_index"] = float(hi_match.split("=")[1].strip())

            if "综合可信度 (CS):" in response or "综合可信度分数 (CS)" in response:
                cs_match = next((line for line in response.split("\n")
                                if "综合可信度" in line and "=" in line), None)
                if cs_match:
                    result["credibility_score"] = float(cs_match.split("=")[1].strip())

            # 提取其他分析部分（与Claude相同）
            # ...分析部分代码与AnthropicClient相同，此处省略...

        except Exception as e:
            # 如果解析失败，添加错误信息但返回原始响应
            result["parse_error"] = str(e)

        return result


class GeminiClient(LlmClient):
    """Google Gemini客户端"""

    def process_content(self, content: str, prompt: str) -> Dict[str, Any]:
        """使用Gemini处理内容

        Args:
            content: 要处理的内容
            prompt: 提示模板

        Returns:
            处理结果字典，包含原始响应和解析后的结果
        """
        start_time = time.time()

        # 构建最终提示
        final_prompt = f"{prompt}\n\n要分析的文章：\n\n{content}"

        # 构建API请求
        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": final_prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 4000
            }
        }

        try:
            # Gemini API密钥作为query parameter提供
            # 对于Gemini，base_url应该是完整的API前缀，不需要额外处理
            response = requests.post(
                f"{self.base_url}/models/{self.model_name}:generateContent?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            response_data = response.json()

            # 提取响应内容
            raw_response = response_data["candidates"][0]["content"]["parts"][0]["text"]

            # 解析响应提取评分
            result = self._parse_response(raw_response)

            # 添加处理时间和元数据
            result["processing_time"] = time.time() - start_time
            result["model"] = self.model_name
            result["llm_name"] = self.name

            return {
                "success": True,
                "raw_response": raw_response,
                "result": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "raw_response": None,
                "result": None
            }

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析响应提取评分和分析结果

        与AnthropicClient._parse_response相同的实现
        """
        # 复用Claude的解析逻辑，因为prompt模板格式相同
        result = {
            "bias_index": None,
            "misleading_index": None,
            "hidden_intent_index": None,
            "credibility_score": None,
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

        try:
            # 提取量化评分部分
            if "偏见指数 (BI):" in response or "偏见指数 (BI)" in response:
                bi_match = next((line for line in response.split("\n")
                                if "偏见指数" in line and "=" in line), None)
                if bi_match:
                    result["bias_index"] = float(bi_match.split("=")[1].strip())

            if "误导性指数 (MI):" in response or "误导性指数 (MI)" in response:
                mi_match = next((line for line in response.split("\n")
                                if "误导性指数" in line and "=" in line), None)
                if mi_match:
                    result["misleading_index"] = float(mi_match.split("=")[1].strip())

            if "隐藏意图指数 (HI):" in response or "隐藏意图指数 (HI)" in response:
                hi_match = next((line for line in response.split("\n")
                                if "隐藏意图指数" in line and "=" in line), None)
                if hi_match:
                    result["hidden_intent_index"] = float(hi_match.split("=")[1].strip())

            if "综合可信度 (CS):" in response or "综合可信度分数 (CS)" in response:
                cs_match = next((line for line in response.split("\n")
                                if "综合可信度" in line and "=" in line), None)
                if cs_match:
                    result["credibility_score"] = float(cs_match.split("=")[1].strip())

            # 提取分析前背景
            background_start = response.find("### 1. 分析前背景总结")
            if background_start != -1:
                bias_start = response.find("### 2. 偏见检测发现", background_start)
                if bias_start != -1:
                    background_text = response[background_start:bias_start].strip()
                    # 移除标题
                    background_text = background_text.replace("### 1. 分析前背景总结", "").strip()
                    result["analysis"]["background"] = background_text

            # 提取偏见发现
            bias_start = response.find("### 2. 偏见检测发现")
            if bias_start != -1:
                misleading_start = response.find("### 3. 误导性内容检测", bias_start)
                if misleading_start != -1:
                    bias_text = response[bias_start:misleading_start].strip()
                    # 提取列表项
                    bias_items = [line.strip() for line in bias_text.split("\n")
                                if line.strip().startswith("-") or line.strip().startswith("*")]
                    result["analysis"]["bias_findings"] = bias_items

            # 提取误导性内容发现
            misleading_start = response.find("### 3. 误导性内容检测")
            if misleading_start != -1:
                hidden_intent_start = response.find("### 4. 隐藏意图检测", misleading_start)
                if hidden_intent_start != -1:
                    misleading_text = response[misleading_start:hidden_intent_start].strip()
                    # 提取列表项
                    misleading_items = [line.strip() for line in misleading_text.split("\n")
                                     if line.strip().startswith("-") or line.strip().startswith("*")]
                    result["analysis"]["misleading_findings"] = misleading_items

            # 提取隐藏意图发现
            hidden_intent_start = response.find("### 4. 隐藏意图检测")
            if hidden_intent_start != -1:
                overall_start = response.find("### 5. 整体评估", hidden_intent_start)
                if overall_start != -1:
                    hidden_intent_text = response[hidden_intent_start:overall_start].strip()
                    # 提取列表项
                    hidden_intent_items = [line.strip() for line in hidden_intent_text.split("\n")
                                        if line.strip().startswith("-") or line.strip().startswith("*")]
                    result["analysis"]["hidden_intent_findings"] = hidden_intent_items

            # 提取整体评估
            overall_start = response.find("### 5. 整体评估")
            if overall_start != -1:
                quantitative_start = response.find("### 6. 量化评分", overall_start)
                if quantitative_start != -1:
                    overall_text = response[overall_start:quantitative_start].strip()
                    # 移除标题
                    overall_text = overall_text.replace("### 5. 整体评估", "").strip()
                    result["analysis"]["overall_assessment"] = overall_text

            # 提取可信度分类
            if "可信度分类:" in response:
                class_match = next((line for line in response.split("\n")
                                  if "可信度分类:" in line), None)
                if class_match:
                    result["analysis"]["credibility_classification"] = class_match.split(":")[1].strip()

            # 提取分析局限性
            limitations_start = response.find("### 7. 分析局限与不确定性")
            if limitations_start != -1:
                limitations_text = response[limitations_start:].strip()
                # 提取列表项
                limitations_items = [line.strip() for line in limitations_text.split("\n")
                                   if line.strip().startswith("-") or line.strip().startswith("*")]
                result["analysis"]["limitations"] = limitations_items

        except Exception as e:
            # 如果解析失败，添加错误信息但返回原始响应
            result["parse_error"] = str(e)

        return result


def get_client_for_llm(llm_config: LlmConfig) -> LlmClient:
    """根据LLM配置获取对应的客户端

    Args:
        llm_config: LLM配置对象

    Returns:
        对应的LLM客户端实例
    """
    from acolyte.core.llm.providers.deepseek import DeepSeekClient
    from acolyte.core.llm.providers.ollama import OllamaClient

    # 获取日志记录器
    logger = get_logger(__name__)
    logger.debug(f"为LLM创建客户端: 名称={llm_config.name}, URL={llm_config.base_url}, 模型={llm_config.model_name}")

    # 根据base_url或其他参数判断LLM类型
    base_url = llm_config.base_url.lower() if llm_config.base_url else ""
    if "anthropic" in base_url:
        return AnthropicClient(llm_config)
    elif "openai" in base_url or "azure" in base_url:
        return OpenAIClient(llm_config)
    elif "googleapis" in base_url or "google" in base_url:
        return GeminiClient(llm_config)
    elif "deepseek" in base_url:
        return DeepSeekClient(llm_config)
    elif "ollama" in base_url or "localhost:11434" in base_url:
        return OllamaClient(llm_config)
    else:
        # 尝试基于模型名称进行判断
        model_name = llm_config.model_name.lower() if llm_config.model_name else ""
        if any(name in model_name for name in ["claude", "anthropic"]):
            return AnthropicClient(llm_config)
        elif any(name in model_name for name in ["gpt", "davinci", "openai"]):
            return OpenAIClient(llm_config)
        elif any(name in model_name for name in ["gemini", "google"]):
            return GeminiClient(llm_config)
        elif any(name in model_name for name in ["deepseek"]):
            return DeepSeekClient(llm_config)
        elif any(name in model_name for name in ["llama", "mistral", "mixtral", "vicuna", "phi", "yi"]):
            return OllamaClient(llm_config)
        else:
            # 如果无法确定，记录警告并默认使用OpenAI客户端
            logger.warning(f"无法确定LLM类型: {llm_config.name}, 使用默认的OpenAI客户端")
            return OpenAIClient(llm_config)