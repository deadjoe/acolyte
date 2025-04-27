import axios from 'axios';

// 创建axios实例
// 检测当前环境，如果是通过IP地址访问，则使用相同的IP地址访问API
const getApiBaseUrl = () => {
  // 优先使用环境变量中的API URL
  if (import.meta.env.VITE_API_URL) {
    return `${import.meta.env.VITE_API_URL}/api`;
  }

  // 如果没有环境变量，则尝试使用当前页面的主机名
  const currentHost = window.location.hostname;
  if (currentHost !== 'localhost' && currentHost !== '127.0.0.1') {
    // 如果不是localhost，则使用当前主机名
    return `http://${currentHost}:8000/api`;
  }

  // 默认使用localhost
  return 'http://localhost:8000/api';
};

const baseURL = getApiBaseUrl();
console.log('API基础URL:', baseURL);

const apiClient = axios.create({
  baseURL,
  timeout: 30000, // 30秒超时
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false, // 不发送凭证
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证信息等
    console.log('发送API请求:', config.method?.toUpperCase(), config.url, config.params || config.data);

    // 确保请求头包含正确的Content-Type
    config.headers = {
      ...config.headers,
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    return config;
  },
  (error) => {
    console.error('请求拦截器错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log('API响应成功:', response.config.url, response.data);
    return response;
  },
  (error) => {
    // 处理错误响应
    if (error.response) {
      // 服务器返回了错误状态码
      console.error('API错误:', error.config.url, error.response.status, error.response.data);
    } else if (error.request) {
      // 请求已发送但没有收到响应
      console.error('API请求无响应:', error.config.url, error.request);
    } else {
      // 请求配置出错
      console.error('API请求配置错误:', error.config?.url, error.message);
    }
    return Promise.reject(error);
  }
);

export default apiClient;
