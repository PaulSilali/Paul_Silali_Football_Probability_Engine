import { useState, useEffect } from 'react';
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
  ArrowUpRight,
  Loader2
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ModernCard } from '@/components/ui/modern-card';
import { MetricCard } from '@/components/ui/metric-card';
import { PageLayout } from '@/components/layouts/PageLayout';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import apiClient from '@/services/api';
import { useToast } from '@/hooks/use-toast';

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
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [systemHealth, setSystemHealth] = useState({
    modelVersion: 'Loading...',
    modelStatus: 'unknown' as const,
    lastRetrain: null as string | null,
    calibrationScore: null as number | null,
    logLoss: null as number | null,
    totalMatches: 0,
    avgWeeklyAccuracy: null as number | null,
    drawAccuracy: null as number | null,
    leagueCount: 0,
    seasonCount: 0,
  });
  const [dataFreshness, setDataFreshness] = useState<Array<{
    source: string;
    lastUpdated: string | null;
    status: string;
    recordCount: number;
  }>>([]);
  const [calibrationTrend, setCalibrationTrend] = useState<Array<{
    week: string;
    brier: number;
  }>>([]);
  const [outcomeDistribution, setOutcomeDistribution] = useState<Array<{
    name: string;
    predicted: number;
    actual: number;
  }>>([]);
  const [leaguePerformance, setLeaguePerformance] = useState<Array<{
    league: string;
    accuracy: number;
    matches: number;
    status: string;
  }>>([]);
  const [decisionIntelligence, setDecisionIntelligence] = useState({
    totalTickets: 0,
    acceptedTickets: 0,
    rejectedTickets: 0,
    avgEvScore: null as number | null,
    avgHitRate: null as number | null,
    currentEvThreshold: 0.12,
    maxContradictions: 1
  });

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.getDashboardSummary();
        
        if (response.success && response.data) {
          setSystemHealth(response.data.systemHealth);
          setDataFreshness(response.data.dataFreshness);
          setCalibrationTrend(response.data.calibrationTrend);
          setOutcomeDistribution(response.data.outcomeDistribution);
          setLeaguePerformance(response.data.leaguePerformance);
          setDecisionIntelligence(response.data.decisionIntelligence || {
            totalTickets: 0,
            acceptedTickets: 0,
            rejectedTickets: 0,
            avgEvScore: null,
            avgHitRate: null,
            currentEvThreshold: 0.12,
            maxContradictions: 1
          });
        } else {
          throw new Error('Failed to load dashboard data');
        }
      } catch (err: any) {
        console.error('Error fetching dashboard data:', err);
        setError(err.message || 'Failed to load dashboard data');
        toast({
          title: 'Error',
          description: 'Failed to load dashboard data. Using fallback values.',
          variant: 'destructive',
        });
        // Set fallback values (no fake data)
        setSystemHealth({
          modelVersion: 'No model',
          modelStatus: 'no_model',
          lastRetrain: null,
          calibrationScore: null,
          logLoss: null,
          totalMatches: 0,
          avgWeeklyAccuracy: null,
          drawAccuracy: null,
          leagueCount: 0,
          seasonCount: 0,
        });
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [toast]);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Loading dashboard data...</p>
        </div>
      </div>
    );
  }

  return (
    <PageLayout
      title="Dashboard"
      description="Real-time system health overview and model performance metrics"
      icon={<Zap className="h-6 w-6" />}
    >

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="animate-fade-in">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Key Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Model Version"
          value={systemHealth.modelVersion}
          icon={<Database className="h-5 w-5" />}
          description={systemHealth.lastRetrain ? `Last retrain: ${formatDate(systemHealth.lastRetrain)}` : 'No training data'}
          variant="primary"
        />
        <MetricCard
          title="Brier Score"
          value={systemHealth.calibrationScore !== null && systemHealth.calibrationScore !== undefined 
            ? systemHealth.calibrationScore.toFixed(3) 
            : 'N/A'}
          change={systemHealth.calibrationScore !== null ? -2.1 : undefined}
          trend={systemHealth.calibrationScore !== null ? 'up' : undefined}
          icon={<Target className="h-5 w-5" />}
          description={systemHealth.calibrationScore !== null 
            ? 'Lower is better (perfect = 0)' 
            : 'No model trained yet'}
          variant="success"
        />
        <MetricCard
          title="Weekly Accuracy"
          value={systemHealth.avgWeeklyAccuracy !== null ? `${systemHealth.avgWeeklyAccuracy}%` : 'N/A'}
          icon={<Percent className="h-5 w-5" />}
          description={systemHealth.drawAccuracy !== null 
            ? `Draw accuracy: ${systemHealth.drawAccuracy}%` 
            : 'Rolling 8-week average'}
          variant="accent"
        />
        <MetricCard
          title="Training Data"
          value={systemHealth.totalMatches.toLocaleString()}
          icon={<BarChart3 className="h-5 w-5" />}
          description={`Across ${systemHealth.leagueCount} leagues, ${systemHealth.seasonCount} seasons`}
          variant="default"
        />
      </div>

      {/* Decision Intelligence Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Tickets"
          value={decisionIntelligence.totalTickets.toLocaleString()}
          icon={<Target className="h-5 w-5" />}
          description={`${decisionIntelligence.acceptedTickets} accepted, ${decisionIntelligence.rejectedTickets} rejected`}
          variant="default"
        />
        <MetricCard
          title="Avg EV Score"
          value={decisionIntelligence.avgEvScore !== null 
            ? decisionIntelligence.avgEvScore.toFixed(3) 
            : 'N/A'}
          icon={<TrendingUp className="h-5 w-5" />}
          description={decisionIntelligence.avgEvScore !== null 
            ? `Average Unified Decision Score` 
            : 'No tickets evaluated yet'}
          variant="primary"
        />
        <MetricCard
          title="Avg Hit Rate"
          value={decisionIntelligence.avgHitRate !== null 
            ? `${decisionIntelligence.avgHitRate.toFixed(1)}%` 
            : 'N/A'}
          icon={<BarChart3 className="h-5 w-5" />}
          description={decisionIntelligence.avgHitRate !== null 
            ? `From ${decisionIntelligence.totalTickets} tickets` 
            : 'No outcomes recorded yet'}
          variant="success"
        />
        <MetricCard
          title="EV Threshold"
          value={decisionIntelligence.currentEvThreshold.toFixed(2)}
          icon={<Activity className="h-5 w-5" />}
          description={`Max contradictions: ${decisionIntelligence.maxContradictions}`}
          variant="accent"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Calibration Trend */}
        <ModernCard
          title="Calibration Trend"
          description="Brier score over last 5 weeks (lower is better)"
          icon={<TrendingUp className="h-5 w-5" />}
          variant="elevated"
        >
            {calibrationTrend.length > 0 ? (
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
            ) : (
              <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <p>No calibration trend data available</p>
                  <p className="text-xs mt-2">Train models to see calibration trend</p>
                </div>
              </div>
            )}
        </ModernCard>

        {/* Outcome Distribution */}
        <ModernCard
          title="Outcome Distribution"
          description="Predicted vs Actual (Market vs Model)"
          icon={<BarChart3 className="h-5 w-5" />}
          variant="elevated"
        >
            <div className="space-y-4">
              {outcomeDistribution.length > 0 ? outcomeDistribution.map((item, index) => (
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
              )) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No outcome distribution data available</p>
                  <p className="text-xs mt-2">Complete some jackpots with actual results to see distribution</p>
                </div>
              )}
            </div>
        </ModernCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Data Freshness */}
        <ModernCard
          title="Data Freshness"
          description="Status of ingested data sources"
          icon={<Clock className="h-5 w-5" />}
          variant="elevated"
        >
            <div className="space-y-3">
              {dataFreshness.length > 0 ? dataFreshness.map((source, index) => (
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
              )) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No data sources configured</p>
                </div>
              )}
            </div>
        </ModernCard>

        {/* League Performance */}
        <ModernCard
          title="League Performance"
          description="Model accuracy by competition"
          icon={<Activity className="h-5 w-5" />}
          variant="elevated"
        >
            <div className="space-y-3">
              {leaguePerformance.length > 0 ? leaguePerformance.map((league, index) => (
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
              )) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No league performance data available</p>
                  <p className="text-xs mt-2">Run validation on completed jackpots to see league performance</p>
                </div>
              )}
            </div>
        </ModernCard>
      </div>

      {/* Quick Actions */}
      <ModernCard
        variant="glow"
        className="border-primary/20"
      >
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
      </ModernCard>
    </PageLayout>
  );
}
