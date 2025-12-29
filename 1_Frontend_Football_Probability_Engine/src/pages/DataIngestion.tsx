import { useState, useCallback } from 'react';
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
  X
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

const initialDataSources: DataSource[] = [
  { id: '1', name: 'Premier League', url: 'football-data.co.uk/englandm.php', leagues: ['E0'], seasons: '2018-2024', status: 'idle', progress: 0, lastUpdated: '2024-12-20' },
  { id: '2', name: 'Championship', url: 'football-data.co.uk/englandm.php', leagues: ['E1'], seasons: '2018-2024', status: 'idle', progress: 0, lastUpdated: '2024-12-20' },
  { id: '3', name: 'La Liga', url: 'football-data.co.uk/spainm.php', leagues: ['SP1'], seasons: '2018-2024', status: 'idle', progress: 0, lastUpdated: '2024-12-18' },
  { id: '4', name: 'Bundesliga', url: 'football-data.co.uk/germanym.php', leagues: ['D1'], seasons: '2018-2024', status: 'idle', progress: 0, lastUpdated: '2024-12-19' },
  { id: '5', name: 'Serie A', url: 'football-data.co.uk/italym.php', leagues: ['I1'], seasons: '2018-2024', status: 'idle', progress: 0, lastUpdated: '2024-12-17' },
  { id: '6', name: 'Ligue 1', url: 'football-data.co.uk/francem.php', leagues: ['F1'], seasons: '2018-2024', status: 'idle', progress: 0, lastUpdated: '2024-12-18' },
  { id: '7', name: 'League One', url: 'football-data.co.uk/englandm.php', leagues: ['E2'], seasons: '2018-2024', status: 'idle', progress: 0, lastUpdated: '2024-12-15' },
  { id: '8', name: 'League Two', url: 'football-data.co.uk/englandm.php', leagues: ['E3'], seasons: '2018-2024', status: 'idle', progress: 0, lastUpdated: '2024-12-15' },
  { id: '9', name: 'Eredivisie', url: 'football-data.co.uk/netherlandsm.php', leagues: ['N1'], seasons: '2018-2024', status: 'idle', progress: 0 },
  { id: '10', name: 'Primeira Liga', url: 'football-data.co.uk/portugalm.php', leagues: ['P1'], seasons: '2018-2024', status: 'idle', progress: 0 },
];

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
function useDataDownload() {
  const [sources, setSources] = useState<DataSource[]>(initialDataSources);
  const [isDownloading, setIsDownloading] = useState(false);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [downloadBatches, setDownloadBatches] = useState<DownloadBatch[]>([]);
  const [batchCounter, setBatchCounter] = useState(1000);
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

    setSources(prev => prev.map(s =>
      selectedSources.includes(s.id)
        ? { ...s, status: 'idle' as const, progress: 0 }
        : s
    ));

    let currentIndex = 0;
    const toDownload = selectedSources.slice();
    let batchRecords = 0;
    const downloadedSourceNames: string[] = [];

    const processNext = () => {
      if (currentIndex >= toDownload.length) {
        setIsDownloading(false);
        
        // Create batch record
        const newBatch: DownloadBatch = {
          id: `batch-${Date.now()}`,
          batchNumber: batchCounter,
          timestamp: new Date().toISOString(),
          sources: downloadedSourceNames,
          totalRecords: batchRecords,
          status: 'completed',
        };
        setDownloadBatches(prev => [newBatch, ...prev]);
        setBatchCounter(prev => prev + 1);
        
        toast({
          title: 'Download Complete',
          description: `Batch #${batchCounter}: Downloaded ${toDownload.length} sources (${batchRecords.toLocaleString()} records)`,
        });
        return;
      }

      const sourceId = toDownload[currentIndex];
      const sourceName = sources.find(s => s.id === sourceId)?.name || 'Unknown';
      
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
          batchRecords += recordCount;
          downloadedSourceNames.push(sourceName);
          
          setSources(prev => prev.map(s =>
            s.id === sourceId
              ? { ...s, status: 'completed' as const, progress: 100, recordCount, lastUpdated: new Date().toISOString().split('T')[0] }
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
  }, [selectedSources, toast, batchCounter, sources]);

  return { sources, isDownloading, selectedSources, toggleSource, selectAll, startDownload, downloadBatches };
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export default function DataIngestion() {
  const { sources, isDownloading, selectedSources, toggleSource, selectAll, startDownload, downloadBatches } = useDataDownload();
  const [jackpotResults, setJackpotResults] = useState<JackpotResult[]>(mockJackpotResults);
  const [manualInput, setManualInput] = useState('');
  const [selectedSeason, setSelectedSeason] = useState('2024-25');
  const [previewBatch, setPreviewBatch] = useState<DownloadBatch | null>(null);
  const [previewData, setPreviewData] = useState<ReturnType<typeof generateMockDataset>>([]);
  const { toast } = useToast();

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
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Data Ingestion</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Import historical data and previous jackpot results
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="secondary" className="text-xs">
            <Database className="h-3 w-3 mr-1" />
            {totalRecords.toLocaleString()} records
          </Badge>
          <Badge variant="outline" className="text-xs">
            {sourcesWithData}/{sources.length} sources
          </Badge>
        </div>
      </div>

      <Tabs defaultValue="football-data">
        <TabsList>
          <TabsTrigger value="football-data" className="gap-2">
            <Globe className="h-4 w-4" />
            Football-Data.co.uk
          </TabsTrigger>
          <TabsTrigger value="api-football" className="gap-2">
            <FileSpreadsheet className="h-4 w-4" />
            API-Football
          </TabsTrigger>
          <TabsTrigger value="jackpot-results" className="gap-2">
            <Trophy className="h-4 w-4" />
            Jackpot Results
          </TabsTrigger>
        </TabsList>

        {/* Football-Data.co.uk Tab */}
        <TabsContent value="football-data" className="space-y-4">
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
                  <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                    <SelectTrigger className="w-[120px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="2024-25">2024-25</SelectItem>
                      <SelectItem value="2023-24">2023-24</SelectItem>
                      <SelectItem value="2022-23">2022-23</SelectItem>
                      <SelectItem value="2021-22">2021-22</SelectItem>
                      <SelectItem value="2020-21">2020-21</SelectItem>
                      <SelectItem value="all">All Seasons</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    onClick={startDownload}
                    disabled={isDownloading || selectedSources.length === 0}
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
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <Button variant="ghost" size="sm" onClick={selectAll}>
                  <Checkbox
                    checked={selectedSources.length === sources.length}
                    className="mr-2"
                  />
                  {selectedSources.length === sources.length ? 'Deselect All' : 'Select All'}
                </Button>
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
                            <div className="flex items-center gap-2">
                              <Loader2 className="h-4 w-4 animate-spin text-primary" />
                              <Progress value={source.progress} className="w-16 h-2" />
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

          {/* Download Batch History */}
          {downloadBatches.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileUp className="h-5 w-5" />
                  Downloaded Data Batches
                </CardTitle>
                <CardDescription>
                  History of completed data downloads
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[200px]">
                  <div className="space-y-3">
                    {downloadBatches.map((batch) => (
                      <div
                        key={batch.id}
                        className="flex items-center justify-between p-3 rounded-lg border bg-muted/30"
                      >
                        <div className="flex items-center gap-4">
                          <div className="flex flex-col">
                            <span className="font-mono font-semibold text-primary">
                              Batch #{batch.batchNumber}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {new Date(batch.timestamp).toLocaleString()}
                            </span>
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {batch.sources.slice(0, 3).map((source, idx) => (
                              <Badge key={idx} variant="outline" className="text-xs">
                                {source}
                              </Badge>
                            ))}
                            {batch.sources.length > 3 && (
                              <Badge variant="secondary" className="text-xs">
                                +{batch.sources.length - 3} more
                              </Badge>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-medium tabular-nums">
                            {batch.totalRecords.toLocaleString()} records
                          </span>
                          <Badge className="bg-green-500/10 text-green-600">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            {batch.status}
                          </Badge>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handlePreviewBatch(batch)}
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            Preview
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          )}
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
