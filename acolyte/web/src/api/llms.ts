import apiClient from './config';

export interface LlmConfigCreateRequest {
  name: string;
  api_key: string;
  base_url: string;
  model_name: string;
  description?: string;
  role?: 'normal' | 'reviewer';
  is_default?: boolean;
}

export interface LlmConfigUpdateRequest {
  name?: string;
  api_key?: string;
  base_url?: string;
  model_name?: string;
  description?: string;
  role?: 'normal' | 'reviewer';
  is_default?: boolean;
}

export interface LlmConfigResponse {
  id: number;
  name: string;
  base_url: string;
  model_name: string;
  description?: string;
  role: string;
  is_default: boolean;
}

// 获取LLM配置列表
export const getLlms = async (role?: string, isDefault?: boolean) => {
  const params = { role, is_default: isDefault };
  const response = await apiClient.get<LlmConfigResponse[]>('/llms', { params });
  return response.data;
};

// 获取特定LLM配置
export const getLlm = async (llmId: number) => {
  const response = await apiClient.get<LlmConfigResponse>(`/llms/${llmId}`);
  return response.data;
};

// 创建LLM配置
export const createLlm = async (llmConfig: LlmConfigCreateRequest) => {
  const response = await apiClient.post<LlmConfigResponse>('/llms', llmConfig);
  return response.data;
};

// 更新LLM配置
export const updateLlm = async (llmId: number, llmConfig: LlmConfigUpdateRequest) => {
  const response = await apiClient.put<LlmConfigResponse>(`/llms/${llmId}`, llmConfig);
  return response.data;
};

// 删除LLM配置
export const deleteLlm = async (llmId: number) => {
  const response = await apiClient.delete(`/llms/${llmId}`);
  return response.data;
};

// 测试LLM连接
export const testLlmConnection = async (llmId: number) => {
  const response = await apiClient.post(`/llms/${llmId}/test`);
  return response.data;
};
