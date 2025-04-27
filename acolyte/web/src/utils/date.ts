/**
 * 格式化日期时间
 * @param dateString 日期字符串
 * @returns 格式化后的日期时间字符串
 */
export const formatDateTime = (dateString?: string): string => {
  if (!dateString) return '-';

  try {
    // 创建Date对象，保持原始时区
    const date = new Date(dateString);

    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      console.warn('无效的日期字符串:', dateString);
      return dateString;
    }

    // 使用toLocaleString格式化日期，保持原始时区
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  } catch (error) {
    console.error('格式化日期时间失败:', error);
    return dateString;
  }
};

/**
 * 格式化日期
 * @param dateString 日期字符串
 * @returns 格式化后的日期字符串
 */
export const formatDate = (dateString?: string): string => {
  if (!dateString) return '-';

  try {
    // 创建Date对象，保持原始时区
    const date = new Date(dateString);

    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      console.warn('无效的日期字符串:', dateString);
      return dateString;
    }

    // 使用toLocaleDateString格式化日期，保持原始时区
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  } catch (error) {
    console.error('格式化日期失败:', error);
    return dateString;
  }
};
