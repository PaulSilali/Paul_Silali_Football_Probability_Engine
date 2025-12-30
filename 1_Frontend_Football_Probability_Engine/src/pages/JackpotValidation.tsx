import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
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
  Sparkles,
  Loader2
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
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/services/api';

// Helper to convert result format
const convertResult = (result: '1' | 'X' | '2'): 'H' | 'D' | 'A' => {
  if (result === '1') return 'H';
  if (result === 'X') return 'D';
  return 'A';
};

const convertResultBack = (result: 'H' | 'D' | 'A'): '1' | 'X' | '2' => {
  if (result === 'H') return '1';
  if (result === 'D') return 'X';
  return '2';
};

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

// Calculate analytics - aggregate across ALL predictions or selected jackpot
const calculateAnalytics = (
  jackpot: JackpotValidation | null, 
  allValidations: JackpotValidation[] = [],
  aggregateAll: boolean = false
) => {
  // If aggregating all, use all validations; otherwise use selected jackpot
  const validationsToUse = aggregateAll ? allValidations : 
    (jackpot ? allValidations.filter(v => 
      v.jackpotId.replace(/ \(Set [A-G]\)/g, '') === jackpot.jackpotId.replace(/ \(Set [A-G]\)/g, '')
    ) : []);
  
  if (validationsToUse.length === 0) {
    return {
      performanceTrend: [],
      outcomeBreakdown: [],
      confidenceAccuracy: [],
      setComparison: [],
      aggregatedStats: null,
    };
  }
  
  // Performance trend - aggregate across all sets for same jackpot(s)
  const performanceTrend = validationsToUse.map(v => ({
    week: v.setUsed,
    accuracy: (v.correctPredictions / v.totalMatches) * 100,
    brierScore: v.brierScore,
    date: v.date,
  }));
  
  // Aggregate outcome breakdown across ALL matches from all validations
  let predictedH = 0, predictedD = 0, predictedA = 0;
  let actualH = 0, actualD = 0, actualA = 0;
  let totalMatches = 0;
  
  validationsToUse.forEach(validation => {
    validation.matches.forEach(match => {
      totalMatches++;
      // Count predictions
      if (match.prediction === 'H') predictedH++;
      else if (match.prediction === 'D') predictedD++;
      else predictedA++;
      
      // Count actuals
      if (match.actualResult === 'H') actualH++;
      else if (match.actualResult === 'D') actualD++;
      else actualA++;
    });
  });
  
  const outcomeBreakdown = [
    {
      name: 'Home Wins',
      predicted: totalMatches > 0 ? (predictedH / totalMatches) * 100 : 0,
      actual: totalMatches > 0 ? (actualH / totalMatches) * 100 : 0,
      color: 'hsl(var(--chart-1))',
    },
    {
      name: 'Draws',
      predicted: totalMatches > 0 ? (predictedD / totalMatches) * 100 : 0,
      actual: totalMatches > 0 ? (actualD / totalMatches) * 100 : 0,
      color: 'hsl(var(--chart-2))',
    },
    {
      name: 'Away Wins',
      predicted: totalMatches > 0 ? (predictedA / totalMatches) * 100 : 0,
      actual: totalMatches > 0 ? (actualA / totalMatches) * 100 : 0,
      color: 'hsl(var(--chart-3))',
    },
  ];
  
  // Confidence vs accuracy - aggregate across all matches
  const confidenceBuckets: Record<string, { correct: number; total: number }> = {
    '40-50%': { correct: 0, total: 0 },
    '50-60%': { correct: 0, total: 0 },
    '60-70%': { correct: 0, total: 0 },
    '70-80%': { correct: 0, total: 0 },
    '80%+': { correct: 0, total: 0 },
  };
  
  validationsToUse.forEach(validation => {
    validation.matches.forEach(match => {
      const conf = match.confidence * 100;
      let bucket = '40-50%';
      if (conf >= 80) bucket = '80%+';
      else if (conf >= 70) bucket = '70-80%';
      else if (conf >= 60) bucket = '60-70%';
      else if (conf >= 50) bucket = '50-60%';
      
      confidenceBuckets[bucket].total++;
      if (match.correct) confidenceBuckets[bucket].correct++;
    });
  });
  
  const confidenceAccuracy = Object.entries(confidenceBuckets)
    .filter(([_, data]) => data.total > 0)
    .map(([confidence, data]) => ({
      confidence,
      accuracy: (data.correct / data.total) * 100,
      count: data.total,
    }));
  
  // Set comparison - aggregate across all jackpots, grouped by set
  const setStats: Record<string, { correct: number; total: number; brier: number; count: number }> = {};
  
  validationsToUse.forEach(v => {
    const setKey = v.setUsed;
    if (!setStats[setKey]) {
      setStats[setKey] = { correct: 0, total: 0, brier: 0, count: 0 };
    }
    setStats[setKey].correct += v.correctPredictions;
    setStats[setKey].total += v.totalMatches;
    setStats[setKey].brier += v.brierScore * v.totalMatches;
    setStats[setKey].count += 1;
  });
  
  const setComparison = Object.entries(setStats).map(([set, stats]) => ({
    set,
    accuracy: stats.total > 0 ? (stats.correct / stats.total) * 100 : 0,
    brierScore: stats.total > 0 ? stats.brier / stats.total : 0,
    correct: stats.correct,
    total: stats.total,
    jackpotCount: stats.count,
  }));
  
  // Aggregated stats across all predictions
  const totalCorrect = validationsToUse.reduce((sum, v) => sum + v.correctPredictions, 0);
  const totalTotal = validationsToUse.reduce((sum, v) => sum + v.totalMatches, 0);
  const avgBrier = validationsToUse.reduce((sum, v) => sum + (v.brierScore * v.totalMatches), 0) / totalTotal;
  
  const aggregatedStats = {
    totalPredictions: validationsToUse.length,
    totalMatches,
    totalCorrect,
    overallAccuracy: totalTotal > 0 ? (totalCorrect / totalTotal) * 100 : 0,
    avgBrierScore: avgBrier || 0,
  };
  
  return {
    performanceTrend,
    outcomeBreakdown,
    confidenceAccuracy,
    setComparison,
    aggregatedStats,
  };
};

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
  const [searchParams] = useSearchParams();
  const jackpotId = searchParams.get('jackpotId');
  const [validations, setValidations] = useState<JackpotValidation[]>([]);
  const [selectedJackpot, setSelectedJackpot] = useState<JackpotValidation | null>(null);
  const [viewMode, setViewMode] = useState<'table' | 'visual'>('table');
  const [isExporting, setIsExporting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadedProbabilities, setLoadedProbabilities] = useState<Record<string, any>>({});
  const [aggregateMode, setAggregateMode] = useState<'all' | 'selected'>('all');
  const { toast } = useToast();

  // Load ALL saved results with actual results across all jackpots
  useEffect(() => {
    const loadValidations = async () => {
      try {
        setLoading(true);
        const validationList: JackpotValidation[] = [];
        const processedJackpots = new Set<string>();
        
        // Load ALL saved results across all jackpots
        const allSavedResponse = await apiClient.getAllSavedResults(500);
        const allSavedResults = allSavedResponse.success && allSavedResponse.data?.results 
          ? allSavedResponse.data.results.filter((r: any) => r.actualResults && Object.keys(r.actualResults).length > 0)
          : [];
        
        console.log(`Loaded ${allSavedResults.length} saved results with actual outcomes`);
        
        // Process each saved result
        for (const savedResult of allSavedResults) {
          const resultJackpotId = savedResult.jackpotId;
          if (!resultJackpotId) continue;
          
          // Load probabilities for this jackpot (cache to avoid duplicate loads)
          let probData: any = null;
          if (!processedJackpots.has(resultJackpotId)) {
            try {
              const probResponse = await apiClient.getProbabilities(resultJackpotId);
              probData = (probResponse as any).success ? (probResponse as any).data : probResponse;
              if (probData && probData.probabilitySets && probData.fixtures) {
                processedJackpots.add(resultJackpotId);
                setLoadedProbabilities(prev => ({ ...prev, [resultJackpotId]: probData.probabilitySets }));
              }
            } catch (err) {
              console.warn(`Failed to load probabilities for jackpot ${resultJackpotId}:`, err);
              continue;
            }
          } else {
            // Use cached probabilities
            probData = {
              probabilitySets: loadedProbabilities[resultJackpotId],
              fixtures: null // Will need to reconstruct or load separately
            };
          }
          
          if (!probData || !probData.probabilitySets) continue;
          
          // Get fixtures - try to load if not cached
          let fixtures = probData.fixtures || [];
          if (fixtures.length === 0 && savedResult.totalFixtures) {
            // Try to reconstruct fixture list from saved result
            const fixtureIds = Object.keys(savedResult.actualResults || {});
            fixtures = fixtureIds.map((id, idx) => ({ id, homeTeam: '', awayTeam: '' }));
          }
          
          // Validate EACH set separately (A-G)
          const setKeys = ['A', 'B', 'C', 'D', 'E', 'F', 'G'];
          
          setKeys.forEach(setId => {
            const hasSelections = savedResult.selections && savedResult.selections[setId];
            const hasProbabilities = probData.probabilitySets[setId];
            
            if (!hasSelections && !hasProbabilities) {
              return; // Skip sets with no data
            }
            
            const matches: JackpotMatch[] = [];
            let correctCount = 0;
            let totalBrier = 0;
            
            fixtures.forEach((fixture: any, idx: number) => {
              const fixtureId = fixture.id || String(idx + 1);
              const actualResultStr = savedResult.actualResults[fixtureId];
              if (!actualResultStr) return;
              
              const actualResult = convertResult(actualResultStr as '1' | 'X' | '2');
              
              // Get probabilities for this set
              const setProbs = probData.probabilitySets[setId];
              if (!setProbs || !setProbs[idx]) return;
              
              const prob = setProbs[idx];
              const predictedH = prob.homeWinProbability / 100;
              const predictedD = prob.drawProbability / 100;
              const predictedA = prob.awayWinProbability / 100;
              
              // Get prediction - prioritize saved selections over highest probability
              let prediction: 'H' | 'D' | 'A' = 'H';
              if (predictedD > predictedH && predictedD > predictedA) prediction = 'D';
              else if (predictedA > predictedH && predictedA > predictedD) prediction = 'A';
              
              // Use saved selection if available (this is what user picked)
              if (hasSelections) {
                const setSelections = savedResult.selections[setId];
                const selection = setSelections[fixtureId] || 
                                 (Object.values(setSelections)[idx] as string);
                if (selection) {
                  prediction = convertResult(selection as '1' | 'X' | '2');
                }
              }
              
              const correct = prediction === actualResult;
              if (correct) correctCount++;
              
              // Calculate Brier score for this match
              const actualH = actualResult === 'H' ? 1 : 0;
              const actualD = actualResult === 'D' ? 1 : 0;
              const actualA = actualResult === 'A' ? 1 : 0;
              const brier = Math.pow(predictedH - actualH, 2) + 
                           Math.pow(predictedD - actualD, 2) + 
                           Math.pow(predictedA - actualA, 2);
              totalBrier += brier;
              
              const confidence = Math.max(predictedH, predictedD, predictedA);
              
              matches.push({
                id: `${savedResult.id}-${fixtureId}`,
                homeTeam: fixture.homeTeam || `Match ${idx + 1}`,
                awayTeam: fixture.awayTeam || '',
                predictedH,
                predictedD,
                predictedA,
                actualResult,
                prediction,
                correct,
                confidence,
              });
            });
            
            if (matches.length > 0) {
              const brierScore = totalBrier / matches.length;
              validationList.push({
                id: `${savedResult.id}-${setId}`,
                jackpotId: `${resultJackpotId} (Set ${setId})`,
                date: savedResult.createdAt || new Date().toISOString(),
                matches,
                setUsed: `Set ${setId}`,
                correctPredictions: correctCount,
                totalMatches: matches.length,
                brierScore,
              });
            }
          });
        }
        
        console.log(`Created ${validationList.length} validations from ${allSavedResults.length} saved results`);
        
        setValidations(validationList);
        if (validationList.length > 0) {
          // If jackpotId specified, filter to that jackpot, otherwise default to Set B
          if (jackpotId) {
            const jackpotValidations = validationList.filter(v => 
              v.jackpotId.replace(/ \(Set [A-G]\)/g, '') === jackpotId
            );
            if (jackpotValidations.length > 0) {
              const setBValidation = jackpotValidations.find(v => v.setUsed === 'Set B');
              setSelectedJackpot(setBValidation || jackpotValidations[0]);
            } else {
              const setBValidation = validationList.find(v => v.setUsed === 'Set B');
              setSelectedJackpot(setBValidation || validationList[0]);
            }
          } else {
            // Default to Set B (recommended) if available, otherwise use first validation
            const setBValidation = validationList.find(v => v.setUsed === 'Set B');
            setSelectedJackpot(setBValidation || validationList[0]);
          }
        }
      } catch (err: any) {
        console.error('Error loading validations:', err);
        toast({
          title: 'Error',
          description: 'Failed to load validation data: ' + (err.message || 'Unknown error'),
          variant: 'destructive',
        });
      } finally {
        setLoading(false);
      }
    };
    
    loadValidations();
  }, [jackpotId, toast]);

  const accuracy = selectedJackpot 
    ? (selectedJackpot.correctPredictions / selectedJackpot.totalMatches) * 100 
    : 0;

  const analytics = useMemo(() => 
    calculateAnalytics(selectedJackpot, validations, aggregateMode === 'all'), 
    [selectedJackpot, validations, aggregateMode]
  );

  const handleExportToTraining = async () => {
    if (!selectedJackpot) return;
    
    setIsExporting(true);
    try {
      // Export selected validation to training
      const response = await apiClient.exportValidationToTraining([selectedJackpot.id]);
      
      if (response.success) {
        toast({
          title: 'Success',
          description: `Validation data exported to training pipeline. ${selectedJackpot.matches.length} matches added to calibration dataset.`,
        });
      } else {
        throw new Error(response.message || 'Export failed');
      }
    } catch (err: any) {
      console.error('Export error:', err);
      toast({
        title: 'Error',
        description: 'Failed to export: ' + (err.message || 'Unknown error'),
        variant: 'destructive',
      });
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportAll = async () => {
    setIsExporting(true);
    try {
      // Export all validations to training
      const validationIds = validations.map(v => v.id);
      const response = await apiClient.exportValidationToTraining(validationIds);
      
      if (response.success) {
        const totalMatches = validations.reduce((acc, v) => acc + v.matches.length, 0);
        toast({
          title: 'Success',
          description: `All validation data exported. ${response.data?.exported_count || validations.length} validations with ${totalMatches} matches added to training.`,
        });
      } else {
        throw new Error(response.message || 'Export failed');
      }
    } catch (err: any) {
      console.error('Export error:', err);
      toast({
        title: 'Error',
        description: 'Failed to export: ' + (err.message || 'Unknown error'),
        variant: 'destructive',
      });
    } finally {
      setIsExporting(false);
    }
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
          {loading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm text-muted-foreground">Loading...</span>
            </div>
          ) : (
            <Select
              value={selectedJackpot?.id || ''}
              onValueChange={(v) => {
                const jackpot = validations.find(j => j.id === v);
                if (jackpot) setSelectedJackpot(jackpot);
              }}
              disabled={validations.length === 0}
            >
              <SelectTrigger className="w-[180px] glass-card">
                <SelectValue placeholder={validations.length === 0 ? "No validations" : "Select jackpot"} />
              </SelectTrigger>
              <SelectContent>
                {validations.map((j) => (
                  <SelectItem key={j.id} value={j.id}>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">{j.setUsed}</Badge>
                      <span>{j.jackpotId.replace(/ \(Set [A-G]\)/g, '')}</span>
                      <span className="text-muted-foreground">
                        ({j.correctPredictions}/{j.totalMatches} - {((j.correctPredictions / j.totalMatches) * 100).toFixed(0)}%)
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
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
                disabled={isExporting || !selectedJackpot || selectedJackpot.matches.length === 0}
                className="glass-card border-primary/30 hover:bg-primary/10"
              >
                {isExporting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Exporting...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4 mr-2" />
                    Export Selected
                  </>
                )}
              </Button>
              <Button
                onClick={handleExportAll}
                disabled={isExporting || validations.length === 0}
                className="btn-glow bg-primary text-primary-foreground"
              >
                {isExporting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Exporting...
                  </>
                ) : (
                  <>
                    <Database className="h-4 w-4 mr-2" />
                    Export All to Training
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      {selectedJackpot ? (
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
      ) : (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8 text-muted-foreground">
              {loading ? (
                <>
                  <Loader2 className="h-8 w-8 mx-auto mb-2 animate-spin" />
                  <p>Loading validation data...</p>
                </>
              ) : (
                <>
                  <Trophy className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No validation data available.</p>
                  <p className="text-sm mt-2">Save probability results with actual outcomes to see validation data.</p>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      )}

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
              {selectedJackpot && selectedJackpot.matches.length > 0 ? (
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
          {/* Aggregate Mode Toggle */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold mb-1">Analytics Scope</h3>
                  <p className="text-sm text-muted-foreground">
                    {aggregateMode === 'all' 
                      ? `Showing aggregated analytics across ALL ${validations.length} predictions` 
                      : 'Showing analytics for selected jackpot only'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant={aggregateMode === 'all' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setAggregateMode('all')}
                  >
                    All Predictions ({validations.length})
                  </Button>
                  <Button
                    variant={aggregateMode === 'selected' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setAggregateMode('selected')}
                    disabled={!selectedJackpot}
                  >
                    Selected Only
                  </Button>
                </div>
              </div>
              {analytics.aggregatedStats && aggregateMode === 'all' && (
                <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Predictions</p>
                    <p className="text-2xl font-bold">{analytics.aggregatedStats.totalPredictions}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total Matches</p>
                    <p className="text-2xl font-bold">{analytics.aggregatedStats.totalMatches}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Overall Accuracy</p>
                    <p className="text-2xl font-bold text-green-600">
                      {analytics.aggregatedStats.overallAccuracy.toFixed(1)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Avg Brier Score</p>
                    <p className="text-2xl font-bold">{analytics.aggregatedStats.avgBrierScore.toFixed(3)}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Outcome Distribution</CardTitle>
                <CardDescription>
                  {aggregateMode === 'all' 
                    ? 'Predicted vs actual across all predictions' 
                    : 'Predicted vs actual outcome frequencies'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {analytics.outcomeBreakdown.length > 0 ? (
                  <div className="h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={analytics.outcomeBreakdown}>
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
                ) : (
                  <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                    <p>No data available</p>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Confidence vs Accuracy</CardTitle>
                <CardDescription>How well calibrated are the predictions</CardDescription>
              </CardHeader>
              <CardContent>
                {analytics.confidenceAccuracy.length > 0 ? (
                  <div className="h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={analytics.confidenceAccuracy}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="confidence" className="text-xs" />
                        <YAxis tickFormatter={(v) => `${v}%`} className="text-xs" />
                        <Tooltip formatter={(v: number) => `${v}%`} />
                        <Bar dataKey="accuracy" name="Accuracy" fill="hsl(var(--chart-3))" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                    <p>No data available</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Set Performance Comparison</CardTitle>
              <CardDescription>Compare accuracy and Brier score across all sets (A-G)</CardDescription>
            </CardHeader>
            <CardContent>
              {analytics.setComparison && analytics.setComparison.length > 0 ? (
                <div className="h-[250px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={analytics.setComparison}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="set" className="text-xs" />
                      <YAxis yAxisId="left" tickFormatter={(v) => `${v}%`} className="text-xs" />
                      <YAxis yAxisId="right" orientation="right" className="text-xs" />
                      <Tooltip />
                      <Legend />
                      <Bar yAxisId="left" dataKey="accuracy" name="Accuracy %" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
                      <Line yAxisId="right" type="monotone" dataKey="brierScore" name="Brier Score" stroke="hsl(var(--chart-2))" strokeWidth={2} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : analytics.performanceTrend.length > 0 ? (
                <div className="h-[250px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={analytics.performanceTrend}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="week" className="text-xs" />
                      <YAxis yAxisId="left" tickFormatter={(v) => `${v}%`} className="text-xs" />
                      <YAxis yAxisId="right" orientation="right" domain={[0, 0.3]} className="text-xs" />
                      <Tooltip />
                      <Legend />
                      <Line yAxisId="left" type="monotone" dataKey="accuracy" name="Accuracy %" stroke="hsl(var(--chart-1))" strokeWidth={2} dot={{ r: 4 }} />
                      <Line yAxisId="right" type="monotone" dataKey="brierScore" name="Brier Score" stroke="hsl(var(--chart-2))" strokeWidth={2} dot={{ r: 4 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                  <p>No data available</p>
                </div>
              )}
            </CardContent>
          </Card>
          
          {/* Set Comparison Table */}
          {analytics.setComparison && analytics.setComparison.length > 1 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Set-by-Set Performance</CardTitle>
                <CardDescription>
                  {aggregateMode === 'all' 
                    ? 'Aggregated performance across all predictions, grouped by set' 
                    : 'Detailed comparison of all probability sets'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Set</TableHead>
                      {aggregateMode === 'all' && <TableHead className="text-right">Jackpots</TableHead>}
                      <TableHead className="text-right">Correct</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead className="text-right">Accuracy</TableHead>
                      <TableHead className="text-right">Brier Score</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {analytics.setComparison
                      .sort((a, b) => b.accuracy - a.accuracy)
                      .map((set) => (
                        <TableRow 
                          key={set.set}
                          className={set.set === selectedJackpot?.setUsed ? 'bg-primary/5' : ''}
                        >
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline">{set.set}</Badge>
                              {set.set === 'Set B' && (
                                <Badge variant="secondary" className="text-xs">Recommended</Badge>
                              )}
                            </div>
                          </TableCell>
                          {aggregateMode === 'all' && (
                            <TableCell className="text-right tabular-nums">{set.jackpotCount || 0}</TableCell>
                          )}
                          <TableCell className="text-right tabular-nums">{set.correct}</TableCell>
                          <TableCell className="text-right tabular-nums">{set.total}</TableCell>
                          <TableCell className="text-right">
                            <span className={`tabular-nums font-medium ${
                              set.accuracy >= 70 ? 'text-green-600' :
                              set.accuracy >= 60 ? 'text-yellow-600' :
                              'text-red-600'
                            }`}>
                              {set.accuracy.toFixed(1)}%
                            </span>
                          </TableCell>
                          <TableCell className="text-right tabular-nums">{set.brierScore.toFixed(3)}</TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">Validation History</CardTitle>
                  <CardDescription>
                    All validated jackpots with performance metrics per set
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Select
                    value={selectedJackpot?.setUsed || ''}
                    onValueChange={(setUsed) => {
                      if (setUsed === '') {
                        // Show all - default to Set B if available
                        const setBValidation = validations.find(v => v.setUsed === 'Set B');
                        setSelectedJackpot(setBValidation || validations[0] || null);
                      } else {
                        const validation = validations.find(v => v.setUsed === setUsed);
                        if (validation) setSelectedJackpot(validation);
                      }
                    }}
                    disabled={validations.length === 0}
                  >
                    <SelectTrigger className="w-[160px]">
                      <SelectValue placeholder="Filter by Set" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">All Sets</SelectItem>
                      {['A', 'B', 'C', 'D', 'E', 'F', 'G'].map(setId => (
                        <SelectItem key={setId} value={`Set ${setId}`}>
                          Set {setId} {setId === 'B' && '(Recommended)'}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {validations.length > 0 ? (
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
                      {validations
                        .sort((a, b) => {
                          // Sort by date (newest first), then by set (A-G)
                          const dateCompare = new Date(b.date).getTime() - new Date(a.date).getTime();
                          if (dateCompare !== 0) return dateCompare;
                          return a.setUsed.localeCompare(b.setUsed);
                        })
                        .map((v) => {
                          const accuracy = (v.correctPredictions / v.totalMatches) * 100;
                          const isRecommended = v.setUsed === 'Set B';
                          const isSelected = selectedJackpot?.id === v.id;
                          
                          return (
                            <TableRow 
                              key={v.id}
                              className={isSelected ? 'bg-primary/10' : ''}
                            >
                              <TableCell className="font-mono text-sm">
                                {v.jackpotId.replace(/ \(Set [A-G]\)/g, '')}
                              </TableCell>
                              <TableCell>{formatDate(v.date)}</TableCell>
                              <TableCell>
                                <div className="flex items-center gap-2">
                                  <Badge variant="outline">{v.setUsed}</Badge>
                                  {isRecommended && (
                                    <Badge variant="secondary" className="text-xs">Recommended</Badge>
                                  )}
                                </div>
                              </TableCell>
                              <TableCell className="text-right tabular-nums">
                                {v.correctPredictions}/{v.totalMatches}
                              </TableCell>
                              <TableCell className="text-right">
                                <span className={`tabular-nums font-medium ${
                                  accuracy >= 75 ? 'text-green-600' :
                                  accuracy >= 60 ? 'text-yellow-600' :
                                  'text-red-600'
                                }`}>
                                  {accuracy.toFixed(1)}%
                                </span>
                              </TableCell>
                              <TableCell className="text-right tabular-nums">
                                <span className={v.brierScore <= 0.20 ? 'text-green-600' : 'text-muted-foreground'}>
                                  {v.brierScore.toFixed(3)}
                                </span>
                              </TableCell>
                              <TableCell>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => setSelectedJackpot(v)}
                                  className={isSelected ? 'bg-primary/20' : ''}
                                >
                                  <Eye className="h-4 w-4 mr-1" />
                                  View
                                </Button>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                    </TableBody>
                  </Table>
                </ScrollArea>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No validation history available.</p>
                  <p className="text-sm mt-2">Save probability results with actual outcomes to see validation history.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
