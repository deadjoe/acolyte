import { describe, it, expect, vi, beforeEach } from 'vitest';
import apiClient from './config';
import { getLlms, getLlm, createLlm, updateLlm, deleteLlm, setDefaultLlm } from './llms';

// 模拟apiClient
vi.mock('./config', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('LLMs API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call getLlms correctly', async () => {
    // 模拟响应
    (apiClient.get as any).mockResolvedValue({ data: [] });

    // 调用API
    await getLlms();

    // 验证API调用
    expect(apiClient.get).toHaveBeenCalledWith('/llms');
  });

  it('should call getLlm with correct parameters', async () => {
    // 模拟响应
    (apiClient.get as any).mockResolvedValue({ data: {} });

    // 调用API
    await getLlm(123);

    // 验证API调用
    expect(apiClient.get).toHaveBeenCalledWith('/llms/123');
  });

  it('should call createLlm with correct parameters', async () => {
    // 模拟响应
    (apiClient.post as any).mockResolvedValue({ data: {} });

    // 调用API
    const llmData = {
      name: 'Test LLM',
      provider: 'openai',
      model_name: 'gpt-4',
      api_key: 'test-key',
    };
    await createLlm(llmData);

    // 验证API调用
    expect(apiClient.post).toHaveBeenCalledWith('/llms', llmData);
  });

  it('should call updateLlm with correct parameters', async () => {
    // 模拟响应
    (apiClient.put as any).mockResolvedValue({ data: {} });

    // 调用API
    const llmData = {
      name: 'Updated LLM',
      provider: 'openai',
      model_name: 'gpt-4',
      api_key: 'updated-key',
    };
    await updateLlm(123, llmData);

    // 验证API调用
    expect(apiClient.put).toHaveBeenCalledWith('/llms/123', llmData);
  });

  it('should call deleteLlm with correct parameters', async () => {
    // 模拟响应
    (apiClient.delete as any).mockResolvedValue({ data: {} });

    // 调用API
    await deleteLlm(123);

    // 验证API调用
    expect(apiClient.delete).toHaveBeenCalledWith('/llms/123');
  });

  it('should call setDefaultLlm with correct parameters', async () => {
    // 模拟响应
    (apiClient.post as any).mockResolvedValue({ data: {} });

    // 调用API
    await setDefaultLlm(123);

    // 验证API调用
    expect(apiClient.post).toHaveBeenCalledWith('/llms/123/set-default');
  });
});
