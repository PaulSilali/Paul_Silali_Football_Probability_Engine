import React, { useState, useMemo, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Info, Download, FileText, Calculator, TrendingUp, Target, Zap, Scale, Users, AlertTriangle, CheckCircle, HelpCircle, Loader2, Save, FolderOpen, X, Trophy, Sparkles } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageLayout } from '@/components/layouts/PageLayout';
import { ModernCard } from '@/components/ui/modern-card';
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { exportProbabilities } from '@/lib/export';
import { AccumulatorCalculator } from '@/components/AccumulatorCalculator';
import { InjuryInput } from '@/components/InjuryInput';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/services/api';
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
  calibrated: boolean;
  heuristic: boolean;
  allowedForDecisionSupport: boolean;
  probabilities: (FixtureProbability & { odds: { home: number; draw: number; away: number } })[] 
}> = {
  A: {
    name: 'Set A - Pure Model',
    description: 'Dixon-Coles statistical model only. Long-term, theory-driven estimates.',
    icon: Calculator,
    useCase: 'Contrarian bettors',
    guidance: 'Best if you believe the model captures value the market misses.',
    calibrated: true,
    heuristic: false,
    allowedForDecisionSupport: true,
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
    calibrated: true,
    heuristic: false,
    allowedForDecisionSupport: true,
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
    calibrated: true,
    heuristic: false,
    allowedForDecisionSupport: true,
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
    guidance: '⚠️ HEURISTIC: Not probability-calibrated. Good for jackpots where draws are historically undervalued.',
    calibrated: false,
    heuristic: true,
    allowedForDecisionSupport: false,
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
    guidance: '⚠️ HEURISTIC: Not probability-calibrated. Want aggressive, decisive picks? This set has lower entropy.',
    calibrated: false,
    heuristic: true,
    allowedForDecisionSupport: false,
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
    calibrated: true,
    heuristic: false,
    allowedForDecisionSupport: true,
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
    calibrated: true,
    heuristic: false,
    allowedForDecisionSupport: true,
    probabilities: [
      { ...baseFixtures[0], homeWinProbability: 51.00, drawProbability: 26.00, awayWinProbability: 23.00, confidenceLow: 41.4, confidenceHigh: 47.6 },
      { ...baseFixtures[1], homeWinProbability: 33.46, drawProbability: 28.49, awayWinProbability: 38.05, confidenceLow: 29.9, confidenceHigh: 36.1 },
      { ...baseFixtures[2], homeWinProbability: 40.45, drawProbability: 30.04, awayWinProbability: 29.51, confidenceLow: 36.9, confidenceHigh: 43.1 },
      { ...baseFixtures[3], homeWinProbability: 47.16, drawProbability: 27.79, awayWinProbability: 25.05, confidenceLow: 43.9, confidenceHigh: 50.1 },
      { ...baseFixtures[4], homeWinProbability: 50.42, drawProbability: 26.14, awayWinProbability: 23.44, confidenceLow: 47.9, confidenceHigh: 54.1 },
    ],
  },
  H: {
    name: 'Set H - Market Consensus Draw',
    description: 'Set B + Draw adjusted by average market odds (70% base + 30% market).',
    icon: Calculator,
    useCase: 'Market-informed draw coverage',
    guidance: 'Uses market consensus to fine-tune draw probabilities. Best when you trust multiple market sources and want balanced draw coverage.',
    calibrated: true,
    heuristic: false,
    allowedForDecisionSupport: true,
    probabilities: [
      { ...baseFixtures[0], homeWinProbability: 51.00, drawProbability: 27.75, awayWinProbability: 21.25, confidenceLow: 41.4, confidenceHigh: 47.6 },
      { ...baseFixtures[1], homeWinProbability: 33.46, drawProbability: 28.49, awayWinProbability: 38.05, confidenceLow: 29.9, confidenceHigh: 36.1 },
      { ...baseFixtures[2], homeWinProbability: 40.45, drawProbability: 30.04, awayWinProbability: 29.51, confidenceLow: 36.9, confidenceHigh: 43.1 },
      { ...baseFixtures[3], homeWinProbability: 47.16, drawProbability: 27.79, awayWinProbability: 25.05, confidenceLow: 43.9, confidenceHigh: 50.1 },
      { ...baseFixtures[4], homeWinProbability: 50.42, drawProbability: 26.14, awayWinProbability: 23.44, confidenceLow: 47.9, confidenceHigh: 54.1 },
    ],
  },
  I: {
    name: 'Set I - Formula-Based Draw',
    description: 'Set A + Draw adjusted by formula considering entropy, spread, and market divergence.',
    icon: Calculator,
    useCase: 'Balanced optimization',
    guidance: 'Intelligently adjusts draw probabilities based on match characteristics (entropy, home-away spread, market divergence). Higher entropy and lower spread boost draw probability.',
    calibrated: true,
    heuristic: false,
    allowedForDecisionSupport: true,
    probabilities: [
      { ...baseFixtures[0], homeWinProbability: 48.00, drawProbability: 31.86, awayWinProbability: 20.14, confidenceLow: 42.1, confidenceHigh: 48.4 },
      { ...baseFixtures[1], homeWinProbability: 32.15, drawProbability: 28.45, awayWinProbability: 39.40, confidenceLow: 29.2, confidenceHigh: 35.1 },
      { ...baseFixtures[2], homeWinProbability: 41.67, drawProbability: 29.33, awayWinProbability: 29.00, confidenceLow: 38.5, confidenceHigh: 44.8 },
      { ...baseFixtures[3], homeWinProbability: 48.92, drawProbability: 26.54, awayWinProbability: 24.54, confidenceLow: 45.8, confidenceHigh: 52.0 },
      { ...baseFixtures[4], homeWinProbability: 52.18, drawProbability: 25.12, awayWinProbability: 22.70, confidenceLow: 49.1, confidenceHigh: 55.3 },
    ],
  },
  J: {
    name: 'Set J - System-Selected Draw Strategy',
    description: 'Set G + Draw adjusted by system-selected optimal strategy (adaptive 1.05x to 1.25x).',
    icon: Calculator,
    useCase: 'Adaptive intelligent coverage',
    guidance: 'The system automatically selects the best draw adjustment strategy based on match context. Combines ensemble approach (Set G) with intelligent draw optimization for maximum coverage.',
    calibrated: true,
    heuristic: false,
    allowedForDecisionSupport: true,
    probabilities: [
      { ...baseFixtures[0], homeWinProbability: 51.00, drawProbability: 28.50, awayWinProbability: 20.50, confidenceLow: 41.4, confidenceHigh: 47.6 },
      { ...baseFixtures[1], homeWinProbability: 33.46, drawProbability: 29.20, awayWinProbability: 37.34, confidenceLow: 29.9, confidenceHigh: 36.1 },
      { ...baseFixtures[2], homeWinProbability: 40.45, drawProbability: 30.50, awayWinProbability: 29.05, confidenceLow: 36.9, confidenceHigh: 43.1 },
      { ...baseFixtures[3], homeWinProbability: 47.16, drawProbability: 28.30, awayWinProbability: 24.54, confidenceLow: 43.9, confidenceHigh: 50.1 },
      { ...baseFixtures[4], homeWinProbability: 50.42, drawProbability: 26.80, awayWinProbability: 22.78, confidenceLow: 47.9, confidenceHigh: 54.1 },
    ],
  },
};

const setKeys = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'] as const;

type Selection = '1' | 'X' | '2' | null;

export default function ProbabilityOutput() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const jackpotId = searchParams.get('jackpotId');
  
  const [activeSet, setActiveSet] = useState<string>('B');
  const [showConfidenceBands, setShowConfidenceBands] = useState(false);
  const [selections, setSelections] = useState<Record<string, Selection>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modelVersion, setModelVersion] = useState<string>('');
  const [loadedSets, setLoadedSets] = useState<Record<string, any>>({});
  const [isSaveDialogOpen, setIsSaveDialogOpen] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [saveDescription, setSaveDescription] = useState('');
  const [actualResults, setActualResults] = useState<Record<string, Selection>>({});
  const [savedResults, setSavedResults] = useState<any[]>([]);
  const [loadingSavedResults, setLoadingSavedResults] = useState(false);
  const [scores, setScores] = useState<Record<string, { correct: number; total: number }>>({});

  // State for pipeline metadata
  const [pipelineMetadata, setPipelineMetadata] = useState<any>(null);
  const [pipelineStatusChecked, setPipelineStatusChecked] = useState(false);

  // State for injury input dialogs
  const [injuryDialogOpen, setInjuryDialogOpen] = useState<{
    open: boolean;
    fixtureId: number | null;
    teamId: number | null;
    teamName: string;
    isHome: boolean;
  }>({
    open: false,
    fixtureId: null,
    teamId: null,
    teamName: '',
    isHome: true,
  });

  // Check pipeline status when loading jackpot
  useEffect(() => {
    const checkPipelineStatus = async () => {
      if (!jackpotId) return;
      
      try {
        const jackpotResponse = await apiClient.getJackpot(jackpotId);
        if (jackpotResponse.success && jackpotResponse.data?.pipelineMetadata) {
          setPipelineMetadata(jackpotResponse.data.pipelineMetadata);
          
          // Check if data is still missing (only if pipeline was run)
          if (jackpotResponse.data.pipelineMetadata.pipeline_run) {
            try {
              const allTeamNames = jackpotResponse.data.fixtures?.flatMap((f: any) => [
                f.homeTeam, f.awayTeam
              ]).filter((name: string) => name && name.trim().length >= 2) || [];
              
              if (allTeamNames.length > 0) {
                const statusResponse = await apiClient.checkTeamsStatus(allTeamNames, undefined);
                
                if (statusResponse.success && statusResponse.data) {
                  const stillMissing = statusResponse.data.missing_teams.length > 0;
                  const stillUntrained = statusResponse.data.untrained_teams.length > 0;
                  
                  if (stillMissing || stillUntrained) {
                    toast({
                      title: 'Pipeline Status Warning',
                      description: stillMissing 
                        ? `${statusResponse.data.missing_teams.length} teams still missing. Download may not have been successful.`
                        : `${statusResponse.data.untrained_teams.length} teams still untrained. Model training may not have been successful.`,
                      variant: 'destructive',
                      duration: 10000,
                    });
                  }
                }
              }
            } catch (error) {
              console.error('Error checking pipeline status:', error);
            }
          }
        }
        setPipelineStatusChecked(true);
      } catch (error) {
        console.error('Error checking pipeline status:', error);
        setPipelineStatusChecked(true);
      }
    };
    
    checkPipelineStatus();
  }, [jackpotId, toast]);

  // Fetch probabilities from API
  useEffect(() => {
    const fetchProbabilities = async () => {
      if (!jackpotId) {
        setError('No jackpot ID provided');
        setLoading(false);
        // Use mock data if no jackpotId
        setLoadedSets(probabilitySets);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.getProbabilities(jackpotId);
        
        // Backend returns PredictionResponse directly, not wrapped in ApiResponse
        const data = (response as any).success ? (response as any).data : response;
        
        if (data && data.probabilitySets) {
          setModelVersion(data.modelVersion || 'Unknown');
          
          // Transform API response to match component format
          const transformedSets: Record<string, any> = {};
          
          Object.keys(data.probabilitySets).forEach(setId => {
            const setProbs = data.probabilitySets[setId];
            const fixtures = data.fixtures || [];
            
            transformedSets[setId] = {
              name: probabilitySets[setId]?.name || `Set ${setId}`,
              description: probabilitySets[setId]?.description || '',
              icon: probabilitySets[setId]?.icon || Calculator,
              useCase: probabilitySets[setId]?.useCase || '',
              guidance: probabilitySets[setId]?.guidance || '',
              calibrated: setProbs[0]?.calibrated ?? probabilitySets[setId]?.calibrated ?? false,
              heuristic: setProbs[0]?.heuristic ?? probabilitySets[setId]?.heuristic ?? false,
              allowedForDecisionSupport: setProbs[0]?.allowedForDecisionSupport ?? probabilitySets[setId]?.allowedForDecisionSupport ?? true,
              probabilities: setProbs.map((prob: any, idx: number) => ({
                fixtureId: fixtures[idx]?.id || String(idx + 1),
                fixtureIdNum: fixtures[idx]?.id ? parseInt(fixtures[idx].id) : null,  // Numeric ID for API
                homeTeam: fixtures[idx]?.homeTeam || '',
                awayTeam: fixtures[idx]?.awayTeam || '',
                homeTeamId: fixtures[idx]?.homeTeamId || fixtures[idx]?.home_team_id || null,
                awayTeamId: fixtures[idx]?.awayTeamId || fixtures[idx]?.away_team_id || null,
                odds: fixtures[idx]?.odds || { home: 2.0, draw: 3.0, away: 2.5 },
                homeWinProbability: prob.homeWinProbability || 0,
                drawProbability: prob.drawProbability || 0,
                awayWinProbability: prob.awayWinProbability || 0,
                entropy: prob.entropy || 1.58,
                confidenceLow: prob.confidenceLow,
                confidenceHigh: prob.confidenceHigh,
              })),
            };
          });
          
          setLoadedSets(transformedSets);
        } else {
          throw new Error('Invalid response format: missing probabilitySets');
        }
      } catch (err: any) {
        console.error('Error fetching probabilities:', err);
        setError(err.message || 'Failed to load probabilities');
        toast({
          title: 'Error',
          description: err.message || 'Failed to load probabilities. Using mock data.',
          variant: 'destructive',
        });
        // Fallback to mock data on error
        setLoadedSets(probabilitySets);
      } finally {
        setLoading(false);
      }
    };

    fetchProbabilities();
  }, [jackpotId, toast]);

  // Use loaded sets if available, otherwise use mock data
  const setsToUse = useMemo(() => {
    return Object.keys(loadedSets).length > 0 ? loadedSets : probabilitySets;
  }, [loadedSets]);

  // Load saved results
  useEffect(() => {
    const loadSavedResults = async () => {
      try {
        setLoadingSavedResults(true);
        
        let response: any;
        if (jackpotId) {
          console.log('Loading saved results for jackpot:', jackpotId);
          response = await apiClient.getSavedResults(jackpotId);
        } else {
          console.log('No jackpotId provided, loading latest saved result');
          response = await apiClient.getLatestSavedResult();
          // Transform response to match expected format
          if (response.success && response.data?.result) {
            response = {
              success: true,
              data: {
                results: [response.data.result]
              }
            };
          }
        }
        
        console.log('Saved results response:', response);
        
        if (response.success && response.data) {
          const results = response.data.results || [];
          console.log(`Loaded ${results.length} saved results:`, results);
          setSavedResults(results);
          
          // If we loaded latest result without jackpotId, try to load probabilities for that jackpotId
          if (!jackpotId && results.length > 0 && results[0].jackpotId) {
            const savedJackpotId = results[0].jackpotId;
            console.log('Found jackpotId from saved result:', savedJackpotId);
            // Load probabilities for this jackpotId
            try {
              const probResponse = await apiClient.getProbabilities(savedJackpotId);
              const probData = (probResponse as any).success ? (probResponse as any).data : probResponse;
              
              if (probData && probData.probabilitySets) {
                setModelVersion(probData.modelVersion || 'Unknown');
                
                const transformedSets: Record<string, any> = {};
                Object.keys(probData.probabilitySets).forEach(setId => {
                  const setProbs = probData.probabilitySets[setId];
                  const fixtures = probData.fixtures || [];
                  
                  transformedSets[setId] = {
                    name: probabilitySets[setId]?.name || `Set ${setId}`,
                    description: probabilitySets[setId]?.description || '',
                    icon: probabilitySets[setId]?.icon || Calculator,
                    useCase: probabilitySets[setId]?.useCase || '',
                    guidance: probabilitySets[setId]?.guidance || '',
                    calibrated: setProbs[0]?.calibrated ?? probabilitySets[setId]?.calibrated ?? false,
                    heuristic: setProbs[0]?.heuristic ?? probabilitySets[setId]?.heuristic ?? false,
                    allowedForDecisionSupport: setProbs[0]?.allowedForDecisionSupport ?? probabilitySets[setId]?.allowedForDecisionSupport ?? true,
                    probabilities: setProbs.map((prob: any, idx: number) => ({
                      fixtureId: fixtures[idx]?.id || String(idx + 1),
                      fixtureIdNum: fixtures[idx]?.id ? parseInt(fixtures[idx].id) : null,  // Numeric ID for API
                      homeTeam: fixtures[idx]?.homeTeam || '',
                      awayTeam: fixtures[idx]?.awayTeam || '',
                      homeTeamId: fixtures[idx]?.homeTeamId || fixtures[idx]?.home_team_id || null,
                      awayTeamId: fixtures[idx]?.awayTeamId || fixtures[idx]?.away_team_id || null,
                      odds: fixtures[idx]?.odds || { home: 2.0, draw: 3.0, away: 2.5 },
                      homeWinProbability: prob.homeWinProbability || 0,
                      drawProbability: prob.drawProbability || 0,
                      awayWinProbability: prob.awayWinProbability || 0,
                      entropy: prob.entropy || 1.58,
                      confidenceLow: prob.confidenceLow,
                      confidenceHigh: prob.confidenceHigh,
                    })),
                  };
                });
                
                setLoadedSets(transformedSets);
                console.log('Loaded probabilities for saved jackpot:', savedJackpotId);
              }
            } catch (err: any) {
              console.error('Error loading probabilities for saved jackpot:', err);
              // Continue with mock data if loading fails
            }
          }
          
          // Load scores if available
          const scoresMap: Record<string, { correct: number; total: number }> = {};
          results.forEach((result: any) => {
            if (result.scores) {
              Object.assign(scoresMap, result.scores);
            }
          });
          if (Object.keys(scoresMap).length > 0) {
            console.log('Loaded scores:', scoresMap);
            setScores(scoresMap);
          }
        } else {
          console.log('No saved results found or invalid response');
        }
      } catch (err: any) {
        console.error('Error loading saved results:', err);
        // Don't show error toast for missing results, just log it
        if (jackpotId) {
          toast({
            title: 'Warning',
            description: 'Could not load saved results: ' + (err.message || 'Unknown error'),
            variant: 'destructive',
          });
        }
      } finally {
        setLoadingSavedResults(false);
      }
    };

    loadSavedResults();
  }, [jackpotId, toast]);

  // Apply last saved result after probabilities are loaded
  useEffect(() => {
    // Need probabilities loaded and saved results available
    if (Object.keys(loadedSets).length === 0 || savedResults.length === 0) {
      console.log('Waiting for probabilities or saved results:', {
        hasLoadedSets: Object.keys(loadedSets).length > 0,
        hasSavedResults: savedResults.length > 0,
        jackpotId
      });
      return;
    }
    
    const lastSavedResult = savedResults[0]; // Most recent result (ordered by created_at DESC)
    console.log('Applying last saved result:', {
      resultId: lastSavedResult.id,
      resultName: lastSavedResult.name,
      hasSelections: !!lastSavedResult.selections,
      hasActualResults: !!lastSavedResult.actualResults,
      hasScores: !!lastSavedResult.scores,
      fixtureIds: Object.keys(loadedSets).length > 0 && loadedSets['B']?.probabilities?.map((p: any) => p.fixtureId),
      savedActualResults: lastSavedResult.actualResults
    });
    
    // Apply selections from the active set (Set B by default) or any set
    if (lastSavedResult.selections) {
      const selectionsToApply: Record<string, Selection> = {};
      
      // Get current probabilities to match fixture IDs
      const currentProbs = setsToUse['B']?.probabilities || setsToUse[activeSet]?.probabilities || [];
      const currentFixtureIds = currentProbs.map((p: any) => p.fixtureId);
      
      // Try to get selections from active set first, then Set B, then any set
      const setPriority = [activeSet, 'B', 'A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'];
      
      for (const setId of setPriority) {
        if (lastSavedResult.selections[setId]) {
          const savedSelections = lastSavedResult.selections[setId];
          
          // Convert saved selections to array and match by index position
          const savedEntries = Object.entries(savedSelections);
          
          savedEntries.forEach(([savedFixtureId, selection], index) => {
            // First try direct ID match
            if (currentFixtureIds.includes(savedFixtureId)) {
              selectionsToApply[savedFixtureId] = selection as Selection;
            } else if (index < currentFixtureIds.length) {
              // Match by index position (most reliable when IDs don't match)
              const matchedFixtureId = currentFixtureIds[index];
              if (matchedFixtureId) {
                selectionsToApply[matchedFixtureId] = selection as Selection;
              }
            }
          });
          
          if (Object.keys(selectionsToApply).length > 0) {
            console.log(`Applied selections from Set ${setId} (matched ${Object.keys(selectionsToApply).length} by index):`, selectionsToApply);
            break; // Use first set found
          }
        }
      }
      
      // If no set-specific selections matched, try merging all sets (match by index)
      if (Object.keys(selectionsToApply).length === 0) {
        // Get the first set's selections to use as reference
        const firstSetSelections = Object.values(lastSavedResult.selections)[0] as any;
        if (firstSetSelections) {
          const savedEntries = Object.entries(firstSetSelections);
          savedEntries.forEach(([savedFixtureId, selection], index) => {
            if (index < currentFixtureIds.length) {
              const matchedFixtureId = currentFixtureIds[index];
              if (matchedFixtureId && !selectionsToApply[matchedFixtureId]) {
                selectionsToApply[matchedFixtureId] = selection as Selection;
              }
            }
          });
        }
        console.log('Applied merged selections from all sets (matched by index):', selectionsToApply);
      }
      
      if (Object.keys(selectionsToApply).length > 0) {
        console.log('Setting selections:', selectionsToApply);
        setSelections(selectionsToApply);
        toast({
          title: 'Loaded Saved Results',
          description: `Applied ${Object.keys(selectionsToApply).length} selections from "${lastSavedResult.name}"`,
        });
      } else {
        console.warn('No selections could be matched. Saved fixture IDs:', Object.keys(lastSavedResult.selections).flatMap(setId => Object.keys(lastSavedResult.selections[setId] || {})), 'Current fixture IDs:', currentFixtureIds);
      }
    }
    
    // Apply actual results if available
    if (lastSavedResult.actualResults && Object.keys(lastSavedResult.actualResults).length > 0) {
      const actualResultsMap: Record<string, Selection> = {};
      const currentProbs = setsToUse['B']?.probabilities || setsToUse[activeSet]?.probabilities || [];
      
      if (currentProbs.length === 0) {
        console.warn('No probabilities available to match actual results, will retry when probabilities load');
        // Don't return early - continue to apply scores if available
      } else {
      
      const currentFixtureIds = currentProbs.map((p: any) => p.fixtureId);
      
      // Convert to array and match by index position
      const savedActualEntries = Object.entries(lastSavedResult.actualResults);
      console.log('Matching actual results:', {
        savedEntries: savedActualEntries.length,
        currentFixtureIds: currentFixtureIds.length,
        savedFixtureIds: savedActualEntries.map(([id]) => id),
        currentFixtureIds: currentFixtureIds
      });
      
      savedActualEntries.forEach(([savedFixtureId, result], index) => {
        // First try direct ID match
        if (currentFixtureIds.includes(savedFixtureId)) {
          actualResultsMap[savedFixtureId] = result as Selection;
          console.log(`Matched by ID: ${savedFixtureId} -> ${result}`);
        } else if (index < currentFixtureIds.length) {
          // Match by index position (most reliable)
          const matchedFixtureId = currentFixtureIds[index];
          if (matchedFixtureId) {
            actualResultsMap[matchedFixtureId] = result as Selection;
            console.log(`Matched by index ${index}: ${savedFixtureId} -> ${matchedFixtureId} = ${result}`);
          }
        }
      });
      
        if (Object.keys(actualResultsMap).length > 0) {
          console.log('Setting actual results (matched):', actualResultsMap);
          setActualResults(actualResultsMap);
          toast({
            title: 'Loaded Saved Results',
            description: `Restored ${Object.keys(actualResultsMap).length} actual results from "${lastSavedResult.name}"`,
          });
        } else {
          console.warn('No actual results could be matched. Saved:', savedActualEntries.map(([id]) => id).slice(0, 5), 'Current:', currentFixtureIds.slice(0, 5));
        }
      }
    } else {
      console.log('No actual results in saved result');
    }
    
    // Apply scores if available
    if (lastSavedResult.scores && Object.keys(lastSavedResult.scores).length > 0) {
      console.log('Setting scores:', lastSavedResult.scores);
      setScores(lastSavedResult.scores);
    }
  }, [loadedSets, savedResults, activeSet, setsToUse, toast]);

  // Calculate scores when actual results change - validate each set separately
  // Uses saved selections per set (what user picked) OR highest probability if no selection
  useEffect(() => {
    if (Object.keys(actualResults).length === 0) return;
    if (Object.keys(setsToUse).length === 0) return;
    
    const newScores: Record<string, { correct: number; total: number }> = {};
    const setKeysForScoring = Object.keys(setsToUse).length > 0 ? Object.keys(setsToUse) : Array.from(setKeys);
    
    // Get saved selections per set from latest saved result
    const savedSelectionsPerSet: Record<string, Record<string, Selection>> = {};
    if (savedResults.length > 0 && savedResults[0].selections) {
      Object.keys(savedResults[0].selections).forEach(setId => {
        const setSelections = savedResults[0].selections[setId];
        savedSelectionsPerSet[setId] = {};
        Object.entries(setSelections).forEach(([fixtureId, selection]) => {
          savedSelectionsPerSet[setId][fixtureId] = selection as Selection;
        });
      });
    }
    
    setKeysForScoring.forEach(setId => {
      const set = setsToUse[setId];
      if (!set) return;
      
      let correct = 0;
      let total = 0;
      
      set.probabilities.forEach(prob => {
        const actualResult = actualResults[prob.fixtureId];
        if (actualResult) {
          total++;
          
          // Priority: 1) Saved selection for this set, 2) Current selection, 3) Highest probability
          let predictedResult: Selection = null;
          
          // First check saved selections for this specific set
          if (savedSelectionsPerSet[setId] && savedSelectionsPerSet[setId][prob.fixtureId]) {
            predictedResult = savedSelectionsPerSet[setId][prob.fixtureId];
          }
          // Then check current selections (global)
          else if (selections[prob.fixtureId]) {
            predictedResult = selections[prob.fixtureId];
          }
          // Fallback to highest probability from this set
          else {
            predictedResult = getHighestProbOutcome(prob);
          }
          
          if (actualResult === predictedResult) {
            correct++;
          }
        }
      });
      
      if (total > 0) {
        newScores[setId] = { correct, total };
      }
    });
    
    setScores(newScores);
  }, [actualResults, setsToUse, selections, savedResults]);

  // Auto-save actual results when they change (with debouncing)
  useEffect(() => {
    if (Object.keys(actualResults).length === 0) return;
    if (!jackpotId || savedResults.length === 0) return;
    
    // Debounce: wait 2 seconds after last change before saving
    const timeoutId = setTimeout(async () => {
      const lastSavedResult = savedResults[0];
      if (!lastSavedResult || !lastSavedResult.id) return;
      
      try {
        console.log('Auto-saving actual results to saved result:', lastSavedResult.id);
        const response = await apiClient.updateActualResults(lastSavedResult.id, actualResults);
        
        if (response.success) {
          console.log('Actual results auto-saved successfully');
          // Update local scores if provided
          if (response.data?.scores) {
            setScores(response.data.scores);
          }
          // Reload saved results to get updated data
          const reloadResponse = await apiClient.getSavedResults(jackpotId);
          if (reloadResponse.success && reloadResponse.data) {
            setSavedResults(reloadResponse.data.results || []);
          }
        }
      } catch (err: any) {
        console.error('Error auto-saving actual results:', err);
        // Don't show error toast for auto-save failures to avoid annoying the user
      }
    }, 2000); // 2 second debounce
    
    return () => clearTimeout(timeoutId);
  }, [actualResults, jackpotId, savedResults]);

  // Save probability result
  const handleSaveResult = async () => {
    console.log('=== SAVE BUTTON CLICKED ===');
    console.log('Current state:', {
      jackpotId,
      saveName,
      saveNameLength: saveName?.length,
      saveNameTrimmed: saveName?.trim(),
      saveNameTrimmedLength: saveName?.trim()?.length,
      saveDescription,
      isSaveDialogOpen,
      selectionsCount: Object.keys(selections).length,
      actualResultsCount: Object.keys(actualResults).length,
      scoresCount: Object.keys(scores).length,
      savedResultsCount: savedResults.length,
      latestSavedResult: savedResults[0],
    });

    // Try to get jackpotId from URL, saved results, or latest saved result
    let targetJackpotId = jackpotId;
    
    if (!targetJackpotId && savedResults.length > 0 && savedResults[0]?.jackpotId) {
      console.log('No jackpotId in URL, using jackpotId from latest saved result:', savedResults[0].jackpotId);
      targetJackpotId = savedResults[0].jackpotId;
    }
    
    if (!targetJackpotId) {
      console.log('No jackpotId found, trying to load latest saved result...');
      try {
        const latestResponse = await apiClient.getLatestSavedResult();
        if (latestResponse.success && latestResponse.data?.result?.jackpotId) {
          targetJackpotId = latestResponse.data.result.jackpotId;
          console.log('Found jackpotId from latest saved result:', targetJackpotId);
        }
      } catch (err) {
        console.error('Error loading latest saved result:', err);
      }
    }

    // Validation with detailed logging
    if (!targetJackpotId) {
      console.error('VALIDATION FAILED: No jackpotId found anywhere', { 
        jackpotId, 
        savedResultsCount: savedResults.length,
        latestSavedResultJackpotId: savedResults[0]?.jackpotId 
      });
      toast({
        title: 'Error',
        description: 'No jackpot ID found. Please navigate from a jackpot input page or ensure you have saved results.',
        variant: 'destructive',
      });
      return;
    }

    const trimmedName = saveName?.trim() || '';
    if (!trimmedName) {
      console.error('VALIDATION FAILED: Empty name', {
        saveName,
        saveNameType: typeof saveName,
        saveNameLength: saveName?.length,
        trimmedName,
        trimmedNameLength: trimmedName.length,
      });
      toast({
        title: 'Error',
        description: 'Please provide a name for the saved result',
        variant: 'destructive',
      });
      return;
    }

    console.log('Validation passed, proceeding with save...');

    try {
      // Build selections object per set
      const selectionsPerSet: Record<string, Record<string, string>> = {};
      const setKeysForSaving = Object.keys(setsToUse).length > 0 ? Object.keys(setsToUse) : Array.from(setKeys);
      
      console.log('Building selections per set...');
      setKeysForSaving.forEach(setId => {
        const setSelections: Record<string, string> = {};
        const setProbs = setsToUse[setId]?.probabilities || [];
        console.log(`Set ${setId}: ${setProbs.length} probabilities`);
        
        setProbs.forEach(prob => {
          const selection = selections[prob.fixtureId];
          if (selection) {
            setSelections[prob.fixtureId] = selection;
          }
        });
        
        if (Object.keys(setSelections).length > 0) {
          selectionsPerSet[setId] = setSelections;
          console.log(`Set ${setId}: ${Object.keys(setSelections).length} selections`);
        }
      });

      const saveData = {
        name: trimmedName,
        description: saveDescription?.trim() || undefined,
        selections: selectionsPerSet,
        actual_results: Object.keys(actualResults).length > 0 ? actualResults : undefined,
        scores: Object.keys(scores).length > 0 ? scores : undefined,
      };
      
      console.log('=== SAVE DATA PREPARED ===');
      console.log('Save payload:', {
        jackpotId: targetJackpotId,
        name: saveData.name,
        nameLength: saveData.name.length,
        description: saveData.description,
        selectionsKeys: Object.keys(saveData.selections),
        selectionsCount: Object.keys(saveData.selections).length,
        actualResultsKeys: saveData.actual_results ? Object.keys(saveData.actual_results) : [],
        actualResultsCount: saveData.actual_results ? Object.keys(saveData.actual_results).length : 0,
        scoresKeys: saveData.scores ? Object.keys(saveData.scores) : [],
        scoresCount: saveData.scores ? Object.keys(saveData.scores).length : 0,
      });
      console.log('Full saveData object:', JSON.stringify(saveData, null, 2));

      console.log('Calling API: saveProbabilityResult with jackpotId:', targetJackpotId);
      const response = await apiClient.saveProbabilityResult(targetJackpotId, saveData);
      console.log('API Response received:', {
        success: response.success,
        message: response.message,
        data: response.data,
      });

      if (response.success) {
        console.log('Save successful!');
        toast({
          title: 'Success',
          description: 'Probability result saved successfully',
        });
        setIsSaveDialogOpen(false);
        setSaveName('');
        setSaveDescription('');
        // Reload saved results
        console.log('Reloading saved results for jackpotId:', targetJackpotId);
        const reloadResponse = await apiClient.getSavedResults(targetJackpotId);
        if (reloadResponse.success && reloadResponse.data) {
          setSavedResults(reloadResponse.data.results || []);
          console.log('Saved results reloaded:', reloadResponse.data.results?.length || 0);
        }
        
        // Update URL if jackpotId was missing
        if (!jackpotId && targetJackpotId) {
          console.log('Updating URL with jackpotId:', targetJackpotId);
          navigate(`/probability-output?jackpotId=${targetJackpotId}`, { replace: true });
        }
      } else {
        console.error('API returned success=false:', response);
        toast({
          title: 'Error',
          description: response.message || 'Failed to save result',
          variant: 'destructive',
        });
      }
    } catch (err: any) {
      console.error('=== ERROR SAVING RESULT ===');
      console.error('Error object:', err);
      console.error('Error type:', typeof err);
      console.error('Error message:', err?.message);
      console.error('Error detail:', err?.detail);
      console.error('Error status:', err?.status);
      console.error('Error stack:', err?.stack);
      console.error('Full error:', JSON.stringify(err, Object.getOwnPropertyNames(err), 2));
      
      const errorMessage = err?.message || err?.detail || err?.error || JSON.stringify(err) || 'Failed to save result';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    }
  };

  const currentSet = setsToUse[activeSet] || setsToUse['B'];
  const availableSetKeys = Object.keys(setsToUse).length > 0 ? Object.keys(setsToUse) : setKeys;
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

  // Get draw pressure indicator (when home ≈ away, draw probability is structurally high)
  const getDrawPressure = (prob: FixtureProbability & { drawComponents?: { poisson?: number; dixonColes?: number; market?: number | null } }) => {
    const homeAwayDiff = Math.abs(prob.homeWinProbability - prob.awayWinProbability);
    const drawProb = prob.drawProbability;
    
    // High draw pressure: home and away are close (within 5%), and draw is elevated (>25%)
    const hasHighDrawPressure = homeAwayDiff < 5 && drawProb > 25;
    
    if (hasHighDrawPressure) {
      return {
        hasPressure: true,
        message: `High structural draw likelihood (goal symmetry: ${homeAwayDiff.toFixed(1)}% spread)`,
        components: prob.drawComponents
      };
    }
    
    return { hasPressure: false, message: null, components: null };
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

  // Show loading state
  if (loading) {
    return (
      <PageLayout
        title="Probability Output"
        description="View calculated probabilities for all sets"
        icon={<Calculator className="h-6 w-6" />}
      >
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center space-y-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
            <p className="text-muted-foreground">Loading probabilities...</p>
          </div>
        </div>
      </PageLayout>
    );
  }

  // Show error state
  if (error && Object.keys(loadedSets).length === 0) {
    return (
      <PageLayout
        title="Probability Output"
        description="View calculated probabilities for all sets"
        icon={<Calculator className="h-6 w-6" />}
      >
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error Loading Probabilities</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button 
          onClick={() => navigate('/jackpot-input')} 
          className="mt-4"
        >
          Go Back to Input
        </Button>
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title="Probability Output"
      description={`Calculated probabilities for the current jackpot — 7 probability sets (A-G)${modelVersion ? ` • Model: ${modelVersion}` : ''}`}
      icon={<Calculator className="h-6 w-6" />}
    >
      {/* Pipeline Status Banner */}
      {pipelineMetadata && pipelineMetadata.pipeline_run && (
        <Alert className={`mb-4 ${
          pipelineMetadata.status === 'completed' && pipelineMetadata.model_trained
            ? 'border-green-500/50 bg-green-500/10'
            : pipelineMetadata.status === 'failed' || pipelineMetadata.errors?.length > 0
            ? 'border-red-500/50 bg-red-500/10'
            : 'border-blue-500/50 bg-blue-500/10'
        }`}>
          <div className="flex items-start gap-3">
            {pipelineMetadata.status === 'completed' && pipelineMetadata.model_trained ? (
              <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
            ) : pipelineMetadata.status === 'failed' ? (
              <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5" />
            ) : (
              <Info className="h-5 w-5 text-blue-500 mt-0.5" />
            )}
            <div className="flex-1 space-y-2">
              <AlertTitle className="font-semibold">
                Pipeline Execution Summary
              </AlertTitle>
              <AlertDescription className="space-y-1 text-sm">
                <div className="flex items-center gap-4 flex-wrap">
                  {pipelineMetadata.teams_created?.length > 0 && (
                    <div className="flex items-center gap-1">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span><strong>{pipelineMetadata.teams_created.length}</strong> teams created</span>
                    </div>
                  )}
                  {pipelineMetadata.data_downloaded && (
                    <div className="flex items-center gap-1">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span>
                        <strong>Data downloaded:</strong> {pipelineMetadata.download_stats?.total_matches || 0} matches
                        {pipelineMetadata.download_stats?.leagues_downloaded?.length > 0 && (
                          <span className="text-muted-foreground ml-1">
                            ({pipelineMetadata.download_stats.leagues_downloaded.map((l: any) => l.league_code).join(', ')})
                          </span>
                        )}
                      </span>
                    </div>
                  )}
                  {pipelineMetadata.model_trained && (
                    <div className="flex items-center gap-1">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span>
                        <strong>Model trained:</strong> {pipelineMetadata.training_stats?.model_version || 'N/A'}
                      </span>
                    </div>
                  )}
                  {pipelineMetadata.probabilities_calculated_with_new_data && (
                    <div className="flex items-center gap-1">
                      <Sparkles className="h-4 w-4 text-blue-500" />
                      <span className="text-green-600 font-medium">
                        ✓ Probabilities calculated using newly trained model data
                      </span>
                    </div>
                  )}
                  {pipelineMetadata.errors?.length > 0 && (
                    <div className="flex items-start gap-1">
                      <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5" />
                      <div>
                        <span className="text-yellow-600 font-medium">Warnings:</span>
                        <ul className="list-disc list-inside ml-2 text-muted-foreground">
                          {pipelineMetadata.errors.slice(0, 3).map((err: string, idx: number) => (
                            <li key={idx}>{err}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
                {pipelineMetadata.execution_timestamp && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Executed: {new Date(pipelineMetadata.execution_timestamp).toLocaleString()}
                  </p>
                )}
              </AlertDescription>
            </div>
          </div>
        </Alert>
      )}

      <div className="flex items-center gap-2">
          <Dialog 
            open={isSaveDialogOpen} 
            onOpenChange={(open) => {
              console.log('Dialog open state changing:', {
                open,
                currentSaveName: saveName,
                currentSaveDescription: saveDescription,
              });
              setIsSaveDialogOpen(open);
              if (!open) {
                // Only clear on close, not on open
                console.log('Dialog closing, clearing form');
                setSaveName('');
                setSaveDescription('');
              }
            }}
          >
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" className="glass-card">
                <Save className="h-4 w-4 mr-2" />
                Save Results
              </Button>
            </DialogTrigger>
            <DialogContent className="glass-card-elevated max-w-md">
              <DialogHeader>
                <DialogTitle>Save Probability Results</DialogTitle>
                <DialogDescription>
                  Save your selections and results for backtesting and analysis
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div>
                  <Label htmlFor="saveName">Name *</Label>
                  <Input
                    id="saveName"
                    value={saveName}
                    onChange={(e) => {
                      const newValue = e.target.value;
                      console.log('Name input changed:', {
                        newValue,
                        newValueLength: newValue.length,
                        trimmed: newValue.trim(),
                        trimmedLength: newValue.trim().length,
                      });
                      setSaveName(newValue);
                    }}
                    onBlur={(e) => {
                      console.log('Name input blurred:', {
                        value: e.target.value,
                        trimmed: e.target.value.trim(),
                      });
                    }}
                    placeholder="e.g., Weekend Jackpot - Set B"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="saveDescription">Description (optional)</Label>
                  <Textarea
                    id="saveDescription"
                    value={saveDescription}
                    onChange={(e) => setSaveDescription(e.target.value)}
                    placeholder="Add notes about this result..."
                    rows={3}
                    className="mt-1"
                  />
                </div>
                <div className="text-xs text-muted-foreground">
                  {Object.keys(selections).length} fixture{Object.keys(selections).length !== 1 ? 's' : ''} selected
                  {Object.keys(actualResults).length > 0 && (
                    <span className="ml-2">
                      • {Object.keys(actualResults).length} actual result{Object.keys(actualResults).length !== 1 ? 's' : ''} entered
                    </span>
                  )}
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsSaveDialogOpen(false)}>
                  Cancel
                </Button>
                <Button 
                  onClick={() => {
                    console.log('Save button clicked - current state:', {
                      saveName,
                      saveNameTrimmed: saveName?.trim(),
                      isDisabled: !saveName.trim(),
                    });
                    handleSaveResult();
                  }} 
                  disabled={!saveName.trim()}
                >
                  <Save className="h-4 w-4 mr-2" />
                  Save
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
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
          <div><strong>New to jackpots?</strong> Start with <Badge className="bg-primary/20 text-primary">Set B (Balanced)</Badge> — trusts the model but respects market wisdom.</div>
          <div><strong>Want aggressive picks?</strong> Try <Badge variant="outline">Set E (Sharp)</Badge> — lower entropy, clearer decisions.</div>
          <div><strong>Conservative?</strong> Use <Badge variant="outline">Set C (Market-Dominant)</Badge> — believes market is usually right.</div>
        </AlertDescription>
      </Alert>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Main probability table */}
        <div className="xl:col-span-2">
          <Tabs value={activeSet} onValueChange={setActiveSet}>
            <ScrollArea className="w-full">
              <TabsList className="inline-flex w-auto min-w-full bg-background/50 p-1">
                {availableSetKeys.map((key) => {
                  const set = setsToUse[key];
                  const Icon = set.icon;
                  const isHeuristic = set.heuristic;
                  const isCalibrated = set.calibrated;
                  return (
                    <TabsTrigger 
                      key={key} 
                      value={key} 
                      className={`flex items-center gap-2 px-4 transition-colors ${
                        isHeuristic 
                          ? 'data-[state=active]:bg-amber-500/20 data-[state=active]:text-amber-700 dark:data-[state=active]:text-amber-400 border-amber-500/30' 
                          : 'data-[state=active]:bg-primary data-[state=active]:text-primary-foreground'
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      <span className="font-medium">{key}</span>
                      {key === 'B' && (
                        <Badge className="bg-accent/20 text-accent text-xs ml-1">★</Badge>
                      )}
                      {isHeuristic && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Badge variant="outline" className="bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30 text-xs ml-1">
                              <AlertTriangle className="h-3 w-3 mr-1" />
                              Heuristic
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>This set is heuristic and not probability-calibrated</p>
                          </TooltipContent>
                        </Tooltip>
                      )}
                      {isCalibrated && !isHeuristic && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Badge variant="outline" className="bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/30 text-xs ml-1">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Calibrated
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>This set is probability-calibrated</p>
                          </TooltipContent>
                        </Tooltip>
                      )}
                    </TabsTrigger>
                  );
                })}
              </TabsList>
              <ScrollBar orientation="horizontal" />
            </ScrollArea>

            {availableSetKeys.map((key) => {
              const set = setsToUse[key];
              const isHeuristic = set.heuristic;
              const isCalibrated = set.calibrated;
              return (
                <TabsContent key={key} value={key} className="mt-4 space-y-4">
                  {/* Guidance tooltip */}
                  <Card className={`glass-card ${
                    isHeuristic 
                      ? 'bg-amber-500/5 border-amber-500/20' 
                      : 'bg-primary/5 border-primary/20'
                  }`}>
                    <CardContent className="pt-4 pb-3">
                      <div className="flex items-start gap-2">
                        <set.icon className={`h-4 w-4 mt-0.5 ${
                          isHeuristic ? 'text-amber-600 dark:text-amber-400' : 'text-primary'
                        }`} />
                        <div className="flex-1">
                          <p className={`text-sm ${
                            isHeuristic ? 'text-amber-700 dark:text-amber-300' : 'text-primary'
                          }`}>
                            {set.guidance}
                          </p>
                          {isHeuristic && (
                            <Alert className="mt-2 bg-amber-500/10 border-amber-500/30">
                              <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                              <AlertTitle className="text-amber-800 dark:text-amber-300">Heuristic Set</AlertTitle>
                              <AlertDescription className="text-amber-700 dark:text-amber-400">
                                This probability set is heuristic and not probability-calibrated. It should not be used for decision support or model evaluation.
                              </AlertDescription>
                            </Alert>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Consensus Picks Row with Score */}
                  <Card className="glass-card">
                    <CardContent className="pt-4 pb-3">
                      <div className="flex flex-wrap items-center justify-between gap-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium text-muted-foreground">Consensus Picks:</span>
                        {set.probabilities.map((prob, idx) => {
                          const pick = getHighestProbOutcome(prob);
                            const actualResult = actualResults[prob.fixtureId];
                            const isCorrect = actualResult && actualResult === pick;
                          return (
                            <Tooltip key={prob.fixtureId}>
                                <TooltipTrigger asChild>
                                  <span className="inline-block cursor-help">
                                <Badge 
                                  variant="outline" 
                                  className={`w-8 h-8 flex items-center justify-center text-sm font-bold ${
                                        isCorrect ? 'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/50' :
                                        actualResult ? 'bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/50' :
                                    pick === '1' ? 'bg-chart-1/20 text-chart-1 border-chart-1/50' :
                                    pick === 'X' ? 'bg-chart-3/20 text-chart-3 border-chart-3/50' :
                                    'bg-chart-2/20 text-chart-2 border-chart-2/50'
                                  }`}
                                >
                                  {pick}
                                </Badge>
                                  </span>
                              </TooltipTrigger>
                              <TooltipContent>
                                Match {idx + 1}: {prob.homeTeam} vs {prob.awayTeam}
                                  {actualResult && (
                                    <div className="mt-1">
                                      Actual: {actualResult} {isCorrect ? '✓' : '✗'}
                                    </div>
                                  )}
                              </TooltipContent>
                            </Tooltip>
                          );
                        })}
                        </div>
                        {scores[key] && (
                          <div className="flex items-center gap-2">
                            <Trophy className="h-4 w-4 text-primary" />
                            <span className="text-sm font-bold">
                              Score: {scores[key].correct}/{scores[key].total}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              ({((scores[key].correct / scores[key].total) * 100).toFixed(1)}%)
                            </span>
                          </div>
                        )}
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
                              <React.Fragment key={prob.fixtureId}>
                                <TableRow className="hover:bg-primary/5">
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
                                    <Tooltip>
                                      <TooltipTrigger asChild>
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
                                          {getDrawPressure(prob).hasPressure && (
                                            <span className="text-xs text-blue-500 ml-1" title="High draw pressure">⚡</span>
                                          )}
                                        </button>
                                      </TooltipTrigger>
                                      <TooltipContent side="top" className="max-w-xs">
                                        {getDrawPressure(prob).hasPressure ? (
                                          <div>
                                            <p className="font-semibold mb-1">{getDrawPressure(prob).message}</p>
                                            {getDrawPressure(prob).components && (
                                              <div className="text-xs mt-2 space-y-1">
                                                <p>Draw Components:</p>
                                                {getDrawPressure(prob).components.poisson !== undefined && (
                                                  <p>• Poisson: {(getDrawPressure(prob).components.poisson! * 100).toFixed(1)}%</p>
                                                )}
                                                {getDrawPressure(prob).components.dixonColes !== undefined && (
                                                  <p>• Dixon-Coles: {(getDrawPressure(prob).components.dixonColes! * 100).toFixed(1)}%</p>
                                                )}
                                                {getDrawPressure(prob).components.market !== null && getDrawPressure(prob).components.market !== undefined && (
                                                  <p>• Market: {(getDrawPressure(prob).components.market! * 100).toFixed(1)}%</p>
                                                )}
                                              </div>
                                            )}
                                          </div>
                                        ) : (
                                          <p>Draw probability: {formatProbability(prob.drawProbability)}%</p>
                                        )}
                                      </TooltipContent>
                                    </Tooltip>
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
                              </React.Fragment>
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

      {/* Actual Results Input Section - Always visible when probabilities are loaded */}
      {currentSet && currentSet.probabilities && currentSet.probabilities.length > 0 && (
        <Card className="glass-card border-primary/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-primary" />
              Enter Actual Results
              {Object.keys(actualResults).length > 0 && (
                <Badge variant="outline" className="ml-2 bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/30">
                  {Object.keys(actualResults).length} entered
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              Enter the actual match results to calculate scores for each probability set.
              {jackpotId && savedResults.length > 0 && (
                <span className="ml-2 text-green-600 dark:text-green-400 font-medium">
                  ✓ Results are auto-saved for backtesting
                </span>
              )}
              {Object.keys(actualResults).length === 0 && savedResults.length > 0 && (
                <span className="ml-2 text-muted-foreground text-sm">
                  (Saved results will be restored automatically)
                </span>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {currentSet.probabilities.map((prob, idx) => {
              const currentActual = actualResults[prob.fixtureId];
              return (
                <div key={prob.fixtureId} className="flex items-center gap-4 p-3 rounded-lg bg-background/50">
                  <div className="flex-1">
                    <div className="font-medium">{prob.homeTeam} vs {prob.awayTeam}</div>
                    <div className="text-sm text-muted-foreground">Match {idx + 1}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant={currentActual === '1' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setActualResults(prev => ({
                        ...prev,
                        [prob.fixtureId]: prev[prob.fixtureId] === '1' ? null : '1'
                      }))}
                    >
                      1 (Home)
                    </Button>
                    <Button
                      variant={currentActual === 'X' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setActualResults(prev => ({
                        ...prev,
                        [prob.fixtureId]: prev[prob.fixtureId] === 'X' ? null : 'X'
                      }))}
                    >
                      X (Draw)
                    </Button>
                    <Button
                      variant={currentActual === '2' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setActualResults(prev => ({
                        ...prev,
                        [prob.fixtureId]: prev[prob.fixtureId] === '2' ? null : '2'
                      }))}
                    >
                      2 (Away)
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
          {Object.keys(actualResults).length > 0 && (
            <div className="mt-4 p-3 rounded-lg bg-primary/10 border border-primary/20">
              <div className="text-sm font-medium mb-2">Score Summary:</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {Object.entries(scores).map(([setId, score]) => (
                  <div key={setId} className="text-sm">
                    <span className="font-medium">Set {setId}:</span>{' '}
                    <span className={score.correct === score.total ? 'text-green-600 dark:text-green-400 font-bold' : ''}>
                      {score.correct}/{score.total}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          </CardContent>
        </Card>
      )}

      {/* Saved Results Section */}
      {jackpotId && (
        <Card className="glass-card border-primary/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5 text-primary" />
              Saved Results
            </CardTitle>
            <CardDescription>
              Previously saved probability results for this jackpot
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadingSavedResults ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : savedResults.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <FolderOpen className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No saved results yet.</p>
                <p className="text-sm mt-2">Save your current selections to track performance over time.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {savedResults.map((result) => (
                  <Card key={result.id} className="glass-card border-border/50 hover:border-primary/30 transition-colors">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h3 className="font-semibold text-foreground">{result.name}</h3>
                            <Badge variant="outline" className="text-xs">
                              {result.totalFixtures} fixtures
                            </Badge>
                          </div>
                          {result.description && (
                            <p className="text-sm text-muted-foreground mb-2">{result.description}</p>
                          )}
                          {result.scores && Object.keys(result.scores).length > 0 && (
                            <div className="flex flex-wrap gap-2 mb-2">
                              {Object.entries(result.scores).map(([setId, score]: [string, any]) => (
                                <Badge key={setId} variant="outline" className="text-xs">
                                  Set {setId}: {score.correct}/{score.total}
                                </Badge>
                              ))}
                            </div>
                          )}
                          <p className="text-xs text-muted-foreground">
                            Saved: {new Date(result.createdAt).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Card className="glass-card bg-muted/20">
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            <strong>Legend:</strong> ★ = Recommended pick | 
            <span className="text-status-stable"> 🟢 High confidence</span> (entropy &lt; 1.0, low divergence) | 
            <span className="text-status-watch"> 🟡 Medium</span> | 
            <span className="text-status-degraded"> 🔴 Low confidence</span> (entropy &gt; 1.2 or high divergence).
            H = Entropy (lower = more decisive).
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            <strong>Stake Amount:</strong> In Kenyan jackpots, the stake amount is the money you bet per entry. 
            Typical stakes range from 50 KSH to 1,000 KSH. The prize structure varies:
            <strong>15 games:</strong> 15M KSH (all correct), 500K (14/15), 50K (13/15) | 
            <strong>17 games:</strong> 200M KSH (all correct), 5M (16/17), 500K (15/17).
          </p>
        </CardContent>
      </Card>

      {/* Injury Input Dialog */}
      {injuryDialogOpen.open && injuryDialogOpen.fixtureId && injuryDialogOpen.teamId && (
        <InjuryInput
          open={injuryDialogOpen.open}
          onOpenChange={(open) => setInjuryDialogOpen(prev => ({ ...prev, open }))}
          fixtureId={injuryDialogOpen.fixtureId}
          teamId={injuryDialogOpen.teamId}
          teamName={injuryDialogOpen.teamName}
          isHome={injuryDialogOpen.isHome}
          onSuccess={() => {
            // Refresh probabilities after injury update
            if (jackpotId) {
              const fetchProbabilities = async () => {
                try {
                  const response = await apiClient.getProbabilities(jackpotId);
                  const data = (response as any).success ? (response as any).data : response;
                  if (data && data.probabilitySets) {
                    // Reload probabilities with updated injury data
                    window.location.reload(); // Simple refresh for now
                  }
                } catch (error) {
                  console.error('Error refreshing probabilities:', error);
                }
              };
              fetchProbabilities();
            }
          }}
        />
      )}
    </PageLayout>
  );
}
