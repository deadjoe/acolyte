"""
单LLM处理器

处理使用单个LLM的任务。
"""
import time
from typing import Dict, Optional

from acolyte.core.db.models import TaskStatus
from acolyte.core.llm.client import get_client_for_llm
from acolyte.core.task.processors.base import BaseTaskProcessor
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class SingleLlmProcessor(BaseTaskProcessor):
    """
    单LLM处理器
    
    使用单个LLM处理任务。
    """
    
    async def process(self, task_id: int) -> Dict:
        """
        处理任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            处理结果字典
        """
        logger.info(f"开始单LLM处理: 任务ID={task_id}")
        start_time = time.time()
        
        try:
            # 更新任务状态为处理中
            status_updated = await self._update_task_status(task_id, TaskStatus.PROCESSING)
            if not status_updated:
                return await self._handle_error(task_id, "更新任务状态失败")
            
            # 获取任务数据
            task_data = await self._get_task_with_content(task_id)
            if not task_data:
                return await self._handle_error(task_id, "任务不存在或内容获取失败")
            
            # 获取任务内容和提示词ID
            task_content = task_data.get("content")
            prompt_id = task_data.get("prompt_id")
            
            # 获取LLM配置
            llm_data = await self._get_llm(is_default=True)
            if not llm_data:
                return await self._handle_error(task_id, "未找到有效的LLM配置")
            
            # 获取提示词
            prompt_data = await self._get_prompt(prompt_id=prompt_id, model_name=llm_data.get("model_name"))
            if not prompt_data:
                return await self._handle_error(task_id, "未找到有效的提示词")
            
            # 提取必要数据
            llm_id = llm_data.get("id")
            prompt_content = prompt_data.get("content")
            
            # 检查数据完整性
            if not task_content or not prompt_content:
                missing = []
                if not task_content:
                    missing.append("任务内容")
                if not prompt_content:
                    missing.append("提示词内容")
                
                error_msg = f"缺少必要数据: {', '.join(missing)}"
                return await self._handle_error(task_id, error_msg)
            
            # 创建LLM客户端
            logger.info(f"使用LLM处理内容: {llm_data.get('name')} (ID={llm_id})")
            
            try:
                # 重建LLM配置对象
                from acolyte.core.db.models import LlmConfig, LlmRole
                reconstructed_llm = LlmConfig(
                    id=llm_data.get("id"),
                    name=llm_data.get("name"),
                    api_key=llm_data.get("api_key"),
                    base_url=llm_data.get("base_url"),
                    model_name=llm_data.get("model_name"),
                    role=llm_data.get("role", "normal"),
                    is_default=llm_data.get("is_default", False)
                )
                
                # 添加provider属性
                provider = llm_data.get("provider")
                if provider:
                    setattr(reconstructed_llm, 'provider', provider)
                
                # 获取客户端
                client = get_client_for_llm(reconstructed_llm)
                
                # 处理内容
                logger.info(f"开始调用LLM API: 任务ID={task_id}, LLM={llm_data.get('name')}")
                # 使用await关键字，因为process_content是异步方法
                result = await client.process_content(content=task_content, prompt=prompt_content)
                logger.info(f"LLM API调用完成: 任务ID={task_id}, 成功={result.get('success', False)}")
                
            except Exception as e:
                return await self._handle_error(task_id, f"LLM处理失败: {str(e)}")
            
            # 检查处理结果
            if not result.get("success", False):
                error = result.get("error", "未知错误")
                return await self._handle_error(task_id, f"LLM处理失败: {error}")
            
            # 记录评分结果
            bias_index = result.get("result", {}).get("bias_index")
            misleading_index = result.get("result", {}).get("misleading_index")
            hidden_intent_index = result.get("result", {}).get("hidden_intent_index")
            credibility_score = result.get("result", {}).get("credibility_score")
            
            logger.info(f"评分结果: BI={bias_index}, MI={misleading_index}, "
                      f"HI={hidden_intent_index}, CS={credibility_score}")
            
            # 保存结果
            result_id = await self._save_result(task_id, llm_id, result)
            if not result_id:
                return await self._handle_error(task_id, "保存处理结果失败")
            
            # 更新任务状态为已完成
            await self._update_task_status(task_id, TaskStatus.COMPLETED)
            
            # 统计处理时间
            elapsed_time = time.time() - start_time
            logger.info(f"单LLM处理完成: 任务ID={task_id}, 耗时={elapsed_time:.2f}秒")
            
            # 返回成功结果
            return {
                "success": True,
                "task_id": task_id,
                "final_result_id": result_id,
                "llm_id": llm_id,
                "result": result.get("result", {})
            }
            
        except Exception as e:
            # 处理所有未捕获的异常
            return await self._handle_error(task_id, e)