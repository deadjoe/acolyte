import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { TaskProvider, useTask } from './TaskContext';

// 创建一个测试组件来使用useTask钩子
const TestComponent = () => {
  const { state } = useTask();
  return (
    <div>
      <div data-testid="task-count">{state.tasks.length}</div>
      <div data-testid="loading">{state.loading.toString()}</div>
      <div data-testid="error">{state.error || 'no-error'}</div>
    </div>
  );
};

describe('TaskContext', () => {
  it('should provide task context with initial state', () => {
    render(
      <TaskProvider>
        <TestComponent />
      </TaskProvider>
    );
    
    // 验证初始状态
    expect(document.querySelector('[data-testid="task-count"]')?.textContent).toBe('0');
    expect(document.querySelector('[data-testid="loading"]')?.textContent).toBe('false');
    expect(document.querySelector('[data-testid="error"]')?.textContent).toBe('no-error');
  });
});
