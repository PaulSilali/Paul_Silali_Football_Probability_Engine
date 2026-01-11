import { useState, useEffect } from 'react';
import { 
  Target, 
  Play, 
  CheckCircle, 
  AlertTriangle,
  Loader2,
  Calendar,
  Database,
  Settings,
  RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageLayout } from '@/components/layouts/PageLayout';
import { ModernCard } from '@/components/ui/modern-card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
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

interface CalibrationVersion {
  calibration_id: string;
  samples_used: number;
  created_at: string;
  valid_from: string;
}

interface ActiveCalibrations {
  model_version: string;
  league: string | null;
  calibrations: Record<string, CalibrationVersion>;
}

export default function CalibrationManagement() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [fitting, setFitting] = useState(false);
  const [activating, setActivating] = useState<string | null>(null);
  const [modelVersion, setModelVersion] = useState('poisson-v1.0');
  const [league, setLeague] = useState<string>('');
  const [minSamples, setMinSamples] = useState(200);
  const [activeCalibrations, setActiveCalibrations] = useState<ActiveCalibrations | null>(null);
  const [fittedCalibrationIds, setFittedCalibrationIds] = useState<string[]>([]);

  useEffect(() => {
    loadActiveCalibrations();
  }, [modelVersion, league]);

  const loadActiveCalibrations = async () => {
    try {
      setLoading(true);
      const response = await apiClient.getActiveCalibrations({
        model_version: modelVersion,
        league: league || undefined,
      });
      
      if (response.success && response.data) {
        setActiveCalibrations(response.data);
      }
    } catch (error: any) {
      console.error('Error loading active calibrations:', error);
      toast({
        title: 'Error',
        description: 'Failed to load active calibrations',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleFitCalibration = async () => {
    try {
      setFitting(true);
      const response = await apiClient.fitCalibration({
        model_version: modelVersion,
        league: league || undefined,
        min_samples: minSamples,
      });
      
      if (response.success && response.data) {
        setFittedCalibrationIds(response.data.calibration_ids);
        toast({
          title: 'Success',
          description: `Fitted ${response.data.calibration_ids.length} calibration curves. Review and activate below.`,
        });
        // Reload active calibrations
        await loadActiveCalibrations();
      } else {
        throw new Error(response.message || 'Failed to fit calibration');
      }
    } catch (error: any) {
      console.error('Error fitting calibration:', error);
      toast({
        title: 'Error',
        description: error?.message || 'Failed to fit calibration',
        variant: 'destructive',
      });
    } finally {
      setFitting(false);
    }
  };

  const handleActivateCalibration = async (calibrationId: string) => {
    try {
      setActivating(calibrationId);
      const response = await apiClient.activateCalibration(calibrationId);
      
      if (response.success) {
        toast({
          title: 'Success',
          description: 'Calibration activated successfully',
        });
        // Reload active calibrations
        await loadActiveCalibrations();
      } else {
        throw new Error(response.message || 'Failed to activate calibration');
      }
    } catch (error: any) {
      console.error('Error activating calibration:', error);
      toast({
        title: 'Error',
        description: error?.message || 'Failed to activate calibration',
        variant: 'destructive',
      });
    } finally {
      setActivating(null);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <PageLayout
      title="Calibration Management"
      description="Fit and manage versioned probability calibration curves"
      icon={<Target className="h-6 w-6" />}
    >
      <div className="space-y-6">
        <Alert>
          <Target className="h-4 w-4" />
          <AlertTitle>Versioned Calibration System</AlertTitle>
          <AlertDescription>
            This system allows you to fit new calibration curves from historical data and activate them safely.
            Calibrations are versioned and reversible - you can always activate a previous version.
          </AlertDescription>
        </Alert>

        {/* Fit New Calibration */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Fit New Calibration
            </CardTitle>
            <CardDescription>
              Fit isotonic regression calibration curves from historical prediction snapshots and results
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="model_version">Model Version</Label>
                <Input
                  id="model_version"
                  value={modelVersion}
                  onChange={(e) => setModelVersion(e.target.value)}
                  placeholder="poisson-v1.0"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="league">League (Optional)</Label>
                <Input
                  id="league"
                  value={league}
                  onChange={(e) => setLeague(e.target.value)}
                  placeholder="E0, SP1, etc. (leave empty for global)"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="min_samples">Min Samples</Label>
                <Input
                  id="min_samples"
                  type="number"
                  value={minSamples}
                  onChange={(e) => setMinSamples(parseInt(e.target.value) || 200)}
                  min={50}
                />
              </div>
            </div>
            <Button
              onClick={handleFitCalibration}
              disabled={fitting || !modelVersion}
              className="w-full md:w-auto"
            >
              {fitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Fitting...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Fit Calibration
                </>
              )}
            </Button>
            {fittedCalibrationIds.length > 0 && (
              <Alert className="bg-green-500/10 border-green-500/20">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <AlertDescription>
                  Fitted {fittedCalibrationIds.length} calibration curves. IDs: {fittedCalibrationIds.join(', ')}
                  <br />
                  <span className="text-xs">Review and activate below.</span>
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Active Calibrations */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              Active Calibrations
            </CardTitle>
            <CardDescription>
              Currently active calibration curves for {modelVersion}
              {league && ` in ${league}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : activeCalibrations && Object.keys(activeCalibrations.calibrations).length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Outcome</TableHead>
                    <TableHead>Calibration ID</TableHead>
                    <TableHead>Samples Used</TableHead>
                    <TableHead>Created At</TableHead>
                    <TableHead>Valid From</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(activeCalibrations.calibrations).map(([outcome, cal]) => (
                    <TableRow key={outcome}>
                      <TableCell>
                        <Badge variant="outline">{outcome}</Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {cal.calibration_id.substring(0, 8)}...
                      </TableCell>
                      <TableCell>{cal.samples_used.toLocaleString()}</TableCell>
                      <TableCell>{formatDate(cal.created_at)}</TableCell>
                      <TableCell>{formatDate(cal.valid_from)}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="bg-green-500/10 text-green-700 dark:text-green-400">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Active
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  No active calibrations found for {modelVersion}
                  {league && ` in ${league}`}. Fit a new calibration above.
                </AlertDescription>
              </Alert>
            )}
            <Button
              variant="outline"
              onClick={loadActiveCalibrations}
              disabled={loading}
              className="mt-4"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </CardContent>
        </Card>

        {/* Info Card */}
        <Card className="bg-muted/50">
          <CardHeader>
            <CardTitle className="text-lg">How It Works</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              <strong>1. Fit Calibration:</strong> Creates new calibration curves from historical data (prediction_snapshot + jackpot_fixtures).
              This does NOT activate them automatically.
            </p>
            <p>
              <strong>2. Review:</strong> Check the fitted calibration IDs and sample counts.
            </p>
            <p>
              <strong>3. Activate:</strong> Use the API endpoint to activate a specific calibration_id.
              This deactivates the previous calibration for the same scope (outcome, league, model_version).
            </p>
            <p>
              <strong>4. Rollback:</strong> To rollback, simply activate a previous calibration_id.
            </p>
            <p className="text-xs italic mt-4">
              Note: Calibrations are versioned and append-only. They never overwrite existing calibrations.
            </p>
          </CardContent>
        </Card>
      </div>
    </PageLayout>
  );
}

