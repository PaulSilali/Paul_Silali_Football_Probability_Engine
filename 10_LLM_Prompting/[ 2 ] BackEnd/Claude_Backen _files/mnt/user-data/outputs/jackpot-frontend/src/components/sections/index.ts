/**
 * Remaining Section Components
 * 
 * - Section 4: Calibration & Validation Dashboard
 * - Section 5: Model Explainability
 * - Section 6: Model Health & Monitoring
 * - Section 7: System & Data Management
 */

import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  ReferenceLine,
} from 'recharts';
import { AlertTriangle, CheckCircle, Clock, Download, RefreshCw, TrendingUp } from 'lucide-react';
import { useAppStore } from '../../store';
import {
  getValidationMetrics,
  getModelHealth,
  getDataCoverage,
  refreshData,
  trainModel,
  pollTaskUntilComplete,
} from '../../api';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Button,
  Badge,
  Alert,
  LoadingSpinner,
  Select,
} from '../ui';
import { formatBrierScore, formatDate, formatRelativeTime } from '../../utils';

// ============================================================================
// SECTION 4: CALIBRATION & VALIDATION DASHBOARD
// ============================================================================

export function CalibrationDashboard() {
  const { validationMetrics, setValidationMetrics } = useAppStore();
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    if (!validationMetrics) {
      loadMetrics();
    }
  }, []);
  
  const loadMetrics = async () => {
    setLoading(true);
    try {
      const metrics = await getValidationMetrics();
      setValidationMetrics(metrics);
    } catch (err) {
      console.error('Failed to load validation metrics:', err);
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      </Card>
    );
  }
  
  if (!validationMetrics) {
    return (
      <Card>
        <div className="text-center py-12">
          <p className="text-slate-600 mb-4">No validation metrics available</p>
          <Button onClick={loadMetrics}>Load Metrics</Button>
        </div>
      </Card>
    );
  }
  
  const { overallBrier, brierTrend, reliabilityCurves, expectedVsObserved } = validationMetrics;
  
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Calibration & Validation Dashboard</CardTitle>
              <CardDescription>
                Model performance metrics demonstrating probability calibration quality
              </CardDescription>
            </div>
            <Button onClick={loadMetrics} variant="ghost" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        
        <Alert variant="info">
          These metrics prove probabilities are trustworthy by comparing predicted probabilities
          with observed outcomes. Lower Brier scores and diagonal reliability curves indicate
          well-calibrated predictions.
        </Alert>
      </Card>
      
      {/* Overall Metrics */}
      <Card>
        <h4 className="text-sm font-medium text-slate-900 mb-4">Overall Performance</h4>
        <div className="grid grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-slate-600 mb-1">Brier Score</p>
            <p className="text-3xl font-semibold text-slate-900">
              {formatBrierScore(overallBrier)}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              {overallBrier < 0.20 ? 'Excellent' : overallBrier < 0.25 ? 'Good' : 'Needs Improvement'}
            </p>
          </div>
          <div>
            <p className="text-sm text-slate-600 mb-1">Sample Size</p>
            <p className="text-2xl font-semibold text-slate-900">
              {expectedVsObserved.reduce((sum, item) => sum + item.sampleSize, 0)}
            </p>
            <p className="text-xs text-slate-500 mt-1">matches evaluated</p>
          </div>
          <div>
            <p className="text-sm text-slate-600 mb-1">Status</p>
            <Badge variant="success" className="text-base">
              {overallBrier < 0.20 ? '✓ Well Calibrated' : '⚠ Monitor'}
            </Badge>
          </div>
        </div>
      </Card>
      
      {/* Brier Score Trend */}
      <Card>
        <CardTitle>Brier Score Trend</CardTitle>
        <CardDescription className="mb-4">
          Lower scores indicate better probability estimates. Target: &lt; 0.20
        </CardDescription>
        
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={brierTrend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="date"
              tick={{ fill: '#64748b', fontSize: 12 }}
              tickFormatter={(date) => new Date(date).toLocaleDateString()}
            />
            <YAxis
              domain={[0, 0.3]}
              tick={{ fill: '#64748b', fontSize: 12 }}
              label={{ value: 'Brier Score', angle: -90, position: 'insideLeft' }}
            />
            <RechartsTooltip
              contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0' }}
            />
            <ReferenceLine y={0.20} stroke="#10b981" strokeDasharray="3 3" label="Target" />
            <Line
              type="monotone"
              dataKey="score"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ fill: '#3b82f6', r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>
      
      {/* Reliability Curves */}
      <Card>
        <CardTitle>Reliability Curves (Calibration Plot)</CardTitle>
        <CardDescription className="mb-4">
          Points should follow the diagonal line. Deviation indicates miscalibration.
        </CardDescription>
        
        <ResponsiveContainer width="100%" height={400}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              type="number"
              dataKey="predictedProbability"
              domain={[0, 1]}
              tick={{ fill: '#64748b', fontSize: 12 }}
              label={{ value: 'Predicted Probability', position: 'insideBottom', offset: -5 }}
            />
            <YAxis
              type="number"
              dataKey="observedFrequency"
              domain={[0, 1]}
              tick={{ fill: '#64748b', fontSize: 12 }}
              label={{ value: 'Observed Frequency', angle: -90, position: 'insideLeft' }}
            />
            <RechartsTooltip
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0' }}
            />
            <ReferenceLine
              segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
              stroke="#64748b"
              strokeDasharray="5 5"
            />
            {reliabilityCurves.map((curve) => (
              <Scatter
                key={curve.outcome}
                name={curve.outcome}
                data={curve.points}
                fill={
                  curve.outcome === 'home' ? '#3b82f6' :
                  curve.outcome === 'draw' ? '#8b5cf6' :
                  '#10b981'
                }
              />
            ))}
            <Legend />
          </ScatterChart>
        </ResponsiveContainer>
      </Card>
      
      {/* Expected vs Observed */}
      <Card>
        <CardTitle>Expected vs Observed Outcomes</CardTitle>
        <CardDescription className="mb-4">
          Comparing model predictions against actual match results
        </CardDescription>
        
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Outcome</TableHead>
              <TableHead className="text-right">Expected</TableHead>
              <TableHead className="text-right">Observed</TableHead>
              <TableHead className="text-right">Difference</TableHead>
              <TableHead className="text-right">% Error</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {expectedVsObserved.map((item) => {
              const diff = item.observed - item.expected;
              const pctError = ((diff / item.expected) * 100).toFixed(1);
              
              return (
                <TableRow key={item.outcome}>
                  <TableCell className="font-medium capitalize">{item.outcome} Win</TableCell>
                  <TableCell className="text-right font-mono">{item.expected}</TableCell>
                  <TableCell className="text-right font-mono">{item.observed}</TableCell>
                  <TableCell className="text-right font-mono">
                    <span className={diff > 0 ? 'text-green-600' : diff < 0 ? 'text-red-600' : ''}>
                      {diff > 0 ? '+' : ''}{diff}
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    <span className={Math.abs(parseFloat(pctError)) > 5 ? 'text-amber-600' : 'text-slate-600'}>
                      {pctError}%
                    </span>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

// ============================================================================
// SECTION 5: MODEL EXPLAINABILITY
// ============================================================================

export function ModelExplainability() {
  const { activePrediction } = useAppStore();
  const [selectedFixtureIndex, setSelectedFixtureIndex] = useState(0);
  
  if (!activePrediction) {
    return (
      <Card>
        <div className="text-center py-12 text-slate-600">
          No active prediction. Generate predictions to view explainability.
        </div>
      </Card>
    );
  }
  
  const { fixtures, explainability } = activePrediction;
  const fixtureExplain = explainability?.[selectedFixtureIndex];
  
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Model Explainability</CardTitle>
          <CardDescription>
            Feature contributions to probability estimates. These describe statistical associations, not causation.
          </CardDescription>
        </CardHeader>
        
        <Alert variant="info">
          These values describe contribution to probability, not causation.
          They show which features pushed probabilities higher or lower relative to the baseline.
        </Alert>
      </Card>
      
      {/* Fixture Selector */}
      <Card>
        <Select
          label="Select Fixture"
          value={selectedFixtureIndex.toString()}
          onChange={(e) => setSelectedFixtureIndex(parseInt(e.target.value))}
        >
          {fixtures.map((fixture, idx) => (
            <option key={fixture.id} value={idx}>
              {idx + 1}. {fixture.homeTeam} vs {fixture.awayTeam}
            </option>
          ))}
        </Select>
      </Card>
      
      {/* Feature Contributions */}
      {fixtureExplain ? (
        <>
          <Card>
            <CardTitle>
              {fixtures[selectedFixtureIndex].homeTeam} vs {fixtures[selectedFixtureIndex].awayTeam}
            </CardTitle>
            
            <div className="mt-4">
              <h4 className="text-sm font-medium text-slate-700 mb-3">Base Rate (League Average)</h4>
              <div className="flex gap-4 text-sm">
                <div>
                  <span className="text-slate-600">Home:</span>{' '}
                  <span className="font-mono">{(fixtureExplain.baseRate.home * 100).toFixed(1)}%</span>
                </div>
                <div>
                  <span className="text-slate-600">Draw:</span>{' '}
                  <span className="font-mono">{(fixtureExplain.baseRate.draw * 100).toFixed(1)}%</span>
                </div>
                <div>
                  <span className="text-slate-600">Away:</span>{' '}
                  <span className="font-mono">{(fixtureExplain.baseRate.away * 100).toFixed(1)}%</span>
                </div>
              </div>
            </div>
            
            <div className="mt-6">
              <h4 className="text-sm font-medium text-slate-700 mb-3">Feature Contributions</h4>
              <div className="space-y-2">
                {fixtureExplain.features.map((feature, idx) => {
                  const contribution = feature.contribution;
                  const isPositive = contribution > 0;
                  const barWidth = Math.abs(contribution) * 200; // Scale for visualization
                  
                  return (
                    <div key={idx} className="flex items-center gap-4">
                      <div className="w-48 text-sm text-slate-700 text-right">
                        {feature.name}
                      </div>
                      <div className="flex-1 relative h-6">
                        <div className="absolute inset-y-0 left-1/2 w-px bg-slate-300" />
                        <div
                          className={`absolute inset-y-0 h-full ${
                            isPositive ? 'bg-blue-500 left-1/2' : 'bg-red-500 right-1/2'
                          }`}
                          style={{ width: `${Math.min(barWidth, 50)}%` }}
                        />
                      </div>
                      <div className="w-20 text-sm font-mono text-slate-900">
                        {isPositive ? '+' : ''}{(contribution * 100).toFixed(1)}pp
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </Card>
          
          {/* Model vs Market */}
          <Card>
            <CardTitle>Model-Market Comparison</CardTitle>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Source</TableHead>
                  <TableHead className="text-center">Home</TableHead>
                  <TableHead className="text-center">Draw</TableHead>
                  <TableHead className="text-center">Away</TableHead>
                  <TableHead className="text-center">Divergence</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell className="font-medium">Model</TableCell>
                  <TableCell className="text-center font-mono">
                    {(fixtureExplain.modelVsMarket.modelProbabilities.home * 100).toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-center font-mono">
                    {(fixtureExplain.modelVsMarket.modelProbabilities.draw * 100).toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-center font-mono">
                    {(fixtureExplain.modelVsMarket.modelProbabilities.away * 100).toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-center" rowSpan={2}>
                    <Badge variant="default">
                      {(fixtureExplain.modelVsMarket.divergence * 100).toFixed(1)}%
                    </Badge>
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Market</TableCell>
                  <TableCell className="text-center font-mono">
                    {(fixtureExplain.modelVsMarket.marketImplied.home * 100).toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-center font-mono">
                    {(fixtureExplain.modelVsMarket.marketImplied.draw * 100).toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-center font-mono">
                    {(fixtureExplain.modelVsMarket.marketImplied.away * 100).toFixed(1)}%
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
            
            <div className="mt-4 p-4 bg-slate-50 rounded-md text-sm text-slate-700">
              {fixtureExplain.modelVsMarket.divergence < 0.05 ? (
                <p>✓ Model and market are closely aligned on this fixture.</p>
              ) : fixtureExplain.modelVsMarket.divergence < 0.10 ? (
                <p>→ Moderate divergence. Model sees some value different from market.</p>
              ) : (
                <p>⚠ Significant divergence. Investigate whether model or market has better information.</p>
              )}
            </div>
          </Card>
        </>
      ) : (
        <Card>
          <Alert variant="warning">
            Explainability data not available for this fixture.
          </Alert>
        </Card>
      )}
    </div>
  );
}

// ============================================================================
// SECTION 6: MODEL HEALTH & MONITORING
// ============================================================================

export function ModelHealth() {
  const { modelHealth, setModelHealth } = useAppStore();
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    if (!modelHealth) {
      loadHealth();
    }
  }, []);
  
  const loadHealth = async () => {
    setLoading(true);
    try {
      const health = await getModelHealth();
      setModelHealth(health);
    } catch (err) {
      console.error('Failed to load model health:', err);
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      </Card>
    );
  }
  
  if (!modelHealth) {
    return (
      <Card>
        <div className="text-center py-12">
          <p className="text-slate-600 mb-4">No health data available</p>
          <Button onClick={loadHealth}>Load Health Status</Button>
        </div>
      </Card>
    );
  }
  
  const { status, lastChecked, metrics, alerts, driftIndicators } = modelHealth;
  
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Model Health & Monitoring</CardTitle>
              <CardDescription>
                System integrity monitoring and drift detection
              </CardDescription>
            </div>
            <Button onClick={loadHealth} variant="ghost" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
      </Card>
      
      {/* Status Overview */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-lg font-medium text-slate-900 mb-1">System Status</h4>
            <p className="text-sm text-slate-600">Last checked: {formatRelativeTime(lastChecked)}</p>
          </div>
          <div>
            {status === 'healthy' && (
              <Badge variant="success" className="text-lg px-4 py-2">
                <CheckCircle className="h-5 w-5 mr-2 inline" />
                Healthy
              </Badge>
            )}
            {status === 'watch' && (
              <Badge variant="warning" className="text-lg px-4 py-2">
                <Clock className="h-5 w-5 mr-2 inline" />
                Watch
              </Badge>
            )}
            {status === 'degraded' && (
              <Badge variant="error" className="text-lg px-4 py-2">
                <AlertTriangle className="h-5 w-5 mr-2 inline" />
                Degraded
              </Badge>
            )}
          </div>
        </div>
      </Card>
      
      {/* Real-Time Metrics */}
      <Card>
        <CardTitle>Real-Time Metrics</CardTitle>
        <div className="mt-4 grid grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-slate-600 mb-1">Model-Market Divergence</p>
            <p className="text-2xl font-semibold text-slate-900">
              {(metrics.modelMarketDivergence * 100).toFixed(1)}%
            </p>
            <Badge variant={metrics.modelMarketDivergence < 0.10 ? 'success' : 'warning'} className="mt-2">
              {metrics.modelMarketDivergence < 0.10 ? 'Normal' : 'Elevated'}
            </Badge>
          </div>
          <div>
            <p className="text-sm text-slate-600 mb-1">Odds Volatility Index</p>
            <p className="text-2xl font-semibold text-slate-900">
              {metrics.oddsVolatilityIndex.toFixed(2)}
            </p>
            <Badge variant={metrics.oddsVolatilityIndex < 3.0 ? 'success' : 'warning'} className="mt-2">
              {metrics.oddsVolatilityIndex < 3.0 ? 'Normal' : 'High'}
            </Badge>
          </div>
          <div>
            <p className="text-sm text-slate-600 mb-1">Avg Prediction Entropy</p>
            <p className="text-2xl font-semibold text-slate-900">
              {metrics.averageEntropy.toFixed(2)}
            </p>
            <Badge variant={
              metrics.averageEntropy > 0.8 && metrics.averageEntropy < 1.3 ? 'success' : 'warning'
            } className="mt-2">
              {metrics.averageEntropy > 0.8 && metrics.averageEntropy < 1.3 ? 'Normal' : 'Check'}
            </Badge>
          </div>
        </div>
      </Card>
      
      {/* Drift Indicators */}
      <Card>
        <CardTitle>Drift Detection</CardTitle>
        <Table className="mt-4">
          <TableHeader>
            <TableRow>
              <TableHead>Metric</TableHead>
              <TableHead>Current Value</TableHead>
              <TableHead>Threshold</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {driftIndicators.map((indicator, idx) => (
              <TableRow key={idx}>
                <TableCell className="font-medium">{indicator.metric}</TableCell>
                <TableCell className="font-mono">{indicator.currentValue.toFixed(3)}</TableCell>
                <TableCell className="font-mono">{indicator.threshold.toFixed(3)}</TableCell>
                <TableCell>
                  <Badge variant={
                    indicator.status === 'normal' ? 'success' :
                    indicator.status === 'warning' ? 'warning' : 'error'
                  }>
                    {indicator.status}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
      
      {/* Alerts */}
      {alerts.length > 0 && (
        <Card>
          <CardTitle>Recent Alerts</CardTitle>
          <div className="mt-4 space-y-3">
            {alerts.map((alert) => (
              <Alert
                key={alert.id}
                variant={
                  alert.severity === 'critical' ? 'error' :
                  alert.severity === 'warning' ? 'warning' : 'info'
                }
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">{alert.message}</p>
                    <p className="text-xs mt-1">{formatDate(alert.timestamp)}</p>
                  </div>
                  {alert.resolved && (
                    <Badge variant="success">Resolved</Badge>
                  )}
                </div>
              </Alert>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

// ============================================================================
// SECTION 7: SYSTEM & DATA MANAGEMENT
// ============================================================================

export function SystemManagement() {
  const { currentModelVersion } = useAppStore();
  const [dataCoverage, setDataCoverage] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskProgress, setTaskProgress] = useState<number | null>(null);
  
  useEffect(() => {
    loadDataCoverage();
  }, []);
  
  const loadDataCoverage = async () => {
    try {
      const coverage = await getDataCoverage();
      setDataCoverage(coverage);
    } catch (err) {
      console.error('Failed to load data coverage:', err);
    }
  };
  
  const handleDataRefresh = async (league: string, season: string) => {
    setLoading(true);
    setTaskProgress(0);
    
    try {
      const { taskId } = await refreshData(league, season);
      
      const task = await pollTaskUntilComplete(taskId, (progress) => {
        setTaskProgress(progress);
      });
      
      if (task.status === 'complete') {
        alert(`Successfully added ${task.details?.matchesAdded} matches`);
        await loadDataCoverage();
      }
    } catch (err) {
      alert(`Failed to refresh data: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
      setTaskProgress(null);
    }
  };
  
  const handleTrainModel = async () => {
    if (!confirm('Start model retraining? This may take several minutes.')) return;
    
    setLoading(true);
    try {
      const { taskId } = await trainModel();
      alert(`Training started. Task ID: ${taskId}`);
    } catch (err) {
      alert(`Failed to start training: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>System & Data Management</CardTitle>
          <CardDescription>
            Model version control and historical data management
          </CardDescription>
        </CardHeader>
      </Card>
      
      {/* Model Information */}
      {currentModelVersion && (
        <Card>
          <CardTitle>Current Model Version</CardTitle>
          <div className="mt-4 grid grid-cols-2 gap-6">
            <div>
              <p className="text-sm text-slate-600">Version</p>
              <p className="text-lg font-semibold text-slate-900">{currentModelVersion.version}</p>
            </div>
            <div>
              <p className="text-sm text-slate-600">Trained At</p>
              <p className="text-lg font-semibold text-slate-900">
                {formatDate(currentModelVersion.trainedAt)}
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-600">Data Version</p>
              <p className="text-lg font-semibold text-slate-900">{currentModelVersion.dataVersion}</p>
            </div>
            <div>
              <p className="text-sm text-slate-600">Brier Score</p>
              <p className="text-lg font-semibold text-slate-900">
                {formatBrierScore(currentModelVersion.validationMetrics.brierScore)}
              </p>
            </div>
          </div>
          
          <div className="mt-6">
            <Button onClick={handleTrainModel} disabled={loading}>
              <TrendingUp className="h-4 w-4 mr-2" />
              Retrain Model
            </Button>
          </div>
        </Card>
      )}
      
      {/* Data Coverage */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <CardTitle>Data Coverage</CardTitle>
          <Button onClick={loadDataCoverage} variant="ghost" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
        
        {taskProgress !== null && (
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-600">Download Progress</span>
              <span className="text-sm font-mono text-slate-900">{taskProgress}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div
                className="bg-slate-700 h-2 rounded-full transition-all duration-300"
                style={{ width: `${taskProgress}%` }}
              />
            </div>
          </div>
        )}
        
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>League</TableHead>
              <TableHead>Seasons</TableHead>
              <TableHead>Matches</TableHead>
              <TableHead>Status</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {dataCoverage.map((league) => (
              <TableRow key={league.leagueId}>
                <TableCell className="font-medium">{league.leagueName}</TableCell>
                <TableCell>{league.seasons.join(', ')}</TableCell>
                <TableCell className="font-mono">{league.matchCount.toLocaleString()}</TableCell>
                <TableCell>
                  <Badge variant={
                    league.status === 'complete' ? 'success' :
                    league.status === 'partial' ? 'warning' : 'error'
                  }>
                    {league.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDataRefresh(league.leagueId, '2024-25')}
                    disabled={loading}
                  >
                    <Download className="h-4 w-4 mr-1" />
                    Update
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
