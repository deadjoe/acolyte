import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AppProvider, useTheme } from './AppContext';

// 创建一个测试组件来使用useTheme钩子
const TestComponent = () => {
  const { theme, setTheme } = useTheme();
  return (
    <div>
      <div data-testid="theme">{theme}</div>
      <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>Toggle Theme</button>
    </div>
  );
};

describe('AppContext', () => {
  it('should provide theme context', () => {
    render(
      <AppProvider>
        <TestComponent />
      </AppProvider>
    );

    // 默认主题应该是light或dark
    const themeElement = screen.getByTestId('theme');
    expect(['light', 'dark']).toContain(themeElement.textContent);
  });
});
