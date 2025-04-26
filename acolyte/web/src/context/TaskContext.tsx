import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { TaskResponse, TaskResultResponse } from '@/api';

// 定义任务状态类型
interface TaskState {
  tasks: TaskResponse[];
  currentTask: TaskResponse | null;
  taskResults: Record<number, TaskResultResponse[]>;
  loading: boolean;
  error: string | null;
}

// 定义操作类型
type TaskAction =
  | { type: 'SET_TASKS'; payload: TaskResponse[] }
  | { type: 'SET_CURRENT_TASK'; payload: TaskResponse | null }
  | { type: 'SET_TASK_RESULTS'; payload: { taskId: number; results: TaskResultResponse[] } }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null };

// 初始状态
const initialState: TaskState = {
  tasks: [],
  currentTask: null,
  taskResults: {},
  loading: false,
  error: null,
};

// 创建上下文
const TaskContext = createContext<{
  state: TaskState;
  dispatch: React.Dispatch<TaskAction>;
}>({
  state: initialState,
  dispatch: () => null,
});

// Reducer函数
function taskReducer(state: TaskState, action: TaskAction): TaskState {
  switch (action.type) {
    case 'SET_TASKS':
      return { ...state, tasks: action.payload };
    case 'SET_CURRENT_TASK':
      return { ...state, currentTask: action.payload };
    case 'SET_TASK_RESULTS':
      return {
        ...state,
        taskResults: {
          ...state.taskResults,
          [action.payload.taskId]: action.payload.results,
        },
      };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    default:
      return state;
  }
}

// 提供者组件
export function TaskProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(taskReducer, initialState);

  return (
    <TaskContext.Provider value={{ state, dispatch }}>
      {children}
    </TaskContext.Provider>
  );
}

// 自定义Hook，用于访问上下文
export function useTask() {
  const context = useContext(TaskContext);
  if (context === undefined) {
    throw new Error('useTask must be used within a TaskProvider');
  }
  return context;
}
