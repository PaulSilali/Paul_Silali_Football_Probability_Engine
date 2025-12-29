import { 
  Activity, 
  Database, 
  Clock, 
  TrendingUp, 
  CheckCircle, 
  AlertTriangle,
  BarChart3,
  Target,
  Percent,
  Zap,
  ArrowUpRight
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

// Mock system health data
const systemHealth = {
  modelVersion: 'v2.4.1',
  modelStatus: 'stable' as const,
  lastRetrain: '2024-12-27T10:00:00Z',
  calibrationScore: 0.142,
  logLoss: 0.891,
  totalMatches: 45672,
  avgWeeklyAccuracy: 67.3,
  drawAccuracy: 58.2,
};

const dataFreshness = [
  { source: 'Match Results', lastUpdated: '2024-12-27T10:05:32Z', status: 'fresh', recordCount: 45672 },
  { source: 'Team Ratings', lastUpdated: '2024-12-27T08:12:45Z', status: 'fresh', recordCount: 2340 },
  { source: 'Market Odds', lastUpdated: '2024-12-26T22:00:00Z', status: 'stale', recordCount: 128945 },
  { source: 'League Metadata', lastUpdated: '2024-12-20T14:30:00Z', status: 'warning', recordCount: 156 },
];

const calibrationTrend = [
  { week: 'W48', brier: 0.168 },
  { week: 'W49', brier: 0.155 },
  { week: 'W50', brier: 0.149 },
  { week: 'W51', brier: 0.144 },
  { week: 'W52', brier: 0.142 },
];

const outcomeDistribution = [
  { name: 'Home', predicted: 42.3, actual: 41.8, color: 'hsl(var(--chart-1))' },
  { name: 'Draw', predicted: 27.5, actual: 28.1, color: 'hsl(var(--chart-2))' },
  { name: 'Away', predicted: 30.2, actual: 30.1, color: 'hsl(var(--chart-3))' },
];

const leaguePerformance = [
  { league: 'Premier League', accuracy: 71.2, matches: 380, status: 'excellent' },
  { league: 'La Liga', accuracy: 68.5, matches: 380, status: 'good' },
  { league: 'Bundesliga', accuracy: 65.8, matches: 306, status: 'good' },
  { league: 'Serie A', accuracy: 64.2, matches: 380, status: 'fair' },
  { league: 'Ligue 1', accuracy: 62.1, matches: 380, status: 'fair' },
];

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'stable':
    case 'fresh':
    case 'excellent':
      return <Badge variant="secondary" className="bg-status-stable/10 text-status-stable border-status-stable/20">
        <CheckCircle className="h-3 w-3 mr-1" />
        {status}
      </Badge>;
    case 'good':
      return <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
        {status}
      </Badge>;
    case 'warning':
    case 'fair':
      return <Badge variant="secondary" className="bg-status-watch/10 text-status-watch border-status-watch/20">
        <AlertTriangle className="h-3 w-3 mr-1" />
        {status}
      </Badge>;
    case 'stale':
      return <Badge variant="secondary" className="bg-status-degraded/10 text-status-degraded border-status-degraded/20">
        <Clock className="h-3 w-3 mr-1" />
        {status}
      </Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

export default function Dashboard() {
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between animate-fade-in">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 glow-primary">
            <Zap className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold gradient-text">Dashboard</h1>
            <p className="text-sm text-muted-foreground">
              System health overview and model performance metrics
            </p>
          </div>
        </div>
      </div>

      {/* Key Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            icon: Database,
            label: 'Model Version',
            value: systemHealth.modelVersion,
            badge: getStatusBadge(systemHealth.modelStatus),
            sub: `Last retrain: ${formatDate(systemHealth.lastRetrain)}`,
            delay: '0s'
          },
          {
            icon: Target,
            label: 'Brier Score',
            value: systemHealth.calibrationScore.toFixed(3),
            badge: <Badge className="bg-status-stable/10 text-status-stable border-status-stable/20">
              <TrendingUp className="h-3 w-3 mr-1" />-2.1%
            </Badge>,
            sub: 'Lower is better (perfect = 0)',
            delay: '0.1s'
          },
          {
            icon: Percent,
            label: 'Weekly Accuracy',
            value: `${systemHealth.avgWeeklyAccuracy}%`,
            badge: <Badge variant="outline">Rolling 8w</Badge>,
            sub: `Draw accuracy: ${systemHealth.drawAccuracy}%`,
            delay: '0.2s'
          },
          {
            icon: BarChart3,
            label: 'Training Data',
            value: systemHealth.totalMatches.toLocaleString(),
            badge: <Badge variant="outline">matches</Badge>,
            sub: 'Across 12 leagues, 8 seasons',
            delay: '0.3s'
          },
        ].map((metric) => (
          <Card 
            key={metric.label} 
            className="glass-card group hover:border-primary/30 transition-all duration-300 animate-fade-in-up"
            style={{ animationDelay: metric.delay }}
          >
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-2">
                <metric.icon className="h-4 w-4 text-primary" />
                {metric.label}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <span className="text-2xl font-bold tabular-nums group-hover:text-primary transition-colors">{metric.value}</span>
                {metric.badge}
              </div>
              <p className="text-xs text-muted-foreground mt-1">{metric.sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Calibration Trend */}
        <Card className="glass-card animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              Calibration Trend
            </CardTitle>
            <CardDescription>Brier score over last 5 weeks (lower is better)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={calibrationTrend}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
                  <XAxis dataKey="week" className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                  <YAxis domain={[0.1, 0.2]} className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'hsl(var(--card))', 
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '12px',
                      boxShadow: '0 4px 30px hsl(var(--primary) / 0.1)'
                    }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="brier" 
                    stroke="hsl(var(--primary))" 
                    strokeWidth={3}
                    dot={{ fill: 'hsl(var(--primary))', strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6, className: 'glow-primary' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Outcome Distribution */}
        <Card className="glass-card animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-accent" />
              Outcome Distribution
            </CardTitle>
            <CardDescription>Predicted vs Actual (Market vs Model)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {outcomeDistribution.map((item, index) => (
                <div key={item.name} className="space-y-2 animate-fade-in" style={{ animationDelay: `${0.1 * index}s` }}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{item.name}</span>
                    <div className="flex items-center gap-4 text-xs">
                      <span className="text-muted-foreground">
                        Predicted: <span className="font-medium text-foreground">{item.predicted}%</span>
                      </span>
                      <span className="text-muted-foreground">
                        Actual: <span className="font-medium text-primary">{item.actual}%</span>
                      </span>
                    </div>
                  </div>
                  <div className="relative h-3 bg-muted/30 rounded-full overflow-hidden">
                    <div 
                      className="absolute h-full bg-primary/30 rounded-full transition-all duration-500"
                      style={{ width: `${item.predicted}%` }}
                    />
                    <div 
                      className="absolute h-full bg-primary rounded-full transition-all duration-500 glow-primary"
                      style={{ width: `${item.actual}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Data Freshness */}
        <Card className="glass-card animate-fade-in-up" style={{ animationDelay: '0.4s' }}>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Clock className="h-5 w-5 text-chart-4" />
              Data Freshness
            </CardTitle>
            <CardDescription>Status of ingested data sources</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {dataFreshness.map((source, index) => (
                <div 
                  key={source.source} 
                  className="flex items-center justify-between py-3 border-b border-border/50 last:border-0 animate-fade-in"
                  style={{ animationDelay: `${0.1 * index}s` }}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-muted/30">
                      <Database className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div>
                      <div className="font-medium text-sm">{source.source}</div>
                      <div className="text-xs text-muted-foreground">
                        {source.recordCount.toLocaleString()} records
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground tabular-nums">
                      {formatDate(source.lastUpdated)}
                    </span>
                    {getStatusBadge(source.status)}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* League Performance */}
        <Card className="glass-card animate-fade-in-up" style={{ animationDelay: '0.5s' }}>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Activity className="h-5 w-5 text-chart-5" />
              League Performance
            </CardTitle>
            <CardDescription>Model accuracy by competition</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {leaguePerformance.map((league, index) => (
                <div key={league.league} className="space-y-2 animate-fade-in" style={{ animationDelay: `${0.1 * index}s` }}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{league.league}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">{league.matches} matches</span>
                      {getStatusBadge(league.status)}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Progress value={league.accuracy} className="h-2 flex-1" />
                    <span className="text-xs font-medium tabular-nums w-12 text-right text-primary">
                      {league.accuracy}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="glass-card-elevated border-primary/10 animate-fade-in-up" style={{ animationDelay: '0.6s' }}>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2 px-3 py-2 glass-card rounded-lg">
              <CheckCircle className="h-4 w-4 text-status-stable" />
              <span>All models healthy</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 glass-card rounded-lg">
              <CheckCircle className="h-4 w-4 text-status-stable" />
              <span>Calibration within tolerance</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 glass-card rounded-lg border-status-watch/30">
              <AlertTriangle className="h-4 w-4 text-status-watch" />
              <span>1 data source needs refresh</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
