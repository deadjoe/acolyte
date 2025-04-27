import { describe, it, expect, vi, beforeEach } from 'vitest';
import apiClient from './config';
import { getPrompts, getPrompt, syncPrompts } from './prompts';

// 模拟apiClient
vi.mock('./config', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn()
  }
}));

describe('Prompts API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call getPrompts correctly', async () => {
    // 模拟响应
    (apiClient.get as any).mockResolvedValue({ data: [] });
    
    // 调用API
    await getPrompts();
    
    // 验证API调用
    expect(apiClient.get).toHaveBeenCalledWith('/prompts');
  });

  it('should call getPrompt with correct parameters', async () => {
    // 模拟响应
    (apiClient.get as any).mockResolvedValue({ data: {} });
    
    // 调用API
    await getPrompt(123);
    
    // 验证API调用
    expect(apiClient.get).toHaveBeenCalledWith('/prompts/123');
  });

  it('should call syncPrompts correctly', async () => {
    // 模拟响应
    (apiClient.post as any).mockResolvedValue({ data: {} });
    
    // 调用API
    await syncPrompts();
    
    // 验证API调用
    expect(apiClient.post).toHaveBeenCalledWith('/prompts/sync');
  });
});
