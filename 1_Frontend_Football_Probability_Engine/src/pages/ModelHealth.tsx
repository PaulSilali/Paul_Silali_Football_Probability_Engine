import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageLayout } from '@/components/layouts/PageLayout';
import { ModernCard } from '@/components/ui/modern-card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, AlertTriangle, Activity } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import apiClient from '@/services/api';
import { useToast } from '@/hooks/use-toast';

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, { label: string; className: string }> = {
    stable: { label: 'Stable', className: 'status-stable' },
    watch: { label: 'Watch', className: 'status-watch' },
    degraded: { label: 'Degraded', className: 'status-degraded' },
    no_model: { label: 'No Model', className: 'status-degraded' },
  };
  
  const variant = variants[status] || { label: status, className: 'bg-muted' };
  
  return (
    <Badge variant="outline" className={`${variant.className} font-medium`}>
      {variant.label}
    </Badge>
  );
}

function DriftSignalBadge({ signal }: { signal: 'normal' | 'elevated' | 'high' }) {
  const variants: Record<typeof signal, { label: string; className: string }> = {
    normal: { label: 'Normal', className: 'bg-muted text-muted-foreground' },
    elevated: { label: 'Elevated', className: 'status-watch' },
    high: { label: 'High', className: 'status-degraded' },
  };
  
  const { label, className } = variants[signal];
  
  return (
    <Badge variant="outline" className={`${className} text-xs`}>
      {label}
    </Badge>
  );
}

export default function ModelHealth() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<{
    status: string;
    lastChecked: string;
    lastValidationDate: string | null;
    metrics: {
      brierScore: number | null;
      logLoss: number | null;
      accuracy: number | null;
    };
    alerts: string[];
    driftIndicators: Array<{
      league: string;
      driftScore: number;
      signal: 'normal' | 'elevated' | 'high';
      accuracy: number;
      matches: number;
    }>;
    oddsDistribution: Array<{
      bucket: string;
      divergence: number;
    }>;
    leagueDrift: Array<{
      league: string;
      driftScore: number;
      signal: 'normal' | 'elevated' | 'high';
      accuracy: number;
      matches: number;
    }>;
  } | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.getModelHealth();
        
        if (response.success && response.data) {
          setHealth(response.data);
        } else {
          throw new Error('Failed to load model health data');
        }
      } catch (err: any) {
        console.error('Error fetching model health:', err);
        setError(err.message || 'Failed to load model health data');
        toast({
          title: 'Error',
          description: 'Failed to load model health data.',
          variant: 'destructive',
        });
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
  }, [toast]);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Loading model health data...</p>
        </div>
      </div>
    );
  }

  if (error || !health) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {error || 'Failed to load model health data'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const lastValidation = health.lastValidationDate 
    ? new Date(health.lastValidationDate)
    : null;

  return (
    <PageLayout
      title="Model Health & Stability"
      description="Monitor model performance and detect drift across leagues"
      icon={<Activity className="h-6 w-6" />}
    >

      {/* Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Overall Status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <StatusBadge status={health.status as string} />
              <span className="text-sm text-muted-foreground">
                All systems operating normally
              </span>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Last Validation</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-medium tabular-nums">
              {lastValidation 
                ? lastValidation.toLocaleDateString('en-US', { 
                    month: 'short', 
                    day: 'numeric',
                    year: 'numeric'
                  })
                : 'Never'}
            </div>
            <div className="text-sm text-muted-foreground">
              {lastValidation 
                ? lastValidation.toLocaleTimeString('en-US', { 
                    hour: '2-digit',
                    minute: '2-digit'
                  })
                : 'No validation data available'}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Leagues Monitored</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-medium tabular-nums">
              {health.leagueDrift.length}
            </div>
            <div className="text-sm text-muted-foreground">
              {health.leagueDrift.filter(l => l.signal === 'elevated' || l.signal === 'high').length} with elevated signals
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Odds Divergence Distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Odds Divergence Distribution</CardTitle>
          <CardDescription>
            Distribution of differences between model probabilities and market-implied probabilities
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[250px]">
            {health.oddsDistribution.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={health.oddsDistribution} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="bucket" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip 
                    formatter={(value: number) => [value, 'Fixtures']}
                    labelFormatter={(label) => `Divergence: ${label}%`}
                  />
                  <Bar 
                    dataKey="divergence" 
                    fill="hsl(var(--chart-1))" 
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <p>No odds divergence data available</p>
              </div>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-4 text-center">
            A symmetric distribution centered near zero indicates good alignment with market consensus
          </p>
        </CardContent>
      </Card>

      {/* League Drift Signals */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">League-Level Drift Signals</CardTitle>
          <CardDescription>
            Monitoring for systematic changes in prediction accuracy by league
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {health.leagueDrift.length > 0 ? health.leagueDrift.map((league) => (
              <div key={league.league} className="flex items-center justify-between py-2 border-b last:border-0">
                <div className="flex items-center gap-4">
                  <span className="font-medium text-sm w-36">{league.league}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all ${
                          league.signal === 'normal' ? 'bg-chart-1' :
                          league.signal === 'elevated' ? 'bg-status-watch' :
                          'bg-status-degraded'
                        }`}
                        style={{ width: `${Math.min(league.driftScore * 1000, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground tabular-nums w-12">
                      {(league.driftScore * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <DriftSignalBadge signal={league.signal} />
              </div>
            )) : (
              <div className="text-center py-8 text-muted-foreground">
                <p>No league drift data available</p>
                <p className="text-xs mt-2">Run validation on completed jackpots to see drift signals</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Alerts */}
      {health.alerts.length > 0 && (
        <Alert variant={health.status === 'degraded' ? 'destructive' : 'default'}>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-1">
              {health.alerts.map((alert, idx) => (
                <p key={idx}>{alert}</p>
              ))}
            </div>
          </AlertDescription>
        </Alert>
      )}

      <Card className="bg-muted/30">
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            <strong>About Drift Signals:</strong> Drift detection monitors for systematic changes in model performance 
            over time. Elevated signals suggest the model may benefit from recalibration for that league. 
            This is a diagnostic tool, not an immediate action trigger.
          </p>
        </CardContent>
      </Card>
    </PageLayout>
  );
}
