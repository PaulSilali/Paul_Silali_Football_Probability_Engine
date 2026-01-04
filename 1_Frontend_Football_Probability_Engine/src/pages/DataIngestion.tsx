import { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
  Square,
  TrendingUp,
  Users,
  Target,
  Info,
  AlertTriangle,
  BarChart3,
  Sparkles,
  Zap,
  Activity,
  Layers,
  HardDrive,
  Calculator,
  ArrowRight
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageLayout } from '@/components/layouts/PageLayout';
import { ModernCard } from '@/components/ui/modern-card';
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
import { DrawStructuralIngestion } from '@/components/DrawStructuralIngestion';

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
  status: 'pending' | 'imported' | 'validated' | 'probabilities_computed';
  correctPredictions?: number;
  hasProbabilities?: boolean;
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
      // Abort the controller first
      abortControllerRef.current.abort();
      
      // Clear progress interval immediately
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      
      // Set states to stop any further processing
      setIsCancelling(true);
      setIsDownloading(false);
      
      // Reset progress immediately
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
      
      // Clear the abort controller reference
      abortControllerRef.current = null;
      
      // Show toast notification
      toast({
        title: 'Download Cancelled',
        description: 'Download has been cancelled. No data was saved.',
        variant: 'default',
      });
      
      // Reset cancelling state after a brief delay
      setTimeout(() => {
      setIsCancelling(false);
      }, 100);
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
      // Check if cancelled - stop immediately
      if (signal.aborted || !abortControllerRef.current) {
        if (progressIntervalRef.current) {
          clearInterval(progressIntervalRef.current);
          progressIntervalRef.current = null;
        }
        return;
      }
      
      setDownloadProgress(prev => {
        // Don't update if already cancelled
        if (signal.aborted) {
          return prev;
        }
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
        
        // Check if cancelled before API call
        if (signal.aborted || !abortControllerRef.current) {
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
          throw new DOMException('Download cancelled', 'AbortError');
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

        // Check if cancelled before API call
        if (signal.aborted || !abortControllerRef.current) {
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
          throw new DOMException('Download cancelled', 'AbortError');
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
        
        // Refresh league stats from database after download completes
        try {
          const statsResponse = await apiClient.getLeagueStats();
          if (statsResponse.success && statsResponse.data) {
            setSources(prev => prev.map(source => {
              const leagueCode = source.leagues[0];
              const stats = statsResponse.data[leagueCode];
              if (stats) {
                // Determine status: if has records and was just completed, keep completed; otherwise idle
                const newStatus = (source.status === 'completed' && stats.recordCount > 0) 
                  ? 'completed' as const 
                  : (stats.recordCount > 0 ? 'completed' as const : 'idle' as const);
                
                return {
                  ...source,
                  recordCount: stats.recordCount,
                  lastUpdated: stats.lastUpdated || undefined,
                  status: newStatus,
                  progress: newStatus === 'completed' ? 100 : 0
                };
              }
              return source;
            }));
          }
        } catch (error) {
          console.error('Failed to refresh league stats:', error);
        }

    } catch (error: any) {
      // Clear progress interval on error
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      
      // Don't show error if download was cancelled
      if (error.name === 'AbortError' || signal.aborted || error.message?.includes('aborted')) {
        // Mark sources as idle (cancelled)
        setSources(prev => prev.map(s =>
          selectedSources.includes(s.id) && s.status === 'downloading'
            ? { ...s, status: 'idle' as const, progress: 0 }
            : s
        ));
        
        setDownloadProgress({
          completed: 0,
          total: 0,
          currentLeague: '',
          overallProgress: 0
        });
        
        setIsDownloading(false);
        setIsCancelling(false);
        abortControllerRef.current = null;
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
      // Only execute finally block if not cancelled
      if (!signal.aborted) {
      // Clear progress interval
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      
      setIsDownloading(false);
      setIsCancelling(false);
        
        // Only clear abort controller if download completed normally
        if (abortControllerRef.current && !signal.aborted) {
      abortControllerRef.current = null;
        }
      
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
        }
  }, [selectedSources, selectedSeason, toast, batchCounter, sources]);

  // Fetch league statistics on component mount
  useEffect(() => {
    const fetchLeagueStats = async () => {
      try {
        const response = await apiClient.getLeagueStats();
        if (response.success && response.data) {
          console.log('League stats response:', response.data);
          // Update sources with fetched statistics
          setSources(prev => prev.map(source => {
            const leagueCode = source.leagues[0]; // Get league code from source
            const stats = response.data[leagueCode];
            if (stats) {
              console.log(`Updating ${source.name} (${leagueCode}):`, stats);
              // Set status based on whether there are records
              const status = stats.recordCount > 0 ? 'completed' as const : 'idle' as const;
              return {
                ...source,
                recordCount: stats.recordCount,
                lastUpdated: stats.lastUpdated || undefined,
                status: status,
                progress: status === 'completed' ? 100 : 0
              };
            } else {
              console.log(`No stats found for ${source.name} (${leagueCode}). Available codes:`, Object.keys(response.data));
            }
            return source;
          }));
        }
      } catch (error) {
        console.error('Failed to fetch league stats:', error);
        // Don't show error toast for this - it's not critical
      }
    };

    fetchLeagueStats();
  }, []); // Only fetch once on mount

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

function formatSeasonDisplay(season: string): string {
  if (season === 'last7') {
    return 'Last 7 Seasons';
  } else if (season === 'last10') {
    return 'Last 10 Seasons';
  } else if (season === 'all') {
    return 'All Seasons';
  } else {
    return season;
  }
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
  const navigate = useNavigate();
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
  const [jackpotResults, setJackpotResults] = useState<JackpotResult[]>([]);
  const [loadingJackpots, setLoadingJackpots] = useState(true);
  const [computingProbabilities, setComputingProbabilities] = useState<Set<string>>(new Set());
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

  // Fetch imported jackpots on component mount
  useEffect(() => {
    const fetchImportedJackpots = async () => {
      try {
        setLoadingJackpots(true);
        const response = await apiClient.getImportedJackpots();
        if (response.success && response.data?.jackpots) {
          // Transform API response to match frontend format
          const transformed = response.data.jackpots.map(j => ({
            id: j.id,
            jackpotId: j.jackpotId,
            date: j.date || new Date().toISOString().split('T')[0],
            matches: j.matches,
            status: j.status,
            correctPredictions: j.correctPredictions,
            hasProbabilities: j.status === 'validated' || j.status === 'probabilities_computed'
          }));
          setJackpotResults(transformed);
        } else {
          // If no data, use empty array (not mock data)
          setJackpotResults([]);
        }
      } catch (error) {
        console.error('Failed to fetch imported jackpots:', error);
        // On error, use empty array instead of mock data
        setJackpotResults([]);
        toast({
          title: 'Warning',
          description: 'Failed to load imported jackpots. Showing empty list.',
          variant: 'default',
        });
      } finally {
        setLoadingJackpots(false);
      }
    };

    fetchImportedJackpots();
  }, [toast]);

  const handlePreviewBatch = (batch: DownloadBatch) => {
    setPreviewBatch(batch);
    setPreviewData(generateMockDataset(batch.batchNumber, batch.sources));
  };

  const handleImportJackpot = async () => {
    if (!manualInput.trim()) {
      toast({
        title: 'Error',
        description: 'Please paste CSV data first',
        variant: 'destructive',
      });
      return;
    }
    
    try {
      console.log('=== IMPORT JACKPOT STARTED ===');
      console.log('Input length:', manualInput.length);
      
      // Parse CSV input - handle both comma and various line endings
      const lines = manualInput.trim().split(/\r?\n/).filter(line => line.trim());
      console.log('Parsed lines:', lines.length);
      console.log('First line:', lines[0]);
      
      if (lines.length < 2) {
        toast({
          title: 'Error',
          description: `Invalid CSV format. Found ${lines.length} lines. Expected header row and at least one data row.`,
          variant: 'destructive',
        });
        return;
      }

      // Parse header - handle spaces in column names
      const header = lines[0].split(',').map(h => h.trim().replace(/\s+/g, ''));
      console.log('Header:', header);
      
      const matchIdx = header.findIndex(h => h.toLowerCase() === 'match');
      const homeTeamIdx = header.findIndex(h => h.toLowerCase().replace(/\s+/g, '') === 'hometeam');
      const awayTeamIdx = header.findIndex(h => h.toLowerCase().replace(/\s+/g, '') === 'awayteam');
      const resultIdx = header.findIndex(h => h.toLowerCase() === 'result');

      console.log('Column indices:', { matchIdx, homeTeamIdx, awayTeamIdx, resultIdx });

      if (matchIdx === -1 || homeTeamIdx === -1 || awayTeamIdx === -1 || resultIdx === -1) {
        toast({
          title: 'Error',
          description: `CSV must contain columns: Match, HomeTeam, AwayTeam, Result. Found: ${header.join(', ')}`,
          variant: 'destructive',
        });
        return;
      }

      // Parse data rows
      const actualResults: Record<string, string> = {};
      const matches: Array<{match: string, home: string, away: string, result: string}> = [];

      for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue; // Skip empty lines
        
        const values = line.split(',').map(v => v.trim());
        console.log(`Row ${i}:`, values);
        
        if (values.length < Math.max(matchIdx, homeTeamIdx, awayTeamIdx, resultIdx) + 1) {
          console.warn(`Row ${i} has insufficient columns, skipping`);
          continue;
        }

        const matchNum = values[matchIdx];
        const homeTeam = values[homeTeamIdx];
        const awayTeam = values[awayTeamIdx];
        let result = values[resultIdx]?.toUpperCase().trim();

        if (!matchNum || !homeTeam || !awayTeam || !result) {
          console.warn(`Row ${i} missing required fields, skipping`);
          continue;
        }

        // Convert result format: H/D/A or 1/X/2
        if (result === 'H' || result === '1') {
          result = '1';
        } else if (result === 'D' || result === 'X') {
          result = 'X';
        } else if (result === 'A' || result === '2') {
          result = '2';
        } else {
          console.warn(`Row ${i} has invalid result: ${result}, skipping`);
          continue; // Skip invalid results
        }

        actualResults[matchNum] = result;
        matches.push({ match: matchNum, home: homeTeam, away: awayTeam, result });
      }

      console.log('Parsed results:', actualResults);
      console.log('Total matches:', matches.length);

      if (Object.keys(actualResults).length === 0) {
        toast({
          title: 'Error',
          description: 'No valid results found in CSV. Please check the format.',
          variant: 'destructive',
        });
        return;
      }

      // Create jackpot with fixtures first (needed for probability computation)
      const fixturesToCreate = matches.map(match => ({
        id: match.match,
        homeTeam: match.home,
        awayTeam: match.away,
        odds: {
          home: 2.0,
          draw: 3.0,
          away: 2.5
        }
      }));

      console.log('Creating jackpot with fixtures:', {
        fixturesCount: fixturesToCreate.length
      });

      // Create jackpot (API will auto-generate jackpot ID)
      const createJackpotResponse = await apiClient.createJackpot(fixturesToCreate);
      if (!createJackpotResponse.success || !createJackpotResponse.data?.id) {
        throw new Error('Failed to create jackpot');
      }

      // Use the auto-generated jackpot ID from the API
      const createdJackpotId = createJackpotResponse.data.id;
      const jackpotName = `Imported Jackpot - ${new Date().toLocaleDateString()}`;

      // Create empty selections (required by API)
      const selections: Record<string, Record<string, string>> = {};
      // Create a placeholder selection for Set A (required field)
      const setASelections: Record<string, string> = {};
      Object.keys(actualResults).forEach(matchNum => {
        setASelections[matchNum] = '1'; // Default to home win, will be updated later
      });
      selections['A'] = setASelections;

      console.log('Calling API to save results:', {
        jackpotId: createdJackpotId,
        name: jackpotName,
        matchesCount: matches.length,
        actualResultsCount: Object.keys(actualResults).length
      });

      // Call API to save
      const response = await apiClient.saveProbabilityResult(createdJackpotId, {
        name: jackpotName,
        description: `Imported ${matches.length} match results`,
        selections: selections,
        actual_results: actualResults,
      });

      console.log('API Response:', response);

      if (response.success) {
        toast({
          title: 'Success',
          description: `Jackpot ${createdJackpotId} imported successfully with ${matches.length} results. You can now compute probabilities.`,
        });
        
        // Refresh the imported jackpots list
        const refreshResponse = await apiClient.getImportedJackpots();
        if (refreshResponse.success && refreshResponse.data?.jackpots) {
          const transformed = refreshResponse.data.jackpots.map(j => ({
            id: j.id,
            jackpotId: j.jackpotId,
            date: j.date || new Date().toISOString().split('T')[0],
            matches: j.matches,
            status: j.status,
            correctPredictions: j.correctPredictions,
            hasProbabilities: j.status === 'validated' || j.status === 'probabilities_computed'
          }));
          setJackpotResults(transformed);
        }
        
    setManualInput('');
      } else {
        throw new Error(response.message || 'Failed to save jackpot results');
      }
    } catch (error: any) {
      console.error('Error importing jackpot:', error);
      console.error('Error details:', {
        message: error.message,
        stack: error.stack,
        response: error.response
      });
    toast({
        title: 'Error',
        description: error.message || error.response?.data?.detail || 'Failed to import jackpot results. Check console for details.',
        variant: 'destructive',
    });
    }
  };

  const handleComputeProbabilities = async (result: JackpotResult) => {
    if (computingProbabilities.has(result.jackpotId)) {
      return; // Already computing
    }

    try {
      setComputingProbabilities(prev => new Set(prev).add(result.jackpotId));
      
      // Get saved result details - try by ID first, fallback to jackpot_id
      let savedResult: any = null;
      let actualResults: Record<string, string> = {};
      let matchNumbers: string[] = [];
      
      try {
        const savedResultResponse = await apiClient.getSavedResult(parseInt(result.id));
        if (savedResultResponse.success && savedResultResponse.data) {
          savedResult = savedResultResponse.data;
          actualResults = savedResult.actualResults || {};
          matchNumbers = Object.keys(actualResults).sort((a, b) => parseInt(a) - parseInt(b));
        }
      } catch (error) {
        // If getSavedResult fails, try getting by jackpot_id
        console.warn(`Failed to get saved result by ID ${result.id}, trying jackpot_id ${result.jackpotId}`);
        try {
          const jackpotResultsResponse = await apiClient.getSavedResults(result.jackpotId);
          if (jackpotResultsResponse.success && jackpotResultsResponse.data?.results?.length > 0) {
            savedResult = jackpotResultsResponse.data.results[0]; // Get most recent
            actualResults = savedResult.actualResults || {};
            matchNumbers = Object.keys(actualResults).sort((a, b) => parseInt(a) - parseInt(b));
          }
        } catch (e) {
          console.error('Failed to get saved results by jackpot_id:', e);
        }
      }
      
      if (!savedResult || Object.keys(actualResults).length === 0) {
        throw new Error('Failed to load jackpot details or no actual results found');
      }

      // Check if jackpot exists, create it if missing
      let jackpotExists = false;
      let actualJackpotId = result.jackpotId;
      
      try {
        const jackpotCheck = await apiClient.getJackpot(result.jackpotId);
        jackpotExists = jackpotCheck.success;
      } catch (e) {
        // Jackpot doesn't exist - create it with placeholder fixtures
        console.warn(`Jackpot ${result.jackpotId} not found, creating it with placeholder fixtures`);
        
        try {
          // Create fixtures with placeholder team names
          // Note: Team names are not stored in saved_probability_results,
          // so we use placeholders. Probabilities will still be computed,
          // but team-specific features won't work until fixtures are updated.
          const fixturesToCreate = matchNumbers.map((matchNum) => ({
            id: matchNum,
            homeTeam: `Team ${matchNum} Home`, // Placeholder
            awayTeam: `Team ${matchNum} Away`, // Placeholder
            odds: {
              home: 2.0,
              draw: 3.0,
              away: 2.5
            }
          }));

          // Create jackpot with placeholder fixtures, using the original jackpot ID if possible
          const createResponse = await apiClient.createJackpot(fixturesToCreate, result.jackpotId);
          if (createResponse.success && createResponse.data?.id) {
            const newJackpotId = createResponse.data.id;
            actualJackpotId = newJackpotId;
            jackpotExists = true;
            
            toast({
              title: 'Warning',
              description: `Created missing jackpot ${actualJackpotId} with placeholder team names. Probabilities will be computed, but team-specific features may not work correctly.`,
              variant: 'default',
            });
          } else {
            throw new Error('Failed to create missing jackpot');
          }
        } catch (createError: any) {
          console.error('Failed to create missing jackpot:', createError);
          toast({
            title: 'Error',
            description: `Jackpot ${result.jackpotId} not found and could not be created automatically. Please re-import the jackpot results or run the SQL fix script.`,
            variant: 'destructive',
          });
          throw new Error(
            `Jackpot ${result.jackpotId} not found. ` +
            `Please re-import the jackpot results using the "Import Results" button, ` +
            `or run: fix_missing_jackpot.sql`
          );
        }
      }

      // Use the actual jackpot ID (may have been updated)
      if (!jackpotExists && actualJackpotId !== result.jackpotId) {
        result.jackpotId = actualJackpotId;
      }

      // Compute probabilities using the actual jackpot ID
      toast({
        title: 'Computing',
        description: `Computing probabilities for ${actualJackpotId}...`,
      });

      const probResponse = await apiClient.getProbabilities(actualJackpotId);
      if (!probResponse.success) {
        throw new Error('Failed to compute probabilities');
      }

      // Save probability results with selections based on highest probability
      const probabilitySets = probResponse.data?.probabilitySets || {};
      const selections: Record<string, Record<string, string>> = {};
      
      console.log('Probability sets received:', Object.keys(probabilitySets));
      console.log('Sample probabilities (Set A, Match 1):', probabilitySets['A']?.[0]);
      
      Object.keys(probabilitySets).forEach(setId => {
        const setProbs = probabilitySets[setId];
        if (!setProbs || !Array.isArray(setProbs)) {
          console.warn(`Set ${setId} has invalid format:`, setProbs);
          return;
        }
        
        const setSelections: Record<string, string> = {};
        setProbs.forEach((prob: any, idx: number) => {
          const matchNum = matchNumbers[idx];
          if (!matchNum) return;
          
          // Select outcome with highest probability
          // Note: Probabilities come as percentages (0-100) from the API
          const homeProb = prob.homeWinProbability / 100;
          const drawProb = prob.drawProbability / 100;
          const awayProb = prob.awayWinProbability / 100;
          
          let selection = '1'; // Default to home
          if (drawProb > homeProb && drawProb > awayProb) {
            selection = 'X';
          } else if (awayProb > homeProb && awayProb > drawProb) {
            selection = '2';
          }
          
          setSelections[matchNum] = selection;
        });
        
        selections[setId] = setSelections;
        
        // Log selection summary for first few sets
        if (['A', 'B', 'C'].includes(setId)) {
          const selectionCounts = Object.values(setSelections).reduce((acc: any, sel: string) => {
            acc[sel] = (acc[sel] || 0) + 1;
            return acc;
          }, {});
          console.log(`Set ${setId} selections:`, selectionCounts);
        }
      });

      // Update saved result with selections (use actual jackpot ID)
      const updateResponse = await apiClient.saveProbabilityResult(actualJackpotId, {
        name: savedResult.name || `Imported Jackpot - ${actualJackpotId}`,
        description: savedResult.description || `Probabilities computed for ${result.matches} matches`,
        selections: selections,
        actual_results: actualResults,
      });

      if (updateResponse.success) {
        toast({
          title: 'Success',
          description: `Probabilities computed successfully for ${result.jackpotId}. You can now view validation.`,
        });

        // Refresh jackpot results
        const refreshResponse = await apiClient.getImportedJackpots();
        if (refreshResponse.success && refreshResponse.data?.jackpots) {
          const transformed = refreshResponse.data.jackpots.map(j => ({
            id: j.id,
            jackpotId: j.jackpotId,
            date: j.date || new Date().toISOString().split('T')[0],
            matches: j.matches,
            status: j.status,
            correctPredictions: j.correctPredictions,
            hasProbabilities: j.status === 'validated' || j.status === 'probabilities_computed'
          }));
          console.log('Refreshed jackpot results:', transformed.find(j => j.jackpotId === actualJackpotId));
          setJackpotResults(transformed);
        } else {
          console.warn('Failed to refresh jackpot results:', refreshResponse);
        }
      }
    } catch (error: any) {
      console.error('Error computing probabilities:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to compute probabilities',
        variant: 'destructive',
      });
    } finally {
      setComputingProbabilities(prev => {
        const next = new Set(prev);
        next.delete(result.jackpotId);
        return next;
      });
    }
  };

  const handleViewValidation = (jackpotId: string) => {
    navigate(`/jackpot-validation?jackpotId=${jackpotId}`);
  };

  const totalRecords = sources.reduce((acc, s) => acc + (s.recordCount || 0), 0);
  const sourcesWithData = sources.filter(s => s.recordCount).length;

  return (
    <PageLayout
      title="Data Ingestion"
      description="Download and import football match data from external sources"
      icon={<Database className="h-6 w-6" />}
    >
      <div className="space-y-6">

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
              value="draw-structural" 
              className="h-12 px-6 text-sm font-medium data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none border-b-2 border-transparent transition-all hover:bg-muted/50 gap-2"
            >
              <BarChart3 className="h-4 w-4" />
              Draw Structural
            </TabsTrigger>
            <TabsTrigger 
              value="data-sources" 
              className="h-12 px-6 text-sm font-medium data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none border-b-2 border-transparent transition-all hover:bg-muted/50 gap-2"
            >
              <FileSpreadsheet className="h-4 w-4" />
              Data Sources
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
                        <TableCell className="text-sm">{formatSeasonDisplay(selectedSeason)}</TableCell>
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

          {/* Data Schema Card - Enhanced Modern Design */}
          <Card className="border-primary/20 bg-gradient-to-br from-background via-background to-primary/5 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-transparent to-primary/5 opacity-50" />
            <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
            <CardHeader className="relative">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
                  <Layers className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-primary animate-pulse" />
                    Data Schema
                  </CardTitle>
                  <CardDescription className="mt-1">
                    Structured format for match and odds data
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="relative">
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50 border border-border/50">
                  <Database className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm font-medium mb-1">CSV Structure</p>
                    <p className="text-xs text-muted-foreground">
                      Each CSV contains: <span className="font-mono text-primary">Date</span>, <span className="font-mono text-primary">HomeTeam</span>, <span className="font-mono text-primary">AwayTeam</span>, <span className="font-mono text-primary">FTHG</span>, <span className="font-mono text-primary">FTAG</span>, <span className="font-mono text-primary">FTR</span>, <span className="font-mono text-primary">B365H</span>, <span className="font-mono text-primary">B365D</span>, <span className="font-mono text-primary">B365A</span>
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50 border border-border/50">
                  <Zap className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm font-medium mb-1">Processing</p>
                    <p className="text-xs text-muted-foreground">
                      Data is normalized and stored for model training with automatic validation and cleaning.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Available Downloaded Data - Enhanced Modern Design */}
            <Card className="border-primary/20 bg-gradient-to-br from-background via-background to-primary/5 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-transparent to-primary/5 opacity-50" />
              <div className="absolute bottom-0 left-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />
              <CardHeader className="relative">
              <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
                      <HardDrive className="h-5 w-5 text-primary" />
                    </div>
                <div>
                <CardTitle className="text-lg flex items-center gap-2">
                        <Activity className="h-4 w-4 text-primary animate-pulse" />
                    Available Downloaded Data
                </CardTitle>
                      <CardDescription className="mt-1">
                    Data available in database and file system from previous downloads
                </CardDescription>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="secondary" className="text-xs bg-primary/10 text-primary border-primary/20">
                        <Database className="h-3 w-3 mr-1" />
                        {batchSummary?.totalBatches || 0} batches
                      </Badge>
                      <Badge variant="secondary" className="text-xs bg-primary/10 text-primary border-primary/20">
                        <FileSpreadsheet className="h-3 w-3 mr-1" />
                        {(batchSummary?.totalRecords || 0).toLocaleString()} records
                      </Badge>
                      <Badge variant="secondary" className="text-xs bg-primary/10 text-primary border-primary/20">
                        <FileSpreadsheet className="h-3 w-3 mr-1" />
                        {batchSummary?.totalFiles || 0} CSV files
                      </Badge>
                      <Badge variant="secondary" className="text-xs bg-primary/10 text-primary border-primary/20">
                        <Globe className="h-3 w-3 mr-1" />
                        {batchSummary?.uniqueLeagues || 0} leagues
                      </Badge>
                    </div>
                  <Button
                    variant="outline"
                    size="sm"
                      className="border-primary/20 hover:bg-primary/10 hover:border-primary/30"
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
              <CardContent className="relative">
              {loadingBatches ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="relative">
                    <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl animate-pulse" />
                    <Loader2 className="h-8 w-8 animate-spin text-primary relative z-10" />
                  </div>
                  <span className="text-sm text-muted-foreground mt-4">Loading batch history...</span>
                </div>
              ) : batchHistory.length === 0 ? (
                <div className="text-center py-12 relative">
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-32 h-32 bg-primary/5 rounded-full blur-2xl" />
                  </div>
                  <div className="relative z-10">
                    <div className="inline-flex p-4 rounded-2xl bg-primary/10 border border-primary/20 mb-4">
                      <Database className="h-12 w-12 text-primary/50" />
                    </div>
                    <p className="text-sm font-medium mt-4">No downloaded data found</p>
                    <p className="text-xs text-muted-foreground mt-2">Download data using the table above to get started</p>
                  </div>
                </div>
              ) : (
                <ScrollArea className="h-[400px]">
                  <div className="space-y-3 pr-4">
                    {batchHistory.map((batch) => (
                      <div
                        key={batch.id}
                        className="group flex items-center justify-between p-4 rounded-lg border border-border/50 bg-gradient-to-r from-muted/30 via-muted/20 to-muted/30 hover:from-muted/50 hover:via-muted/40 hover:to-muted/50 hover:border-primary/30 transition-all duration-300 relative overflow-hidden"
                      >
                        <div className="absolute inset-0 bg-gradient-to-r from-primary/0 via-primary/5 to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                        <div className="relative z-10 flex items-start gap-4 flex-1">
                          <div className="flex flex-col min-w-[140px]">
                            <div className="flex items-center gap-2 mb-1">
                              <div className="p-1.5 rounded-md bg-primary/10 border border-primary/20">
                                <Activity className="h-3.5 w-3.5 text-primary" />
                              </div>
                              <span className="font-mono font-semibold text-primary text-sm">
                              Batch #{batch.batchNumber}
                            </span>
                            </div>
                            <span className="text-xs text-muted-foreground mt-1">
                              {batch.completedAt 
                                ? new Date(batch.completedAt).toLocaleString()
                                : batch.startedAt
                                ? new Date(batch.startedAt).toLocaleString()
                                : 'Unknown date'}
                            </span>
                            <Badge variant="outline" className="text-xs mt-2 w-fit border-primary/20 bg-primary/5">
                              {batch.source}
                            </Badge>
                          </div>
                          
                          {batch.fileInfo && (
                            <div className="flex flex-col gap-3 flex-1">
                              <div className="flex flex-wrap gap-1.5">
                                {(() => {
                                  // Use leagueDetails if available (includes names), otherwise fall back to codes
                                  const leagueDetails = batch.fileInfo.leagueDetails || {};
                                  const leaguesToShow = batch.fileInfo.leagues.slice(0, 5);
                                  
                                  return leaguesToShow.map((leagueCode, idx) => {
                                    const leagueInfo = leagueDetails[leagueCode];
                                    const displayName = leagueInfo ? `${leagueInfo.name} (${leagueCode})` : leagueCode;
                                    
                                    return (
                                      <Badge key={idx} variant="secondary" className="text-xs bg-primary/10 text-primary border-primary/20">
                                        <Globe className="h-3 w-3 mr-1" />
                                        {displayName}
                              </Badge>
                                    );
                                  });
                                })()}
                                {batch.fileInfo.leagues.length > 5 && (
                                  <Badge variant="secondary" className="text-xs bg-primary/10 text-primary border-primary/20">
                                    +{batch.fileInfo.leagues.length - 5} more
                              </Badge>
                            )}
                          </div>
                              <div className="flex items-center gap-4 text-xs">
                                <div className="flex items-center gap-1.5 text-muted-foreground">
                                  <FileSpreadsheet className="h-3.5 w-3.5 text-primary" />
                                  <span className="font-medium text-foreground">{batch.fileInfo.csvCount}</span> CSV file{batch.fileInfo.csvCount !== 1 ? 's' : ''}
                                </div>
                                {batch.fileInfo.seasons.length > 0 && (
                                  <div className="flex items-center gap-1.5 text-muted-foreground">
                                    <Calendar className="h-3.5 w-3.5 text-primary" />
                                    <span>Seasons: {batch.fileInfo.seasons.slice(0, 3).join(', ')}</span>
                                    {batch.fileInfo.seasons.length > 3 && <span>+{batch.fileInfo.seasons.length - 3}</span>}
                                  </div>
                                )}
                        </div>
                              <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-mono">
                                <HardDrive className="h-3.5 w-3.5 text-primary" />
                                <span className="truncate max-w-md">{batch.fileInfo.folderName}</span>
                              </div>
                            </div>
                          )}
                          
                          {!batch.fileInfo && batch.leagueCode && (
                            <div className="flex flex-col gap-2">
                              <Badge variant="outline" className="text-xs w-fit border-primary/20 bg-primary/5">
                                <Globe className="h-3 w-3 mr-1" />
                                {batch.leagueCode}
                              </Badge>
                              {batch.season && (
                                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                  <Calendar className="h-3.5 w-3.5 text-primary" />
                                  <span>Season: {batch.season}</span>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                        
                        <div className="relative z-10 flex items-center gap-3 flex-shrink-0">
                          <div className="text-right">
                            <div className="flex items-center gap-1.5 text-sm font-semibold tabular-nums text-primary">
                              <Database className="h-4 w-4" />
                              {batch.recordsInserted.toLocaleString()}
                            </div>
                            <div className="text-xs text-muted-foreground mt-0.5">
                              records
                            </div>
                            {batch.recordsProcessed > 0 && (
                              <div className="text-xs text-muted-foreground mt-1">
                                {batch.recordsProcessed.toLocaleString()} processed
                              </div>
                            )}
                          </div>
                          <div className="flex flex-col gap-2">
                          <Badge 
                            className={
                              batch.status === 'completed' 
                                  ? 'bg-green-500/20 text-green-400 border-green-500/30 shadow-lg shadow-green-500/10'
                                : batch.status === 'failed'
                                  ? 'bg-red-500/20 text-red-400 border-red-500/30 shadow-lg shadow-red-500/10'
                                  : 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30 shadow-lg shadow-yellow-500/10'
                            }
                          >
                            {batch.status === 'completed' && <CheckCircle className="h-3 w-3 mr-1" />}
                            {batch.status === 'failed' && <AlertCircle className="h-3 w-3 mr-1" />}
                            {batch.status}
                          </Badge>
                          {batch.hasFiles && (
                              <Badge variant="outline" className="text-xs border-primary/20 bg-primary/5">
                              <FileSpreadsheet className="h-3 w-3 mr-1" />
                              Files
                            </Badge>
                          )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
              </CardContent>
            </Card>
        </TabsContent>

        {/* Data Sources Tab */}
        <TabsContent value="data-sources" className="space-y-6">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>Comprehensive Data Sources</AlertTitle>
            <AlertDescription>
              Multiple data sources enhance model accuracy, especially for draw probability calibration. 
              Each source provides unique signals that improve jackpot prediction consistency.
            </AlertDescription>
          </Alert>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 1. Football-Data.co.uk */}
            <ModernCard
              title="Football-Data.co.uk"
              description="Historical Match Results & Odds (Primary Source)"
              icon={<Database className="h-5 w-5" />}
              variant="glow"
            >
              <div className="space-y-4">
                <div>
                  <Badge variant="secondary" className="mb-2">FREE • CSV • Active</Badge>
                  <p className="text-sm text-muted-foreground">
                    <strong>URL:</strong> https://www.football-data.co.uk/mmz4281/{'{season}'}/{'{league_code}'}.csv
                  </p>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">What You Get:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>20+ years of league results</li>
                    <li>Goals, halftime/fulltime scores</li>
                    <li>Closing odds (1X2) from multiple bookmakers</li>
                    <li>43 leagues across multiple countries</li>
                    <li>Bet365, Pinnacle, and average odds</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">Why It Helps:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Long-horizon stability for model training</li>
                    <li>Low variance draw frequency estimation</li>
                    <li>League-specific draw baselines</li>
                    <li>Draw rate is league-structural, not seasonal noise</li>
                    <li>Enables league draw priors (mandatory for jackpot pools)</li>
                  </ul>
                </div>
                <div className="pt-2 border-t">
                  <Badge variant="outline" className="text-xs">Status: ✅ Active</Badge>
                </div>
              </div>
            </ModernCard>

            {/* 2. Football-Data.org */}
            <ModernCard
              title="Football-Data.org"
              description="Match-Level Outcome & Odds Data"
              icon={<Globe className="h-5 w-5" />}
              variant="default"
            >
              <div className="space-y-4">
                <div>
                  <Badge variant="secondary" className="mb-2">FREE • API • Planned</Badge>
                  <p className="text-sm text-muted-foreground">
                    RESTful API for fixtures and odds
                  </p>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">What You Get:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Fixtures (past & upcoming)</li>
                    <li>Final scores</li>
                    <li>1X2 odds (multiple bookmakers)</li>
                    <li>Match status, kickoff time</li>
                    <li>Opening vs closing odds (market movement)</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">Why It Helps:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Primary training labels</li>
                    <li>Odds = market prior (not oracle)</li>
                    <li>Enables odds blending + calibration</li>
                    <li>Market draw odds often better calibrated than model raw outputs</li>
                    <li>Narrowing draw odds = rising stalemate expectation</li>
                  </ul>
                </div>
                <div className="pt-2 border-t">
                  <Badge variant="outline" className="text-xs">Status: 🚧 Planned</Badge>
                </div>
              </div>
            </ModernCard>

            {/* 3. API-Football */}
            <ModernCard
              title="API-Football (RapidAPI)"
              description="Head-to-Head Statistics & Real-time Data"
              icon={<FileSpreadsheet className="h-5 w-5" />}
              variant="default"
            >
              <div className="space-y-4">
                <div>
                  <Badge variant="secondary" className="mb-2">FREE Tier Available • API • Planned</Badge>
                  <p className="text-sm text-muted-foreground">
                    <strong>Endpoint:</strong> https://v3.football.api-sports.io
                  </p>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">What You Get:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Historical meetings between two teams</li>
                    <li>Goals scored, wins/draws/losses</li>
                    <li>Venue-specific H2H</li>
                    <li>Real-time fixtures and results</li>
                    <li>900+ leagues coverage</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">Why It Helps:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Captures stylistic stalemates</li>
                    <li>Rivalry effects</li>
                    <li>Tactical deadlocks</li>
                    <li>Repeated low-goal H2H → draw inflation factor</li>
                    <li>Especially powerful when Poisson home ≈ away</li>
                  </ul>
                </div>
                <div className="pt-2 border-t">
                  <Badge variant="outline" className="text-xs">Status: 🚧 Planned</Badge>
                </div>
              </div>
            </ModernCard>

            {/* 4. ClubElo */}
            <ModernCard
              title="ClubElo"
              description="Team Strength Proxies"
              icon={<TrendingUp className="h-5 w-5" />}
              variant="default"
            >
              <div className="space-y-4">
                <div>
                  <Badge variant="secondary" className="mb-2">FREE • CSV • Planned</Badge>
                  <p className="text-sm text-muted-foreground">
                    Daily Elo ratings per team
                  </p>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">What You Get:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Daily Elo ratings per team</li>
                    <li>Attack/defense adjusted strength</li>
                    <li>Smooth, stable strength estimates</li>
                    <li>Historical rating trends</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">Why It Helps:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Replaces subjective "form"</li>
                    <li>Smooth, stable strength estimates</li>
                    <li>Elo difference ≈ 0 → draw probability ↑</li>
                    <li>Strong empirical draw signal across leagues</li>
                  </ul>
                </div>
                <div className="pt-2 border-t">
                  <Badge variant="outline" className="text-xs">Status: 🚧 Planned</Badge>
                </div>
              </div>
            </ModernCard>

            {/* 5. Understat */}
            <ModernCard
              title="Understat"
              description="Goal Expectancy Components (xG-lite)"
              icon={<Target className="h-5 w-5" />}
              variant="default"
            >
              <div className="space-y-4">
                <div>
                  <Badge variant="secondary" className="mb-2">FREE • Scrape/API-lite • Planned</Badge>
                  <p className="text-sm text-muted-foreground">
                    Expected goals and shot statistics
                  </p>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">What You Get:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Expected goals (xG)</li>
                    <li>Shots, deep completions</li>
                    <li>Shot quality metrics</li>
                    <li>Possession-adjusted statistics</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">Why It Helps:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Separates dominance from finishing luck</li>
                    <li>Improves Poisson λ estimation</li>
                    <li>Low combined xG + symmetry → draw likelihood</li>
                    <li>Prevents overconfidence in 1-goal games</li>
                  </ul>
                </div>
                <div className="pt-2 border-t">
                  <Badge variant="outline" className="text-xs">Status: 🚧 Planned</Badge>
                </div>
              </div>
            </ModernCard>

            {/* 6. WorldFootball.net */}
            <ModernCard
              title="WorldFootball.net"
              description="Referee Statistics & League Metadata"
              icon={<Users className="h-5 w-5" />}
              variant="default"
            >
              <div className="space-y-4">
                <div>
                  <Badge variant="secondary" className="mb-2">FREE • Scrape • Planned</Badge>
                  <p className="text-sm text-muted-foreground">
                    Referee and league structural data
                  </p>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">What You Get:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Referee match history</li>
                    <li>Cards per game</li>
                    <li>Penalties awarded</li>
                    <li>League size, relegation pressure</li>
                    <li>Promotion zones</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">Why It Helps:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Game disruption modeling</li>
                    <li>Variance control</li>
                    <li>Low-penalty, low-card referees → more stalemates</li>
                    <li>Relegation six-pointers → high draw rate</li>
                    <li>End-season mid-table matches → draw spikes</li>
                  </ul>
                </div>
                <div className="pt-2 border-t">
                  <Badge variant="outline" className="text-xs">Status: 🚧 Planned</Badge>
                </div>
              </div>
            </ModernCard>

            {/* 7. Scheduling & Fatigue */}
            <ModernCard
              title="Scheduling & Fatigue Signals"
              description="Match Congestion & Rest Days"
              icon={<Calendar className="h-5 w-5" />}
              variant="default"
            >
              <div className="space-y-4">
                <div>
                  <Badge variant="secondary" className="mb-2">FREE • API • Planned</Badge>
                  <p className="text-sm text-muted-foreground">
                    Via Football-Data.org API
                  </p>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">What You Get:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Match congestion</li>
                    <li>Days of rest</li>
                    <li>Home/away sequences</li>
                    <li>Fixture density</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">Why It Helps:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Fatigue reduces pressing & finishing</li>
                    <li>Increases conservative tactics</li>
                    <li>Short rest + away team → draw bias</li>
                    <li>Midweek matches inflate draws</li>
                  </ul>
                </div>
                <div className="pt-2 border-t">
                  <Badge variant="outline" className="text-xs">Status: 🚧 Planned</Badge>
                </div>
              </div>
            </ModernCard>

            {/* 8. Open-Meteo */}
            <ModernCard
              title="Open-Meteo"
              description="Weather Data (Free, Deterministic)"
              icon={<Globe className="h-5 w-5" />}
              variant="default"
            >
              <div className="space-y-4">
                <div>
                  <Badge variant="secondary" className="mb-2">FREE • API • Planned</Badge>
                  <p className="text-sm text-muted-foreground">
                    Historical and forecast weather data
                  </p>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">What You Get:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Temperature</li>
                    <li>Rain/precipitation</li>
                    <li>Wind speed</li>
                    <li>Weather conditions at match time</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-2">Why It Helps:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Match tempo adjustment</li>
                    <li>Shot quality degradation</li>
                    <li>Rain + wind → fewer goals → draw inflation</li>
                    <li>Particularly relevant in lower leagues</li>
                  </ul>
                </div>
                <div className="pt-2 border-t">
                  <Badge variant="outline" className="text-xs">Status: 🚧 Planned</Badge>
                </div>
              </div>
            </ModernCard>
          </div>

          {/* Recommended Stack */}
          <ModernCard
            title="Recommended Minimal FREE Data Stack"
            description="Production-safe baseline for optimal draw calibration"
            icon={<CheckCircle className="h-5 w-5" />}
            variant="elevated"
            className="mt-6"
          >
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                For a clean, production-safe baseline, prioritize these sources:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="font-medium text-sm">Football-Data.co.uk</span>
                    <Badge variant="secondary" className="text-xs">✅ Active</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground ml-6">Historical results + odds</p>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-blue-600" />
                    <span className="font-medium text-sm">Football-Data.org API</span>
                    <Badge variant="outline" className="text-xs">🚧 Planned</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground ml-6">Fixtures + odds</p>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-blue-600" />
                    <span className="font-medium text-sm">ClubElo ratings</span>
                    <Badge variant="outline" className="text-xs">🚧 Planned</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground ml-6">Team strength proxies</p>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-blue-600" />
                    <span className="font-medium text-sm">H2H stats</span>
                    <Badge variant="outline" className="text-xs">🚧 Planned</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground ml-6">Head-to-head statistics</p>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-blue-600" />
                    <span className="font-medium text-sm">Weather (Open-Meteo)</span>
                    <Badge variant="outline" className="text-xs">🚧 Planned</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground ml-6">Match conditions</p>
                </div>
              </div>
              <div className="pt-4 border-t">
                <h4 className="font-semibold text-sm mb-2">This Stack Materially Improves:</h4>
                <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                  <li>Draw probability calibration</li>
                  <li>Odds blending stability</li>
                  <li>Jackpot hit-rate consistency</li>
                </ul>
              </div>
            </div>
          </ModernCard>

          {/* What NOT to Use */}
          <Alert variant="destructive" className="mt-6">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>What You Should NOT Use (By Design)</AlertTitle>
            <AlertDescription>
              <p className="mb-2">You are correct to exclude these sources as they hurt calibration and fail audit defensibility:</p>
              <ul className="list-disc list-inside space-y-1 text-sm">
                <li>Social media sentiment</li>
                <li>Injury rumors</li>
                <li>Lineups prediction models</li>
                <li>Neural network outputs</li>
              </ul>
            </AlertDescription>
          </Alert>
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
                  <Button 
                    onClick={(e) => {
                      e.preventDefault();
                      console.log('Import button clicked');
                      handleImportJackpot();
                    }} 
                    disabled={!manualInput.trim()}
                  >
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
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {loadingJackpots ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center py-8">
                            <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
                            <p className="text-sm text-muted-foreground">Loading imported jackpots...</p>
                          </TableCell>
                        </TableRow>
                      ) : jackpotResults.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center py-8">
                            <Trophy className="h-8 w-8 mx-auto mb-2 opacity-50" />
                            <p className="text-sm text-muted-foreground">No imported jackpots yet</p>
                            <p className="text-xs text-muted-foreground mt-1">
                              Import jackpot results using the format shown above
                            </p>
                          </TableCell>
                        </TableRow>
                      ) : (
                        jackpotResults.map((result) => (
                        <TableRow key={result.id}>
                          <TableCell className="font-mono text-sm">{result.jackpotId}</TableCell>
                          <TableCell className="text-sm">{formatDate(result.date)}</TableCell>
                          <TableCell className="text-right">{result.matches}</TableCell>
                          <TableCell>
                            {result.status === 'validated' ? (
                              <Badge variant="secondary" className="bg-green-500/10 text-green-600">
                                Validated
                              </Badge>
                            ) : result.hasProbabilities ? (
                              <Badge variant="secondary" className="bg-purple-500/10 text-purple-600">
                                Probabilities Computed
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
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              {!result.hasProbabilities && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleComputeProbabilities(result)}
                                  disabled={computingProbabilities.has(result.jackpotId)}
                                >
                                  {computingProbabilities.has(result.jackpotId) ? (
                                    <>
                                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                      Computing...
                                    </>
                                  ) : (
                                    <>
                                      <Calculator className="h-3 w-3 mr-1" />
                                      Compute
                                    </>
                                  )}
                                </Button>
                              )}
                              {result.hasProbabilities && (
                                <Button
                                  size="sm"
                                  variant="default"
                                  onClick={() => handleViewValidation(result.jackpotId)}
                                >
                                  <Eye className="h-3 w-3 mr-1" />
                                  View Validation
                                </Button>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          <Alert>
            <Trophy className="h-4 w-4" />
            <AlertTitle>Validation Flow</AlertTitle>
            <AlertDescription className="space-y-2">
              <p>
              Imported jackpot results are compared against model predictions to compute calibration metrics.
              </p>
              <div className="flex items-center gap-2 mt-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => navigate('/jackpot-validation')}
                >
                  <ArrowRight className="h-3 w-3 mr-1" />
                  Go to Validation Page
                </Button>
              </div>
            </AlertDescription>
          </Alert>
        </TabsContent>

        {/* Draw Structural Data Tab */}
        <TabsContent value="draw-structural" className="space-y-4">
          <DrawStructuralIngestion />
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
    </PageLayout>
  );
}
