import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.tsx';

// 创建环境变量默认值
if (!import.meta.env.VITE_API_URL) {
  window.ENV = {
    ...window.ENV,
    VITE_API_URL: 'http://localhost:8000/api',
  };
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
