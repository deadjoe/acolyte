import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Loader2, RefreshCw, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { getPrompts, syncPrompts, getPrompt } from '@/api';
import { usePrompt } from '@/context/PromptContext';

export function PromptConfigPage() {
  const { state, dispatch } = usePrompt();
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [viewPrompt, setViewPrompt] = useState<{ id: number; content: string } | null>(null);

  // 加载提示词列表
  const loadPrompts = async () => {
    try {
      setLoading(true);
      dispatch({ type: 'SET_LOADING', payload: true });

      const prompts = await getPrompts();
      dispatch({ type: 'SET_PROMPTS', payload: prompts });

    } catch (error) {
      console.error('获取提示词列表失败:', error);
      dispatch({ type: 'SET_ERROR', payload: '获取提示词列表失败' });
      toast.error('获取提示词列表失败');
    } finally {
      setLoading(false);
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  // 同步提示词
  const handleSyncPrompts = async () => {
    try {
      setSyncing(true);

      const result = await syncPrompts();

      if (result.success) {
        toast.success(`同步成功: ${result.message || '提示词已同步'}`);
        // 重新加载提示词列表
        await loadPrompts();
      } else {
        toast.error(`同步失败: ${result.message || '未知错误'}`);
      }

    } catch (error) {
      console.error('同步提示词失败:', error);
      toast.error('同步提示词失败');
    } finally {
      setSyncing(false);
    }
  };

  // 查看提示词内容
  const handleViewPrompt = async (id: number) => {
    try {
      // 显示加载状态
      setViewPrompt({ id, content: '加载中...' });

      // 获取完整的提示词内容
      const promptDetail = await getPrompt(id);

      // 更新提示词内容
      setViewPrompt({
        id,
        content: promptDetail.content || '此提示词没有内容'
      });
    } catch (error) {
      console.error('获取提示词内容失败:', error);
      setViewPrompt({
        id,
        content: '获取提示词内容失败，请重试'
      });
      toast.error('获取提示词内容失败');
    }
  };

  // 初始加载
  useEffect(() => {
    loadPrompts();
  }, []);

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">提示词管理</h1>
        <div className="flex space-x-2">
          <Button onClick={loadPrompts} variant="outline" size="icon">
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button onClick={handleSyncPrompts} disabled={syncing}>
            {syncing ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              '同步提示词'
            )}
          </Button>
        </div>
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
                <TableHead>版本</TableHead>
                <TableHead>模型目标</TableHead>
                <TableHead>描述</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {state.prompts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    没有找到提示词
                  </TableCell>
                </TableRow>
              ) : (
                state.prompts.map((prompt) => (
                  <TableRow key={prompt.id}>
                    <TableCell>{prompt.id}</TableCell>
                    <TableCell>{prompt.version}</TableCell>
                    <TableCell>{prompt.model_target || '-'}</TableCell>
                    <TableCell className="max-w-[300px] truncate">
                      {prompt.description || '-'}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${
                          prompt.is_active
                            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
                            : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                        }`}
                      >
                        {prompt.is_active ? '激活' : '未激活'}
                      </span>
                    </TableCell>
                    <TableCell>{formatDate(prompt.created_at)}</TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleViewPrompt(prompt.id)}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        查看内容
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {/* 查看提示词内容对话框 */}
      <Dialog open={!!viewPrompt} onOpenChange={(open) => !open && setViewPrompt(null)}>
        <DialogContent className="sm:max-w-[700px] max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>提示词内容</DialogTitle>
            <DialogDescription>
              ID: {viewPrompt?.id}
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 flex-1 overflow-hidden flex flex-col">
            <div className="border rounded-md overflow-auto h-[400px] p-4 font-mono text-sm whitespace-pre-wrap">
              {viewPrompt?.content || ''}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
