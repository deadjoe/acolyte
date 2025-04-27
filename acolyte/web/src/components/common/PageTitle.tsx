import React, { ReactNode } from 'react';

interface PageTitleProps {
  title: string;
  actions?: ReactNode;
}

export function PageTitle({ title, actions }: PageTitleProps) {
  return (
    <div className="flex items-center justify-between px-1 py-2">
      <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
      {actions && <div className="flex space-x-2">{actions}</div>}
    </div>
  );
}
