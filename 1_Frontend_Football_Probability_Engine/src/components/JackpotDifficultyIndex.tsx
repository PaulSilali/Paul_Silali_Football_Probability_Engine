import { useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { 
  Gauge, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle, 
  HelpCircle,
  Percent,
  Scale,
  Target
} from 'lucide-react';
import type { FixtureProbability } from '@/types';

interface JackpotDifficultyIndexProps {
  probabilities: (FixtureProbability & { odds: { home: number; draw: number; away: number } })[];
}

// Calculate entropy: H = -Σ p_i * log2(p_i)
const calculateEntropy = (probs: number[]): number => {
  return -probs.reduce((sum, p) => {
    if (p <= 0) return sum;
    return sum + (p / 100) * Math.log2(p / 100);
  }, 0);
};

// Get market implied probabilities from odds
const getMarketProbs = (odds: { home: number; draw: number; away: number }) => {
  const total = 1/odds.home + 1/odds.draw + 1/odds.away;
  return {
    home: (1/odds.home / total) * 100,
    draw: (1/odds.draw / total) * 100,
    away: (1/odds.away / total) * 100,
  };
};

type DifficultyLevel = 'Easy' | 'Normal' | 'Hard' | 'Extreme';

interface JDIMetrics {
  score: number; // 0-100
  level: DifficultyLevel;
  avgEntropy: number;
  avgDrawRate: number;
  favoriteConcentration: number;
  marketModelDivergence: number;
  closeMatchCount: number;
}

export function JackpotDifficultyIndex({ probabilities }: JackpotDifficultyIndexProps) {
  const metrics = useMemo<JDIMetrics>(() => {
    if (probabilities.length === 0) {
      return {
        score: 50,
        level: 'Normal',
        avgEntropy: 0,
        avgDrawRate: 0,
        favoriteConcentration: 0,
        marketModelDivergence: 0,
        closeMatchCount: 0,
      };
    }

    // Calculate entropy for each match
    const entropies = probabilities.map(p => 
      calculateEntropy([p.homeWinProbability, p.drawProbability, p.awayWinProbability])
    );
    const avgEntropy = entropies.reduce((a, b) => a + b, 0) / entropies.length;

    // Average draw probability
    const avgDrawRate = probabilities.reduce((sum, p) => sum + p.drawProbability, 0) / probabilities.length;

    // Favorite concentration (how dominant favorites are)
    const maxProbs = probabilities.map(p => 
      Math.max(p.homeWinProbability, p.drawProbability, p.awayWinProbability)
    );
    const favoriteConcentration = maxProbs.reduce((a, b) => a + b, 0) / maxProbs.length;

    // Market-model divergence
    const divergences = probabilities.map(p => {
      const market = getMarketProbs(p.odds);
      return Math.abs(p.homeWinProbability - market.home) +
             Math.abs(p.drawProbability - market.draw) +
             Math.abs(p.awayWinProbability - market.away);
    });
    const marketModelDivergence = divergences.reduce((a, b) => a + b, 0) / divergences.length;

    // Close matches (where max probability < 40%)
    const closeMatchCount = probabilities.filter(p => 
      Math.max(p.homeWinProbability, p.drawProbability, p.awayWinProbability) < 40
    ).length;

    // Calculate JDI score (0-100, higher = harder)
    // Factors: high entropy, high draw rate, low favorite concentration, many close matches
    let score = 0;
    score += (avgEntropy / 1.58) * 25; // Max entropy is ~1.58 for 3 outcomes
    score += (avgDrawRate / 33.33) * 20; // Normalize to 33.33%
    score += (1 - favoriteConcentration / 60) * 20; // Lower favorite = harder
    score += (closeMatchCount / probabilities.length) * 20;
    score += (marketModelDivergence / 30) * 15; // High divergence = uncertainty

    score = Math.min(100, Math.max(0, score));

    let level: DifficultyLevel;
    if (score < 35) level = 'Easy';
    else if (score < 55) level = 'Normal';
    else if (score < 75) level = 'Hard';
    else level = 'Extreme';

    return {
      score,
      level,
      avgEntropy,
      avgDrawRate,
      favoriteConcentration,
      marketModelDivergence,
      closeMatchCount,
    };
  }, [probabilities]);

  const getLevelColor = (level: DifficultyLevel) => {
    switch (level) {
      case 'Easy': return 'text-status-stable bg-status-stable/10 border-status-stable/30';
      case 'Normal': return 'text-primary bg-primary/10 border-primary/30';
      case 'Hard': return 'text-status-watch bg-status-watch/10 border-status-watch/30';
      case 'Extreme': return 'text-status-degraded bg-status-degraded/10 border-status-degraded/30';
    }
  };

  const getLevelIcon = (level: DifficultyLevel) => {
    switch (level) {
      case 'Easy': return CheckCircle;
      case 'Normal': return Target;
      case 'Hard': return AlertTriangle;
      case 'Extreme': return AlertTriangle;
    }
  };

  const LevelIcon = getLevelIcon(metrics.level);

  return (
    <Card className="glass-card">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Gauge className="h-5 w-5 text-primary" />
              Jackpot Difficulty Index
            </CardTitle>
            <CardDescription>Week's overall prediction difficulty</CardDescription>
          </div>
          <Badge variant="outline" className={`text-sm font-bold ${getLevelColor(metrics.level)}`}>
            <LevelIcon className="h-4 w-4 mr-1" />
            {metrics.level}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Main JDI Score */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Difficulty Score</span>
            <span className="font-bold text-lg tabular-nums">{metrics.score.toFixed(0)}/100</span>
          </div>
          <div className="relative h-3 bg-muted/30 rounded-full overflow-hidden">
            <div 
              className={`absolute h-full rounded-full transition-all duration-500 ${
                metrics.level === 'Easy' ? 'bg-status-stable' :
                metrics.level === 'Normal' ? 'bg-primary' :
                metrics.level === 'Hard' ? 'bg-status-watch' :
                'bg-status-degraded'
              }`}
              style={{ width: `${metrics.score}%` }}
            />
            {/* Difficulty markers */}
            <div className="absolute top-0 left-[35%] w-px h-full bg-border/50" />
            <div className="absolute top-0 left-[55%] w-px h-full bg-border/50" />
            <div className="absolute top-0 left-[75%] w-px h-full bg-border/50" />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Easy</span>
            <span>Normal</span>
            <span>Hard</span>
            <span>Extreme</span>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 gap-3 pt-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="p-3 rounded-lg bg-muted/20 space-y-1 cursor-help">
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Scale className="h-3 w-3" />
                  Avg Entropy
                </div>
                <div className="text-lg font-bold tabular-nums">
                  {metrics.avgEntropy.toFixed(2)}
                </div>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p className="max-w-[200px] text-xs">
                Average uncertainty across matches. Higher = more unpredictable outcomes. Max ~1.58.
              </p>
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <div className="p-3 rounded-lg bg-muted/20 space-y-1 cursor-help">
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Percent className="h-3 w-3" />
                  Avg Draw %
                </div>
                <div className={`text-lg font-bold tabular-nums ${
                  metrics.avgDrawRate > 30 ? 'text-status-watch' : ''
                }`}>
                  {metrics.avgDrawRate.toFixed(1)}%
                </div>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p className="max-w-[200px] text-xs">
                Average draw probability. High draw rates make jackpots harder to predict.
              </p>
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <div className="p-3 rounded-lg bg-muted/20 space-y-1 cursor-help">
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <TrendingUp className="h-3 w-3" />
                  Close Matches
                </div>
                <div className="text-lg font-bold tabular-nums">
                  {metrics.closeMatchCount}/{probabilities.length}
                </div>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p className="max-w-[200px] text-xs">
                Matches where no outcome exceeds 40%. These are coin-flip scenarios.
              </p>
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <div className="p-3 rounded-lg bg-muted/20 space-y-1 cursor-help">
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <AlertTriangle className="h-3 w-3" />
                  Model-Market Div
                </div>
                <div className={`text-lg font-bold tabular-nums ${
                  metrics.marketModelDivergence > 20 ? 'text-status-watch' : ''
                }`}>
                  {metrics.marketModelDivergence.toFixed(1)}%
                </div>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p className="max-w-[200px] text-xs">
                Average divergence between model and market odds. High divergence = uncertainty about true probabilities.
              </p>
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Interpretation */}
        <div className={`p-3 rounded-lg border ${getLevelColor(metrics.level)}`}>
          <div className="flex items-start gap-2">
            <HelpCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <p className="text-xs">
              {metrics.level === 'Easy' && 'This week has clear favorites and low entropy. Model predictions should be more reliable.'}
              {metrics.level === 'Normal' && 'Balanced difficulty with some uncertainty. Use multiple probability sets for coverage.'}
              {metrics.level === 'Hard' && 'High uncertainty this week. Consider draw-enhanced sets and conservative strategies.'}
              {metrics.level === 'Extreme' && 'Extremely unpredictable week. Maximize coverage and diversify across all probability sets.'}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
