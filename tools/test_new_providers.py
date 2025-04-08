#!/usr/bin/env python
"""
测试DeepSeek和Ollama提供商的实现

此脚本测试DeepSeek和Ollama LLM客户端的功能，包括:
1. 连接测试
2. 内容处理
"""

import asyncio
import os
import sys

# 添加项目根目录到PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.providers.deepseek import DeepSeekClient
from acolyte.core.llm.providers.ollama import OllamaClient
from acolyte.utils.logging import get_logger

# 配置日志
logger = get_logger(__name__)


async def test_deepseek():
    """测试DeepSeek提供商"""
    print("\n====== 测试 DeepSeek 提供商 ======")

    # 从环境变量或配置文件获取API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("⚠️ 未设置DEEPSEEK_API_KEY环境变量，跳过DeepSeek测试")
        return

    # 创建配置
    deepseek_config = LlmConfig(
        name="DeepSeek测试",
        api_key=api_key,
        base_url="https://api.deepseek.ai/v1",
        model_name="deepseek-chat",
    )

    # 创建客户端
    client = DeepSeekClient(deepseek_config)

    # 测试连接
    print("正在测试DeepSeek连接...")
    connection_result = await client._test_connection()
    print(f"连接测试结果: {'✅ 成功' if connection_result.get('success') else '❌ 失败'}")
    print(f"消息: {connection_result.get('message', '无消息')}")

    if connection_result.get("success"):
        # 测试内容处理
        print("\n正在测试DeepSeek内容处理...")
        content = "昨天，中国队在比赛中以3:0战胜了日本队，取得了重要胜利。"
        prompt = """请分析以下文本内容，检测其中的偏见、误导性信息和隐藏意图。
        在回答中，请提供以下信息:
        
        ### 1. 分析前背景总结
        
        ### 2. 偏见检测发现
        
        ### 3. 误导性内容检测
        
        ### 4. 隐藏意图检测
        
        ### 5. 整体评估
        
        ### 6. 量化评分
        使用以下指标为内容评分(0-10分，数值越大表示该特性越明显):
        - 偏见指数 (BI) = 5
        - 误导性指数 (MI) = 3
        - 隐藏意图指数 (HI) = 2
        - 综合可信度 (CS) = 7
        
        ### 7. 分析局限与不确定性
        """

        result = await client.process_content(content, prompt)

        print(f"处理结果: {'✅ 成功' if result.get('success') else '❌ 失败'}")
        if result.get("success"):
            scores = result.get("scores", {})
            print("\n评分结果:")
            print(f"偏见指数: {scores.get('bias_index')}")
            print(f"误导性指数: {scores.get('misleading_index')}")
            print(f"隐藏意图指数: {scores.get('hidden_intent_index')}")
            print(f"综合可信度: {scores.get('credibility_score')}")


async def test_ollama():
    """测试Ollama提供商"""
    print("\n====== 测试 Ollama 提供商 ======")

    # 创建配置
    ollama_config = LlmConfig(
        name="Ollama测试",
        api_key="",  # Ollama不需要API密钥
        base_url="http://localhost:11434",
        model_name="llama2",  # 使用默认安装的模型，可能需要根据实际情况调整
    )

    # 创建客户端
    client = OllamaClient(ollama_config)

    # 测试连接
    print("正在测试Ollama连接...")
    connection_result = await client._test_connection()
    print(f"连接测试结果: {'✅ 成功' if connection_result.get('success') else '❌ 失败'}")
    print(f"消息: {connection_result.get('message', '无消息')}")

    if connection_result.get("success"):
        # 测试内容处理
        print("\n正在测试Ollama内容处理...")
        content = "昨天，中国队在比赛中以3:0战胜了日本队，取得了重要胜利。"
        prompt = """请分析以下文本内容，检测其中的偏见、误导性信息和隐藏意图。
        在回答中，请提供以下信息:
        
        ### 1. 分析前背景总结
        
        ### 2. 偏见检测发现
        
        ### 3. 误导性内容检测
        
        ### 4. 隐藏意图检测
        
        ### 5. 整体评估
        
        ### 6. 量化评分
        使用以下指标为内容评分(0-10分，数值越大表示该特性越明显):
        - 偏见指数 (BI) = 5
        - 误导性指数 (MI) = 3
        - 隐藏意图指数 (HI) = 2
        - 综合可信度 (CS) = 7
        
        ### 7. 分析局限与不确定性
        """

        result = await client.process_content(content, prompt)

        print(f"处理结果: {'✅ 成功' if result.get('success') else '❌ 失败'}")
        if result.get("success"):
            scores = result.get("scores", {})
            print("\n评分结果:")
            print(f"偏见指数: {scores.get('bias_index')}")
            print(f"误导性指数: {scores.get('misleading_index')}")
            print(f"隐藏意图指数: {scores.get('hidden_intent_index')}")
            print(f"综合可信度: {scores.get('credibility_score')}")


async def main():
    """主函数"""
    print("开始测试新增的LLM提供商...")

    await test_deepseek()
    await test_ollama()

    print("\n测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
