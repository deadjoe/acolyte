import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * 格式化日期
 * @param dateString 日期字符串
 * @param options 格式化选项
 * @returns 格式化后的日期字符串
 */
export function formatDate(
  dateString?: string,
  options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }
) {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleString('zh-CN', options);
}

/**
 * 截断文本
 * @param text 文本
 * @param maxLength 最大长度
 * @returns 截断后的文本
 */
export function truncateText(text: string, maxLength: number) {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

/**
 * 延迟执行
 * @param ms 延迟时间（毫秒）
 * @returns Promise
 */
export function delay(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 获取处理模式中文名称
 * @param mode 处理模式
 * @returns 中文名称
 */
export function getProcessingModeName(mode: string) {
  const normalizedMode = mode.toLowerCase();
  switch (normalizedMode) {
    case 'single':
      return '单LLM';
    case 'multiple':
      return '多LLM并行';
    case 'multiple_with_review':
      return '多LLM评议';
    default:
      return mode;
  }
}

/**
 * 获取任务状态中文名称
 * @param status 任务状态
 * @returns 中文名称
 */
export function getTaskStatusName(status: string) {
  switch (status) {
    case 'completed':
      return '已完成';
    case 'processing':
      return '处理中';
    case 'pending':
      return '等待中';
    case 'failed':
      return '失败';
    default:
      return status;
  }
}

/**
 * 获取任务状态样式
 * @param status 任务状态
 * @returns 样式类名
 */
export function getTaskStatusStyle(status: string) {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
    case 'processing':
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
    case 'pending':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
    case 'failed':
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
  }
}
