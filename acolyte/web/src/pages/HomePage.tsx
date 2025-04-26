import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';

export function HomePage() {
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
    </div>
  );
}
