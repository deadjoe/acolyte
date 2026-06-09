import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Header } from './Header';
import { BrowserRouter } from 'react-router-dom';
import '@/context/AppContext';

// 模拟useTheme钩子
vi.mock('@/context/AppContext', () => ({
  useTheme: vi.fn(() => ({
    theme: 'light',
    setTheme: vi.fn(),
  })),
}));

describe('Header', () => {
  it('should render the header with logo and navigation', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    );

    // 验证logo存在
    expect(screen.getByText('Acolyte')).toBeInTheDocument();

    // 验证导航链接存在
    expect(screen.getByText('内容分析')).toBeInTheDocument();
    expect(screen.getByText('历史记录')).toBeInTheDocument();
    expect(screen.getByText('配置管理')).toBeInTheDocument();
  });
});
