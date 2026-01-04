/**
 * Modern Futuristic Card Component
 * Enhanced glassmorphism with animations and glow effects
 */
import { ReactNode } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface ModernCardProps {
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
  variant?: 'default' | 'elevated' | 'glow' | 'gradient';
  icon?: ReactNode;
  footer?: ReactNode;
  hover?: boolean;
}

export function ModernCard({
  title,
  description,
  children,
  className,
  variant = 'default',
  icon,
  footer,
  hover = true,
}: ModernCardProps) {
  const variantClasses = {
    default: 'glass-card',
    elevated: 'glass-card-elevated',
    glow: 'glass-card border-primary/20 glow-primary',
    gradient: 'glass-card border-gradient-to-r from-primary/20 to-accent/20',
  };

  return (
    <Card
      className={cn(
        variantClasses[variant],
        hover && 'transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl hover:shadow-primary/10',
        'group relative overflow-hidden',
        className
      )}
    >
      {/* Animated gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      
      {/* Scan line effect */}
      <div className="absolute inset-0 scan-lines pointer-events-none" />
      
      {(title || description || icon) && (
        <CardHeader className="relative">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              {icon && (
                <div className="p-2 rounded-lg bg-primary/10 text-primary border border-primary/20">
                  {icon}
                </div>
              )}
              <div>
                {title && (
                  <CardTitle className="text-xl font-semibold gradient-text">
                    {title}
                  </CardTitle>
                )}
                {description && (
                  <CardDescription className="mt-1 text-sm text-muted-foreground">
                    {description}
                  </CardDescription>
                )}
              </div>
            </div>
          </div>
        </CardHeader>
      )}
      
      <CardContent className="relative">
        {children}
      </CardContent>
      
      {footer && (
        <div className="relative px-6 pb-6 pt-0 border-t border-border/50">
          {footer}
        </div>
      )}
    </Card>
  );
}

