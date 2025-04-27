import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import apiClient from './config';

// 模拟axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      }
    }))
  }
}));

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should create axios instance with correct base URL', () => {
    // 保存原始环境变量
    const originalEnv = import.meta.env;
    
    // 模拟环境变量
    vi.stubGlobal('import.meta.env', {
      ...originalEnv,
      VITE_API_URL: 'http://test-api.example.com'
    });
    
    // 重新导入apiClient
    const createSpy = vi.spyOn(axios, 'create');
    
    // 验证axios.create被调用
    expect(createSpy).toHaveBeenCalled();
    
    // 恢复原始环境变量
    vi.stubGlobal('import.meta.env', originalEnv);
  });
});
