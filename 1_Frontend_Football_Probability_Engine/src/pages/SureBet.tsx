import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { 
  Target, Upload, Loader2, CheckCircle2, AlertTriangle, 
  Calculator, TrendingUp, Sparkles, Zap, DollarSign,
  Play, Filter, X, CheckCircle, AlertCircle, Download,
  Save, FolderOpen, Trophy, Star, FileText
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageLayout } from '@/components/layouts/PageLayout';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/services/api';
import { Checkbox } from '@/components/ui/checkbox';

interface Game {
  id: string;
  homeTeam: string;
  awayTeam: string;
  draw?: string;
  homeOdds?: number | null;
  drawOdds?: number | null;
  awayOdds?: number | null;
  doubleChance1X?: number | null;
  doubleChance12?: number | null;
  doubleChanceX2?: number | null;
  isValidated?: boolean;
  needsTraining?: boolean;
  isTrained?: boolean;
  hasData?: boolean;
  confidence?: number;
  homeProbability?: number;
  drawProbability?: number;
  awayProbability?: number;
  predictedOutcome?: '1' | 'X' | '2';
  predictedDoubleChance?: '1X' | '12' | 'X2';
  doubleChanceConfidence?: number;
  isSureBet?: boolean;
  selected?: boolean;
  selectedDoubleChance?: boolean;
}

export default function SureBet() {
  const { toast } = useToast();
  const [bulkInput, setBulkInput] = useState('');
  const [isBulkDialogOpen, setIsBulkDialogOpen] = useState(false);
  const [games, setGames] = useState<Game[]>([]);
  const [isValidating, setIsValidating] = useState(false);
  const [isTraining, setIsTraining] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [sureBets, setSureBets] = useState<Game[]>([]);
  const [doubleChanceBets, setDoubleChanceBets] = useState<Game[]>([]);
  const [betAmount, setBetAmount] = useState<number>(100);
  const [betAmountKshs, setBetAmountKshs] = useState<number>(100);
  const [selectedGames, setSelectedGames] = useState<Set<string>>(new Set());
  const [selectedDoubleChanceGames, setSelectedDoubleChanceGames] = useState<Set<string>>(new Set());
  const [removedGames, setRemovedGames] = useState<Game[]>([]);
  const [savedLists, setSavedLists] = useState<any[]>([]);
  const [isLoadingSavedLists, setIsLoadingSavedLists] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saveListName, setSaveListName] = useState('');
  const [saveListDescription, setSaveListDescription] = useState('');
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
  const [isImportingPDF, setIsImportingPDF] = useState(false);
  const pdfFileInputRef = useRef<HTMLInputElement>(null);
  const [restoredStateInfo, setRestoredStateInfo] = useState<{
    sureBets: number;
    games: number;
    doubleChanceBets: number;
  } | null>(null);

  const handleBulkImport = useCallback(() => {
    if (!bulkInput.trim()) {
      toast({
        title: 'Error',
        description: 'Please paste game data first',
        variant: 'destructive',
      });
      return;
    }

    const lines = bulkInput.trim().split(/\r?\n/).filter(line => line.trim());
    if (lines.length < 2) {
      toast({
        title: 'Error',
        description: 'Invalid format. Expected header row and at least one data row.',
        variant: 'destructive',
      });
      return;
    }

    // Parse header - match Jackpot Input format: HomeTeam, AwayTeam, HomeOdds, DrawOdds, AwayOdds
    const parseOdds = (value: string): number => {
      const parsed = parseFloat(value);
      return isNaN(parsed) || parsed <= 0 ? 0 : parsed;
    };

    const newGames: Game[] = [];
    for (let i = 0; i < lines.length && newGames.length < 200; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      
      const parts = line.split(/[,\t]/).map(p => p.trim());
      if (parts.length >= 5) {
        newGames.push({
          id: `game-${i + 1}`,
          homeTeam: parts[0] || '',
          awayTeam: parts[1] || '',
          homeOdds: parseOdds(parts[2]),
          drawOdds: parseOdds(parts[3]),
          awayOdds: parseOdds(parts[4]),
        });
      } else if (parts.length >= 2) {
        // Allow games without odds (will use default/model probabilities)
        newGames.push({
          id: `game-${i + 1}`,
          homeTeam: parts[0] || '',
          awayTeam: parts[1] || '',
          homeOdds: parts[2] ? parseOdds(parts[2]) : undefined,
          drawOdds: parts[3] ? parseOdds(parts[3]) : undefined,
          awayOdds: parts[4] ? parseOdds(parts[4]) : undefined,
        });
      }
    }

    if (newGames.length > 0) {
      setGames(newGames);
      setBulkInput('');
      setIsBulkDialogOpen(false);
      toast({
        title: 'Success',
        description: `Imported ${newGames.length} games`,
      });
    }
  }, [bulkInput, toast]);

  const handleValidateGames = useCallback(async () => {
    if (games.length === 0) {
      toast({
        title: 'Error',
        description: 'Please import games first',
        variant: 'destructive',
      });
      return;
    }

    setIsValidating(true);
    try {
      const response = await apiClient.validateSureBetGames({ games });
      if (response.success && response.data) {
        setGames(response.data.validatedGames || games);
        toast({
          title: 'Validation Complete',
          description: `Validated ${games.length} games`,
        });
      }
    } catch (error: any) {
      toast({
        title: 'Validation Failed',
        description: error.message || 'Failed to validate games',
        variant: 'destructive',
      });
    } finally {
      setIsValidating(false);
    }
  }, [games, toast]);

  const handleTrainMissingGames = useCallback(async () => {
    const needsTraining = games.filter(g => g.needsTraining && !g.isTrained);
    if (needsTraining.length === 0) {
      toast({
        title: 'Info',
        description: 'No games need training',
      });
      return;
    }

    setIsTraining(true);
    try {
      const response = await apiClient.trainSureBetGames({ 
        gameIds: needsTraining.map(g => g.id) 
      });
      if (response.success) {
        // Refresh games after training
        await handleValidateGames();
        toast({
          title: 'Training Complete',
          description: `Trained ${needsTraining.length} games`,
        });
      }
    } catch (error: any) {
      toast({
        title: 'Training Failed',
        description: error.message || 'Failed to train games',
        variant: 'destructive',
      });
    } finally {
      setIsTraining(false);
    }
  }, [games, toast, handleValidateGames]);

  const handleDownloadAndValidate = useCallback(async () => {
    const noDataGames = games.filter(g => !g.hasData);
    if (noDataGames.length === 0) {
      toast({
        title: 'Info',
        description: 'No games need data download',
      });
      return;
    }

    setIsDownloading(true);
    try {
      const response = await apiClient.downloadAndValidateSureBetGames({ 
        games: noDataGames 
      });
      if (response.success && response.data) {
        // Update games list with validated games
        const validatedGames = response.data.validatedGames || [];
        const removedGames = response.data.removedGames || [];
        
        // Remove games that were removed
        setGames(prev => prev.filter(g => !removedGames.some(r => r.id === g.id)));
        
        // Update validated games
        setGames(prev => prev.map(g => {
          const validated = validatedGames.find(v => v.id === g.id);
          return validated ? { ...g, ...validated } : g;
        }));
        
        // Store removed games for display
        setRemovedGames(removedGames);
        
        toast({
          title: 'Download Complete',
          description: `Downloaded ${response.data.downloaded || 0} leagues, validated ${validatedGames.length} games, removed ${removedGames.length} games`,
        });
      }
    } catch (error: any) {
      toast({
        title: 'Download Failed',
        description: error.message || 'Failed to download and validate games',
        variant: 'destructive',
      });
    } finally {
      setIsDownloading(false);
    }
  }, [games, toast]);

  const handleAnalyzeSureBets = useCallback(async () => {
    const validGames = games.filter(g => g.hasData && g.isValidated);
    if (validGames.length === 0) {
      toast({
        title: 'Error',
        description: 'No validated games with data available',
        variant: 'destructive',
      });
      return;
    }

    setIsAnalyzing(true);
    try {
      const response = await apiClient.analyzeSureBets({ 
        games: validGames,
        maxResults: 20 
      });
      if (response.success && response.data) {
        const singleOutcomeBets = response.data.sureBets || [];
        
        // Preserve double chance odds from original games and calculate implied odds if missing
        const gamesWithDC: Game[] = singleOutcomeBets.map(bet => {
          const originalGame = validGames.find(g => g.id === bet.id);
          
          // Calculate implied odds from probabilities if odds are missing
          let homeOdds = bet.homeOdds;
          let drawOdds = bet.drawOdds;
          let awayOdds = bet.awayOdds;
          
          if ((!homeOdds || homeOdds <= 0) && bet.homeProbability && bet.homeProbability > 0) {
            homeOdds = 100 / bet.homeProbability; // Implied odds from probability
          }
          if ((!drawOdds || drawOdds <= 0) && bet.drawProbability && bet.drawProbability > 0) {
            drawOdds = 100 / bet.drawProbability;
          }
          if ((!awayOdds || awayOdds <= 0) && bet.awayProbability && bet.awayProbability > 0) {
            awayOdds = 100 / bet.awayProbability;
          }
          
          // Fallback to defaults if still missing
          if (!homeOdds || homeOdds <= 0) homeOdds = 2.0;
          if (!drawOdds || drawOdds <= 0) drawOdds = 3.0;
          if (!awayOdds || awayOdds <= 0) awayOdds = 2.5;
          
          return {
            ...bet,
            homeOdds,
            drawOdds,
            awayOdds,
            doubleChance1X: originalGame?.doubleChance1X ?? null,
            doubleChance12: originalGame?.doubleChance12 ?? null,
            doubleChanceX2: originalGame?.doubleChanceX2 ?? null,
          } as Game;
        });
        
        setSureBets(gamesWithDC);
        
        // Generate double chance bets from single outcome bets
        const dcBets: Game[] = [];
        gamesWithDC.forEach(game => {
          const homeProb = game.homeProbability || 0;
          const drawProb = game.drawProbability || 0;
          const awayProb = game.awayProbability || 0;
          
          // Calculate all double chance probabilities upfront
          const prob1X = homeProb + drawProb;
          const prob12 = homeProb + awayProb;
          const probX2 = drawProb + awayProb;
          
          // Determine best double chance based on predicted outcome
          let predictedDC: '1X' | '12' | 'X2' | null = null;
          let dcOdds: number | null = null;
          let dcConfidence = 0;
          
          if (game.predictedOutcome === '1') {
            // If predicted Home, offer 1X (Home or Draw) or 12 (Home or Away)
            // Choose the one with higher probability
            if (prob1X > prob12) {
              predictedDC = '1X';
              dcConfidence = ((prob1X / 100 - 0.5) / 0.5) * 100;
              // Use provided odds or calculate implied odds
              dcOdds = game.doubleChance1X || (prob1X > 0 ? 100 / prob1X : 1.5);
            } else {
              predictedDC = '12';
              dcConfidence = ((prob12 / 100 - 0.5) / 0.5) * 100;
              dcOdds = game.doubleChance12 || (prob12 > 0 ? 100 / prob12 : 1.5);
            }
          } else if (game.predictedOutcome === 'X') {
            // If predicted Draw, offer 1X (Home or Draw) or X2 (Draw or Away)
            if (prob1X > probX2) {
              predictedDC = '1X';
              dcConfidence = ((prob1X / 100 - 0.5) / 0.5) * 100;
              dcOdds = game.doubleChance1X || (prob1X > 0 ? 100 / prob1X : 1.5);
            } else {
              predictedDC = 'X2';
              dcConfidence = ((probX2 / 100 - 0.5) / 0.5) * 100;
              dcOdds = game.doubleChanceX2 || (probX2 > 0 ? 100 / probX2 : 1.5);
            }
          } else if (game.predictedOutcome === '2') {
            // If predicted Away, offer 12 (Home or Away) or X2 (Draw or Away)
            if (prob12 > probX2) {
              predictedDC = '12';
              dcConfidence = ((prob12 / 100 - 0.5) / 0.5) * 100;
              dcOdds = game.doubleChance12 || (prob12 > 0 ? 100 / prob12 : 1.5);
            } else {
              predictedDC = 'X2';
              dcConfidence = ((probX2 / 100 - 0.5) / 0.5) * 100;
              dcOdds = game.doubleChanceX2 || (probX2 > 0 ? 100 / probX2 : 1.5);
            }
          }
          
          // Always generate double chance bet if we have a prediction
          if (predictedDC && dcOdds && dcOdds > 0) {
            // Ensure minimum confidence
            const finalConfidence = Math.max(dcConfidence, 10);
            
            dcBets.push({
              ...game,
              predictedDoubleChance: predictedDC,
              doubleChanceConfidence: finalConfidence,
              doubleChance1X: predictedDC === '1X' ? dcOdds : (game.doubleChance1X || null),
              doubleChance12: predictedDC === '12' ? dcOdds : (game.doubleChance12 || null),
              doubleChanceX2: predictedDC === 'X2' ? dcOdds : (game.doubleChanceX2 || null),
            });
          }
        });
        
        setDoubleChanceBets(dcBets);
        
        toast({
          title: 'Analysis Complete',
          description: `Found ${singleOutcomeBets.length} single bets and ${dcBets.length} double chance bets`,
        });
      }
    } catch (error: any) {
      toast({
        title: 'Analysis Failed',
        description: error.message || 'Failed to analyze sure bets',
        variant: 'destructive',
      });
    } finally {
      setIsAnalyzing(false);
    }
  }, [games, toast]);

  const toggleGameSelection = useCallback((gameId: string) => {
    setSelectedGames(prev => {
      const newSet = new Set(prev);
      if (newSet.has(gameId)) {
        newSet.delete(gameId);
      } else {
        newSet.add(gameId);
      }
      return newSet;
    });
  }, []);

  const bettingCalculations = useMemo(() => {
    const selected = sureBets.filter(g => selectedGames.has(g.id));
    if (selected.length === 0) return null;

    const totalOdds = selected.reduce((acc, g) => {
      const odds = g.predictedOutcome === '1' ? g.homeOdds :
                   g.predictedOutcome === 'X' ? g.drawOdds :
                   g.awayOdds;
      return acc * (odds || 1);
    }, 1);

    const totalProbability = selected.reduce((acc, g) => {
      const prob = g.predictedOutcome === '1' ? (g.homeProbability || 0) :
                   g.predictedOutcome === 'X' ? (g.drawProbability || 0) :
                   (g.awayProbability || 0);
      return acc * (prob / 100);
    }, 1);

    const expectedAmountKshs = betAmountKshs * totalOdds;
    const weightedAmountKshs = betAmountKshs * totalProbability;

    return {
      selectedCount: selected.length,
      totalOdds: totalOdds.toFixed(2),
      totalProbability: (totalProbability * 100).toFixed(2),
      expectedAmountKshs: expectedAmountKshs.toFixed(2),
      weightedAmountKshs: weightedAmountKshs.toFixed(2),
      averageConfidence: selected.reduce((acc, g) => acc + (g.confidence || 0), 0) / selected.length,
    };
  }, [sureBets, selectedGames, betAmountKshs]);

  // PDF Import handler
  const handlePDFImport = useCallback(async (file: File) => {
    if (!file) {
      toast({
        title: 'Error',
        description: 'No file selected',
        variant: 'destructive',
      });
      return;
    }

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast({
        title: 'Error',
        description: 'Please select a PDF file',
        variant: 'destructive',
      });
      return;
    }

    setIsImportingPDF(true);
    try {
      console.log('Importing PDF:', file.name, file.size, 'bytes');
      const response = await apiClient.importPDFGames(file);
      console.log('PDF import response:', response);
      
      if (response.success && response.data) {
        const pdfGames: Game[] = response.data.games.map((g: any) => ({
          id: g.id || `game-${g.gameId}`,
          homeTeam: g.homeTeam,
          awayTeam: g.awayTeam,
          homeOdds: g.homeOdds,
          drawOdds: g.drawOdds,
          awayOdds: g.awayOdds,
          doubleChance1X: g.doubleChance1X,
          doubleChance12: g.doubleChance12,
          doubleChanceX2: g.doubleChanceX2,
        }));
        
        console.log('Parsed games from PDF:', pdfGames.length);
        setGames(prev => [...prev, ...pdfGames]);
        
        // Show removed games info if any
        const removedCount = response.data.removedGames?.length || 0;
        let description = `Imported ${pdfGames.length} game${pdfGames.length !== 1 ? 's' : ''} from PDF`;
        if (removedCount > 0) {
          description += `. Removed ${removedCount} game${removedCount !== 1 ? 's' : ''} that have started or start within 10 minutes.`;
        }
        
        toast({
          title: 'PDF Imported Successfully',
          description: description,
        });
      } else {
        toast({
          title: 'PDF Import Failed',
          description: response.message || 'Failed to parse PDF. Please check the format.',
          variant: 'destructive',
        });
      }
    } catch (error: any) {
      console.error('PDF import error:', error);
      toast({
        title: 'PDF Import Failed',
        description: error.message || error.response?.data?.detail || 'Failed to import PDF. Please check the console for details.',
        variant: 'destructive',
      });
    } finally {
      setIsImportingPDF(false);
    }
  }, [toast]);

  const toggleDoubleChanceSelection = useCallback((gameId: string) => {
    setSelectedDoubleChanceGames(prev => {
      const newSet = new Set(prev);
      if (newSet.has(gameId)) {
        newSet.delete(gameId);
      } else {
        newSet.add(gameId);
      }
      return newSet;
    });
  }, []);

  // Section 1: Single Outcome Calculations
  const section1Calculations = useMemo(() => {
    const selected = sureBets.filter(g => selectedGames.has(g.id));
    if (selected.length === 0) return null;

    const totalOdds = selected.reduce((acc, g) => {
      const odds = g.predictedOutcome === '1' ? g.homeOdds :
                   g.predictedOutcome === 'X' ? g.drawOdds :
                   g.awayOdds;
      return acc * (odds || 1);
    }, 1);

    const totalProbability = selected.reduce((acc, g) => {
      const prob = g.predictedOutcome === '1' ? (g.homeProbability || 0) :
                   g.predictedOutcome === 'X' ? (g.drawProbability || 0) :
                   (g.awayProbability || 0);
      return acc * (prob / 100);
    }, 1);

    const expectedAmountKshs = betAmountKshs * totalOdds;
    const weightedAmountKshs = betAmountKshs * totalProbability;

    return {
      selectedCount: selected.length,
      totalOdds: totalOdds.toFixed(2),
      totalProbability: (totalProbability * 100).toFixed(2),
      expectedAmountKshs: expectedAmountKshs.toFixed(2),
      weightedAmountKshs: weightedAmountKshs.toFixed(2),
      averageConfidence: selected.reduce((acc, g) => acc + (g.confidence || 0), 0) / selected.length,
    };
  }, [sureBets, selectedGames, betAmountKshs]);

  // Section 2: Best of Best Single Outcome (Top 10 with best odds from all games)
  const section2BestOfBest = useMemo(() => {
    return [...sureBets]
      .map(game => {
        // Get the odds for the predicted outcome
        const odds = game.predictedOutcome === '1' ? (game.homeOdds || 0) :
                     game.predictedOutcome === 'X' ? (game.drawOdds || 0) :
                     (game.awayOdds || 0);
        return { ...game, predictedOdds: odds };
      })
      .sort((a, b) => {
        // Sort by: first confidence (descending), then odds (descending)
        const confidenceDiff = (b.confidence || 0) - (a.confidence || 0);
        if (Math.abs(confidenceDiff) > 5) {
          return confidenceDiff; // If confidence difference is significant, use that
        }
        // If confidence is similar, prefer higher odds
        return (b.predictedOdds || 0) - (a.predictedOdds || 0);
      })
      .slice(0, 10);
  }, [sureBets]);

  const section2Calculations = useMemo(() => {
    if (section2BestOfBest.length === 0) return null;

    const totalOdds = section2BestOfBest.reduce((acc, g) => {
      const odds = g.predictedOutcome === '1' ? g.homeOdds :
                   g.predictedOutcome === 'X' ? g.drawOdds :
                   g.awayOdds;
      return acc * (odds || 1);
    }, 1);

    const totalProbability = section2BestOfBest.reduce((acc, g) => {
      const prob = g.predictedOutcome === '1' ? (g.homeProbability || 0) :
                   g.predictedOutcome === 'X' ? (g.drawProbability || 0) :
                   (g.awayProbability || 0);
      return acc * (prob / 100);
    }, 1);

    const expectedAmountKshs = betAmountKshs * totalOdds;
    const weightedAmountKshs = betAmountKshs * totalProbability;

    return {
      selectedCount: section2BestOfBest.length,
      totalOdds: totalOdds.toFixed(2),
      totalProbability: (totalProbability * 100).toFixed(2),
      expectedAmountKshs: expectedAmountKshs.toFixed(2),
      weightedAmountKshs: weightedAmountKshs.toFixed(2),
      averageConfidence: section2BestOfBest.reduce((acc, g) => acc + (g.confidence || 0), 0) / section2BestOfBest.length,
    };
  }, [section2BestOfBest, betAmountKshs]);

  // Section 3: Double Chance Calculations
  const section3Calculations = useMemo(() => {
    const selected = doubleChanceBets.filter(g => selectedDoubleChanceGames.has(g.id));
    if (selected.length === 0) return null;

    const totalOdds = selected.reduce((acc, g) => {
      const odds = g.predictedDoubleChance === '1X' ? g.doubleChance1X :
                   g.predictedDoubleChance === '12' ? g.doubleChance12 :
                   g.doubleChanceX2;
      return acc * (odds || 1);
    }, 1);

    const totalProbability = selected.reduce((acc, g) => {
      const homeProb = g.homeProbability || 0;
      const drawProb = g.drawProbability || 0;
      const awayProb = g.awayProbability || 0;
      
      let prob = 0;
      if (g.predictedDoubleChance === '1X') {
        prob = homeProb + drawProb;
      } else if (g.predictedDoubleChance === '12') {
        prob = homeProb + awayProb;
      } else if (g.predictedDoubleChance === 'X2') {
        prob = drawProb + awayProb;
      }
      return acc * (prob / 100);
    }, 1);

    const expectedAmountKshs = betAmountKshs * totalOdds;
    const weightedAmountKshs = betAmountKshs * totalProbability;

    return {
      selectedCount: selected.length,
      totalOdds: totalOdds.toFixed(2),
      totalProbability: (totalProbability * 100).toFixed(2),
      expectedAmountKshs: expectedAmountKshs.toFixed(2),
      weightedAmountKshs: weightedAmountKshs.toFixed(2),
      averageConfidence: selected.reduce((acc, g) => acc + (g.doubleChanceConfidence || 0), 0) / selected.length,
    };
  }, [doubleChanceBets, selectedDoubleChanceGames, betAmountKshs]);

  // Section 4: Best of Best Double Chance (Top 5 from all games)
  const section4BestOfBest = useMemo(() => {
    return [...doubleChanceBets]
      .sort((a, b) => (b.doubleChanceConfidence || 0) - (a.doubleChanceConfidence || 0))
      .slice(0, 5);
  }, [doubleChanceBets]);

  const section4Calculations = useMemo(() => {
    if (section4BestOfBest.length === 0) return null;

    const totalOdds = section4BestOfBest.reduce((acc, g) => {
      const odds = g.predictedDoubleChance === '1X' ? g.doubleChance1X :
                   g.predictedDoubleChance === '12' ? g.doubleChance12 :
                   g.doubleChanceX2;
      return acc * (odds || 1);
    }, 1);

    const totalProbability = section4BestOfBest.reduce((acc, g) => {
      const homeProb = g.homeProbability || 0;
      const drawProb = g.drawProbability || 0;
      const awayProb = g.awayProbability || 0;
      
      let prob = 0;
      if (g.predictedDoubleChance === '1X') {
        prob = homeProb + drawProb;
      } else if (g.predictedDoubleChance === '12') {
        prob = homeProb + awayProb;
      } else if (g.predictedDoubleChance === 'X2') {
        prob = drawProb + awayProb;
      }
      return acc * (prob / 100);
    }, 1);

    const expectedAmountKshs = betAmountKshs * totalOdds;
    const weightedAmountKshs = betAmountKshs * totalProbability;

    return {
      selectedCount: section4BestOfBest.length,
      totalOdds: totalOdds.toFixed(2),
      totalProbability: (totalProbability * 100).toFixed(2),
      expectedAmountKshs: expectedAmountKshs.toFixed(2),
      weightedAmountKshs: weightedAmountKshs.toFixed(2),
      averageConfidence: section4BestOfBest.reduce((acc, g) => acc + (g.doubleChanceConfidence || 0), 0) / section4BestOfBest.length,
    };
  }, [section4BestOfBest, betAmountKshs]);

  // Load saved lists on mount
  const loadSavedLists = useCallback(async () => {
    setIsLoadingSavedLists(true);
    try {
      const response = await apiClient.getSavedSureBetLists();
      if (response.success && response.data) {
        setSavedLists(response.data.savedLists || []);
      }
    } catch (error: any) {
      console.error('Failed to load saved lists:', error);
    } finally {
      setIsLoadingSavedLists(false);
    }
  }, []);

  // Save state to sessionStorage
  const saveStateToSessionStorage = useCallback((state: {
    games?: Game[];
    sureBets?: Game[];
    doubleChanceBets?: Game[];
    betAmountKshs?: number;
    selectedGames?: string[];
    selectedDoubleChanceGames?: string[];
  }) => {
    try {
      const stateToSave = {
        games: state.games || games,
        sureBets: state.sureBets || sureBets,
        doubleChanceBets: state.doubleChanceBets || doubleChanceBets,
        betAmountKshs: state.betAmountKshs !== undefined ? state.betAmountKshs : betAmountKshs,
        selectedGames: state.selectedGames || Array.from(selectedGames),
        selectedDoubleChanceGames: state.selectedDoubleChanceGames || Array.from(selectedDoubleChanceGames),
      };
      sessionStorage.setItem('sureBetState', JSON.stringify(stateToSave));
    } catch (error) {
      console.error('Failed to save state to sessionStorage:', error);
    }
  }, [games, sureBets, doubleChanceBets, betAmountKshs, selectedGames, selectedDoubleChanceGames]);

  // Load state from sessionStorage
  const loadStateFromSessionStorage = useCallback(() => {
    try {
      const savedState = sessionStorage.getItem('sureBetState');
      if (savedState) {
        const parsed = JSON.parse(savedState);
        let restored = false;
        const restoredInfo: { sureBets: number; games: number; doubleChanceBets: number } = {
          sureBets: 0,
          games: 0,
          doubleChanceBets: 0,
        };
        
        if (parsed.games && parsed.games.length > 0) {
          setGames(parsed.games);
          restoredInfo.games = parsed.games.length;
          restored = true;
        }
        if (parsed.sureBets && parsed.sureBets.length > 0) {
          setSureBets(parsed.sureBets);
          restoredInfo.sureBets = parsed.sureBets.length;
          restored = true;
        }
        if (parsed.doubleChanceBets && parsed.doubleChanceBets.length > 0) {
          setDoubleChanceBets(parsed.doubleChanceBets);
          restoredInfo.doubleChanceBets = parsed.doubleChanceBets.length;
          restored = true;
        }
        if (parsed.betAmountKshs !== undefined) {
          setBetAmountKshs(parsed.betAmountKshs);
        }
        if (parsed.selectedGames && parsed.selectedGames.length > 0) {
          setSelectedGames(new Set(parsed.selectedGames));
        }
        if (parsed.selectedDoubleChanceGames && parsed.selectedDoubleChanceGames.length > 0) {
          setSelectedDoubleChanceGames(new Set(parsed.selectedDoubleChanceGames));
        }
        
        if (restored) {
          setRestoredStateInfo(restoredInfo);
          // Auto-hide after 10 seconds
          setTimeout(() => {
            setRestoredStateInfo(null);
          }, 10000);
        }
        
        return restored;
      }
    } catch (error) {
      console.error('Failed to load state from sessionStorage:', error);
    }
    return false;
  }, []);

  // Save current sure bet list
  const handleSaveList = useCallback(async () => {
    if (!saveListName.trim()) {
      toast({
        title: 'Error',
        description: 'Please enter a name for the list',
        variant: 'destructive',
      });
      return;
    }

    if (sureBets.length === 0) {
      toast({
        title: 'Error',
        description: 'No sure bets to save',
        variant: 'destructive',
      });
      return;
    }

    setIsSaving(true);
    try {
      const selected = sureBets.filter(g => selectedGames.has(g.id));
      const response = await apiClient.saveSureBetList({
        name: saveListName,
        description: saveListDescription,
        games: sureBets,
        betAmountKshs: betAmountKshs,
        selectedGameIds: Array.from(selectedGames),
        totalOdds: bettingCalculations ? parseFloat(bettingCalculations.totalOdds) : undefined,
        totalProbability: bettingCalculations ? parseFloat(bettingCalculations.totalProbability) / 100 : undefined,
        expectedAmountKshs: bettingCalculations ? parseFloat(bettingCalculations.expectedAmountKshs) : undefined,
        weightedAmountKshs: bettingCalculations ? parseFloat(bettingCalculations.weightedAmountKshs) : undefined,
      });

      if (response.success) {
        toast({
          title: 'Success',
          description: 'Sure bet list saved successfully',
        });
        setSaveDialogOpen(false);
        setSaveListName('');
        setSaveListDescription('');
        await loadSavedLists();
        // Also save to sessionStorage
        saveStateToSessionStorage({});
      }
    } catch (error: any) {
      toast({
        title: 'Save Failed',
        description: error.message || 'Failed to save sure bet list',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  }, [saveListName, saveListDescription, sureBets, selectedGames, betAmountKshs, bettingCalculations, toast, loadSavedLists, saveStateToSessionStorage]);

  // Load a saved list
  const handleLoadList = useCallback(async (listId: number) => {
    try {
      const response = await apiClient.getSavedSureBetList(listId);
      if (response.success && response.data) {
        const loadedGames = response.data.games || [];
        
        // Set sure bets
        setSureBets(loadedGames);
        
        // Restore bet amount
        if (response.data.betAmountKshs) {
          setBetAmountKshs(response.data.betAmountKshs);
        }
        
        // Restore selected games
        if (response.data.selectedGameIds) {
          setSelectedGames(new Set(response.data.selectedGameIds));
        }
        
        // Regenerate double chance bets from loaded sure bets
        const dcBets: Game[] = [];
        loadedGames.forEach(game => {
          const homeProb = game.homeProbability || 0;
          const drawProb = game.drawProbability || 0;
          const awayProb = game.awayProbability || 0;
          
          // Calculate all double chance probabilities upfront
          const prob1X = homeProb + drawProb;
          const prob12 = homeProb + awayProb;
          const probX2 = drawProb + awayProb;
          
          // Determine best double chance based on predicted outcome
          let predictedDC: '1X' | '12' | 'X2' | null = null;
          let dcOdds: number | null = null;
          let dcConfidence = 0;
          
          if (game.predictedOutcome === '1') {
            if (prob1X > prob12) {
              predictedDC = '1X';
              dcConfidence = ((prob1X / 100 - 0.5) / 0.5) * 100;
              dcOdds = game.doubleChance1X || (prob1X > 0 ? 100 / prob1X : 1.5);
            } else {
              predictedDC = '12';
              dcConfidence = ((prob12 / 100 - 0.5) / 0.5) * 100;
              dcOdds = game.doubleChance12 || (prob12 > 0 ? 100 / prob12 : 1.5);
            }
          } else if (game.predictedOutcome === 'X') {
            if (prob1X > probX2) {
              predictedDC = '1X';
              dcConfidence = ((prob1X / 100 - 0.5) / 0.5) * 100;
              dcOdds = game.doubleChance1X || (prob1X > 0 ? 100 / prob1X : 1.5);
            } else {
              predictedDC = 'X2';
              dcConfidence = ((probX2 / 100 - 0.5) / 0.5) * 100;
              dcOdds = game.doubleChanceX2 || (probX2 > 0 ? 100 / probX2 : 1.5);
            }
          } else if (game.predictedOutcome === '2') {
            if (prob12 > probX2) {
              predictedDC = '12';
              dcConfidence = ((prob12 / 100 - 0.5) / 0.5) * 100;
              dcOdds = game.doubleChance12 || (prob12 > 0 ? 100 / prob12 : 1.5);
            } else {
              predictedDC = 'X2';
              dcConfidence = ((probX2 / 100 - 0.5) / 0.5) * 100;
              dcOdds = game.doubleChanceX2 || (probX2 > 0 ? 100 / probX2 : 1.5);
            }
          }
          
          if (predictedDC && dcOdds && dcOdds > 0) {
            const finalConfidence = Math.max(dcConfidence, 10);
            dcBets.push({
              ...game,
              predictedDoubleChance: predictedDC,
              doubleChanceConfidence: finalConfidence,
              doubleChance1X: predictedDC === '1X' ? dcOdds : (game.doubleChance1X || null),
              doubleChance12: predictedDC === '12' ? dcOdds : (game.doubleChance12 || null),
              doubleChanceX2: predictedDC === 'X2' ? dcOdds : (game.doubleChanceX2 || null),
            });
          }
        });
        
        setDoubleChanceBets(dcBets);
        
        // Restore original games state if available (for validation status)
        if (response.data.originalGames) {
          setGames(response.data.originalGames);
        } else {
          // If original games not saved, use sure bets as games
          setGames(loadedGames);
        }
        
        // Save to sessionStorage for persistence
        saveStateToSessionStorage({
          games: response.data.originalGames || loadedGames,
          sureBets: loadedGames,
          doubleChanceBets: dcBets,
          betAmountKshs: response.data.betAmountKshs || betAmountKshs,
          selectedGames: Array.from(response.data.selectedGameIds || []),
          selectedDoubleChanceGames: [],
        });
        
        setLoadDialogOpen(false);
        toast({
          title: 'Success',
          description: 'Sure bet list loaded successfully',
        });
      }
    } catch (error: any) {
      toast({
        title: 'Load Failed',
        description: error.message || 'Failed to load sure bet list',
        variant: 'destructive',
      });
    }
  }, [toast, betAmountKshs, saveStateToSessionStorage]);

  const validatedCount = games.filter(g => g.isValidated).length;
  const needsTrainingCount = games.filter(g => g.needsTraining && !g.isTrained).length;
  const hasDataCount = games.filter(g => g.hasData).length;

  // Save state whenever key state changes
  useEffect(() => {
    if (sureBets.length > 0 || games.length > 0) {
      saveStateToSessionStorage({});
    }
  }, [sureBets, doubleChanceBets, games, betAmountKshs, selectedGames, selectedDoubleChanceGames, saveStateToSessionStorage]);

  // Load saved lists and restore state on mount
  useEffect(() => {
    loadSavedLists();
    // Try to restore state from sessionStorage
    loadStateFromSessionStorage();
  }, [loadSavedLists, loadStateFromSessionStorage]);

  return (
    <PageLayout title="Sure Bet Analyzer">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold gradient-text flex items-center gap-3">
              <Target className="h-8 w-8 text-primary" />
              Sure Bet Analyzer
            </h1>
            <p className="text-muted-foreground mt-2">
              Find high-confidence sure bets from up to 200 games
            </p>
          </div>
          <div className="flex gap-2">
            <Dialog open={isBulkDialogOpen} onOpenChange={setIsBulkDialogOpen}>
              <DialogTrigger asChild>
                <Button className="btn-glow bg-primary text-primary-foreground gap-2">
                  <Upload className="h-4 w-4" />
                  Bulk Import Games
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-3xl glass-card-elevated">
              <DialogHeader>
                <DialogTitle className="gradient-text">Bulk Import Games</DialogTitle>
                <DialogDescription>
                  Paste fixtures in CSV or tab-separated format: HomeTeam, AwayTeam, HomeOdds, DrawOdds, AwayOdds
                </DialogDescription>
              </DialogHeader>
              <Textarea
                placeholder="Arsenal, Chelsea, 2.10, 3.40, 3.20
Liverpool, Man City, 2.80, 3.30, 2.45
Barcelona, Real Madrid, 2.50, 3.20, 2.80"
                value={bulkInput}
                onChange={(e) => setBulkInput(e.target.value)}
                className="min-h-[300px] font-mono text-sm bg-background/50"
              />
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsBulkDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleBulkImport} disabled={!bulkInput.trim()}>
                  Import {bulkInput.trim().split(/\r?\n/).length - 1} Games
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <input
            type="file"
            accept=".pdf"
            ref={pdfFileInputRef}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                handlePDFImport(file);
                // Reset the input so the same file can be selected again
                if (pdfFileInputRef.current) {
                  pdfFileInputRef.current.value = '';
                }
              }
            }}
            className="hidden"
          />
          <Button
            onClick={() => pdfFileInputRef.current?.click()}
            disabled={isImportingPDF}
            variant="outline"
            className="gap-2"
          >
            {isImportingPDF ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Importing PDF...
              </>
            ) : (
              <>
                <FileText className="h-4 w-4" />
                Import PDF
              </>
            )}
          </Button>
        </div>
        </div>

        {/* State Restoration Banner - appears after header */}
        {restoredStateInfo && (
          <Alert className="bg-green-500/10 border-green-500/30">
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <AlertDescription className="text-green-700 dark:text-green-400">
              <div className="flex items-center justify-between">
                <div>
                  <strong>State Restored!</strong> Your previous session has been restored:
                  {restoredStateInfo.games > 0 && ` ${restoredStateInfo.games} game${restoredStateInfo.games !== 1 ? 's' : ''}`}
                  {restoredStateInfo.sureBets > 0 && `, ${restoredStateInfo.sureBets} sure bet${restoredStateInfo.sureBets !== 1 ? 's' : ''}`}
                  {restoredStateInfo.doubleChanceBets > 0 && `, ${restoredStateInfo.doubleChanceBets} double chance bet${restoredStateInfo.doubleChanceBets !== 1 ? 's' : ''}`}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setRestoredStateInfo(null)}
                  className="text-green-700 dark:text-green-400 hover:text-green-800 dark:hover:text-green-300"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </AlertDescription>
          </Alert>
        )}

        {/* Stats Cards */}
        {games.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="glass-card border-primary/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-muted-foreground">Total Games</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{games.length}</div>
              </CardContent>
            </Card>
            <Card className="glass-card border-green-500/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-muted-foreground">Validated</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">{validatedCount}</div>
              </CardContent>
            </Card>
            <Card className="glass-card border-yellow-500/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-muted-foreground">Need Training</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-yellow-600">{needsTrainingCount}</div>
              </CardContent>
            </Card>
            <Card className="glass-card border-blue-500/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-muted-foreground">Has Data</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600">{hasDataCount}</div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Action Buttons */}
        {games.length > 0 && (
          <Card className="glass-card border-primary/30">
            <CardHeader>
              <CardTitle>Game Processing</CardTitle>
              <CardDescription>
                Validate games, train missing data, and analyze sure bets
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              <Button
                onClick={handleValidateGames}
                disabled={isValidating || isTraining || isAnalyzing || isDownloading}
                variant="outline"
                className="gap-2"
              >
                {isValidating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Validating...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4" />
                    Validate Games
                  </>
                )}
              </Button>
              {needsTrainingCount > 0 && (
                <Button
                  onClick={handleTrainMissingGames}
                  disabled={isValidating || isTraining || isAnalyzing || isDownloading}
                  variant="outline"
                  className="gap-2"
                >
                  {isTraining ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Training...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" />
                      Train Missing ({needsTrainingCount})
                    </>
                  )}
                </Button>
              )}
              {hasDataCount < games.length && (
                <Button
                  onClick={handleDownloadAndValidate}
                  disabled={isValidating || isTraining || isAnalyzing || isDownloading}
                  variant="outline"
                  className="gap-2 border-yellow-500/30 text-yellow-600 hover:bg-yellow-500/10"
                >
                  {isDownloading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Downloading...
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4" />
                      Download Data & Validate ({games.length - hasDataCount})
                    </>
                  )}
                </Button>
              )}
              {hasDataCount > 0 && (
                <Button
                  onClick={handleAnalyzeSureBets}
                  disabled={isValidating || isTraining || isAnalyzing || isDownloading}
                  className="btn-glow bg-primary text-primary-foreground gap-2"
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Target className="h-4 w-4" />
                      Analyze Sure Bets
                    </>
                  )}
                </Button>
              )}
            </CardContent>
          </Card>
        )}

        {/* Bet Amount Input at Top */}
        {(sureBets.length > 0 || doubleChanceBets.length > 0) && (
          <Card className="glass-card border-primary/30 mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calculator className="h-5 w-5 text-primary" />
                Bet Amount (KShs)
              </CardTitle>
              <CardDescription>
                Enter your bet amount to calculate potential winnings for all sections below
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <Label htmlFor="global-bet-amount-kshs" className="w-32">Amount:</Label>
                <Input
                  id="global-bet-amount-kshs"
                  type="number"
                  value={betAmountKshs}
                  onChange={(e) => setBetAmountKshs(parseFloat(e.target.value) || 0)}
                  className="max-w-[200px]"
                  min="0"
                  step="1"
                />
                <span className="text-muted-foreground">KShs</span>
              </div>
            </CardContent>
          </Card>
        )}

        {/* SECTION 1: Single Outcome Sure Bets */}
        {sureBets.length > 0 && (
          <>
            <Card className="glass-card border-accent/30">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Zap className="h-5 w-5 text-accent" />
                      Section 1: Single Outcome Sure Bets ({sureBets.length} games)
                    </CardTitle>
                    <CardDescription>
                      Select games to include in your bet (up to 20). Each game has one predicted outcome (Home/Draw/Away).
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Dialog open={loadDialogOpen} onOpenChange={setLoadDialogOpen}>
                      <DialogTrigger asChild>
                        <Button variant="outline" size="sm" className="gap-2">
                          <FolderOpen className="h-4 w-4" />
                          Load Saved
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-2xl">
                        <DialogHeader>
                          <DialogTitle>Load Saved Sure Bet List</DialogTitle>
                          <DialogDescription>
                            Select a saved list to load
                          </DialogDescription>
                        </DialogHeader>
                        <div className="max-h-[400px] overflow-y-auto space-y-2">
                          {isLoadingSavedLists ? (
                            <div className="flex items-center justify-center py-8">
                              <Loader2 className="h-6 w-6 animate-spin" />
                            </div>
                          ) : savedLists.length === 0 ? (
                            <div className="text-center py-8 text-muted-foreground">
                              No saved lists found
                            </div>
                          ) : (
                            savedLists.map((list) => (
                              <Card
                                key={list.id}
                                className="cursor-pointer hover:bg-accent/10 transition-colors"
                                onClick={() => handleLoadList(list.id)}
                              >
                                <CardContent className="p-4">
                                  <div className="flex items-center justify-between">
                                    <div>
                                      <div className="font-semibold">{list.name}</div>
                                      {list.description && (
                                        <div className="text-sm text-muted-foreground mt-1">
                                          {list.description}
                                        </div>
                                      )}
                                      <div className="text-xs text-muted-foreground mt-2">
                                        {list.selectedGameIds?.length || 0} games selected • 
                                        {list.betAmountKshs ? ` ${list.betAmountKshs.toLocaleString()} KShs` : ' No bet amount'} • 
                                        {new Date(list.createdAt).toLocaleDateString()}
                                      </div>
                                    </div>
                                    <Button variant="ghost" size="sm">
                                      Load
                                    </Button>
                                  </div>
                                </CardContent>
                              </Card>
                            ))
                          )}
                        </div>
                        <DialogFooter>
                          <Button variant="outline" onClick={() => setLoadDialogOpen(false)}>
                            Cancel
                          </Button>
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>
                    <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
                      <DialogTrigger asChild>
                        <Button variant="outline" size="sm" className="gap-2">
                          <Save className="h-4 w-4" />
                          Save List
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Save Sure Bet List</DialogTitle>
                          <DialogDescription>
                            Save the current sure bet list for later use
                          </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4">
                          <div>
                            <Label htmlFor="save-name">Name *</Label>
                            <Input
                              id="save-name"
                              value={saveListName}
                              onChange={(e) => setSaveListName(e.target.value)}
                              placeholder="e.g., Top 10 Sure Bets - Jan 2026"
                            />
                          </div>
                          <div>
                            <Label htmlFor="save-description">Description</Label>
                            <Textarea
                              id="save-description"
                              value={saveListDescription}
                              onChange={(e) => setSaveListDescription(e.target.value)}
                              placeholder="Optional description..."
                              rows={3}
                            />
                          </div>
                        </div>
                        <DialogFooter>
                          <Button variant="outline" onClick={() => setSaveDialogOpen(false)}>
                            Cancel
                          </Button>
                          <Button onClick={handleSaveList} disabled={isSaving || !saveListName.trim()}>
                            {isSaving ? (
                              <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Saving...
                              </>
                            ) : (
                              <>
                                <Save className="h-4 w-4 mr-2" />
                                Save
                              </>
                            )}
                          </Button>
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[50px]">Select</TableHead>
                        <TableHead>Home Team</TableHead>
                        <TableHead>Away Team</TableHead>
                        <TableHead>Prediction</TableHead>
                        <TableHead className="text-right">Confidence</TableHead>
                        <TableHead className="text-right">Probability</TableHead>
                        <TableHead className="text-right">Odds</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sureBets.map((game) => (
                        <TableRow
                          key={game.id}
                          className={selectedGames.has(game.id) ? 'bg-primary/10' : ''}
                        >
                          <TableCell>
                            <Checkbox
                              checked={selectedGames.has(game.id)}
                              onCheckedChange={() => toggleGameSelection(game.id)}
                              disabled={selectedGames.size >= 20 && !selectedGames.has(game.id)}
                            />
                          </TableCell>
                          <TableCell className="font-medium">{game.homeTeam}</TableCell>
                          <TableCell>{game.awayTeam}</TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className={
                                game.predictedOutcome === '1' ? 'bg-chart-1/20 text-chart-1 border-chart-1/50' :
                                game.predictedOutcome === 'X' ? 'bg-chart-3/20 text-chart-3 border-chart-3/50' :
                                'bg-chart-2/20 text-chart-2 border-chart-2/50'
                              }
                            >
                              {game.predictedOutcome === '1' ? 'Home' :
                               game.predictedOutcome === 'X' ? 'Draw' : 'Away'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <span className="font-semibold">{(game.confidence || 0).toFixed(1)}%</span>
                          </TableCell>
                          <TableCell className="text-right">
                            {game.predictedOutcome === '1' ? (game.homeProbability || 0).toFixed(1) :
                             game.predictedOutcome === 'X' ? (game.drawProbability || 0).toFixed(1) :
                             (game.awayProbability || 0).toFixed(1)}%
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex flex-col gap-1">
                              <div className={game.predictedOutcome === '1' ? 'font-semibold text-primary' : 'text-xs text-muted-foreground'}>
                                H: {game.homeOdds ? game.homeOdds.toFixed(2) : '-'}
                              </div>
                              <div className={game.predictedOutcome === 'X' ? 'font-semibold text-primary' : 'text-xs text-muted-foreground'}>
                                D: {game.drawOdds ? game.drawOdds.toFixed(2) : '-'}
                              </div>
                              <div className={game.predictedOutcome === '2' ? 'font-semibold text-primary' : 'text-xs text-muted-foreground'}>
                                A: {game.awayOdds ? game.awayOdds.toFixed(2) : '-'}
                              </div>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>

            {/* Section 1 Calculations */}
            {section1Calculations && (
              <Card className="glass-card border-primary/30">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Calculator className="h-5 w-5 text-primary" />
                    Section 1 Calculations
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground">Selected Games</div>
                      <div className="text-2xl font-bold">{section1Calculations.selectedCount}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Total Odds</div>
                      <div className="text-2xl font-bold text-primary">{section1Calculations.totalOdds}x</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Total Probability</div>
                      <div className="text-2xl font-bold">{section1Calculations.totalProbability}%</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Avg Confidence</div>
                      <div className="text-2xl font-bold text-green-600">{section1Calculations.averageConfidence.toFixed(1)}%</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t">
                    <Card className="bg-primary/10 border-primary/30">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Expected Amount (KShs)</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-3xl font-bold text-primary flex items-center gap-2">
                          <DollarSign className="h-6 w-6" />
                          {parseFloat(section1Calculations.expectedAmountKshs).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Bet Amount × Total Odds
                        </div>
                      </CardContent>
                    </Card>
                    <Card className="bg-accent/10 border-accent/30">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Weighted Amount (KShs)</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-3xl font-bold text-accent flex items-center gap-2">
                          <TrendingUp className="h-6 w-6" />
                          {parseFloat(section1Calculations.weightedAmountKshs).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Bet Amount × Total Probability
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* SECTION 2: Best of Best Single Outcome */}
        {sureBets.length > 0 && section2BestOfBest.length > 0 && (
          <>
            <Card className="glass-card border-yellow-500/30 bg-gradient-to-br from-yellow-500/10 to-transparent">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Trophy className="h-5 w-5 text-yellow-600" />
                  Section 2: Best of the Best - Single Outcome
                </CardTitle>
                <CardDescription>
                  Top {section2BestOfBest.length} highest confidence games from Section 1
                </CardDescription>
              </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {section2BestOfBest.map((game, idx) => (
                      <Card key={game.id} className="bg-background/50 border-primary/20">
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <Star className="h-4 w-4 text-yellow-600 fill-yellow-600" />
                              <span className="font-semibold text-sm">#{idx + 1}</span>
                            </div>
                            <Badge className="bg-yellow-600/20 text-yellow-700 border-yellow-600/30">
                              {(game.confidence || 0).toFixed(1)}% confidence
                            </Badge>
                          </div>
                          <div className="space-y-1">
                            <div className="font-medium">{game.homeTeam} vs {game.awayTeam}</div>
                            <div className="flex items-center gap-2">
                              <Badge
                                variant="outline"
                                className={
                                  game.predictedOutcome === '1' ? 'bg-chart-1/20 text-chart-1 border-chart-1/50' :
                                  game.predictedOutcome === 'X' ? 'bg-chart-3/20 text-chart-3 border-chart-3/50' :
                                  'bg-chart-2/20 text-chart-2 border-chart-2/50'
                                }
                              >
                                {game.predictedOutcome === '1' ? 'Home' :
                                 game.predictedOutcome === 'X' ? 'Draw' : 'Away'}
                              </Badge>
                              <span className="text-sm text-muted-foreground">
                                {game.predictedOutcome === '1' ? (game.homeProbability || 0).toFixed(1) :
                                 game.predictedOutcome === 'X' ? (game.drawProbability || 0).toFixed(1) :
                                 (game.awayProbability || 0).toFixed(1)}% prob
                              </span>
                            </div>
                            {game.predictedOutcome === '1' && game.homeOdds && (
                              <div className="text-xs text-muted-foreground">Odds: {game.homeOdds.toFixed(2)}</div>
                            )}
                            {game.predictedOutcome === 'X' && game.drawOdds && (
                              <div className="text-xs text-muted-foreground">Odds: {game.drawOdds.toFixed(2)}</div>
                            )}
                            {game.predictedOutcome === '2' && game.awayOdds && (
                              <div className="text-xs text-muted-foreground">Odds: {game.awayOdds.toFixed(2)}</div>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </CardContent>
              </Card>

            {/* Section 2 Calculations */}
            {section2Calculations && (
              <Card className="glass-card border-yellow-500/30">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Calculator className="h-5 w-5 text-yellow-600" />
                    Section 2 Calculations
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground">Selected Games</div>
                      <div className="text-2xl font-bold">{section2Calculations.selectedCount}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Total Odds</div>
                      <div className="text-2xl font-bold text-primary">{section2Calculations.totalOdds}x</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Total Probability</div>
                      <div className="text-2xl font-bold">{section2Calculations.totalProbability}%</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Avg Confidence</div>
                      <div className="text-2xl font-bold text-green-600">{section2Calculations.averageConfidence.toFixed(1)}%</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t">
                    <Card className="bg-primary/10 border-primary/30">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Expected Amount (KShs)</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-3xl font-bold text-primary flex items-center gap-2">
                          <DollarSign className="h-6 w-6" />
                          {parseFloat(section2Calculations.expectedAmountKshs).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Bet Amount × Total Odds
                        </div>
                      </CardContent>
                    </Card>
                    <Card className="bg-accent/10 border-accent/30">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Weighted Amount (KShs)</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-3xl font-bold text-accent flex items-center gap-2">
                          <TrendingUp className="h-6 w-6" />
                          {parseFloat(section2Calculations.weightedAmountKshs).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Bet Amount × Total Probability
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* SECTION 3: Double Chance Sure Bets */}
        {doubleChanceBets.length > 0 && (
          <>
            <Card className="glass-card border-blue-500/30">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-blue-600" />
                      Section 3: Double Chance Sure Bets ({doubleChanceBets.length} games)
                    </CardTitle>
                    <CardDescription>
                      Select games to include in your double chance bet (up to 20). Each game has a double chance prediction (1X, 12, or X2).
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[50px]">Select</TableHead>
                        <TableHead>Home Team</TableHead>
                        <TableHead>Away Team</TableHead>
                        <TableHead>Double Chance</TableHead>
                        <TableHead className="text-right">Confidence</TableHead>
                        <TableHead className="text-right">Probability</TableHead>
                        <TableHead className="text-right">Odds</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {doubleChanceBets.map((game) => (
                        <TableRow
                          key={game.id}
                          className={selectedDoubleChanceGames.has(game.id) ? 'bg-primary/10' : ''}
                        >
                          <TableCell>
                            <Checkbox
                              checked={selectedDoubleChanceGames.has(game.id)}
                              onCheckedChange={() => toggleDoubleChanceSelection(game.id)}
                              disabled={selectedDoubleChanceGames.size >= 20 && !selectedDoubleChanceGames.has(game.id)}
                            />
                          </TableCell>
                          <TableCell className="font-medium">{game.homeTeam}</TableCell>
                          <TableCell>{game.awayTeam}</TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className="bg-blue-500/20 text-blue-700 border-blue-500/50"
                            >
                              {game.predictedDoubleChance}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <span className="font-semibold">{(game.doubleChanceConfidence || 0).toFixed(1)}%</span>
                          </TableCell>
                          <TableCell className="text-right">
                            {game.predictedDoubleChance === '1X' ? ((game.homeProbability || 0) + (game.drawProbability || 0)).toFixed(1) :
                             game.predictedDoubleChance === '12' ? ((game.homeProbability || 0) + (game.awayProbability || 0)).toFixed(1) :
                             ((game.drawProbability || 0) + (game.awayProbability || 0)).toFixed(1)}%
                          </TableCell>
                          <TableCell className="text-right">
                            <span className="font-semibold">
                              {game.predictedDoubleChance === '1X' ? (game.doubleChance1X ? game.doubleChance1X.toFixed(2) : '-') :
                               game.predictedDoubleChance === '12' ? (game.doubleChance12 ? game.doubleChance12.toFixed(2) : '-') :
                               (game.doubleChanceX2 ? game.doubleChanceX2.toFixed(2) : '-')}
                            </span>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>

            {/* Section 3 Calculations */}
            {section3Calculations && (
              <Card className="glass-card border-blue-500/30">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Calculator className="h-5 w-5 text-blue-600" />
                    Section 3 Calculations
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground">Selected Games</div>
                      <div className="text-2xl font-bold">{section3Calculations.selectedCount}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Total Odds</div>
                      <div className="text-2xl font-bold text-primary">{section3Calculations.totalOdds}x</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Total Probability</div>
                      <div className="text-2xl font-bold">{section3Calculations.totalProbability}%</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Avg Confidence</div>
                      <div className="text-2xl font-bold text-green-600">{section3Calculations.averageConfidence.toFixed(1)}%</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t">
                    <Card className="bg-primary/10 border-primary/30">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Expected Amount (KShs)</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-3xl font-bold text-primary flex items-center gap-2">
                          <DollarSign className="h-6 w-6" />
                          {parseFloat(section3Calculations.expectedAmountKshs).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Bet Amount × Total Odds
                        </div>
                      </CardContent>
                    </Card>
                    <Card className="bg-accent/10 border-accent/30">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Weighted Amount (KShs)</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-3xl font-bold text-accent flex items-center gap-2">
                          <TrendingUp className="h-6 w-6" />
                          {parseFloat(section3Calculations.weightedAmountKshs).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Bet Amount × Total Probability
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* SECTION 4: Best of Best Double Chance */}
        {doubleChanceBets.length > 0 && section4BestOfBest.length > 0 && (
          <>
            <Card className="glass-card border-purple-500/30 bg-gradient-to-br from-purple-500/10 to-transparent">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Trophy className="h-5 w-5 text-purple-600" />
                  Section 4: Best of the Best - Double Chance
                </CardTitle>
                <CardDescription>
                  Top {section4BestOfBest.length} highest confidence double chance games from Section 3
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {section4BestOfBest.map((game, idx) => (
                    <Card key={game.id} className="bg-background/50 border-primary/20">
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Star className="h-4 w-4 text-purple-600 fill-purple-600" />
                            <span className="font-semibold text-sm">#{idx + 1}</span>
                          </div>
                          <Badge className="bg-purple-600/20 text-purple-700 border-purple-600/30">
                            {(game.doubleChanceConfidence || 0).toFixed(1)}% confidence
                          </Badge>
                        </div>
                        <div className="space-y-1">
                          <div className="font-medium">{game.homeTeam} vs {game.awayTeam}</div>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="bg-blue-500/20 text-blue-700 border-blue-500/50">
                              {game.predictedDoubleChance}
                            </Badge>
                            <span className="text-sm text-muted-foreground">
                              {game.predictedDoubleChance === '1X' ? ((game.homeProbability || 0) + (game.drawProbability || 0)).toFixed(1) :
                               game.predictedDoubleChance === '12' ? ((game.homeProbability || 0) + (game.awayProbability || 0)).toFixed(1) :
                               ((game.drawProbability || 0) + (game.awayProbability || 0)).toFixed(1)}% prob
                            </span>
                          </div>
                          {game.predictedDoubleChance === '1X' && game.doubleChance1X && (
                            <div className="text-xs text-muted-foreground">Odds: {game.doubleChance1X.toFixed(2)}</div>
                          )}
                          {game.predictedDoubleChance === '12' && game.doubleChance12 && (
                            <div className="text-xs text-muted-foreground">Odds: {game.doubleChance12.toFixed(2)}</div>
                          )}
                          {game.predictedDoubleChance === 'X2' && game.doubleChanceX2 && (
                            <div className="text-xs text-muted-foreground">Odds: {game.doubleChanceX2.toFixed(2)}</div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Section 4 Calculations */}
            {section4Calculations && (
              <Card className="glass-card border-purple-500/30">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Calculator className="h-5 w-5 text-purple-600" />
                    Section 4 Calculations
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground">Selected Games</div>
                      <div className="text-2xl font-bold">{section4Calculations.selectedCount}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Total Odds</div>
                      <div className="text-2xl font-bold text-primary">{section4Calculations.totalOdds}x</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Total Probability</div>
                      <div className="text-2xl font-bold">{section4Calculations.totalProbability}%</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Avg Confidence</div>
                      <div className="text-2xl font-bold text-green-600">{section4Calculations.averageConfidence.toFixed(1)}%</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t">
                    <Card className="bg-primary/10 border-primary/30">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Expected Amount (KShs)</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-3xl font-bold text-primary flex items-center gap-2">
                          <DollarSign className="h-6 w-6" />
                          {parseFloat(section4Calculations.expectedAmountKshs).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Bet Amount × Total Odds
                        </div>
                      </CardContent>
                    </Card>
                    <Card className="bg-accent/10 border-accent/30">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Weighted Amount (KShs)</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-3xl font-bold text-accent flex items-center gap-2">
                          <TrendingUp className="h-6 w-6" />
                          {parseFloat(section4Calculations.weightedAmountKshs).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Bet Amount × Total Probability
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* Removed Games Alert */}
        {removedGames.length > 0 && (
          <Alert className="glass-card border-yellow-500/30 bg-yellow-500/10">
            <AlertTriangle className="h-4 w-4 text-yellow-600" />
            <AlertDescription className="text-yellow-600">
              <strong>{removedGames.length} games removed:</strong> {removedGames.slice(0, 3).map(g => `${g.homeTeam} vs ${g.awayTeam}`).join(', ')}
              {removedGames.length > 3 && ` and ${removedGames.length - 3} more`}
              . Reason: Insufficient data after download attempt.
            </AlertDescription>
          </Alert>
        )}

        {/* Games List */}
        {games.length > 0 && sureBets.length === 0 && (
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>Imported Games</CardTitle>
              <CardDescription>
                {games.length} games imported. Validate and analyze to find sure bets.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {games.map((game, idx) => (
                  <div
                    key={game.id}
                    className="flex items-center justify-between p-3 rounded-lg border border-border/50 bg-background/50"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-muted-foreground w-8">{idx + 1}</span>
                      <span className="font-medium">{game.homeTeam}</span>
                      <span className="text-muted-foreground">vs</span>
                      <span className="font-medium">{game.awayTeam}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {game.isValidated && (
                        <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/30">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Validated
                        </Badge>
                      )}
                      {game.needsTraining && (
                        <Badge variant="outline" className="bg-yellow-500/10 text-yellow-600 border-yellow-500/30">
                          <AlertCircle className="h-3 w-3 mr-1" />
                          Needs Training
                        </Badge>
                      )}
                      {!game.hasData && (
                        <Badge variant="outline" className="bg-red-500/10 text-red-600 border-red-500/30">
                          <X className="h-3 w-3 mr-1" />
                          No Data
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </PageLayout>
  );
}

