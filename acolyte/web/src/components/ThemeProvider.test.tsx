import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { ThemeProvider } from './ThemeProvider';
import { useTheme } from '@/context/AppContext';

// 模拟useTheme钩子
vi.mock('@/context/AppContext', () => ({
  useTheme: vi.fn()
}));

describe('ThemeProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // 模拟document.documentElement
    Object.defineProperty(window.document, 'documentElement', {
      writable: true,
      value: {
        classList: {
          add: vi.fn(),
          remove: vi.fn()
        }
      }
    });
  });

  it('should add dark class to html element when theme is dark', () => {
    // 模拟useTheme返回dark主题
    (useTheme as any).mockReturnValue({ theme: 'dark' });
    
    render(<ThemeProvider>Test</ThemeProvider>);
    
    // 验证dark类被添加
    expect(document.documentElement.classList.add).toHaveBeenCalledWith('dark');
    expect(document.documentElement.classList.remove).not.toHaveBeenCalled();
  });

  it('should remove dark class from html element when theme is light', () => {
    // 模拟useTheme返回light主题
    (useTheme as any).mockReturnValue({ theme: 'light' });
    
    render(<ThemeProvider>Test</ThemeProvider>);
    
    // 验证dark类被移除
    expect(document.documentElement.classList.remove).toHaveBeenCalledWith('dark');
    expect(document.documentElement.classList.add).not.toHaveBeenCalled();
  });
});
