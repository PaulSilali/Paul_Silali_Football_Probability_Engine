import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { ModelHealth as ModelHealthType, ModelStatus } from '@/types';

// Mock data
const mockHealth: ModelHealthType = {
  status: 'stable',
  lastValidationDate: '2024-12-27T10:30:00Z',
  oddsDistribution: [
    { bucket: '-10 to -5', divergence: 12 },
    { bucket: '-5 to -2', divergence: 28 },
    { bucket: '-2 to 0', divergence: 35 },
    { bucket: '0 to 2', divergence: 38 },
    { bucket: '2 to 5', divergence: 25 },
    { bucket: '5 to 10', divergence: 15 },
  ],
  leagueDrift: [
    { league: 'Premier League', driftScore: 0.023, signal: 'normal' },
    { league: 'La Liga', driftScore: 0.018, signal: 'normal' },
    { league: 'Bundesliga', driftScore: 0.041, signal: 'elevated' },
    { league: 'Serie A', driftScore: 0.029, signal: 'normal' },
    { league: 'Ligue 1', driftScore: 0.034, signal: 'normal' },
  ],
};

function StatusBadge({ status }: { status: ModelStatus }) {
  const variants: Record<ModelStatus, { label: string; className: string }> = {
    stable: { label: 'Stable', className: 'status-stable' },
    watch: { label: 'Watch', className: 'status-watch' },
    degraded: { label: 'Degraded', className: 'status-degraded' },
  };
  
  const { label, className } = variants[status];
  
  return (
    <Badge variant="outline" className={`${className} font-medium`}>
      {label}
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
  const health = mockHealth;
  const lastValidation = new Date(health.lastValidationDate);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Model Health & Stability</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Monitor model performance and detect drift
        </p>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Overall Status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <StatusBadge status={health.status} />
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
              {lastValidation.toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric',
                year: 'numeric'
              })}
            </div>
            <div className="text-sm text-muted-foreground">
              {lastValidation.toLocaleTimeString('en-US', { 
                hour: '2-digit',
                minute: '2-digit'
              })}
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
            {health.leagueDrift.map((league) => (
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
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="bg-muted/30">
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            <strong>About Drift Signals:</strong> Drift detection monitors for systematic changes in model performance 
            over time. Elevated signals suggest the model may benefit from recalibration for that league. 
            This is a diagnostic tool, not an immediate action trigger.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
