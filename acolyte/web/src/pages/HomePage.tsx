import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { getTasks } from '@/api';
import { TaskCard } from '@/components/tasks';
import { LoadingSpinner } from '@/components/common';
import { useTask } from '@/context/TaskContext';

export function HomePage() {
  const { state, dispatch } = useTask();
  const [loading, setLoading] = useState(false);
  // 添加本地状态来管理任务列表
  const [localTasks, setLocalTasks] = useState<TaskResponse[]>([]);

  // 加载最近任务
  useEffect(() => {
    const loadRecentTasks = async () => {
      try {
        setLoading(true);

        // 添加硬编码的测试数据，以便验证渲染逻辑是否正常
        const testData = [
          {
            id: 999,
            content: "测试任务内容 - 这是一个硬编码的测试数据，用于验证渲染逻辑",
            processing_mode: "SINGLE",
            status: "completed",
            prompt_id: 1,
            created_at: "2025-04-26 20:00:00",
            updated_at: "2025-04-26 20:01:00"
          },
          {
            id: 998,
            content: "另一个测试任务 - 处理中状态",
            processing_mode: "multiple",
            status: "completed",
            prompt_id: 1,
            created_at: "2025-04-26 19:50:00",
            updated_at: "2025-04-26 19:51:00"
          },
          {
            id: 997,
            content: "第三个测试任务 - 评议模式",
            processing_mode: "multiple_with_review",
            status: "completed",
            prompt_id: 1,
            created_at: "2025-04-26 19:40:00",
            updated_at: "2025-04-26 19:41:00"
          }
        ];

        console.log('使用测试数据:', testData);
        setLocalTasks(testData);
        dispatch({ type: 'SET_TASKS', payload: testData });

        // 获取最近5个已完成的任务
        try {
          const apiUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/tasks?status=completed&limit=5`;
          console.log('请求URL:', apiUrl);

          const response = await fetch(apiUrl);
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const responseText = await response.text();
          console.log('API响应文本:', responseText);

          try {
            if (responseText.trim()) {
              const data = JSON.parse(responseText);
              console.log('解析后的数据:', data);

              if (Array.isArray(data) && data.length > 0) {
                setLocalTasks(data);
                dispatch({ type: 'SET_TASKS', payload: data });
                console.log('成功获取并设置任务列表');
              } else {
                console.warn('API返回的数据不是数组或为空数组');
              }
            } else {
              console.warn('API响应为空');
            }
          } catch (parseError) {
            console.error('解析JSON失败:', parseError);
          }
        } catch (apiError) {
          console.error('API获取最近任务失败:', apiError);
        }

      } catch (error) {
        console.error('获取最近任务失败:', error);
      } finally {
        setLoading(false);
      }
    };

    loadRecentTasks();
  }, [dispatch]);

  return (
    <div className="space-y-8">
      <section className="py-12 md:py-16 lg:py-20">
        <div className="container px-4 md:px-6">
          <div className="flex flex-col items-center space-y-4 text-center">
            <h1 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl lg:text-6xl">
              Acolyte 内容分析评估系统
            </h1>
            <p className="max-w-[700px] text-gray-500 md:text-xl dark:text-gray-400">
              专注于检测文本内容中的偏见、误导性和隐藏意图，提供量化评分和详细分析。
            </p>
            <div className="flex flex-col gap-2 min-[400px]:flex-row">
              <Link to="/analyze">
                <Button size="lg">开始分析</Button>
              </Link>
              <Link to="/history">
                <Button variant="outline" size="lg">查看历史</Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="py-8 md:py-12 lg:py-16">
        <div className="container px-4 md:px-6">
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>单LLM分析</CardTitle>
                <CardDescription>使用单个LLM进行内容分析</CardDescription>
              </CardHeader>
              <CardContent>
                <p>使用默认或指定的LLM对内容进行分析，获取偏见指数、误导性指数、隐藏意图指数和综合可信度评分。</p>
              </CardContent>
              <CardFooter>
                <Link to="/analyze?mode=single">
                  <Button variant="outline">使用此模式</Button>
                </Link>
              </CardFooter>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>多LLM并行分析</CardTitle>
                <CardDescription>使用多个LLM并行分析内容</CardDescription>
              </CardHeader>
              <CardContent>
                <p>同时使用多个LLM对内容进行分析，获取多个分析结果，便于比较不同LLM的评估差异。</p>
              </CardContent>
              <CardFooter>
                <Link to="/analyze?mode=multiple">
                  <Button variant="outline">使用此模式</Button>
                </Link>
              </CardFooter>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>多LLM评议分析</CardTitle>
                <CardDescription>使用评议者LLM对多个分析结果进行评估</CardDescription>
              </CardHeader>
              <CardContent>
                <p>先使用多个LLM分析内容，然后由评议者LLM对这些结果进行评估，选出最佳结果或综合多个结果。</p>
              </CardContent>
              <CardFooter>
                <Link to="/analyze?mode=multiple_with_review">
                  <Button variant="outline">使用此模式</Button>
                </Link>
              </CardFooter>
            </Card>
          </div>
        </div>
      </section>

      <section className="py-8 md:py-12">
        <div className="container px-4 md:px-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold tracking-tight">最近分析</h2>
            <Link to="/history">
              <Button variant="ghost" size="sm">查看全部</Button>
            </Link>
          </div>

          {loading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner text="加载最近任务..." />
            </div>
          ) : localTasks.length > 0 ? (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {localTasks.map((task) => (
                <TaskCard key={task.id} task={task} />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                没有找到最近的分析任务
              </CardContent>
            </Card>
          )}
        </div>
      </section>
    </div>
  );
}
