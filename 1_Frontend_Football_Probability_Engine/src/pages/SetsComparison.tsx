import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Info, Calculator, TrendingUp, Target, Zap, Scale, Users, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageLayout } from '@/components/layouts/PageLayout';
import { ModernCard } from '@/components/ui/modern-card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
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
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/services/api';
import type { ProbabilitySet, FixtureProbability, Jackpot, PaginatedResponse } from '@/types';

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
  {
    id: 'H',
    name: 'Set H: Market Consensus Draw',
    description: 'Set B + Draw adjusted by average market odds (70% base + 30% market). Uses market consensus to fine-tune draw probabilities.',
    icon: Calculator,
    useCase: 'Market-informed draw coverage',
    probabilities: [
      { fixtureId: '1', homeTeam: 'Arsenal', awayTeam: 'Chelsea', homeWinProbability: 51.00, drawProbability: 27.75, awayWinProbability: 21.25 },
      { fixtureId: '2', homeTeam: 'Liverpool', awayTeam: 'Man City', homeWinProbability: 33.46, drawProbability: 28.49, awayWinProbability: 38.05 },
      { fixtureId: '3', homeTeam: 'Man United', awayTeam: 'Tottenham', homeWinProbability: 40.45, drawProbability: 30.04, awayWinProbability: 29.51 },
    ],
  },
  {
    id: 'I',
    name: 'Set I: Formula-Based Draw',
    description: 'Set A + Draw adjusted by formula considering entropy, spread, and market divergence. Intelligently adjusts draw probabilities based on match characteristics.',
    icon: Calculator,
    useCase: 'Balanced optimization',
    probabilities: [
      { fixtureId: '1', homeTeam: 'Arsenal', awayTeam: 'Chelsea', homeWinProbability: 48.00, drawProbability: 31.86, awayWinProbability: 20.14 },
      { fixtureId: '2', homeTeam: 'Liverpool', awayTeam: 'Man City', homeWinProbability: 32.15, drawProbability: 28.45, awayWinProbability: 39.40 },
      { fixtureId: '3', homeTeam: 'Man United', awayTeam: 'Tottenham', homeWinProbability: 41.67, drawProbability: 29.33, awayWinProbability: 29.00 },
    ],
  },
  {
    id: 'J',
    name: 'Set J: System-Selected Draw Strategy',
    description: 'Set G + Draw adjusted by system-selected optimal strategy (adaptive 1.05x to 1.25x). Automatically selects best draw adjustment based on match context.',
    icon: Calculator,
    useCase: 'Adaptive intelligent coverage',
    probabilities: [
      { fixtureId: '1', homeTeam: 'Arsenal', awayTeam: 'Chelsea', homeWinProbability: 51.00, drawProbability: 28.50, awayWinProbability: 20.50 },
      { fixtureId: '2', homeTeam: 'Liverpool', awayTeam: 'Man City', homeWinProbability: 33.46, drawProbability: 29.20, awayWinProbability: 37.34 },
      { fixtureId: '3', homeTeam: 'Man United', awayTeam: 'Tottenham', homeWinProbability: 40.45, drawProbability: 30.50, awayWinProbability: 29.05 },
    ],
  },
];

type Selection = '1' | 'X' | '2' | null;

export default function SetsComparison() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { toast } = useToast();
  const jackpotId = searchParams.get('jackpotId');
  
  const [showDelta, setShowDelta] = useState(false);
  const [selectedSets, setSelectedSets] = useState(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']);
  const [loadedSets, setLoadedSets] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [actualResults, setActualResults] = useState<Record<string, Selection>>({});
  const [savedResults, setSavedResults] = useState<any[]>([]);
  const [allJackpots, setAllJackpots] = useState<Array<{id: string; name: string; createdAt: string}>>([]);
  const [loadingJackpots, setLoadingJackpots] = useState(false);
  
  // Load all jackpots for dropdown
  useEffect(() => {
    const loadJackpots = async () => {
      try {
        setLoadingJackpots(true);
        // Fetch jackpots (default page size is 20, which should be enough for most cases)
        const response = await apiClient.getJackpots();
        
        // Handle PaginatedResponse format - data is already an array
        const jackpotsData = response.data || [];
        
        if (jackpotsData.length > 0) {
          const jackpots = jackpotsData.map((j: any) => ({
            id: j.id,
            name: j.name || `Jackpot ${j.id}`,
            createdAt: j.createdAt
          })).sort((a: any, b: any) => 
            new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
          );
          setAllJackpots(jackpots);
          
          // If no jackpotId in URL, use the most recent one
          if (!jackpotId && jackpots.length > 0) {
            const params = new URLSearchParams(searchParams);
            params.set('jackpotId', jackpots[0].id);
            setSearchParams(params, { replace: true });
          }
        }
      } catch (err: any) {
        console.error('Error loading jackpots:', err);
        toast({
          title: 'Warning',
          description: 'Failed to load jackpot list',
          variant: 'destructive',
        });
      } finally {
        setLoadingJackpots(false);
      }
    };
    
    loadJackpots();
  }, [toast, searchParams, setSearchParams, jackpotId]);
  
  // Fetch probabilities from API
  useEffect(() => {
    const fetchProbabilities = async () => {
      const targetJackpotId = jackpotId;
      
      if (!targetJackpotId) {
        // Use mock data if no jackpotId
        setLoadedSets({});
        return;
      }

      try {
        setLoading(true);
        const response = await apiClient.getProbabilities(targetJackpotId);
        const data = (response as any).success ? (response as any).data : response;
        
        if (data && data.probabilitySets) {
          const transformedSets: Record<string, any> = {};
          
          Object.keys(data.probabilitySets).forEach(setId => {
            const setProbs = data.probabilitySets[setId];
            const fixtures = data.fixtures || [];
            const setMetadata = sets.find(s => s.id === setId);
            
            transformedSets[setId] = {
              id: setId,
              name: setMetadata?.name || `Set ${setId}`,
              description: setMetadata?.description || '',
              icon: setMetadata?.icon || Calculator,
              useCase: setMetadata?.useCase || '',
              probabilities: setProbs.map((prob: any, idx: number) => ({
                fixtureId: fixtures[idx]?.id || String(idx + 1),
                homeTeam: fixtures[idx]?.homeTeam || '',
                awayTeam: fixtures[idx]?.awayTeam || '',
                homeWinProbability: prob.homeWinProbability || 0,
                drawProbability: prob.drawProbability || 0,
                awayWinProbability: prob.awayWinProbability || 0,
              })),
            };
          });
          
          setLoadedSets(transformedSets);
        }
      } catch (err: any) {
        console.error('Error fetching probabilities:', err);
        toast({
          title: 'Error',
          description: 'Failed to load probabilities. Using mock data.',
          variant: 'destructive',
        });
      } finally {
        setLoading(false);
      }
    };

    fetchProbabilities();
  }, [jackpotId, toast]);

  // Load saved results
  useEffect(() => {
    const loadSavedResults = async () => {
      const targetJackpotId = jackpotId;
      if (!targetJackpotId) {
        // Try to load latest saved result
        try {
          const response = await apiClient.getLatestSavedResult();
          if (response.success && response.data?.result) {
            const result = response.data.result;
            setSavedResults([result]);
            if (result.jackpotId && !jackpotId) {
              // Load probabilities for this jackpot
              const probResponse = await apiClient.getProbabilities(result.jackpotId);
              const probData = (probResponse as any).success ? (probResponse as any).data : probResponse;
              if (probData && probData.probabilitySets) {
                const transformedSets: Record<string, any> = {};
                Object.keys(probData.probabilitySets).forEach(setId => {
                  const setProbs = probData.probabilitySets[setId];
                  const fixtures = probData.fixtures || [];
                  const setMetadata = sets.find(s => s.id === setId);
                  transformedSets[setId] = {
                    id: setId,
                    name: setMetadata?.name || `Set ${setId}`,
                    description: setMetadata?.description || '',
                    icon: setMetadata?.icon || Calculator,
                    useCase: setMetadata?.useCase || '',
                    probabilities: setProbs.map((prob: any, idx: number) => ({
                      fixtureId: fixtures[idx]?.id || String(idx + 1),
                      homeTeam: fixtures[idx]?.homeTeam || '',
                      awayTeam: fixtures[idx]?.awayTeam || '',
                      homeWinProbability: prob.homeWinProbability || 0,
                      drawProbability: prob.drawProbability || 0,
                      awayWinProbability: prob.awayWinProbability || 0,
                    })),
                  };
                });
                setLoadedSets(transformedSets);
                // Apply actual results after loading probabilities
                if (result.actualResults && Object.keys(result.actualResults).length > 0) {
                  const actualResultsMap: Record<string, Selection> = {};
                  const currentProbs = transformedSets['A']?.probabilities || Object.values(transformedSets)[0]?.probabilities || [];
                  const currentFixtureIds = currentProbs.map((p: any) => p.fixtureId);
                  Object.entries(result.actualResults).forEach(([savedFixtureId, result], index) => {
                    if (currentFixtureIds.includes(savedFixtureId)) {
                      actualResultsMap[savedFixtureId] = result as Selection;
                    } else if (index < currentFixtureIds.length) {
                      const matchedFixtureId = currentFixtureIds[index];
                      if (matchedFixtureId) {
                        actualResultsMap[matchedFixtureId] = result as Selection;
                      }
                    }
                  });
                  setActualResults(actualResultsMap);
                }
              }
            }
          }
        } catch (err: any) {
          console.error('Error loading latest saved result:', err);
        }
        return;
      }
      
      try {
        const response = await apiClient.getSavedResults(targetJackpotId);
        if (response.success && response.data) {
          const results = response.data.results || [];
          setSavedResults(results);
        }
      } catch (err: any) {
        console.error('Error loading saved results:', err);
      }
    };

    loadSavedResults();
  }, [jackpotId]);

  // Apply actual results when loadedSets or savedResults change
  useEffect(() => {
    if (Object.keys(loadedSets).length === 0 || savedResults.length === 0) return;
    
    const lastResult = savedResults[0];
    if (!lastResult?.actualResults || Object.keys(lastResult.actualResults).length === 0) return;
    
    const actualResultsMap: Record<string, Selection> = {};
    const currentProbs = loadedSets['A']?.probabilities || Object.values(loadedSets)[0]?.probabilities || [];
    const currentFixtureIds = currentProbs.map((p: any) => p.fixtureId);
    
    Object.entries(lastResult.actualResults).forEach(([savedFixtureId, result], index) => {
      if (currentFixtureIds.includes(savedFixtureId)) {
        actualResultsMap[savedFixtureId] = result as Selection;
      } else if (index < currentFixtureIds.length) {
        const matchedFixtureId = currentFixtureIds[index];
        if (matchedFixtureId) {
          actualResultsMap[matchedFixtureId] = result as Selection;
        }
      }
    });
    setActualResults(actualResultsMap);
  }, [loadedSets, savedResults]);

  // Use loaded sets if available, otherwise use mock data
  const setsToUse = useMemo(() => {
    if (Object.keys(loadedSets).length > 0) {
      return Object.values(loadedSets) as (ProbabilitySet & { icon: React.ElementType; useCase: string })[];
    }
    return sets;
  }, [loadedSets]);

  const baseSet = setsToUse.find(s => s.id === 'A') || setsToUse[0];
  const visibleSets = setsToUse.filter(s => selectedSets.includes(s.id));
  
  // Get highest probability outcome for a set
  const getHighestProbOutcome = (prob: FixtureProbability): '1' | 'X' | '2' => {
    const { homeWinProbability, drawProbability, awayWinProbability } = prob;
    if (homeWinProbability >= drawProbability && homeWinProbability >= awayWinProbability) return '1';
    if (awayWinProbability >= homeWinProbability && awayWinProbability >= drawProbability) return '2';
    return 'X';
  };

  // Calculate normalized entropy (0-1 scale)
  const calculateEntropy = (prob: FixtureProbability): number => {
    const { homeWinProbability, drawProbability, awayWinProbability } = prob;
    const h = homeWinProbability / 100;
    const d = drawProbability / 100;
    const a = awayWinProbability / 100;
    
    let entropy = 0;
    if (h > 0) entropy -= h * Math.log(h);
    if (d > 0) entropy -= d * Math.log(d);
    if (a > 0) entropy -= a * Math.log(a);
    
    // Normalize to [0, 1] where 1 = maximum uncertainty (log(3))
    const maxEntropy = Math.log(3);
    return Math.min(Math.max(entropy / maxEntropy, 0), 1);
  };

  // Get entropy badge level
  const getEntropyLevel = (entropy: number): 'HIGH' | 'MEDIUM' | 'LOW' => {
    if (entropy >= 0.85) return 'HIGH';
    if (entropy >= 0.60) return 'MEDIUM';
    return 'LOW';
  };

  // Get dominance indicator
  const getDominanceIndicator = (prob: FixtureProbability): string => {
    const { homeWinProbability, drawProbability, awayWinProbability } = prob;
    const maxProb = Math.max(homeWinProbability, drawProbability, awayWinProbability);
    const minProb = Math.min(homeWinProbability, drawProbability, awayWinProbability);
    const diff = maxProb - minProb;
    
    // If all probabilities are close (within 5%), it's balanced
    if (diff < 5) return 'No dominant outcome';
    
    // If max is home and difference is small, weak home edge
    if (maxProb === homeWinProbability && diff < 10) return 'Weak home edge';
    
    // If max is away and difference is small, weak away edge
    if (maxProb === awayWinProbability && diff < 10) return 'Weak away edge';
    
    // Otherwise, there's a clear favorite
    return 'Clear favorite';
  };

  // Get clear favorite indicator (for cross-tab display)
  const getClearFavorite = (prob: FixtureProbability): { favorite: 'H' | 'D' | 'A' | null; strength: 'strong' | 'weak' | null } => {
    const { homeWinProbability, drawProbability, awayWinProbability } = prob;
    const maxProb = Math.max(homeWinProbability, drawProbability, awayWinProbability);
    const minProb = Math.min(homeWinProbability, drawProbability, awayWinProbability);
    const diff = maxProb - minProb;
    
    // If all probabilities are close (within 5%), no clear favorite
    if (diff < 5) return { favorite: null, strength: null };
    
    // Determine which is the favorite
    let favorite: 'H' | 'D' | 'A' | null = null;
    if (maxProb === homeWinProbability) favorite = 'H';
    else if (maxProb === drawProbability) favorite = 'D';
    else if (maxProb === awayWinProbability) favorite = 'A';
    
    // Determine strength (strong if diff >= 10, weak if diff < 10)
    const strength: 'strong' | 'weak' | null = diff >= 10 ? 'strong' : 'weak';
    
    return { favorite, strength };
  };

  const formatProbability = (value: number) => {
    // Values are already percentages (0-100 range)
    // Show 2 decimal places by default, but use more precision for very small values
    if (value < 0.1) return value.toFixed(4);
    if (value < 1) return value.toFixed(3);
    // For normal percentages, show 2 decimal places
    return value.toFixed(2);
  };
  
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
    <PageLayout
      title="Probability Sets Comparison"
      description="Compare 10 different probability estimation approaches (A-J)"
      icon={<Scale className="h-6 w-6" />}
    >
        <div className="flex items-center gap-4">
          {/* Jackpot Selector */}
          <div className="flex items-center gap-2">
            <Label htmlFor="jackpot-select" className="text-sm whitespace-nowrap">
              Jackpot:
            </Label>
            <Select
              value={jackpotId || ''}
              onValueChange={(value) => {
                const params = new URLSearchParams(searchParams);
                if (value) {
                  params.set('jackpotId', value);
                } else {
                  params.delete('jackpotId');
                }
                setSearchParams(params, { replace: true });
              }}
              disabled={loadingJackpots}
            >
              <SelectTrigger id="jackpot-select" className="w-[250px]">
                <SelectValue placeholder={loadingJackpots ? "Loading..." : "Select jackpot"} />
              </SelectTrigger>
              <SelectContent>
                {allJackpots.length === 0 ? (
                  <div className="px-2 py-1.5 text-sm text-muted-foreground">
                    No jackpots available
                  </div>
                ) : (
                  allJackpots.map((jackpot) => (
                    <SelectItem key={jackpot.id} value={jackpot.id}>
                      {jackpot.name} ({new Date(jackpot.createdAt).toLocaleDateString()})
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
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

      {/* Set Selection & Explanations */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {setsToUse.map((set) => {
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
            <div className="p-3 rounded-lg bg-background/50">
              <span className="text-primary font-bold">Set H:</span>
              <span className="text-muted-foreground ml-2">P_X' = 0.7×P_X(B) + 0.3×O_X</span>
            </div>
            <div className="p-3 rounded-lg bg-background/50">
              <span className="text-primary font-bold">Set I:</span>
              <span className="text-muted-foreground ml-2">P_X' = P_X(A)×f(entropy,spread)</span>
            </div>
            <div className="p-3 rounded-lg bg-background/50 md:col-span-2">
              <span className="text-primary font-bold">Set J:</span>
              <span className="text-muted-foreground ml-2">P_X' = P_X(G)×strategy(λ_h,λ_a) [1.05x-1.25x]</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Outcome Type Summary */}
      {!showDelta && (
        <Card className="glass-card bg-primary/5 border-primary/20">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary" />
              Overall Outcome Dominance
            </CardTitle>
            <CardDescription>
              Which outcome type has the highest probabilities across all sets and fixtures
            </CardDescription>
          </CardHeader>
          <CardContent>
            {useMemo(() => {
              // Calculate average probabilities for each outcome type across all fixtures and sets
              let totalHome = 0;
              let totalDraw = 0;
              let totalAway = 0;
              let count = 0;

              baseSet.probabilities.forEach((baseProbability) => {
                visibleSets.forEach(set => {
                  const prob = set.probabilities.find(p => p.fixtureId === baseProbability.fixtureId);
                  if (prob) {
                    totalHome += prob.homeWinProbability || 0;
                    totalDraw += prob.drawProbability || 0;
                    totalAway += prob.awayWinProbability || 0;
                    count++;
                  }
                });
              });

              const avgHome = count > 0 ? totalHome / count : 0;
              const avgDraw = count > 0 ? totalDraw / count : 0;
              const avgAway = count > 0 ? totalAway / count : 0;

              const maxAvg = Math.max(avgHome, avgDraw, avgAway);
              const winner = maxAvg === avgHome ? 'Home' : maxAvg === avgDraw ? 'Draw' : 'Away';

              return (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className={`p-4 rounded-lg border-2 ${
                    winner === 'Home' 
                      ? 'bg-blue-500/20 border-blue-500/50' 
                      : 'bg-background/50 border-border'
                  }`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-muted-foreground">Home Win</span>
                      {winner === 'Home' && <span className="text-blue-600 dark:text-blue-400 text-xs">★ Highest</span>}
                    </div>
                    <div className={`text-2xl font-bold ${
                      winner === 'Home' ? 'text-blue-600 dark:text-blue-400' : 'text-foreground'
                    }`}>
                      {formatProbability(avgHome)}%
                    </div>
                  </div>
                  <div className={`p-4 rounded-lg border-2 ${
                    winner === 'Draw' 
                      ? 'bg-purple-500/20 border-purple-500/50' 
                      : 'bg-background/50 border-border'
                  }`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-muted-foreground">Draw</span>
                      {winner === 'Draw' && <span className="text-purple-600 dark:text-purple-400 text-xs">★ Highest</span>}
                    </div>
                    <div className={`text-2xl font-bold ${
                      winner === 'Draw' ? 'text-purple-600 dark:text-purple-400' : 'text-foreground'
                    }`}>
                      {formatProbability(avgDraw)}%
                    </div>
                  </div>
                  <div className={`p-4 rounded-lg border-2 ${
                    winner === 'Away' 
                      ? 'bg-green-500/20 border-green-500/50' 
                      : 'bg-background/50 border-border'
                  }`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-muted-foreground">Away Win</span>
                      {winner === 'Away' && <span className="text-green-600 dark:text-green-400 text-xs">★ Highest</span>}
                    </div>
                    <div className={`text-2xl font-bold ${
                      winner === 'Away' ? 'text-green-600 dark:text-green-400' : 'text-foreground'
                    }`}>
                      {formatProbability(avgAway)}%
                    </div>
                  </div>
                </div>
              );
            }, [baseSet, visibleSets, showDelta, formatProbability])}
          </CardContent>
        </Card>
      )}

      {/* Comparison Table */}
      <Card className="glass-card">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg">Side-by-Side Comparison</CardTitle>
          <CardDescription>
            {showDelta 
              ? 'Showing differences relative to Set A (Pure Model)'
              : 'Showing absolute probabilities for each selected set. ★ indicates highest probability in row.'
            }
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="home" className="w-full">
            <TabsList className="grid grid-cols-4 w-full max-w-lg">
              <TabsTrigger value="home">Home Win %</TabsTrigger>
              <TabsTrigger value="draw">Draw %</TabsTrigger>
              <TabsTrigger value="away">Away Win %</TabsTrigger>
              <TabsTrigger value="actual">Actual Results</TabsTrigger>
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
                      {Object.keys(actualResults).length > 0 && (
                        <TableHead className="text-center w-[100px]">
                          <Tooltip>
                            <TooltipTrigger className="flex items-center justify-center gap-1 cursor-help">
                              <Badge variant="outline" className="text-xs">Actual</Badge>
                            </TooltipTrigger>
                            <TooltipContent>Actual match results from saved data</TooltipContent>
                          </Tooltip>
                        </TableHead>
                      )}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {baseSet.probabilities.map((baseProbability) => {
                      const actualResult = actualResults[baseProbability.fixtureId];
                      const entropy = calculateEntropy(baseProbability);
                      const entropyLevel = getEntropyLevel(entropy);
                      const dominance = getDominanceIndicator(baseProbability);
                      const clearFavorite = getClearFavorite(baseProbability);
                      
                      // Find max value across all sets for this fixture (for highlighting)
                      const homeValues = visibleSets.map(set => {
                        const prob = set.probabilities.find(p => p.fixtureId === baseProbability.fixtureId);
                        return prob?.homeWinProbability || 0;
                      });
                      const maxHomeValue = Math.max(...homeValues);
                      
                      return (
                        <TableRow key={baseProbability.fixtureId} className="hover:bg-primary/5">
                          <TableCell className="font-medium sticky left-0 bg-card">
                            <div className="flex flex-col gap-1">
                              <span>{baseProbability.homeTeam} vs {baseProbability.awayTeam}</span>
                              <div className="flex items-center gap-2 flex-wrap">
                                <Badge 
                                  variant="outline" 
                                  className={`text-xs ${
                                    entropyLevel === 'HIGH' ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/50' :
                                    entropyLevel === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border-yellow-500/50' :
                                    'bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/50'
                                  }`}
                                >
                                  {entropyLevel} UNCERTAINTY
                                </Badge>
                                <span className="text-xs text-muted-foreground">{dominance}</span>
                                {clearFavorite.favorite && clearFavorite.favorite !== 'H' && (
                                  <Badge 
                                    variant="outline" 
                                    className={`text-xs ${
                                      clearFavorite.favorite === 'D' 
                                        ? 'bg-purple-500/20 text-purple-600 dark:text-purple-400 border-purple-500/50' 
                                        : 'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/50'
                                    }`}
                                  >
                                    {clearFavorite.favorite === 'D' ? 'Draw' : 'Away'} {clearFavorite.strength === 'strong' ? 'favored' : 'slight edge'}
                                  </Badge>
                                )}
                              </div>
                            </div>
                          </TableCell>
                          {visibleSets.map(set => {
                            const prob = set.probabilities.find(p => p.fixtureId === baseProbability.fixtureId);
                            const value = prob?.homeWinProbability || 0;
                            const baseValue = baseProbability.homeWinProbability;
                            const predicted = prob ? getHighestProbOutcome(prob) : null;
                            const isCorrect = actualResult && predicted === actualResult;
                            const isMax = !showDelta && Math.abs(value - maxHomeValue) < 0.01;
                            
                            return (
                              <TableCell 
                                key={set.id} 
                                className={`text-right tabular-nums ${isMax ? 'bg-primary/20 font-semibold' : ''}`}
                              >
                                {showDelta && set.id !== 'A' ? (
                                  <span className={getDeltaColor(value, baseValue)}>
                                    {formatDelta(value, baseValue)}
                                  </span>
                                ) : (
                                  <div className="flex items-center justify-end gap-1">
                                    <span className={isMax ? 'text-primary font-bold' : ''}>{formatProbability(value)}%</span>
                                    {isMax && <span className="text-primary text-xs">★</span>}
                                    {actualResult && predicted === '1' && (
                                      <span className={isCorrect ? 'text-green-600' : 'text-red-600'}>
                                        {isCorrect ? '✓' : '✗'}
                                      </span>
                                    )}
                                  </div>
                                )}
                              </TableCell>
                            );
                          })}
                          {Object.keys(actualResults).length > 0 && (
                            <TableCell className="text-center">
                              {actualResult ? (
                                <Badge 
                                  variant="outline" 
                                  className={`text-sm font-bold ${
                                    actualResult === '1' ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/50' :
                                    actualResult === 'X' ? 'bg-purple-500/20 text-purple-600 dark:text-purple-400 border-purple-500/50' :
                                    'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/50'
                                  }`}
                                >
                                  {actualResult}
                                </Badge>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </TableCell>
                          )}
                        </TableRow>
                      );
                    })}
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
                      {Object.keys(actualResults).length > 0 && (
                        <TableHead className="text-center w-[100px]">
                          <Badge variant="outline" className="text-xs">Actual</Badge>
                        </TableHead>
                      )}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {baseSet.probabilities.map((baseProbability) => {
                      const actualResult = actualResults[baseProbability.fixtureId];
                      const entropy = calculateEntropy(baseProbability);
                      const entropyLevel = getEntropyLevel(entropy);
                      const dominance = getDominanceIndicator(baseProbability);
                      const clearFavorite = getClearFavorite(baseProbability);
                      
                      // Find max value across all sets for this fixture (for highlighting)
                      const drawValues = visibleSets.map(set => {
                        const prob = set.probabilities.find(p => p.fixtureId === baseProbability.fixtureId);
                        return prob?.drawProbability || 0;
                      });
                      const maxDrawValue = Math.max(...drawValues);
                      
                      return (
                        <TableRow key={baseProbability.fixtureId} className="hover:bg-primary/5">
                          <TableCell className="font-medium sticky left-0 bg-card">
                            <div className="flex flex-col gap-1">
                              <span>{baseProbability.homeTeam} vs {baseProbability.awayTeam}</span>
                              <div className="flex items-center gap-2 flex-wrap">
                                <Badge 
                                  variant="outline" 
                                  className={`text-xs ${
                                    entropyLevel === 'HIGH' ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/50' :
                                    entropyLevel === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border-yellow-500/50' :
                                    'bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/50'
                                  }`}
                                >
                                  {entropyLevel} UNCERTAINTY
                                </Badge>
                                <span className="text-xs text-muted-foreground">{dominance}</span>
                                {clearFavorite.favorite && clearFavorite.favorite !== 'D' && (
                                  <Badge 
                                    variant="outline" 
                                    className={`text-xs ${
                                      clearFavorite.favorite === 'H' 
                                        ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/50' 
                                        : 'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/50'
                                    }`}
                                  >
                                    {clearFavorite.favorite === 'H' ? 'Home' : 'Away'} {clearFavorite.strength === 'strong' ? 'favored' : 'slight edge'}
                                  </Badge>
                                )}
                              </div>
                            </div>
                          </TableCell>
                          {visibleSets.map(set => {
                            const prob = set.probabilities.find(p => p.fixtureId === baseProbability.fixtureId);
                            const value = prob?.drawProbability || 0;
                            const baseValue = baseProbability.drawProbability;
                            const predicted = prob ? getHighestProbOutcome(prob) : null;
                            const isCorrect = actualResult && predicted === actualResult;
                            const isMax = !showDelta && Math.abs(value - maxDrawValue) < 0.01;
                            
                            return (
                              <TableCell 
                                key={set.id} 
                                className={`text-right tabular-nums ${isMax ? 'bg-purple-500/20 font-semibold' : ''}`}
                              >
                                {showDelta && set.id !== 'A' ? (
                                  <span className={getDeltaColor(value, baseValue)}>
                                    {formatDelta(value, baseValue)}
                                  </span>
                                ) : (
                                  <div className="flex items-center justify-end gap-1">
                                    <span className={isMax ? 'text-purple-600 dark:text-purple-400 font-bold' : ''}>{formatProbability(value)}%</span>
                                    {isMax && <span className="text-purple-600 dark:text-purple-400 text-xs">★</span>}
                                    {actualResult && predicted === 'X' && (
                                      <span className={isCorrect ? 'text-green-600' : 'text-red-600'}>
                                        {isCorrect ? '✓' : '✗'}
                                      </span>
                                    )}
                                  </div>
                                )}
                              </TableCell>
                            );
                          })}
                          {Object.keys(actualResults).length > 0 && (
                            <TableCell className="text-center">
                              {actualResult ? (
                                <Badge 
                                  variant="outline" 
                                  className={`text-sm font-bold ${
                                    actualResult === '1' ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/50' :
                                    actualResult === 'X' ? 'bg-purple-500/20 text-purple-600 dark:text-purple-400 border-purple-500/50' :
                                    'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/50'
                                  }`}
                                >
                                  {actualResult}
                                </Badge>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </TableCell>
                          )}
                        </TableRow>
                      );
                    })}
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
                      {Object.keys(actualResults).length > 0 && (
                        <TableHead className="text-center w-[100px]">
                          <Badge variant="outline" className="text-xs">Actual</Badge>
                        </TableHead>
                      )}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {baseSet.probabilities.map((baseProbability) => {
                      const actualResult = actualResults[baseProbability.fixtureId];
                      const entropy = calculateEntropy(baseProbability);
                      const entropyLevel = getEntropyLevel(entropy);
                      const dominance = getDominanceIndicator(baseProbability);
                      const clearFavorite = getClearFavorite(baseProbability);
                      
                      // Find max value across all sets for this fixture (for highlighting)
                      const awayValues = visibleSets.map(set => {
                        const prob = set.probabilities.find(p => p.fixtureId === baseProbability.fixtureId);
                        return prob?.awayWinProbability || 0;
                      });
                      const maxAwayValue = Math.max(...awayValues);
                      
                      return (
                        <TableRow key={baseProbability.fixtureId} className="hover:bg-primary/5">
                          <TableCell className="font-medium sticky left-0 bg-card">
                            <div className="flex flex-col gap-1">
                              <span>{baseProbability.homeTeam} vs {baseProbability.awayTeam}</span>
                              <div className="flex items-center gap-2 flex-wrap">
                                <Badge 
                                  variant="outline" 
                                  className={`text-xs ${
                                    entropyLevel === 'HIGH' ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/50' :
                                    entropyLevel === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border-yellow-500/50' :
                                    'bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/50'
                                  }`}
                                >
                                  {entropyLevel} UNCERTAINTY
                                </Badge>
                                <span className="text-xs text-muted-foreground">{dominance}</span>
                                {clearFavorite.favorite && clearFavorite.favorite !== 'A' && (
                                  <Badge 
                                    variant="outline" 
                                    className={`text-xs ${
                                      clearFavorite.favorite === 'H' 
                                        ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/50' 
                                        : 'bg-purple-500/20 text-purple-600 dark:text-purple-400 border-purple-500/50'
                                    }`}
                                  >
                                    {clearFavorite.favorite === 'H' ? 'Home' : 'Draw'} {clearFavorite.strength === 'strong' ? 'favored' : 'slight edge'}
                                  </Badge>
                                )}
                              </div>
                            </div>
                          </TableCell>
                          {visibleSets.map(set => {
                            const prob = set.probabilities.find(p => p.fixtureId === baseProbability.fixtureId);
                            const value = prob?.awayWinProbability || 0;
                            const baseValue = baseProbability.awayWinProbability;
                            const predicted = prob ? getHighestProbOutcome(prob) : null;
                            const isCorrect = actualResult && predicted === actualResult;
                            const isMax = !showDelta && Math.abs(value - maxAwayValue) < 0.01;
                            
                            return (
                              <TableCell 
                                key={set.id} 
                                className={`text-right tabular-nums ${isMax ? 'bg-green-500/20 font-semibold' : ''}`}
                              >
                                {showDelta && set.id !== 'A' ? (
                                  <span className={getDeltaColor(value, baseValue)}>
                                    {formatDelta(value, baseValue)}
                                  </span>
                                ) : (
                                  <div className="flex items-center justify-end gap-1">
                                    <span className={isMax ? 'text-green-600 dark:text-green-400 font-bold' : ''}>{formatProbability(value)}%</span>
                                    {isMax && <span className="text-green-600 dark:text-green-400 text-xs">★</span>}
                                    {actualResult && predicted === '2' && (
                                      <span className={isCorrect ? 'text-green-600' : 'text-red-600'}>
                                        {isCorrect ? '✓' : '✗'}
                                      </span>
                                    )}
                                  </div>
                                )}
                              </TableCell>
                            );
                          })}
                          {Object.keys(actualResults).length > 0 && (
                            <TableCell className="text-center">
                              {actualResult ? (
                                <Badge 
                                  variant="outline" 
                                  className={`text-sm font-bold ${
                                    actualResult === '1' ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/50' :
                                    actualResult === 'X' ? 'bg-purple-500/20 text-purple-600 dark:text-purple-400 border-purple-500/50' :
                                    'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/50'
                                  }`}
                                >
                                  {actualResult}
                                </Badge>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </TableCell>
                          )}
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>

            {/* Actual Results Tab */}
            <TabsContent value="actual" className="mt-4">
              {Object.keys(actualResults).length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Info className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No actual results available.</p>
                  <p className="text-sm mt-2">
                    {jackpotId 
                      ? 'Enter actual results in the Probability Output page and save them to see them here.'
                      : 'Navigate to Probability Output page with a jackpot ID to load saved results.'}
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="sticky left-0 bg-card">Fixture</TableHead>
                        {visibleSets.map(set => (
                          <TableHead key={set.id} className="text-center w-[100px]">
                            <Badge variant="outline" className="text-xs">{set.id}</Badge>
                          </TableHead>
                        ))}
                        <TableHead className="text-center w-[100px]">Actual</TableHead>
                        <TableHead className="text-center w-[100px]">Accuracy</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {baseSet.probabilities.map((baseProbability) => {
                        const actualResult = actualResults[baseProbability.fixtureId];
                        if (!actualResult) return null;
                        
                        const entropy = calculateEntropy(baseProbability);
                        const entropyLevel = getEntropyLevel(entropy);
                        const dominance = getDominanceIndicator(baseProbability);
                        
                        return (
                          <TableRow key={baseProbability.fixtureId} className="hover:bg-primary/5">
                            <TableCell className="font-medium sticky left-0 bg-card">
                              <div className="flex flex-col gap-1">
                                <span>{baseProbability.homeTeam} vs {baseProbability.awayTeam}</span>
                                <div className="flex items-center gap-2 flex-wrap">
                                  <Badge 
                                    variant="outline" 
                                    className={`text-xs ${
                                      entropyLevel === 'HIGH' ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/50' :
                                      entropyLevel === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border-yellow-500/50' :
                                      'bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/50'
                                    }`}
                                  >
                                    {entropyLevel} UNCERTAINTY
                                  </Badge>
                                  <span className="text-xs text-muted-foreground">{dominance}</span>
                                </div>
                              </div>
                            </TableCell>
                            {visibleSets.map(set => {
                              const prob = set.probabilities.find(p => p.fixtureId === baseProbability.fixtureId);
                              const predicted = prob ? getHighestProbOutcome(prob) : null;
                              const isCorrect = predicted === actualResult;
                              
                              return (
                                <TableCell key={set.id} className="text-center">
                                  {predicted ? (
                                    <div className="flex flex-col items-center gap-1">
                                      <Badge 
                                        variant="outline" 
                                        className={`text-sm font-bold ${
                                          predicted === '1' ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/50' :
                                          predicted === 'X' ? 'bg-purple-500/20 text-purple-600 dark:text-purple-400 border-purple-500/50' :
                                          'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/50'
                                        }`}
                                      >
                                        {predicted}
                                      </Badge>
                                      {isCorrect ? (
                                        <CheckCircle className="h-4 w-4 text-green-600" />
                                      ) : (
                                        <XCircle className="h-4 w-4 text-red-600" />
                                      )}
                                    </div>
                                  ) : (
                                    <span className="text-muted-foreground">—</span>
                                  )}
                                </TableCell>
                              );
                            })}
                            <TableCell className="text-center">
                              <Badge 
                                variant="outline" 
                                className={`text-sm font-bold ${
                                  actualResult === '1' ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/50' :
                                  actualResult === 'X' ? 'bg-purple-500/20 text-purple-600 dark:text-purple-400 border-purple-500/50' :
                                  'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/50'
                                }`}
                              >
                                {actualResult}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-center">
                              {visibleSets.map(set => {
                                const prob = set.probabilities.find(p => p.fixtureId === baseProbability.fixtureId);
                                const predicted = prob ? getHighestProbOutcome(prob) : null;
                                return predicted === actualResult;
                              }).some(correct => correct) ? (
                                <Badge variant="outline" className="bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/50">
                                  {visibleSets.filter(set => {
                                    const prob = set.probabilities.find(p => p.fixtureId === baseProbability.fixtureId);
                                    return prob && getHighestProbOutcome(prob) === actualResult;
                                  }).length}/{visibleSets.length}
                                </Badge>
                              ) : (
                                <Badge variant="outline" className="bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/50">
                                  0/{visibleSets.length}
                                </Badge>
                              )}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
      
      {loading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <span className="ml-2 text-muted-foreground">Loading probabilities...</span>
        </div>
      )}
    </PageLayout>
  );
}
