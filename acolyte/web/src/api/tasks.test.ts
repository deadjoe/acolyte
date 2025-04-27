import { describe, it, expect, vi, beforeEach } from 'vitest';
import apiClient from './config';
import { getTasks, getTask, getTaskResults, createTask, deleteTask, clearTasks } from './tasks';

// 模拟apiClient
vi.mock('./config', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('Tasks API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call getTasks with correct parameters', async () => {
    // 模拟响应
    (apiClient.get as any).mockResolvedValue({ data: [] });

    // 调用API
    await getTasks();

    // 验证API调用
    expect(apiClient.get).toHaveBeenCalledWith('/tasks', { params: {} });

    // 测试带参数的调用
    await getTasks('completed', 10, 20);
    expect(apiClient.get).toHaveBeenCalledWith('/tasks', {
      params: { status: 'completed', skip: 10, limit: 20 },
    });
  });

  it('should call getTask with correct parameters', async () => {
    // 模拟响应
    (apiClient.get as any).mockResolvedValue({ data: {} });

    // 调用API
    await getTask(123);

    // 验证API调用
    expect(apiClient.get).toHaveBeenCalledWith('/tasks/123');
  });

  it('should call getTaskResults with correct parameters', async () => {
    // 模拟响应
    (apiClient.get as any).mockResolvedValue({ data: [] });

    // 调用API
    await getTaskResults(123);

    // 验证API调用
    expect(apiClient.get).toHaveBeenCalledWith('/tasks/123/results', {
      params: { include_raw_response: false },
    });

    // 测试带参数的调用
    await getTaskResults(123, true);
    expect(apiClient.get).toHaveBeenCalledWith('/tasks/123/results', {
      params: { include_raw_response: true },
    });
  });

  it('should call createTask with correct parameters', async () => {
    // 模拟响应
    (apiClient.post as any).mockResolvedValue({ data: {} });

    // 调用API
    const taskData = {
      content: 'Test content',
      processing_mode: 'single' as const,
      prompt_id: 1,
      llm_ids: [1, 2],
    };
    await createTask(taskData);

    // 验证API调用
    expect(apiClient.post).toHaveBeenCalledWith('/tasks', taskData);
  });

  it('should call deleteTask with correct parameters', async () => {
    // 模拟响应
    (apiClient.delete as any).mockResolvedValue({ data: {} });

    // 调用API
    await deleteTask(123);

    // 验证API调用
    expect(apiClient.delete).toHaveBeenCalledWith('/tasks/123');
  });

  it('should call clearTasks with correct parameters', async () => {
    // 模拟响应
    (apiClient.delete as any).mockResolvedValue({ data: {} });

    // 调用API
    await clearTasks();

    // 验证API调用
    expect(apiClient.delete).toHaveBeenCalledWith('/tasks', {
      params: { confirm: true },
    });

    // 测试带参数的调用
    await clearTasks('completed');
    expect(apiClient.delete).toHaveBeenCalledWith('/tasks', {
      params: { confirm: true, status: 'completed' },
    });
  });
});
