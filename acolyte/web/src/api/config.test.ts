import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import apiClient from './config';

// 模拟axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}));

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should be an axios instance', () => {
    // 验证apiClient存在
    expect(apiClient).toBeDefined();

    // 验证apiClient有axios实例的典型方法
    expect(typeof apiClient.get).toBe('function');
    expect(typeof apiClient.post).toBe('function');
    expect(typeof apiClient.put).toBe('function');
    expect(typeof apiClient.delete).toBe('function');
  });
});
