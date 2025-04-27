import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Loader2, Search, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { TaskResponse } from '@/api';
import { useTask } from '@/context/TaskContext';
import { formatDateTime } from '@/utils/date';

export function HistoryPage() {
  const { state, dispatch } = useTask();
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  // 任务列表状态
  const [tasks, setTasks] = useState<TaskResponse[]>([]);

  // 加载任务列表
  const loadTasks = async () => {
    try {
      setLoading(true);

      console.log('开始获取任务列表, 状态过滤:', statusFilter);

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
          status: "processing",
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
        },
        {
          id: 996,
          content: "第四个测试任务 - 失败状态",
          processing_mode: "single",
          status: "failed",
          prompt_id: 1,
          created_at: "2025-04-26 19:30:00",
          updated_at: "2025-04-26 19:31:00"
        },
        {
          id: 995,
          content: "第五个测试任务 - 等待中状态",
          processing_mode: "multiple",
          status: "pending",
          prompt_id: 1,
          created_at: "2025-04-26 19:20:00",
          updated_at: "2025-04-26 19:21:00"
        }
      ];

      console.log('使用测试数据:', testData);
      setTasks(testData);

      // 直接更新本地状态，不使用Context
      // dispatch({ type: 'SET_TASKS', payload: testData });

      // 显示成功通知
      toast.success(`已加载测试数据`);

      // 直接使用fetch API获取数据
      const apiUrl = `${import.meta.env.VITE_API_URL}/api/tasks${statusFilter ? `?status=${statusFilter}` : ''}`;
      console.log('请求URL:', apiUrl);

      // 尝试从API获取真实数据
      try {
        console.log('尝试从API获取真实数据');
        const response = await fetch(apiUrl);
        console.log('API响应状态:', response.status);

        if (!response.ok) {
          console.error(`HTTP error! status: ${response.status}`);
          toast.error(`API请求失败: ${response.status}`);
        } else {
          const responseText = await response.text();
          console.log('API响应文本:', responseText);

          try {
            if (responseText.trim()) {
              const data = JSON.parse(responseText);
              console.log('解析后的数据:', data);

              if (Array.isArray(data)) {
                console.log('数据是数组, 长度:', data.length);
                setTasks(data);
                // dispatch({ type: 'SET_TASKS', payload: data });

                // 显示成功通知
                toast.success(`成功获取${data.length}条任务记录`);
              } else {
                console.error('数据不是数组:', data);
                toast.error('获取的数据格式不正确');
              }
            } else {
              console.warn('API响应为空');
              toast.warning('API响应为空');
            }
          } catch (parseError) {
            console.error('解析JSON失败:', parseError);
            toast.error('解析响应数据失败');
          }
        }
      } catch (fetchError) {
        console.error('fetch请求失败:', fetchError);
        toast.error(`API请求失败: ${fetchError.message}`);
      }
    } catch (error) {
      console.error('获取任务列表失败:', error);
      // dispatch({ type: 'SET_ERROR', payload: '获取任务列表失败' });

      // 只在第一次加载失败时显示错误通知
      if (tasks.length === 0) {
        toast.error('获取任务列表失败');
      }
    } finally {
      setLoading(false);
      // dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  // 初始加载和自动刷新
  useEffect(() => {
    loadTasks();

    // 设置自动刷新（每30秒刷新一次）
    const refreshInterval = setInterval(() => {
      loadTasks();
    }, 30000);

    return () => clearInterval(refreshInterval);
  }, [statusFilter]);

  // 过滤任务
  console.log('当前任务列表:', tasks);
  console.log('Context中的任务列表:', state.tasks);

  // 使用本地任务列表，不使用Context
  const tasksToUse = tasks;
  console.log('使用的任务列表:', tasksToUse);

  const filteredTasks = tasksToUse.filter(task =>
    task.content.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // 使用导入的formatDateTime函数，不再需要本地定义

  // 获取状态标签样式
  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'processing':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
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

  // 获取处理模式中文名称
  const getModeName = (mode: string) => {
    const normalizedMode = mode.toLowerCase();
    switch (normalizedMode) {
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">历史记录</h1>
        <Button onClick={loadTasks} variant="outline" size="icon">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="搜索内容..."
            className="pl-8"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <Select
          value={statusFilter || "all"}
          onValueChange={(value) => setStatusFilter(value === "all" ? undefined : value)}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="所有状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">所有状态</SelectItem>
            <SelectItem value="completed">已完成</SelectItem>
            <SelectItem value="processing">处理中</SelectItem>
            <SelectItem value="pending">等待中</SelectItem>
            <SelectItem value="failed">失败</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>内容</TableHead>
                <TableHead>处理模式</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredTasks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    没有找到任务记录
                  </TableCell>
                </TableRow>
              ) : (
                filteredTasks.map((task) => (
                  <TableRow key={task.id}>
                    <TableCell>{task.id}</TableCell>
                    <TableCell className="max-w-[300px] truncate">{task.content}</TableCell>
                    <TableCell>{getModeName(task.processing_mode)}</TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded-full text-xs ${getStatusStyle(task.status)}`}>
                        {getStatusName(task.status)}
                      </span>
                    </TableCell>
                    <TableCell>{formatDateTime(task.created_at)}</TableCell>
                    <TableCell>
                      <Link to={`/result/${task.id}`}>
                        <Button variant="outline" size="sm">
                          查看结果
                        </Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
