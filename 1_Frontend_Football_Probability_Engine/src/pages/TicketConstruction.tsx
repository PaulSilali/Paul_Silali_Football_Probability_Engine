import { useState, useMemo, useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { Jackpot, PaginatedResponse } from '@/types';
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
  Loader2,
  Save
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageLayout } from '@/components/layouts/PageLayout';
import { ModernCard } from '@/components/ui/modern-card';
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
  H: { name: 'Market Consensus Draw', icon: Layers, risk: 'Low', color: 'text-chart-2' },
  I: { name: 'Formula-Based Draw', icon: Sparkles, risk: 'Medium', color: 'text-chart-6' },
  J: { name: 'System-Selected Draw', icon: Target, risk: 'Medium-Low', color: 'text-primary' },
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
  ranking?: number; // Ranking from 1-10 (1 = highest probability)
}

export default function TicketConstruction() {
  const [searchParams, setSearchParams] = useSearchParams();
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
  const [allJackpots, setAllJackpots] = useState<Array<{id: string; name: string; createdAt: string}>>([]);
  const [loadingJackpots, setLoadingJackpots] = useState(false);
  const [savingTickets, setSavingTickets] = useState(false);
  const [saveTicketName, setSaveTicketName] = useState('');
  const [saveTicketDescription, setSaveTicketDescription] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [savedTicketsList, setSavedTicketsList] = useState<Array<{
    id: number;
    name: string;
    description: string | null;
    createdAt: string;
    selections: Record<string, Record<string, string>>;
  }>>([]);
  const [loadingSavedTickets, setLoadingSavedTickets] = useState(false);
  const [selectedSavedTicketId, setSelectedSavedTicketId] = useState<string>('');
  const { toast } = useToast();

  // Load all jackpots for dropdown
  useEffect(() => {
    const loadJackpots = async () => {
      try {
        setLoadingJackpots(true);
        // Request a large page size to get all jackpots (or at least 100)
        const response = await apiClient.getJackpots(1, 1000);
        const jackpotsData = response.data || [];
        
        if (jackpotsData.length > 0) {
          // Deduplicate by id (in case API returns duplicates)
          const jackpotMap = new Map<string, {id: string; name: string; createdAt: string}>();
          jackpotsData.forEach((j: any) => {
            if (!jackpotMap.has(j.id)) {
              jackpotMap.set(j.id, {
                id: j.id,
                name: j.name || `Jackpot ${j.id}`,
                createdAt: j.createdAt
              });
            }
          });
          
          const jackpots = Array.from(jackpotMap.values()).sort((a: any, b: any) => 
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

  // Function to load saved tickets (reusable)
  const loadSavedTickets = useCallback(async (targetJackpotId?: string) => {
    const idToLoad = targetJackpotId || jackpotId;
    if (!idToLoad) {
      setSavedTicketsList([]);
      return;
    }

    try {
      setLoadingSavedTickets(true);
      const response = await apiClient.getSavedResults(idToLoad);
      if (response.success && response.data?.results) {
        // Filter for ticket-like saved results (those with selections that look like tickets)
        const ticketResults = response.data.results.filter((result: any) => {
          const selections = result.selections || {};
          const setKeys = Object.keys(selections);
          if (setKeys.length === 0) return false;
          
          // Check for new format: {"ticket-0": {"setKey": "B", "1": "1", "2": "X"}, ...}
          const isNewFormat = setKeys.some(key => key.startsWith('ticket-'));
          if (isNewFormat) {
            const firstTicket = selections[setKeys[0]] || {};
            const firstTicketKeys = Object.keys(firstTicket).filter(k => k !== 'setKey');
            return firstTicketKeys.length > 0 && firstTicketKeys.every(k => /^\d+$/.test(k));
          }
          
          // Check for old format: {"A": {"1": "1", "2": "X"}, "B": {...}}
          const firstSet = selections[setKeys[0]] || {};
          const firstSetKeys = Object.keys(firstSet);
          return firstSetKeys.length > 0 && firstSetKeys.every(k => /^\d+$/.test(k));
        });
        
        setSavedTicketsList(ticketResults.map((r: any) => ({
          id: r.id,
          name: r.name,
          description: r.description,
          createdAt: r.createdAt,
          selections: r.selections
        })));
      }
    } catch (err: any) {
      console.error('Error loading saved tickets:', err);
      setSavedTicketsList([]);
    } finally {
      setLoadingSavedTickets(false);
    }
  }, [jackpotId]);

  // Load saved tickets for the current jackpot
  useEffect(() => {
    loadSavedTickets();
  }, [loadSavedTickets]);

  // Load saved ticket when selected
  useEffect(() => {
    if (!selectedSavedTicketId || savedTicketsList.length === 0 || fixtureData.length === 0) return;

    const savedTicket = savedTicketsList.find(t => t.id.toString() === selectedSavedTicketId);
    if (!savedTicket) return;

    // Convert saved selections back to ticket format
    const loadedTickets: GeneratedTicket[] = [];
    const selections = savedTicket.selections || {};

    // Check if using new format (ticket-0, ticket-1, ...) or old format (A, B, ...)
    const isNewFormat = Object.keys(selections).some(key => key.startsWith('ticket-'));
    
    if (isNewFormat) {
      // New format: {"ticket-0": {"setKey": "B", "1": "1", "2": "X"}, ...}
      Object.keys(selections).sort((a, b) => {
        const aIdx = parseInt(a.replace('ticket-', ''));
        const bIdx = parseInt(b.replace('ticket-', ''));
        return aIdx - bIdx;
      }).forEach(ticketKey => {
        const ticketData = selections[ticketKey] || {};
        const setKey = ticketData.setKey || 'B';
        const picks: Pick[] = [];
        
        // Extract picks (keys that are numeric fixture indices)
        const sortedKeys = Object.keys(ticketData)
          .filter(k => k !== 'setKey' && /^\d+$/.test(k))
          .sort((a, b) => parseInt(a) - parseInt(b));
        
        sortedKeys.forEach(fixtureKey => {
          const pick = ticketData[fixtureKey] as Pick;
          if (pick === '1' || pick === 'X' || pick === '2') {
            picks.push(pick);
          }
        });

        if (picks.length > 0) {
          // Pad picks to match current fixtureData length
          while (picks.length < fixtureData.length) {
            picks.push('1' as Pick); // Default to '1' for missing fixtures
          }
          // Trim if picks exceed fixtureData length
          if (picks.length > fixtureData.length) {
            picks.splice(fixtureData.length);
          }

          // Calculate probability and odds from picks
          let probability = 1;
          let combinedOdds = 1;

          picks.forEach((pick, idx) => {
            const fixture = fixtureData[idx];
            if (!fixture) return;

            // Get probability from loaded sets (if available)
            const setKeyTyped = setKey as SetKey;
            if (loadedSets[setKeyTyped]?.probabilities?.[idx]) {
              const prob = loadedSets[setKeyTyped].probabilities[idx];
              const pickProb = pick === '1' ? prob.homeWinProbability / 100 :
                              pick === 'X' ? prob.drawProbability / 100 :
                              prob.awayWinProbability / 100;
              probability *= pickProb;
            } else {
              // Fallback: use default probability if not loaded
              probability *= 0.33;
            }

            // Get odds from fixture data
            if (fixture.odds) {
              const pickOdds = pick === '1' ? fixture.odds.home :
                              pick === 'X' ? fixture.odds.draw :
                              pick === '2' ? fixture.odds.away : 1;
              combinedOdds *= pickOdds;
            }
          });

          loadedTickets.push({
            id: `saved-${savedTicket.id}-${ticketKey}`,
            setKey: setKey as SetKey,
            picks,
            probability: probability * 100,
            combinedOdds,
          });
        }
      });
    } else {
      // Old format: {"A": {"1": "1", "2": "X"}, "B": {...}}
      Object.keys(selections).forEach(setKey => {
        const setSelections = selections[setKey] || {};
        const picks: Pick[] = [];
        
        // Sort by fixture number (keys are "1", "2", "3", etc.)
        const sortedKeys = Object.keys(setSelections).sort((a, b) => parseInt(a) - parseInt(b));
        
        sortedKeys.forEach(fixtureKey => {
          const pick = setSelections[fixtureKey] as Pick;
          if (pick === '1' || pick === 'X' || pick === '2') {
            picks.push(pick);
          }
        });

        if (picks.length > 0) {
          // Pad picks to match current fixtureData length
          while (picks.length < fixtureData.length) {
            picks.push('1' as Pick); // Default to '1' for missing fixtures
          }
          // Trim if picks exceed fixtureData length
          if (picks.length > fixtureData.length) {
            picks.splice(fixtureData.length);
          }

          // Calculate probability and odds from picks
          let probability = 1;
          let combinedOdds = 1;

          picks.forEach((pick, idx) => {
            const fixture = fixtureData[idx];
            if (!fixture) return;

            // Get probability from loaded sets (if available)
            const setKeyTyped = setKey as SetKey;
            if (loadedSets[setKeyTyped]?.probabilities?.[idx]) {
              const prob = loadedSets[setKeyTyped].probabilities[idx];
              const pickProb = pick === '1' ? prob.homeWinProbability / 100 :
                              pick === 'X' ? prob.drawProbability / 100 :
                              prob.awayWinProbability / 100;
              probability *= pickProb;
            } else {
              // Fallback: use default probability if not loaded
              probability *= 0.33;
            }

            // Get odds from fixture data
            if (fixture.odds) {
              const pickOdds = pick === '1' ? fixture.odds.home :
                              pick === 'X' ? fixture.odds.draw :
                              pick === '2' ? fixture.odds.away : 1;
              combinedOdds *= pickOdds;
            }
          });

          loadedTickets.push({
            id: `saved-${savedTicket.id}-${setKey}`,
            setKey: setKey as SetKey,
            picks,
            probability: probability * 100,
            combinedOdds,
          });
        }
      });
    }

    if (loadedTickets.length > 0) {
      // Sort tickets by probability (highest first) and assign rankings
      const sortedTickets = [...loadedTickets].sort((a, b) => b.probability - a.probability);
      const ticketsWithRanking = sortedTickets.map((ticket, index) => ({
        ...ticket,
        ranking: index + 1, // Rank 1 = highest probability
      }));
      
      setTickets(ticketsWithRanking);
      toast({
        title: 'Tickets Loaded',
        description: `Loaded ${loadedTickets.length} ticket(s) from "${savedTicket.name}"`,
      });
    }
  }, [selectedSavedTicketId, savedTicketsList, fixtureData, loadedSets, toast]);

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

  // Generate tickets using backend API with draw constraints and H2H-aware eligibility
  const generateTickets = useCallback(async () => {
    if (fixtureData.length === 0 || !jackpotId) {
      toast({
        title: 'Error',
        description: 'No fixture data available or jackpot ID missing. Please ensure probabilities are loaded.',
        variant: 'destructive',
      });
      return;
    }

    try {
      setLoading(true);
      
      // Call backend ticket generation API with draw constraints
      const response = await apiClient.generateTickets(
        jackpotId,
        selectedSets,
        1, // 1 ticket per set
        undefined // league code will be inferred from fixtures
      );

      if (response.success && response.data) {
        const bundle = response.data;
        
        // Convert backend tickets to frontend format
        const newTickets: GeneratedTicket[] = bundle.tickets.map((ticket: any) => {
          // Calculate probability and odds from picks
          let probability = 1;
          let combinedOdds = 1;
          
          ticket.picks.forEach((pick: string, idx: number) => {
            const fixture = fixtureData[idx];
            if (!fixture) return;
            
            // Get probability from loaded sets
            const setKey = ticket.setKey || selectedSets[0];
            if (loadedSets[setKey]?.probabilities?.[idx]) {
              const prob = loadedSets[setKey].probabilities[idx];
              const pickProb = pick === '1' ? prob.homeWinProbability / 100 :
                              pick === 'X' ? prob.drawProbability / 100 :
                              prob.awayWinProbability / 100;
              probability *= pickProb;
            } else {
              // Fallback: if probabilities not loaded, use a default (but this shouldn't happen)
              // This ensures we don't get 0% if data is missing
              probability *= 0.33; // Default to ~33% per match if data missing
            }
            
            // Get odds from fixture data
            if (fixture.odds) {
              const pickOdds = pick === '1' ? fixture.odds.home :
                              pick === 'X' ? fixture.odds.draw :
                              pick === '2' ? fixture.odds.away : 1;
              combinedOdds *= pickOdds;
            }
          });
          
          // Ensure probability is valid (not NaN or 0)
          if (!probability || isNaN(probability) || probability <= 0) {
            probability = 0.0001; // Very small default if calculation failed
          }

          return {
            id: ticket.id || `ticket-${ticket.setKey}-${Date.now()}`,
            setKey: ticket.setKey || selectedSets[0],
            picks: ticket.picks as Pick[],
            probability: probability * 100, // Already in percentage (0-100)
            combinedOdds,
          };
        });

        // Sort tickets by probability (highest first) and assign rankings
        const sortedTickets = [...newTickets].sort((a, b) => b.probability - a.probability);
        const ticketsWithRanking = sortedTickets.map((ticket, index) => ({
          ...ticket,
          ranking: index + 1, // Rank 1 = highest probability
        }));

        setTickets(ticketsWithRanking);
        
        toast({
          title: 'Tickets Generated',
          description: `${newTickets.length} tickets created with ${bundle.coverage?.draw_pct?.toFixed(1) || 0}% draw coverage`,
        });
      } else {
        throw new Error(response.message || 'Failed to generate tickets');
      }
    } catch (error: any) {
      console.error('Error generating tickets:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to generate tickets. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [selectedSets, fixtureData, loadedSets, jackpotId, toast]);

  // Coverage diagnostics with warnings
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

    const homePct = totalPicks > 0 ? (homePicks / totalPicks) * 100 : 0;
    const drawPct = totalPicks > 0 ? (drawPicks / totalPicks) * 100 : 0;
    const awayPct = totalPicks > 0 ? (awayPicks / totalPicks) * 100 : 0;

    // Generate warnings
    const warnings: string[] = [];
    if (drawPct < 1.0) {
      warnings.push('No draw selections detected. This reduces jackpot coverage in draw-heavy leagues.');
    } else if (drawPct < 15.0) {
      warnings.push('Draw coverage is low. Historical jackpot draws are under-represented.');
    }
    if (overlapWarning) {
      warnings.push('Some tickets have identical picks. Consider diversifying.');
    }
    if (Math.abs(homePct - awayPct) > 40.0) {
      warnings.push('Significant imbalance between home and away selections.');
    }

    return {
      homePct,
      drawPct,
      awayPct,
      uniqueTickets,
      overlapWarning,
      warnings,
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

  // Save tickets function
  const saveTickets = useCallback(async () => {
    if (tickets.length === 0) {
      toast({
        title: 'Error',
        description: 'No tickets to save. Please generate tickets first.',
        variant: 'destructive',
      });
      return;
    }

    if (!saveTicketName.trim()) {
      toast({
        title: 'Error',
        description: 'Please enter a name for the saved tickets.',
        variant: 'destructive',
      });
      return;
    }

    if (!jackpotId) {
      toast({
        title: 'Error',
        description: 'Jackpot ID is missing.',
        variant: 'destructive',
      });
      return;
    }

    try {
      setSavingTickets(true);
      
      const response = await apiClient.saveTickets(
        jackpotId,
        saveTicketName.trim(),
        saveTicketDescription.trim() || undefined,
        tickets.map(t => ({
          id: t.id,
          setKey: t.setKey,
          picks: t.picks,
          probability: t.probability,
          combinedOdds: t.combinedOdds
        }))
      );

      if (response.success) {
        toast({
          title: 'Success',
          description: `Saved ${tickets.length} tickets successfully`,
        });
        setShowSaveDialog(false);
        setSaveTicketName('');
        setSaveTicketDescription('');
        
        // Refresh saved tickets list to show the newly saved ticket
        await loadSavedTickets(jackpotId);
      } else {
        throw new Error(response.message || 'Failed to save tickets');
      }
    } catch (error: any) {
      console.error('Error saving tickets:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to save tickets. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setSavingTickets(false);
    }
  }, [tickets, saveTicketName, saveTicketDescription, jackpotId, toast, loadSavedTickets]);

  return (
    <PageLayout
      title="Ticket Construction"
      description="Generate optimized tickets from probability sets"
      icon={<Ticket className="h-6 w-6" />}
    >
        {/* Jackpot Selector and Load Saved Tickets */}
        <div className="flex items-center gap-4 flex-wrap">
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
                setSelectedSavedTicketId(''); // Reset saved ticket selection when jackpot changes
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

          {jackpotId && (
            <div className="flex items-center gap-2">
              <Label htmlFor="saved-tickets-select" className="text-sm whitespace-nowrap">
                Load Saved Tickets:
              </Label>
              <Select
                value={selectedSavedTicketId || 'none'}
                onValueChange={(value) => {
                  if (value === 'none') {
                    setSelectedSavedTicketId('');
                    setTickets([]); // Clear tickets if "None" selected
                  } else {
                    setSelectedSavedTicketId(value);
                  }
                }}
                disabled={loadingSavedTickets}
              >
                <SelectTrigger id="saved-tickets-select" className="w-[300px]">
                  <SelectValue placeholder={loadingSavedTickets ? "Loading..." : "Select saved tickets"} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None (Generate New)</SelectItem>
                  {savedTicketsList.length === 0 ? (
                    <div className="px-2 py-1.5 text-sm text-muted-foreground">
                      No saved tickets found
                    </div>
                  ) : (
                    savedTicketsList.map((savedTicket) => (
                      <SelectItem key={savedTicket.id} value={savedTicket.id.toString()}>
                        {savedTicket.name} ({new Date(savedTicket.createdAt).toLocaleDateString()})
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
          )}
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

      <div className="space-y-6">
        {/* Select Probability Sets Section */}
          <Card className="glass-card">
            <CardHeader>
            <div className="flex items-center justify-between">
              <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Layers className="h-5 w-5 text-primary" />
                Select Probability Sets
              </CardTitle>
              <CardDescription>
                Choose which sets to generate tickets from
              </CardDescription>
              </div>
              {/* Select All Checkbox */}
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="select-all-sets"
                  checked={selectedSets.length === Object.keys(probabilitySets).length}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedSets(Object.keys(probabilitySets) as SetKey[]);
                    } else {
                      setSelectedSets([]);
                    }
                  }}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <Label htmlFor="select-all-sets" className="text-sm font-medium cursor-pointer">
                  Select All ({Object.keys(probabilitySets).length})
                </Label>
              </div>
            </div>
            </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 lg:grid-cols-10 gap-3">
                {(Object.entries(probabilitySets) as [SetKey, typeof probabilitySets['A']][]).map(([key, set]) => {
                  const Icon = set.icon;
                  const isSelected = selectedSets.includes(key);
                  
                  return (
                    <button
                      key={key}
                      onClick={() => isSelected ? removeSet(key) : addSet(key)}
                    className={`relative flex flex-col items-center gap-2 p-4 rounded-lg border transition-all ${
                        isSelected 
                        ? 'bg-primary/10 border-primary/50 shadow-md' 
                        : 'bg-muted/20 border-border/50 hover:border-primary/30 hover:shadow-sm'
                      }`}
                    >
                    <div className={`p-2.5 rounded-md ${isSelected ? 'bg-primary/20' : 'bg-muted/30'}`}>
                      <Icon className={`h-5 w-5 ${set.color}`} />
                      </div>
                    <div className="flex-1 text-center w-full">
                      <div className="font-semibold text-sm">Set {key}</div>
                      <div className="text-xs text-muted-foreground mt-0.5 leading-tight">{set.name}</div>
                      <div className="text-[10px] text-muted-foreground/80 mt-1">Risk: {set.risk}</div>
                      </div>
                    {isSelected && <CheckCircle className="h-4 w-4 text-primary absolute top-2 right-2" />}
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

        {/* Budget Allocation Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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
        </div>

        {/* Generated Tickets */}
      <div className="space-y-4">
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

                {coverageDiagnostics.warnings && coverageDiagnostics.warnings.length > 0 && (
                  <Alert 
                    variant={coverageDiagnostics.drawPct < 1.0 ? "destructive" : "default"} 
                    className="mt-4"
                  >
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      <ul className="list-disc list-inside space-y-1 text-sm">
                        {coverageDiagnostics.warnings.map((warning, idx) => (
                          <li key={idx}>{warning}</li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}

                {coverageDiagnostics.overlapWarning && !coverageDiagnostics.warnings?.includes('Some tickets have identical picks. Consider diversifying.') && (
                  <Alert className="border-status-watch/50 bg-status-watch/10 mt-4">
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
              <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <Ticket className="h-5 w-5 text-primary" />
                Generated Tickets ({tickets.length})
              </CardTitle>
                {tickets.length > 0 && (
                  <div className="flex items-center gap-2">
                    <Button
                      onClick={() => {
                        // Export tickets to CSV
                        const matchHeaders = fixtureData.map((f, idx) => `Match ${idx + 1} (${f.home} vs ${f.away})`);
                        const headers = ['Ticket ID', 'Set', 'Picks', 'Probability (%)', 'Ranking', ...matchHeaders];
                        
                        const rows = tickets.map(ticket => [
                          ticket.id,
                          ticket.setKey,
                          ticket.picks.join(''),
                          ticket.probability.toFixed(2) + '%',
                          ticket.ranking || '-',
                          ...ticket.picks.map((pick, idx) => {
                            const fixture = fixtureData[idx];
                            return fixture ? `${pick}` : '';
                          })
                        ]);
                        
                        // Create CSV content with proper escaping
                        const escapeCSV = (value: any): string => {
                          if (value === null || value === undefined) return '';
                          const str = String(value);
                          // Escape quotes and wrap in quotes if contains comma, quote, or newline
                          if (str.includes(',') || str.includes('"') || str.includes('\n')) {
                            return `"${str.replace(/"/g, '""')}"`;
                          }
                          return str;
                        };
                        
                        const csvContent = [
                          headers.map(escapeCSV).join(','),
                          ...rows.map(row => row.map(escapeCSV).join(','))
                        ].join('\n');
                        
                        // Create blob and download
                        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                        const link = document.createElement('a');
                        const url = URL.createObjectURL(blob);
                        link.setAttribute('href', url);
                        link.setAttribute('download', `tickets_${jackpotId || 'export'}_${new Date().toISOString().split('T')[0]}.csv`);
                        link.style.visibility = 'hidden';
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        
                        toast({
                          title: 'Export Successful',
                          description: `Exported ${tickets.length} tickets to CSV`,
                        });
                      }}
                      variant="outline"
                      size="sm"
                      className="gap-2"
                    >
                      <Download className="h-4 w-4" />
                      Export CSV
                    </Button>
                    <Button
                      onClick={() => setShowSaveDialog(true)}
                      variant="outline"
                      size="sm"
                      className="gap-2"
                    >
                      <Save className="h-4 w-4" />
                      Save Tickets
                    </Button>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {tickets.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Ticket className="h-12 w-12 mx-auto mb-3 opacity-30" />
                  <p>Select probability sets and click Generate to create tickets</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <ScrollArea className="h-[600px]">
                  <Table>
                      <TableHeader className="sticky top-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-10">
                        {/* Team names header row */}
                        <TableRow className="border-b-0 h-12">
                          <TableHead className="w-[80px] sticky left-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-20 border-r border-t-0 py-1">
                            <div className="text-xs font-semibold text-muted-foreground">Set</div>
                          </TableHead>
                          {fixtureData.map((fixture, idx) => (
                            <TableHead 
                              key={fixture.id} 
                              className="p-0.5 text-center border-l border-border/50 min-w-[70px] py-1"
                            >
                              <div className="flex flex-col items-center gap-0">
                                <div className="text-[10px] font-medium text-muted-foreground leading-[1.1] px-0.5">
                                  {fixture.home.length > 6 ? fixture.home.substring(0, 6) + '..' : fixture.home}
                                </div>
                                <div className="text-[8px] text-muted-foreground/70">vs</div>
                                <div className="text-[10px] font-medium text-muted-foreground leading-[1.1] px-0.5">
                                  {fixture.away.length > 6 ? fixture.away.substring(0, 6) + '..' : fixture.away}
                                </div>
                              </div>
                            </TableHead>
                          ))}
                          <TableHead className="text-right w-[100px] border-l-2 border-primary/20 py-1">
                            <div className="text-xs font-semibold text-muted-foreground">Probability</div>
                          </TableHead>
                          <TableHead className="text-center w-[100px] py-1">
                            <div className="text-xs font-semibold text-muted-foreground">Ranking</div>
                          </TableHead>
                          <TableHead className="w-[100px] py-1">
                            <div className="text-xs font-semibold text-muted-foreground">Actions</div>
                          </TableHead>
                        </TableRow>
                        {/* Picks header row */}
                        <TableRow className="h-8">
                          <TableHead className="w-[80px] sticky left-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-20 border-r border-t-0 py-0.5"></TableHead>
                          {fixtureData.map((fixture, idx) => (
                            <TableHead 
                              key={`pick-header-${fixture.id}`}
                              className="p-0.5 text-center border-l border-border/50 min-w-[70px] py-0.5"
                            >
                              <div className="text-[10px] font-semibold text-muted-foreground">#{idx + 1}</div>
                            </TableHead>
                          ))}
                          <TableHead className="text-right w-[100px] border-l-2 border-primary/20 border-t-0 py-0.5"></TableHead>
                          <TableHead className="text-right w-[100px] border-t-0 py-0.5"></TableHead>
                          <TableHead className="w-[100px] border-t-0 py-0.5"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {tickets.map((ticket) => {
                        const set = probabilitySets[ticket.setKey];
                        const Icon = set.icon;
                        
                        return (
                            <TableRow key={ticket.id} className="hover:bg-muted/30 transition-colors">
                              <TableCell className="sticky left-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-10 border-r">
                                <Badge variant="outline" className={`${set.color} text-xs`}>
                                <Icon className="h-3 w-3 mr-1" />
                                {ticket.setKey}
                              </Badge>
                            </TableCell>
                              {fixtureData.map((fixture, idx) => {
                                const pick = ticket.picks[idx]; // Get pick for this fixture index
                                // Get probability for this pick from loaded sets
                                const setKey = ticket.setKey;
                                const prob = loadedSets[setKey]?.probabilities?.[idx];
                                const pickProbability = pick === '1' ? prob?.homeWinProbability :
                                                       pick === 'X' ? prob?.drawProbability :
                                                       pick === '2' ? prob?.awayWinProbability : null;
                                
                                return (
                                  <TableCell 
                                    key={`${ticket.id}-${idx}`}
                                    className="p-0.5 text-center border-l border-border/50"
                                  >
                                    {pick ? (
                                      <div className="flex flex-col items-center gap-0.5">
                                        <Badge 
                                          variant="outline"
                                          className={`w-5 h-5 p-0 justify-center text-[11px] font-bold transition-all hover:scale-110 ${
                                            pick === '1' ? 'bg-chart-1/20 text-chart-1 border-chart-1/50 hover:bg-chart-1/30' :
                                            pick === 'X' ? 'bg-chart-3/20 text-chart-3 border-chart-3/50 hover:bg-chart-3/30' :
                                            'bg-chart-2/20 text-chart-2 border-chart-2/50 hover:bg-chart-2/30'
                                          }`}
                                        >
                                          {pick}
                                        </Badge>
                                        {pickProbability !== null && pickProbability !== undefined && (
                                          <span className={`text-[10px] font-semibold leading-none ${
                                            pick === '1' ? 'text-chart-1' :
                                            pick === 'X' ? 'text-chart-3' :
                                            'text-chart-2'
                                          }`}>
                                            {pickProbability.toFixed(0)}%
                                          </span>
                                        )}
                                      </div>
                                    ) : (
                                      <span className="text-muted-foreground/30 text-xs">—</span>
                                    )}
                            </TableCell>
                                );
                              })}
                              <TableCell className="text-right tabular-nums text-sm border-l-2 border-primary/20 font-medium">
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <span className="cursor-help">
                                      {ticket.probability > 0.01 
                                        ? ticket.probability.toFixed(2) + '%'
                                        : ticket.probability > 0.001
                                        ? ticket.probability.toFixed(3) + '%'
                                        : ticket.probability > 0
                                        ? ticket.probability.toFixed(4) + '%'
                                        : '0.00%'}
                                    </span>
                                  </TooltipTrigger>
                                  <TooltipContent className="max-w-xs">
                                    <p className="font-semibold mb-1">Ticket Probability</p>
                                    <p className="text-xs mb-2">
                                      Chance that <strong>all {fixtureData.length} picks</strong> are correct.
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                      {ticket.probability > 0 
                                        ? `1 in ${Math.round(100 / ticket.probability).toLocaleString()} chance`
                                        : 'Cannot calculate'}
                                    </p>
                                    <p className="text-xs text-muted-foreground mt-2">
                                      Low probabilities are normal for accumulator bets.
                                    </p>
                                  </TooltipContent>
                                </Tooltip>
                            </TableCell>
                              <TableCell className="text-center tabular-nums font-semibold">
                                <Badge variant={ticket.ranking && ticket.ranking <= 3 ? "default" : "outline"} className="text-xs">
                                  {ticket.ranking || '-'}
                                </Badge>
                            </TableCell>
                            <TableCell>
                                <div className="flex gap-1 justify-center">
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button 
                                      size="icon" 
                                      variant="ghost" 
                                        className="h-7 w-7 hover:bg-primary/10"
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
                                        className="h-7 w-7 hover:bg-primary/10"
                                      onClick={() => {
                                        const csv = [
                                          ['Set', 'Picks', 'Probability (%)', 'Ranking'],
                                          [
                                            ticket.setKey,
                                            ticket.picks.join(''),
                                            ticket.probability.toFixed(2) + '%',
                                            ticket.ranking?.toString() || '-'
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
                </div>
              )}
            </CardContent>
          </Card>

          {/* Save Dialog */}
          {showSaveDialog && (
            <Card className="glass-card border-primary/50">
              <CardHeader>
                <CardTitle className="text-lg">Save Tickets</CardTitle>
                <CardDescription>
                  Save {tickets.length} generated ticket{tickets.length !== 1 ? 's' : ''} for later reference
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="save-name">Name *</Label>
                  <Input
                    id="save-name"
                    value={saveTicketName}
                    onChange={(e) => setSaveTicketName(e.target.value)}
                    placeholder="e.g., Week 1 Tickets - Set B"
                    className="bg-background/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="save-description">Description (Optional)</Label>
                  <Input
                    id="save-description"
                    value={saveTicketDescription}
                    onChange={(e) => setSaveTicketDescription(e.target.value)}
                    placeholder="Additional notes..."
                    className="bg-background/50"
                  />
                </div>
                <div className="flex gap-2 justify-end">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowSaveDialog(false);
                      setSaveTicketName('');
                      setSaveTicketDescription('');
                    }}
                    disabled={savingTickets}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={saveTickets}
                    disabled={savingTickets || !saveTicketName.trim()}
                    className="gap-2"
                  >
                    {savingTickets ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4" />
                        Save
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

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
    </PageLayout>
  );
}
