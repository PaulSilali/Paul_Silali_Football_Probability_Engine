import { useState, useMemo, useCallback } from 'react';
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
  Sparkles
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

// Mock fixture data with picks per set
const fixtureData = [
  { id: '1', home: 'Gillingham', away: 'Cambridge', sets: { A: '1', B: '1', C: '1', D: 'X', E: '1', F: '1', G: '1' } },
  { id: '2', home: 'AFC Wimbledon', away: 'Crawley', sets: { A: 'X', B: '1', C: '1', D: 'X', E: '1', F: '1', G: '1' } },
  { id: '3', home: 'Cheltenham', away: 'Walsall', sets: { A: '1', B: '1', C: '2', D: 'X', E: '2', F: '2', G: '1' } },
  { id: '4', home: 'Blackpool', away: 'Doncaster', sets: { A: '1', B: '1', C: '1', D: '1', E: '1', F: '1', G: '1' } },
  { id: '5', home: 'Burton', away: 'Accrington', sets: { A: '1', B: '1', C: '1', D: 'X', E: '1', F: '1', G: '1' } },
  { id: '6', home: 'Chesterfield', away: 'Harrogate', sets: { A: '1', B: '1', C: '1', D: '1', E: '1', F: '1', G: '1' } },
  { id: '7', home: 'Plymouth', away: 'Luton', sets: { A: '1', B: 'X', C: '2', D: 'X', E: '2', F: '2', G: 'X' } },
  { id: '8', home: 'Portsmouth', away: 'Swansea', sets: { A: '2', B: '2', C: '2', D: 'X', E: '2', F: '2', G: '2' } },
  { id: '9', home: 'Peterborough', away: 'Northampton', sets: { A: '1', B: '1', C: '1', D: '1', E: '1', F: '1', G: '1' } },
  { id: '10', home: 'Chippenham', away: 'Taunton', sets: { A: '1', B: '2', C: '2', D: 'X', E: '2', F: '2', G: '2' } },
  { id: '11', home: 'Salisbury', away: 'Frome', sets: { A: '1', B: '1', C: '1', D: '1', E: '1', F: '1', G: '1' } },
  { id: '12', home: 'Eastleigh', away: 'Woking', sets: { A: '1', B: '1', C: '1', D: 'X', E: '1', F: '1', G: '1' } },
  { id: '13', home: 'Telford', away: 'Kidderminster', sets: { A: '1', B: '1', C: 'X', D: 'X', E: '1', F: '1', G: '1' } },
];

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
  const [selectedSets, setSelectedSets] = useState<SetKey[]>(['B']);
  const [budget, setBudget] = useState<number>(500);
  const [tickets, setTickets] = useState<GeneratedTicket[]>([]);
  const { toast } = useToast();

  // Generate tickets based on selected sets
  const generateTickets = useCallback(() => {
    const newTickets: GeneratedTicket[] = selectedSets.map((setKey, idx) => {
      const picks = fixtureData.map(f => f.sets[setKey] as Pick);
      
      // Calculate mock probability and odds
      const probability = picks.reduce((acc, pick) => {
        const base = pick === '1' ? 0.45 : pick === 'X' ? 0.28 : 0.35;
        return acc * (base + Math.random() * 0.1);
      }, 1) * 100;
      
      const combinedOdds = picks.reduce((acc, pick) => {
        const base = pick === '1' ? 2.2 : pick === 'X' ? 3.3 : 2.8;
        return acc * (base + Math.random() * 0.5);
      }, 1);

      return {
        id: `ticket-${setKey}-${Date.now()}-${idx}`,
        setKey,
        picks,
        probability: probability,
        combinedOdds,
      };
    });

    setTickets(newTickets);
    toast({
      title: 'Tickets Generated',
      description: `${newTickets.length} tickets created using Sets ${selectedSets.join(', ')}`,
    });
  }, [selectedSets, toast]);

  // Coverage diagnostics
  const coverageDiagnostics = useMemo(() => {
    if (tickets.length === 0) return null;

    const totalPicks = fixtureData.length * tickets.length;
    let homePicks = 0;
    let drawPicks = 0;
    let awayPicks = 0;

    tickets.forEach(ticket => {
      ticket.picks.forEach(pick => {
        if (pick === '1') homePicks++;
        else if (pick === 'X') drawPicks++;
        else awayPicks++;
      });
    });

    // Check for overlap
    const pickStrings = tickets.map(t => t.picks.join(''));
    const uniqueTickets = new Set(pickStrings).size;
    const overlapWarning = uniqueTickets < tickets.length;

    return {
      homePct: (homePicks / totalPicks) * 100,
      drawPct: (drawPicks / totalPicks) * 100,
      awayPct: (awayPicks / totalPicks) * 100,
      uniqueTickets,
      overlapWarning,
    };
  }, [tickets]);

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
                disabled={selectedSets.length === 0}
              >
                <Sparkles className="h-4 w-4 mr-2" />
                Generate {selectedSets.length} Ticket{selectedSets.length !== 1 ? 's' : ''}
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
                                    <Button size="icon" variant="ghost" className="h-7 w-7">
                                      <Copy className="h-3.5 w-3.5" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>Copy picks</TooltipContent>
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
