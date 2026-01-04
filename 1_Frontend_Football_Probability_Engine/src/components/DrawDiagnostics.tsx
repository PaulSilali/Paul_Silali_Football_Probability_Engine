import { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  Target,
  AlertCircle,
  CheckCircle,
  Loader2,
  RefreshCw,
  Info
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/services/api';

interface DrawDiagnosticsData {
  brier_score: number | null;
  reliability_curve: Array<{
    predicted_prob: number;
    observed_frequency: number;
    sample_count: number;
    bin_low: number;
    bin_high: number;
  }>;
  sample_count: number;
  mean_predicted: number;
  mean_actual: number;
  calibration_error: number;
}

interface DrawStats {
  avg_multiplier: number | null;
  total_predictions: number;
  with_components: number;
  distribution: Array<{ category: string; count: number }>;
}

export function DrawDiagnostics() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [diagnostics, setDiagnostics] = useState<DrawDiagnosticsData | null>(null);
  const [stats, setStats] = useState<DrawStats | null>(null);
  const [modelId, setModelId] = useState<number | undefined>();

  const loadDiagnostics = async () => {
    setLoading(true);
    try {
      const [diagResponse, statsResponse] = await Promise.all([
        apiClient.getDrawDiagnostics(modelId),
        apiClient.getDrawStats()
      ]);
      
      setDiagnostics(diagResponse.data);
      setStats(statsResponse.data);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to load diagnostics',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDiagnostics();
  }, [modelId]);

  const handleTrainCalibrator = async () => {
    setLoading(true);
    try {
      const response = await apiClient.trainDrawCalibrator(modelId);
      toast({
        title: response.data.is_fitted ? 'Success' : 'Warning',
        description: response.data.message
      });
      if (response.data.is_fitted) {
        loadDiagnostics();
      }
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to train calibrator',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  // Prepare reliability curve data
  const reliabilityData = diagnostics?.reliability_curve.map(point => ({
    predicted: (point.predicted_prob * 100).toFixed(1),
    observed: (point.observed_frequency * 100).toFixed(1),
    sample: point.sample_count,
    perfect: (point.predicted_prob * 100).toFixed(1) // Perfect calibration line
  })) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Draw Probability Diagnostics</h2>
          <p className="text-muted-foreground">
            Monitor draw probability calibration and structural adjustment performance
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={handleTrainCalibrator}
            disabled={loading}
            variant="outline"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Training...
              </>
            ) : (
              <>
                <Target className="h-4 w-4 mr-2" />
                Train Calibrator
              </>
            )}
          </Button>
          <Button
            onClick={loadDiagnostics}
            disabled={loading}
            variant="outline"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Draw Brier Score
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {diagnostics?.brier_score !== null && diagnostics?.brier_score !== undefined
                ? diagnostics.brier_score.toFixed(4)
                : 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {diagnostics?.brier_score !== null && diagnostics.brier_score < 0.2
                ? 'Excellent'
                : diagnostics?.brier_score !== null && diagnostics.brier_score < 0.25
                ? 'Good'
                : 'Needs Improvement'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Calibration Error
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {diagnostics?.calibration_error !== undefined
                ? (diagnostics.calibration_error * 100).toFixed(2) + '%'
                : 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Lower is better
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Sample Size
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {diagnostics?.sample_count?.toLocaleString() || '0'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Predictions analyzed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Avg Multiplier
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.avg_multiplier?.toFixed(3) || 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Draw adjustment factor
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Reliability Curve */}
      <Card>
        <CardHeader>
          <CardTitle>Reliability Curve</CardTitle>
          <CardDescription>
            Predicted vs observed draw probability (perfect calibration = diagonal line)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {reliabilityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={reliabilityData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="predicted"
                  label={{ value: 'Predicted Probability (%)', position: 'insideBottom', offset: -5 }}
                />
                <YAxis
                  label={{ value: 'Observed Frequency (%)', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip
                  formatter={(value: any, name: string) => {
                    if (name === 'perfect') return null;
                    return [`${value}%`, name === 'observed' ? 'Observed' : 'Perfect'];
                  }}
                  labelFormatter={(label) => `Predicted: ${label}%`}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="perfect"
                  stroke="#8884d8"
                  strokeDasharray="5 5"
                  name="Perfect Calibration"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="observed"
                  stroke="#82ca9d"
                  strokeWidth={2}
                  name="Observed"
                  dot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-muted-foreground">
              <AlertCircle className="h-8 w-8 mr-2" />
              No reliability data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Draw Probability Distribution</CardTitle>
          <CardDescription>
            Distribution of predicted draw probabilities
          </CardDescription>
        </CardHeader>
        <CardContent>
          {stats?.distribution && stats.distribution.length > 0 ? (
            <div className="space-y-4">
              {stats.distribution.map((item) => (
                <div key={item.category} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{item.category}</span>
                    <span className="text-sm text-muted-foreground">{item.count} predictions</span>
                  </div>
                  <Progress
                    value={(item.count / (stats.total_predictions || 1)) * 100}
                    className="h-2"
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-muted-foreground py-8">
              No distribution data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Prediction Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Mean Predicted:</span>
              <span className="font-medium">
                {diagnostics?.mean_predicted !== undefined
                  ? (diagnostics.mean_predicted * 100).toFixed(2) + '%'
                  : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Mean Actual:</span>
              <span className="font-medium">
                {diagnostics?.mean_actual !== undefined
                  ? (diagnostics.mean_actual * 100).toFixed(2) + '%'
                  : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">With Components:</span>
              <span className="font-medium">
                {stats?.with_components || 0} / {stats?.total_predictions || 0}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Status</CardTitle>
          </CardHeader>
          <CardContent>
            {diagnostics?.brier_score !== null && diagnostics?.brier_score !== undefined ? (
              <Alert>
                {diagnostics.brier_score < 0.2 ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {diagnostics.brier_score < 0.2
                    ? 'Draw calibration is excellent'
                    : diagnostics.brier_score < 0.25
                    ? 'Draw calibration is good'
                    : 'Draw calibration needs improvement'}
                </AlertDescription>
              </Alert>
            ) : (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  Insufficient validation data. More predictions with actual results needed.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

