import { Link } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { TaskResponse } from '@/api';
import {
  formatDate,
  truncateText,
  getProcessingModeName,
  getTaskStatusName,
  getTaskStatusStyle,
} from '@/lib/utils';

interface TaskCardProps {
  task: TaskResponse;
}

export function TaskCard({ task }: TaskCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">任务 #{task.id}</CardTitle>
          <span className={`px-2 py-1 rounded-full text-xs ${getTaskStatusStyle(task.status)}`}>
            {getTaskStatusName(task.status)}
          </span>
        </div>
        <CardDescription>
          {getProcessingModeName(task.processing_mode)} · {formatDate(task.created_at)}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground line-clamp-3">
          {truncateText(task.content, 150)}
        </p>
      </CardContent>
      <CardFooter>
        <Link to={`/result/${task.id}`} className="w-full">
          <Button variant="outline" size="sm" className="w-full">
            <ExternalLink className="mr-2 h-4 w-4" />
            查看结果
          </Button>
        </Link>
      </CardFooter>
    </Card>
  );
}
