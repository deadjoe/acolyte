#!/usr/bin/env python
"""
测试LLM API连接
"""
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from acolyte.core.db.database import db
from acolyte.core.db.models import LlmConfig
from acolyte.core.llm.client import get_client_for_llm


async def main():
    """主函数"""
    with db.session_scope() as session:
        # 获取默认LLM
        default_llm = session.query(LlmConfig).filter(LlmConfig.is_default == True).first()
        if not default_llm:
            print("错误: 未找到默认LLM配置")
            return

        print(f"使用LLM: {default_llm.name} (ID={default_llm.id})")
        print(f"  模型: {default_llm.model_name}")
        print(f"  基础URL: {default_llm.base_url}")
        print(f"  API密钥: {default_llm.api_key[:8]}...")

        # 创建LLM客户端
        client = get_client_for_llm(default_llm)

        # 测试内容
        test_content = "这是一个测试内容，用于验证API连接。"
        test_prompt = "你好，这是一个测试请求，请回复'API测试成功'"

        # 调用API
        print("开始调用API...")
        result = await client.process_content(test_content, test_prompt)

        if result["success"]:
            print("API调用成功!")
            print(f"处理时间: {result.get('result', {}).get('processing_time', 'N/A')}秒")
            print(f"回复内容:\n{result['raw_response'][:200]}...")
        else:
            print(f"API调用失败: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
