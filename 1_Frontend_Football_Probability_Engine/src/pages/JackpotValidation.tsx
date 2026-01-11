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
  Loader2,
  RefreshCw,
  Zap
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageLayout } from '@/components/layouts/PageLayout';
import { ModernCard } from '@/components/ui/modern-card';
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
  leagueCode?: string;  // League code for analytics
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
      v.jackpotId.replace(/ \(Set [A-J]\)/g, '') === jackpot.jackpotId.replace(/ \(Set [A-J]\)/g, '')
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
  const setStats: Record<string, { 
    correct: number; 
    total: number; 
    brier: number; 
    count: number;
    hCorrect: number;
    hTotal: number;
    dCorrect: number;
    dTotal: number;
    aCorrect: number;
    aTotal: number;
  }> = {};
  
  validationsToUse.forEach(v => {
    const setKey = v.setUsed;
    if (!setStats[setKey]) {
      setStats[setKey] = { 
        correct: 0, 
        total: 0, 
        brier: 0, 
        count: 0,
        hCorrect: 0,
        hTotal: 0,
        dCorrect: 0,
        dTotal: 0,
        aCorrect: 0,
        aTotal: 0,
      };
    }
    setStats[setKey].correct += v.correctPredictions;
    setStats[setKey].total += v.totalMatches;
    setStats[setKey].brier += v.brierScore * v.totalMatches;
    setStats[setKey].count += 1;
    
    // Calculate H/D/A accuracy per set
    v.matches.forEach(match => {
      if (match.actualResult === 'H') {
        setStats[setKey].hTotal++;
        if (match.prediction === 'H') setStats[setKey].hCorrect++;
      } else if (match.actualResult === 'D') {
        setStats[setKey].dTotal++;
        if (match.prediction === 'D') setStats[setKey].dCorrect++;
      } else if (match.actualResult === 'A') {
        setStats[setKey].aTotal++;
        if (match.prediction === 'A') setStats[setKey].aCorrect++;
      }
    });
  });
  
  const setComparison = Object.entries(setStats).map(([set, stats]) => ({
    set,
    accuracy: stats.total > 0 ? (stats.correct / stats.total) * 100 : 0,
    brierScore: stats.total > 0 ? stats.brier / stats.total : 0,
    correct: stats.correct,
    total: stats.total,
    jackpotCount: stats.count,
    hAccuracy: stats.hTotal > 0 ? (stats.hCorrect / stats.hTotal) * 100 : 0,
    hCorrect: stats.hCorrect,
    hTotal: stats.hTotal,
    dAccuracy: stats.dTotal > 0 ? (stats.dCorrect / stats.dTotal) * 100 : 0,
    dCorrect: stats.dCorrect,
    dTotal: stats.dTotal,
    aAccuracy: stats.aTotal > 0 ? (stats.aCorrect / stats.aTotal) * 100 : 0,
    aCorrect: stats.aCorrect,
    aTotal: stats.aTotal,
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
  
  // Find best set for each outcome type (H/D/A)
  const bestSetForH = setComparison.length > 0 
    ? setComparison.reduce((best, current) => 
        current.hTotal > 0 && current.hAccuracy > (best.hAccuracy || 0) ? current : best
      , setComparison[0])
    : null;
  
  const bestSetForD = setComparison.length > 0 
    ? setComparison.reduce((best, current) => 
        current.dTotal > 0 && current.dAccuracy > (best.dAccuracy || 0) ? current : best
      , setComparison[0])
    : null;
  
  const bestSetForA = setComparison.length > 0 
    ? setComparison.reduce((best, current) => 
        current.aTotal > 0 && current.aAccuracy > (best.aAccuracy || 0) ? current : best
      , setComparison[0])
    : null;
  
  // Calculate league-specific performance per set
  const leagueSetStats: Record<string, Record<string, { correct: number; total: number; accuracy: number }>> = {};
  
  validationsToUse.forEach(validation => {
    validation.matches.forEach(match => {
      const league = match.leagueCode || 'Unknown';
      const set = validation.setUsed;
      
      if (!leagueSetStats[league]) {
        leagueSetStats[league] = {};
      }
      if (!leagueSetStats[league][set]) {
        leagueSetStats[league][set] = { correct: 0, total: 0, accuracy: 0 };
      }
      
      leagueSetStats[league][set].total++;
      if (match.correct) {
        leagueSetStats[league][set].correct++;
      }
    });
  });
  
  // Calculate accuracy for each league-set combination
  Object.keys(leagueSetStats).forEach(league => {
    Object.keys(leagueSetStats[league]).forEach(set => {
      const stats = leagueSetStats[league][set];
      stats.accuracy = stats.total > 0 ? (stats.correct / stats.total) * 100 : 0;
    });
  });
  
  // Find best set for each league
  const bestSetPerLeague: Record<string, { set: string; accuracy: number; correct: number; total: number }> = {};
  Object.keys(leagueSetStats).forEach(league => {
    const sets = leagueSetStats[league];
    const bestSet = Object.entries(sets).reduce((best, [set, stats]) => {
      if (stats.total > 0 && stats.accuracy > (best.accuracy || 0)) {
        return { set, ...stats };
      }
      return best;
    }, { set: '', accuracy: 0, correct: 0, total: 0 });
    
    if (bestSet.total > 0) {
      bestSetPerLeague[league] = bestSet;
    }
  });
  
  return {
    performanceTrend,
    outcomeBreakdown,
    confidenceAccuracy,
    setComparison,
    aggregatedStats,
    bestSetForH,
    bestSetForD,
    bestSetForA,
    bestSetPerLeague,
    leagueSetStats,
  };
};

// Generate detailed analytics report
const generateAnalyticsReport = (
  analytics: ReturnType<typeof calculateAnalytics>,
  validations: JackpotValidation[],
  aggregateMode: 'all' | 'selected'
): string => {
  const timestamp = new Date().toISOString();
  const reportLines: string[] = [];
  
  reportLines.push('='.repeat(80));
  reportLines.push('ANALYTICS REPORT - FOOTBALL PROBABILITY ENGINE');
  reportLines.push('='.repeat(80));
  reportLines.push(`Generated: ${new Date(timestamp).toLocaleString()}`);
  reportLines.push(`Scope: ${aggregateMode === 'all' ? 'All Predictions' : 'Selected Jackpot'}`);
  reportLines.push('');
  
  // Overall Statistics
  if (analytics.aggregatedStats) {
    reportLines.push('OVERALL STATISTICS');
    reportLines.push('-'.repeat(80));
    reportLines.push(`Total Predictions: ${analytics.aggregatedStats.totalPredictions}`);
    reportLines.push(`Total Matches: ${analytics.aggregatedStats.totalMatches}`);
    reportLines.push(`Overall Accuracy: ${analytics.aggregatedStats.overallAccuracy.toFixed(2)}%`);
    reportLines.push(`Average Brier Score: ${analytics.aggregatedStats.avgBrierScore.toFixed(3)}`);
    reportLines.push('');
  }
  
  // Best Sets for H/D/A
  reportLines.push('BEST SETS FOR OUTCOME PREDICTION');
  reportLines.push('-'.repeat(80));
  if (analytics.bestSetForH && analytics.bestSetForH.hTotal > 0) {
    reportLines.push(`Best for Home Wins: ${analytics.bestSetForH.set} - ${analytics.bestSetForH.hAccuracy.toFixed(2)}% (${analytics.bestSetForH.hCorrect}/${analytics.bestSetForH.hTotal})`);
  }
  if (analytics.bestSetForD && analytics.bestSetForD.dTotal > 0) {
    reportLines.push(`Best for Draws: ${analytics.bestSetForD.set} - ${analytics.bestSetForD.dAccuracy.toFixed(2)}% (${analytics.bestSetForD.dCorrect}/${analytics.bestSetForD.dTotal})`);
  }
  if (analytics.bestSetForA && analytics.bestSetForA.aTotal > 0) {
    reportLines.push(`Best for Away Wins: ${analytics.bestSetForA.set} - ${analytics.bestSetForA.aAccuracy.toFixed(2)}% (${analytics.bestSetForA.aCorrect}/${analytics.bestSetForA.aTotal})`);
  }
  reportLines.push('');
  
  // Best Set Per League
  if (analytics.bestSetPerLeague && Object.keys(analytics.bestSetPerLeague).length > 0) {
    reportLines.push('BEST SET PER LEAGUE');
    reportLines.push('-'.repeat(80));
    Object.entries(analytics.bestSetPerLeague)
      .sort(([, a], [, b]) => b.accuracy - a.accuracy)
      .forEach(([league, bestSet]) => {
        reportLines.push(`${league}: ${bestSet.set} - ${bestSet.accuracy.toFixed(2)}% (${bestSet.correct}/${bestSet.total})`);
      });
    reportLines.push('');
  }
  
  // Set-by-Set Performance
  if (analytics.setComparison && analytics.setComparison.length > 0) {
    reportLines.push('SET-BY-SET PERFORMANCE');
    reportLines.push('-'.repeat(80));
    reportLines.push('Set | Accuracy | Brier Score | H Accuracy | D Accuracy | A Accuracy | Total');
    reportLines.push('-'.repeat(80));
    
    analytics.setComparison
      .sort((a, b) => b.accuracy - a.accuracy)
      .forEach(set => {
        const hAcc = set.hTotal > 0 ? `${set.hAccuracy.toFixed(1)}%` : 'N/A';
        const dAcc = set.dTotal > 0 ? `${set.dAccuracy.toFixed(1)}%` : 'N/A';
        const aAcc = set.aTotal > 0 ? `${set.aAccuracy.toFixed(1)}%` : 'N/A';
        reportLines.push(
          `${set.set.padEnd(6)} | ${set.accuracy.toFixed(1)}%`.padEnd(15) + 
          ` | ${set.brierScore.toFixed(3)}`.padEnd(15) +
          ` | ${hAcc.padEnd(12)} | ${dAcc.padEnd(12)} | ${aAcc.padEnd(12)} | ${set.total}`
        );
      });
    reportLines.push('');
  }
  
  // Outcome Breakdown
  if (analytics.outcomeBreakdown && analytics.outcomeBreakdown.length > 0) {
    reportLines.push('OUTCOME DISTRIBUTION');
    reportLines.push('-'.repeat(80));
    analytics.outcomeBreakdown.forEach(outcome => {
      reportLines.push(`${outcome.name}:`);
      reportLines.push(`  Predicted: ${outcome.predicted.toFixed(2)}%`);
      reportLines.push(`  Actual: ${outcome.actual.toFixed(2)}%`);
      reportLines.push(`  Difference: ${(outcome.predicted - outcome.actual).toFixed(2)}%`);
    });
    reportLines.push('');
  }
  
  // Confidence vs Accuracy
  if (analytics.confidenceAccuracy && analytics.confidenceAccuracy.length > 0) {
    reportLines.push('CONFIDENCE VS ACCURACY');
    reportLines.push('-'.repeat(80));
    analytics.confidenceAccuracy.forEach(bucket => {
      reportLines.push(`${bucket.confidence}: ${bucket.accuracy.toFixed(2)}% accuracy (${bucket.count} matches)`);
    });
    reportLines.push('');
  }
  
  // Detailed Set Performance
  if (analytics.setComparison && analytics.setComparison.length > 0) {
    reportLines.push('DETAILED SET PERFORMANCE');
    reportLines.push('-'.repeat(80));
    analytics.setComparison
      .sort((a, b) => b.accuracy - a.accuracy)
      .forEach(set => {
        reportLines.push(`${set.set}:`);
        reportLines.push(`  Overall: ${set.correct}/${set.total} (${set.accuracy.toFixed(2)}%)`);
        if (set.hTotal > 0) {
          reportLines.push(`  Home Wins: ${set.hCorrect}/${set.hTotal} (${set.hAccuracy.toFixed(2)}%)`);
        }
        if (set.dTotal > 0) {
          reportLines.push(`  Draws: ${set.dCorrect}/${set.dTotal} (${set.dAccuracy.toFixed(2)}%)`);
        }
        if (set.aTotal > 0) {
          reportLines.push(`  Away Wins: ${set.aCorrect}/${set.aTotal} (${set.aAccuracy.toFixed(2)}%)`);
        }
        reportLines.push(`  Brier Score: ${set.brierScore.toFixed(3)}`);
        if (aggregateMode === 'all') {
          reportLines.push(`  Jackpots: ${set.jackpotCount}`);
        }
        reportLines.push('');
      });
  }
  
  reportLines.push('='.repeat(80));
  reportLines.push('End of Report');
  reportLines.push('='.repeat(80));
  
  return reportLines.join('\n');
};

// Download report as file
const downloadReport = (reportContent: string) => {
  const blob = new Blob([reportContent], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `analytics-report-${new Date().toISOString().split('T')[0]}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
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
  const [selectedJackpotId, setSelectedJackpotId] = useState<string>('');
  const [selectedSet, setSelectedSet] = useState<string>('');
  const [viewMode, setViewMode] = useState<'table' | 'visual'>('table');
  const [isExporting, setIsExporting] = useState(false);
  const [isRetraining, setIsRetraining] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadedProbabilities, setLoadedProbabilities] = useState<Record<string, any>>({});
  const [aggregateMode, setAggregateMode] = useState<'all' | 'selected'>('all');
  const [exportedValidations, setExportedValidations] = useState<Set<string>>(new Set());
  const [hasRetrained, setHasRetrained] = useState(false);
  const { toast } = useToast();

  // Get unique jackpot IDs and sets from validations
  const uniqueJackpotIds = useMemo(() => {
    const ids = new Set<string>();
    validations.forEach(v => {
      // Remove " (Set X)" pattern where X can be A-J
      const baseId = v.jackpotId.replace(/ \(Set [A-J]\)/g, '');
      ids.add(baseId);
    });
    return Array.from(ids).sort();
  }, [validations]);

  const availableSets = useMemo(() => {
    const sets = new Set<string>();
    validations.forEach(v => {
      sets.add(v.setUsed);
    });
    return Array.from(sets).sort();
  }, [validations]);

  // Filter validations based on selected jackpot and set
  const filteredValidations = useMemo(() => {
    return validations.filter(v => {
      // Remove " (Set X)" pattern where X can be A-J
      const baseId = v.jackpotId.replace(/ \(Set [A-J]\)/g, '');
      const matchesJackpot = !selectedJackpotId || baseId === selectedJackpotId;
      const matchesSet = !selectedSet || v.setUsed === selectedSet;
      return matchesJackpot && matchesSet;
    });
  }, [validations, selectedJackpotId, selectedSet]);

  // Update selectedJackpot when filters change
  useEffect(() => {
    if (filteredValidations.length > 0) {
      // Prefer Set B if available, otherwise use first
      const setBValidation = filteredValidations.find(v => v.setUsed === 'Set B');
      setSelectedJackpot(setBValidation || filteredValidations[0]);
    } else {
      setSelectedJackpot(null);
    }
  }, [filteredValidations]);

  /**
   * Load validation data from saved_probability_results table
   * 
   * Data Flow:
   * 1. Fetches all saved_probability_results with actualResults from database
   * 2. For each saved result, loads probability predictions for the jackpot
   * 3. Compares predictions (from selections or highest probability) with actual results
   * 4. Calculates accuracy, Brier score, and creates validation objects
   * 5. Each validation represents one jackpot + one set (A-J) combination
   * 
   * Note: The validation_results table is populated when exporting to training,
   * but the validation page displays data computed from saved_probability_results
   */
  useEffect(() => {
    const loadValidations = async () => {
      try {
        setLoading(true);
        console.log('=== VALIDATION PAGE: Starting to load validations ===');
        console.log('Jackpot ID from URL:', jackpotId);
        
        const validationList: JackpotValidation[] = [];
        const processedJackpots = new Set<string>();
        
        // Load ALL saved results across all jackpots
        console.log('Step 1: Fetching all saved results...');
        const allSavedResponse = await apiClient.getAllSavedResults(500);
        console.log('Step 1 Response:', {
          success: allSavedResponse.success,
          hasData: !!allSavedResponse.data,
          resultsCount: allSavedResponse.data?.results?.length || 0,
          rawResponse: allSavedResponse
        });
        
        const allSavedResults = allSavedResponse.success && allSavedResponse.data?.results 
          ? allSavedResponse.data.results.filter((r: any) => r.actualResults && Object.keys(r.actualResults).length > 0)
          : [];
        
        console.log(`Step 2: Filtered to ${allSavedResults.length} saved results with actual outcomes`);
        console.log('Step 2 Details:', allSavedResults.map((r: any) => ({
          id: r.id,
          jackpotId: r.jackpotId,
          hasActualResults: !!r.actualResults,
          actualResultsCount: r.actualResults ? Object.keys(r.actualResults).length : 0,
          hasSelections: !!r.selections,
          selectionsKeys: r.selections ? Object.keys(r.selections) : [],
          totalFixtures: r.totalFixtures
        })));
        
        // Process each saved result
        console.log(`Step 3: Processing ${allSavedResults.length} saved results...`);
        for (let i = 0; i < allSavedResults.length; i++) {
          const savedResult = allSavedResults[i];
          const resultJackpotId = savedResult.jackpotId;
          
          console.log(`\n--- Processing saved result ${i + 1}/${allSavedResults.length} ---`);
          console.log('Saved Result:', {
            id: savedResult.id,
            jackpotId: resultJackpotId,
            hasActualResults: !!savedResult.actualResults,
            actualResultsKeys: savedResult.actualResults ? Object.keys(savedResult.actualResults) : [],
            actualResultsSample: savedResult.actualResults ? Object.entries(savedResult.actualResults).slice(0, 5) : [],
            actualResultsType: savedResult.actualResults ? typeof savedResult.actualResults : 'none',
            hasSelections: !!savedResult.selections,
            selectionsKeys: savedResult.selections ? Object.keys(savedResult.selections) : [],
            totalFixtures: savedResult.totalFixtures
          });
          
          if (!resultJackpotId) {
            console.warn(`⚠️ Skipping saved result ${savedResult.id}: No jackpotId`);
            continue;
          }
          
          // Load probabilities for this jackpot (cache to avoid duplicate loads)
          let probData: any = null;
          if (!processedJackpots.has(resultJackpotId)) {
            console.log(`  Loading probabilities for jackpot ${resultJackpotId}...`);
            try {
              const probResponse = await apiClient.getProbabilities(resultJackpotId);
              console.log(`  Probability response:`, {
                success: (probResponse as any).success,
                hasData: !!(probResponse as any).data,
                dataKeys: (probResponse as any).data ? Object.keys((probResponse as any).data) : [],
                fullResponse: probResponse
              });
              
              // Handle ApiResponse format (wrapped in {success, data, message})
              if ((probResponse as any).success && (probResponse as any).data) {
                probData = (probResponse as any).data;
                console.log(`  Extracted data from ApiResponse:`, {
                  hasProbabilitySets: !!probData.probabilitySets,
                  setsKeys: probData.probabilitySets ? Object.keys(probData.probabilitySets) : [],
                  hasFixtures: !!probData.fixtures,
                  fixturesCount: probData.fixtures?.length || 0
                });
              } else {
                // Fallback: assume response is direct data (backward compatibility)
                probData = probResponse as any;
                console.log(`  Using response as direct data (backward compatibility)`);
              }
              
              if (probData && probData.probabilitySets && probData.fixtures) {
                console.log(`  ✓ Loaded probabilities for ${resultJackpotId}:`, {
                  setsCount: Object.keys(probData.probabilitySets).length,
                  setsKeys: Object.keys(probData.probabilitySets),
                  fixturesCount: probData.fixtures?.length || 0
                });
                processedJackpots.add(resultJackpotId);
                setLoadedProbabilities(prev => ({ ...prev, [resultJackpotId]: probData.probabilitySets }));
              } else {
                console.warn(`  ⚠️ Missing data in probability response:`, {
                  hasProbData: !!probData,
                  hasProbabilitySets: !!probData?.probabilitySets,
                  hasFixtures: !!probData?.fixtures
                });
              }
            } catch (err) {
              console.error(`  ❌ Failed to load probabilities for jackpot ${resultJackpotId}:`, err);
              continue;
            }
          } else {
            console.log(`  Using cached probabilities for ${resultJackpotId}`);
            // Use cached probabilities
            probData = {
              probabilitySets: loadedProbabilities[resultJackpotId],
              fixtures: null // Will need to reconstruct or load separately
            };
          }
          
          if (!probData || !probData.probabilitySets) {
            console.warn(`  ⚠️ Skipping: No probability data for jackpot ${resultJackpotId}`);
            continue;
          }
          
          console.log(`  Processing probability sets:`, {
            setsAvailable: Object.keys(probData.probabilitySets).length,
            setsKeys: Object.keys(probData.probabilitySets)
          });
          
          // Get fixtures - try to load if not cached
          let fixtures = probData.fixtures || [];
          console.log(`  Fixtures:`, {
            fromProbData: probData.fixtures?.length || 0,
            totalFixtures: savedResult.totalFixtures,
            actualResultsKeys: savedResult.actualResults ? Object.keys(savedResult.actualResults).length : 0
          });
          
          if (fixtures.length === 0 && savedResult.totalFixtures) {
            // Try to reconstruct fixture list from saved result
            const fixtureIds = Object.keys(savedResult.actualResults || {});
            fixtures = fixtureIds.map((id, idx) => ({ id, homeTeam: '', awayTeam: '' }));
            console.log(`  Reconstructed ${fixtures.length} fixtures from actualResults`);
          }
          
          // Validate EACH set separately (A-J)
          // Get all available sets from probabilitySets and selections
          const availableSets = new Set<string>();
          if (probData.probabilitySets) {
            Object.keys(probData.probabilitySets).forEach(key => availableSets.add(key));
          }
          if (savedResult.selections) {
            Object.keys(savedResult.selections).forEach(key => availableSets.add(key));
          }
          const setKeys = Array.from(availableSets).sort();
          console.log(`  Processing ${setKeys.length} sets:`, setKeys);
          
          setKeys.forEach(setId => {
            const hasSelections = savedResult.selections && savedResult.selections[setId];
            const hasProbabilities = probData.probabilitySets[setId];
            
            console.log(`    Set ${setId}:`, {
              hasSelections,
              hasProbabilities,
              selectionsCount: hasSelections ? Object.keys(savedResult.selections[setId]).length : 0,
              probabilitiesCount: hasProbabilities ? probData.probabilitySets[setId].length : 0
            });
            
            if (!hasSelections && !hasProbabilities) {
              console.log(`    ⚠️ Skipping Set ${setId}: No selections or probabilities`);
              return; // Skip sets with no data
            }
            
            const matches: JackpotMatch[] = [];
            let correctCount = 0;
            let totalBrier = 0;
            
            console.log(`    Processing ${fixtures.length} fixtures for Set ${setId}...`);
            
            fixtures.forEach((fixture: any, idx: number) => {
              const fixtureId = fixture.id || String(idx + 1);
              // actualResults uses match numbers (1-indexed) as keys from CSV import, not fixture IDs
              // Priority: match number (1-indexed) > fixture ID > index (0-indexed) > by position
              const matchNumber = String(idx + 1); // 1-indexed match number (from CSV: "1", "2", "3", ...)
              
              // Debug: Log first match to see structure
              if (idx === 0) {
                console.log(`      DEBUG First match:`, {
                  fixtureId,
                  matchNumber,
                  actualResultsKeys: savedResult.actualResults ? Object.keys(savedResult.actualResults) : 'none',
                  actualResultsSample: savedResult.actualResults ? Object.entries(savedResult.actualResults).slice(0, 5) : 'none',
                  lookupMatchNumber: savedResult.actualResults?.[matchNumber],
                  lookupFixtureId: savedResult.actualResults?.[fixtureId]
                });
              }
              
              const actualResultStr = savedResult.actualResults[matchNumber] || 
                                     savedResult.actualResults[fixtureId] ||
                                     savedResult.actualResults[String(idx)] ||
                                     (savedResult.actualResults && Object.values(savedResult.actualResults)[idx] as string);
              
              if (!actualResultStr) {
                console.log(`      Match ${idx + 1} (fixtureId: ${fixtureId}, matchNumber: ${matchNumber}): ⚠️ No actual result found.`, {
                  availableKeys: savedResult.actualResults ? Object.keys(savedResult.actualResults) : 'none',
                  actualResultsSample: savedResult.actualResults ? Object.entries(savedResult.actualResults).slice(0, 3) : 'none'
                });
                return;
              }
              
              console.log(`      Match ${idx + 1} (fixtureId: ${fixtureId}, matchNumber: ${matchNumber}): ✓ Found actual result: ${actualResultStr}`);
              
              const actualResult = convertResult(actualResultStr as '1' | 'X' | '2');
              
              // Get probabilities for this set
              const setProbs = probData.probabilitySets[setId];
              if (!setProbs || !setProbs[idx]) {
                console.log(`      Match ${idx + 1} (${fixtureId}): ⚠️ No probability data at index ${idx}, skipping`);
                return;
              }
              
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
                leagueCode: fixture.leagueCode || undefined,
              });
            });
            
            console.log(`    Set ${setId} Summary:`, {
              matchesProcessed: matches.length,
              correctCount,
              totalBrier,
              brierScore: matches.length > 0 ? totalBrier / matches.length : 0
            });
            
            if (matches.length > 0) {
              const brierScore = totalBrier / matches.length;
              const validation = {
                id: `${savedResult.id}-${setId}`,
                jackpotId: `${resultJackpotId} (Set ${setId})`,
                date: savedResult.createdAt || new Date().toISOString(),
                matches,
                setUsed: `Set ${setId}`,
                correctPredictions: correctCount,
                totalMatches: matches.length,
                brierScore,
              };
              validationList.push(validation);
              console.log(`    ✓ Created validation for Set ${setId}:`, {
                id: validation.id,
                matches: validation.totalMatches,
                correct: validation.correctPredictions,
                brierScore: validation.brierScore
              });
            } else {
              console.log(`    ⚠️ Set ${setId}: No matches processed, skipping validation`);
            }
          });
        }
        
        console.log(`\n=== VALIDATION PAGE: Summary ===`);
        console.log(`Total saved results processed: ${allSavedResults.length}`);
        console.log(`Total validations created: ${validationList.length}`);
        console.log(`Validations by jackpot:`, validationList.reduce((acc: any, v) => {
          const baseId = v.jackpotId.replace(/ \(Set [A-J]\)/g, '');
          if (!acc[baseId]) acc[baseId] = [];
          acc[baseId].push(v.setUsed);
          return acc;
        }, {}));
        
        if (validationList.length === 0) {
          console.warn('⚠️ NO VALIDATIONS CREATED! Possible reasons:');
          console.warn('  1. Saved results have no actualResults');
          console.warn('  2. Probabilities not loaded successfully');
          console.warn('  3. Fixtures count mismatch');
          console.warn('  4. Sets have no selections or probabilities');
        }
        
        setValidations(validationList);
        if (validationList.length > 0) {
          // Set initial dropdown selections
          if (jackpotId) {
            // If jackpotId specified in URL, select it
            setSelectedJackpotId(jackpotId);
            const jackpotValidations = validationList.filter(v => 
              v.jackpotId.replace(/ \(Set [A-J]\)/g, '') === jackpotId
            );
            if (jackpotValidations.length > 0) {
              const setBValidation = jackpotValidations.find(v => v.setUsed === 'Set B');
              if (setBValidation) {
                setSelectedSet('Set B');
                setSelectedJackpot(setBValidation);
            } else {
                setSelectedSet(jackpotValidations[0].setUsed);
                setSelectedJackpot(jackpotValidations[0]);
              }
            } else {
              // Fallback: use first validation
              const setBValidation = validationList.find(v => v.setUsed === 'Set B');
              if (setBValidation) {
                setSelectedJackpotId(setBValidation.jackpotId.replace(/ \(Set [A-J]\)/g, ''));
                setSelectedSet('Set B');
                setSelectedJackpot(setBValidation);
              } else {
                const first = validationList[0];
                setSelectedJackpotId(first.jackpotId.replace(/ \(Set [A-J]\)/g, ''));
                setSelectedSet(first.setUsed);
                setSelectedJackpot(first);
              }
            }
          } else {
            // Default to Set B (recommended) if available, otherwise use first validation
            const setBValidation = validationList.find(v => v.setUsed === 'Set B');
            if (setBValidation) {
              setSelectedJackpotId(setBValidation.jackpotId.replace(/ \(Set [A-J]\)/g, ''));
              setSelectedSet('Set B');
              setSelectedJackpot(setBValidation);
            } else {
              const first = validationList[0];
              setSelectedJackpotId(first.jackpotId.replace(/ \(Set [A-J]\)/g, ''));
              setSelectedSet(first.setUsed);
              setSelectedJackpot(first);
            }
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

  // Debug: Log when selectedJackpot changes
  useEffect(() => {
    if (selectedJackpot) {
      console.log('Selected jackpot changed:', {
        id: selectedJackpot.id,
        jackpotId: selectedJackpot.jackpotId,
        setUsed: selectedJackpot.setUsed,
        matchesCount: selectedJackpot.matches.length,
        matches: selectedJackpot.matches.slice(0, 3).map(m => ({
          homeTeam: m.homeTeam,
          awayTeam: m.awayTeam,
          prediction: m.prediction,
          actual: m.actualResult
        }))
      });
    }
  }, [selectedJackpot]);

  const handleExportToTraining = async () => {
    if (!selectedJackpot) return;
    
    setIsExporting(true);
    try {
      // Export selected validation to training
      const response = await apiClient.exportValidationToTraining([selectedJackpot.id]);
      
      if (response.success) {
        // Mark as exported
        setExportedValidations(prev => new Set(prev).add(selectedJackpot.id));
        
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
        const autoRetrained = response.data?.auto_retrained;
        const totalValidationMatches = response.data?.total_validation_matches || 0;
        
        // Mark all as exported
        setExportedValidations(prev => {
          const newSet = new Set(prev);
          validationIds.forEach(id => newSet.add(id));
          return newSet;
        });
        
        // Mark as retrained if auto-retrained
        if (autoRetrained) {
          setHasRetrained(true);
        }
        
        toast({
          title: 'Success',
          description: `All validation data exported. ${response.data?.exported_count || validations.length} validations with ${totalMatches} matches added to training.${autoRetrained ? ` Calibration model auto-retrained using ${response.data?.auto_retrain_result?.matchCount || 0} validation matches!` : ''}`,
        });
        
        // Show info about retraining if not auto-retrained
        if (!autoRetrained && totalValidationMatches < 50) {
          toast({
            title: 'Info',
            description: `Retrain calibration model manually when you have 50+ validation matches (currently: ${totalValidationMatches})`,
            variant: 'default',
          });
        }
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

  const handleRetrainCalibration = async () => {
    setIsRetraining(true);
    try {
      // First, check how many validation matches are available
      // We'll use a lower threshold if needed, but warn the user
      const response = await apiClient.retrainCalibrationFromValidation({
        use_all_validation: true,
        min_validation_matches: 10  // Lower threshold to allow training with available data
      });
      
      if (response.success) {
        const matchCount = response.data?.matchCount || 0;
        const warning = matchCount < 50 
          ? ` Warning: Training with only ${matchCount} matches (recommended: 50+). Results may be less reliable.`
          : '';
        
        // Mark as retrained
        setHasRetrained(true);
        
        toast({
          title: 'Success',
          description: `Calibration model retrained successfully! Using ${matchCount} validation matches. New model version: ${response.data?.version || 'N/A'}.${warning}`,
        });
        
        // Refresh page data after retraining
        setTimeout(() => {
          window.location.reload();
        }, 2000);
      } else {
        throw new Error(response.message || 'Retraining failed');
      }
    } catch (err: any) {
      console.error('Retraining error:', err);
      const errorMsg = err.message || 'Unknown error';
      
      // Provide helpful error message
      let userFriendlyMsg = errorMsg;
      if (errorMsg.includes('Insufficient validation matches')) {
        const matchCount = errorMsg.match(/(\d+)\s+\(minimum:/)?.[1];
        const minRequired = errorMsg.match(/minimum:\s+(\d+)/)?.[1];
        if (matchCount && minRequired) {
          userFriendlyMsg = `You have ${matchCount} validation matches, but ${minRequired} are required. Export more validation results or the system will use available data with a lower threshold.`;
        }
      }
      
      toast({
        title: 'Error',
        description: 'Failed to retrain: ' + userFriendlyMsg,
        variant: 'destructive',
      });
    } finally {
      setIsRetraining(false);
    }
  };

  return (
    <PageLayout
      title="Jackpot Validation"
      description="Validate predictions against actual results"
      icon={<Trophy className="h-6 w-6" />}
    >
      {/* Data Source Info & Workflow Guide */}
      <div className="mb-4 space-y-3">
        <div className="p-3 rounded-lg bg-muted/50 border border-muted">
          <p className="text-xs text-muted-foreground">
            <strong>Data Source:</strong> Validation data is loaded from <code className="px-1 py-0.5 bg-background rounded">saved_probability_results</code> table. 
            Each validation combines actual results with probability predictions to calculate accuracy and Brier scores.
            {validations.length > 0 && (
              <span className="ml-2 text-primary font-medium">
                {validations.length} validation{validations.length !== 1 ? 's' : ''} loaded
              </span>
            )}
          </p>
        </div>
        
        {/* Workflow Guide */}
        <div className="p-4 rounded-lg bg-gradient-to-r from-primary/10 to-accent/10 border border-primary/20">
          <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <ArrowRight className="h-4 w-4" />
            Next Steps After Validation
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div className="p-2 rounded bg-background/50">
              <div className="font-medium text-primary mb-1">1. Export to Training</div>
              <p className="text-muted-foreground">
                Click "Export All to Training" to send validated predictions to the calibration model. 
                This populates the <code className="px-1 py-0.5 bg-background rounded text-xs">validation_results</code> table.
              </p>
            </div>
            <div className="p-2 rounded bg-background/50">
              <div className="font-medium text-accent mb-1">2. Retrain Calibration</div>
              <p className="text-muted-foreground">
                Click <strong>"Retrain Calibration Model"</strong> button above to automatically improve model accuracy using your validation results. 
                System auto-retrains when 50+ matches are exported, or retrain manually anytime.
              </p>
            </div>
            <div className="p-2 rounded bg-background/50">
              <div className="font-medium text-chart-1 mb-1">3. Backtesting</div>
              <p className="text-muted-foreground">
                After recalibration, use backtesting to evaluate model performance on historical data. 
                Compare metrics before/after calibration.
              </p>
            </div>
            <div className="p-2 rounded bg-background/50">
              <div className="font-medium text-chart-2 mb-1">4. Production</div>
              <p className="text-muted-foreground">
                Once validated and recalibrated, deploy the improved model for live predictions. 
                Monitor performance in the Dashboard.
              </p>
            </div>
          </div>
        </div>
      </div>

        {/* Two Separate Dropdowns: Jackpot and Set */}
        <div className="flex items-center gap-3 animate-slide-in-right flex-wrap">
          {loading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm text-muted-foreground">Loading...</span>
            </div>
          ) : (
            <>
              {/* Jackpot Dropdown */}
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-muted-foreground whitespace-nowrap">
                  Jackpot:
                </label>
            <Select
                  value={selectedJackpotId || '__all__'}
              onValueChange={(v) => {
                    setSelectedJackpotId(v === '__all__' ? '' : v);
                    // Reset set selection when jackpot changes
                    setSelectedSet('');
              }}
              disabled={validations.length === 0}
            >
                  <SelectTrigger className="w-[280px] glass-card min-w-[280px]">
                    <SelectValue placeholder={validations.length === 0 ? "No jackpots" : "All Jackpots"} />
              </SelectTrigger>
                  <SelectContent className="max-h-[300px]">
                    <SelectItem value="__all__" className="font-semibold">
                      <div className="flex items-center gap-2 py-1">
                        <Trophy className="h-4 w-4 text-primary" />
                        <span>All Jackpots ({uniqueJackpotIds.length})</span>
                      </div>
                    </SelectItem>
                    <div className="border-t my-1" />
                    {uniqueJackpotIds.map((id) => {
                      const jackpotValidations = validations.filter(v => 
                        v.jackpotId.replace(/ \(Set [A-J]\)/g, '') === id
                      );
                      const totalMatches = jackpotValidations.reduce((sum, v) => sum + v.totalMatches, 0);
                      const totalCorrect = jackpotValidations.reduce((sum, v) => sum + v.correctPredictions, 0);
                      const avgAccuracy = totalMatches > 0 ? ((totalCorrect / totalMatches) * 100).toFixed(1) : '0';
                      
                      return (
                        <SelectItem key={id} value={id}>
                          <div className="flex items-center gap-2 py-1 w-full">
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium truncate">{id}</div>
                              <div className="text-xs text-muted-foreground">
                                {jackpotValidations.length} set{jackpotValidations.length !== 1 ? 's' : ''} • {totalCorrect}/{totalMatches} correct ({avgAccuracy}%)
                              </div>
                            </div>
                          </div>
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>
              </div>

              {/* Set Dropdown */}
                    <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-muted-foreground whitespace-nowrap">
                  Set:
                </label>
                <Select
                  value={selectedSet || '__all__'}
                  onValueChange={(v) => {
                    setSelectedSet(v === '__all__' ? '' : v);
                  }}
                  disabled={validations.length === 0}
                >
                  <SelectTrigger className="w-[200px] glass-card min-w-[200px]">
                    <SelectValue placeholder={validations.length === 0 ? "No sets" : "All Sets"} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__" className="font-semibold">
                      <div className="flex items-center gap-2 py-1">
                        <span>All Sets ({availableSets.length})</span>
                    </div>
                  </SelectItem>
                    <div className="border-t my-1" />
                    {availableSets.map((set) => {
                      const setValidations = validations.filter(v => v.setUsed === set);
                      const totalMatches = setValidations.reduce((sum, v) => sum + v.totalMatches, 0);
                      const totalCorrect = setValidations.reduce((sum, v) => sum + v.correctPredictions, 0);
                      const avgAccuracy = totalMatches > 0 ? ((totalCorrect / totalMatches) * 100).toFixed(1) : '0';
                      const isRecommended = set === 'Set B';
                      
                      return (
                        <SelectItem key={set} value={set}>
                          <div className="flex items-center gap-2 py-1 w-full">
                            <Badge 
                              variant={isRecommended ? 'default' : 'outline'} 
                              className="text-xs min-w-[60px] justify-center"
                            >
                              {set}
                            </Badge>
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium">
                                {set} {isRecommended && <span className="text-xs text-muted-foreground">(Recommended)</span>}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {totalCorrect}/{totalMatches} ({avgAccuracy}%)
                              </div>
                            </div>
                          </div>
                        </SelectItem>
                      );
                    })}
              </SelectContent>
            </Select>
              </div>

              {/* Show filtered count */}
              {filteredValidations.length > 0 && (
                <div className="text-sm text-muted-foreground">
                  Showing {filteredValidations.length} validation{filteredValidations.length !== 1 ? 's' : ''}
                </div>
              )}
            </>
          )}
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
            <div className="flex items-center gap-2 flex-wrap">
              <Button
                variant="outline"
                onClick={handleExportToTraining}
                disabled={
                  isExporting || 
                  !selectedJackpot || 
                  selectedJackpot.matches.length === 0 ||
                  exportedValidations.has(selectedJackpot.id)
                }
                className="glass-card border-primary/30 hover:bg-primary/10"
                title={exportedValidations.has(selectedJackpot?.id || '') ? 'Already exported' : ''}
              >
                {isExporting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Exporting...
                  </>
                ) : exportedValidations.has(selectedJackpot?.id || '') ? (
                  <>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Already Exported
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
                disabled={
                  isExporting || 
                  validations.length === 0 ||
                  validations.every(v => exportedValidations.has(v.id))
                }
                className="btn-glow bg-primary text-primary-foreground"
                title={validations.every(v => exportedValidations.has(v.id)) ? 'All validations already exported' : ''}
              >
                {isExporting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Exporting...
                  </>
                ) : validations.every(v => exportedValidations.has(v.id)) ? (
                  <>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    All Exported
                  </>
                ) : (
                  <>
                    <Database className="h-4 w-4 mr-2" />
                    Export All to Training
                  </>
                )}
              </Button>
              <Button
                onClick={handleRetrainCalibration}
                disabled={isRetraining || isExporting || hasRetrained}
                variant="outline"
                className="glass-card border-accent/30 hover:bg-accent/10 text-accent"
                title={hasRetrained ? 'Already retrained' : ''}
              >
                {isRetraining ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Retraining...
                  </>
                ) : hasRetrained ? (
                  <>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Already Retrained
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retrain Calibration Model
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Overall Summary Cards - All Jackpots */}
      {validations.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          {(() => {
            const totalMatches = validations.reduce((sum, v) => sum + v.totalMatches, 0);
            const totalCorrect = validations.reduce((sum, v) => sum + v.correctPredictions, 0);
            const avgAccuracy = totalMatches > 0 ? (totalCorrect / totalMatches) * 100 : 0;
            const avgBrier = validations.reduce((sum, v) => sum + v.brierScore, 0) / validations.length;
            
            // Find best set across all jackpots
            const setStats = validations.reduce((acc: any, v) => {
              const set = v.setUsed;
              if (!acc[set]) {
                acc[set] = { matches: 0, correct: 0, brier: 0, count: 0 };
              }
              acc[set].matches += v.totalMatches;
              acc[set].correct += v.correctPredictions;
              acc[set].brier += v.brierScore;
              acc[set].count += 1;
              return acc;
            }, {});
            
            const bestSet = Object.entries(setStats).reduce((best: any, [set, stats]: [string, any]) => {
              const accuracy = stats.matches > 0 ? (stats.correct / stats.matches) * 100 : 0;
              const avgBrier = stats.count > 0 ? stats.brier / stats.count : Infinity;
              if (!best || accuracy > best.accuracy || (accuracy === best.accuracy && avgBrier < best.brier)) {
                return { set, accuracy, brier: avgBrier, correct: stats.correct, matches: stats.matches };
              }
              return best;
            }, null);
            
            // Find best jackpot performance
            const jackpotStats = validations.reduce((acc: any, v) => {
              const baseId = v.jackpotId.replace(/ \(Set [A-J]\)/g, '');
              if (!acc[baseId]) {
                acc[baseId] = { matches: 0, correct: 0, sets: new Set() };
              }
              acc[baseId].matches += v.totalMatches;
              acc[baseId].correct += v.correctPredictions;
              acc[baseId].sets.add(v.setUsed);
              return acc;
            }, {});
            
            const bestJackpot = Object.entries(jackpotStats).reduce((best: any, [id, stats]: [string, any]) => {
              const accuracy = stats.matches > 0 ? (stats.correct / stats.matches) * 100 : 0;
              if (!best || accuracy > best.accuracy || (accuracy === best.accuracy && stats.correct > best.correct)) {
                return { id, accuracy, correct: stats.correct, matches: stats.matches, sets: Array.from(stats.sets) };
              }
              return best;
            }, null);
            
            return (
              <>
                <Card className="glass-card-elevated border-primary/20">
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">Overall Accuracy</p>
                        <p className="text-2xl font-bold tabular-nums">{avgAccuracy.toFixed(1)}%</p>
                      </div>
                      <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                        <Target className="h-6 w-6 text-primary" />
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      {totalCorrect}/{totalMatches} correct across {validations.length} validation{validations.length !== 1 ? 's' : ''}
                    </p>
                  </CardContent>
                </Card>

                <Card className="glass-card-elevated border-chart-2/20">
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">Average Brier Score</p>
                        <p className="text-2xl font-bold tabular-nums">{avgBrier.toFixed(3)}</p>
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

                <Card className="glass-card-elevated border-accent/20">
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">Best Set</p>
                        <p className="text-2xl font-bold tabular-nums">{bestSet?.set || 'N/A'}</p>
                      </div>
                      <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center">
                        <Trophy className="h-6 w-6 text-accent" />
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      {bestSet ? `${bestSet.correct}/${bestSet.matches} (${bestSet.accuracy.toFixed(1)}%)` : 'No data'}
                    </p>
                  </CardContent>
                </Card>

                <Card className="glass-card-elevated border-chart-1/20">
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">Best Jackpot</p>
                        <p className="text-lg font-bold tabular-nums truncate">{bestJackpot?.id || 'N/A'}</p>
                      </div>
                      <div className="h-12 w-12 rounded-full bg-chart-1/10 flex items-center justify-center">
                        <TrendingUp className="h-6 w-6 text-chart-1" />
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      {bestJackpot ? `${bestJackpot.correct}/${bestJackpot.matches} (${bestJackpot.accuracy.toFixed(1)}%) • ${bestJackpot.sets.join(', ')}` : 'No data'}
                    </p>
                  </CardContent>
                </Card>
              </>
            );
          })()}
        </div>
      )}

      {/* Summary Cards */}
      {selectedJackpot && selectedJackpot.matches ? (
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
                      <TableBody key={`table-${selectedJackpot.id}`}>
                        {selectedJackpot.matches.map((match, idx) => (
                          <TableRow key={`${selectedJackpot.id}-${match.id}-${idx}`}>
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
          
          {/* Best Set for H/D/A Predictions */}
          {analytics.setComparison && analytics.setComparison.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Best Sets for Outcome Prediction</CardTitle>
                <CardDescription>
                  Which probability sets perform best at predicting Home Wins, Draws, and Away Wins
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Best Set for Home Wins */}
                  <Card className="border-chart-1/20">
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <p className="text-sm text-muted-foreground">Best for Home Wins</p>
                          <p className="text-2xl font-bold">{analytics.bestSetForH?.set || 'N/A'}</p>
                        </div>
                        <div className="h-12 w-12 rounded-full bg-chart-1/10 flex items-center justify-center">
                          <Trophy className="h-6 w-6 text-chart-1" />
                        </div>
                      </div>
                      {analytics.bestSetForH && analytics.bestSetForH.hTotal > 0 ? (
                        <>
                          <p className="text-lg font-semibold text-green-600">
                            {analytics.bestSetForH.hAccuracy.toFixed(1)}%
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {analytics.bestSetForH.hCorrect}/{analytics.bestSetForH.hTotal} correct predictions
                          </p>
                        </>
                      ) : (
                        <p className="text-sm text-muted-foreground">No data available</p>
                      )}
                    </CardContent>
                  </Card>

                  {/* Best Set for Draws */}
                  <Card className="border-chart-2/20">
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <p className="text-sm text-muted-foreground">Best for Draws</p>
                          <p className="text-2xl font-bold">{analytics.bestSetForD?.set || 'N/A'}</p>
                        </div>
                        <div className="h-12 w-12 rounded-full bg-chart-2/10 flex items-center justify-center">
                          <Trophy className="h-6 w-6 text-chart-2" />
                        </div>
                      </div>
                      {analytics.bestSetForD && analytics.bestSetForD.dTotal > 0 ? (
                        <>
                          <p className="text-lg font-semibold text-green-600">
                            {analytics.bestSetForD.dAccuracy.toFixed(1)}%
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {analytics.bestSetForD.dCorrect}/{analytics.bestSetForD.dTotal} correct predictions
                          </p>
                        </>
                      ) : (
                        <p className="text-sm text-muted-foreground">No data available</p>
                      )}
                    </CardContent>
                  </Card>

                  {/* Best Set for Away Wins */}
                  <Card className="border-chart-3/20">
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <p className="text-sm text-muted-foreground">Best for Away Wins</p>
                          <p className="text-2xl font-bold">{analytics.bestSetForA?.set || 'N/A'}</p>
                        </div>
                        <div className="h-12 w-12 rounded-full bg-chart-3/10 flex items-center justify-center">
                          <Trophy className="h-6 w-6 text-chart-3" />
                        </div>
                      </div>
                      {analytics.bestSetForA && analytics.bestSetForA.aTotal > 0 ? (
                        <>
                          <p className="text-lg font-semibold text-green-600">
                            {analytics.bestSetForA.aAccuracy.toFixed(1)}%
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {analytics.bestSetForA.aCorrect}/{analytics.bestSetForA.aTotal} correct predictions
                          </p>
                        </>
                      ) : (
                        <p className="text-sm text-muted-foreground">No data available</p>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Best Set Per League */}
          {analytics.bestSetPerLeague && Object.keys(analytics.bestSetPerLeague).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Best Set Per League</CardTitle>
                <CardDescription>
                  Which probability sets perform best for each league over time
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(analytics.bestSetPerLeague)
                    .sort(([, a], [, b]) => b.accuracy - a.accuracy)
                    .map(([league, bestSet]) => (
                      <Card key={league} className="border-primary/20">
                        <CardContent className="pt-6">
                          <div className="flex items-center justify-between mb-4">
                            <div>
                              <p className="text-sm text-muted-foreground">Best for {league}</p>
                              <p className="text-2xl font-bold">{bestSet.set}</p>
                            </div>
                            <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                              <Trophy className="h-6 w-6 text-primary" />
                            </div>
                          </div>
                          <p className="text-lg font-semibold text-green-600">
                            {bestSet.accuracy.toFixed(1)}%
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {bestSet.correct}/{bestSet.total} correct predictions
                          </p>
                        </CardContent>
                      </Card>
                    ))}
                </div>
              </CardContent>
            </Card>
          )}
          
          {/* Set Comparison Table */}
          {analytics.setComparison && analytics.setComparison.length > 1 && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                <CardTitle className="text-lg">Set-by-Set Performance</CardTitle>
                <CardDescription>
                  {aggregateMode === 'all' 
                    ? 'Aggregated performance across all predictions, grouped by set' 
                    : 'Detailed comparison of all probability sets'}
                </CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      // Generate and download analytics report
                      const report = generateAnalyticsReport(analytics, validations, aggregateMode);
                      downloadReport(report);
                      toast({
                        title: 'Report Generated',
                        description: 'Analytics report has been downloaded successfully.',
                      });
                    }}
                    className="gap-2"
                  >
                    <Download className="h-4 w-4" />
                    Export Report
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Set</TableHead>
                      {aggregateMode === 'all' && <TableHead className="text-right">Jackpots</TableHead>}
                      <TableHead className="text-right">Correct</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead className="text-right">Accuracy</TableHead>
                        <TableHead className="text-right">H Accuracy</TableHead>
                        <TableHead className="text-right">D Accuracy</TableHead>
                        <TableHead className="text-right">A Accuracy</TableHead>
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
                            <TableCell className="text-right">
                              {set.hTotal > 0 ? (
                                <span className={`tabular-nums ${
                                  set.hAccuracy >= 70 ? 'text-green-600' :
                                  set.hAccuracy >= 60 ? 'text-yellow-600' :
                                  'text-red-600'
                                }`}>
                                  {set.hAccuracy.toFixed(1)}%
                                  <span className="text-xs text-muted-foreground ml-1">
                                    ({set.hCorrect}/{set.hTotal})
                                  </span>
                                </span>
                              ) : (
                                <span className="text-muted-foreground text-xs">N/A</span>
                              )}
                            </TableCell>
                            <TableCell className="text-right">
                              {set.dTotal > 0 ? (
                                <span className={`tabular-nums ${
                                  set.dAccuracy >= 70 ? 'text-green-600' :
                                  set.dAccuracy >= 60 ? 'text-yellow-600' :
                                  'text-red-600'
                                }`}>
                                  {set.dAccuracy.toFixed(1)}%
                                  <span className="text-xs text-muted-foreground ml-1">
                                    ({set.dCorrect}/{set.dTotal})
                                  </span>
                                </span>
                              ) : (
                                <span className="text-muted-foreground text-xs">N/A</span>
                              )}
                            </TableCell>
                            <TableCell className="text-right">
                              {set.aTotal > 0 ? (
                                <span className={`tabular-nums ${
                                  set.aAccuracy >= 70 ? 'text-green-600' :
                                  set.aAccuracy >= 60 ? 'text-yellow-600' :
                                  'text-red-600'
                                }`}>
                                  {set.aAccuracy.toFixed(1)}%
                                  <span className="text-xs text-muted-foreground ml-1">
                                    ({set.aCorrect}/{set.aTotal})
                                  </span>
                                </span>
                              ) : (
                                <span className="text-muted-foreground text-xs">N/A</span>
                              )}
                            </TableCell>
                          <TableCell className="text-right tabular-nums">{set.brierScore.toFixed(3)}</TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
                </div>
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
                    value={selectedJackpot?.setUsed || '__all__'}
                    onValueChange={(setUsed) => {
                      if (setUsed === '__all__') {
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
                      <SelectItem value="__all__">All Sets</SelectItem>
                      {['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'].map(setId => (
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
                                {v.jackpotId.replace(/ \(Set [A-J]\)/g, '')}
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
    </PageLayout>
  );
}
