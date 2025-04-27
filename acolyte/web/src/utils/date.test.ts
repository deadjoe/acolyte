import { describe, it, expect } from 'vitest';
import { formatDate, formatDateTime } from './date';

describe('Date utilities', () => {
  it('should format date correctly', () => {
    // 使用固定日期进行测试
    const testDate = new Date('2023-05-15T10:30:00Z');

    // 测试formatDate
    expect(formatDate(testDate.toISOString())).toMatch(/\d{4}-\d{2}-\d{2}/);

    // 测试formatDateTime
    expect(formatDateTime(testDate.toISOString())).toMatch(/\d{4}-\d{2}-\d{2} \d{2}:\d{2}/);

    // 测试无效输入
    expect(formatDate('')).toBe('-');
    expect(formatDate(undefined)).toBe('-');
    expect(formatDateTime('')).toBe('-');
    expect(formatDateTime(undefined)).toBe('-');
  });
});
