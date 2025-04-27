import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import { Layout } from '@/components/layout';
import { ThemeProvider } from '@/components/ThemeProvider';
import { AppProvider, TaskProvider, LlmProvider, PromptProvider } from '@/context';
import {
  HomePage,
  AnalyzePage,
  HistoryPage,
  LlmConfigPage,
  PromptConfigPage,
  TaskResultPage,
  SystemConfigPage,
  TestApiPage
} from '@/pages';

function App() {
  return (
    <AppProvider>
      <ThemeProvider>
        <TaskProvider>
          <LlmProvider>
            <PromptProvider>
              <Router>
                <Layout>
                  <Routes>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/analyze" element={<AnalyzePage />} />
                    <Route path="/history" element={<HistoryPage />} />
                    <Route path="/result/:id" element={<TaskResultPage />} />
                    <Route path="/config/llm" element={<LlmConfigPage />} />
                    <Route path="/config/prompt" element={<PromptConfigPage />} />
                    <Route path="/config/system" element={<SystemConfigPage />} />
                    <Route path="/test-api" element={<TestApiPage />} />
                  </Routes>
                </Layout>
              </Router>
              <Toaster />
            </PromptProvider>
          </LlmProvider>
        </TaskProvider>
      </ThemeProvider>
    </AppProvider>
  );
}

export default App;
