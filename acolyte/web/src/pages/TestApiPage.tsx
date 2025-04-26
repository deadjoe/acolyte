import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';

export function TestApiPage() {
  const [apiUrl, setApiUrl] = useState(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/tasks`);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState('');
  
  const testApi = async () => {
    try {
      setLoading(true);
      setResponse('');
      
      console.log('测试API URL:', apiUrl);
      
      // 使用fetch API
      const fetchResponse = await fetch(apiUrl);
      const responseText = await fetchResponse.text();
      
      console.log('响应状态:', fetchResponse.status);
      console.log('响应文本:', responseText);
      
      setResponse(`状态码: ${fetchResponse.status}\n\n${responseText}`);
      
      if (fetchResponse.ok) {
        toast.success('API请求成功');
      } else {
        toast.error(`API请求失败: ${fetchResponse.status}`);
      }
      
    } catch (error) {
      console.error('API请求失败:', error);
      setResponse(`错误: ${error instanceof Error ? error.message : String(error)}`);
      toast.error('API请求失败');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">API测试</h1>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>测试API调用</CardTitle>
          <CardDescription>
            输入API URL并测试连接
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">API URL</label>
            <Input
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="输入API URL"
            />
          </div>
          
          <Button onClick={testApi} disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                测试中...
              </>
            ) : (
              '测试API'
            )}
          </Button>
        </CardContent>
        <CardFooter className="flex flex-col items-start">
          <h3 className="text-sm font-medium mb-2">响应结果</h3>
          <Textarea
            value={response}
            readOnly
            className="min-h-[200px] font-mono text-sm"
          />
        </CardFooter>
      </Card>
    </div>
  );
}
