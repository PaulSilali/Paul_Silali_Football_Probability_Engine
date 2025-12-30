import { useState, useCallback, useEffect } from 'react';
import {
  Play,
  Loader2,
  CheckCircle,
  AlertCircle,
  Settings,
  TrendingUp,
  Percent,
  Target,
  Clock,
  Database,
  Layers,
  Activity,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Minus
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/services/api';
import type { ModelStatus, TaskStatus } from '@/types';

// Model training types
interface ModelConfig {
  id: string;
  name: string;
  description: string;
  status: 'idle' | 'training' | 'completed' | 'failed';
  progress: number;
  phase: string;
  lastTrained?: string;
  metrics?: {
    brierScore?: number;
    logLoss?: number;
    drawAccuracy?: number;
    rmse?: number;
  };
  parameters: Record<string, number | string | boolean>;
}

// Initial models state - metrics will be loaded from backend
const initialModels: ModelConfig[] = [
  {
    id: 'poisson',
    name: 'Poisson / Dixon-Coles',
    description: 'Team strength model for goal expectations',
    status: 'idle',
    progress: 0,
    phase: '',
    // Metrics and lastTrained will be populated from backend
    parameters: {
      decayRate: 0.0065,
      homeAdvantage: true,
      lowScoreCorrection: true,
    },
  },
  {
    id: 'blending',
    name: 'Odds Blending Model',
    description: 'Learn a global trust weight between model and market',
    status: 'idle',
    progress: 0,
    phase: '',
    // Metrics will be populated after training
    parameters: {
      algorithm: 'Grid Search',
      modelWeight: 0.65,
      marketWeight: 0.35,
      leagueSpecific: false,
      crossValidation: 1,
    },
  },
  {
    id: 'calibration',
    name: 'Calibration Model',
    description: 'Marginal isotonic calibration for probability correctness',
    status: 'idle',
    progress: 0,
    phase: '',
    // Metrics will be populated after training
    parameters: {
      method: 'Isotonic',
      perLeague: false,
      minSamples: 200,
      smoothing: 0.0,
    },
  },
  {
    id: 'draw',
    name: 'Draw Model',
    description: 'Dedicated draw probability model with Poisson, Dixon-Coles, and market blending',
    status: 'idle',
    progress: 0,
    phase: '',
    // Metrics will be populated after training
    parameters: {
      wPoisson: 0.55,
      wDixonColes: 0.30,
      wMarket: 0.15,
      drawFloor: 0.18,
      drawCap: 0.38,
    },
  },
];

const trainingPhases: Record<string, string[]> = {
  poisson: [
    'Loading historical match data...',
    'Computing team attack strengths...',
    'Computing team defense strengths...',
    'Estimating home advantage...',
    'Applying Dixon-Coles low-score correction...',
    'Validating out-of-sample...',
    'Finalizing parameters...',
  ],
  blending: [
    'Loading model probabilities...',
    'Loading market probabilities...',
    'Splitting train/validation...',
    'Training LightGBM ensemble...',
    'Optimizing blend weights...',
    'Cross-validation...',
    'Finalizing model...',
  ],
  calibration: [
    'Loading probability predictions...',
    'Binning by predicted probability...',
    'Fitting isotonic regression...',
    'Per-league calibration...',
    'Validating calibration curves...',
    'Finalizing calibrator...',
  ],
  draw: [
    'Loading draw predictions...',
    'Computing Poisson draw probabilities...',
    'Applying Dixon-Coles adjustments...',
    'Blending with market signals...',
    'Validating draw bounds...',
    'Storing draw components...',
    'Finalizing draw model...',
  ],
};

// Training history is now loaded from backend - see loadTrainingHistory()

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatDateTime(dateString: string) {
  return new Date(dateString).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function MLTraining() {
  const [models, setModels] = useState<ModelConfig[]>(initialModels);
  const [isTrainingPipeline, setIsTrainingPipeline] = useState(false);
  const [expandedParams, setExpandedParams] = useState<string[]>([]);
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [trainingTasks, setTrainingTasks] = useState<Map<string, NodeJS.Timeout>>(new Map());
  const [trainingHistory, setTrainingHistory] = useState<Array<{
    id: string;
    modelId: string | null;
    runType: string;
    status: string;
    startedAt: string | null;
    completedAt: string | null;
    matchCount: number | null;
    dateFrom: string | null;
    dateTo: string | null;
    brierScore: number | null;
    logLoss: number | null;
    validationAccuracy: number | null;
    errorMessage: string | null;
    duration: number | null;
  }>>([]);
  const [leagues, setLeagues] = useState<Array<{code: string; name: string; country: string; tier: number}>>([]);
  const [selectedLeagues, setSelectedLeagues] = useState<string[]>([]);
  const [selectedSeasons, setSelectedSeasons] = useState<string[]>([]);
  const [showConfig, setShowConfig] = useState(false);
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const { toast } = useToast();

  const toggleParams = (modelId: string) => {
    setExpandedParams(prev =>
      prev.includes(modelId) ? prev.filter(id => id !== modelId) : [...prev, modelId]
    );
  };

  // Poll task status for training progress
  const pollTaskStatus = useCallback(async (taskId: string, modelId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await apiClient.getTaskStatus(taskId);
        if (response.success && response.data) {
          const task: TaskStatus = response.data;
          
          // Update model progress
      setModels(prev => prev.map(m =>
        m.id === modelId
              ? {
                  ...m,
                  progress: task.progress || 0,
                  phase: task.phase || 'Training...',
                  status: task.status === 'running' ? 'training' as const :
                          task.status === 'completed' ? 'completed' as const :
                          task.status === 'failed' ? 'failed' as const : 'idle' as const
                }
          : m
      ));

          // Handle completion
          if (task.status === 'completed' && task.result) {
            clearInterval(pollInterval);
            setTrainingTasks(prev => {
              const next = new Map(prev);
              next.delete(taskId);
              return next;
            });
            
            // Update model with completion status
            setModels(prev => prev.map(m =>
              m.id === modelId
                ? {
                    ...m,
                    status: 'completed' as const,
                    progress: 100,
                    phase: 'Complete',
                    lastTrained: new Date().toISOString(),
                    // Only set metrics if they exist in result
                    metrics: task.result?.metrics ? {
                      brierScore: task.result.metrics.brierScore,
                      logLoss: task.result.metrics.logLoss,
                      drawAccuracy: task.result.metrics.drawAccuracy,
                      rmse: task.result.metrics.rmse,
                    } : undefined,
                  }
                : m
            ));
            
            toast({
              title: 'Training Complete',
              description: `${models.find(m => m.id === modelId)?.name} trained successfully.`,
            });
            
            // Refresh model status and training history from backend
            loadModelStatus();
            loadTrainingHistory();
          }

          // Handle failure
          if (task.status === 'failed') {
            clearInterval(pollInterval);
            setTrainingTasks(prev => {
              const next = new Map(prev);
              next.delete(taskId);
              return next;
            });
            
            setModels(prev => prev.map(m =>
              m.id === modelId
                ? { ...m, status: 'failed' as const, phase: task.error || 'Failed' }
                : m
            ));
            
            toast({
              title: 'Training Failed',
              description: task.error || 'Model training failed. Please check logs.',
              variant: 'destructive',
            });
          }
        }
      } catch (error: any) {
        console.error('Error polling task status:', error);
        // Continue polling on error (might be temporary)
      }
    }, 2000); // Poll every 2 seconds

    // Store interval for cleanup
    setTrainingTasks(prev => {
      const next = new Map(prev);
      next.set(taskId, pollInterval);
      return next;
    });
  }, [models, toast]);

  // Load model status from backend
  const loadModelStatus = useCallback(async () => {
    try {
      const response = await apiClient.getModelStatus();
      if (response.success && response.data) {
        setModelStatus(response.data);
        // Update models with real metrics from backend (only if model exists)
        if (response.data.status !== 'no_model') {
          setModels(prev => prev.map(m => {
            if (m.id === 'poisson' && response.data) {
              return {
                ...m,
                metrics: response.data.brierScore !== null || response.data.logLoss !== null ? {
                  brierScore: response.data.brierScore || undefined,
                  logLoss: response.data.logLoss || undefined,
                  drawAccuracy: response.data.drawAccuracy || undefined,
                } : undefined,
                lastTrained: response.data.trainedAt || undefined,
              };
            }
            return m;
          }));
        }
      }
    } catch (error) {
      console.error('Error loading model status:', error);
    }
  }, []);

  // Load model status, training history, and leagues on mount
  useEffect(() => {
    loadModelStatus();
    loadTrainingHistory();
    loadLeagues();
  }, []);

  const loadTrainingHistory = useCallback(async () => {
    try {
      const response = await apiClient.getTrainingHistory(50);
      if (response.success && response.data) {
        setTrainingHistory(response.data);
      }
    } catch (error) {
      console.error('Error loading training history:', error);
    }
  }, []);

  const loadLeagues = useCallback(async () => {
    try {
      const response = await apiClient.getLeagues();
      if (response.success && response.data) {
        setLeagues(response.data);
      }
    } catch (error) {
      console.error('Error loading leagues:', error);
    }
  }, []);

  // Cleanup polling intervals on unmount
  useEffect(() => {
    return () => {
      trainingTasks.forEach(interval => clearInterval(interval));
    };
  }, [trainingTasks]);

  const trainModel = useCallback(async (modelId: string) => {
    const phases = trainingPhases[modelId] || ['Training...'];
    
    // Set initial training state
    setModels(prev => prev.map(m =>
      m.id === modelId ? { ...m, status: 'training' as const, progress: 0, phase: phases[0] } : m
    ));

    try {
      // Call backend API with configuration
      const response = await apiClient.trainModel({
        modelType: modelId === 'poisson' ? 'poisson' :
                   modelId === 'blending' ? 'blending' :
                   modelId === 'calibration' ? 'calibration' :
                   modelId === 'draw' ? 'draw' : undefined,
        leagues: selectedLeagues.length > 0 ? selectedLeagues : undefined,
        seasons: selectedSeasons.length > 0 ? selectedSeasons : undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
      });

      if (response.success && response.data) {
        const taskId = response.data.taskId;
        toast({
          title: 'Training Started',
          description: `Training task queued. Task ID: ${taskId}`,
        });
        
        // Start polling for progress
        pollTaskStatus(taskId, modelId);
      } else {
        throw new Error('Failed to start training');
      }
    } catch (error: any) {
      console.error('Error starting training:', error);
      setModels(prev => prev.map(m =>
        m.id === modelId ? { ...m, status: 'failed' as const, phase: 'Failed to start' } : m
      ));
      toast({
        title: 'Training Failed',
        description: error?.message || 'Failed to start model training. Please try again.',
        variant: 'destructive',
      });
    }
  }, [pollTaskStatus, toast]);

  const trainFullPipeline = useCallback(async () => {
    setIsTrainingPipeline(true);
    
    try {
      // Call backend API for full pipeline training with configuration
      const response = await apiClient.trainModel({
        modelType: 'full',
        leagues: selectedLeagues.length > 0 ? selectedLeagues : undefined,
        seasons: selectedSeasons.length > 0 ? selectedSeasons : undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
      });

      if (response.success && response.data) {
        const taskId = response.data.taskId;
        toast({
          title: 'Pipeline Training Started',
          description: `Full pipeline training queued. Task ID: ${taskId}`,
        });
        
        // Set all models to training state
        setModels(prev => prev.map(m => ({
          ...m,
          status: 'training' as const,
          progress: 0,
          phase: 'Queued...',
        })));
        
        // Poll for pipeline progress (backend should handle sequential training)
        const pollInterval = setInterval(async () => {
          try {
            const taskResponse = await apiClient.getTaskStatus(taskId);
            if (taskResponse.success && taskResponse.data) {
              const task: TaskStatus = taskResponse.data;
              
              // Update all models with overall progress
              setModels(prev => prev.map(m => ({
                ...m,
                progress: task.progress || 0,
                phase: task.phase || 'Training pipeline...',
                status: task.status === 'running' ? 'training' as const :
                        task.status === 'completed' ? 'completed' as const :
                        task.status === 'failed' ? 'failed' as const : 'idle' as const
              })));

              if (task.status === 'completed') {
                clearInterval(pollInterval);
                setIsTrainingPipeline(false);
                
                // Update all models to completed state
                setModels(prev => prev.map(m => ({
                  ...m,
                  status: 'completed' as const,
                  progress: 100,
                  phase: 'Complete',
                  lastTrained: new Date().toISOString(),
                  // Metrics will be loaded from backend via loadModelStatus
                })));
                
                toast({
                  title: 'Pipeline Complete',
                  description: 'All models trained successfully. New version ready for activation.',
                });
                
                // Refresh all data from backend
                loadModelStatus();
                loadTrainingHistory();
              }

              if (task.status === 'failed') {
                clearInterval(pollInterval);
                setIsTrainingPipeline(false);
                setModels(prev => prev.map(m => ({
                  ...m,
                  status: 'failed' as const,
                  phase: task.error || 'Failed',
                })));
                
                toast({
                  title: 'Pipeline Failed',
                  description: task.error || 'Pipeline training failed. Please check logs.',
                  variant: 'destructive',
                });
              }
            }
          } catch (error) {
            console.error('Error polling pipeline status:', error);
        }
        }, 2000);
      } else {
        throw new Error('Failed to start pipeline training');
      }
    } catch (error: any) {
      console.error('Error starting pipeline training:', error);
      setIsTrainingPipeline(false);
      toast({
        title: 'Pipeline Failed',
        description: error?.message || 'Failed to start pipeline training. Please try again.',
        variant: 'destructive',
      });
    }
  }, [loadModelStatus, toast]);

  const isAnyTraining = models.some(m => m.status === 'training');

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">ML Training</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Train and configure prediction models
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setShowConfig(!showConfig)}
          >
            <Settings className="h-4 w-4 mr-2" />
            {showConfig ? 'Hide' : 'Show'} Configuration
          </Button>
          <Button
            onClick={trainFullPipeline}
            disabled={isTrainingPipeline || isAnyTraining}
          >
            {isTrainingPipeline ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Training Pipeline...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Train Full Pipeline
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Training Configuration */}
      {showConfig && (
        <Card className="border-primary/20 bg-gradient-to-br from-background to-background/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5 text-primary" />
              Training Configuration
            </CardTitle>
            <CardDescription>
              Configure which leagues, seasons, and date range to use for training
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* League Selection */}
            <div className="space-y-3">
              <Label className="text-base font-semibold">Select Leagues</Label>
              <p className="text-sm text-muted-foreground">
                Leave empty to train on all leagues. Selected: {selectedLeagues.length} league(s)
              </p>
              <ScrollArea className="h-[200px] border rounded-lg p-4">
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  {leagues.map((league) => (
                    <div key={league.code} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id={`league-${league.code}`}
                        checked={selectedLeagues.includes(league.code)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedLeagues([...selectedLeagues, league.code]);
                          } else {
                            setSelectedLeagues(selectedLeagues.filter(l => l !== league.code));
                          }
                        }}
                        className="h-4 w-4 rounded border-gray-300"
                      />
                      <Label htmlFor={`league-${league.code}`} className="text-sm cursor-pointer">
                        {league.code} - {league.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </ScrollArea>
              {selectedLeagues.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedLeagues([])}
                  className="text-destructive hover:text-destructive"
                >
                  Clear Selection
                </Button>
              )}
            </div>

            {/* Season Selection */}
            <div className="space-y-3">
              <Label className="text-base font-semibold">Select Seasons</Label>
              <p className="text-sm text-muted-foreground">
                Leave empty to train on all seasons. Format: YYYY-YY (e.g., 2324 for 2023-24)
              </p>
              <div className="flex flex-wrap gap-2">
                {['2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617'].map((season) => (
                  <div key={season} className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id={`season-${season}`}
                      checked={selectedSeasons.includes(season)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedSeasons([...selectedSeasons, season]);
                        } else {
                          setSelectedSeasons(selectedSeasons.filter(s => s !== season));
                        }
                      }}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                    <Label htmlFor={`season-${season}`} className="text-sm cursor-pointer">
                      {season}
                    </Label>
                  </div>
                ))}
              </div>
              {selectedSeasons.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedSeasons([])}
                  className="text-destructive hover:text-destructive"
                >
                  Clear Selection
                </Button>
              )}
            </div>

            {/* Date Range */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="dateFrom">Date From (Optional)</Label>
                <Input
                  id="dateFrom"
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  placeholder="YYYY-MM-DD"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="dateTo">Date To (Optional)</Label>
                <Input
                  id="dateTo"
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  placeholder="YYYY-MM-DD"
                />
              </div>
            </div>

            {/* Summary */}
            <div className="p-4 bg-muted/50 rounded-lg">
              <p className="text-sm font-medium mb-2">Training Configuration Summary:</p>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Leagues: {selectedLeagues.length > 0 ? selectedLeagues.join(', ') : 'All leagues'}</li>
                <li>• Seasons: {selectedSeasons.length > 0 ? selectedSeasons.join(', ') : 'All seasons'}</li>
                <li>• Date Range: {dateFrom && dateTo ? `${dateFrom} to ${dateTo}` : dateFrom ? `From ${dateFrom}` : dateTo ? `Until ${dateTo}` : 'No date filter'}</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      )}

      {isTrainingPipeline && (
        <Alert>
          <Loader2 className="h-4 w-4 animate-spin" />
          <AlertTitle>Full Pipeline Training</AlertTitle>
          <AlertDescription>
            Training Poisson → Odds Blending → Calibration in sequence
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="models">
        <TabsList>
          <TabsTrigger value="models" className="gap-2">
            <Layers className="h-4 w-4" />
            Model Training
          </TabsTrigger>
          <TabsTrigger value="history" className="gap-2">
            <Clock className="h-4 w-4" />
            Training History
          </TabsTrigger>
        </TabsList>

        {/* Models Tab */}
        <TabsContent value="models" className="space-y-4">
          {models.map((model) => (
            <Card key={model.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {model.id === 'poisson' && <TrendingUp className="h-5 w-5 text-primary" />}
                    {model.id === 'blending' && <Percent className="h-5 w-5 text-primary" />}
                    {model.id === 'calibration' && <Target className="h-5 w-5 text-primary" />}
                    {model.id === 'draw' && <Minus className="h-5 w-5 text-primary" />}
                    <div>
                      <CardTitle className="text-lg">{model.name}</CardTitle>
                      <CardDescription>{model.description}</CardDescription>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {model.lastTrained && (
                      <Badge variant="outline" className="text-xs">
                        Last: {formatDateTime(model.lastTrained)}
                      </Badge>
                    )}
                    <Button
                      size="sm"
                      onClick={() => trainModel(model.id)}
                      disabled={model.status === 'training' || isTrainingPipeline}
                    >
                      {model.status === 'training' ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Training...
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4 mr-2" />
                          Train
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Training Progress */}
                {model.status === 'training' && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{model.phase}</span>
                      <span className="tabular-nums font-medium">{Math.round(model.progress)}%</span>
                    </div>
                    <Progress value={model.progress} className="h-2" />
                  </div>
                )}

                {/* Metrics */}
                {model.metrics && model.status !== 'training' && (
                  <div className="grid grid-cols-4 gap-4">
                    {model.metrics.brierScore !== undefined && (
                      <div className="text-center p-3 bg-muted/50 rounded-lg">
                        <p className="text-xs text-muted-foreground">Brier Score</p>
                        <p className="text-lg font-semibold tabular-nums">{model.metrics.brierScore.toFixed(3)}</p>
                      </div>
                    )}
                    {model.metrics.logLoss !== undefined && (
                      <div className="text-center p-3 bg-muted/50 rounded-lg">
                        <p className="text-xs text-muted-foreground">Log Loss</p>
                        <p className="text-lg font-semibold tabular-nums">{model.metrics.logLoss.toFixed(3)}</p>
                      </div>
                    )}
                    {model.metrics.drawAccuracy !== undefined && (
                      <div className="text-center p-3 bg-muted/50 rounded-lg">
                        <p className="text-xs text-muted-foreground">Draw Accuracy</p>
                        <p className="text-lg font-semibold tabular-nums">{model.metrics.drawAccuracy.toFixed(1)}%</p>
                      </div>
                    )}
                    {model.metrics.rmse !== undefined && (
                      <div className="text-center p-3 bg-muted/50 rounded-lg">
                        <p className="text-xs text-muted-foreground">RMSE</p>
                        <p className="text-lg font-semibold tabular-nums">{model.metrics.rmse.toFixed(3)}</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Parameters */}
                <Collapsible open={expandedParams.includes(model.id)}>
                  <CollapsibleTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleParams(model.id)}
                      className="w-full justify-between"
                    >
                      <span className="flex items-center gap-2">
                        <Settings className="h-4 w-4" />
                        Training Parameters
                      </span>
                      {expandedParams.includes(model.id) ? (
                        <ChevronUp className="h-4 w-4" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )}
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="pt-4">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 p-4 bg-muted/30 rounded-lg">
                      {Object.entries(model.parameters).map(([key, value]) => (
                        <div key={key} className="space-y-1">
                          <Label className="text-xs capitalize">{key.replace(/([A-Z])/g, ' $1')}</Label>
                          {typeof value === 'boolean' ? (
                            <div className="flex items-center gap-2">
                              <Switch checked={value} disabled />
                              <span className="text-sm">{value ? 'Enabled' : 'Disabled'}</span>
                            </div>
                          ) : typeof value === 'number' ? (
                            <Input type="number" value={value} disabled className="h-8" />
                          ) : (
                            <Input value={String(value)} disabled className="h-8" />
                          )}
                        </div>
                      ))}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        {/* Training History Tab */}
        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Training History
              </CardTitle>
              <CardDescription>
                    Past training runs and performance changes from database
              </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={loadTrainingHistory}
                >
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {trainingHistory.length === 0 ? (
                <div className="h-[400px] flex items-center justify-center text-muted-foreground">
                  <div className="text-center">
                    <Clock className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No training history found.</p>
                    <p className="text-sm mt-2">Training runs will appear here after training completes.</p>
                  </div>
                </div>
              ) : (
              <ScrollArea className="h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                        <TableHead>Run Type</TableHead>
                        <TableHead>Matches</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead>Status</TableHead>
                        <TableHead className="text-right">Brier Score</TableHead>
                        <TableHead className="text-right">Log Loss</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {trainingHistory.map((run) => (
                      <TableRow key={run.id}>
                          <TableCell className="text-sm">
                            {run.startedAt ? formatDate(run.startedAt) : '—'}
                          </TableCell>
                          <TableCell className="font-medium capitalize">{run.runType}</TableCell>
                          <TableCell className="text-sm text-muted-foreground tabular-nums">
                            {run.matchCount?.toLocaleString() || '—'}
                          </TableCell>
                        <TableCell className="text-sm text-muted-foreground tabular-nums">
                            {run.duration ? `${Math.round(run.duration)}m` : '—'}
                        </TableCell>
                        <TableCell>
                            {run.status === 'active' ? (
                            <Badge variant="secondary" className="bg-green-500/10 text-green-600">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Active
                            </Badge>
                            ) : run.status === 'archived' ? (
                            <Badge variant="outline" className="bg-gray-500/10 text-gray-600">
                              <Clock className="h-3 w-3 mr-1" />
                              Archived
                            </Badge>
                            ) : run.status === 'failed' || run.trainingStatus === 'failed' ? (
                            <Badge variant="destructive">
                              <AlertCircle className="h-3 w-3 mr-1" />
                              Failed
                            </Badge>
                            ) : run.status === 'completed' || run.trainingStatus === 'completed' ? (
                            <Badge variant="secondary" className="bg-blue-500/10 text-blue-600">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Completed
                            </Badge>
                            ) : (
                              <Badge variant="outline">{run.status || run.trainingStatus || 'Unknown'}</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                            {run.brierScore !== null && run.brierScore !== undefined ? (
                              <span className="font-medium">{run.brierScore.toFixed(3)}</span>
                            ) : '—'}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {run.logLoss !== null && run.logLoss !== undefined ? (
                              <span className="font-medium">{run.logLoss.toFixed(3)}</span>
                          ) : '—'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
              )}
            </CardContent>
          </Card>

          <Alert>
            <Activity className="h-4 w-4" />
            <AlertTitle>Training Schedule</AlertTitle>
            <AlertDescription>
              Recommended: Weekly incremental updates, monthly full pipeline retrain.
              Models are versioned automatically after each successful training run.
            </AlertDescription>
          </Alert>
        </TabsContent>
      </Tabs>
    </div>
  );
}
