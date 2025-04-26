import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.tsx';

// 创建环境变量默认值
console.log('环境变量:', import.meta.env);
const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
console.log('使用API URL:', apiUrl);

window.ENV = {
  ...window.ENV,
  VITE_API_URL: apiUrl,
};

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
