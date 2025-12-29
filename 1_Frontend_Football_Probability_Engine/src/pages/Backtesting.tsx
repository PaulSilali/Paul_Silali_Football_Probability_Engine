import { useState } from 'react';
import { 
  History, 
  Upload, 
  FileText, 
  PenLine,
  Globe,
  Play,
  BarChart3,
  AlertCircle,
  Loader2,
  CheckCircle
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { toast } from 'sonner';
import { PDFResultsImport, type ParsedResult } from '@/components/PDFResultsImport';
import { ManualResultsEntry } from '@/components/ManualResultsEntry';
import { BacktestComparison } from '@/components/BacktestComparison';
import { WebScrapingImport } from '@/components/WebScrapingImport';

interface GeneratedProbability {
  matchId: string;
  homeTeam: string;
  awayTeam: string;
  sets: {
    setA: { H: number; D: number; A: number };
    setB: { H: number; D: number; A: number };
    setC: { H: number; D: number; A: number };
    setD: { H: number; D: number; A: number };
    setE: { H: number; D: number; A: number };
    setF: { H: number; D: number; A: number };
    setG: { H: number; D: number; A: number };
  };
  confidence: number;
}

// Simulated probability generation based on odds and historical patterns
const generateProbabilities = (results: ParsedResult[]): GeneratedProbability[] => {
  return results.map((result, idx) => {
    // Use odds if available, otherwise generate based on typical patterns
    let baseH = 0.40, baseD = 0.28, baseA = 0.32;
    
    if (result.homeOdds && result.drawOdds && result.awayOdds) {
      // Convert odds to implied probabilities (remove overround)
      const impliedH = 1 / result.homeOdds;
      const impliedD = 1 / result.drawOdds;
      const impliedA = 1 / result.awayOdds;
      const total = impliedH + impliedD + impliedA;
      
      baseH = impliedH / total;
      baseD = impliedD / total;
      baseA = impliedA / total;
    }

    // Generate variations for each set
    const addNoise = (base: number, factor: number) => 
      Math.max(0.05, Math.min(0.90, base + (Math.random() - 0.5) * factor));

    const normalize = (h: number, d: number, a: number) => {
      const total = h + d + a;
      return { H: h / total, D: d / total, A: a / total };
    };

    // Set A: Model-only (more variance from market)
    const setA = normalize(
      addNoise(baseH, 0.15),
      addNoise(baseD, 0.12),
      addNoise(baseA, 0.15)
    );

    // Set B: Market-adjusted (closest to odds)
    const setB = normalize(
      addNoise(baseH, 0.05),
      addNoise(baseD, 0.05),
      addNoise(baseA, 0.05)
    );

    // Set C: Conservative (compressed extremes)
    const setC = normalize(
      0.33 + (baseH - 0.33) * 0.6,
      0.34 + (baseD - 0.33) * 0.4,
      0.33 + (baseA - 0.33) * 0.6
    );

    // Set D: Market-only (pure odds)
    const setD = normalize(baseH, baseD, baseA);

    // Set E: High-confidence (amplified favorites)
    const maxProb = Math.max(baseH, baseD, baseA);
    const setE = normalize(
      baseH === maxProb ? baseH * 1.15 : baseH * 0.9,
      baseD === maxProb ? baseD * 1.15 : baseD * 0.85,
      baseA === maxProb ? baseA * 1.15 : baseA * 0.9
    );

    // Set F: Draw-enhanced
    const setF = normalize(
      baseH * 0.92,
      baseD * 1.25,
      baseA * 0.92
    );

    // Set G: Upset-biased (boost underdogs)
    const minProb = Math.min(baseH, baseA);
    const setG = normalize(
      baseH === minProb ? baseH * 1.3 : baseH * 0.85,
      baseD * 1.1,
      baseA === minProb ? baseA * 1.3 : baseA * 0.85
    );

    return {
      matchId: result.id,
      homeTeam: result.homeTeam,
      awayTeam: result.awayTeam,
      sets: { setA, setB, setC, setD, setE, setF, setG },
      confidence: 0.5 + Math.random() * 0.4,
    };
  });
};

export default function Backtesting() {
  const [inputMode, setInputMode] = useState<'pdf' | 'manual' | 'web'>('pdf');
  const [results, setResults] = useState<ParsedResult[]>([]);
  const [probabilities, setProbabilities] = useState<GeneratedProbability[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [hasRun, setHasRun] = useState(false);

  const handleResultsImported = (importedResults: ParsedResult[]) => {
    setResults(importedResults);
    setProbabilities([]);
    setHasRun(false);
  };

  const handleRunBacktest = async () => {
    if (results.length === 0) {
      toast.error('Please import or enter match results first');
      return;
    }

    setIsGenerating(true);
    
    // Simulate model inference time
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const generatedProbs = generateProbabilities(results);
    setProbabilities(generatedProbs);
    setHasRun(true);
    setIsGenerating(false);
    
    toast.success('Backtest complete!', {
      description: `Generated probabilities for ${results.length} matches across 7 sets`
    });
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 rounded-lg bg-primary/10">
              <History className="h-5 w-5 text-primary" />
            </div>
            <h1 className="text-2xl font-semibold gradient-text">Backtesting</h1>
          </div>
          <p className="text-sm text-muted-foreground">
            Test model probabilities against historical jackpot results
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {results.length > 0 && (
            <Badge variant="outline" className="gap-1">
              <CheckCircle className="h-3 w-3" />
              {results.length} matches loaded
            </Badge>
          )}
          <Button
            onClick={handleRunBacktest}
            disabled={results.length === 0 || isGenerating}
            className="btn-glow"
          >
            {isGenerating ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Run Backtest
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Workflow Info */}
      <Alert className="glass-card border-primary/20">
        <BarChart3 className="h-4 w-4" />
        <AlertTitle>How Backtesting Works</AlertTitle>
        <AlertDescription>
          <ol className="list-decimal list-inside space-y-1 mt-2 text-sm">
            <li>Import past jackpot results via PDF or manual entry</li>
            <li>System generates probabilities using all 7 sets (A-G)</li>
            <li>Compare predictions against actual outcomes</li>
            <li>Analyze which probability set performs best historically</li>
          </ol>
        </AlertDescription>
      </Alert>

      {/* Input Section */}
      {!hasRun && (
        <div className="animate-fade-in-up">
          <Tabs value={inputMode} onValueChange={(v) => setInputMode(v as 'pdf' | 'manual' | 'web')}>
            <TabsList className="mb-4">
              <TabsTrigger value="pdf" className="gap-2">
                <Upload className="h-4 w-4" />
                PDF/Image Import
              </TabsTrigger>
              <TabsTrigger value="manual" className="gap-2">
                <PenLine className="h-4 w-4" />
                Manual Entry
              </TabsTrigger>
              <TabsTrigger value="web" className="gap-2">
                <Globe className="h-4 w-4" />
                Web Import
              </TabsTrigger>
            </TabsList>

            <TabsContent value="pdf">
              <PDFResultsImport onResultsImported={handleResultsImported} />
            </TabsContent>

            <TabsContent value="manual">
              <ManualResultsEntry onResultsSubmitted={handleResultsImported} />
            </TabsContent>

            <TabsContent value="web">
              <WebScrapingImport onResultsImported={handleResultsImported} />
            </TabsContent>
          </Tabs>
        </div>
      )}

      {/* Results Preview (before running backtest) */}
      {results.length > 0 && !hasRun && (
        <Card className="glass-card animate-fade-in-up">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              Loaded Results Summary
            </CardTitle>
            <CardDescription>
              Ready to generate probabilities and compare
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-lg bg-muted/30 text-center">
                <p className="text-2xl font-bold tabular-nums">{results.length}</p>
                <p className="text-sm text-muted-foreground">Total Matches</p>
              </div>
              <div className="p-4 rounded-lg bg-green-500/10 text-center">
                <p className="text-2xl font-bold tabular-nums text-green-600">
                  {results.filter(r => r.result === 'H').length}
                </p>
                <p className="text-sm text-muted-foreground">Home Wins</p>
              </div>
              <div className="p-4 rounded-lg bg-yellow-500/10 text-center">
                <p className="text-2xl font-bold tabular-nums text-yellow-600">
                  {results.filter(r => r.result === 'D').length}
                </p>
                <p className="text-sm text-muted-foreground">Draws</p>
              </div>
              <div className="p-4 rounded-lg bg-blue-500/10 text-center">
                <p className="text-2xl font-bold tabular-nums text-blue-600">
                  {results.filter(r => r.result === 'A').length}
                </p>
                <p className="text-sm text-muted-foreground">Away Wins</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Backtest Comparison Results */}
      {hasRun && probabilities.length > 0 && (
        <div className="animate-fade-in-up">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Backtest Results</h2>
            <Button 
              variant="outline" 
              onClick={() => {
                setHasRun(false);
                setResults([]);
                setProbabilities([]);
              }}
            >
              New Backtest
            </Button>
          </div>
          <BacktestComparison results={results} probabilities={probabilities} />
        </div>
      )}
    </div>
  );
}
