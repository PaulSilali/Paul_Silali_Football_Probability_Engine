/**
 * Modern Page Layout Component
 * Provides consistent layout structure for all pages
 */
import { ReactNode } from 'react';
import { SectionHeader } from '@/components/ui/section-header';
import { cn } from '@/lib/utils';

interface PageLayoutProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  badge?: ReactNode;
}

export function PageLayout({
  title,
  description,
  icon,
  action,
  children,
  className,
  badge,
}: PageLayoutProps) {
  return (
    <div className={cn('p-6 space-y-8 min-h-screen bg-gradient-to-br from-background via-background to-background/95', className)}>
      <SectionHeader
        title={title}
        description={description}
        icon={icon}
        action={action}
        badge={badge}
      />
      {children}
    </div>
  );
}

