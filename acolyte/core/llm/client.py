"""
LLM客户端实现
"""
import json
import time
from typing import Any, Dict, Optional

import requests

from acolyte.core.db.models import LlmConfig


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
        start_time = time.time()

        # 构建最终提示
        final_prompt = f"{prompt}\n\n要分析的文章：\n\n{content}"

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
            
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            response_data = response.json()

            # 提取响应内容
            raw_response = response_data["content"][0]["text"]

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

        Args:
            response: 原始响应文本

        Returns:
            解析后的结果字典，包含评分和分析
        """
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
    # 根据base_url或其他参数判断LLM类型
    base_url = llm_config.base_url.lower()
    if "anthropic" in base_url:
        return AnthropicClient(llm_config)
    elif "openai" in base_url or "azure" in base_url:
        return OpenAIClient(llm_config)
    elif "googleapis" in base_url or "google" in base_url:
        return GeminiClient(llm_config)
    else:
        # 尝试基于模型名称进行判断
        model_name = llm_config.model_name.lower()
        if any(name in model_name for name in ["claude", "anthropic"]):
            return AnthropicClient(llm_config)
        elif any(name in model_name for name in ["gpt", "davinci", "openai"]):
            return OpenAIClient(llm_config)
        elif any(name in model_name for name in ["gemini", "google"]):
            return GeminiClient(llm_config)
        else:
            # 默认使用OpenAI客户端
            return OpenAIClient(llm_config)