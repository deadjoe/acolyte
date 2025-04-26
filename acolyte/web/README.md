# Acolyte Web 前端

Acolyte内容分析评估系统的Web前端界面，基于React、Tailwind CSS和shadcn UI构建。

## 技术栈

- **React**: 用于构建用户界面的JavaScript库
- **TypeScript**: 类型安全的JavaScript超集
- **Vite**: 现代前端构建工具
- **Tailwind CSS**: 实用优先的CSS框架
- **shadcn UI**: 基于Radix UI和Tailwind CSS的组件库
- **React Router**: 用于前端路由
- **Axios**: 用于HTTP请求
- **React Context API**: 用于状态管理

## 开发环境设置

### 前提条件

- Node.js 18+
- pnpm (推荐) 或 npm

### 安装依赖

```bash
cd acolyte/web
pnpm install
```

### 开发服务器

```bash
pnpm dev
```

这将启动开发服务器，通常在 http://localhost:5173 上运行。

### 构建生产版本

```bash
pnpm build
```

构建后的文件将位于 `dist` 目录中。

## 项目结构

```
acolyte/web/
├── public/                  # 静态资源
├── src/                     # 源代码
│   ├── api/                 # API调用
│   │   ├── tasks.ts         # 任务相关API
│   │   ├── llms.ts          # LLM配置相关API
│   │   ├── prompts.ts       # 提示词相关API
│   │   └── config.ts        # 配置相关API
│   ├── components/          # 可复用组件
│   │   ├── common/          # 通用组件
│   │   ├── layout/          # 布局组件
│   │   ├── tasks/           # 任务相关组件
│   │   ├── llms/            # LLM相关组件
│   │   └── prompts/         # 提示词相关组件
│   ├── context/             # React Context
│   │   ├── AppContext.tsx   # 应用状态上下文
│   │   ├── TaskContext.tsx  # 任务状态上下文
│   │   ├── LlmContext.tsx   # LLM配置状态上下文
│   │   └── PromptContext.tsx# 提示词状态上下文
│   ├── pages/               # 页面组件
│   │   ├── HomePage.tsx     # 首页
│   │   ├── AnalyzePage.tsx  # 内容分析页面
│   │   ├── HistoryPage.tsx  # 历史记录页面
│   │   └── LlmConfigPage.tsx# LLM配置页面
│   ├── utils/               # 工具函数
│   ├── App.tsx              # 应用主组件
│   ├── main.tsx             # 入口文件
│   └── index.css            # 全局样式
├── .env                     # 环境变量
├── package.json             # 项目依赖
├── vite.config.ts           # Vite配置
├── tailwind.config.js       # Tailwind配置
└── README.md                # 项目说明
```

## 环境变量

在 `.env` 文件中配置以下环境变量：

- `VITE_API_URL`: API服务器的URL，默认为 `http://localhost:8000/api`

## 主要功能

- **内容分析**: 分析文本内容中的偏见、误导性和隐藏意图
- **历史记录**: 查看和管理历史分析任务
- **LLM配置**: 管理LLM配置，包括API密钥、模型名称等
- **提示词管理**: 管理提示词模板

## 与后端集成

Web前端通过API与后端服务进行通信。确保后端服务正在运行，并且API URL配置正确。

## 贡献

欢迎贡献代码、报告问题或提出改进建议。
