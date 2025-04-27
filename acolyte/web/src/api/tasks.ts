import apiClient from './config';

export interface TaskCreateRequest {
  content: string;
  processing_mode: 'single' | 'multiple' | 'multiple_with_review';
  prompt_id?: number;
  llm_ids?: number[];
}

export interface TaskResponse {
  id: number;
  content: string;
  processing_mode: string;
  status: string;
  prompt_id?: number;
  created_at?: string;
  updated_at?: string;
}

export interface TaskResultResponse {
  id: number;
  task_id: number;
  llm_id: number;
  bias_index?: number;
  misleading_index?: number;
  hidden_intent_index?: number;
  credibility_score?: number;
  is_review_result: boolean;
  raw_response?: string;
}

// 创建任务
export const createTask = async (taskData: TaskCreateRequest) => {
  const response = await apiClient.post<TaskResponse>('/tasks', taskData);
  return response.data;
};

// 获取任务列表
export const getTasks = async (status?: string, skip = 0, limit = 100) => {
  const params = { status, skip, limit };
  const response = await apiClient.get<TaskResponse[]>('/tasks', { params });
  return response.data;
};

// 获取特定任务
export const getTask = async (taskId: number) => {
  const response = await apiClient.get<TaskResponse>(`/tasks/${taskId}`);
  return response.data;
};

// 获取任务最终结果
export const getTaskFinalResult = async (taskId: number, includeRawResponse = false) => {
  const params = { include_raw_response: includeRawResponse };
  const response = await apiClient.get<TaskResultResponse>(`/tasks/${taskId}/final-result`, { params });
  return response.data;
};

// 获取任务所有结果
export const getTaskResults = async (taskId: number, includeRawResponse = false) => {
  const params = { include_raw_response: includeRawResponse };
  const response = await apiClient.get<TaskResultResponse[]>(`/tasks/${taskId}/results`, { params });
  return response.data;
};

// 删除特定任务
export const deleteTask = async (taskId: number) => {
  try {
    console.log(`删除任务: ID=${taskId}`);
    const response = await apiClient.delete(`/tasks/${taskId}`);
    console.log(`删除任务成功: ID=${taskId}`, response.data);
    return response.data;
  } catch (error) {
    console.error(`删除任务失败: ID=${taskId}`, error);
    throw error;
  }
};

// 批量删除任务
export const deleteTasks = async (taskIds: number[]) => {
  try {
    console.log(`批量删除任务: IDs=${taskIds.join(',')}`);
    const response = await apiClient.post('/tasks/batch-delete', { task_ids: taskIds });
    console.log(`批量删除任务成功: 数量=${taskIds.length}`, response.data);
    return response.data;
  } catch (error) {
    console.error(`批量删除任务失败: IDs=${taskIds.join(',')}`, error);
    throw error;
  }
};

// 清空所有历史记录
export const clearAllTasks = async () => {
  try {
    console.log('清空所有历史记录');
    const response = await apiClient.post('/tasks/clear-all');
    console.log('清空所有历史记录成功', response.data);
    return response.data;
  } catch (error) {
    console.error('清空所有历史记录失败', error);
    throw error;
  }
};
