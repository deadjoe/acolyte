import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import { Layout } from '@/components/layout';
import { AppProvider, TaskProvider, LlmProvider, PromptProvider } from '@/context';
import { HomePage, AnalyzePage, HistoryPage, LlmConfigPage } from '@/pages';

function App() {
  return (
    <AppProvider>
      <TaskProvider>
        <LlmProvider>
          <PromptProvider>
            <Router>
              <Layout>
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/analyze" element={<AnalyzePage />} />
                  <Route path="/history" element={<HistoryPage />} />
                  <Route path="/config/llm" element={<LlmConfigPage />} />
                  {/* 添加更多路由 */}
                </Routes>
              </Layout>
            </Router>
            <Toaster />
          </PromptProvider>
        </LlmProvider>
      </TaskProvider>
    </AppProvider>
  );
}

export default App;
