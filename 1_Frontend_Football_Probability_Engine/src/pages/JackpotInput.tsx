import { useState, useCallback } from 'react';
import { Plus, Trash2, Upload, AlertTriangle, ArrowRight, Sparkles, Target, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { PDFJackpotImport, ParsedFixture } from '@/components/PDFJackpotImport';
import type { Fixture } from '@/types';

interface EditableFixture extends Omit<Fixture, 'id'> {
  id: string;
  tempId: string;
}

const createEmptyFixture = (): EditableFixture => ({
  id: '',
  tempId: crypto.randomUUID(),
  homeTeam: '',
  awayTeam: '',
  homeOdds: 0,
  drawOdds: 0,
  awayOdds: 0,
  validationWarnings: [],
});

export default function JackpotInput() {
  const [fixtures, setFixtures] = useState<EditableFixture[]>([
    createEmptyFixture(),
  ]);
  const [bulkInput, setBulkInput] = useState('');
  const [isBulkDialogOpen, setIsBulkDialogOpen] = useState(false);
  const [isPDFDialogOpen, setIsPDFDialogOpen] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const handlePDFImport = useCallback((parsedFixtures: ParsedFixture[]) => {
    const newFixtures: EditableFixture[] = parsedFixtures.map(f => ({
      id: f.id,
      tempId: crypto.randomUUID(),
      homeTeam: f.homeTeam,
      awayTeam: f.awayTeam || 'Away Team',
      homeOdds: f.homeOdds,
      drawOdds: f.drawOdds,
      awayOdds: f.awayOdds,
      validationWarnings: [],
    }));
    setFixtures(newFixtures);
  }, []);
  const addFixture = useCallback(() => {
    setFixtures((prev) => [...prev, createEmptyFixture()]);
  }, []);

  const removeFixture = useCallback((tempId: string) => {
    setFixtures((prev) => prev.filter((f) => f.tempId !== tempId));
  }, []);

  const updateFixture = useCallback(
    (tempId: string, field: keyof EditableFixture, value: string | number) => {
      setFixtures((prev) =>
        prev.map((f) =>
          f.tempId === tempId ? { ...f, [field]: value } : f
        )
      );
    },
    []
  );

  const parseOdds = (value: string): number => {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? 0 : parsed;
  };

  const validateFixtures = useCallback((): boolean => {
    const errors: string[] = [];
    
    fixtures.forEach((fixture, index) => {
      if (!fixture.homeTeam.trim()) {
        errors.push(`Row ${index + 1}: Home team is required`);
      }
      if (!fixture.awayTeam.trim()) {
        errors.push(`Row ${index + 1}: Away team is required`);
      }
      if (fixture.homeOdds <= 1) {
        errors.push(`Row ${index + 1}: Home odds must be greater than 1.00`);
      }
      if (fixture.drawOdds <= 1) {
        errors.push(`Row ${index + 1}: Draw odds must be greater than 1.00`);
      }
      if (fixture.awayOdds <= 1) {
        errors.push(`Row ${index + 1}: Away odds must be greater than 1.00`);
      }
    });

    setValidationErrors(errors);
    return errors.length === 0;
  }, [fixtures]);

  const handleBulkImport = useCallback(() => {
    const lines = bulkInput.trim().split('\n');
    const newFixtures: EditableFixture[] = [];

    lines.forEach((line) => {
      const parts = line.split(/[,\t]/);
      if (parts.length >= 5) {
        newFixtures.push({
          id: '',
          tempId: crypto.randomUUID(),
          homeTeam: parts[0].trim(),
          awayTeam: parts[1].trim(),
          homeOdds: parseOdds(parts[2]),
          drawOdds: parseOdds(parts[3]),
          awayOdds: parseOdds(parts[4]),
          validationWarnings: [],
        });
      }
    });

    if (newFixtures.length > 0) {
      setFixtures(newFixtures);
      setBulkInput('');
      setIsBulkDialogOpen(false);
    }
  }, [bulkInput]);

  const handleSubmit = useCallback(() => {
    if (validateFixtures()) {
      // TODO: Submit to API
      console.log('Submitting fixtures:', fixtures);
    }
  }, [fixtures, validateFixtures]);

  const isValid = fixtures.length > 0 && 
    fixtures.every(f => 
      f.homeTeam.trim() && 
      f.awayTeam.trim() && 
      f.homeOdds > 1 && 
      f.drawOdds > 1 && 
      f.awayOdds > 1
    );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 glow-primary">
            <Target className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold gradient-text">Jackpot Input</h1>
            <p className="text-sm text-muted-foreground">
              Enter fixtures and their corresponding decimal odds
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 animate-slide-in-right">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => setIsPDFDialogOpen(true)}
            className="glass-card border-accent/30 hover:bg-accent/10"
          >
            <FileText className="h-4 w-4 mr-2" />
            Import PDF
          </Button>
          <Dialog open={isBulkDialogOpen} onOpenChange={setIsBulkDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" className="glass-card border-primary/30 hover:bg-primary/10">
                <Upload className="h-4 w-4 mr-2" />
                Bulk Import
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl glass-card-elevated">
              <DialogHeader>
                <DialogTitle className="gradient-text">Bulk Import Fixtures</DialogTitle>
                <DialogDescription>
                  Paste fixtures in CSV or tab-separated format: HomeTeam, AwayTeam, HomeOdds, DrawOdds, AwayOdds
                </DialogDescription>
              </DialogHeader>
              <Textarea
                placeholder="Arsenal, Chelsea, 2.10, 3.40, 3.20
Liverpool, Man City, 2.80, 3.30, 2.45"
                value={bulkInput}
                onChange={(e) => setBulkInput(e.target.value)}
                className="min-h-[200px] font-mono text-sm bg-background/50"
              />
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsBulkDialogOpen(false)} className="glass-card">
                  Cancel
                </Button>
                <Button onClick={handleBulkImport} disabled={!bulkInput.trim()} className="btn-glow bg-primary text-primary-foreground">
                  Import
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Button onClick={addFixture} size="sm" className="btn-glow bg-primary text-primary-foreground">
            <Plus className="h-4 w-4 mr-2" />
            Add Fixture
          </Button>
        </div>
      </div>

      {validationErrors.length > 0 && (
        <Alert variant="destructive" className="animate-fade-in border-destructive/50 bg-destructive/10">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <ul className="list-disc list-inside space-y-1">
              {validationErrors.map((error, i) => (
                <li key={i}>{error}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      <Card className="glass-card animate-fade-in-up">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-accent" />
            Fixtures
          </CardTitle>
          <CardDescription>
            Enter team names and decimal odds for each fixture
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-border/50">
                  <TableHead className="w-[40px] text-muted-foreground">#</TableHead>
                  <TableHead className="text-muted-foreground">Home Team</TableHead>
                  <TableHead className="text-muted-foreground">Away Team</TableHead>
                  <TableHead className="w-[100px] text-right text-muted-foreground">Home</TableHead>
                  <TableHead className="w-[100px] text-right text-muted-foreground">Draw</TableHead>
                  <TableHead className="w-[100px] text-right text-muted-foreground">Away</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {fixtures.map((fixture, index) => (
                  <TableRow 
                    key={fixture.tempId} 
                    className="border-border/30 hover:bg-primary/5 transition-colors animate-fade-in"
                    style={{ animationDelay: `${0.05 * index}s` }}
                  >
                    <TableCell className="text-muted-foreground tabular-nums font-medium">
                      {index + 1}
                    </TableCell>
                    <TableCell>
                      <Input
                        value={fixture.homeTeam}
                        onChange={(e) => updateFixture(fixture.tempId, 'homeTeam', e.target.value)}
                        placeholder="Home team"
                        className="h-9 bg-background/50 border-border/50 focus:border-primary"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        value={fixture.awayTeam}
                        onChange={(e) => updateFixture(fixture.tempId, 'awayTeam', e.target.value)}
                        placeholder="Away team"
                        className="h-9 bg-background/50 border-border/50 focus:border-primary"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        step="0.01"
                        min="1.01"
                        value={fixture.homeOdds || ''}
                        onChange={(e) => updateFixture(fixture.tempId, 'homeOdds', parseOdds(e.target.value))}
                        placeholder="1.00"
                        className="h-9 text-right tabular-nums bg-background/50 border-border/50 focus:border-primary"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        step="0.01"
                        min="1.01"
                        value={fixture.drawOdds || ''}
                        onChange={(e) => updateFixture(fixture.tempId, 'drawOdds', parseOdds(e.target.value))}
                        placeholder="1.00"
                        className="h-9 text-right tabular-nums bg-background/50 border-border/50 focus:border-primary"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        step="0.01"
                        min="1.01"
                        value={fixture.awayOdds || ''}
                        onChange={(e) => updateFixture(fixture.tempId, 'awayOdds', parseOdds(e.target.value))}
                        placeholder="1.00"
                        className="h-9 text-right tabular-nums bg-background/50 border-border/50 focus:border-primary"
                      />
                    </TableCell>
                    <TableCell>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => removeFixture(fixture.tempId)}
                            disabled={fixtures.length === 1}
                            className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Remove fixture</TooltipContent>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
        <Button onClick={handleSubmit} disabled={!isValid} size="lg" className="btn-glow bg-primary text-primary-foreground">
          <Sparkles className="mr-2 h-5 w-5" />
          Calculate Probabilities
          <ArrowRight className="ml-2 h-5 w-5" />
        </Button>
      </div>

      {/* PDF Import Dialog */}
      <PDFJackpotImport 
        open={isPDFDialogOpen} 
        onOpenChange={setIsPDFDialogOpen}
        onImport={handlePDFImport}
      />
    </div>
  );
}
