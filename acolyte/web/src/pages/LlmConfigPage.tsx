import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Loader2, Plus, RefreshCw, Check, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { getLlms, createLlm, updateLlm, deleteLlm, testLlmConnection, setDefaultLlm, LlmConfigCreateRequest, LlmConfigUpdateRequest } from '@/api';
import { useLlm } from '@/context/LlmContext';

export function LlmConfigPage() {
  const { state, dispatch } = useLlm();
  const [loading, setLoading] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [formData, setFormData] = useState<LlmConfigCreateRequest>({
    name: '',
    api_key: '',
    base_url: '',
    model_name: '',
    description: '',
    role: 'normal',
    is_default: false,
  });

  // 加载LLM列表
  const loadLlms = async () => {
    try {
      setLoading(true);
      dispatch({ type: 'SET_LOADING', payload: true });

      const llms = await getLlms();
      dispatch({ type: 'SET_LLMS', payload: llms });

      // 设置默认LLM
      const defaultLlm = llms.find(llm => llm.is_default);
      if (defaultLlm) {
        dispatch({ type: 'SET_DEFAULT_LLM', payload: defaultLlm });
      }

    } catch (error) {
      console.error('获取LLM列表失败:', error);
      dispatch({ type: 'SET_ERROR', payload: '获取LLM列表失败' });
      toast.error('获取LLM列表失败');
    } finally {
      setLoading(false);
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  // 初始加载
  useEffect(() => {
    loadLlms();
  }, []);

  // 处理表单输入变化
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  // 处理选择框变化
  const handleSelectChange = (name: string, value: string) => {
    setFormData({ ...formData, [name]: value });
  };

  // 处理复选框变化
  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    setFormData({ ...formData, [name]: checked });
  };

  // 提交表单
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setLoading(true);

      const result = await createLlm(formData);
      dispatch({ type: 'ADD_LLM', payload: result });

      toast.success('LLM配置创建成功');
      setOpenDialog(false);
      setFormData({
        name: '',
        api_key: '',
        base_url: '',
        model_name: '',
        description: '',
        role: 'normal',
        is_default: false,
      });

    } catch (error) {
      console.error('创建LLM配置失败:', error);
      toast.error('创建LLM配置失败');
    } finally {
      setLoading(false);
    }
  };

  // 设置默认LLM
  const handleSetDefault = async (llmId: number) => {
    try {
      setLoading(true);

      // 使用专门的setDefaultLlm函数
      const result = await setDefaultLlm(llmId);

      // 获取LLM名称
      const llm = state.llms.find(l => l.id === llmId);
      const llmName = llm ? llm.name : `ID为${llmId}的LLM`;

      // 立即更新状态
      const updatedLlms = await getLlms();
      dispatch({ type: 'SET_LLMS', payload: updatedLlms });

      // 设置新的默认LLM
      const newDefaultLlm = updatedLlms.find(l => l.is_default);
      if (newDefaultLlm) {
        dispatch({ type: 'SET_DEFAULT_LLM', payload: newDefaultLlm });
      }

      toast.success(`已将 ${llmName} 设为默认LLM`);

    } catch (error) {
      console.error('设置默认LLM失败:', error);
      toast.error('设置默认LLM失败');
    } finally {
      setLoading(false);
    }
  };

  // 测试LLM连接
  const handleTestConnection = async (llmId: number) => {
    try {
      setTestingId(llmId);

      // 获取LLM信息，用于显示正确的API URL
      const llm = state.llms.find(l => l.id === llmId);
      const llmName = llm ? llm.name : `ID为${llmId}的LLM`;

      // 显示正确的API URL
      console.log(`测试LLM连接: ${llmName}, API端点: ${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/llms/${llmId}/test`);

      // 先获取最新的LLM列表，确保数据是最新的
      try {
        await loadLlms();
      } catch (refreshError) {
        console.warn('刷新LLM列表失败，继续使用当前数据:', refreshError);
      }

      // 使用专用的测试连接API
      const result = await testLlmConnection(llmId);

      if (result.success) {
        toast.success(`连接测试成功: ${result.message || '连接正常'}`);
      } else {
        toast.error(`连接测试失败: ${result.message || '未知错误'}`);
      }

    } catch (error) {
      console.error('测试LLM连接失败:', error);
      toast.error('测试LLM连接失败');
    } finally {
      setTestingId(null);
    }
  };

  // 删除LLM配置
  const handleDelete = async (llmId: number) => {
    if (!confirm('确定要删除此LLM配置吗？')) {
      return;
    }

    try {
      setLoading(true);

      await deleteLlm(llmId);
      dispatch({ type: 'REMOVE_LLM', payload: llmId });

      toast.success('LLM配置已删除');

    } catch (error) {
      console.error('删除LLM配置失败:', error);
      toast.error('删除LLM配置失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">LLM配置管理</h1>
        <div className="flex space-x-2">
          <Button onClick={loadLlms} variant="outline" size="icon">
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Dialog open={openDialog} onOpenChange={setOpenDialog}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                添加LLM
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>添加LLM配置</DialogTitle>
                <DialogDescription>
                  添加新的LLM配置，包括API密钥、模型名称等信息。
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSubmit}>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-4 items-center gap-4">
                    <label htmlFor="name" className="text-right text-sm font-medium">
                      名称
                    </label>
                    <Input
                      id="name"
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      className="col-span-3"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <label htmlFor="api_key" className="text-right text-sm font-medium">
                      API密钥
                    </label>
                    <Input
                      id="api_key"
                      name="api_key"
                      value={formData.api_key}
                      onChange={handleInputChange}
                      className="col-span-3"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <label htmlFor="base_url" className="text-right text-sm font-medium">
                      基础URL
                    </label>
                    <Input
                      id="base_url"
                      name="base_url"
                      value={formData.base_url}
                      onChange={handleInputChange}
                      className="col-span-3"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <label htmlFor="model_name" className="text-right text-sm font-medium">
                      模型名称
                    </label>
                    <Input
                      id="model_name"
                      name="model_name"
                      value={formData.model_name}
                      onChange={handleInputChange}
                      className="col-span-3"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <label htmlFor="description" className="text-right text-sm font-medium">
                      描述
                    </label>
                    <Input
                      id="description"
                      name="description"
                      value={formData.description || ''}
                      onChange={handleInputChange}
                      className="col-span-3"
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <label htmlFor="role" className="text-right text-sm font-medium">
                      角色
                    </label>
                    <Select
                      value={formData.role}
                      onValueChange={(value) => handleSelectChange('role', value)}
                    >
                      <SelectTrigger className="col-span-3">
                        <SelectValue placeholder="选择角色" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="normal">普通评估者</SelectItem>
                        <SelectItem value="reviewer">评议者</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <label htmlFor="is_default" className="text-right text-sm font-medium">
                      默认LLM
                    </label>
                    <div className="col-span-3 flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="is_default"
                        name="is_default"
                        checked={formData.is_default}
                        onChange={handleCheckboxChange}
                        className="h-4 w-4 rounded border-gray-300"
                      />
                      <label htmlFor="is_default" className="text-sm">
                        设为默认LLM
                      </label>
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button type="submit" disabled={loading}>
                    {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    保存
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {loading && !testingId ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>名称</TableHead>
                <TableHead>模型</TableHead>
                <TableHead>角色</TableHead>
                <TableHead>默认</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {state.llms.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    没有找到LLM配置
                  </TableCell>
                </TableRow>
              ) : (
                state.llms.map((llm) => (
                  <TableRow key={llm.id}>
                    <TableCell>{llm.id}</TableCell>
                    <TableCell>{llm.name}</TableCell>
                    <TableCell>{llm.model_name}</TableCell>
                    <TableCell>
                      {llm.role === 'normal' ? '普通评估者' : '评议者'}
                    </TableCell>
                    <TableCell>
                      {llm.is_default ? (
                        <Check className="h-4 w-4 text-green-500" />
                      ) : (
                        <X className="h-4 w-4 text-muted-foreground" />
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleTestConnection(llm.id)}
                          disabled={testingId === llm.id}
                        >
                          {testingId === llm.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            '测试'
                          )}
                        </Button>
                        {!llm.is_default && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleSetDefault(llm.id)}
                          >
                            设为默认
                          </Button>
                        )}
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDelete(llm.id)}
                        >
                          删除
                        </Button>
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
