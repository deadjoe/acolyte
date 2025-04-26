import apiClient from './config';

export interface PromptCreateRequest {
  version: string;
  model_target?: string;
  content: string;
  description?: string;
  is_active?: boolean;
}

export interface PromptResponse {
  id: number;
  version: string;
  model_target?: string;
  content: string;
  description?: string;
  is_active: boolean;
  file_path?: string;
  created_at?: string;
  updated_at?: string;
}

export interface PromptSyncRequest {
  prompt_dir?: string;
}

// 获取提示词列表
export const getPrompts = async (modelTarget?: string, version?: string) => {
  const params = { model_target: modelTarget, version };
  const response = await apiClient.get<PromptResponse[]>('/prompts', { params });
  return response.data;
};

// 获取最新版本的提示词
export const getLatestPrompt = async (modelTarget?: string) => {
  const params = { model_target: modelTarget };
  const response = await apiClient.get<PromptResponse>('/prompts/latest', { params });
  return response.data;
};

// 获取特定提示词
export const getPrompt = async (promptId: number) => {
  const response = await apiClient.get<PromptResponse>(`/prompts/${promptId}`);
  return response.data;
};

// 创建提示词
export const createPrompt = async (promptData: PromptCreateRequest) => {
  const response = await apiClient.post<PromptResponse>('/prompts', promptData);
  return response.data;
};

// 同步提示词
export const syncPrompts = async (promptDir?: string) => {
  const data: PromptSyncRequest = {};
  if (promptDir) {
    data.prompt_dir = promptDir;
  }
  const response = await apiClient.post('/prompts/sync', data);
  return response.data;
};
