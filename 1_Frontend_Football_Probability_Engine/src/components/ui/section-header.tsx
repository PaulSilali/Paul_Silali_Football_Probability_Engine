/**
 * Modern Section Header Component
 * Professional page headers with gradient text and icons
 */
import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface SectionHeaderProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
  badge?: ReactNode;
}

export function SectionHeader({
  title,
  description,
  icon,
  action,
  className,
  badge,
}: SectionHeaderProps) {
  return (
    <div className={cn('flex items-start justify-between gap-4 mb-8', className)}>
      <div className="flex items-start gap-4 flex-1">
        {icon && (
          <div className="p-3 rounded-xl bg-primary/10 text-primary border border-primary/20 glow-primary">
            {icon}
          </div>
        )}
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-4xl font-bold gradient-text">
              {title}
            </h1>
            {badge && badge}
          </div>
          {description && (
            <p className="text-muted-foreground text-lg leading-relaxed max-w-2xl">
              {description}
            </p>
          )}
        </div>
      </div>
      {action && (
        <div className="flex-shrink-0">
          {action}
        </div>
      )}
    </div>
  );
}

