import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { createTask, getLlms, getPrompts, getLatestPrompt, updateLlm } from '@/api';
import { useLlm } from '@/context/LlmContext';
import { usePrompt } from '@/context/PromptContext';

interface AnalyzeFormData {
  content: string;
  processing_mode: 'single' | 'multiple' | 'multiple_with_review';
  prompt_id?: number;
  llm_ids?: number[];
}

export function AnalyzePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialMode = searchParams.get('mode') as 'single' | 'multiple' | 'multiple_with_review' || 'single';

  const { state: llmState, dispatch: llmDispatch } = useLlm();
  const { state: promptState, dispatch: promptDispatch } = usePrompt();

  const [loading, setLoading] = useState(false);
  const [selectedLlms, setSelectedLlms] = useState<number[]>([]);
  const [selectedPromptId, setSelectedPromptId] = useState<number | undefined>(undefined);

  const { register, handleSubmit, setValue, watch } = useForm<AnalyzeFormData>({
    defaultValues: {
      content: '',
      processing_mode: initialMode,
    },
  });

  const processingMode = watch('processing_mode');

  // 加载LLM列表
  useEffect(() => {
    const fetchLlms = async () => {
      try {
        llmDispatch({ type: 'SET_LOADING', payload: true });
        const llms = await getLlms();
        llmDispatch({ type: 'SET_LLMS', payload: llms });

        // 设置默认LLM
        const defaultLlm = llms.find(llm => llm.is_default);
        if (defaultLlm) {
          llmDispatch({ type: 'SET_DEFAULT_LLM', payload: defaultLlm });
          setSelectedLlms([defaultLlm.id]);
        }
      } catch (error) {
        console.error('获取LLM列表失败:', error);
        llmDispatch({ type: 'SET_ERROR', payload: '获取LLM列表失败' });
      } finally {
        llmDispatch({ type: 'SET_LOADING', payload: false });
      }
    };

    fetchLlms();
  }, [llmDispatch]);

  // 加载提示词列表
  useEffect(() => {
    const fetchPrompts = async () => {
      try {
        promptDispatch({ type: 'SET_LOADING', payload: true });
        const prompts = await getPrompts();
        promptDispatch({ type: 'SET_PROMPTS', payload: prompts });

        // 获取最新提示词
        const latestPrompt = await getLatestPrompt();
        promptDispatch({ type: 'SET_CURRENT_PROMPT', payload: latestPrompt });
        setSelectedPromptId(latestPrompt.id);
      } catch (error) {
        console.error('获取提示词列表失败:', error);
        promptDispatch({ type: 'SET_ERROR', payload: '获取提示词列表失败' });
      } finally {
        promptDispatch({ type: 'SET_LOADING', payload: false });
      }
    };

    fetchPrompts();
  }, [promptDispatch]);

  // 处理LLM选择
  const handleLlmSelect = async (llmId: number) => {
    console.log(`选择LLM ID: ${llmId}, 当前处理模式: ${processingMode}`);

    if (processingMode === 'single') {
      // 在单LLM模式下，只选择一个LLM
      console.log(`单LLM模式: 设置选中的LLM为 [${llmId}]`);
      setSelectedLlms([llmId]);

      // 获取选中的LLM和当前默认LLM
      const selectedLlm = llmState.llms.find(llm => llm.id === llmId);
      const defaultLlm = llmState.llms.find(llm => llm.is_default);

      // 如果选中的LLM不是当前默认LLM，则将其设置为默认LLM
      if (selectedLlm && defaultLlm && llmId !== defaultLlm.id) {
        try {
          // 显示加载状态
          toast.loading('正在设置默认LLM...');

          // 先将当前默认LLM的is_default设置为false
          await updateLlm(defaultLlm.id, { is_default: false });
          console.log(`已将原默认LLM ${defaultLlm.name} (ID=${defaultLlm.id}) 的is_default设置为false`);

          // 再将选中的LLM的is_default设置为true
          const updatedLlm = await updateLlm(llmId, { is_default: true });
          console.log(`已将选中的LLM ${selectedLlm.name} (ID=${llmId}) 的is_default设置为true`);

          // 更新Context中的默认LLM
          llmDispatch({ type: 'SET_DEFAULT_LLM', payload: updatedLlm });

          // 显示成功消息
          toast.success(`已将 ${selectedLlm.name} 设置为默认LLM`);
        } catch (error) {
          console.error('设置默认LLM失败:', error);
          toast.error('设置默认LLM失败');
        }
      }
    } else {
      // 在多LLM模式下，可以选择多个LLM
      if (selectedLlms.includes(llmId)) {
        // 如果已经选中，则取消选择
        const newSelectedLlms = selectedLlms.filter(id => id !== llmId);
        console.log(`多LLM模式: 取消选择LLM ${llmId}, 新的选中列表: [${newSelectedLlms.join(', ')}]`);
        setSelectedLlms(newSelectedLlms);
      } else {
        // 如果未选中，则添加到选中列表
        const newSelectedLlms = [...selectedLlms, llmId];
        console.log(`多LLM模式: 添加选择LLM ${llmId}, 新的选中列表: [${newSelectedLlms.join(', ')}]`);
        setSelectedLlms(newSelectedLlms);
      }
    }
  };

  // 处理提交
  const onSubmit = async (data: AnalyzeFormData) => {
    if (!data.content.trim()) {
      toast.error('请输入要分析的内容');
      return;
    }

    if (processingMode !== 'single' && selectedLlms.length < 2) {
      toast.error('多LLM模式下请至少选择两个LLM');
      return;
    }

    try {
      setLoading(true);

      // 确保在单LLM模式下也发送选定的LLM ID
      const taskData: AnalyzeFormData = {
        content: data.content,
        processing_mode: data.processing_mode,
        prompt_id: selectedPromptId,
        llm_ids: selectedLlms,
      };

      console.log('提交任务数据:', JSON.stringify(taskData, null, 2));

      const result = await createTask(taskData);
      toast.success(`任务创建成功，ID: ${result.id}`);

      // 创建任务后，添加轮询逻辑检查任务状态
      let taskCompleted = false;
      let attempts = 0;
      const maxAttempts = 30; // 最多轮询30次
      const pollInterval = 2000; // 每2秒轮询一次

      const pollTaskStatus = async () => {
        try {
          if (attempts >= maxAttempts) {
            toast.info(`任务正在后台处理，您可以稍后在历史记录中查看结果`);
            navigate(`/history`);
            return;
          }

          attempts++;

          // 获取任务状态
          const taskStatus = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/tasks/${result.id}`).then(res => res.json());

          if (taskStatus.status === 'completed') {
            taskCompleted = true;
            toast.success('任务处理完成');
            navigate(`/result/${result.id}`);
          } else if (taskStatus.status === 'failed') {
            taskCompleted = true;
            toast.error('任务处理失败');
            navigate(`/history`);
          } else {
            // 继续轮询
            setTimeout(pollTaskStatus, pollInterval);
          }
        } catch (error) {
          console.error('轮询任务状态失败:', error);
          toast.error('获取任务状态失败，请在历史记录中查看结果');
          navigate(`/history`);
        }
      };

      // 开始轮询
      setTimeout(pollTaskStatus, pollInterval);

    } catch (error) {
      console.error('创建任务失败:', error);
      toast.error('创建任务失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">内容分析</h1>
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        <Card>
          <CardHeader>
            <CardTitle>分析设置</CardTitle>
            <CardDescription>
              选择处理模式、LLM和提示词模板
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium">处理模式</label>
              <Tabs
                defaultValue={initialMode}
                onValueChange={(value) => {
                  console.log(`切换处理模式: ${value}`);
                  setValue('processing_mode', value as any);

                  // 切换到单LLM模式时，如果有选中的LLM，则保留第一个；否则使用默认LLM
                  if (value === 'single') {
                    const defaultLlm = llmState.llms.find(llm => llm.is_default);
                    if (selectedLlms.length > 0) {
                      console.log(`切换到单LLM模式: 保留第一个选中的LLM ${selectedLlms[0]}`);
                      setSelectedLlms([selectedLlms[0]]);
                    } else if (defaultLlm) {
                      console.log(`切换到单LLM模式: 使用默认LLM ${defaultLlm.id}`);
                      setSelectedLlms([defaultLlm.id]);
                    }
                  }
                }}
                className="w-full"
              >
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="single">单LLM</TabsTrigger>
                  <TabsTrigger value="multiple">多LLM并行</TabsTrigger>
                  <TabsTrigger value="multiple_with_review">多LLM评议</TabsTrigger>
                </TabsList>
                <TabsContent value="single" className="mt-2">
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      使用单个LLM进行内容分析。
                    </p>
                    <div className="bg-blue-100 dark:bg-blue-900 p-2 rounded-md">
                      <p className="text-sm text-blue-800 dark:text-blue-200">
                        <strong>提示：</strong> 在单LLM模式下，选择LLM时会自动将其设置为默认LLM。
                      </p>
                    </div>
                  </div>
                </TabsContent>
                <TabsContent value="multiple" className="mt-2">
                  <p className="text-sm text-muted-foreground">
                    使用多个LLM并行处理任务，返回所有结果。
                  </p>
                </TabsContent>
                <TabsContent value="multiple_with_review" className="mt-2">
                  <p className="text-sm text-muted-foreground">
                    使用多个LLM处理任务，然后由评议者LLM进行评估和投票。
                  </p>
                </TabsContent>
              </Tabs>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">选择LLM</label>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {llmState.llms.map((llm) => (
                  <Button
                    key={llm.id}
                    type="button"
                    variant={selectedLlms.includes(llm.id) ? "default" : "outline"}
                    onClick={() => handleLlmSelect(llm.id)}
                    className="justify-start"
                  >
                    <span className="truncate">{llm.name}</span>
                    {llm.is_default && (
                      <span className="ml-2 text-xs bg-primary/20 px-1 rounded">默认</span>
                    )}
                  </Button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">提示词模板</label>
              <Select
                value={selectedPromptId?.toString()}
                onValueChange={(value) => setSelectedPromptId(parseInt(value))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择提示词模板" />
                </SelectTrigger>
                <SelectContent>
                  {promptState.prompts.map((prompt) => (
                    <SelectItem key={prompt.id} value={prompt.id.toString()}>
                      {prompt.version} {prompt.model_target ? `(${prompt.model_target})` : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">内容</label>
              <Textarea
                {...register('content', { required: true })}
                placeholder="输入要分析的内容..."
                className="min-h-[200px]"
              />
            </div>
          </CardContent>
          <CardFooter>
            <Button type="submit" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              开始分析
            </Button>
          </CardFooter>
        </Card>
      </form>
    </div>
  );
}
