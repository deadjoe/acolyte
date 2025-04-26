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

      // 直接使用fetch API获取数据
      const apiUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/tasks${statusFilter ? `?status=${statusFilter}` : ''}`;
      console.log('请求URL:', apiUrl);

      const response = await fetch(apiUrl);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('获取到的任务列表:', data);

      // 更新本地状态和Context状态
      setTasks(data);
      dispatch({ type: 'SET_TASKS', payload: data });

      // 如果是自动刷新且有新任务，显示通知
      if (state.tasks.length > 0 && data.length > state.tasks.length) {
        toast.info('发现新的任务');
      }

    } catch (error) {
      console.error('获取任务列表失败:', error);
      dispatch({ type: 'SET_ERROR', payload: '获取任务列表失败' });

      // 只在第一次加载失败时显示错误通知
      if (state.tasks.length === 0) {
        toast.error('获取任务列表失败');
      }
    } finally {
      setLoading(false);
      dispatch({ type: 'SET_LOADING', payload: false });
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
  const filteredTasks = tasks.filter(task =>
    task.content.toLowerCase().includes(searchTerm.toLowerCase())
  );

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
          value={statusFilter}
          onValueChange={(value) => setStatusFilter(value || undefined)}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="所有状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">所有状态</SelectItem>
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
                    <TableCell>{formatDate(task.created_at)}</TableCell>
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
