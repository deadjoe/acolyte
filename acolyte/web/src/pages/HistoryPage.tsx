import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Loader2, Search, RefreshCw, Trash2, X, CheckSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { TaskResponse, getTasks, deleteTask, deleteTasks, clearAllTasks } from '@/api';
import { useTask } from '@/context/TaskContext';
import { formatDateTime } from '@/utils/date';

export function HistoryPage() {
  const { state, dispatch } = useTask();
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [selectedTasks, setSelectedTasks] = useState<number[]>([]);
  const [selectMode, setSelectMode] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deletingTaskId, setDeletingTaskId] = useState<number | null>(null);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);

  // 任务列表状态
  const [tasks, setTasks] = useState<TaskResponse[]>([]);

  // 加载任务列表
  const loadTasks = async () => {
    try {
      setLoading(true);

      // 退出选择模式
      setSelectMode(false);
      setSelectedTasks([]);

      console.log('开始获取任务列表, 状态过滤:', statusFilter);

      // 使用API函数获取任务列表
      const data = await getTasks(statusFilter);
      console.log('获取到的任务数据:', data);

      setTasks(data);
      toast.success(`成功获取${data.length}条任务记录`);
    } catch (error) {
      console.error('获取任务列表失败:', error);

      // 只在第一次加载失败时显示错误通知
      if (tasks.length === 0) {
        toast.error('获取任务列表失败');
      }
    } finally {
      setLoading(false);
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

  // 切换选择模式
  const toggleSelectMode = () => {
    setSelectMode(!selectMode);
    setSelectedTasks([]);
  };

  // 处理任务选择
  const handleTaskSelect = (taskId: number) => {
    setSelectedTasks(prev => {
      if (prev.includes(taskId)) {
        return prev.filter(id => id !== taskId);
      } else {
        return [...prev, taskId];
      }
    });
  };

  // 全选/取消全选
  const toggleSelectAll = () => {
    if (selectedTasks.length === filteredTasks.length) {
      setSelectedTasks([]);
    } else {
      setSelectedTasks(filteredTasks.map(task => task.id));
    }
  };

  // 删除单个任务
  const handleDeleteTask = async (taskId: number) => {
    try {
      setDeleteLoading(true);
      setDeletingTaskId(taskId);
      console.log(`开始删除任务: ID=${taskId}`);

      const result = await deleteTask(taskId);
      console.log(`删除任务API返回结果:`, result);

      toast.success('任务删除成功');
      await loadTasks();
    } catch (error: any) {
      console.error('删除任务失败:', error);

      // 显示详细错误信息
      const errorMessage = error.response?.data?.detail || error.message || '删除任务失败';
      toast.error(`删除任务失败: ${errorMessage}`);
    } finally {
      setDeleteLoading(false);
      setDeletingTaskId(null);
    }
  };

  // 批量删除任务
  const handleDeleteSelected = async () => {
    if (selectedTasks.length === 0) {
      toast.warning('请先选择要删除的任务');
      return;
    }

    try {
      setDeleteLoading(true);
      console.log(`开始批量删除任务: IDs=${selectedTasks.join(',')}`);

      const result = await deleteTasks(selectedTasks);
      console.log(`批量删除任务API返回结果:`, result);

      toast.success(`成功删除${selectedTasks.length}条任务记录`);
      setSelectedTasks([]);
      await loadTasks();
    } catch (error: any) {
      console.error('批量删除任务失败:', error);

      // 显示详细错误信息
      const errorMessage = error.response?.data?.detail || error.message || '批量删除任务失败';
      toast.error(`批量删除任务失败: ${errorMessage}`);
    } finally {
      setDeleteLoading(false);
    }
  };

  // 清空所有历史记录
  const handleClearAll = async () => {
    try {
      setDeleteLoading(true);
      console.log('开始清空所有历史记录');

      const result = await clearAllTasks();
      console.log('清空所有历史记录API返回结果:', result);

      toast.success('所有历史记录已清空');
      setClearDialogOpen(false);
      await loadTasks();
    } catch (error: any) {
      console.error('清空历史记录失败:', error);

      // 显示详细错误信息
      const errorMessage = error.response?.data?.detail || error.message || '清空历史记录失败';
      toast.error(`清空历史记录失败: ${errorMessage}`);
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">历史记录</h1>
        <div className="flex space-x-2">
          {selectMode ? (
            <>
              <Button
                onClick={handleDeleteSelected}
                variant="destructive"
                size="sm"
                disabled={selectedTasks.length === 0 || deleteLoading}
              >
                {deleteLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Trash2 className="h-4 w-4 mr-2" />
                )}
                删除选中 ({selectedTasks.length})
              </Button>
              <Button onClick={toggleSelectMode} variant="outline" size="sm">
                <X className="h-4 w-4 mr-2" />
                取消选择
              </Button>
            </>
          ) : (
            <>
              <Button onClick={toggleSelectMode} variant="outline" size="sm">
                <CheckSquare className="h-4 w-4 mr-2" />
                多选
              </Button>
              <Dialog open={clearDialogOpen} onOpenChange={setClearDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Trash2 className="h-4 w-4 mr-2" />
                    清空
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>确认清空所有历史记录</DialogTitle>
                    <DialogDescription>
                      此操作将删除所有历史记录，且无法恢复。确定要继续吗？
                    </DialogDescription>
                  </DialogHeader>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setClearDialogOpen(false)}>
                      取消
                    </Button>
                    <Button variant="destructive" onClick={handleClearAll} disabled={deleteLoading}>
                      {deleteLoading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                      确认清空
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
              <Button onClick={loadTasks} variant="outline" size="icon">
                <RefreshCw className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="搜索内容..."
            className="pl-8"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
          />
        </div>
        <Select
          value={statusFilter || 'all'}
          onValueChange={value => setStatusFilter(value === 'all' ? undefined : value)}
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
                {selectMode && (
                  <TableHead className="w-[50px]">
                    <Checkbox
                      checked={
                        selectedTasks.length === filteredTasks.length && filteredTasks.length > 0
                      }
                      onCheckedChange={toggleSelectAll}
                      aria-label="全选"
                    />
                  </TableHead>
                )}
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
                  <TableCell
                    colSpan={selectMode ? 7 : 6}
                    className="text-center py-8 text-muted-foreground"
                  >
                    没有找到任务记录
                  </TableCell>
                </TableRow>
              ) : (
                filteredTasks.map(task => (
                  <TableRow key={task.id}>
                    {selectMode && (
                      <TableCell>
                        <Checkbox
                          checked={selectedTasks.includes(task.id)}
                          onCheckedChange={() => handleTaskSelect(task.id)}
                          aria-label={`选择任务 ${task.id}`}
                        />
                      </TableCell>
                    )}
                    <TableCell>{task.id}</TableCell>
                    <TableCell className="max-w-[300px] truncate">{task.content}</TableCell>
                    <TableCell>{getModeName(task.processing_mode)}</TableCell>
                    <TableCell>
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${getStatusStyle(task.status)}`}
                      >
                        {getStatusName(task.status)}
                      </span>
                    </TableCell>
                    <TableCell>{formatDateTime(task.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex space-x-2">
                        <Link to={`/result/${task.id}`}>
                          <Button variant="outline" size="sm">
                            查看结果
                          </Button>
                        </Link>
                        {!selectMode && (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={e => {
                              e.preventDefault();
                              e.stopPropagation();
                              handleDeleteTask(task.id);
                            }}
                            disabled={
                              deleteLoading &&
                              (deletingTaskId === task.id || deletingTaskId === null)
                            }
                          >
                            {deleteLoading && deletingTaskId === task.id && (
                              <Loader2 className="h-4 w-4 animate-spin mr-1" />
                            )}
                            删除
                          </Button>
                        )}
                      </div>
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
