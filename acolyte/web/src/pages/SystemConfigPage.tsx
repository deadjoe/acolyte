import React, { useState } from 'react';
import { toast } from 'sonner';
import { Loader2, Download, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { apiClient } from '@/api';
import { PageTitle } from '@/components/common';

export function SystemConfigPage() {
  const [exportLoading, setExportLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importDialogOpen, setImportDialogOpen] = useState(false);

  // 导出配置
  const handleExportConfig = async () => {
    try {
      setExportLoading(true);

      const response = await apiClient.get('/config/export', {
        responseType: 'blob',
      });

      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute(
        'download',
        `acolyte_config_${new Date().toISOString().split('T')[0]}.json`
      );
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      toast.success('配置导出成功');
    } catch (error) {
      console.error('导出配置失败:', error);
      toast.error('导出配置失败');
    } finally {
      setExportLoading(false);
    }
  };

  // 导入配置
  const handleImportConfig = async () => {
    if (!importFile) {
      toast.error('请选择配置文件');
      return;
    }

    try {
      setImportLoading(true);

      const formData = new FormData();
      formData.append('config_file', importFile);

      const response = await apiClient.post('/config/import', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.success) {
        toast.success('配置导入成功');
        setImportDialogOpen(false);
        setImportFile(null);
      } else {
        toast.error(`导入失败: ${response.data.message || '未知错误'}`);
      }
    } catch (error) {
      console.error('导入配置失败:', error);
      toast.error('导入配置失败');
    } finally {
      setImportLoading(false);
    }
  };

  // 处理文件选择
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setImportFile(e.target.files[0]);
    }
  };

  return (
    <div className="space-y-6">
      <PageTitle title="系统配置" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>导出配置</CardTitle>
            <CardDescription>导出系统配置，包括LLM配置和提示词模板</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              导出的配置文件包含所有LLM配置（包括API密钥）和提示词模板。请妥善保管导出的配置文件。
            </p>
          </CardContent>
          <CardFooter>
            <Button onClick={handleExportConfig} disabled={exportLoading}>
              {exportLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" />
              )}
              导出配置
            </Button>
          </CardFooter>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>导入配置</CardTitle>
            <CardDescription>从配置文件导入系统配置</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              导入配置将覆盖现有的LLM配置和提示词模板。请确保导入的配置文件格式正确。
            </p>
          </CardContent>
          <CardFooter>
            <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Upload className="mr-2 h-4 w-4" />
                  导入配置
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>导入配置</DialogTitle>
                  <DialogDescription>选择要导入的配置文件。导入将覆盖现有配置。</DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <Label htmlFor="config-file">配置文件</Label>
                    <Input
                      id="config-file"
                      type="file"
                      accept=".json"
                      onChange={handleFileChange}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button onClick={handleImportConfig} disabled={!importFile || importLoading}>
                    {importLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    导入
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </CardFooter>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>系统信息</CardTitle>
          <CardDescription>Acolyte内容分析评估系统</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-medium">API服务器</h3>
              <p className="text-sm text-muted-foreground">
                {import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium">Web版本</h3>
              <p className="text-sm text-muted-foreground">1.0.0</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
