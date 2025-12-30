import { useState, useEffect, useMemo } from 'react';
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
  CheckCircle,
  Database,
  Calendar,
  TrendingUp,
  RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { PDFResultsImport, type ParsedResult } from '@/components/PDFResultsImport';
import { ManualResultsEntry } from '@/components/ManualResultsEntry';
import { BacktestComparison } from '@/components/BacktestComparison';
import { WebScrapingImport } from '@/components/WebScrapingImport';
import apiClient from '@/services/api';

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

interface SavedResult {
  id: number;
  name: string;
  description?: string;
  jackpotId: string;
  selections: Record<string, Record<string, string>>;
  actualResults: Record<string, string>;
  scores: Record<string, { correct: number; total: number }>;
  modelVersion?: string;
  totalFixtures: number;
  createdAt: string;
  updatedAt: string;
}

// Convert result format (1/X/2 to H/D/A)
const convertResult = (result: '1' | 'X' | '2'): 'H' | 'D' | 'A' => {
  if (result === '1') return 'H';
  if (result === 'X') return 'D';
  return 'A';
};

// Simulated probability generation (for PDF/manual/web import mode)
const generateProbabilities = (results: ParsedResult[]): GeneratedProbability[] => {
  return results.map((result, idx) => {
    let baseH = 0.40, baseD = 0.28, baseA = 0.32;
    
    if (result.homeOdds && result.drawOdds && result.awayOdds) {
      const impliedH = 1 / result.homeOdds;
      const impliedD = 1 / result.drawOdds;
      const impliedA = 1 / result.awayOdds;
      const total = impliedH + impliedD + impliedA;
      
      baseH = impliedH / total;
      baseD = impliedD / total;
      baseA = impliedA / total;
    }

    const addNoise = (base: number, factor: number) => 
      Math.max(0.05, Math.min(0.90, base + (Math.random() - 0.5) * factor));

    const normalize = (h: number, d: number, a: number) => {
      const total = h + d + a;
      return { H: h / total, D: d / total, A: a / total };
    };

    const setA = normalize(addNoise(baseH, 0.15), addNoise(baseD, 0.12), addNoise(baseA, 0.15));
    const setB = normalize(addNoise(baseH, 0.05), addNoise(baseD, 0.05), addNoise(baseA, 0.05));
    const setC = normalize(0.33 + (baseH - 0.33) * 0.6, 0.34 + (baseD - 0.33) * 0.4, 0.33 + (baseA - 0.33) * 0.6);
    const setD = normalize(baseH, baseD, baseA);
    const maxProb = Math.max(baseH, baseD, baseA);
    const setE = normalize(
      baseH === maxProb ? baseH * 1.15 : baseH * 0.9,
      baseD === maxProb ? baseD * 1.15 : baseD * 0.85,
      baseA === maxProb ? baseA * 1.15 : baseA * 0.9
    );
    const setF = normalize(baseH * 0.92, baseD * 1.25, baseA * 0.92);
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
  const [inputMode, setInputMode] = useState<'saved' | 'pdf' | 'manual' | 'web'>('saved');
  const [results, setResults] = useState<ParsedResult[]>([]);
  const [probabilities, setProbabilities] = useState<GeneratedProbability[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [hasRun, setHasRun] = useState(false);
  
  // Saved results mode
  const [savedResults, setSavedResults] = useState<SavedResult[]>([]);
  const [selectedSavedResult, setSelectedSavedResult] = useState<number | null>(null);
  const [loadingSavedResults, setLoadingSavedResults] = useState(false);
  const [loadingProbabilities, setLoadingProbabilities] = useState(false);

  // Load saved results on mount
  useEffect(() => {
    const loadSavedResults = async () => {
      try {
        setLoadingSavedResults(true);
        const response = await apiClient.getAllSavedResults(500);
        if (response.success && response.data?.results) {
          // Filter to only results with actual outcomes
          const withActuals = response.data.results.filter((r: SavedResult) => 
            r.actualResults && Object.keys(r.actualResults).length > 0
          );
          setSavedResults(withActuals);
          if (withActuals.length > 0 && !selectedSavedResult) {
            setSelectedSavedResult(withActuals[0].id);
          }
        }
      } catch (err: any) {
        console.error('Error loading saved results:', err);
        toast.error('Failed to load saved results');
      } finally {
        setLoadingSavedResults(false);
      }
    };

    if (inputMode === 'saved') {
      loadSavedResults();
    }
  }, [inputMode]);

  // Load probabilities when saved result is selected
  useEffect(() => {
    const loadBacktestData = async () => {
      if (inputMode !== 'saved' || !selectedSavedResult) return;

      const savedResult = savedResults.find(r => r.id === selectedSavedResult);
      if (!savedResult || !savedResult.actualResults) return;

      try {
        setLoadingProbabilities(true);
        
        // Load probabilities for this jackpot
        const probResponse = await apiClient.getProbabilities(savedResult.jackpotId);
        const probData = (probResponse as any).success ? (probResponse as any).data : probResponse;
        
        if (!probData || !probData.probabilitySets || !probData.fixtures) {
          toast.error('Failed to load probabilities for this jackpot');
          return;
        }

        // Convert to ParsedResult format for actual results
        const parsedResults: ParsedResult[] = probData.fixtures.map((fixture: any, idx: number) => {
          const fixtureId = fixture.id || String(idx + 1);
          const actualResult = savedResult.actualResults[fixtureId];
          
          // Try index-based matching if ID doesn't match
          let actual: 'H' | 'D' | 'A' | null = null;
          if (actualResult) {
            actual = convertResult(actualResult as '1' | 'X' | '2');
          } else {
            // Try by index
            const actualEntries = Object.entries(savedResult.actualResults);
            if (idx < actualEntries.length) {
              actual = convertResult(actualEntries[idx][1] as '1' | 'X' | '2');
            }
          }

          return {
            id: fixtureId,
            homeTeam: fixture.homeTeam || '',
            awayTeam: fixture.awayTeam || '',
            result: actual || 'H', // Default if not found
            homeOdds: fixture.odds?.home,
            drawOdds: fixture.odds?.draw,
            awayOdds: fixture.odds?.away,
          };
        });

        // Convert probabilities to GeneratedProbability format
        const generatedProbs: GeneratedProbability[] = probData.fixtures.map((fixture: any, idx: number) => {
          const fixtureId = fixture.id || String(idx + 1);
          
          const getSetProbs = (setId: string) => {
            const setProbs = probData.probabilitySets[setId];
            if (!setProbs || idx >= setProbs.length) {
              return { H: 0.33, D: 0.34, A: 0.33 };
            }
            const prob = setProbs[idx];
            return {
              H: (prob.homeWinProbability || 0) / 100,
              D: (prob.drawProbability || 0) / 100,
              A: (prob.awayWinProbability || 0) / 100,
            };
          };

          return {
            matchId: fixtureId,
            homeTeam: fixture.homeTeam || '',
            awayTeam: fixture.awayTeam || '',
            sets: {
              setA: getSetProbs('A'),
              setB: getSetProbs('B'),
              setC: getSetProbs('C'),
              setD: getSetProbs('D'),
              setE: getSetProbs('E'),
              setF: getSetProbs('F'),
              setG: getSetProbs('G'),
            },
            confidence: 0.7, // Could calculate from entropy if available
          };
        });

        setResults(parsedResults);
        setProbabilities(generatedProbs);
        setHasRun(true);
        
        toast.success('Backtest loaded!', {
          description: `Analyzing ${parsedResults.length} matches from ${savedResult.name}`
        });
      } catch (err: any) {
        console.error('Error loading backtest data:', err);
        toast.error('Failed to load backtest data');
      } finally {
        setLoadingProbabilities(false);
      }
    };

    loadBacktestData();
  }, [selectedSavedResult, inputMode, savedResults]);

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

  const selectedResult = useMemo(() => {
    return savedResults.find(r => r.id === selectedSavedResult);
  }, [savedResults, selectedSavedResult]);

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
          {inputMode !== 'saved' && (
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
          )}
        </div>
      </div>

      {/* Workflow Info */}
      <Alert className="glass-card border-primary/20">
        <BarChart3 className="h-4 w-4" />
        <AlertTitle>How Backtesting Works</AlertTitle>
        <AlertDescription>
          <ol className="list-decimal list-inside space-y-1 mt-2 text-sm">
            {inputMode === 'saved' ? (
              <>
                <li>Select a saved jackpot result with actual outcomes</li>
                <li>System loads real probabilities calculated for that jackpot</li>
                <li>Compare predictions against actual outcomes automatically</li>
                <li>Analyze which probability set performed best</li>
              </>
            ) : (
              <>
                <li>Import past jackpot results via PDF or manual entry</li>
                <li>System generates probabilities using all 7 sets (A-G)</li>
                <li>Compare predictions against actual outcomes</li>
                <li>Analyze which probability set performs best historically</li>
              </>
            )}
          </ol>
        </AlertDescription>
      </Alert>

      {/* Input Section */}
      {!hasRun && (
        <div className="animate-fade-in-up">
          <Tabs value={inputMode} onValueChange={(v) => {
            setInputMode(v as 'saved' | 'pdf' | 'manual' | 'web');
            setResults([]);
            setProbabilities([]);
            setHasRun(false);
          }}>
            <TabsList className="mb-4">
              <TabsTrigger value="saved" className="gap-2">
                <Database className="h-4 w-4" />
                Saved Results
              </TabsTrigger>
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

            <TabsContent value="saved">
              <Card className="glass-card">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="h-5 w-5 text-primary" />
                    Select Saved Result
                  </CardTitle>
                  <CardDescription>
                    Choose a saved jackpot result with actual outcomes to backtest
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {loadingSavedResults ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-primary" />
                    </div>
                  ) : savedResults.length === 0 ? (
                    <Alert>
                      <AlertCircle className="h-4 w-4" />
                      <AlertTitle>No saved results found</AlertTitle>
                      <AlertDescription>
                        Save probability results with actual outcomes in the Probability Output page first.
                      </AlertDescription>
                    </Alert>
                  ) : (
                    <>
                      <div className="space-y-2">
                        <Label>Select Result</Label>
                        <Select
                          value={selectedSavedResult?.toString() || ''}
                          onValueChange={(v) => setSelectedSavedResult(parseInt(v))}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select a saved result" />
                          </SelectTrigger>
                          <SelectContent>
                            {savedResults.map((result) => (
                              <SelectItem key={result.id} value={result.id.toString()}>
                                <div className="flex flex-col">
                                  <span className="font-medium">{result.name}</span>
                                  <span className="text-xs text-muted-foreground">
                                    {result.jackpotId} • {new Date(result.createdAt).toLocaleDateString()}
                                  </span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      {selectedResult && (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4">
                          <div className="p-4 rounded-lg bg-muted/30 text-center">
                            <p className="text-2xl font-bold tabular-nums">{selectedResult.totalFixtures}</p>
                            <p className="text-sm text-muted-foreground">Total Matches</p>
                          </div>
                          <div className="p-4 rounded-lg bg-primary/10 text-center">
                            <p className="text-2xl font-bold tabular-nums text-primary">
                              {Object.keys(selectedResult.actualResults || {}).length}
                            </p>
                            <p className="text-sm text-muted-foreground">With Results</p>
                          </div>
                          <div className="p-4 rounded-lg bg-green-500/10 text-center">
                            <p className="text-2xl font-bold tabular-nums text-green-600">
                              {selectedResult.scores?.B?.correct || 0}
                            </p>
                            <p className="text-sm text-muted-foreground">Set B Correct</p>
                          </div>
                          <div className="p-4 rounded-lg bg-blue-500/10 text-center">
                            <p className="text-2xl font-bold tabular-nums text-blue-600">
                              {selectedResult.modelVersion || 'N/A'}
                            </p>
                            <p className="text-sm text-muted-foreground">Model Version</p>
                          </div>
                        </div>
                      )}

                      {loadingProbabilities && (
                        <div className="flex items-center justify-center py-4">
                          <Loader2 className="h-5 w-5 animate-spin text-primary mr-2" />
                          <span className="text-sm text-muted-foreground">Loading probabilities...</span>
                        </div>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

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
      {results.length > 0 && !hasRun && inputMode !== 'saved' && (
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
            <div>
              <h2 className="text-lg font-semibold">Backtest Results</h2>
              {selectedResult && (
                <p className="text-sm text-muted-foreground">
                  {selectedResult.name} • {new Date(selectedResult.createdAt).toLocaleDateString()}
                </p>
              )}
            </div>
            <Button 
              variant="outline" 
              onClick={() => {
                setHasRun(false);
                setResults([]);
                setProbabilities([]);
                if (inputMode === 'saved') {
                  setSelectedSavedResult(null);
                }
              }}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              New Backtest
            </Button>
          </div>
          <BacktestComparison results={results} probabilities={probabilities} />
        </div>
      )}
    </div>
  );
}
