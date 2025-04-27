import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { LlmConfigResponse } from '@/api';

// 定义LLM状态类型
interface LlmState {
  llms: LlmConfigResponse[];
  defaultLlm: LlmConfigResponse | null;
  loading: boolean;
  error: string | null;
}

// 定义操作类型
type LlmAction =
  | { type: 'SET_LLMS'; payload: LlmConfigResponse[] }
  | { type: 'SET_DEFAULT_LLM'; payload: LlmConfigResponse | null }
  | { type: 'ADD_LLM'; payload: LlmConfigResponse }
  | { type: 'UPDATE_LLM'; payload: LlmConfigResponse }
  | { type: 'REMOVE_LLM'; payload: number }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null };

// 初始状态
const initialState: LlmState = {
  llms: [],
  defaultLlm: null,
  loading: false,
  error: null,
};

// 创建上下文
const LlmContext = createContext<{
  state: LlmState;
  dispatch: React.Dispatch<LlmAction>;
}>({
  state: initialState,
  dispatch: () => null,
});

// Reducer函数
function llmReducer(state: LlmState, action: LlmAction): LlmState {
  switch (action.type) {
    case 'SET_LLMS':
      return { ...state, llms: action.payload };
    case 'SET_DEFAULT_LLM':
      return { ...state, defaultLlm: action.payload };
    case 'ADD_LLM':
      return { ...state, llms: [...state.llms, action.payload] };
    case 'UPDATE_LLM':
      return {
        ...state,
        llms: state.llms.map(llm => (llm.id === action.payload.id ? action.payload : llm)),
        defaultLlm:
          state.defaultLlm?.id === action.payload.id && action.payload.is_default
            ? action.payload
            : state.defaultLlm,
      };
    case 'REMOVE_LLM':
      return {
        ...state,
        llms: state.llms.filter(llm => llm.id !== action.payload),
        defaultLlm: state.defaultLlm?.id === action.payload ? null : state.defaultLlm,
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
export function LlmProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(llmReducer, initialState);

  return <LlmContext.Provider value={{ state, dispatch }}>{children}</LlmContext.Provider>;
}

// 自定义Hook，用于访问上下文
export function useLlm() {
  const context = useContext(LlmContext);
  if (context === undefined) {
    throw new Error('useLlm must be used within a LlmProvider');
  }
  return context;
}
