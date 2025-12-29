import { useState } from 'react';
import { Info, Calculator, TrendingUp, Target, Zap, Scale, Users } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { ProbabilitySet, FixtureProbability } from '@/types';

const sets: (ProbabilitySet & { icon: React.ElementType; useCase: string })[] = [
  {
    id: 'A',
    name: 'Set A: Pure Model',
    description: 'Dixon-Coles statistical model without market adjustments. Best for contrarian bettors who believe the model captures value the market misses.',
    icon: Calculator,
    useCase: 'Contrarian bettors, model believers',
    probabilities: [
      { fixtureId: '1', homeTeam: 'Arsenal', awayTeam: 'Chelsea', homeWinProbability: 48.00, drawProbability: 27.00, awayWinProbability: 25.00 },
      { fixtureId: '2', homeTeam: 'Liverpool', awayTeam: 'Man City', homeWinProbability: 32.15, drawProbability: 28.45, awayWinProbability: 39.40 },
      { fixtureId: '3', homeTeam: 'Man United', awayTeam: 'Tottenham', homeWinProbability: 41.67, drawProbability: 29.33, awayWinProbability: 29.00 },
    ],
  },
  {
    id: 'B',
    name: 'Set B: Market-Aware (Balanced)',
    description: '60% model + 40% market odds via GLM weighting. Recommended default for most users.',
    icon: Scale,
    useCase: 'Balanced bettors (recommended)',
    probabilities: [
      { fixtureId: '1', homeTeam: 'Arsenal', awayTeam: 'Chelsea', homeWinProbability: 52.00, drawProbability: 26.00, awayWinProbability: 22.00 },
      { fixtureId: '2', homeTeam: 'Liverpool', awayTeam: 'Man City', homeWinProbability: 33.45, drawProbability: 27.89, awayWinProbability: 38.66 },
      { fixtureId: '3', homeTeam: 'Man United', awayTeam: 'Tottenham', homeWinProbability: 40.23, drawProbability: 30.12, awayWinProbability: 29.65 },
    ],
  },
  {
    id: 'C',
    name: 'Set C: Market-Dominant (Conservative)',
    description: '80% market odds + 20% model. For risk-averse bettors who believe market is usually right.',
    icon: Target,
    useCase: 'Risk-averse, market-efficient believers',
    probabilities: [
      { fixtureId: '1', homeTeam: 'Arsenal', awayTeam: 'Chelsea', homeWinProbability: 55.00, drawProbability: 25.00, awayWinProbability: 20.00 },
      { fixtureId: '2', homeTeam: 'Liverpool', awayTeam: 'Man City', homeWinProbability: 34.78, drawProbability: 29.12, awayWinProbability: 36.10 },
      { fixtureId: '3', homeTeam: 'Man United', awayTeam: 'Tottenham', homeWinProbability: 39.45, drawProbability: 30.67, awayWinProbability: 29.88 },
    ],
  },
  {
    id: 'D',
    name: 'Set D: Draw-Boosted (Risk-Adjusted)',
    description: 'Model with draw probability × 1.15. Draws are historically undervalued in jackpots.',
    icon: TrendingUp,
    useCase: 'Jackpot-specific strategists',
    probabilities: [
      { fixtureId: '1', homeTeam: 'Arsenal', awayTeam: 'Chelsea', homeWinProbability: 44.00, drawProbability: 31.00, awayWinProbability: 25.00 },
      { fixtureId: '2', homeTeam: 'Liverpool', awayTeam: 'Man City', homeWinProbability: 30.50, drawProbability: 32.70, awayWinProbability: 36.80 },
      { fixtureId: '3', homeTeam: 'Man United', awayTeam: 'Tottenham', homeWinProbability: 38.20, drawProbability: 33.70, awayWinProbability: 28.10 },
    ],
  },
  {
    id: 'E',
    name: 'Set E: Entropy-Penalized (High Conviction)',
    description: 'Probabilities pushed toward extremes (temperature=1.5). Fewer draws, clearer picks.',
    icon: Zap,
    useCase: 'Accumulator builders seeking decisive picks',
    probabilities: [
      { fixtureId: '1', homeTeam: 'Arsenal', awayTeam: 'Chelsea', homeWinProbability: 58.00, drawProbability: 22.00, awayWinProbability: 20.00 },
      { fixtureId: '2', homeTeam: 'Liverpool', awayTeam: 'Man City', homeWinProbability: 28.00, drawProbability: 24.00, awayWinProbability: 48.00 },
      { fixtureId: '3', homeTeam: 'Man United', awayTeam: 'Tottenham', homeWinProbability: 46.00, drawProbability: 26.00, awayWinProbability: 28.00 },
    ],
  },
  {
    id: 'F',
    name: 'Set F: Kelly-Weighted (Bankroll Optimized)',
    description: 'Model probabilities weighted by Kelly criterion for long-term bankroll growth optimization.',
    icon: Calculator,
    useCase: 'Professional bettors',
    probabilities: [
      { fixtureId: '1', homeTeam: 'Arsenal', awayTeam: 'Chelsea', homeWinProbability: 52.00, drawProbability: 26.00, awayWinProbability: 22.00 },
      { fixtureId: '2', homeTeam: 'Liverpool', awayTeam: 'Man City', homeWinProbability: 33.89, drawProbability: 27.11, awayWinProbability: 39.00 },
      { fixtureId: '3', homeTeam: 'Man United', awayTeam: 'Tottenham', homeWinProbability: 40.23, drawProbability: 30.12, awayWinProbability: 29.65 },
    ],
  },
  {
    id: 'G',
    name: 'Set G: Ensemble (Meta-Model)',
    description: 'Average of Sets A, B, C weighted by historical Brier score performance. Diversified consensus.',
    icon: Users,
    useCase: 'Risk-averse, seeking diversification',
    probabilities: [
      { fixtureId: '1', homeTeam: 'Arsenal', awayTeam: 'Chelsea', homeWinProbability: 51.00, drawProbability: 26.00, awayWinProbability: 23.00 },
      { fixtureId: '2', homeTeam: 'Liverpool', awayTeam: 'Man City', homeWinProbability: 33.46, drawProbability: 28.49, awayWinProbability: 38.05 },
      { fixtureId: '3', homeTeam: 'Man United', awayTeam: 'Tottenham', homeWinProbability: 40.45, drawProbability: 30.04, awayWinProbability: 29.51 },
    ],
  },
];

export default function SetsComparison() {
  const [showDelta, setShowDelta] = useState(false);
  const [selectedSets, setSelectedSets] = useState(['A', 'B', 'C', 'D', 'E', 'F', 'G']);
  const baseSet = sets.find(s => s.id === 'A')!;
  const visibleSets = sets.filter(s => selectedSets.includes(s.id));

  const formatProbability = (value: number) => value.toFixed(2);
  
  const formatDelta = (value: number, baseValue: number) => {
    const delta = value - baseValue;
    if (Math.abs(delta) < 0.01) return '—';
    const sign = delta > 0 ? '+' : '';
    return `${sign}${delta.toFixed(2)}`;
  };

  const getDeltaColor = (value: number, baseValue: number) => {
    const delta = value - baseValue;
    if (Math.abs(delta) < 0.5) return 'text-muted-foreground';
    if (delta > 0) return 'text-status-stable';
    return 'text-status-degraded';
  };

  const toggleSet = (id: string) => {
    setSelectedSets(prev => 
      prev.includes(id) 
        ? prev.filter(s => s !== id)
        : [...prev, id]
    );
  };

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground text-glow">Probability Sets Comparison</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Compare 7 different probability estimation approaches (A-G)
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center space-x-2">
            <Switch
              id="show-delta"
              checked={showDelta}
              onCheckedChange={setShowDelta}
            />
            <Label htmlFor="show-delta" className="text-sm">
              Show deltas vs Set A
            </Label>
          </div>
        </div>
      </div>

      {/* Set Selection & Explanations */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {sets.map((set) => {
          const Icon = set.icon;
          const isSelected = selectedSets.includes(set.id);
          return (
            <Card 
              key={set.id} 
              className={`glass-card cursor-pointer transition-all duration-300 hover:scale-[1.02] ${
                isSelected ? 'ring-2 ring-primary/50 glow-primary' : 'opacity-60'
              }`}
              onClick={() => toggleSet(set.id)}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <span className={`flex h-7 w-7 items-center justify-center rounded-lg ${
                    isSelected ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
                  }`}>
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="flex-1">Set {set.id}</span>
                  {set.id === 'B' && (
                    <Badge className="bg-accent/20 text-accent text-xs">Default</Badge>
                  )}
                  {set.id === 'F' && (
                    <Badge className="bg-chart-4/20 text-chart-4 text-xs">Pro</Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-xs text-muted-foreground line-clamp-2">{set.description}</p>
                <div className="flex items-center gap-1">
                  <Badge variant="outline" className="text-xs">
                    {set.useCase}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Mathematical Definitions Panel */}
      <Card className="glass-card-elevated">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Info className="h-4 w-4 text-primary" />
            Set Formulas
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs font-mono">
            <div className="p-3 rounded-lg bg-background/50">
              <span className="text-primary font-bold">Set A:</span>
              <span className="text-muted-foreground ml-2">P = Calibrate(DC(λ,ρ))</span>
            </div>
            <div className="p-3 rounded-lg bg-background/50">
              <span className="text-primary font-bold">Set B:</span>
              <span className="text-muted-foreground ml-2">P = GLM(0.6×M + 0.4×O)</span>
            </div>
            <div className="p-3 rounded-lg bg-background/50">
              <span className="text-primary font-bold">Set C:</span>
              <span className="text-muted-foreground ml-2">P = 0.8×O + 0.2×M</span>
            </div>
            <div className="p-3 rounded-lg bg-background/50">
              <span className="text-primary font-bold">Set D:</span>
              <span className="text-muted-foreground ml-2">P_X' = P_X × 1.15</span>
            </div>
            <div className="p-3 rounded-lg bg-background/50">
              <span className="text-primary font-bold">Set E:</span>
              <span className="text-muted-foreground ml-2">P = Softmax(logit(B)×1.5)</span>
            </div>
            <div className="p-3 rounded-lg bg-background/50">
              <span className="text-primary font-bold">Set F:</span>
              <span className="text-muted-foreground ml-2">K = (p×O-1)/(O-1)</span>
            </div>
            <div className="p-3 rounded-lg bg-background/50 md:col-span-2">
              <span className="text-primary font-bold">Set G:</span>
              <span className="text-muted-foreground ml-2">P = Σw_i×P_i where w_i ∝ 1/BS_i</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Comparison Table */}
      <Card className="glass-card">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg">Side-by-Side Comparison</CardTitle>
          <CardDescription>
            {showDelta 
              ? 'Showing differences relative to Set A (Pure Model)'
              : 'Showing absolute probabilities for each selected set'
            }
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="home" className="w-full">
            <TabsList className="grid grid-cols-3 w-full max-w-md">
              <TabsTrigger value="home">Home Win %</TabsTrigger>
              <TabsTrigger value="draw">Draw %</TabsTrigger>
              <TabsTrigger value="away">Away Win %</TabsTrigger>
            </TabsList>
            
            <TabsContent value="home" className="mt-4">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="sticky left-0 bg-card">Fixture</TableHead>
                      {visibleSets.map(set => (
                        <TableHead key={set.id} className="text-right w-[100px]">
                          <Tooltip>
                            <TooltipTrigger className="flex items-center justify-end gap-1 cursor-help">
                              <Badge variant="outline" className="text-xs">{set.id}</Badge>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">{set.name}: {set.description}</TooltipContent>
                          </Tooltip>
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {baseSet.probabilities.map((baseProbability) => (
                      <TableRow key={baseProbability.fixtureId} className="hover:bg-primary/5">
                        <TableCell className="font-medium sticky left-0 bg-card">
                          {baseProbability.homeTeam} vs {baseProbability.awayTeam}
                        </TableCell>
                        {visibleSets.map(set => {
                          const prob = set.probabilities.find(p => p.fixtureId === baseProbability.fixtureId);
                          const value = prob?.homeWinProbability || 0;
                          const baseValue = baseProbability.homeWinProbability;
                          
                          return (
                            <TableCell key={set.id} className="text-right tabular-nums">
                              {showDelta && set.id !== 'A' ? (
                                <span className={getDeltaColor(value, baseValue)}>
                                  {formatDelta(value, baseValue)}
                                </span>
                              ) : (
                                <span>{formatProbability(value)}%</span>
                              )}
                            </TableCell>
                          );
                        })}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>

            <TabsContent value="draw" className="mt-4">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="sticky left-0 bg-card">Fixture</TableHead>
                      {visibleSets.map(set => (
                        <TableHead key={set.id} className="text-right w-[100px]">
                          <Badge variant="outline" className="text-xs">{set.id}</Badge>
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {baseSet.probabilities.map((baseProbability) => (
                      <TableRow key={baseProbability.fixtureId} className="hover:bg-primary/5">
                        <TableCell className="font-medium sticky left-0 bg-card">
                          {baseProbability.homeTeam} vs {baseProbability.awayTeam}
                        </TableCell>
                        {visibleSets.map(set => {
                          const prob = set.probabilities.find(p => p.fixtureId === baseProbability.fixtureId);
                          const value = prob?.drawProbability || 0;
                          const baseValue = baseProbability.drawProbability;
                          
                          return (
                            <TableCell key={set.id} className="text-right tabular-nums">
                              {showDelta && set.id !== 'A' ? (
                                <span className={getDeltaColor(value, baseValue)}>
                                  {formatDelta(value, baseValue)}
                                </span>
                              ) : (
                                <span>{formatProbability(value)}%</span>
                              )}
                            </TableCell>
                          );
                        })}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>

            <TabsContent value="away" className="mt-4">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="sticky left-0 bg-card">Fixture</TableHead>
                      {visibleSets.map(set => (
                        <TableHead key={set.id} className="text-right w-[100px]">
                          <Badge variant="outline" className="text-xs">{set.id}</Badge>
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {baseSet.probabilities.map((baseProbability) => (
                      <TableRow key={baseProbability.fixtureId} className="hover:bg-primary/5">
                        <TableCell className="font-medium sticky left-0 bg-card">
                          {baseProbability.homeTeam} vs {baseProbability.awayTeam}
                        </TableCell>
                        {visibleSets.map(set => {
                          const prob = set.probabilities.find(p => p.fixtureId === baseProbability.fixtureId);
                          const value = prob?.awayWinProbability || 0;
                          const baseValue = baseProbability.awayWinProbability;
                          
                          return (
                            <TableCell key={set.id} className="text-right tabular-nums">
                              {showDelta && set.id !== 'A' ? (
                                <span className={getDeltaColor(value, baseValue)}>
                                  {formatDelta(value, baseValue)}
                                </span>
                              ) : (
                                <span>{formatProbability(value)}%</span>
                              )}
                            </TableCell>
                          );
                        })}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
