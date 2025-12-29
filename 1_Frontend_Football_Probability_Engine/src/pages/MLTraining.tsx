import { useState, useCallback } from 'react';
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
  ChevronUp
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

const initialModels: ModelConfig[] = [
  {
    id: 'poisson',
    name: 'Poisson / Dixon-Coles',
    description: 'Team strength model for goal expectations',
    status: 'idle',
    progress: 0,
    phase: '',
    lastTrained: '2024-12-27T10:00:00Z',
    metrics: { brierScore: 0.142, logLoss: 0.891, drawAccuracy: 58.2, rmse: 0.823 },
    parameters: {
      decayRate: 0.0065,
      homeAdvantage: true,
      lowScoreCorrection: true,
      seasons: '2018-2024',
      leagues: 12,
    },
  },
  {
    id: 'blending',
    name: 'Odds Blending Model',
    description: 'Learn trust weights between model and market',
    status: 'idle',
    progress: 0,
    phase: '',
    lastTrained: '2024-12-27T10:05:00Z',
    metrics: { brierScore: 0.138, logLoss: 0.872 },
    parameters: {
      algorithm: 'LightGBM',
      modelWeight: 0.65,
      marketWeight: 0.35,
      leagueSpecific: true,
      crossValidation: 5,
    },
  },
  {
    id: 'calibration',
    name: 'Calibration Model',
    description: 'Isotonic regression for probability correctness',
    status: 'idle',
    progress: 0,
    phase: '',
    lastTrained: '2024-12-27T10:08:00Z',
    metrics: { brierScore: 0.135, logLoss: 0.858 },
    parameters: {
      method: 'Isotonic',
      perLeague: true,
      minSamples: 100,
      smoothing: 0.1,
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
};

const trainingHistory = [
  { id: '1', date: '2024-12-27', model: 'Full Pipeline', duration: '12m 45s', status: 'success', brierDelta: -0.003 },
  { id: '2', date: '2024-12-20', model: 'Poisson Only', duration: '4m 32s', status: 'success', brierDelta: -0.002 },
  { id: '3', date: '2024-12-15', model: 'Full Pipeline', duration: '11m 58s', status: 'success', brierDelta: -0.005 },
  { id: '4', date: '2024-12-08', model: 'Calibration Only', duration: '1m 23s', status: 'success', brierDelta: -0.001 },
  { id: '5', date: '2024-12-01', model: 'Full Pipeline', duration: '13m 02s', status: 'failed', brierDelta: 0 },
];

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
  const { toast } = useToast();

  const toggleParams = (modelId: string) => {
    setExpandedParams(prev =>
      prev.includes(modelId) ? prev.filter(id => id !== modelId) : [...prev, modelId]
    );
  };

  const trainModel = useCallback((modelId: string) => {
    const phases = trainingPhases[modelId] || ['Training...'];
    
    setModels(prev => prev.map(m =>
      m.id === modelId ? { ...m, status: 'training' as const, progress: 0, phase: phases[0] } : m
    ));

    let phaseIndex = 0;
    let progress = 0;

    const interval = setInterval(() => {
      progress += Math.random() * 8 + 2;
      
      const newPhaseIndex = Math.min(
        Math.floor((progress / 100) * phases.length),
        phases.length - 1
      );
      
      if (newPhaseIndex > phaseIndex) {
        phaseIndex = newPhaseIndex;
      }

      setModels(prev => prev.map(m =>
        m.id === modelId
          ? { ...m, progress: Math.min(progress, 100), phase: phases[phaseIndex] }
          : m
      ));

      if (progress >= 100) {
        clearInterval(interval);
        const metrics = {
          brierScore: 0.13 + Math.random() * 0.02,
          logLoss: 0.85 + Math.random() * 0.05,
          drawAccuracy: 55 + Math.random() * 8,
          rmse: 0.8 + Math.random() * 0.1,
        };
        setModels(prev => prev.map(m =>
          m.id === modelId
            ? {
                ...m,
                status: 'completed' as const,
                progress: 100,
                phase: 'Complete',
                lastTrained: new Date().toISOString(),
                metrics,
              }
            : m
        ));
        toast({
          title: 'Training Complete',
          description: `${models.find(m => m.id === modelId)?.name} trained successfully.`,
        });
      }
    }, 300);
  }, [models, toast]);

  const trainFullPipeline = useCallback(() => {
    setIsTrainingPipeline(true);
    const modelOrder = ['poisson', 'blending', 'calibration'];
    let currentIndex = 0;

    const trainNext = () => {
      if (currentIndex >= modelOrder.length) {
        setIsTrainingPipeline(false);
        toast({
          title: 'Pipeline Complete',
          description: 'All models trained successfully. New version ready for activation.',
        });
        return;
      }

      const modelId = modelOrder[currentIndex];
      const phases = trainingPhases[modelId] || ['Training...'];
      
      setModels(prev => prev.map(m =>
        m.id === modelId ? { ...m, status: 'training' as const, progress: 0, phase: phases[0] } : m
      ));

      let phaseIndex = 0;
      let progress = 0;

      const interval = setInterval(() => {
        progress += Math.random() * 10 + 5;
        const newPhaseIndex = Math.min(Math.floor((progress / 100) * phases.length), phases.length - 1);
        if (newPhaseIndex > phaseIndex) phaseIndex = newPhaseIndex;

        setModels(prev => prev.map(m =>
          m.id === modelId ? { ...m, progress: Math.min(progress, 100), phase: phases[phaseIndex] } : m
        ));

        if (progress >= 100) {
          clearInterval(interval);
          setModels(prev => prev.map(m =>
            m.id === modelId
              ? {
                  ...m,
                  status: 'completed' as const,
                  progress: 100,
                  phase: 'Complete',
                  lastTrained: new Date().toISOString(),
                  metrics: {
                    brierScore: 0.13 + Math.random() * 0.02,
                    logLoss: 0.85 + Math.random() * 0.05,
                    drawAccuracy: 55 + Math.random() * 8,
                  },
                }
              : m
          ));
          currentIndex++;
          setTimeout(trainNext, 500);
        }
      }, 200);
    };

    trainNext();
  }, [toast]);

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
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Training History
              </CardTitle>
              <CardDescription>
                Past training runs and performance changes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Model</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Brier Δ</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {trainingHistory.map((run) => (
                      <TableRow key={run.id}>
                        <TableCell className="text-sm">{formatDate(run.date)}</TableCell>
                        <TableCell className="font-medium">{run.model}</TableCell>
                        <TableCell className="text-sm text-muted-foreground tabular-nums">
                          {run.duration}
                        </TableCell>
                        <TableCell>
                          {run.status === 'success' ? (
                            <Badge variant="secondary" className="bg-green-500/10 text-green-600">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Success
                            </Badge>
                          ) : (
                            <Badge variant="destructive">
                              <AlertCircle className="h-3 w-3 mr-1" />
                              Failed
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {run.brierDelta !== 0 ? (
                            <span className={run.brierDelta < 0 ? 'text-green-600' : 'text-red-600'}>
                              {run.brierDelta > 0 ? '+' : ''}{run.brierDelta.toFixed(3)}
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
