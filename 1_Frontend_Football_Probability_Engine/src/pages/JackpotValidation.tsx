import { useState } from 'react';
import {
  Trophy,
  CheckCircle,
  XCircle,
  BarChart3,
  Target,
  TrendingUp,
  Calendar,
  ArrowRight,
  Eye,
  Download,
  Database,
  Sparkles
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
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
} from 'recharts';
import { toast } from 'sonner';

// Mock jackpot validation data
interface JackpotMatch {
  id: string;
  homeTeam: string;
  awayTeam: string;
  predictedH: number;
  predictedD: number;
  predictedA: number;
  actualResult: 'H' | 'D' | 'A';
  prediction: 'H' | 'D' | 'A';
  correct: boolean;
  confidence: number;
}

interface JackpotValidation {
  id: string;
  jackpotId: string;
  date: string;
  matches: JackpotMatch[];
  setUsed: string;
  correctPredictions: number;
  totalMatches: number;
  brierScore: number;
}

const mockValidations: JackpotValidation[] = [
  {
    id: '1',
    jackpotId: 'JK-2024-1230',
    date: '2024-12-22',
    setUsed: 'Set B',
    correctPredictions: 10,
    totalMatches: 13,
    brierScore: 0.152,
    matches: [
      { id: '1', homeTeam: 'Arsenal', awayTeam: 'Chelsea', predictedH: 0.52, predictedD: 0.26, predictedA: 0.22, actualResult: 'H', prediction: 'H', correct: true, confidence: 0.52 },
      { id: '2', homeTeam: 'Liverpool', awayTeam: 'Man City', predictedH: 0.38, predictedD: 0.29, predictedA: 0.33, actualResult: 'D', prediction: 'H', correct: false, confidence: 0.38 },
      { id: '3', homeTeam: 'Tottenham', awayTeam: 'Newcastle', predictedH: 0.45, predictedD: 0.28, predictedA: 0.27, actualResult: 'H', prediction: 'H', correct: true, confidence: 0.45 },
      { id: '4', homeTeam: 'Man United', awayTeam: 'Aston Villa', predictedH: 0.41, predictedD: 0.30, predictedA: 0.29, actualResult: 'A', prediction: 'H', correct: false, confidence: 0.41 },
      { id: '5', homeTeam: 'Brighton', awayTeam: 'Wolves', predictedH: 0.48, predictedD: 0.27, predictedA: 0.25, actualResult: 'H', prediction: 'H', correct: true, confidence: 0.48 },
      { id: '6', homeTeam: 'Everton', awayTeam: 'West Ham', predictedH: 0.35, predictedD: 0.32, predictedA: 0.33, actualResult: 'D', prediction: 'D', correct: true, confidence: 0.35 },
      { id: '7', homeTeam: 'Bournemouth', awayTeam: 'Fulham', predictedH: 0.42, predictedD: 0.29, predictedA: 0.29, actualResult: 'H', prediction: 'H', correct: true, confidence: 0.42 },
      { id: '8', homeTeam: 'Crystal Palace', awayTeam: 'Brentford', predictedH: 0.38, predictedD: 0.31, predictedA: 0.31, actualResult: 'A', prediction: 'D', correct: false, confidence: 0.38 },
      { id: '9', homeTeam: 'Nottm Forest', awayTeam: 'Burnley', predictedH: 0.47, predictedD: 0.28, predictedA: 0.25, actualResult: 'H', prediction: 'H', correct: true, confidence: 0.47 },
      { id: '10', homeTeam: 'Sheffield Utd', awayTeam: 'Luton', predictedH: 0.40, predictedD: 0.30, predictedA: 0.30, actualResult: 'H', prediction: 'H', correct: true, confidence: 0.40 },
      { id: '11', homeTeam: 'Barcelona', awayTeam: 'Real Madrid', predictedH: 0.44, predictedD: 0.28, predictedA: 0.28, actualResult: 'D', prediction: 'H', correct: false, confidence: 0.44 },
      { id: '12', homeTeam: 'Bayern Munich', awayTeam: 'Dortmund', predictedH: 0.55, predictedD: 0.24, predictedA: 0.21, actualResult: 'H', prediction: 'H', correct: true, confidence: 0.55 },
      { id: '13', homeTeam: 'Juventus', awayTeam: 'AC Milan', predictedH: 0.43, predictedD: 0.29, predictedA: 0.28, actualResult: 'H', prediction: 'H', correct: true, confidence: 0.43 },
    ],
  },
  {
    id: '2',
    jackpotId: 'JK-2024-1229',
    date: '2024-12-15',
    setUsed: 'Set C',
    correctPredictions: 11,
    totalMatches: 13,
    brierScore: 0.138,
    matches: [],
  },
  {
    id: '3',
    jackpotId: 'JK-2024-1228',
    date: '2024-12-08',
    setUsed: 'Set B',
    correctPredictions: 9,
    totalMatches: 13,
    brierScore: 0.167,
    matches: [],
  },
];

const performanceTrend = [
  { week: 'W48', accuracy: 69, brierScore: 0.167 },
  { week: 'W49', accuracy: 77, brierScore: 0.152 },
  { week: 'W50', accuracy: 85, brierScore: 0.138 },
  { week: 'W51', accuracy: 77, brierScore: 0.152 },
];

const outcomeBreakdown = [
  { name: 'Home Wins', predicted: 42, actual: 44, color: 'hsl(var(--chart-1))' },
  { name: 'Draws', predicted: 28, actual: 26, color: 'hsl(var(--chart-2))' },
  { name: 'Away Wins', predicted: 30, actual: 30, color: 'hsl(var(--chart-3))' },
];

const confidenceAccuracy = [
  { confidence: '40-50%', accuracy: 48, count: 24 },
  { confidence: '50-60%', accuracy: 58, count: 32 },
  { confidence: '60-70%', accuracy: 65, count: 18 },
  { confidence: '70-80%', accuracy: 74, count: 8 },
  { confidence: '80%+', accuracy: 82, count: 4 },
];

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function ResultIcon({ predicted, actual }: { predicted: string; actual: string }) {
  if (predicted === actual) {
    return <CheckCircle className="h-4 w-4 text-green-500" />;
  }
  return <XCircle className="h-4 w-4 text-red-500" />;
}

export default function JackpotValidation() {
  const [selectedJackpot, setSelectedJackpot] = useState(mockValidations[0]);
  const [viewMode, setViewMode] = useState<'table' | 'visual'>('table');
  const [isExporting, setIsExporting] = useState(false);

  const accuracy = (selectedJackpot.correctPredictions / selectedJackpot.totalMatches) * 100;

  const handleExportToTraining = async () => {
    setIsExporting(true);
    // Simulate export process
    await new Promise(resolve => setTimeout(resolve, 1500));
    toast.success('Validation data exported to training pipeline', {
      description: `${selectedJackpot.matches.length} matches added to calibration dataset`
    });
    setIsExporting(false);
  };

  const handleExportAll = async () => {
    setIsExporting(true);
    await new Promise(resolve => setTimeout(resolve, 2000));
    const totalMatches = mockValidations.reduce((acc, v) => acc + v.matches.length, 0);
    toast.success('All validation data exported', {
      description: `${totalMatches} matches across ${mockValidations.length} jackpots added to training`
    });
    setIsExporting(false);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header with glassmorphism */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="animate-fade-in">
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 rounded-lg bg-primary/10">
              <Trophy className="h-5 w-5 text-primary" />
            </div>
            <h1 className="text-2xl font-semibold gradient-text">Jackpot Validation</h1>
          </div>
          <p className="text-sm text-muted-foreground">
            Compare predictions vs actual outcomes — export to calibration training
          </p>
        </div>
        <div className="flex items-center gap-3 animate-slide-in-right">
          <Select
            value={selectedJackpot.id}
            onValueChange={(v) => {
              const jackpot = mockValidations.find(j => j.id === v);
              if (jackpot) setSelectedJackpot(jackpot);
            }}
          >
            <SelectTrigger className="w-[180px] glass-card">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {mockValidations.map((j) => (
                <SelectItem key={j.id} value={j.id}>
                  {j.jackpotId}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Export to Training Card */}
      <Card className="glass-card-elevated border-primary/20 animate-fade-in-up">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-gradient-to-br from-primary/20 to-accent/20">
                <Database className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-accent" />
                  Export Validation Data to Training
                </h3>
                <p className="text-sm text-muted-foreground">
                  Feed validated predictions into the calibration model for improved accuracy
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={handleExportToTraining}
                disabled={isExporting || selectedJackpot.matches.length === 0}
                className="glass-card border-primary/30 hover:bg-primary/10"
              >
                <Download className="h-4 w-4 mr-2" />
                Export Selected
              </Button>
              <Button
                onClick={handleExportAll}
                disabled={isExporting}
                className="btn-glow bg-primary text-primary-foreground"
              >
                <Database className="h-4 w-4 mr-2" />
                Export All to Training
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Accuracy</p>
                <p className="text-2xl font-bold tabular-nums">{accuracy.toFixed(1)}%</p>
              </div>
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                <Target className="h-6 w-6 text-primary" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {selectedJackpot.correctPredictions}/{selectedJackpot.totalMatches} correct
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Brier Score</p>
                <p className="text-2xl font-bold tabular-nums">{selectedJackpot.brierScore.toFixed(3)}</p>
              </div>
              <div className="h-12 w-12 rounded-full bg-chart-2/10 flex items-center justify-center">
                <BarChart3 className="h-6 w-6 text-chart-2" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Lower is better (0.20 typical)
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Set Used</p>
                <p className="text-2xl font-bold">{selectedJackpot.setUsed}</p>
              </div>
              <div className="h-12 w-12 rounded-full bg-chart-3/10 flex items-center justify-center">
                <TrendingUp className="h-6 w-6 text-chart-3" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Probability set configuration
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Date</p>
                <p className="text-2xl font-bold">{formatDate(selectedJackpot.date)}</p>
              </div>
              <div className="h-12 w-12 rounded-full bg-chart-4/10 flex items-center justify-center">
                <Calendar className="h-6 w-6 text-chart-4" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Jackpot {selectedJackpot.jackpotId}
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="matches">
        <TabsList>
          <TabsTrigger value="matches" className="gap-2">
            <Trophy className="h-4 w-4" />
            Match Results
          </TabsTrigger>
          <TabsTrigger value="analytics" className="gap-2">
            <BarChart3 className="h-4 w-4" />
            Analytics
          </TabsTrigger>
          <TabsTrigger value="history" className="gap-2">
            <Calendar className="h-4 w-4" />
            History
          </TabsTrigger>
        </TabsList>

        {/* Match Results Tab */}
        <TabsContent value="matches" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">Match-by-Match Comparison</CardTitle>
                  <CardDescription>
                    Predicted probabilities vs actual outcomes
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant={viewMode === 'table' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setViewMode('table')}
                  >
                    Table
                  </Button>
                  <Button
                    variant={viewMode === 'visual' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setViewMode('visual')}
                  >
                    Visual
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {selectedJackpot.matches.length > 0 ? (
                viewMode === 'table' ? (
                  <ScrollArea className="h-[400px]">
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
                        {selectedJackpot.matches.map((match, idx) => (
                          <TableRow key={match.id}>
                            <TableCell className="font-medium">{idx + 1}</TableCell>
                            <TableCell>
                              <span className="font-medium">{match.homeTeam}</span>
                              <span className="text-muted-foreground mx-2">vs</span>
                              <span>{match.awayTeam}</span>
                            </TableCell>
                            <TableCell className={`text-right tabular-nums ${match.actualResult === 'H' ? 'font-bold text-green-600' : ''}`}>
                              {(match.predictedH * 100).toFixed(0)}%
                            </TableCell>
                            <TableCell className={`text-right tabular-nums ${match.actualResult === 'D' ? 'font-bold text-green-600' : ''}`}>
                              {(match.predictedD * 100).toFixed(0)}%
                            </TableCell>
                            <TableCell className={`text-right tabular-nums ${match.actualResult === 'A' ? 'font-bold text-green-600' : ''}`}>
                              {(match.predictedA * 100).toFixed(0)}%
                            </TableCell>
                            <TableCell className="text-center">
                              <Badge variant="outline">{match.prediction}</Badge>
                            </TableCell>
                            <TableCell className="text-center">
                              <Badge variant="secondary">{match.actualResult}</Badge>
                            </TableCell>
                            <TableCell className="text-center">
                              <ResultIcon predicted={match.prediction} actual={match.actualResult} />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {selectedJackpot.matches.map((match, idx) => (
                      <div
                        key={match.id}
                        className={`p-3 rounded-lg border ${match.correct ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'}`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-muted-foreground">Match {idx + 1}</span>
                          <ResultIcon predicted={match.prediction} actual={match.actualResult} />
                        </div>
                        <div className="flex items-center gap-2 text-sm">
                          <span className="font-medium">{match.homeTeam}</span>
                          <ArrowRight className="h-3 w-3 text-muted-foreground" />
                          <span>{match.awayTeam}</span>
                        </div>
                        <div className="flex items-center gap-4 mt-2 text-xs">
                          <div className="flex items-center gap-1">
                            <span className="text-muted-foreground">Pred:</span>
                            <Badge variant="outline" className="text-xs">{match.prediction}</Badge>
                          </div>
                          <div className="flex items-center gap-1">
                            <span className="text-muted-foreground">Actual:</span>
                            <Badge variant="secondary" className="text-xs">{match.actualResult}</Badge>
                          </div>
                          <div className="text-muted-foreground">
                            Conf: {(match.confidence * 100).toFixed(0)}%
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <Trophy className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No match data available for this jackpot.</p>
                  <p className="text-sm">Import results from the Data Ingestion page.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Outcome Distribution</CardTitle>
                <CardDescription>Predicted vs actual outcome frequencies</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[250px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={outcomeBreakdown}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="name" className="text-xs" />
                      <YAxis className="text-xs" />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="predicted" name="Predicted %" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="actual" name="Actual %" fill="hsl(var(--chart-2))" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Confidence vs Accuracy</CardTitle>
                <CardDescription>How well calibrated are the predictions</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[250px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={confidenceAccuracy}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="confidence" className="text-xs" />
                      <YAxis tickFormatter={(v) => `${v}%`} className="text-xs" />
                      <Tooltip formatter={(v: number) => `${v}%`} />
                      <Bar dataKey="accuracy" name="Accuracy" fill="hsl(var(--chart-3))" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Weekly Performance Trend</CardTitle>
              <CardDescription>Accuracy and Brier score over time</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={performanceTrend}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="week" className="text-xs" />
                    <YAxis yAxisId="left" tickFormatter={(v) => `${v}%`} className="text-xs" />
                    <YAxis yAxisId="right" orientation="right" domain={[0.1, 0.2]} className="text-xs" />
                    <Tooltip />
                    <Legend />
                    <Line yAxisId="left" type="monotone" dataKey="accuracy" name="Accuracy %" stroke="hsl(var(--chart-1))" strokeWidth={2} dot={{ r: 4 }} />
                    <Line yAxisId="right" type="monotone" dataKey="brierScore" name="Brier Score" stroke="hsl(var(--chart-2))" strokeWidth={2} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Validation History</CardTitle>
              <CardDescription>All validated jackpots with performance metrics</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Jackpot ID</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Set</TableHead>
                      <TableHead className="text-right">Correct</TableHead>
                      <TableHead className="text-right">Accuracy</TableHead>
                      <TableHead className="text-right">Brier</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mockValidations.map((v) => (
                      <TableRow key={v.id}>
                        <TableCell className="font-mono text-sm">{v.jackpotId}</TableCell>
                        <TableCell>{formatDate(v.date)}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{v.setUsed}</Badge>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {v.correctPredictions}/{v.totalMatches}
                        </TableCell>
                        <TableCell className="text-right">
                          <span className={(v.correctPredictions / v.totalMatches) >= 0.75 ? 'text-green-600 font-medium' : ''}>
                            {((v.correctPredictions / v.totalMatches) * 100).toFixed(1)}%
                          </span>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{v.brierScore.toFixed(3)}</TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedJackpot(v)}
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            View
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
