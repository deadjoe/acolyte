// 这个文件将在每个测试文件之前运行

import { vi, beforeAll, beforeEach, afterEach, afterAll } from 'vitest';

// 导入jest-dom扩展断言
import '@testing-library/jest-dom';

// 全局模拟
vi.mock('@/api/config', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// 全局设置
beforeAll(() => {
  // 全局设置，例如模拟localStorage
  const localStorageMock = {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
  };

  Object.defineProperty(window, 'localStorage', {
    value: localStorageMock,
  });
});

// 每个测试之前的设置
beforeEach(() => {
  // 重置所有模拟
  vi.resetAllMocks();
});

// 每个测试之后的清理
afterEach(() => {
  // 清理操作
});

// 所有测试完成后的清理
afterAll(() => {
  // 全局清理
});
