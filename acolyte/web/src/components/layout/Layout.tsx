import { ReactNode } from 'react';
import { Header } from './Header';
import { Footer } from './Footer';
import { Toaster } from '@/components/ui/sonner';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="relative min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 container py-6">{children}</main>
      <Footer />
      <Toaster />
    </div>
  );
}
