import { useMemo } from 'react';
import { 
  CheckCircle, 
  XCircle, 
  TrendingUp, 
  TrendingDown,
  Target,
  BarChart3,
  Layers,
  AlertTriangle
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
  ScatterChart,
  Scatter,
  Cell,
} from 'recharts';
import type { ParsedResult } from './PDFResultsImport';

interface GeneratedProbability {
  matchId: string;
  homeTeam: string;
  awayTeam: string;
  sets: {
    setA: { H: number; D: number; A: number };
    setB: { H: number; D: number; A: number };
    setC: { H: number; D: number; A: number };
    setD: { H: number; D: number; A: number };
    setE: { H: number; D: number; A: number };
    setF: { H: number; D: number; A: number };
    setG: { H: number; D: number; A: number };
    setH?: { H: number; D: number; A: number };
    setI?: { H: number; D: number; A: number };
    setJ?: { H: number; D: number; A: number };
  };
  confidence: number;
}

interface BacktestComparisonProps {
  results: ParsedResult[];
  probabilities: GeneratedProbability[];
}

const SET_NAMES = {
  setA: 'Set A - Pure Model',
  setB: 'Set B - Market-Aware (Balanced)',
  setC: 'Set C - Market-Dominant',
  setD: 'Set D - Draw-Boosted',
  setE: 'Set E - Entropy-Penalized',
  setF: 'Set F - Kelly-Weighted',
  setG: 'Set G - Ensemble',
  setH: 'Set H - Market Consensus Draw',
  setI: 'Set I - Formula-Based Draw',
  setJ: 'Set J - System-Selected Draw',
};

const SET_COLORS: Record<string, string> = {
  setA: 'hsl(var(--chart-1))',
  setB: 'hsl(var(--chart-2))',
  setC: 'hsl(var(--chart-3))',
  setD: 'hsl(var(--chart-4))',
  setE: 'hsl(var(--chart-5))',
  setF: 'hsl(210 80% 60%)',
  setG: 'hsl(280 80% 60%)',
  setH: 'hsl(150 80% 50%)',
  setI: 'hsl(30 80% 55%)',
  setJ: 'hsl(320 80% 55%)',
};

export function BacktestComparison({ results, probabilities }: BacktestComparisonProps) {
  // Calculate metrics for each probability set
  const setMetrics = useMemo(() => {
    const metrics: Record<string, {
      correct: number;
      total: number;
      brierScore: number;
      logLoss: number;
      predictions: { predicted: string; actual: string; correct: boolean }[];
    }> = {};

    // Include all sets A-J, but only process sets that exist in the data
    const allSetKeys = ['setA', 'setB', 'setC', 'setD', 'setE', 'setF', 'setG', 'setH', 'setI', 'setJ'] as const;
    // Filter to only sets that have data
    const setKeys = allSetKeys.filter(setKey => {
      // Check if at least one probability has this set
      return probabilities.some(prob => prob.sets[setKey] !== undefined);
    }) as typeof allSetKeys;

    setKeys.forEach(setKey => {
      let correct = 0;
      let brierSum = 0;
      let logLossSum = 0;
      const predictions: { predicted: string; actual: string; correct: boolean }[] = [];

      results.forEach((result, idx) => {
        const prob = probabilities[idx];
        if (!prob) return;

        const setProbs = prob.sets[setKey];
        const predictedResult = 
          setProbs.H >= setProbs.D && setProbs.H >= setProbs.A ? 'H' :
          setProbs.D >= setProbs.A ? 'D' : 'A';

        const isCorrect = predictedResult === result.result;
        if (isCorrect) correct++;

        predictions.push({
          predicted: predictedResult,
          actual: result.result,
          correct: isCorrect,
        });

        // Brier score calculation
        const actualH = result.result === 'H' ? 1 : 0;
        const actualD = result.result === 'D' ? 1 : 0;
        const actualA = result.result === 'A' ? 1 : 0;

        brierSum += Math.pow(setProbs.H - actualH, 2) + 
                   Math.pow(setProbs.D - actualD, 2) + 
                   Math.pow(setProbs.A - actualA, 2);

        // Log loss calculation
        const predictedProb = result.result === 'H' ? setProbs.H :
                             result.result === 'D' ? setProbs.D : setProbs.A;
        logLossSum += -Math.log(Math.max(predictedProb, 0.001));
      });

      metrics[setKey] = {
        correct,
        total: results.length,
        brierScore: brierSum / results.length,
        logLoss: logLossSum / results.length,
        predictions,
      };
    });

    return metrics;
  }, [results, probabilities]);

  // Find best performing set
  const bestSet = useMemo(() => {
    let best = 'setB';
    let bestAccuracy = 0;
    Object.entries(setMetrics).forEach(([key, metrics]) => {
      const accuracy = metrics.correct / metrics.total;
      if (accuracy > bestAccuracy) {
        bestAccuracy = accuracy;
        best = key;
      }
    });
    return best;
  }, [setMetrics]);

  // Chart data for set comparison
  const setComparisonData = useMemo(() => {
    return Object.entries(setMetrics).map(([key, metrics]) => ({
      name: key.replace('set', 'Set '),
      accuracy: ((metrics.correct / metrics.total) * 100).toFixed(1),
      brierScore: metrics.brierScore.toFixed(3),
      logLoss: metrics.logLoss.toFixed(3),
      fill: SET_COLORS[key],
    }));
  }, [setMetrics]);

  // Calibration data
  const calibrationData = useMemo(() => {
    const buckets: { predicted: number; actual: number; count: number }[] = [];
    const bucketSize = 0.1;

    for (let i = 0; i < 10; i++) {
      const lower = i * bucketSize;
      const upper = (i + 1) * bucketSize;
      let actualWins = 0;
      let count = 0;

      results.forEach((result, idx) => {
        const prob = probabilities[idx];
        if (!prob) return;

        const setProbs = prob.sets.setB; // Use Set B for calibration
        const outcomes = [
          { prob: setProbs.H, actual: result.result === 'H' },
          { prob: setProbs.D, actual: result.result === 'D' },
          { prob: setProbs.A, actual: result.result === 'A' },
        ];

        outcomes.forEach(o => {
          if (o.prob >= lower && o.prob < upper) {
            count++;
            if (o.actual) actualWins++;
          }
        });
      });

      if (count > 0) {
        buckets.push({
          predicted: (lower + upper) / 2,
          actual: actualWins / count,
          count,
        });
      }
    }

    return buckets.map(b => ({
      predicted: `${(b.predicted * 100).toFixed(0)}%`,
      predictedValue: b.predicted * 100,
      actualValue: b.actual * 100,
      count: b.count,
    }));
  }, [results, probabilities]);

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Best Performing Set</p>
                <p className="text-2xl font-bold">{bestSet.replace('set', 'Set ')}</p>
              </div>
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                <TrendingUp className="h-6 w-6 text-primary" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {((setMetrics[bestSet].correct / setMetrics[bestSet].total) * 100).toFixed(1)}% accuracy
            </p>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Set B Accuracy</p>
                <p className="text-2xl font-bold tabular-nums">
                  {((setMetrics.setB.correct / setMetrics.setB.total) * 100).toFixed(1)}%
                </p>
              </div>
              <div className="h-12 w-12 rounded-full bg-chart-2/10 flex items-center justify-center">
                <Target className="h-6 w-6 text-chart-2" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {setMetrics.setB.correct}/{setMetrics.setB.total} correct
            </p>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg Brier Score</p>
                <p className="text-2xl font-bold tabular-nums">
                  {setMetrics.setB.brierScore.toFixed(3)}
                </p>
              </div>
              <div className="h-12 w-12 rounded-full bg-chart-3/10 flex items-center justify-center">
                <BarChart3 className="h-6 w-6 text-chart-3" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Lower is better (0.20 typical)
            </p>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Matches Tested</p>
                <p className="text-2xl font-bold tabular-nums">{results.length}</p>
              </div>
              <div className="h-12 w-12 rounded-full bg-chart-4/10 flex items-center justify-center">
                <Layers className="h-6 w-6 text-chart-4" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Across {setKeys.length} probability sets
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="comparison">
        <TabsList className="mb-4">
          <TabsTrigger value="comparison">Set Comparison</TabsTrigger>
          <TabsTrigger value="detailed">Match Details</TabsTrigger>
          <TabsTrigger value="calibration">Calibration</TabsTrigger>
        </TabsList>

        {/* Set Comparison Tab */}
        <TabsContent value="comparison" className="space-y-4">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>Probability Set Performance</CardTitle>
              <CardDescription>
                Comparing accuracy across all probability sets ({setKeys.length} sets available)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={setComparisonData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis type="number" domain={[0, 100]} unit="%" />
                    <YAxis dataKey="name" type="category" width={80} />
                    <Tooltip 
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="glass-card p-3 border border-border">
                              <p className="font-medium">{data.name}</p>
                              <p className="text-sm">Accuracy: {data.accuracy}%</p>
                              <p className="text-sm">Brier: {data.brierScore}</p>
                              <p className="text-sm">Log Loss: {data.logLoss}</p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Bar dataKey="accuracy" radius={[0, 4, 4, 0]}>
                      {setComparisonData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Set Metrics Table */}
              <div className="mt-6">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Set</TableHead>
                      <TableHead className="text-right">Correct</TableHead>
                      <TableHead className="text-right">Accuracy</TableHead>
                      <TableHead className="text-right">Brier Score</TableHead>
                      <TableHead className="text-right">Log Loss</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Object.entries(setMetrics).map(([key, metrics]) => (
                      <TableRow key={key} className={key === bestSet ? 'bg-primary/5' : ''}>
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            <div 
                              className="w-3 h-3 rounded-full" 
                              style={{ backgroundColor: SET_COLORS[key] }}
                            />
                            {key.replace('set', 'Set ')}
                            {key === bestSet && (
                              <Badge variant="outline" className="ml-2 text-xs">Best</Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {metrics.correct}/{metrics.total}
                        </TableCell>
                        <TableCell className="text-right tabular-nums font-medium">
                          {((metrics.correct / metrics.total) * 100).toFixed(1)}%
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {metrics.brierScore.toFixed(3)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {metrics.logLoss.toFixed(3)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Detailed Match Results Tab */}
        <TabsContent value="detailed">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>Match-by-Match Backtest</CardTitle>
              <CardDescription>
                Comparing Set B predictions against actual results
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[50px]">#</TableHead>
                      <TableHead>Match</TableHead>
                      <TableHead className="text-right">P(H)</TableHead>
                      <TableHead className="text-right">P(D)</TableHead>
                      <TableHead className="text-right">P(A)</TableHead>
                      <TableHead className="text-center">Predicted</TableHead>
                      <TableHead className="text-center">Actual</TableHead>
                      <TableHead className="text-center">Result</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results.map((result, idx) => {
                      const prob = probabilities[idx];
                      if (!prob) return null;

                      const setProbs = prob.sets.setB;
                      const predictedResult = 
                        setProbs.H >= setProbs.D && setProbs.H >= setProbs.A ? 'H' :
                        setProbs.D >= setProbs.A ? 'D' : 'A';
                      const isCorrect = predictedResult === result.result;

                      return (
                        <TableRow key={result.id}>
                          <TableCell className="font-medium">{idx + 1}</TableCell>
                          <TableCell>
                            <span className="font-medium">{result.homeTeam}</span>
                            <span className="text-muted-foreground mx-2">vs</span>
                            <span>{result.awayTeam}</span>
                            <span className="text-muted-foreground ml-2 text-xs">
                              ({result.homeScore}-{result.awayScore})
                            </span>
                          </TableCell>
                          <TableCell className={`text-right tabular-nums ${result.result === 'H' ? 'font-bold text-green-600' : ''}`}>
                            {(setProbs.H * 100).toFixed(0)}%
                          </TableCell>
                          <TableCell className={`text-right tabular-nums ${result.result === 'D' ? 'font-bold text-green-600' : ''}`}>
                            {(setProbs.D * 100).toFixed(0)}%
                          </TableCell>
                          <TableCell className={`text-right tabular-nums ${result.result === 'A' ? 'font-bold text-green-600' : ''}`}>
                            {(setProbs.A * 100).toFixed(0)}%
                          </TableCell>
                          <TableCell className="text-center">
                            <Badge variant="outline">{predictedResult}</Badge>
                          </TableCell>
                          <TableCell className="text-center">
                            <Badge variant="secondary">{result.result}</Badge>
                          </TableCell>
                          <TableCell className="text-center">
                            {isCorrect ? (
                              <CheckCircle className="h-4 w-4 text-green-500 mx-auto" />
                            ) : (
                              <XCircle className="h-4 w-4 text-red-500 mx-auto" />
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Calibration Tab */}
        <TabsContent value="calibration">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>Calibration Analysis</CardTitle>
              <CardDescription>
                How well do predicted probabilities match actual outcomes?
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={calibrationData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="predicted" />
                    <YAxis domain={[0, 100]} unit="%" />
                    <Tooltip />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="predictedValue" 
                      stroke="hsl(var(--muted-foreground))" 
                      strokeDasharray="5 5"
                      name="Perfect Calibration"
                      dot={false}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="actualValue" 
                      stroke="hsl(var(--primary))" 
                      strokeWidth={2}
                      name="Actual Outcomes"
                      dot={{ fill: 'hsl(var(--primary))' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="mt-4 p-4 rounded-lg bg-muted/30 border border-border">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-medium mb-1">Calibration Interpretation</p>
                    <p className="text-muted-foreground">
                      Points close to the diagonal line indicate well-calibrated probabilities. 
                      Points above the line suggest overconfidence; below suggests underconfidence.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
