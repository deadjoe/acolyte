import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { PromptResponse } from '@/api';

// 定义提示词状态类型
interface PromptState {
  prompts: PromptResponse[];
  currentPrompt: PromptResponse | null;
  loading: boolean;
  error: string | null;
}

// 定义操作类型
type PromptAction =
  | { type: 'SET_PROMPTS'; payload: PromptResponse[] }
  | { type: 'SET_CURRENT_PROMPT'; payload: PromptResponse | null }
  | { type: 'ADD_PROMPT'; payload: PromptResponse }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null };

// 初始状态
const initialState: PromptState = {
  prompts: [],
  currentPrompt: null,
  loading: false,
  error: null,
};

// 创建上下文
const PromptContext = createContext<{
  state: PromptState;
  dispatch: React.Dispatch<PromptAction>;
}>({
  state: initialState,
  dispatch: () => null,
});

// Reducer函数
function promptReducer(state: PromptState, action: PromptAction): PromptState {
  switch (action.type) {
    case 'SET_PROMPTS':
      return { ...state, prompts: action.payload };
    case 'SET_CURRENT_PROMPT':
      return { ...state, currentPrompt: action.payload };
    case 'ADD_PROMPT':
      return { ...state, prompts: [...state.prompts, action.payload] };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    default:
      return state;
  }
}

// 提供者组件
export function PromptProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(promptReducer, initialState);

  return (
    <PromptContext.Provider value={{ state, dispatch }}>
      {children}
    </PromptContext.Provider>
  );
}

// 自定义Hook，用于访问上下文
export function usePrompt() {
  const context = useContext(PromptContext);
  if (context === undefined) {
    throw new Error('usePrompt must be used within a PromptProvider');
  }
  return context;
}
