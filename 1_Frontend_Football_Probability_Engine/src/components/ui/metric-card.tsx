/**
 * Modern Metric Card Component
 * Displays key metrics with animations and visual indicators
 */
import { ReactNode } from 'react';
import { TrendingUp, TrendingDown, Minus, ArrowUpRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ModernCard } from './modern-card';

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  variant?: 'default' | 'primary' | 'accent' | 'success' | 'warning' | 'danger';
  description?: string;
  className?: string;
}

export function MetricCard({
  title,
  value,
  change,
  changeLabel,
  icon,
  trend,
  variant = 'default',
  description,
  className,
}: MetricCardProps) {
  const variantStyles = {
    default: 'border-border',
    primary: 'border-primary/30 bg-primary/5',
    accent: 'border-accent/30 bg-accent/5',
    success: 'border-[hsl(var(--status-stable))]/30 bg-[hsl(var(--status-stable))]/5',
    warning: 'border-[hsl(var(--status-watch))]/30 bg-[hsl(var(--status-watch))]/5',
    danger: 'border-[hsl(var(--status-degraded))]/30 bg-[hsl(var(--status-degraded))]/5',
  };

  const getTrendIcon = () => {
    if (trend === 'up') return <TrendingUp className="h-4 w-4" />;
    if (trend === 'down') return <TrendingDown className="h-4 w-4" />;
    return <Minus className="h-4 w-4" />;
  };

  const getTrendColor = () => {
    if (trend === 'up') return 'text-[hsl(var(--status-stable))]';
    if (trend === 'down') return 'text-[hsl(var(--status-degraded))]';
    return 'text-muted-foreground';
  };

  return (
    <ModernCard
      variant="elevated"
      className={cn(variantStyles[variant], className)}
      icon={icon}
    >
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
            {title}
          </p>
          {change !== undefined && (
            <div className={cn('flex items-center gap-1 text-xs font-medium', getTrendColor())}>
              {getTrendIcon()}
              <span>{change > 0 ? '+' : ''}{change}%</span>
            </div>
          )}
        </div>
        
        <div className="flex items-baseline gap-2">
          <h3 className="text-3xl font-bold tabular-nums text-glow">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </h3>
          {changeLabel && (
            <span className="text-xs text-muted-foreground">{changeLabel}</span>
          )}
        </div>
        
        {description && (
          <p className="text-xs text-muted-foreground mt-2">{description}</p>
        )}
      </div>
      
      {/* Animated progress bar */}
      {change !== undefined && (
        <div className="mt-4 h-1 bg-muted/20 rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full transition-all duration-1000',
              trend === 'up' ? 'bg-[hsl(var(--status-stable))]' : 
              trend === 'down' ? 'bg-[hsl(var(--status-degraded))]' : 
              'bg-muted-foreground'
            )}
            style={{ width: `${Math.min(Math.abs(change), 100)}%` }}
          />
        </div>
      )}
    </ModernCard>
  );
}

