import { useState, useMemo, useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  Ticket, 
  Plus, 
  Trash2, 
  Copy, 
  Download, 
  CheckCircle, 
  AlertTriangle,
  HelpCircle,
  Calculator,
  Layers,
  Target,
  TrendingUp,
  Zap,
  Scale,
  Users,
  Sparkles,
  Loader2
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/services/api';

// Probability set configurations
const probabilitySets = {
  A: { name: 'Pure Model', icon: Calculator, risk: 'Medium', color: 'text-chart-1' },
  B: { name: 'Balanced', icon: Scale, risk: 'Medium-Low', color: 'text-primary' },
  C: { name: 'Conservative', icon: Target, risk: 'Low', color: 'text-status-stable' },
  D: { name: 'Draw-Boosted', icon: TrendingUp, risk: 'Medium', color: 'text-chart-3' },
  E: { name: 'High Conviction', icon: Zap, risk: 'Medium-High', color: 'text-status-watch' },
  F: { name: 'Kelly-Weighted', icon: Calculator, risk: 'High', color: 'text-chart-5' },
  G: { name: 'Ensemble', icon: Users, risk: 'Low', color: 'text-chart-4' },
};

// Helper function to get highest probability outcome
const getHighestProbOutcome = (homeProb: number, drawProb: number, awayProb: number): '1' | 'X' | '2' => {
  if (homeProb >= drawProb && homeProb >= awayProb) return '1';
  if (awayProb >= homeProb && awayProb >= drawProb) return '2';
  return 'X';
};

type SetKey = keyof typeof probabilitySets;
type Pick = '1' | 'X' | '2';

interface GeneratedTicket {
  id: string;
  setKey: SetKey;
  picks: Pick[];
  probability: number;
  combinedOdds: number;
}

export default function TicketConstruction() {
  const [searchParams] = useSearchParams();
  const jackpotId = searchParams.get('jackpotId');
  const [selectedSets, setSelectedSets] = useState<SetKey[]>(['B']);
  const [budget, setBudget] = useState<number>(500);
  const [tickets, setTickets] = useState<GeneratedTicket[]>([]);
  const [loading, setLoading] = useState(false);
  const [fixtureData, setFixtureData] = useState<Array<{
    id: string;
    home: string;
    away: string;
    sets: Record<string, '1' | 'X' | '2'>;
    odds?: { home: number; draw: number; away: number };
  }>>([]);
  const [loadedSets, setLoadedSets] = useState<Record<string, any>>({});
  const [savedResults, setSavedResults] = useState<any[]>([]);
  const { toast } = useToast();

  // Load probabilities and saved results
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        let targetJackpotId = jackpotId;
        
        // If no jackpotId, try to get from latest saved result
        if (!targetJackpotId) {
          const latestResponse = await apiClient.getLatestSavedResult();
          if (latestResponse.success && latestResponse.data?.result?.jackpotId) {
            targetJackpotId = latestResponse.data.result.jackpotId;
          }
        }
        
        if (targetJackpotId) {
          // Load probabilities
          const probResponse = await apiClient.getProbabilities(targetJackpotId);
          const probData = (probResponse as any).success ? (probResponse as any).data : probResponse;
          
          // Declare transformedSets in outer scope so it's available in both blocks
          let transformedSets: Record<string, any> = {};
          
          if (probData && probData.probabilitySets && probData.fixtures) {
            transformedSets = {};
            Object.keys(probData.probabilitySets).forEach(setId => {
              const setProbs = probData.probabilitySets[setId];
              transformedSets[setId] = {
                probabilities: setProbs.map((prob: any, idx: number) => ({
                  fixtureId: probData.fixtures[idx]?.id || String(idx + 1),
                  homeTeam: probData.fixtures[idx]?.homeTeam || '',
                  awayTeam: probData.fixtures[idx]?.awayTeam || '',
                  odds: probData.fixtures[idx]?.odds || { home: 2.0, draw: 3.0, away: 2.5 },
                  homeWinProbability: prob.homeWinProbability || 0,
                  drawProbability: prob.drawProbability || 0,
                  awayWinProbability: prob.awayWinProbability || 0,
                })),
              };
            });
            setLoadedSets(transformedSets);
            
            // Build fixture data with picks from probabilities
            const fixtures = probData.fixtures || [];
            const fixtureDataWithPicks = fixtures.map((fixture: any, idx: number) => {
              const sets: Record<string, '1' | 'X' | '2'> = {};
              Object.keys(transformedSets).forEach(setId => {
                const prob = transformedSets[setId].probabilities[idx];
                if (prob) {
                  sets[setId] = getHighestProbOutcome(
                    prob.homeWinProbability / 100,
                    prob.drawProbability / 100,
                    prob.awayWinProbability / 100
                  );
                }
              });
              return {
                id: fixture.id || String(idx + 1),
                home: fixture.homeTeam || '',
                away: fixture.awayTeam || '',
                sets,
                odds: fixture.odds || { home: 2.0, draw: 3.0, away: 2.5 },
              };
            });
            setFixtureData(fixtureDataWithPicks);
          }
          
          // Load saved results to get actual selections
          const savedResponse = await apiClient.getSavedResults(targetJackpotId);
          if (savedResponse.success && savedResponse.data?.results) {
            setSavedResults(savedResponse.data.results);
            
            // If we have saved selections, use those instead of highest probability
            if (savedResponse.data.results.length > 0 && savedResponse.data.results[0].selections && probData && probData.fixtures) {
              const latestResult = savedResponse.data.results[0];
              const fixtures = probData.fixtures || [];
              const fixtureDataWithSelections = fixtures.map((fixture: any, idx: number) => {
                const sets: Record<string, '1' | 'X' | '2'> = {};
                
                // First, try to get selections from saved results (user picks)
                Object.keys(latestResult.selections || {}).forEach(setId => {
                  const setSelections = latestResult.selections[setId];
                  const fixtureId = fixture.id || String(idx + 1);
                  
                  // Check by fixture ID first
                  if (setSelections && setSelections[fixtureId]) {
                    sets[setId] = setSelections[fixtureId] as '1' | 'X' | '2';
                  } else {
                    // Try by index if ID doesn't match
                    const selectionEntries = Object.entries(setSelections || {});
                    if (idx < selectionEntries.length) {
                      sets[setId] = selectionEntries[idx][1] as '1' | 'X' | '2';
                    } else {
                      // Fallback to highest probability only if no selection exists
                      const prob = transformedSets[setId]?.probabilities?.[idx];
                      if (prob) {
                        sets[setId] = getHighestProbOutcome(
                          prob.homeWinProbability / 100,
                          prob.drawProbability / 100,
                          prob.awayWinProbability / 100
                        );
                      }
                    }
                  }
                });
                
                // Fill in any missing sets with highest probability
                Object.keys(transformedSets).forEach(setId => {
                  if (!sets[setId]) {
                    const prob = transformedSets[setId]?.probabilities?.[idx];
                    if (prob) {
                      sets[setId] = getHighestProbOutcome(
                        prob.homeWinProbability / 100,
                        prob.drawProbability / 100,
                        prob.awayWinProbability / 100
                      );
                    }
                  }
                });
                
                return {
                  id: fixture.id || String(idx + 1),
                  home: fixture.homeTeam || '',
                  away: fixture.awayTeam || '',
                  sets,
                  odds: fixture.odds || { home: 2.0, draw: 3.0, away: 2.5 },
                };
              });
              setFixtureData(fixtureDataWithSelections);
            }
          }
        } else {
          // Use mock data if no jackpotId found
          setFixtureData([
            { id: '1', home: 'Gillingham', away: 'Cambridge', sets: { A: '1', B: '1', C: '1', D: 'X', E: '1', F: '1', G: '1' }, odds: { home: 2.0, draw: 3.0, away: 2.5 } },
            { id: '2', home: 'AFC Wimbledon', away: 'Crawley', sets: { A: 'X', B: '1', C: '1', D: 'X', E: '1', F: '1', G: '1' }, odds: { home: 2.2, draw: 3.2, away: 2.8 } },
            { id: '3', home: 'Cheltenham', away: 'Walsall', sets: { A: '1', B: '1', C: '2', D: 'X', E: '2', F: '2', G: '1' }, odds: { home: 2.1, draw: 3.1, away: 2.9 } },
            { id: '4', home: 'Blackpool', away: 'Doncaster', sets: { A: '1', B: '1', C: '1', D: '1', E: '1', F: '1', G: '1' }, odds: { home: 1.9, draw: 3.3, away: 3.1 } },
            { id: '5', home: 'Burton', away: 'Accrington', sets: { A: '1', B: '1', C: '1', D: 'X', E: '1', F: '1', G: '1' }, odds: { home: 2.0, draw: 3.2, away: 2.7 } },
            { id: '6', home: 'Chesterfield', away: 'Harrogate', sets: { A: '1', B: '1', C: '1', D: '1', E: '1', F: '1', G: '1' }, odds: { home: 1.8, draw: 3.4, away: 3.2 } },
            { id: '7', home: 'Plymouth', away: 'Luton', sets: { A: '1', B: 'X', C: '2', D: 'X', E: '2', F: '2', G: 'X' }, odds: { home: 2.3, draw: 3.0, away: 2.6 } },
            { id: '8', home: 'Portsmouth', away: 'Swansea', sets: { A: '2', B: '2', C: '2', D: 'X', E: '2', F: '2', G: '2' }, odds: { home: 2.5, draw: 3.1, away: 2.4 } },
            { id: '9', home: 'Peterborough', away: 'Northampton', sets: { A: '1', B: '1', C: '1', D: '1', E: '1', F: '1', G: '1' }, odds: { home: 1.9, draw: 3.3, away: 3.1 } },
            { id: '10', home: 'Chippenham', away: 'Taunton', sets: { A: '1', B: '2', C: '2', D: 'X', E: '2', F: '2', G: '2' }, odds: { home: 2.4, draw: 3.2, away: 2.3 } },
            { id: '11', home: 'Salisbury', away: 'Frome', sets: { A: '1', B: '1', C: '1', D: '1', E: '1', F: '1', G: '1' }, odds: { home: 2.0, draw: 3.0, away: 2.8 } },
            { id: '12', home: 'Eastleigh', away: 'Woking', sets: { A: '1', B: '1', C: '1', D: 'X', E: '1', F: '1', G: '1' }, odds: { home: 2.1, draw: 3.1, away: 2.9 } },
            { id: '13', home: 'Telford', away: 'Kidderminster', sets: { A: '1', B: '1', C: 'X', D: 'X', E: '1', F: '1', G: '1' }, odds: { home: 2.2, draw: 3.0, away: 2.7 } },
          ]);
        }
      } catch (err: any) {
        console.error('Error loading ticket data:', err);
        toast({
          title: 'Warning',
          description: 'Could not load probability data. Using mock data.',
          variant: 'destructive',
        });
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, [jackpotId, toast]);

  // Generate tickets based on selected sets
  const generateTickets = useCallback(() => {
    if (fixtureData.length === 0) {
      toast({
        title: 'Error',
        description: 'No fixture data available. Please ensure probabilities are loaded.',
        variant: 'destructive',
      });
      return;
    }

    const newTickets: GeneratedTicket[] = selectedSets.map((setKey, idx) => {
      const picks = fixtureData.map(f => f.sets[setKey] as Pick).filter(p => p !== undefined);
      
      if (picks.length === 0) {
        return null;
      }
      
      // Calculate actual probability and odds from loaded data
      let probability = 1;
      let combinedOdds = 1;
      
      fixtureData.forEach((fixture, fixtureIdx) => {
        const pick = picks[fixtureIdx];
        if (!pick) return;
        
        // Get probability from loaded sets if available
        if (loadedSets[setKey]?.probabilities?.[fixtureIdx]) {
          const prob = loadedSets[setKey].probabilities[fixtureIdx];
          const pickProb = pick === '1' ? prob.homeWinProbability / 100 :
                          pick === 'X' ? prob.drawProbability / 100 :
                          prob.awayWinProbability / 100;
          probability *= pickProb;
        } else {
          // Fallback to mock calculation
          const base = pick === '1' ? 0.45 : pick === 'X' ? 0.28 : 0.35;
          probability *= base;
        }
        
        // Get odds from fixture data
        if (fixture.odds) {
          const pickOdds = pick === '1' ? fixture.odds.home :
                          pick === 'X' ? fixture.odds.draw :
                          fixture.odds.away;
          combinedOdds *= pickOdds;
        } else {
          // Fallback to mock odds
          const base = pick === '1' ? 2.2 : pick === 'X' ? 3.3 : 2.8;
          combinedOdds *= base;
        }
      });

      return {
        id: `ticket-${setKey}-${Date.now()}-${idx}`,
        setKey,
        picks,
        probability: probability * 100,
        combinedOdds,
      };
    }).filter((ticket): ticket is GeneratedTicket => ticket !== null);

    setTickets(newTickets);
    toast({
      title: 'Tickets Generated',
      description: `${newTickets.length} tickets created using Sets ${selectedSets.join(', ')}`,
    });
  }, [selectedSets, fixtureData, loadedSets, toast]);

  // Coverage diagnostics
  const coverageDiagnostics = useMemo(() => {
    if (tickets.length === 0 || fixtureData.length === 0) return null;

    const totalPicks = fixtureData.length * tickets.length;
    let homePicks = 0;
    let drawPicks = 0;
    let awayPicks = 0;

    tickets.forEach(ticket => {
      ticket.picks.forEach(pick => {
        if (pick === '1') homePicks++;
        else if (pick === 'X') drawPicks++;
        else if (pick === '2') awayPicks++;
      });
    });

    // Check for overlap
    const pickStrings = tickets.map(t => t.picks.join(''));
    const uniqueTickets = new Set(pickStrings).size;
    const overlapWarning = uniqueTickets < tickets.length;

    return {
      homePct: totalPicks > 0 ? (homePicks / totalPicks) * 100 : 0,
      drawPct: totalPicks > 0 ? (drawPicks / totalPicks) * 100 : 0,
      awayPct: totalPicks > 0 ? (awayPicks / totalPicks) * 100 : 0,
      uniqueTickets,
      overlapWarning,
    };
  }, [tickets, fixtureData]);

  const addSet = (setKey: SetKey) => {
    if (!selectedSets.includes(setKey)) {
      setSelectedSets(prev => [...prev, setKey]);
    }
  };

  const removeSet = (setKey: SetKey) => {
    setSelectedSets(prev => prev.filter(s => s !== setKey));
  };

  const costPerTicket = budget / Math.max(selectedSets.length, 1);

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 glow-primary">
            <Ticket className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold gradient-text">Ticket Construction</h1>
            <p className="text-sm text-muted-foreground">
              Generate jackpot tickets using probability Sets A-G
            </p>
          </div>
        </div>
      </div>

      {/* Strategy Guide */}
      <Alert className="glass-card border-primary/20">
        <HelpCircle className="h-4 w-4 text-primary" />
        <AlertTitle>Ticket Strategy</AlertTitle>
        <AlertDescription>
          <strong>Rule:</strong> Use ONE probability set per ticket. Do NOT mix sets within a ticket.
          Diversify by generating multiple tickets from different sets.
        </AlertDescription>
      </Alert>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration Panel */}
        <div className="space-y-4">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Layers className="h-5 w-5 text-primary" />
                Select Probability Sets
              </CardTitle>
              <CardDescription>
                Choose which sets to generate tickets from
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-1 gap-2">
                {(Object.entries(probabilitySets) as [SetKey, typeof probabilitySets['A']][]).map(([key, set]) => {
                  const Icon = set.icon;
                  const isSelected = selectedSets.includes(key);
                  
                  return (
                    <button
                      key={key}
                      onClick={() => isSelected ? removeSet(key) : addSet(key)}
                      className={`flex items-center gap-3 p-3 rounded-lg border transition-all text-left ${
                        isSelected 
                          ? 'bg-primary/10 border-primary/50' 
                          : 'bg-muted/20 border-border/50 hover:border-primary/30'
                      }`}
                    >
                      <div className={`p-1.5 rounded-md ${isSelected ? 'bg-primary/20' : 'bg-muted/30'}`}>
                        <Icon className={`h-4 w-4 ${set.color}`} />
                      </div>
                      <div className="flex-1">
                        <div className="font-medium text-sm">Set {key} - {set.name}</div>
                        <div className="text-xs text-muted-foreground">Risk: {set.risk}</div>
                      </div>
                      {isSelected && <CheckCircle className="h-4 w-4 text-primary" />}
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="text-lg">Budget Allocation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Total Budget (KES)</Label>
                <Input
                  type="number"
                  value={budget}
                  onChange={(e) => setBudget(Number(e.target.value))}
                  className="bg-background/50"
                />
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Tickets to generate:</span>
                <span className="font-bold">{selectedSets.length}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Cost per ticket:</span>
                <span className="font-bold tabular-nums">KES {costPerTicket.toFixed(0)}</span>
              </div>
              <Button 
                onClick={generateTickets} 
                className="w-full btn-glow bg-primary text-primary-foreground"
                disabled={selectedSets.length === 0 || loading || fixtureData.length === 0}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Generate {selectedSets.length} Ticket{selectedSets.length !== 1 ? 's' : ''}
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Generated Tickets */}
        <div className="lg:col-span-2 space-y-4">
          {/* Coverage Diagnostics */}
          {coverageDiagnostics && (
            <Card className="glass-card">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Target className="h-5 w-5 text-accent" />
                  Coverage Diagnostics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="text-center p-3 rounded-lg bg-chart-1/10">
                    <div className="text-2xl font-bold text-chart-1 tabular-nums">
                      {coverageDiagnostics.homePct.toFixed(0)}%
                    </div>
                    <div className="text-xs text-muted-foreground">Home (1)</div>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-chart-3/10">
                    <div className="text-2xl font-bold text-chart-3 tabular-nums">
                      {coverageDiagnostics.drawPct.toFixed(0)}%
                    </div>
                    <div className="text-xs text-muted-foreground">Draw (X)</div>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-chart-2/10">
                    <div className="text-2xl font-bold text-chart-2 tabular-nums">
                      {coverageDiagnostics.awayPct.toFixed(0)}%
                    </div>
                    <div className="text-xs text-muted-foreground">Away (2)</div>
                  </div>
                </div>

                {coverageDiagnostics.overlapWarning && (
                  <Alert className="border-status-watch/50 bg-status-watch/10">
                    <AlertTriangle className="h-4 w-4 text-status-watch" />
                    <AlertDescription className="text-status-watch">
                      Some tickets have identical picks. Consider using more diverse sets.
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          )}

          {/* Tickets Table */}
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Ticket className="h-5 w-5 text-primary" />
                Generated Tickets ({tickets.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {tickets.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Ticket className="h-12 w-12 mx-auto mb-3 opacity-30" />
                  <p>Select probability sets and click Generate to create tickets</p>
                </div>
              ) : (
                <ScrollArea className="h-[400px]">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[60px]">Set</TableHead>
                        <TableHead>Picks</TableHead>
                        <TableHead className="text-right">Prob</TableHead>
                        <TableHead className="text-right">Odds</TableHead>
                        <TableHead className="w-[80px]"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {tickets.map((ticket) => {
                        const set = probabilitySets[ticket.setKey];
                        const Icon = set.icon;
                        
                        return (
                          <TableRow key={ticket.id}>
                            <TableCell>
                              <Badge variant="outline" className={`${set.color}`}>
                                <Icon className="h-3 w-3 mr-1" />
                                {ticket.setKey}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <div className="flex gap-0.5 flex-wrap">
                                {ticket.picks.map((pick, idx) => (
                                  <Badge 
                                    key={idx}
                                    variant="outline"
                                    className={`w-6 h-6 p-0 justify-center text-xs font-bold ${
                                      pick === '1' ? 'bg-chart-1/20 text-chart-1 border-chart-1/50' :
                                      pick === 'X' ? 'bg-chart-3/20 text-chart-3 border-chart-3/50' :
                                      'bg-chart-2/20 text-chart-2 border-chart-2/50'
                                    }`}
                                  >
                                    {pick}
                                  </Badge>
                                ))}
                              </div>
                            </TableCell>
                            <TableCell className="text-right tabular-nums text-sm">
                              {ticket.probability.toExponential(2)}
                            </TableCell>
                            <TableCell className="text-right tabular-nums font-medium">
                              {ticket.combinedOdds.toFixed(0)}
                            </TableCell>
                            <TableCell>
                              <div className="flex gap-1">
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button 
                                      size="icon" 
                                      variant="ghost" 
                                      className="h-7 w-7"
                                      onClick={() => {
                                        const picksString = ticket.picks.join('');
                                        navigator.clipboard.writeText(picksString);
                                        toast({
                                          title: 'Copied',
                                          description: 'Ticket picks copied to clipboard',
                                        });
                                      }}
                                    >
                                      <Copy className="h-3.5 w-3.5" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>Copy picks</TooltipContent>
                                </Tooltip>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button 
                                      size="icon" 
                                      variant="ghost" 
                                      className="h-7 w-7"
                                      onClick={() => {
                                        const csv = [
                                          ['Set', 'Picks', 'Probability', 'Combined Odds'],
                                          [
                                            ticket.setKey,
                                            ticket.picks.join(''),
                                            ticket.probability.toExponential(2),
                                            ticket.combinedOdds.toFixed(2)
                                          ]
                                        ].map(row => row.join(',')).join('\n');
                                        
                                        const blob = new Blob([csv], { type: 'text/csv' });
                                        const url = URL.createObjectURL(blob);
                                        const a = document.createElement('a');
                                        a.href = url;
                                        a.download = `ticket-${ticket.setKey}-${Date.now()}.csv`;
                                        a.click();
                                        URL.revokeObjectURL(url);
                                        
                                        toast({
                                          title: 'Downloaded',
                                          description: 'Ticket exported as CSV',
                                        });
                                      }}
                                    >
                                      <Download className="h-3.5 w-3.5" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>Export ticket</TooltipContent>
                                </Tooltip>
                              </div>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </ScrollArea>
              )}
            </CardContent>
          </Card>

          {/* Fixture Reference */}
          <Card className="glass-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm text-muted-foreground">Fixture Reference</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 text-xs">
                {fixtureData.map((fixture, idx) => (
                  <div key={fixture.id} className="flex items-center gap-1">
                    <span className="text-muted-foreground w-4">{idx + 1}.</span>
                    <span className="truncate">{fixture.home} v {fixture.away}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
