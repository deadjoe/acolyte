import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { LlmProvider, useLlm } from './LlmContext';

// 创建一个测试组件来使用useLlm钩子
const TestComponent = () => {
  const { state } = useLlm();
  return (
    <div>
      <div data-testid="llm-count">{state.llms.length}</div>
      <div data-testid="loading">{state.loading.toString()}</div>
      <div data-testid="error">{state.error || 'no-error'}</div>
    </div>
  );
};

describe('LlmContext', () => {
  it('should provide llm context with initial state', () => {
    render(
      <LlmProvider>
        <TestComponent />
      </LlmProvider>
    );

    // 验证初始状态
    expect(document.querySelector('[data-testid="llm-count"]')?.textContent).toBe('0');
    expect(document.querySelector('[data-testid="loading"]')?.textContent).toBe('false');
    expect(document.querySelector('[data-testid="error"]')?.textContent).toBe('no-error');
  });
});
