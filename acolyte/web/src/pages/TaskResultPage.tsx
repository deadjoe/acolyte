import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Loader2, ArrowLeft, FileText, BarChart, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { getTask, getTaskResults, getLlm } from '@/api';
import { useTask } from '@/context/TaskContext';

export function TaskResultPage() {
  const { id } = useParams<{ id: string }>();
  const taskId = parseInt(id || '0');
  const { state, dispatch } = useTask();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [llmNames, setLlmNames] = useState<Record<number, string>>({});

  // 加载任务和结果
  useEffect(() => {
    const loadTaskAndResults = async () => {
      if (!taskId) return;

      try {
        setLoading(true);

        // 获取任务信息
        const task = await getTask(taskId);
        dispatch({ type: 'SET_CURRENT_TASK', payload: task });

        // 获取任务结果
        const results = await getTaskResults(taskId, true);
        dispatch({
          type: 'SET_TASK_RESULTS',
          payload: { taskId, results },
        });

        // 获取LLM名称
        const llmIds = [...new Set(results.map(result => result.llm_id))];
        const llmNamesMap: Record<number, string> = {};

        for (const llmId of llmIds) {
          try {
            const llm = await getLlm(llmId);
            llmNamesMap[llmId] = llm.name;
          } catch (error) {
            console.error(`获取LLM信息失败 (ID: ${llmId}):`, error);
            llmNamesMap[llmId] = `LLM #${llmId}`;
          }
        }

        setLlmNames(llmNamesMap);

      } catch (error) {
        console.error('加载任务和结果失败:', error);
        toast.error('加载任务和结果失败');
      } finally {
        setLoading(false);
      }
    };

    loadTaskAndResults();

    // 如果任务未完成，设置自动刷新
    const refreshInterval = setInterval(async () => {
      try {
        // 获取最新任务状态
        const task = await getTask(taskId);

        // 如果任务状态已更新，重新加载结果
        if (task.status !== state.currentTask?.status) {
          dispatch({ type: 'SET_CURRENT_TASK', payload: task });

          if (task.status === 'completed') {
            toast.success('任务处理完成');
            const results = await getTaskResults(taskId, true);
            dispatch({
              type: 'SET_TASK_RESULTS',
              payload: { taskId, results },
            });

            // 获取LLM名称
            const llmIds = [...new Set(results.map(result => result.llm_id))];
            const llmNamesMap: Record<number, string> = {};

            for (const llmId of llmIds) {
              try {
                const llm = await getLlm(llmId);
                llmNamesMap[llmId] = llm.name;
              } catch (error) {
                console.error(`获取LLM信息失败 (ID: ${llmId}):`, error);
                llmNamesMap[llmId] = `LLM #${llmId}`;
              }
            }

            setLlmNames(llmNamesMap);
          } else if (task.status === 'failed') {
            toast.error('任务处理失败');
          }
        }
      } catch (error) {
        console.error('自动刷新任务状态失败:', error);
      }
    }, 5000); // 每5秒刷新一次

    return () => clearInterval(refreshInterval);
  }, [taskId, dispatch, state.currentTask?.status]);

  // 获取处理模式中文名称
  const getModeName = (mode: string) => {
    switch (mode) {
      case 'single':
        return '单LLM';
      case 'multiple':
        return '多LLM并行';
      case 'multiple_with_review':
        return '多LLM评议';
      default:
        return mode;
    }
  };

  // 获取状态中文名称
  const getStatusName = (status: string) => {
    switch (status) {
      case 'completed':
        return '已完成';
      case 'processing':
        return '处理中';
      case 'pending':
        return '等待中';
      case 'failed':
        return '失败';
      default:
        return status;
    }
  };

  // 格式化日期
  const formatDate = (dateString?: string) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 获取结果类型名称
  const getResultTypeName = (isReviewResult: boolean) => {
    return isReviewResult ? '评议结果' : '分析结果';
  };

  // 渲染评分卡片
  const renderScoreCard = (title: string, score: number | undefined, description: string) => {
    if (score === undefined) return null;

    let color = 'bg-gray-100 text-gray-800';
    if (score < 30) color = 'bg-green-100 text-green-800';
    else if (score < 60) color = 'bg-yellow-100 text-yellow-800';
    else color = 'bg-red-100 text-red-800';

    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="text-2xl font-bold">{score}</div>
            <div className={`px-2 py-1 rounded-full text-xs ${color}`}>
              {score < 30 ? '低' : score < 60 ? '中' : '高'}
            </div>
          </div>
          <div className="mt-4 h-2 w-full rounded-full bg-gray-200">
            <div
              className={`h-2 rounded-full ${
                score < 30
                  ? 'bg-green-500'
                  : score < 60
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              }`}
              style={{ width: `${score}%` }}
            />
          </div>
        </CardContent>
      </Card>
    );
  };

  // 渲染可信度评分卡片
  const renderCredibilityCard = (score: number | undefined) => {
    if (score === undefined) return null;

    let color = 'bg-gray-100 text-gray-800';
    if (score > 70) color = 'bg-green-100 text-green-800';
    else if (score > 40) color = 'bg-yellow-100 text-yellow-800';
    else color = 'bg-red-100 text-red-800';

    return (
      <Card className="col-span-full">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">综合可信度评分</CardTitle>
          <CardDescription>内容的整体可信度评估</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="text-3xl font-bold">{score}</div>
            <div className={`px-2 py-1 rounded-full text-xs ${color}`}>
              {score > 70 ? '高' : score > 40 ? '中' : '低'}
            </div>
          </div>
          <div className="mt-4 h-3 w-full rounded-full bg-gray-200">
            <div
              className={`h-3 rounded-full ${
                score > 70
                  ? 'bg-green-500'
                  : score > 40
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              }`}
              style={{ width: `${score}%` }}
            />
          </div>
        </CardContent>
      </Card>
    );
  };

  const task = state.currentTask;
  const results = state.taskResults[taskId] || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Link to="/history">
            <Button variant="ghost" size="sm" className="mr-2">
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回历史记录
            </Button>
          </Link>
          <h1 className="text-3xl font-bold tracking-tight">任务结果</h1>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={async () => {
            try {
              setRefreshing(true);
              const task = await getTask(taskId);
              dispatch({ type: 'SET_CURRENT_TASK', payload: task });

              const results = await getTaskResults(taskId, true);
              dispatch({
                type: 'SET_TASK_RESULTS',
                payload: { taskId, results },
              });

              toast.success('刷新成功');
            } catch (error) {
              console.error('刷新失败:', error);
              toast.error('刷新失败');
            } finally {
              setRefreshing(false);
            }
          }}
          disabled={refreshing}
        >
          {refreshing ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          刷新
        </Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : task ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle>任务信息</CardTitle>
              <CardDescription>ID: {task.id}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <h3 className="text-sm font-medium">处理模式</h3>
                  <p>{getModeName(task.processing_mode)}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium">状态</h3>
                  <p>{getStatusName(task.status)}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium">创建时间</h3>
                  <p>{formatDate(task.created_at)}</p>
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium">内容</h3>
                <p className="mt-1 whitespace-pre-wrap rounded-md border p-4 text-sm">
                  {task.content}
                </p>
              </div>
            </CardContent>
          </Card>

          {results.length > 0 ? (
            <Tabs defaultValue="results" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="results">
                  <BarChart className="mr-2 h-4 w-4" />
                  分析结果
                </TabsTrigger>
                <TabsTrigger value="raw">
                  <FileText className="mr-2 h-4 w-4" />
                  原始响应
                </TabsTrigger>
              </TabsList>

              <TabsContent value="results" className="space-y-4">
                {results.map((result) => (
                  <Card key={result.id} className="overflow-hidden">
                    <CardHeader className="bg-muted/50">
                      <div className="flex items-center justify-between">
                        <CardTitle>
                          {llmNames[result.llm_id] || `LLM #${result.llm_id}`}
                        </CardTitle>
                        <span className="text-sm text-muted-foreground">
                          {getResultTypeName(result.is_review_result)}
                        </span>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-6">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {renderScoreCard(
                          '偏见指数',
                          result.bias_index,
                          '内容中的偏见程度'
                        )}
                        {renderScoreCard(
                          '误导性指数',
                          result.misleading_index,
                          '内容的误导性程度'
                        )}
                        {renderScoreCard(
                          '隐藏意图指数',
                          result.hidden_intent_index,
                          '内容中的隐藏意图程度'
                        )}
                        {renderCredibilityCard(result.credibility_score)}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </TabsContent>

              <TabsContent value="raw" className="space-y-4">
                {results.map((result) => (
                  <Card key={`raw-${result.id}`}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle>
                          {llmNames[result.llm_id] || `LLM #${result.llm_id}`}
                        </CardTitle>
                        <span className="text-sm text-muted-foreground">
                          {getResultTypeName(result.is_review_result)}
                        </span>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <pre className="whitespace-pre-wrap rounded-md bg-muted p-4 text-sm">
                        {result.raw_response || '无原始响应'}
                      </pre>
                    </CardContent>
                  </Card>
                ))}
              </TabsContent>
            </Tabs>
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                {task.status === 'completed' ? (
                  '没有找到分析结果'
                ) : (
                  '任务尚未完成，请稍后查看结果'
                )}
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            没有找到任务信息
          </CardContent>
        </Card>
      )}
    </div>
  );
}
