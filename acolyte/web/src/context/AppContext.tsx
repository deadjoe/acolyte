import React, { createContext, useContext, useReducer, ReactNode } from 'react';

// 定义应用状态类型
interface AppState {
  theme: 'light' | 'dark';
  language: 'zh' | 'en';
  notifications: Notification[];
}

// 通知类型
interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
}

// 定义操作类型
type AppAction =
  | { type: 'SET_THEME'; payload: 'light' | 'dark' }
  | { type: 'SET_LANGUAGE'; payload: 'zh' | 'en' }
  | { type: 'ADD_NOTIFICATION'; payload: Omit<Notification, 'id'> }
  | { type: 'REMOVE_NOTIFICATION'; payload: string };

// 初始状态
const initialState: AppState = {
  theme: 'light',
  language: 'zh',
  notifications: [],
};

// 创建上下文
const AppContext = createContext<{
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
}>({
  state: initialState,
  dispatch: () => null,
});

// Reducer函数
function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_THEME':
      return { ...state, theme: action.payload };
    case 'SET_LANGUAGE':
      return { ...state, language: action.payload };
    case 'ADD_NOTIFICATION': {
      const newNotification = {
        id: Date.now().toString(),
        ...action.payload,
      };
      return {
        ...state,
        notifications: [...state.notifications, newNotification],
      };
    }
    case 'REMOVE_NOTIFICATION':
      return {
        ...state,
        notifications: state.notifications.filter(
          notification => notification.id !== action.payload
        ),
      };
    default:
      return state;
  }
}

// 提供者组件
export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  return <AppContext.Provider value={{ state, dispatch }}>{children}</AppContext.Provider>;
}

// 自定义Hook，用于访问上下文
export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}

// 辅助函数
export function useTheme() {
  const { state, dispatch } = useApp();
  return {
    theme: state.theme,
    setTheme: (theme: 'light' | 'dark') => dispatch({ type: 'SET_THEME', payload: theme }),
    toggleTheme: () =>
      dispatch({ type: 'SET_THEME', payload: state.theme === 'light' ? 'dark' : 'light' }),
  };
}

export function useLanguage() {
  const { state, dispatch } = useApp();
  return {
    language: state.language,
    setLanguage: (language: 'zh' | 'en') => dispatch({ type: 'SET_LANGUAGE', payload: language }),
  };
}

export function useNotifications() {
  const { state, dispatch } = useApp();
  return {
    notifications: state.notifications,
    addNotification: (notification: Omit<Notification, 'id'>) =>
      dispatch({ type: 'ADD_NOTIFICATION', payload: notification }),
    removeNotification: (id: string) => dispatch({ type: 'REMOVE_NOTIFICATION', payload: id }),
  };
}
