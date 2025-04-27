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
  // 由于/prompts/latest端点存在问题，直接使用获取所有提示词的方法
  console.log('获取最新提示词，使用获取所有提示词的方法');

  // 获取所有提示词并选择最新的一个
  const allPrompts = await getPrompts(modelTarget);

  if (allPrompts.length === 0) {
    throw new Error('没有找到任何提示词');
  }

  // 按照创建时间或ID排序，选择最新的一个
  const sortedPrompts = [...allPrompts].sort((a, b) => {
    // 如果有创建时间，按创建时间排序
    if (a.created_at && b.created_at) {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    }
    // 否则按ID排序，假设ID越大越新
    return b.id - a.id;
  });

  // 返回第一个（最新的）提示词
  console.log('找到最新提示词:', sortedPrompts[0]);
  return sortedPrompts[0];
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
