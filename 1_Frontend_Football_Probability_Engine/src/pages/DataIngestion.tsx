import { useState, useCallback, useRef, useEffect } from 'react';
import {
  Globe,
  Database,
  FileSpreadsheet,
  Download,
  Loader2,
  CheckCircle,
  AlertCircle,
  Upload,
  Calendar,
  Trophy,
  RefreshCw,
  FileUp,
  Clock,
  Eye,
  X,
  Square
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useToast } from '@/hooks/use-toast';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import apiClient from '@/services/api';
import { allLeagues } from '@/data/allLeagues';

// Mock dataset for preview
const generateMockDataset = (batchNumber: number, sources: string[]) => {
  const teams = ['Arsenal', 'Chelsea', 'Liverpool', 'Man City', 'Man United', 'Tottenham', 'Newcastle', 'Brighton', 'Aston Villa', 'West Ham'];
  const data = [];
  for (let i = 0; i < 20; i++) {
    const homeIdx = Math.floor(Math.random() * teams.length);
    let awayIdx = Math.floor(Math.random() * teams.length);
    while (awayIdx === homeIdx) awayIdx = Math.floor(Math.random() * teams.length);
    
    const fthg = Math.floor(Math.random() * 5);
    const ftag = Math.floor(Math.random() * 5);
    const ftr = fthg > ftag ? 'H' : fthg < ftag ? 'A' : 'D';
    
    data.push({
      date: `2024-${String(Math.floor(Math.random() * 12) + 1).padStart(2, '0')}-${String(Math.floor(Math.random() * 28) + 1).padStart(2, '0')}`,
      homeTeam: teams[homeIdx],
      awayTeam: teams[awayIdx],
      fthg,
      ftag,
      ftr,
      b365h: (1 + Math.random() * 4).toFixed(2),
      b365d: (2 + Math.random() * 2).toFixed(2),
      b365a: (1 + Math.random() * 5).toFixed(2),
    });
  }
  return data;
};

// Data source types
interface DataSource {
  id: string;
  name: string;
  url: string;
  leagues: string[];
  seasons: string;
  status: 'idle' | 'downloading' | 'completed' | 'failed';
  progress: number;
  recordCount?: number;
  lastUpdated?: string;
}

interface JackpotResult {
  id: string;
  jackpotId: string;
  date: string;
  matches: number;
  status: 'pending' | 'imported' | 'validated';
  correctPredictions?: number;
}

// Convert allLeagues to DataSource format
const initialDataSources: DataSource[] = allLeagues.map(league => ({
  id: league.id,
  name: league.name,
  url: league.url,
  leagues: [league.code],
  seasons: '2018-2024',
  status: 'idle' as const,
  progress: 0,
  lastUpdated: undefined,
}));

const mockJackpotResults: JackpotResult[] = [
  { id: '1', jackpotId: 'JK-2024-1230', date: '2024-12-22', matches: 13, status: 'validated', correctPredictions: 10 },
  { id: '2', jackpotId: 'JK-2024-1229', date: '2024-12-15', matches: 13, status: 'validated', correctPredictions: 11 },
  { id: '3', jackpotId: 'JK-2024-1228', date: '2024-12-08', matches: 13, status: 'validated', correctPredictions: 9 },
  { id: '4', jackpotId: 'JK-2024-1227', date: '2024-12-01', matches: 15, status: 'imported' },
];

interface DownloadBatch {
  id: string;
  batchNumber: number;
  timestamp: string;
  sources: string[];
  totalRecords: number;
  status: 'completed' | 'partial';
}

// Data download hook
function useDataDownload(selectedSeason: string = '2024-25') {
  const [sources, setSources] = useState<DataSource[]>(initialDataSources);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [downloadBatches, setDownloadBatches] = useState<DownloadBatch[]>([]);
  const [batchCounter, setBatchCounter] = useState(1000);
  const [downloadProgress, setDownloadProgress] = useState({
    completed: 0,
    total: 0,
    currentLeague: '',
    overallProgress: 0
  });
  const abortControllerRef = useRef<AbortController | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const { toast } = useToast();

  const toggleSource = (id: string) => {
    setSelectedSources(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    if (selectedSources.length === sources.length) {
      setSelectedSources([]);
    } else {
      setSelectedSources(sources.map(s => s.id));
    }
  };

  // Helper function to convert season format: "2023-24" -> "2324"
  const convertSeasonFormat = (season: string): string => {
    if (season === 'all' || season === 'last7' || season === 'last10') return 'all';
    const parts = season.split('-');
    if (parts.length === 2) {
      const startYear = parts[0].slice(-2); // Last 2 digits
      const endYear = parts[1].slice(-2);   // Last 2 digits
      return `${startYear}${endYear}`;
    }
    return season;
  };

  const cancelDownload = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsCancelling(true);
      setIsDownloading(false);
      
      // Clear progress interval
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      
      // Reset progress
      setDownloadProgress({
        completed: 0,
        total: 0,
        currentLeague: '',
        overallProgress: 0
      });
      
      // Mark downloading sources as cancelled
      setSources(prev => prev.map(s =>
        s.status === 'downloading'
          ? { ...s, status: 'idle' as const, progress: 0 }
          : s
      ));
      
      toast({
        title: 'Download Cancelled',
        description: 'Download has been cancelled. No data was saved.',
        variant: 'default',
      });
      
      abortControllerRef.current = null;
      setIsCancelling(false);
    }
  }, [toast]);

  const startDownload = useCallback(async () => {
    if (selectedSources.length === 0) return;

    setIsDownloading(true);
    setIsCancelling(false);

    // Create new AbortController for this download
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    const toDownload = sources.filter(s => selectedSources.includes(s.id));
    const totalLeagues = toDownload.length;
    
    // Initialize progress tracking
    setDownloadProgress({
      completed: 0,
      total: totalLeagues,
      currentLeague: '',
      overallProgress: 0
    });

    // Reset selected sources to downloading state
    setSources(prev => prev.map(s =>
      selectedSources.includes(s.id)
        ? { ...s, status: 'downloading' as const, progress: 0 }
        : s
    ));

    const downloadedSourceNames: string[] = [];
    let totalRecords = 0;
    let batchNumber = batchCounter;
    
    // Clear any existing progress interval
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
    
    // Start progress simulation
    progressIntervalRef.current = setInterval(() => {
      if (signal.aborted) {
        if (progressIntervalRef.current) {
          clearInterval(progressIntervalRef.current);
          progressIntervalRef.current = null;
        }
        return;
      }
      
      setDownloadProgress(prev => {
        // Increment progress gradually (max 90% until actual completion)
        const newProgress = Math.min(prev.overallProgress + 2, 90);
        return {
          ...prev,
          overallProgress: newProgress
        };
      });
    }, 500);
    
    try {
      // Check if cancelled before starting
      if (signal.aborted) {
        if (progressIntervalRef.current) {
          clearInterval(progressIntervalRef.current);
          progressIntervalRef.current = null;
        }
        return;
      }
      // Prepare leagues for batch download
      const isMultiSeason = selectedSeason === 'all' || selectedSeason === 'last7' || selectedSeason === 'last10';
      const leagues = toDownload.map(source => ({
        code: source.leagues[0], // Use first league code
        season: isMultiSeason ? undefined : convertSeasonFormat(selectedSeason)
      }));

      // Use batch download API if multiple sources or multi-season selection
      if (toDownload.length > 1 || isMultiSeason) {
        // Pass the actual season value (last7, last10, or all) instead of converting to 'all'
        const seasonParam = isMultiSeason ? selectedSeason : undefined;
        
        // Check if cancelled
        if (signal.aborted) {
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
          return;
        }
        
        const response = await apiClient.batchDownload(
          'football-data.co.uk',
          leagues,
          seasonParam,
          signal
        );
        
        // Check if cancelled after API call
        if (signal.aborted) {
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
          return;
        }

        if (response.success && response.data) {
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
          batchNumber = response.data.results[0]?.batchNumber || batchCounter;
          totalRecords = response.data.totalStats.inserted + response.data.totalStats.updated;

          // Update sources with results and track progress
          let completedCount = 0;
          response.data.results.forEach((result, idx) => {
            if (idx < toDownload.length) {
              const sourceId = toDownload[idx].id;
              downloadedSourceNames.push(toDownload[idx].name);
              completedCount++;
              
              // Update progress as each league completes
              setDownloadProgress(prev => ({
                completed: completedCount,
                total: totalLeagues,
                currentLeague: toDownload[idx].name,
                overallProgress: Math.round((completedCount / totalLeagues) * 100)
              }));
              
              setSources(prev => prev.map(s =>
                s.id === sourceId
                  ? {
                      ...s,
                      status: 'completed' as const,
                      progress: 100,
                      recordCount: result.stats?.inserted + result.stats?.updated || 0,
                      lastUpdated: new Date().toISOString().split('T')[0]
                    }
                  : s
              ));
            }
          });
          
          // Final progress update
          setDownloadProgress(prev => ({
            ...prev,
            completed: totalLeagues,
            overallProgress: 100,
            currentLeague: ''
          }));
        }
      } else {
        // Single league download
        const source = toDownload[0];
        const leagueCode = source.leagues[0];
        // For multi-season options, pass as-is; otherwise convert format
        const season = (selectedSeason === 'last7' || selectedSeason === 'last10') 
          ? selectedSeason 
          : convertSeasonFormat(selectedSeason);

        // Check if cancelled
        if (signal.aborted) {
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
          return;
        }

        const response = await apiClient.refreshData(
          'football-data.co.uk',
          leagueCode,
          season,
          signal
        );
        
        // Check if cancelled after API call
        if (signal.aborted) {
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
          return;
        }

        if (response.success && response.data) {
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
          batchNumber = response.data.batchNumber || batchCounter;
          totalRecords = response.data.stats.inserted + response.data.stats.updated;
          downloadedSourceNames.push(source.name);

          // Update progress for single download
          setDownloadProgress({
            completed: 1,
            total: 1,
            currentLeague: source.name,
            overallProgress: 100
          });

          setSources(prev => prev.map(s =>
            s.id === source.id
              ? {
                  ...s,
                  status: 'completed' as const,
                  progress: 100,
                  recordCount: totalRecords,
                  lastUpdated: new Date().toISOString().split('T')[0]
                }
              : s
          ));
        }
      }
        
        // Create batch record
        const newBatch: DownloadBatch = {
          id: `batch-${Date.now()}`,
        batchNumber: batchNumber,
          timestamp: new Date().toISOString(),
          sources: downloadedSourceNames,
        totalRecords: totalRecords,
          status: 'completed',
        };
        setDownloadBatches(prev => [newBatch, ...prev]);
      setBatchCounter(batchNumber + 1);
        
        toast({
          title: 'Download Complete',
        description: `Batch #${batchNumber}: Downloaded ${downloadedSourceNames.length} sources (${totalRecords.toLocaleString()} records)`,
        });

    } catch (error: any) {
      // Clear progress interval on error
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      
      // Don't show error if download was cancelled
      if (error.name === 'AbortError' || signal.aborted) {
        setDownloadProgress({
          completed: 0,
          total: 0,
          currentLeague: '',
          overallProgress: 0
        });
        return;
      }

      console.error('Download error:', error);
      
      // Mark sources as failed
      setSources(prev => prev.map(s =>
        selectedSources.includes(s.id)
          ? { ...s, status: 'failed' as const, progress: 0 }
          : s
      ));

      // Reset progress
      setDownloadProgress({
        completed: 0,
        total: 0,
        currentLeague: '',
        overallProgress: 0
      });

      toast({
        title: 'Download Failed',
        description: error.message || 'Failed to download data. Please try again.',
        variant: 'destructive',
      });
    } finally {
      // Clear progress interval
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      
      setIsDownloading(false);
      setIsCancelling(false);
      abortControllerRef.current = null;
      
      // Reset progress after a delay to show completion
      setTimeout(() => {
        setDownloadProgress(prev => {
          // Only reset if download is complete (not cancelled)
          if (prev.overallProgress === 100) {
            return {
              completed: 0,
              total: 0,
              currentLeague: '',
              overallProgress: 0
            };
          }
          return prev;
        });
      }, 2000);
        }
  }, [selectedSources, selectedSeason, toast, batchCounter, sources]);

  return { 
    sources, 
    isDownloading, 
    isCancelling,
    selectedSources, 
    toggleSource, 
    selectAll, 
    startDownload, 
    cancelDownload,
    downloadBatches,
    downloadProgress
  };
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

// Generate list of seasons (current season going back)
function generateSeasons(count: number = 10): string[] {
  const currentDate = new Date();
  const currentYear = currentDate.getFullYear();
  const currentMonth = currentDate.getMonth() + 1; // 1-12
  
  // Determine current season (assumes season starts in August)
  let currentSeasonStart: number;
  if (currentMonth >= 8) {
    currentSeasonStart = currentYear;
  } else {
    currentSeasonStart = currentYear - 1;
  }
  
  const seasons: string[] = [];
  for (let i = 0; i < count; i++) {
    const yearStart = currentSeasonStart - i;
    const yearEnd = yearStart + 1;
    const season = `${yearStart}-${String(yearEnd).slice(-2)}`;
    seasons.push(season);
  }
  
  return seasons;
}

interface BatchHistoryItem {
  id: string;
  batchNumber: number;
  source: string;
  status: string;
  startedAt: string | null;
  completedAt: string | null;
  recordsProcessed: number;
  recordsInserted: number;
  recordsUpdated: number;
  recordsSkipped: number;
  hasFiles: boolean;
  fileInfo?: {
    batchNumber: number;
    folderName: string;
    csvCount: number;
    leagues: string[];
    seasons: string[];
    files: string[];
  };
  leagueCode?: string;
  season?: string;
}

interface BatchHistorySummary {
  totalBatches: number;
  totalRecords: number;
  totalFiles: number;
  uniqueLeagues: number;
  leagues: string[];
}

export default function DataIngestion() {
  const [selectedSeason, setSelectedSeason] = useState('2024-25');
  const { 
    sources, 
    isDownloading, 
    isCancelling,
    selectedSources, 
    toggleSource, 
    selectAll, 
    startDownload, 
    cancelDownload,
    downloadBatches,
    downloadProgress
  } = useDataDownload(selectedSeason);
  const [jackpotResults, setJackpotResults] = useState<JackpotResult[]>(mockJackpotResults);
  const [manualInput, setManualInput] = useState('');
  const [previewBatch, setPreviewBatch] = useState<DownloadBatch | null>(null);
  const [previewData, setPreviewData] = useState<ReturnType<typeof generateMockDataset>>([]);
  const [batchHistory, setBatchHistory] = useState<BatchHistoryItem[]>([]);
  const [batchSummary, setBatchSummary] = useState<BatchHistorySummary | null>(null);
  const [loadingBatches, setLoadingBatches] = useState(true);
  const { toast } = useToast();
  
  // Generate seasons list
  const seasonsList = generateSeasons(10);

  // Fetch batch history on component mount and after downloads
  useEffect(() => {
    const fetchBatchHistory = async () => {
      try {
        setLoadingBatches(true);
        const response = await apiClient.getBatchHistory(50);
        if (response.success && response.data) {
          setBatchHistory(response.data.batches);
          setBatchSummary(response.data.summary);
        }
      } catch (error) {
        console.error('Failed to fetch batch history:', error);
        toast({
          title: 'Error',
          description: 'Failed to load batch history',
          variant: 'destructive',
        });
      } finally {
        setLoadingBatches(false);
      }
    };

    fetchBatchHistory();
  }, [toast, downloadBatches.length]); // Refresh when new batches are added

  const handlePreviewBatch = (batch: DownloadBatch) => {
    setPreviewBatch(batch);
    setPreviewData(generateMockDataset(batch.batchNumber, batch.sources));
  };

  const handleImportJackpot = () => {
    if (!manualInput.trim()) return;
    
    const newResult: JackpotResult = {
      id: String(jackpotResults.length + 1),
      jackpotId: `JK-2024-${1231 + jackpotResults.length}`,
      date: new Date().toISOString().split('T')[0],
      matches: 13,
      status: 'pending',
    };
    
    setJackpotResults(prev => [newResult, ...prev]);
    setManualInput('');
    toast({
      title: 'Jackpot Results Imported',
      description: `${newResult.jackpotId} has been queued for validation.`,
    });
  };

  const totalRecords = sources.reduce((acc, s) => acc + (s.recordCount || 0), 0);
  const sourcesWithData = sources.filter(s => s.recordCount).length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/20 p-6 space-y-6">
      {/* Header Section with Gradient */}
      <div className="relative overflow-hidden rounded-xl border border-border/50 bg-gradient-to-r from-primary/5 via-primary/10 to-primary/5 p-6 shadow-lg">
        <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>
        <div className="relative flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
              Data Ingestion
            </h1>
            <p className="text-muted-foreground text-lg">
              Import historical data and previous jackpot results
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="secondary" className="text-sm px-3 py-1 bg-primary/10 text-primary border-primary/30">
              <Database className="h-4 w-4 mr-1" />
              {totalRecords.toLocaleString()} records
            </Badge>
            <Badge variant="outline" className="text-sm px-3 py-1 border-border/50">
              {sourcesWithData}/{sources.length} sources
            </Badge>
          </div>
        </div>
      </div>

      <Tabs defaultValue="football-data" className="space-y-6">
        <div className="w-full border-b border-border/40 bg-gradient-to-r from-background via-background/95 to-background">
          <TabsList className="w-full h-14 justify-start gap-1 bg-transparent p-0">
            <TabsTrigger 
              value="football-data" 
              className="h-12 px-6 text-sm font-medium data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none border-b-2 border-transparent transition-all hover:bg-muted/50 gap-2"
            >
              <Globe className="h-4 w-4" />
              Football-Data.co.uk
            </TabsTrigger>
            <TabsTrigger 
              value="api-football" 
              className="h-12 px-6 text-sm font-medium data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none border-b-2 border-transparent transition-all hover:bg-muted/50 gap-2"
            >
              <FileSpreadsheet className="h-4 w-4" />
              API-Football
            </TabsTrigger>
            <TabsTrigger 
              value="jackpot-results" 
              className="h-12 px-6 text-sm font-medium data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none border-b-2 border-transparent transition-all hover:bg-muted/50 gap-2"
            >
              <Trophy className="h-4 w-4" />
              Jackpot Results
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Football-Data.co.uk Tab */}
        <TabsContent value="football-data" className="space-y-4">
          {/* Download Progress Summary */}
          {isDownloading && downloadProgress.total > 0 && (
            <Card className="border-primary/50 bg-primary/5">
              <CardContent className="pt-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Loader2 className="h-5 w-5 animate-spin text-primary" />
                      <div>
                        <p className="font-semibold text-sm">
                          Downloading {downloadProgress.completed}/{downloadProgress.total} leagues
                        </p>
                        {downloadProgress.currentLeague && (
                          <p className="text-xs text-muted-foreground mt-1">
                            Currently downloading: <span className="font-medium">{downloadProgress.currentLeague}</span>
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-primary">
                        {downloadProgress.overallProgress}%
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {downloadProgress.completed} completed
                      </div>
                    </div>
                  </div>
                  <Progress value={downloadProgress.overallProgress} className="h-3" />
                </div>
              </CardContent>
            </Card>
          )}
          
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Globe className="h-5 w-5" />
                    Historical Match & Odds Data
                  </CardTitle>
                  <CardDescription>
                    Download CSV files from Football-Data.co.uk (free, no API key required)
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Select value={selectedSeason} onValueChange={setSelectedSeason} disabled={isDownloading}>
                    <SelectTrigger className="w-[200px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {seasonsList.map((season) => (
                        <SelectItem key={season} value={season}>
                          {season}
                        </SelectItem>
                      ))}
                      <SelectItem value="last7">Last 7 Seasons (Ideal)</SelectItem>
                      <SelectItem value="last10">Last 10 Seasons (Diminishing Returns)</SelectItem>
                    </SelectContent>
                  </Select>
                  {isDownloading ? (
                  <Button
                      onClick={cancelDownload}
                      variant="destructive"
                      disabled={isCancelling}
                  >
                      {isCancelling ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Cancelling...
                      </>
                    ) : (
                      <>
                          <Square className="h-4 w-4 mr-2" />
                          Stop Download
                      </>
                    )}
                  </Button>
                  ) : (
                    <Button
                      onClick={startDownload}
                      disabled={selectedSources.length === 0}
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Download Selected
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <div
                  onClick={selectAll}
                  className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md hover:bg-accent hover:text-accent-foreground cursor-pointer transition-colors"
                >
                  <Checkbox
                    checked={selectedSources.length === sources.length}
                    className="pointer-events-none"
                  />
                  {selectedSources.length === sources.length ? 'Deselect All' : 'Select All'}
                </div>
              </div>
              <ScrollArea className="h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[50px]">Select</TableHead>
                      <TableHead>League</TableHead>
                      <TableHead>Source URL</TableHead>
                      <TableHead>Seasons</TableHead>
                      <TableHead>Last Updated</TableHead>
                      <TableHead className="text-right">Records</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sources.map((source) => (
                      <TableRow key={source.id}>
                        <TableCell>
                          <Checkbox
                            checked={selectedSources.includes(source.id)}
                            onCheckedChange={() => toggleSource(source.id)}
                            disabled={isDownloading}
                          />
                        </TableCell>
                        <TableCell className="font-medium">{source.name}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {source.url}
                        </TableCell>
                        <TableCell className="text-sm">{source.seasons}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {source.lastUpdated ? formatDate(source.lastUpdated) : '—'}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {source.recordCount?.toLocaleString() || '—'}
                        </TableCell>
                        <TableCell>
                          {source.status === 'downloading' ? (
                            <div className="flex items-center gap-2 min-w-[120px]">
                              <Loader2 className="h-4 w-4 animate-spin text-primary flex-shrink-0" />
                              <div className="flex-1 min-w-[80px]">
                                <Progress value={source.progress || downloadProgress.overallProgress} className="h-2" />
                                <span className="text-xs text-muted-foreground mt-0.5 block">
                                  {source.progress || downloadProgress.overallProgress}%
                                </span>
                              </div>
                            </div>
                          ) : source.status === 'completed' ? (
                            <Badge variant="secondary" className="bg-green-500/10 text-green-600">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Done
                            </Badge>
                          ) : source.status === 'failed' ? (
                            <Badge variant="destructive">
                              <AlertCircle className="h-3 w-3 mr-1" />
                              Failed
                            </Badge>
                          ) : (
                            <Badge variant="outline">Idle</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>

          <Alert>
            <Database className="h-4 w-4" />
            <AlertTitle>Data Schema</AlertTitle>
            <AlertDescription>
              Each CSV contains: Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR, B365H, B365D, B365A.
              Data is normalized and stored for model training.
            </AlertDescription>
          </Alert>

          {/* Available Downloaded Data */}
            <Card>
              <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                <CardTitle className="text-lg flex items-center gap-2">
                    <Database className="h-5 w-5" />
                    Available Downloaded Data
                </CardTitle>
                <CardDescription>
                    Data available in database and file system from previous downloads
                </CardDescription>
                </div>
                <div className="flex items-center gap-3">
                  {batchSummary && (
                    <div className="flex items-center gap-4">
                      <Badge variant="secondary" className="text-xs">
                        {batchSummary.totalBatches} batches
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        {batchSummary.totalRecords.toLocaleString()} records
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        {batchSummary.totalFiles} CSV files
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        {batchSummary.uniqueLeagues} leagues
                      </Badge>
                    </div>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={async () => {
                      try {
                        setLoadingBatches(true);
                        const response = await apiClient.getBatchHistory(50);
                        if (response.success && response.data) {
                          setBatchHistory(response.data.batches);
                          setBatchSummary(response.data.summary);
                          toast({
                            title: 'Refreshed',
                            description: 'Batch history updated',
                          });
                        }
                      } catch (error) {
                        toast({
                          title: 'Error',
                          description: 'Failed to refresh batch history',
                          variant: 'destructive',
                        });
                      } finally {
                        setLoadingBatches(false);
                      }
                    }}
                    disabled={loadingBatches}
                  >
                    <RefreshCw className={`h-4 w-4 mr-1 ${loadingBatches ? 'animate-spin' : ''}`} />
                    Refresh
                  </Button>
                </div>
              </div>
              </CardHeader>
              <CardContent>
              {loadingBatches ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground mr-2" />
                  <span className="text-sm text-muted-foreground">Loading batch history...</span>
                </div>
              ) : batchHistory.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Database className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p className="text-sm">No downloaded data found.</p>
                  <p className="text-xs mt-1">Download data using the table above to get started.</p>
                </div>
              ) : (
                <ScrollArea className="h-[400px]">
                  <div className="space-y-3">
                    {batchHistory.map((batch) => (
                      <div
                        key={batch.id}
                        className="flex items-center justify-between p-4 rounded-lg border bg-muted/30 hover:bg-muted/50 transition-colors"
                      >
                        <div className="flex items-start gap-4 flex-1">
                          <div className="flex flex-col min-w-[120px]">
                            <span className="font-mono font-semibold text-primary">
                              Batch #{batch.batchNumber}
                            </span>
                            <span className="text-xs text-muted-foreground mt-1">
                              {batch.completedAt 
                                ? new Date(batch.completedAt).toLocaleString()
                                : batch.startedAt
                                ? new Date(batch.startedAt).toLocaleString()
                                : 'Unknown date'}
                            </span>
                            <Badge variant="outline" className="text-xs mt-1 w-fit">
                              {batch.source}
                            </Badge>
                          </div>
                          
                          {batch.fileInfo && (
                            <div className="flex flex-col gap-2 flex-1">
                          <div className="flex flex-wrap gap-1">
                                {batch.fileInfo.leagues.slice(0, 5).map((league, idx) => (
                                  <Badge key={idx} variant="secondary" className="text-xs">
                                    {league}
                              </Badge>
                            ))}
                                {batch.fileInfo.leagues.length > 5 && (
                              <Badge variant="secondary" className="text-xs">
                                    +{batch.fileInfo.leagues.length - 5} more
                              </Badge>
                            )}
                          </div>
                              <div className="text-xs text-muted-foreground">
                                <span className="font-medium">{batch.fileInfo.csvCount}</span> CSV file{batch.fileInfo.csvCount !== 1 ? 's' : ''}
                                {batch.fileInfo.seasons.length > 0 && (
                                  <span className="ml-2">
                                    • Seasons: {batch.fileInfo.seasons.slice(0, 3).join(', ')}
                                    {batch.fileInfo.seasons.length > 3 && ` +${batch.fileInfo.seasons.length - 3} more`}
                                  </span>
                                )}
                        </div>
                              <div className="text-xs text-muted-foreground font-mono">
                                Folder: {batch.fileInfo.folderName}
                              </div>
                            </div>
                          )}
                          
                          {!batch.fileInfo && batch.leagueCode && (
                            <div className="flex flex-col gap-1">
                              <Badge variant="outline" className="text-xs w-fit">
                                {batch.leagueCode}
                              </Badge>
                              {batch.season && (
                                <span className="text-xs text-muted-foreground">
                                  Season: {batch.season}
                          </span>
                              )}
                            </div>
                          )}
                        </div>
                        
                        <div className="flex items-center gap-3 flex-shrink-0">
                          <div className="text-right">
                            <div className="text-sm font-medium tabular-nums">
                              {batch.recordsInserted.toLocaleString()} records
                            </div>
                            {batch.recordsProcessed > 0 && (
                              <div className="text-xs text-muted-foreground">
                                {batch.recordsProcessed.toLocaleString()} processed
                              </div>
                            )}
                          </div>
                          <Badge 
                            className={
                              batch.status === 'completed' 
                                ? 'bg-green-500/10 text-green-600'
                                : batch.status === 'failed'
                                ? 'bg-red-500/10 text-red-600'
                                : 'bg-yellow-500/10 text-yellow-600'
                            }
                          >
                            {batch.status === 'completed' && <CheckCircle className="h-3 w-3 mr-1" />}
                            {batch.status === 'failed' && <AlertCircle className="h-3 w-3 mr-1" />}
                            {batch.status}
                          </Badge>
                          {batch.hasFiles && (
                            <Badge variant="outline" className="text-xs">
                              <FileSpreadsheet className="h-3 w-3 mr-1" />
                              Files
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
              </CardContent>
            </Card>
        </TabsContent>

        {/* API-Football Tab */}
        <TabsContent value="api-football" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <FileSpreadsheet className="h-5 w-5" />
                API-Football Integration
              </CardTitle>
              <CardDescription>
                Real-time fixtures and odds via API (requires API key for production)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert>
                <Clock className="h-4 w-4" />
                <AlertTitle>Optional Data Source</AlertTitle>
                <AlertDescription>
                  API-Football provides live fixtures and real-time odds. Currently using Football-Data.co.uk as primary source.
                  API integration available for production deployment.
                </AlertDescription>
              </Alert>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>API Key</Label>
                  <Input type="password" placeholder="Enter API-Football key" disabled />
                </div>
                <div className="space-y-2">
                  <Label>Endpoint</Label>
                  <Input value="https://v3.football.api-sports.io" disabled />
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <Badge variant="outline">Status: Not Connected</Badge>
                <Button variant="outline" size="sm" disabled>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Test Connection
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Jackpot Results Tab */}
        <TabsContent value="jackpot-results" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Upload className="h-5 w-5" />
                  Import Jackpot Results
                </CardTitle>
                <CardDescription>
                  Enter previous jackpot outcomes for validation
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Paste Jackpot Results (CSV format)</Label>
                  <Textarea
                    placeholder="Match,HomeTeam,AwayTeam,Result&#10;1,Arsenal,Chelsea,H&#10;2,Liverpool,Man City,D&#10;..."
                    className="font-mono text-sm h-[200px]"
                    value={manualInput}
                    onChange={(e) => setManualInput(e.target.value)}
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Button onClick={handleImportJackpot} disabled={!manualInput.trim()}>
                    <FileUp className="h-4 w-4 mr-2" />
                    Import Results
                  </Button>
                  <Button variant="outline">
                    <Upload className="h-4 w-4 mr-2" />
                    Upload CSV File
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Trophy className="h-5 w-5" />
                  Imported Jackpots
                </CardTitle>
                <CardDescription>
                  Historical jackpot results for backtesting
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[280px]">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Jackpot ID</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead className="text-right">Matches</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Correct</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {jackpotResults.map((result) => (
                        <TableRow key={result.id}>
                          <TableCell className="font-mono text-sm">{result.jackpotId}</TableCell>
                          <TableCell className="text-sm">{formatDate(result.date)}</TableCell>
                          <TableCell className="text-right">{result.matches}</TableCell>
                          <TableCell>
                            {result.status === 'validated' ? (
                              <Badge variant="secondary" className="bg-green-500/10 text-green-600">
                                Validated
                              </Badge>
                            ) : result.status === 'imported' ? (
                              <Badge variant="secondary" className="bg-blue-500/10 text-blue-600">
                                Imported
                              </Badge>
                            ) : (
                              <Badge variant="outline">Pending</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {result.correctPredictions !== undefined ? (
                              <span className={result.correctPredictions >= 10 ? 'text-green-600' : 'text-muted-foreground'}>
                                {result.correctPredictions}/{result.matches}
                              </span>
                            ) : '—'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          <Alert>
            <Trophy className="h-4 w-4" />
            <AlertTitle>Validation Flow</AlertTitle>
            <AlertDescription>
              Imported jackpot results are compared against model predictions to compute calibration metrics.
              Go to Jackpot Validation page for detailed comparison analysis.
            </AlertDescription>
          </Alert>
        </TabsContent>
      </Tabs>

      {/* Dataset Preview Dialog */}
      <Dialog open={!!previewBatch} onOpenChange={() => setPreviewBatch(null)}>
        <DialogContent className="max-w-4xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Batch #{previewBatch?.batchNumber} - Dataset Preview
            </DialogTitle>
            <DialogDescription>
              Showing sample of {previewBatch?.totalRecords.toLocaleString()} records from {previewBatch?.sources.join(', ')}
            </DialogDescription>
          </DialogHeader>
          <ScrollArea className="h-[400px] mt-4">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Home Team</TableHead>
                  <TableHead>Away Team</TableHead>
                  <TableHead className="text-center">FTHG</TableHead>
                  <TableHead className="text-center">FTAG</TableHead>
                  <TableHead className="text-center">FTR</TableHead>
                  <TableHead className="text-right">B365H</TableHead>
                  <TableHead className="text-right">B365D</TableHead>
                  <TableHead className="text-right">B365A</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {previewData.map((row, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="font-mono text-sm">{row.date}</TableCell>
                    <TableCell>{row.homeTeam}</TableCell>
                    <TableCell>{row.awayTeam}</TableCell>
                    <TableCell className="text-center tabular-nums">{row.fthg}</TableCell>
                    <TableCell className="text-center tabular-nums">{row.ftag}</TableCell>
                    <TableCell className="text-center">
                      <Badge variant={row.ftr === 'H' ? 'default' : row.ftr === 'A' ? 'secondary' : 'outline'}>
                        {row.ftr}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{row.b365h}</TableCell>
                    <TableCell className="text-right tabular-nums">{row.b365d}</TableCell>
                    <TableCell className="text-right tabular-nums">{row.b365a}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ScrollArea>
          <div className="flex justify-between items-center pt-4 border-t">
            <span className="text-sm text-muted-foreground">
              Showing 20 sample rows of {previewBatch?.totalRecords.toLocaleString()} total
            </span>
            <Button variant="outline" onClick={() => setPreviewBatch(null)}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
