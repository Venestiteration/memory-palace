import type { ReactNode } from 'react';

interface PageContainerProps {
  children: ReactNode;
  className?: string;
}

export default function PageContainer({ children, className = '' }: PageContainerProps) {
  return (
    <main className={`flex-1 overflow-auto px-4 py-4 pb-20 ${className}`}>
      {children}
    </main>
  );
}