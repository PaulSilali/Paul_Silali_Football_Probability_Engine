import { useState } from 'react';
import { Plus, Trash2, Save, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import type { ParsedResult } from './PDFResultsImport';

interface ManualResultsEntryProps {
  onResultsSubmitted: (results: ParsedResult[]) => void;
}

interface ManualMatch {
  id: string;
  homeTeam: string;
  awayTeam: string;
  homeScore: string;
  awayScore: string;
  homeOdds: string;
  drawOdds: string;
  awayOdds: string;
}

const createEmptyMatch = (id: string): ManualMatch => ({
  id,
  homeTeam: '',
  awayTeam: '',
  homeScore: '',
  awayScore: '',
  homeOdds: '',
  drawOdds: '',
  awayOdds: '',
});

export function ManualResultsEntry({ onResultsSubmitted }: ManualResultsEntryProps) {
  const [matches, setMatches] = useState<ManualMatch[]>([
    createEmptyMatch('1'),
    createEmptyMatch('2'),
    createEmptyMatch('3'),
  ]);
  const [jackpotName, setJackpotName] = useState('');

  const addMatch = () => {
    const newId = String(matches.length + 1);
    setMatches([...matches, createEmptyMatch(newId)]);
  };

  const removeMatch = (id: string) => {
    if (matches.length > 1) {
      setMatches(matches.filter(m => m.id !== id));
    }
  };

  const updateMatch = (id: string, field: keyof ManualMatch, value: string) => {
    setMatches(matches.map(m => 
      m.id === id ? { ...m, [field]: value } : m
    ));
  };

  const resetForm = () => {
    setMatches([
      createEmptyMatch('1'),
      createEmptyMatch('2'),
      createEmptyMatch('3'),
    ]);
    setJackpotName('');
  };

  const determineResult = (homeScore: number, awayScore: number): 'H' | 'D' | 'A' => {
    if (homeScore > awayScore) return 'H';
    if (homeScore < awayScore) return 'A';
    return 'D';
  };

  const handleSubmit = () => {
    // Validate all matches have required fields
    const validMatches = matches.filter(m => 
      m.homeTeam.trim() && 
      m.awayTeam.trim() && 
      m.homeScore !== '' && 
      m.awayScore !== ''
    );

    if (validMatches.length === 0) {
      toast.error('Please enter at least one complete match');
      return;
    }

    const results: ParsedResult[] = validMatches.map((m, idx) => ({
      id: String(idx + 1),
      homeTeam: m.homeTeam.trim(),
      awayTeam: m.awayTeam.trim(),
      homeScore: parseInt(m.homeScore) || 0,
      awayScore: parseInt(m.awayScore) || 0,
      result: determineResult(parseInt(m.homeScore) || 0, parseInt(m.awayScore) || 0),
      homeOdds: m.homeOdds ? parseFloat(m.homeOdds) : undefined,
      drawOdds: m.drawOdds ? parseFloat(m.drawOdds) : undefined,
      awayOdds: m.awayOdds ? parseFloat(m.awayOdds) : undefined,
    }));

    onResultsSubmitted(results);
    toast.success(`${results.length} match results submitted for backtesting`);
  };

  const isMatchComplete = (m: ManualMatch) => 
    m.homeTeam.trim() && m.awayTeam.trim() && m.homeScore !== '' && m.awayScore !== '';

  const completeCount = matches.filter(isMatchComplete).length;

  return (
    <Card className="glass-card">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Manual Results Entry</span>
          <Badge variant="outline">
            {completeCount}/{matches.length} complete
          </Badge>
        </CardTitle>
        <CardDescription>
          Paste or type past jackpot match results for backtesting
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Jackpot Name */}
        <div>
          <label className="text-sm font-medium mb-1.5 block">Jackpot Reference (optional)</label>
          <Input
            value={jackpotName}
            onChange={(e) => setJackpotName(e.target.value)}
            placeholder="e.g., SportPesa Mega Jackpot Week 52"
            className="glass-card"
          />
        </div>

        {/* Match Entries */}
        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-3">
            {matches.map((match, idx) => (
              <div 
                key={match.id}
                className={`p-4 rounded-lg border transition-colors ${
                  isMatchComplete(match) 
                    ? 'bg-green-500/5 border-green-500/20' 
                    : 'bg-muted/30 border-border'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium">Match {idx + 1}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeMatch(match.id)}
                    disabled={matches.length <= 1}
                    className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>

                {/* Teams Row */}
                <div className="grid grid-cols-5 gap-2 mb-3">
                  <Input
                    value={match.homeTeam}
                    onChange={(e) => updateMatch(match.id, 'homeTeam', e.target.value)}
                    placeholder="Home Team"
                    className="col-span-2 text-sm"
                  />
                  <div className="flex items-center justify-center text-muted-foreground text-sm">
                    vs
                  </div>
                  <Input
                    value={match.awayTeam}
                    onChange={(e) => updateMatch(match.id, 'awayTeam', e.target.value)}
                    placeholder="Away Team"
                    className="col-span-2 text-sm"
                  />
                </div>

                {/* Score Row */}
                <div className="grid grid-cols-5 gap-2 mb-3">
                  <Input
                    type="number"
                    min="0"
                    value={match.homeScore}
                    onChange={(e) => updateMatch(match.id, 'homeScore', e.target.value)}
                    placeholder="0"
                    className="text-center text-sm col-span-2"
                  />
                  <div className="flex items-center justify-center text-muted-foreground text-sm">
                    Score
                  </div>
                  <Input
                    type="number"
                    min="0"
                    value={match.awayScore}
                    onChange={(e) => updateMatch(match.id, 'awayScore', e.target.value)}
                    placeholder="0"
                    className="text-center text-sm col-span-2"
                  />
                </div>

                {/* Odds Row (Optional) */}
                <div className="grid grid-cols-3 gap-2">
                  <Input
                    type="number"
                    step="0.01"
                    value={match.homeOdds}
                    onChange={(e) => updateMatch(match.id, 'homeOdds', e.target.value)}
                    placeholder="H Odds"
                    className="text-center text-xs"
                  />
                  <Input
                    type="number"
                    step="0.01"
                    value={match.drawOdds}
                    onChange={(e) => updateMatch(match.id, 'drawOdds', e.target.value)}
                    placeholder="D Odds"
                    className="text-center text-xs"
                  />
                  <Input
                    type="number"
                    step="0.01"
                    value={match.awayOdds}
                    onChange={(e) => updateMatch(match.id, 'awayOdds', e.target.value)}
                    placeholder="A Odds"
                    className="text-center text-xs"
                  />
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>

        {/* Actions */}
        <div className="flex gap-2">
          <Button variant="outline" onClick={addMatch} className="flex-1">
            <Plus className="h-4 w-4 mr-2" />
            Add Match
          </Button>
          <Button variant="outline" onClick={resetForm}>
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={completeCount === 0}
            className="flex-1 btn-glow"
          >
            <Save className="h-4 w-4 mr-2" />
            Submit Results
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
