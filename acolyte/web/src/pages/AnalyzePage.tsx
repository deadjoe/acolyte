import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { createTask, getLlms, getPrompts, getLatestPrompt } from '@/api';
import { useLlm } from '@/context/LlmContext';
import { usePrompt } from '@/context/PromptContext';

interface AnalyzeFormData {
  content: string;
  processing_mode: 'single' | 'multiple' | 'multiple_with_review';
  prompt_id?: number;
  llm_ids?: number[];
}

export function AnalyzePage() {
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
  const handleLlmSelect = (llmId: number) => {
    if (processingMode === 'single') {
      setSelectedLlms([llmId]);
    } else {
      if (selectedLlms.includes(llmId)) {
        setSelectedLlms(selectedLlms.filter(id => id !== llmId));
      } else {
        setSelectedLlms([...selectedLlms, llmId]);
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
      
      const taskData: AnalyzeFormData = {
        content: data.content,
        processing_mode: data.processing_mode,
        prompt_id: selectedPromptId,
        llm_ids: selectedLlms.length > 0 ? selectedLlms : undefined,
      };
      
      const result = await createTask(taskData);
      toast.success(`任务创建成功，ID: ${result.id}`);
      
      // 这里可以添加导航到结果页面的逻辑
      
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
                onValueChange={(value) => setValue('processing_mode', value as any)}
                className="w-full"
              >
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="single">单LLM</TabsTrigger>
                  <TabsTrigger value="multiple">多LLM并行</TabsTrigger>
                  <TabsTrigger value="multiple_with_review">多LLM评议</TabsTrigger>
                </TabsList>
                <TabsContent value="single" className="mt-2">
                  <p className="text-sm text-muted-foreground">
                    使用单个LLM进行内容分析，通常是默认的LLM。
                  </p>
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
