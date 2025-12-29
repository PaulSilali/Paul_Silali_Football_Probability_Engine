import { useState, useCallback } from 'react';
import { 
  RefreshCw, 
  Clock, 
  Database, 
  FileText, 
  Lock, 
  Download, 
  Play, 
  Loader2, 
  CheckCircle, 
  AlertCircle,
  Globe,
  FileSpreadsheet,
  Power,
  Trash2,
  Eye
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Checkbox } from '@/components/ui/checkbox';
import { useToast } from '@/hooks/use-toast';
import { exportAuditLog } from '@/lib/export';
import type { ModelVersion, DataUpdate, AuditEntry } from '@/types';

// Extended model registry with training metadata
interface ExtendedModelVersion extends ModelVersion {
  trainingData: {
    seasons: string;
    leagues: number;
    matches: number;
  };
  metrics: {
    brierScore: number;
    logLoss: number;
    drawAccuracy: number;
  };
  trainedBy: string;
  trainingDuration: string;
}

const modelRegistry: ExtendedModelVersion[] = [
  { 
    id: '1', 
    version: 'v2.4.1', 
    releaseDate: '2024-12-15', 
    description: 'Improved home advantage calibration', 
    isActive: true, 
    lockedJackpots: 3,
    trainingData: { seasons: '2018-2024', leagues: 12, matches: 45672 },
    metrics: { brierScore: 0.142, logLoss: 0.891, drawAccuracy: 58.2 },
    trainedBy: 'Scheduled',
    trainingDuration: '4m 32s'
  },
  { 
    id: '2', 
    version: 'v2.4.0', 
    releaseDate: '2024-11-28', 
    description: 'Added draw inflation adjustment', 
    isActive: false, 
    lockedJackpots: 12,
    trainingData: { seasons: '2018-2024', leagues: 12, matches: 44856 },
    metrics: { brierScore: 0.148, logLoss: 0.912, drawAccuracy: 55.8 },
    trainedBy: 'Manual',
    trainingDuration: '4m 18s'
  },
  { 
    id: '3', 
    version: 'v2.3.2', 
    releaseDate: '2024-10-15', 
    description: 'Bug fixes for odds parsing', 
    isActive: false, 
    lockedJackpots: 8,
    trainingData: { seasons: '2018-2024', leagues: 10, matches: 42340 },
    metrics: { brierScore: 0.155, logLoss: 0.934, drawAccuracy: 52.1 },
    trainedBy: 'Manual',
    trainingDuration: '3m 58s'
  },
  { 
    id: '4', 
    version: 'v2.3.1', 
    releaseDate: '2024-09-01', 
    description: 'Initial Dixon-Coles implementation', 
    isActive: false, 
    lockedJackpots: 24,
    trainingData: { seasons: '2017-2024', leagues: 8, matches: 38920 },
    metrics: { brierScore: 0.162, logLoss: 0.958, drawAccuracy: 48.5 },
    trainedBy: 'Manual',
    trainingDuration: '3m 42s'
  },
];

// Data sources for Football-Data.co.uk download
interface DataSource {
  id: string;
  name: string;
  url: string;
  leagues: string[];
  seasons: string;
  status: 'idle' | 'downloading' | 'completed' | 'failed';
  progress: number;
  recordCount?: number;
}

const initialDataSources: DataSource[] = [
  { id: '1', name: 'Premier League', url: 'football-data.co.uk/englandm.php', leagues: ['E0'], seasons: '2018-2024', status: 'idle', progress: 0 },
  { id: '2', name: 'Championship', url: 'football-data.co.uk/englandm.php', leagues: ['E1'], seasons: '2018-2024', status: 'idle', progress: 0 },
  { id: '3', name: 'La Liga', url: 'football-data.co.uk/spainm.php', leagues: ['SP1'], seasons: '2018-2024', status: 'idle', progress: 0 },
  { id: '4', name: 'Bundesliga', url: 'football-data.co.uk/germanym.php', leagues: ['D1'], seasons: '2018-2024', status: 'idle', progress: 0 },
  { id: '5', name: 'Serie A', url: 'football-data.co.uk/italym.php', leagues: ['I1'], seasons: '2018-2024', status: 'idle', progress: 0 },
  { id: '6', name: 'Ligue 1', url: 'football-data.co.uk/francem.php', leagues: ['F1'], seasons: '2018-2024', status: 'idle', progress: 0 },
  { id: '7', name: 'League One', url: 'football-data.co.uk/englandm.php', leagues: ['E2'], seasons: '2018-2024', status: 'idle', progress: 0 },
  { id: '8', name: 'League Two', url: 'football-data.co.uk/englandm.php', leagues: ['E3'], seasons: '2018-2024', status: 'idle', progress: 0 },
];

const initialDataUpdates: DataUpdate[] = [
  { id: '1', source: 'Match Results', status: 'completed', progress: 100, startedAt: '2024-12-27T10:00:00Z', completedAt: '2024-12-27T10:05:32Z' },
  { id: '2', source: 'Team Ratings', status: 'completed', progress: 100, startedAt: '2024-12-27T08:00:00Z', completedAt: '2024-12-27T08:12:45Z' },
  { id: '3', source: 'Market Odds', status: 'completed', progress: 100, startedAt: '2024-12-27T11:30:00Z', completedAt: '2024-12-27T11:35:00Z' },
];

const dataFreshness = [
  { source: 'Match Results', lastUpdated: '2024-12-27T10:05:32Z', recordCount: 45672 },
  { source: 'Team Ratings', lastUpdated: '2024-12-27T08:12:45Z', recordCount: 2340 },
  { source: 'Market Odds', lastUpdated: '2024-12-26T22:00:00Z', recordCount: 128945 },
  { source: 'League Metadata', lastUpdated: '2024-12-20T14:30:00Z', recordCount: 156 },
];

const auditLog: AuditEntry[] = [
  { id: '1', timestamp: '2024-12-27T11:45:23Z', action: 'Probability Calculation', modelVersion: 'v2.4.1', probabilitySet: 'Set A', jackpotId: 'JK-2024-1234', details: 'Calculated probabilities for 13 fixtures' },
  { id: '2', timestamp: '2024-12-27T10:30:00Z', action: 'Model Validation', modelVersion: 'v2.4.1', probabilitySet: 'All Sets', details: 'Automated validation completed successfully' },
  { id: '3', timestamp: '2024-12-27T10:05:32Z', action: 'Data Update', modelVersion: 'v2.4.1', probabilitySet: '-', details: 'Match Results updated with 156 new records' },
  { id: '4', timestamp: '2024-12-26T16:20:15Z', action: 'Probability Calculation', modelVersion: 'v2.4.1', probabilitySet: 'Set B', jackpotId: 'JK-2024-1233', details: 'Calculated probabilities for 15 fixtures' },
  { id: '5', timestamp: '2024-12-26T14:00:00Z', action: 'Model Activation', modelVersion: 'v2.4.1', probabilitySet: '-', details: 'Model version v2.4.1 activated' },
];

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatTime(dateString: string) {
  return new Date(dateString).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDateTime(dateString: string) {
  return `${formatDate(dateString)} ${formatTime(dateString)}`;
}

// Data download hook (simulates Football-Data.co.uk CSV download via backend)
function useDataDownload() {
  const [sources, setSources] = useState<DataSource[]>(initialDataSources);
  const [isDownloading, setIsDownloading] = useState(false);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
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

  const startDownload = useCallback(() => {
    if (selectedSources.length === 0) return;
    
    setIsDownloading(true);
    
    // Reset selected sources to downloading
    setSources(prev => prev.map(s => 
      selectedSources.includes(s.id) 
        ? { ...s, status: 'idle' as const, progress: 0 }
        : s
    ));

    let currentIndex = 0;
    const toDownload = selectedSources.slice();

    const processNext = () => {
      if (currentIndex >= toDownload.length) {
        setIsDownloading(false);
        toast({
          title: 'Download Complete',
          description: `Downloaded ${toDownload.length} data sources from Football-Data.co.uk`,
        });
        return;
      }

      const sourceId = toDownload[currentIndex];
      setSources(prev => prev.map(s => 
        s.id === sourceId ? { ...s, status: 'downloading' as const, progress: 0 } : s
      ));

      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 20 + 10;
        if (progress >= 100) {
          progress = 100;
          clearInterval(interval);
          const recordCount = Math.floor(Math.random() * 3000) + 2000;
          setSources(prev => prev.map(s => 
            s.id === sourceId 
              ? { ...s, status: 'completed' as const, progress: 100, recordCount }
              : s
          ));
          currentIndex++;
          setTimeout(processNext, 200);
        } else {
          setSources(prev => prev.map(s => 
            s.id === sourceId ? { ...s, progress: Math.min(progress, 99) } : s
          ));
        }
      }, 150);
    };

    processNext();
  }, [selectedSources, toast]);

  return { sources, isDownloading, selectedSources, toggleSource, selectAll, startDownload };
}

// Simulated WebSocket-style progress hook
function useDataUpdateProgress() {
  const [updates, setUpdates] = useState<DataUpdate[]>(initialDataUpdates);
  const [isUpdating, setIsUpdating] = useState(false);

  const triggerUpdate = useCallback(() => {
    setIsUpdating(true);
    const sources = ['Match Results', 'Team Ratings', 'Market Odds', 'League Metadata'];
    
    const newUpdates: DataUpdate[] = sources.map((source, i) => ({
      id: String(i + 1),
      source,
      status: 'pending' as const,
      progress: 0,
      startedAt: new Date().toISOString(),
    }));
    setUpdates(newUpdates);

    let currentIndex = 0;
    
    const processNext = () => {
      if (currentIndex >= sources.length) {
        setIsUpdating(false);
        return;
      }

      const idx = currentIndex;
      setUpdates(prev => prev.map((u, i) => 
        i === idx ? { ...u, status: 'in_progress' as const, progress: 0 } : u
      ));

      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 15 + 5;
        if (progress >= 100) {
          progress = 100;
          clearInterval(interval);
          setUpdates(prev => prev.map((u, i) => 
            i === idx ? { ...u, status: 'completed' as const, progress: 100, completedAt: new Date().toISOString() } : u
          ));
          currentIndex++;
          setTimeout(processNext, 300);
        } else {
          setUpdates(prev => prev.map((u, i) => 
            i === idx ? { ...u, progress: Math.min(progress, 99) } : u
          ));
        }
      }, 200);
    };

    processNext();
  }, []);

  return { updates, isUpdating, triggerUpdate };
}

// Retrain simulation hook
function useModelRetrain() {
  const [isRetraining, setIsRetraining] = useState(false);
  const [retrainProgress, setRetrainProgress] = useState(0);
  const [retrainPhase, setRetrainPhase] = useState('');
  const { toast } = useToast();

  const startRetrain = useCallback(() => {
    setIsRetraining(true);
    setRetrainProgress(0);
    
    const phases = [
      'Loading historical data...',
      'Computing team strengths...',
      'Fitting Dixon-Coles model...',
      'Running calibration...',
      'Validating out-of-sample...',
      'Generating probability sets...',
      'Finalizing model version...',
    ];

    let phaseIndex = 0;
    let progress = 0;

    const interval = setInterval(() => {
      progress += Math.random() * 8 + 2;
      
      if (progress >= (phaseIndex + 1) * (100 / phases.length)) {
        phaseIndex = Math.min(phaseIndex + 1, phases.length - 1);
      }
      
      setRetrainPhase(phases[phaseIndex]);
      setRetrainProgress(Math.min(progress, 100));

      if (progress >= 100) {
        clearInterval(interval);
        setIsRetraining(false);
        setRetrainProgress(100);
        setRetrainPhase('Complete');
        toast({
          title: 'Model Retrained Successfully',
          description: 'New model version v2.4.2 is ready for activation.',
        });
      }
    }, 300);
  }, [toast]);

  return { isRetraining, retrainProgress, retrainPhase, startRetrain };
}

export default function System() {
  const [showRetrainDialog, setShowRetrainDialog] = useState(false);
  const [showDownloadDialog, setShowDownloadDialog] = useState(false);
  const { updates, isUpdating, triggerUpdate } = useDataUpdateProgress();
  const { isRetraining, retrainProgress, retrainPhase, startRetrain } = useModelRetrain();
  const { sources, isDownloading, selectedSources, toggleSource, selectAll, startDownload } = useDataDownload();
  const { toast } = useToast();

  const handleRetrain = () => {
    setShowRetrainDialog(false);
    startRetrain();
  };

  const handleActivateVersion = (version: string) => {
    toast({
      title: 'Model Activated',
      description: `Model ${version} is now the active version.`,
    });
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">System & Data Management</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Model registry, data sources, training, and audit trail
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowDownloadDialog(true)}>
            <Globe className="h-4 w-4 mr-2" />
            Download Data
          </Button>
          <Button size="sm" onClick={() => setShowRetrainDialog(true)} disabled={isRetraining}>
            {isRetraining ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Retraining...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Retrain Model
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Retrain Progress Alert */}
      {isRetraining && (
        <Alert>
          <Loader2 className="h-4 w-4 animate-spin" />
          <AlertDescription className="flex items-center justify-between">
            <div>
              <span className="font-medium">Model Retraining in Progress: </span>
              <span className="text-muted-foreground">{retrainPhase}</span>
            </div>
            <span className="tabular-nums font-medium">{Math.round(retrainProgress)}%</span>
          </AlertDescription>
          <Progress value={retrainProgress} className="mt-2 h-2" />
        </Alert>
      )}

      <Tabs defaultValue="registry">
        <TabsList>
          <TabsTrigger value="registry">Model Registry</TabsTrigger>
          <TabsTrigger value="data">Data Sources</TabsTrigger>
          <TabsTrigger value="audit">Audit Trail</TabsTrigger>
        </TabsList>

        {/* Model Registry Tab */}
        <TabsContent value="registry" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Database className="h-5 w-5" />
                Model Version Registry
              </CardTitle>
              <CardDescription>
                Full history of trained models with metrics and training metadata
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Version</TableHead>
                      <TableHead>Release Date</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead className="text-right">Brier</TableHead>
                      <TableHead className="text-right">Draw Acc</TableHead>
                      <TableHead>Training Data</TableHead>
                      <TableHead className="text-right">Locked</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {modelRegistry.map((model) => (
                      <TableRow key={model.id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-medium">{model.version}</span>
                            {model.isActive && (
                              <Badge variant="secondary" className="bg-green-500/10 text-green-600 text-xs">
                                Active
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDate(model.releaseDate)}
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate text-sm">
                          {model.description}
                        </TableCell>
                        <TableCell className="text-right tabular-nums font-medium">
                          {model.metrics.brierScore.toFixed(3)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {model.metrics.drawAccuracy}%
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {model.trainingData.matches.toLocaleString()} matches
                          <br />
                          {model.trainingData.leagues} leagues
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Lock className="h-3 w-3 text-muted-foreground" />
                            <span className="tabular-nums">{model.lockedJackpots}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            {!model.isActive && (
                              <Button 
                                variant="ghost" 
                                size="icon" 
                                className="h-8 w-8"
                                onClick={() => handleActivateVersion(model.version)}
                              >
                                <Power className="h-4 w-4" />
                              </Button>
                            )}
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Data Freshness */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Data Freshness
              </CardTitle>
              <CardDescription>
                Last update times for each data source
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {dataFreshness.map((source) => (
                  <div key={source.source} className="p-4 border rounded-lg">
                    <div className="font-medium text-sm">{source.source}</div>
                    <div className="text-2xl font-bold tabular-nums mt-1">
                      {source.recordCount.toLocaleString()}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Last: {formatDateTime(source.lastUpdated)}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Data Sources Tab */}
        <TabsContent value="data" className="space-y-6">
          {/* Data Update Progress */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <RefreshCw className={`h-5 w-5 ${isUpdating ? 'animate-spin' : ''}`} />
                  Data Sync Status
                </CardTitle>
                <CardDescription>
                  Background data synchronization with real-time progress
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={triggerUpdate} disabled={isUpdating}>
                {isUpdating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Syncing...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Sync Now
                  </>
                )}
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {updates.map((update) => (
                  <div key={update.id} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {update.status === 'completed' && <CheckCircle className="h-4 w-4 text-green-500" />}
                        {update.status === 'in_progress' && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
                        {update.status === 'pending' && <Clock className="h-4 w-4 text-muted-foreground" />}
                        {update.status === 'failed' && <AlertCircle className="h-4 w-4 text-destructive" />}
                        <span className="font-medium text-sm">{update.source}</span>
                        <Badge 
                          variant={
                            update.status === 'completed' ? 'secondary' : 
                            update.status === 'in_progress' ? 'default' : 
                            'outline'
                          } 
                          className="text-xs"
                        >
                          {update.status === 'in_progress' ? 'Syncing...' : 
                           update.status === 'completed' ? 'Completed' : 
                           update.status === 'pending' ? 'Pending' : 'Failed'}
                        </Badge>
                      </div>
                      <span className="text-xs text-muted-foreground tabular-nums">
                        {update.status === 'completed' && update.completedAt 
                          ? `Completed ${formatTime(update.completedAt)}`
                          : update.status === 'in_progress' 
                          ? `${Math.round(update.progress)}%`
                          : 'Waiting...'}
                      </span>
                    </div>
                    <Progress 
                      value={update.progress} 
                      className={`h-2 ${update.status === 'in_progress' ? 'animate-pulse' : ''}`} 
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Football-Data.co.uk Sources */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <FileSpreadsheet className="h-5 w-5" />
                Football-Data.co.uk Sources
              </CardTitle>
              <CardDescription>
                Historical match results and odds data (free, CSV format)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]">
                      <Checkbox 
                        checked={selectedSources.length === sources.length}
                        onCheckedChange={selectAll}
                      />
                    </TableHead>
                    <TableHead>League</TableHead>
                    <TableHead>Source URL</TableHead>
                    <TableHead>Seasons</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Records</TableHead>
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
                      <TableCell className="text-xs text-muted-foreground font-mono">
                        {source.url}
                      </TableCell>
                      <TableCell className="text-sm">{source.seasons}</TableCell>
                      <TableCell>
                        {source.status === 'idle' && (
                          <Badge variant="outline" className="text-xs">Ready</Badge>
                        )}
                        {source.status === 'downloading' && (
                          <div className="flex items-center gap-2">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            <span className="text-xs tabular-nums">{Math.round(source.progress)}%</span>
                          </div>
                        )}
                        {source.status === 'completed' && (
                          <Badge variant="secondary" className="bg-green-500/10 text-green-600 text-xs">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Done
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {source.recordCount ? source.recordCount.toLocaleString() : '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="flex items-center justify-between mt-4 pt-4 border-t">
                <p className="text-sm text-muted-foreground">
                  {selectedSources.length} source(s) selected
                </p>
                <Button 
                  onClick={startDownload} 
                  disabled={selectedSources.length === 0 || isDownloading}
                >
                  {isDownloading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Downloading...
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4 mr-2" />
                      Download Selected
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Audit Trail Tab */}
        <TabsContent value="audit" className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Audit Trail
                </CardTitle>
                <CardDescription>
                  Recent system actions and calculations
                </CardDescription>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Download className="h-4 w-4 mr-2" />
                    Export
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => exportAuditLog(auditLog.map(e => ({
                    timestamp: formatDateTime(e.timestamp),
                    action: e.action,
                    modelVersion: e.modelVersion,
                    probabilitySet: e.probabilitySet,
                    details: e.details,
                  })), 'csv')}>
                    <Download className="h-4 w-4 mr-2" />
                    Export as CSV
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => exportAuditLog(auditLog.map(e => ({
                    timestamp: formatDateTime(e.timestamp),
                    action: e.action,
                    modelVersion: e.modelVersion,
                    probabilitySet: e.probabilitySet,
                    details: e.details,
                  })), 'pdf')}>
                    <FileText className="h-4 w-4 mr-2" />
                    Export as PDF
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[160px]">Timestamp</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead className="w-[100px]">Model</TableHead>
                      <TableHead className="w-[80px]">Set</TableHead>
                      <TableHead>Details</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {auditLog.map((entry) => (
                      <TableRow key={entry.id}>
                        <TableCell className="text-xs tabular-nums text-muted-foreground">
                          {formatDateTime(entry.timestamp)}
                        </TableCell>
                        <TableCell className="font-medium text-sm">{entry.action}</TableCell>
                        <TableCell className="text-xs">{entry.modelVersion}</TableCell>
                        <TableCell className="text-xs">{entry.probabilitySet}</TableCell>
                        <TableCell className="text-xs text-muted-foreground max-w-[250px] truncate">
                          {entry.details}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Retrain Confirmation Dialog */}
      <Dialog open={showRetrainDialog} onOpenChange={setShowRetrainDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Trigger Model Retrain</DialogTitle>
            <DialogDescription>
              This will start a full model retrain using the latest data. The process includes:
            </DialogDescription>
          </DialogHeader>
          <ul className="text-sm text-muted-foreground space-y-2 my-4">
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Load latest historical match data
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Recompute team attack/defense strengths
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Fit Poisson/Dixon-Coles model
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Run isotonic calibration
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Validate with out-of-sample Brier scores
            </li>
          </ul>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRetrainDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleRetrain}>
              <Play className="h-4 w-4 mr-2" />
              Start Retrain
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Data Download Dialog */}
      <Dialog open={showDownloadDialog} onOpenChange={setShowDownloadDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5" />
              Download Training Data
            </DialogTitle>
            <DialogDescription>
              Download historical match results and odds from Football-Data.co.uk. 
              This data is free and includes all required fields for model training.
            </DialogDescription>
          </DialogHeader>
          <Alert className="my-4">
            <FileSpreadsheet className="h-4 w-4" />
            <AlertTitle>Data Flow</AlertTitle>
            <AlertDescription className="text-xs">
              Frontend → Your Backend → Football-Data.co.uk (CSV) → Parse & Store → Feature Store
            </AlertDescription>
          </Alert>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm font-medium">
              <span>Available Data Sources</span>
              <Button variant="ghost" size="sm" onClick={selectAll}>
                {selectedSources.length === sources.length ? 'Deselect All' : 'Select All'}
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-2 max-h-[200px] overflow-y-auto">
              {sources.map((source) => (
                <div 
                  key={source.id}
                  className={`flex items-center gap-2 p-2 border rounded cursor-pointer transition-colors ${
                    selectedSources.includes(source.id) ? 'border-primary bg-primary/5' : 'hover:bg-muted/50'
                  }`}
                  onClick={() => toggleSource(source.id)}
                >
                  <Checkbox checked={selectedSources.includes(source.id)} />
                  <span className="text-sm">{source.name}</span>
                </div>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDownloadDialog(false)}>
              Cancel
            </Button>
            <Button onClick={() => { setShowDownloadDialog(false); startDownload(); }} disabled={selectedSources.length === 0}>
              <Download className="h-4 w-4 mr-2" />
              Download {selectedSources.length} Source(s)
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
