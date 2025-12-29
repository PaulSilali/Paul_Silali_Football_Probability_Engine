import { useState, useMemo } from 'react';
import { Info, Download, FileText, Calculator, TrendingUp, Target, Zap, Scale, Users, AlertTriangle, CheckCircle, HelpCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { exportProbabilities } from '@/lib/export';
import { AccumulatorCalculator } from '@/components/AccumulatorCalculator';
import type { FixtureProbability } from '@/types';

// Base fixture data with odds
const baseFixtures = [
  { fixtureId: '1', homeTeam: 'Arsenal', awayTeam: 'Chelsea', odds: { home: 2.10, draw: 3.40, away: 3.60 } },
  { fixtureId: '2', homeTeam: 'Liverpool', awayTeam: 'Man City', odds: { home: 3.00, draw: 3.50, away: 2.40 } },
  { fixtureId: '3', homeTeam: 'Man United', awayTeam: 'Tottenham', odds: { home: 2.40, draw: 3.40, away: 3.00 } },
  { fixtureId: '4', homeTeam: 'Newcastle', awayTeam: 'Brighton', odds: { home: 2.05, draw: 3.50, away: 3.80 } },
  { fixtureId: '5', homeTeam: 'Aston Villa', awayTeam: 'West Ham', odds: { home: 1.90, draw: 3.60, away: 4.20 } },
];

// Calculate entropy: H = -Σ p_i * log2(p_i)
const calculateEntropy = (probs: number[]): number => {
  return -probs.reduce((sum, p) => {
    if (p <= 0) return sum;
    return sum + (p / 100) * Math.log2(p / 100);
  }, 0);
};

// Calculate market implied probabilities from odds
const getMarketProbs = (odds: { home: number; draw: number; away: number }) => {
  const total = 1/odds.home + 1/odds.draw + 1/odds.away;
  return {
    home: (1/odds.home / total) * 100,
    draw: (1/odds.draw / total) * 100,
    away: (1/odds.away / total) * 100,
  };
};

// Probability sets A-G as per system design
const probabilitySets: Record<string, { 
  name: string; 
  description: string; 
  icon: React.ElementType;
  useCase: string;
  guidance: string;
  probabilities: (FixtureProbability & { odds: { home: number; draw: number; away: number } })[] 
}> = {
  A: {
    name: 'Set A - Pure Model',
    description: 'Dixon-Coles statistical model only. Long-term, theory-driven estimates.',
    icon: Calculator,
    useCase: 'Contrarian bettors',
    guidance: 'Best if you believe the model captures value the market misses.',
    probabilities: [
      { ...baseFixtures[0], homeWinProbability: 48.00, drawProbability: 27.00, awayWinProbability: 25.00, confidenceLow: 42.1, confidenceHigh: 48.4 },
      { ...baseFixtures[1], homeWinProbability: 32.15, drawProbability: 28.45, awayWinProbability: 39.40, confidenceLow: 29.2, confidenceHigh: 35.1 },
      { ...baseFixtures[2], homeWinProbability: 41.67, drawProbability: 29.33, awayWinProbability: 29.00, confidenceLow: 38.5, confidenceHigh: 44.8 },
      { ...baseFixtures[3], homeWinProbability: 48.92, drawProbability: 26.54, awayWinProbability: 24.54, confidenceLow: 45.8, confidenceHigh: 52.0 },
      { ...baseFixtures[4], homeWinProbability: 52.18, drawProbability: 25.12, awayWinProbability: 22.70, confidenceLow: 49.1, confidenceHigh: 55.3 },
    ],
  },
  B: {
    name: 'Set B - Market-Aware (Balanced)',
    description: '60% model + 40% market odds via GLM. Recommended default.',
    icon: Scale,
    useCase: 'Balanced bettors',
    guidance: '🌟 Recommended for most users. Trusts model but respects market wisdom.',
    probabilities: [
      { ...baseFixtures[0], homeWinProbability: 52.00, drawProbability: 26.00, awayWinProbability: 22.00, confidenceLow: 41.0, confidenceHigh: 47.2 },
      { ...baseFixtures[1], homeWinProbability: 33.89, drawProbability: 27.11, awayWinProbability: 39.00, confidenceLow: 30.8, confidenceHigh: 37.0 },
      { ...baseFixtures[2], homeWinProbability: 40.23, drawProbability: 30.12, awayWinProbability: 29.65, confidenceLow: 37.1, confidenceHigh: 43.4 },
      { ...baseFixtures[3], homeWinProbability: 47.56, drawProbability: 27.33, awayWinProbability: 25.11, confidenceLow: 44.5, confidenceHigh: 50.6 },
      { ...baseFixtures[4], homeWinProbability: 50.89, drawProbability: 26.01, awayWinProbability: 23.10, confidenceLow: 47.8, confidenceHigh: 54.0 },
    ],
  },
  C: {
    name: 'Set C - Market-Dominant (Conservative)',
    description: '80% market + 20% model. For market-efficient believers.',
    icon: Target,
    useCase: 'Risk-averse',
    guidance: 'Conservative choice. Believes market is usually right.',
    probabilities: [
      { ...baseFixtures[0], homeWinProbability: 55.00, drawProbability: 25.00, awayWinProbability: 20.00, confidenceLow: 39.4, confidenceHigh: 45.6 },
      { ...baseFixtures[1], homeWinProbability: 31.00, drawProbability: 32.00, awayWinProbability: 37.00, confidenceLow: 28.0, confidenceHigh: 34.0 },
      { ...baseFixtures[2], homeWinProbability: 38.50, drawProbability: 33.00, awayWinProbability: 28.50, confidenceLow: 35.4, confidenceHigh: 41.6 },
      { ...baseFixtures[3], homeWinProbability: 45.00, drawProbability: 30.50, awayWinProbability: 24.50, confidenceLow: 41.9, confidenceHigh: 48.1 },
      { ...baseFixtures[4], homeWinProbability: 48.20, drawProbability: 29.30, awayWinProbability: 22.50, confidenceLow: 45.1, confidenceHigh: 51.3 },
    ],
  },
  D: {
    name: 'Set D - Draw-Boosted',
    description: 'Draw probability × 1.15. Jackpot survival strategy.',
    icon: TrendingUp,
    useCase: 'Draw specialists',
    guidance: 'Good for jackpots where draws are historically undervalued.',
    probabilities: [
      { ...baseFixtures[0], homeWinProbability: 44.00, drawProbability: 31.00, awayWinProbability: 25.00, confidenceLow: 40.7, confidenceHigh: 46.9 },
      { ...baseFixtures[1], homeWinProbability: 30.50, drawProbability: 32.70, awayWinProbability: 36.80, confidenceLow: 32.1, confidenceHigh: 38.3 },
      { ...baseFixtures[2], homeWinProbability: 38.20, drawProbability: 33.70, awayWinProbability: 28.10, confidenceLow: 36.0, confidenceHigh: 42.2 },
      { ...baseFixtures[3], homeWinProbability: 43.50, drawProbability: 30.50, awayWinProbability: 26.00, confidenceLow: 43.7, confidenceHigh: 49.9 },
      { ...baseFixtures[4], homeWinProbability: 46.80, drawProbability: 28.90, awayWinProbability: 24.30, confidenceLow: 46.5, confidenceHigh: 52.7 },
    ],
  },
  E: {
    name: 'Set E - High Conviction',
    description: 'Entropy-penalized. Sharper picks, fewer draws.',
    icon: Zap,
    useCase: 'Accumulator builders',
    guidance: 'Want aggressive, decisive picks? This set has lower entropy.',
    probabilities: [
      { ...baseFixtures[0], homeWinProbability: 58.00, drawProbability: 22.00, awayWinProbability: 20.00, confidenceLow: 37.0, confidenceHigh: 43.2 },
      { ...baseFixtures[1], homeWinProbability: 28.00, drawProbability: 24.00, awayWinProbability: 48.00, confidenceLow: 26.7, confidenceHigh: 32.9 },
      { ...baseFixtures[2], homeWinProbability: 46.00, drawProbability: 26.00, awayWinProbability: 28.00, confidenceLow: 34.1, confidenceHigh: 40.3 },
      { ...baseFixtures[3], homeWinProbability: 54.00, drawProbability: 23.00, awayWinProbability: 23.00, confidenceLow: 40.4, confidenceHigh: 46.6 },
      { ...baseFixtures[4], homeWinProbability: 58.00, drawProbability: 22.00, awayWinProbability: 20.00, confidenceLow: 43.7, confidenceHigh: 49.9 },
    ],
  },
  F: {
    name: 'Set F - Kelly-Weighted',
    description: 'Optimized for long-term bankroll growth.',
    icon: Calculator,
    useCase: 'Professional bettors',
    guidance: 'For pros: emphasizes matches with highest Kelly % edge.',
    probabilities: [
      { ...baseFixtures[0], homeWinProbability: 52.00, drawProbability: 26.00, awayWinProbability: 22.00, confidenceLow: 35.4, confidenceHigh: 41.6 },
      { ...baseFixtures[1], homeWinProbability: 33.89, drawProbability: 27.11, awayWinProbability: 39.00, confidenceLow: 32.9, confidenceHigh: 39.1 },
      { ...baseFixtures[2], homeWinProbability: 40.23, drawProbability: 30.12, awayWinProbability: 29.65, confidenceLow: 32.7, confidenceHigh: 38.9 },
      { ...baseFixtures[3], homeWinProbability: 47.56, drawProbability: 27.33, awayWinProbability: 25.11, confidenceLow: 38.1, confidenceHigh: 44.3 },
      { ...baseFixtures[4], homeWinProbability: 50.89, drawProbability: 26.01, awayWinProbability: 23.10, confidenceLow: 40.9, confidenceHigh: 47.1 },
    ],
  },
  G: {
    name: 'Set G - Ensemble',
    description: 'Weighted average of A, B, C by Brier score.',
    icon: Users,
    useCase: 'Diversified consensus',
    guidance: 'Risk-averse? This set diversifies across model perspectives.',
    probabilities: [
      { ...baseFixtures[0], homeWinProbability: 51.00, drawProbability: 26.00, awayWinProbability: 23.00, confidenceLow: 41.4, confidenceHigh: 47.6 },
      { ...baseFixtures[1], homeWinProbability: 33.46, drawProbability: 28.49, awayWinProbability: 38.05, confidenceLow: 29.9, confidenceHigh: 36.1 },
      { ...baseFixtures[2], homeWinProbability: 40.45, drawProbability: 30.04, awayWinProbability: 29.51, confidenceLow: 36.9, confidenceHigh: 43.1 },
      { ...baseFixtures[3], homeWinProbability: 47.16, drawProbability: 27.79, awayWinProbability: 25.05, confidenceLow: 43.9, confidenceHigh: 50.1 },
      { ...baseFixtures[4], homeWinProbability: 50.42, drawProbability: 26.14, awayWinProbability: 23.44, confidenceLow: 47.9, confidenceHigh: 54.1 },
    ],
  },
};

const setKeys = ['A', 'B', 'C', 'D', 'E', 'F', 'G'] as const;

type Selection = '1' | 'X' | '2' | null;

export default function ProbabilityOutput() {
  const [activeSet, setActiveSet] = useState<string>('B');
  const [showConfidenceBands, setShowConfidenceBands] = useState(false);
  const [selections, setSelections] = useState<Record<string, Selection>>({});

  const currentSet = probabilitySets[activeSet];
  const formatProbability = (value: number) => value.toFixed(1);

  const handleExport = (format: 'csv' | 'pdf') => {
    exportProbabilities(currentSet.probabilities, currentSet.name, format);
  };

  const toggleSelection = (fixtureId: string, selection: Selection) => {
    setSelections(prev => ({
      ...prev,
      [fixtureId]: prev[fixtureId] === selection ? null : selection
    }));
  };

  // Build accumulator data from selections
  const accumulatorFixtures = currentSet.probabilities
    .filter(prob => selections[prob.fixtureId])
    .map(prob => {
      const sel = selections[prob.fixtureId]!;
      const probability = sel === '1' ? prob.homeWinProbability 
        : sel === 'X' ? prob.drawProbability 
        : prob.awayWinProbability;
      const odds = sel === '1' ? prob.odds.home 
        : sel === 'X' ? prob.odds.draw 
        : prob.odds.away;
      
      return {
        id: prob.fixtureId,
        homeTeam: prob.homeTeam,
        awayTeam: prob.awayTeam,
        selection: sel,
        probability,
        odds,
      };
    });

  const getHighestProbOutcome = (prob: FixtureProbability): '1' | 'X' | '2' => {
    const { homeWinProbability, drawProbability, awayWinProbability } = prob;
    if (homeWinProbability >= drawProbability && homeWinProbability >= awayWinProbability) return '1';
    if (awayWinProbability >= homeWinProbability && awayWinProbability >= drawProbability) return '2';
    return 'X';
  };

  // Get confidence indicator based on entropy and market divergence
  const getConfidenceIndicator = (prob: FixtureProbability & { odds: { home: number; draw: number; away: number } }) => {
    const entropy = calculateEntropy([prob.homeWinProbability, prob.drawProbability, prob.awayWinProbability]);
    const marketProbs = getMarketProbs(prob.odds);
    const divergence = Math.abs(prob.homeWinProbability - marketProbs.home) + 
                       Math.abs(prob.drawProbability - marketProbs.draw) + 
                       Math.abs(prob.awayWinProbability - marketProbs.away);
    
    if (entropy < 1.0 && divergence < 15) {
      return { color: 'text-status-stable', icon: CheckCircle, label: 'High confidence' };
    } else if (entropy > 1.2 || divergence > 25) {
      return { color: 'text-status-degraded', icon: AlertTriangle, label: 'Low confidence' };
    }
    return { color: 'text-status-watch', icon: Info, label: 'Medium confidence' };
  };

  // Get divergence alert
  const getDivergenceAlert = (prob: FixtureProbability & { odds: { home: number; draw: number; away: number } }) => {
    const marketProbs = getMarketProbs(prob.odds);
    const homeDiv = prob.homeWinProbability - marketProbs.home;
    const drawDiv = prob.drawProbability - marketProbs.draw;
    const awayDiv = prob.awayWinProbability - marketProbs.away;
    
    const maxDiv = Math.max(Math.abs(homeDiv), Math.abs(drawDiv), Math.abs(awayDiv));
    if (maxDiv > 10) {
      const outcome = Math.abs(homeDiv) === maxDiv ? 'Home' : Math.abs(drawDiv) === maxDiv ? 'Draw' : 'Away';
      const direction = (Math.abs(homeDiv) === maxDiv ? homeDiv : Math.abs(drawDiv) === maxDiv ? drawDiv : awayDiv) > 0 ? 'more' : 'less';
      return `Model sees ${maxDiv.toFixed(0)}% ${direction} value in ${outcome} than market`;
    }
    return null;
  };

  // Consensus picks for current set
  const consensusPicks = useMemo(() => {
    return currentSet.probabilities.map(prob => getHighestProbOutcome(prob));
  }, [currentSet]);

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground text-glow">Probability Output</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Calculated probabilities for the current jackpot — 7 probability sets (A-G)
          </p>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="glass-card">
              <Download className="h-4 w-4 mr-2" />
              Export Set {activeSet}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => handleExport('csv')}>
              <Download className="h-4 w-4 mr-2" />
              Export as CSV
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleExport('pdf')}>
              <FileText className="h-4 w-4 mr-2" />
              Export as PDF
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* User Guidance Alert */}
      <Alert className="glass-card border-primary/20">
        <HelpCircle className="h-4 w-4 text-primary" />
        <AlertTitle>Which Set Should You Use?</AlertTitle>
        <AlertDescription className="space-y-1">
          <p><strong>New to jackpots?</strong> Start with <Badge className="bg-primary/20 text-primary">Set B (Balanced)</Badge> — trusts the model but respects market wisdom.</p>
          <p><strong>Want aggressive picks?</strong> Try <Badge variant="outline">Set E (Sharp)</Badge> — lower entropy, clearer decisions.</p>
          <p><strong>Conservative?</strong> Use <Badge variant="outline">Set C (Market-Dominant)</Badge> — believes market is usually right.</p>
        </AlertDescription>
      </Alert>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Main probability table */}
        <div className="xl:col-span-2">
          <Tabs value={activeSet} onValueChange={setActiveSet}>
            <ScrollArea className="w-full">
              <TabsList className="inline-flex w-auto min-w-full bg-background/50 p-1">
                {setKeys.map((key) => {
                  const set = probabilitySets[key];
                  const Icon = set.icon;
                  return (
                    <TabsTrigger 
                      key={key} 
                      value={key} 
                      className="flex items-center gap-2 px-4 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                    >
                      <Icon className="h-4 w-4" />
                      <span className="font-medium">{key}</span>
                      {key === 'B' && (
                        <Badge className="bg-accent/20 text-accent text-xs ml-1">★</Badge>
                      )}
                    </TabsTrigger>
                  );
                })}
              </TabsList>
              <ScrollBar orientation="horizontal" />
            </ScrollArea>

            {setKeys.map((key) => {
              const set = probabilitySets[key];
              return (
                <TabsContent key={key} value={key} className="mt-4 space-y-4">
                  {/* Guidance tooltip */}
                  <Card className="glass-card bg-primary/5 border-primary/20">
                    <CardContent className="pt-4 pb-3">
                      <p className="text-sm text-primary flex items-center gap-2">
                        <set.icon className="h-4 w-4" />
                        {set.guidance}
                      </p>
                    </CardContent>
                  </Card>

                  {/* Consensus Picks Row */}
                  <Card className="glass-card">
                    <CardContent className="pt-4 pb-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium text-muted-foreground">Consensus Picks:</span>
                        {set.probabilities.map((prob, idx) => {
                          const pick = getHighestProbOutcome(prob);
                          return (
                            <Tooltip key={prob.fixtureId}>
                              <TooltipTrigger>
                                <Badge 
                                  variant="outline" 
                                  className={`w-8 h-8 flex items-center justify-center text-sm font-bold ${
                                    pick === '1' ? 'bg-chart-1/20 text-chart-1 border-chart-1/50' :
                                    pick === 'X' ? 'bg-chart-3/20 text-chart-3 border-chart-3/50' :
                                    'bg-chart-2/20 text-chart-2 border-chart-2/50'
                                  }`}
                                >
                                  {pick}
                                </Badge>
                              </TooltipTrigger>
                              <TooltipContent>
                                Match {idx + 1}: {prob.homeTeam} vs {prob.awayTeam}
                              </TooltipContent>
                            </Tooltip>
                          );
                        })}
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="glass-card">
                    <CardHeader className="pb-4">
                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                        <div>
                          <CardTitle className="text-lg flex items-center gap-2">
                            <set.icon className="h-5 w-5 text-primary" />
                            {set.name}
                          </CardTitle>
                          <CardDescription>{set.description}</CardDescription>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setShowConfidenceBands(!showConfidenceBands)}
                          className="shrink-0"
                        >
                          {showConfidenceBands ? 'Hide' : 'Show'} Details
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[40px]">#</TableHead>
                            <TableHead>Fixture</TableHead>
                            <TableHead className="text-center w-[80px]">Home %</TableHead>
                            <TableHead className="text-center w-[80px]">Draw %</TableHead>
                            <TableHead className="text-center w-[80px]">Away %</TableHead>
                            <TableHead className="text-center w-[70px]">
                              <Tooltip>
                                <TooltipTrigger className="cursor-help flex items-center justify-center gap-1">
                                  <span>H</span>
                                  <Info className="h-3 w-3" />
                                </TooltipTrigger>
                                <TooltipContent>Entropy (uncertainty). Lower = more decisive pick.</TooltipContent>
                              </Tooltip>
                            </TableHead>
                            <TableHead className="text-center w-[60px]">Conf</TableHead>
                            <TableHead className="text-center w-[50px]">Pick</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {set.probabilities.map((prob, index) => {
                            const recommended = getHighestProbOutcome(prob);
                            const currentSelection = selections[prob.fixtureId];
                            const entropy = calculateEntropy([prob.homeWinProbability, prob.drawProbability, prob.awayWinProbability]);
                            const confidence = getConfidenceIndicator(prob);
                            const ConfIcon = confidence.icon;
                            const divergenceAlert = getDivergenceAlert(prob);
                            
                            return (
                              <>
                                <TableRow key={prob.fixtureId} className="hover:bg-primary/5">
                                  <TableCell className="text-muted-foreground tabular-nums font-medium">
                                    {index + 1}
                                  </TableCell>
                                  <TableCell>
                                    <div className="font-medium">{prob.homeTeam}</div>
                                    <div className="text-sm text-muted-foreground">vs {prob.awayTeam}</div>
                                  </TableCell>
                                  <TableCell className="text-center">
                                    <button
                                      onClick={() => toggleSelection(prob.fixtureId, '1')}
                                      className={`w-full p-1.5 rounded transition-all text-sm ${
                                        currentSelection === '1' 
                                          ? 'bg-primary text-primary-foreground' 
                                          : 'hover:bg-primary/10'
                                      }`}
                                    >
                                      <div className="font-medium tabular-nums">
                                        {formatProbability(prob.homeWinProbability)}%
                                      </div>
                                      {recommended === '1' && <span className="text-xs">★</span>}
                                    </button>
                                  </TableCell>
                                  <TableCell className="text-center">
                                    <button
                                      onClick={() => toggleSelection(prob.fixtureId, 'X')}
                                      className={`w-full p-1.5 rounded transition-all text-sm ${
                                        currentSelection === 'X' 
                                          ? 'bg-primary text-primary-foreground' 
                                          : 'hover:bg-primary/10'
                                      }`}
                                    >
                                      <div className="font-medium tabular-nums">
                                        {formatProbability(prob.drawProbability)}%
                                      </div>
                                      {recommended === 'X' && <span className="text-xs">★</span>}
                                    </button>
                                  </TableCell>
                                  <TableCell className="text-center">
                                    <button
                                      onClick={() => toggleSelection(prob.fixtureId, '2')}
                                      className={`w-full p-1.5 rounded transition-all text-sm ${
                                        currentSelection === '2' 
                                          ? 'bg-primary text-primary-foreground' 
                                          : 'hover:bg-primary/10'
                                      }`}
                                    >
                                      <div className="font-medium tabular-nums">
                                        {formatProbability(prob.awayWinProbability)}%
                                      </div>
                                      {recommended === '2' && <span className="text-xs">★</span>}
                                    </button>
                                  </TableCell>
                                  <TableCell className="text-center">
                                    <span className={`tabular-nums text-sm ${
                                      entropy < 1.0 ? 'text-status-stable' : 
                                      entropy > 1.2 ? 'text-status-degraded' : 'text-muted-foreground'
                                    }`}>
                                      {entropy.toFixed(2)}
                                    </span>
                                  </TableCell>
                                  <TableCell className="text-center">
                                    <Tooltip>
                                      <TooltipTrigger>
                                        <ConfIcon className={`h-4 w-4 ${confidence.color}`} />
                                      </TooltipTrigger>
                                      <TooltipContent>{confidence.label}</TooltipContent>
                                    </Tooltip>
                                  </TableCell>
                                  <TableCell className="text-center">
                                    <Badge 
                                      variant={currentSelection ? 'default' : 'outline'}
                                      className={currentSelection ? 'bg-primary' : ''}
                                    >
                                      {currentSelection || '—'}
                                    </Badge>
                                  </TableCell>
                                </TableRow>
                                {/* Divergence alert row */}
                                {showConfidenceBands && divergenceAlert && (
                                  <TableRow key={`${prob.fixtureId}-alert`} className="bg-status-watch/5">
                                    <TableCell colSpan={8} className="py-1">
                                      <div className="flex items-center gap-2 text-xs text-status-watch">
                                        <AlertTriangle className="h-3 w-3" />
                                        {divergenceAlert}
                                      </div>
                                    </TableCell>
                                  </TableRow>
                                )}
                              </>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                </TabsContent>
              );
            })}
          </Tabs>
        </div>

        {/* Accumulator Calculator */}
        <div className="xl:col-span-1">
          <AccumulatorCalculator fixtures={accumulatorFixtures} />
        </div>
      </div>

      <Card className="glass-card bg-muted/20">
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            <strong>Legend:</strong> ★ = Recommended pick | 
            <span className="text-status-stable"> 🟢 High confidence</span> (entropy &lt; 1.0, low divergence) | 
            <span className="text-status-watch"> 🟡 Medium</span> | 
            <span className="text-status-degraded"> 🔴 Low confidence</span> (entropy &gt; 1.2 or high divergence).
            H = Entropy (lower = more decisive).
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
