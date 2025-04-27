import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { PromptProvider, usePrompt } from './PromptContext';

// 创建一个测试组件来使用usePrompt钩子
const TestComponent = () => {
  const { state } = usePrompt();
  return (
    <div>
      <div data-testid="prompt-count">{state.prompts.length}</div>
      <div data-testid="loading">{state.loading.toString()}</div>
      <div data-testid="error">{state.error || 'no-error'}</div>
    </div>
  );
};

describe('PromptContext', () => {
  it('should provide prompt context with initial state', () => {
    render(
      <PromptProvider>
        <TestComponent />
      </PromptProvider>
    );

    // 验证初始状态
    expect(document.querySelector('[data-testid="prompt-count"]')?.textContent).toBe('0');
    expect(document.querySelector('[data-testid="loading"]')?.textContent).toBe('false');
    expect(document.querySelector('[data-testid="error"]')?.textContent).toBe('no-error');
  });
});
