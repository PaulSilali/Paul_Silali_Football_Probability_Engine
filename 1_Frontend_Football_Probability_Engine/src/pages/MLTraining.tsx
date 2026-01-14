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
import { PageLayout } from '@/components/layouts/PageLayout';
import { ModernCard } from '@/components/ui/modern-card';
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

function formatDateTime(dateInput: string | Date | object | null | undefined) {
  try {
    // Handle null/undefined
    if (!dateInput) {
      return 'Never';
    }
    
    // If it's already a Date object, use it
    let date: Date;
    if (dateInput instanceof Date) {
      date = dateInput;
    } else if (typeof dateInput === 'string') {
      date = new Date(dateInput);
    } else if (typeof dateInput === 'object') {
      // Handle object with date properties (e.g., {year, month, day} or ISO string property)
      if ('toISOString' in dateInput && typeof dateInput.toISOString === 'function') {
        date = dateInput as Date;
      } else if ('$date' in dateInput) {
        // MongoDB date format
        date = new Date((dateInput as any).$date);
      } else {
        // Try to extract ISO string from object
        const isoString = (dateInput as any).toString?.() || (dateInput as any).toISOString?.() || JSON.stringify(dateInput);
        date = new Date(isoString);
      }
    } else {
      console.warn('[MLTraining] Unexpected date format:', typeof dateInput, dateInput);
      return 'Invalid Date';
    }
    
    if (isNaN(date.getTime())) {
      console.warn('[MLTraining] Invalid date:', dateInput);
      return 'Invalid Date';
    }
    
    const formatted = date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
    
    // Only log in debug mode (remove console.log to reduce noise)
    // console.log('[MLTraining] Formatting timestamp:', {
    //   input: dateInput,
    //   parsed: date.toISOString(),
    //   formatted: formatted,
    //   localTime: date.toLocaleString()
    // });
    
    return formatted;
  } catch (error) {
    console.error('[MLTraining] Error formatting date:', dateInput, error);
    return 'Invalid Date';
  }
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
  // Window configuration (SP-FX Recommended)
  const [baseModelWindowYears, setBaseModelWindowYears] = useState<number>(4.0);
  const [drawModelWindowYears, setDrawModelWindowYears] = useState<number>(2.0);
  const [oddsCalibrationWindowYears, setOddsCalibrationWindowYears] = useState<number>(1.5);
  const [excludePreCovid, setExcludePreCovid] = useState<boolean>(false);
  const { toast } = useToast();

  const toggleParams = (modelId: string) => {
    setExpandedParams(prev =>
      prev.includes(modelId) ? prev.filter(id => id !== modelId) : [...prev, modelId]
    );
  };

  // Load model status from backend
  const loadModelStatus = useCallback(async () => {
    try {
      console.log('[MLTraining] Loading model status from backend...');
      const response = await apiClient.getModelStatus();
      console.log('[MLTraining] Model status response received:', {
        success: response.success,
        hasData: !!response.data,
        timestamp: new Date().toISOString()
      });
      
      if (response.success && response.data) {
        setModelStatus(response.data);
        // Update models with real metrics from backend (only if model exists)
        if (response.data.status !== 'no_model') {
          setModels(prev => prev.map(m => {
            // Update Poisson model with Poisson-specific data
            if (m.id === 'poisson' && response.data.poisson) {
              const trainedAt = response.data.poisson.trainedAt;
              // Only log if timestamp actually changed or is new
              if (trainedAt && trainedAt !== m.lastTrained) {
                console.log('[MLTraining] Poisson model timestamp updated:', {
                  raw: trainedAt,
                  formatted: formatDateTime(trainedAt),
                  previous: m.lastTrained
                });
              }
              
              return {
                ...m,
                metrics: response.data.poisson.brierScore !== null || response.data.poisson.logLoss !== null ? {
                  brierScore: response.data.poisson.brierScore || undefined,
                  logLoss: response.data.poisson.logLoss || undefined,
                  drawAccuracy: response.data.poisson.drawAccuracy || undefined,
                } : undefined,
                lastTrained: trainedAt ? formatDateTime(trainedAt) : undefined,
              };
            }
            // Update Blending model with Blending-specific data
            if (m.id === 'blending' && response.data.blending) {
              const trainedAt = response.data.blending.trainedAt;
              // Only log if timestamp actually changed or is new
              if (trainedAt && trainedAt !== m.lastTrained) {
                console.log('[MLTraining] Blending model timestamp received:', {
                  raw: trainedAt,
                  formatted: formatDateTime(trainedAt),
                  previous: m.lastTrained,
                  changed: true
                });
              }
              
              return {
                ...m,
                metrics: response.data.blending.brierScore !== null || response.data.blending.logLoss !== null ? {
                  brierScore: response.data.blending.brierScore || undefined,
                  logLoss: response.data.blending.logLoss || undefined,
                } : undefined,
                lastTrained: trainedAt ? formatDateTime(trainedAt) : undefined,
              };
            }
            // Update Calibration model with Calibration-specific data
            if (m.id === 'calibration' && response.data.calibration) {
              const trainedAt = response.data.calibration.trainedAt;
              // Only log if timestamp actually changed or is new
              if (trainedAt && trainedAt !== m.lastTrained) {
                console.log('[MLTraining] Calibration model timestamp received:', {
                  raw: trainedAt,
                  formatted: formatDateTime(trainedAt),
                  previous: m.lastTrained,
                  changed: true
                });
              }
              
              return {
                ...m,
                metrics: response.data.calibration.brierScore !== null || response.data.calibration.logLoss !== null ? {
                  brierScore: response.data.calibration.brierScore || undefined,
                  logLoss: response.data.calibration.logLoss || undefined,
                } : undefined,
                lastTrained: trainedAt ? formatDateTime(trainedAt) : undefined,
              };
            }
            return m;
          }));
          
          console.log('[MLTraining] Model status updated successfully');
        }
      } else {
        console.warn('[MLTraining] No model data in response:', response);
      }
    } catch (error) {
      console.error('[MLTraining] Error loading model status:', error);
    }
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

  // Poll task status for training progress
  const pollTaskStatus = useCallback(async (taskId: string, modelId: string) => {
    let isCompleted = false;
    
    const pollInterval = setInterval(async () => {
      // Stop polling if already completed
      if (isCompleted) {
        clearInterval(pollInterval);
        return;
      }
      
      try {
        const response = await apiClient.getTaskStatus(taskId);
        if (response.success && response.data) {
          const task: TaskStatus = response.data;
          
          console.log(`[MLTraining] Polling task ${taskId}: status=${task.status}, progress=${task.progress}, phase=${task.phase}`);
          
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

          // Handle completion - check status first, result is optional
          if (task.status === 'completed') {
            console.log(`[MLTraining] Task ${taskId} completed, stopping polling`);
            isCompleted = true;
            clearInterval(pollInterval);
            setTrainingTasks(prev => {
              const next = new Map(prev);
              next.delete(taskId);
              return next;
            });
            
            // Get model name from current state (use functional update to avoid stale closure)
            let modelName = 'Model';
            
            // First, update progress to 100% with animation
            setModels(prev => {
              const found = prev.find(m => m.id === modelId);
              if (found) {
                modelName = found.name;
              }
              return prev.map(m =>
                m.id === modelId
                  ? {
                      ...m,
                      status: 'completed' as const,
                      progress: 100, // Ensure 100% is set immediately
                      phase: task.phase || 'Complete',
                      // Only set metrics if they exist in result
                      metrics: task.result?.metrics ? {
                        brierScore: task.result.metrics.brierScore,
                        logLoss: task.result.metrics.logLoss,
                        drawAccuracy: task.result.metrics.drawAccuracy,
                        rmse: task.result.metrics.rmse,
                      } : m.metrics, // Keep existing metrics if new ones aren't available
                    }
                  : m
              );
            });
            
            // Force a re-render by updating state again after a brief delay
            setTimeout(() => {
              setModels(prev => prev.map(m => 
                m.id === modelId ? { ...m, progress: 100 } : m
              ));
            }, 100);
            
            toast({
              title: 'Training Complete',
              description: `${modelName} trained successfully.`,
            });
            
            // Refresh model status and training history from backend (this will update lastTrained with actual timestamp)
            console.log('[MLTraining] Training completed, refreshing model status...');
            console.log('[MLTraining] Current time:', new Date().toISOString());
            
            // Refresh data after a short delay to ensure UI updates first
            setTimeout(async () => {
              await loadModelStatus();
              await loadTrainingHistory();
              console.log('[MLTraining] Model status refresh complete');
            }, 500);
          }

          // Handle failure
          if (task.status === 'failed') {
            console.log(`[MLTraining] Task ${taskId} failed, stopping polling`);
            isCompleted = true;
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
        
        // If 404, task doesn't exist - stop polling
        const statusCode = error?.response?.status || error?.status || (error?.message?.includes('404') ? 404 : null);
        if (statusCode === 404) {
          console.log(`[MLTraining] Task ${taskId} not found (404), stopping polling`);
          isCompleted = true;
          clearInterval(pollInterval);
          setTrainingTasks(prev => {
            const next = new Map(prev);
            next.delete(taskId);
            return next;
          });
          
          // Reset model status
          setModels(prev => prev.map(m =>
            m.id === modelId
              ? { ...m, status: 'idle' as const, progress: 0, phase: 'Task not found' }
              : m
          ));
          return;
        }
        
        // For other errors, continue polling (might be temporary network issue)
      }
    }, 2000); // Poll every 2 seconds

    // Store interval for cleanup
    setTrainingTasks(prev => {
      const next = new Map(prev);
      next.set(taskId, pollInterval);
      return next;
    });
  }, [toast, loadModelStatus, loadTrainingHistory]);

  // Load model status, training history, and leagues on mount
  useEffect(() => {
    loadModelStatus();
    loadTrainingHistory();
    loadLeagues();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Intentionally empty - only run on mount

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
        baseModelWindowYears: baseModelWindowYears,
        drawModelWindowYears: drawModelWindowYears,
        oddsCalibrationWindowYears: oddsCalibrationWindowYears,
        excludePreCovid: excludePreCovid,
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
  }, [pollTaskStatus, toast, selectedLeagues, selectedSeasons, dateFrom, dateTo, baseModelWindowYears, drawModelWindowYears, oddsCalibrationWindowYears, excludePreCovid]);

  const trainFullPipeline = useCallback(async () => {
    setIsTrainingPipeline(true);
    
    // Store interval reference for cleanup
    let pollInterval: NodeJS.Timeout | null = null;
    
    try {
      // Call backend API for full pipeline training with configuration
      const response = await apiClient.trainModel({
        modelType: 'full',
        leagues: selectedLeagues.length > 0 ? selectedLeagues : undefined,
        seasons: selectedSeasons.length > 0 ? selectedSeasons : undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        baseModelWindowYears: baseModelWindowYears,
        drawModelWindowYears: drawModelWindowYears,
        oddsCalibrationWindowYears: oddsCalibrationWindowYears,
        excludePreCovid: excludePreCovid,
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
        pollInterval = setInterval(async () => {
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
                setTrainingTasks(prev => {
                  const next = new Map(prev);
                  next.delete(taskId);
                  return next;
                });
                setIsTrainingPipeline(false);
                
                // Update all models to completed state with 100% progress
                setModels(prev => prev.map(m => ({
                  ...m,
                  status: 'completed' as const,
                  progress: 100, // Ensure 100% is set
                  phase: 'Complete',
                  // Don't set lastTrained here - will be updated from backend with actual completion time
                })));
                
                // Force re-render after a brief delay
                setTimeout(() => {
                  setModels(prev => prev.map(m => ({
                    ...m,
                    progress: 100
                  })));
                }, 100);
                
                toast({
                  title: 'Pipeline Complete',
                  description: 'All models trained successfully. New version ready for activation.',
                });
                
                // Refresh all data from backend after UI updates
                setTimeout(async () => {
                  await loadModelStatus();
                  await loadTrainingHistory();
                }, 500);
              }

              if (task.status === 'failed') {
                clearInterval(pollInterval);
                setTrainingTasks(prev => {
                  const next = new Map(prev);
                  next.delete(taskId);
                  return next;
                });
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
        
        // Store interval for cleanup
        setTrainingTasks(prev => {
          const next = new Map(prev);
          next.set(taskId, pollInterval!);
          return next;
        });
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
  }, [loadModelStatus, loadTrainingHistory, toast, selectedLeagues, selectedSeasons, dateFrom, dateTo]);

  const isAnyTraining = models.some(m => m.status === 'training');

  return (
    <PageLayout
      title="ML Training"
      description="Train and configure prediction models with advanced parameters"
      icon={<Layers className="h-6 w-6" />}
      action={
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setShowConfig(!showConfig)}
            className="btn-glow"
          >
            <Settings className="h-4 w-4 mr-2" />
            {showConfig ? 'Hide' : 'Show'} Configuration
          </Button>
          <Button
            onClick={trainFullPipeline}
            disabled={isTrainingPipeline || isAnyTraining}
            className="btn-glow"
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
      }
    >
      <div className="space-y-6">

      {/* Training Configuration */}
      {showConfig && (
        <ModernCard
          title="Training Configuration"
          description="Configure which leagues, seasons, and date range to use for training"
          icon={<Settings className="h-5 w-5" />}
          variant="elevated"
        >
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

            {/* Look-Back Window Configuration (SP-FX Recommended) */}
            <div className="space-y-4 p-4 bg-primary/5 rounded-lg border border-primary/20">
              <div className="flex items-center gap-2">
                <Info className="h-4 w-4 text-primary" />
                <Label className="text-base font-semibold">Look-Back Window Configuration</Label>
              </div>
              <p className="text-sm text-muted-foreground">
                Component-specific windows for optimal jackpot prediction (SP-FX Recommended)
              </p>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="baseModelWindow" className="text-sm">
                    Base Model Window (Years)
                    <span className="text-xs text-muted-foreground ml-1">(3-4 seasons recommended)</span>
                  </Label>
                  <Input
                    id="baseModelWindow"
                    type="number"
                    step="0.5"
                    min="1"
                    max="10"
                    value={baseModelWindowYears}
                    onChange={(e) => setBaseModelWindowYears(parseFloat(e.target.value) || 4.0)}
                    className="w-full"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="drawModelWindow" className="text-sm">
                    Draw Model Window (Years)
                    <span className="text-xs text-muted-foreground ml-1">(1.5-2.5 seasons recommended)</span>
                  </Label>
                  <Input
                    id="drawModelWindow"
                    type="number"
                    step="0.5"
                    min="1"
                    max="5"
                    value={drawModelWindowYears}
                    onChange={(e) => setDrawModelWindowYears(parseFloat(e.target.value) || 2.0)}
                    className="w-full"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="oddsCalibrationWindow" className="text-sm">
                    Odds Calibration Window (Years)
                    <span className="text-xs text-muted-foreground ml-1">(1-2 seasons recommended)</span>
                  </Label>
                  <Input
                    id="oddsCalibrationWindow"
                    type="number"
                    step="0.5"
                    min="0.5"
                    max="5"
                    value={oddsCalibrationWindowYears}
                    onChange={(e) => setOddsCalibrationWindowYears(parseFloat(e.target.value) || 1.5)}
                    className="w-full"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="excludePreCovid" className="text-sm flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="excludePreCovid"
                      checked={excludePreCovid}
                      onChange={(e) => setExcludePreCovid(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                    Exclude Pre-COVID Data
                    <span className="text-xs text-muted-foreground">(Before Aug 2020)</span>
                  </Label>
                </div>
              </div>
              
              <div className="mt-2 p-2 bg-muted/50 rounded text-xs text-muted-foreground">
                <p className="font-medium mb-1">Why Different Windows?</p>
                <ul className="list-disc list-inside space-y-0.5">
                  <li>Base models: 3-4 seasons for team strength stability</li>
                  <li>Draw models: 1.5-2.5 seasons (draw rates change faster)</li>
                  <li>Odds calibration: 1-2 seasons (market evolution)</li>
                </ul>
              </div>
            </div>

            {/* Summary */}
            <div className="p-4 bg-muted/50 rounded-lg">
              <p className="text-sm font-medium mb-2">Training Configuration Summary:</p>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Leagues: {selectedLeagues.length > 0 ? selectedLeagues.join(', ') : 'All leagues'}</li>
                <li>• Seasons: {selectedSeasons.length > 0 ? selectedSeasons.join(', ') : 'All seasons'}</li>
                <li>• Date Range: {dateFrom && dateTo ? `${dateFrom} to ${dateTo}` : dateFrom ? `From ${dateFrom}` : dateTo ? `Until ${dateTo}` : 'No date filter'}</li>
                <li>• Base Model Window: {baseModelWindowYears} years</li>
                <li>• Draw Model Window: {drawModelWindowYears} years</li>
                <li>• Odds Calibration Window: {oddsCalibrationWindowYears} years</li>
                <li>• Exclude Pre-COVID: {excludePreCovid ? 'Yes' : 'No'}</li>
              </ul>
            </div>
          </CardContent>
        </ModernCard>
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
                      disabled={
                        model.status === 'training' || 
                        isTrainingPipeline ||
                        model.id === 'draw'  // Draw model is deterministic, doesn't need training
                      }
                      title={model.id === 'draw' ? 'Draw model is deterministic and computed at inference time. It does not require training.' : undefined}
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
                {(model.status === 'training' || (model.status === 'completed' && model.progress < 100)) && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{model.phase}</span>
                      <span className="tabular-nums font-medium">{Math.round(model.progress)}%</span>
                    </div>
                    <Progress value={model.progress} className="h-2" />
                  </div>
                )}
                {/* Show completion state briefly */}
                {model.status === 'completed' && model.progress === 100 && (
                  <div className="space-y-2 animate-fade-in">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-green-600 font-medium">✓ Complete</span>
                      <span className="tabular-nums font-medium text-green-600">100%</span>
                    </div>
                    <Progress value={100} className="h-2" />
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
    </PageLayout>
  );
}
