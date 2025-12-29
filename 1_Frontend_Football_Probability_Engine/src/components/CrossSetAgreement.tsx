import { useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { 
  GitCompare, 
  CheckCircle, 
  AlertTriangle, 
  XCircle,
  Users,
  Target
} from 'lucide-react';
import type { FixtureProbability } from '@/types';

interface ProbabilitySet {
  name: string;
  probabilities: FixtureProbability[];
}

interface CrossSetAgreementProps {
  sets: Record<string, ProbabilitySet>;
  activeSet: string;
}

type AgreementLevel = 'High' | 'Medium' | 'Low';

interface AgreementMetrics {
  overallAgreement: number; // 0-100
  level: AgreementLevel;
  unanimousPicks: number;
  majorityPicks: number;
  conflictedPicks: number;
  fixtureAgreements: {
    fixtureId: string;
    homeTeam: string;
    awayTeam: string;
    consensusPick: '1' | 'X' | '2' | null;
    agreementPct: number;
    pickCounts: { home: number; draw: number; away: number };
  }[];
}

const getHighestProbOutcome = (prob: FixtureProbability): '1' | 'X' | '2' => {
  const { homeWinProbability, drawProbability, awayWinProbability } = prob;
  if (homeWinProbability >= drawProbability && homeWinProbability >= awayWinProbability) return '1';
  if (awayWinProbability >= homeWinProbability && awayWinProbability >= drawProbability) return '2';
  return 'X';
};

export function CrossSetAgreement({ sets, activeSet }: CrossSetAgreementProps) {
  const metrics = useMemo<AgreementMetrics>(() => {
    const setKeys = Object.keys(sets);
    if (setKeys.length === 0) {
      return {
        overallAgreement: 0,
        level: 'Low',
        unanimousPicks: 0,
        majorityPicks: 0,
        conflictedPicks: 0,
        fixtureAgreements: [],
      };
    }

    const firstSet = sets[setKeys[0]];
    const fixtureCount = firstSet.probabilities.length;
    
    const fixtureAgreements: AgreementMetrics['fixtureAgreements'] = [];
    let totalAgreement = 0;
    let unanimousPicks = 0;
    let majorityPicks = 0;
    let conflictedPicks = 0;

    // For each fixture, count picks across all sets
    for (let i = 0; i < fixtureCount; i++) {
      const pickCounts = { home: 0, draw: 0, away: 0 };
      
      setKeys.forEach(key => {
        const prob = sets[key].probabilities[i];
        if (prob) {
          const pick = getHighestProbOutcome(prob);
          if (pick === '1') pickCounts.home++;
          else if (pick === 'X') pickCounts.draw++;
          else pickCounts.away++;
        }
      });

      const maxCount = Math.max(pickCounts.home, pickCounts.draw, pickCounts.away);
      const agreementPct = (maxCount / setKeys.length) * 100;
      
      let consensusPick: '1' | 'X' | '2' | null = null;
      if (pickCounts.home === maxCount) consensusPick = '1';
      else if (pickCounts.draw === maxCount) consensusPick = 'X';
      else if (pickCounts.away === maxCount) consensusPick = '2';

      if (maxCount === setKeys.length) unanimousPicks++;
      else if (maxCount >= Math.ceil(setKeys.length / 2)) majorityPicks++;
      else conflictedPicks++;

      totalAgreement += agreementPct;

      const fixture = firstSet.probabilities[i];
      fixtureAgreements.push({
        fixtureId: fixture.fixtureId,
        homeTeam: fixture.homeTeam,
        awayTeam: fixture.awayTeam,
        consensusPick,
        agreementPct,
        pickCounts,
      });
    }

    const overallAgreement = fixtureCount > 0 ? totalAgreement / fixtureCount : 0;
    
    let level: AgreementLevel;
    if (overallAgreement >= 85) level = 'High';
    else if (overallAgreement >= 60) level = 'Medium';
    else level = 'Low';

    return {
      overallAgreement,
      level,
      unanimousPicks,
      majorityPicks,
      conflictedPicks,
      fixtureAgreements,
    };
  }, [sets]);

  const getLevelColor = (level: AgreementLevel) => {
    switch (level) {
      case 'High': return 'text-status-stable bg-status-stable/10 border-status-stable/30';
      case 'Medium': return 'text-status-watch bg-status-watch/10 border-status-watch/30';
      case 'Low': return 'text-status-degraded bg-status-degraded/10 border-status-degraded/30';
    }
  };

  const getAgreementIcon = (pct: number) => {
    if (pct === 100) return <CheckCircle className="h-4 w-4 text-status-stable" />;
    if (pct >= 70) return <Target className="h-4 w-4 text-status-watch" />;
    return <AlertTriangle className="h-4 w-4 text-status-degraded" />;
  };

  return (
    <Card className="glass-card">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <GitCompare className="h-5 w-5 text-primary" />
              Cross-Set Agreement
            </CardTitle>
            <CardDescription>How much do Sets A-G agree on picks?</CardDescription>
          </div>
          <Badge variant="outline" className={`text-sm font-bold ${getLevelColor(metrics.level)}`}>
            {metrics.level} Agreement
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Overall Agreement */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Overall Set Agreement</span>
            <span className="font-bold text-lg tabular-nums">{metrics.overallAgreement.toFixed(0)}%</span>
          </div>
          <Progress 
            value={metrics.overallAgreement} 
            className={`h-2 ${
              metrics.level === 'High' ? '[&>div]:bg-status-stable' :
              metrics.level === 'Medium' ? '[&>div]:bg-status-watch' :
              '[&>div]:bg-status-degraded'
            }`}
          />
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="p-2 rounded-lg bg-status-stable/10 cursor-help">
                <div className="text-xl font-bold text-status-stable">{metrics.unanimousPicks}</div>
                <div className="text-xs text-muted-foreground">Unanimous</div>
              </div>
            </TooltipTrigger>
            <TooltipContent>All 7 sets agree on the pick</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <div className="p-2 rounded-lg bg-status-watch/10 cursor-help">
                <div className="text-xl font-bold text-status-watch">{metrics.majorityPicks}</div>
                <div className="text-xs text-muted-foreground">Majority</div>
              </div>
            </TooltipTrigger>
            <TooltipContent>4+ sets agree on the pick</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <div className="p-2 rounded-lg bg-status-degraded/10 cursor-help">
                <div className="text-xl font-bold text-status-degraded">{metrics.conflictedPicks}</div>
                <div className="text-xs text-muted-foreground">Conflicted</div>
              </div>
            </TooltipTrigger>
            <TooltipContent>No clear majority - sets disagree</TooltipContent>
          </Tooltip>
        </div>

        {/* Per-Fixture Agreement */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Match-by-Match Agreement</h4>
          <div className="space-y-1">
            {metrics.fixtureAgreements.map((fixture, idx) => (
              <div 
                key={fixture.fixtureId}
                className="flex items-center gap-2 p-2 rounded-lg bg-muted/20 hover:bg-muted/30 transition-colors"
              >
                <span className="text-xs text-muted-foreground w-5">{idx + 1}</span>
                {getAgreementIcon(fixture.agreementPct)}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">
                    {fixture.homeTeam} vs {fixture.awayTeam}
                  </div>
                </div>
                <div className="flex items-center gap-1 text-xs">
                  <Badge 
                    variant="outline" 
                    className={`w-8 justify-center ${
                      fixture.consensusPick === '1' ? 'bg-chart-1/20 text-chart-1 border-chart-1/50' :
                      fixture.consensusPick === 'X' ? 'bg-chart-3/20 text-chart-3 border-chart-3/50' :
                      'bg-chart-2/20 text-chart-2 border-chart-2/50'
                    }`}
                  >
                    {fixture.consensusPick || '?'}
                  </Badge>
                  <span className="text-muted-foreground tabular-nums w-10 text-right">
                    {fixture.agreementPct.toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Interpretation */}
        <div className={`p-3 rounded-lg border ${getLevelColor(metrics.level)}`}>
          <div className="flex items-start gap-2">
            <Users className="h-4 w-4 mt-0.5 shrink-0" />
            <p className="text-xs">
              {metrics.level === 'High' && 'Sets strongly agree this week. High confidence in consensus picks.'}
              {metrics.level === 'Medium' && 'Moderate agreement. Consider using multiple sets for diversification.'}
              {metrics.level === 'Low' && 'Sets disagree significantly. This is a "chaos week" - maximize coverage across sets.'}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
