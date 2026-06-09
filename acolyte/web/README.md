# Acolyte Web

Acolyte 内容分析评估系统的前端界面。基于 React + TypeScript + Vite + Tailwind CSS v4 + shadcn UI。

## 技术栈

- **React 19** + **TypeScript 6**
- **Vite 8** — 构建工具
- **Tailwind CSS v4** — CSS 框架
- **shadcn UI** — 基于 Radix UI 的组件库
- **React Router 7** — 前端路由
- **Axios** — HTTP 请求
- **Vitest 4** — 单元测试
- **bun** — 包管理器和运行时

## 开发

```bash
bun install           # 安装依赖
bun run dev           # 启动开发服务器 (http://localhost:5173)
bun run build         # 生产构建
bun run test          # 运行测试 (26 passed)
bun run lint          # ESLint
bun run format        # Prettier 格式化
```

确保后端 API 服务已在 `http://localhost:8000` 运行。

## 项目结构

```
acolyte/web/
├── src/
│   ├── api/              # API 接口层
│   ├── components/       # 可复用组件
│   │   ├── common/       # 通用组件 (LoadingSpinner, PageTitle)
│   │   ├── layout/       # 布局组件 (Header, Footer, Layout)
│   │   ├── tasks/        # 任务相关组件 (TaskCard)
│   │   └── ui/           # shadcn UI 组件
│   ├── context/          # React Context (App, Task, Llm, Prompt)
│   ├── pages/            # 页面组件
│   │   ├── HomePage.tsx          # 首页
│   │   ├── AnalyzePage.tsx       # 内容分析
│   │   ├── HistoryPage.tsx       # 历史记录
│   │   ├── TaskResultPage.tsx    # 任务结果
│   │   ├── LlmConfigPage.tsx     # LLM 配置
│   │   ├── PromptConfigPage.tsx  # 提示词管理
│   │   ├── SystemConfigPage.tsx  # 系统设置
│   │   └── TestApiPage.tsx       # API 测试
│   └── lib/              # 工具函数
├── public/               # 静态资源
├── index.html            # HTML 入口
├── vite.config.ts        # Vite 配置
├── vitest.config.ts      # 测试配置
└── eslint.config.js      # ESLint 配置
```

## 环境变量

在 `.env` 文件中配置（参考 `.env.example`）：

- `VITE_API_URL` — API 服务器地址，默认 `http://localhost:8000`
