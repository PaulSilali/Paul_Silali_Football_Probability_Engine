import { useState } from 'react';
import { Info } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  BarChart,
  Bar,
  Legend,
} from 'recharts';
import type { CalibrationPoint, BrierScorePoint } from '@/types';

// Mock data
const reliabilityCurve: CalibrationPoint[] = [
  { predictedProbability: 0.1, observedFrequency: 0.09, sampleSize: 245 },
  { predictedProbability: 0.2, observedFrequency: 0.21, sampleSize: 312 },
  { predictedProbability: 0.3, observedFrequency: 0.28, sampleSize: 428 },
  { predictedProbability: 0.4, observedFrequency: 0.42, sampleSize: 356 },
  { predictedProbability: 0.5, observedFrequency: 0.48, sampleSize: 289 },
  { predictedProbability: 0.6, observedFrequency: 0.61, sampleSize: 334 },
  { predictedProbability: 0.7, observedFrequency: 0.68, sampleSize: 278 },
  { predictedProbability: 0.8, observedFrequency: 0.79, sampleSize: 201 },
  { predictedProbability: 0.9, observedFrequency: 0.88, sampleSize: 156 },
];

const brierScoreTrend: BrierScorePoint[] = [
  { date: '2024-01', score: 0.198 },
  { date: '2024-02', score: 0.192 },
  { date: '2024-03', score: 0.205 },
  { date: '2024-04', score: 0.188 },
  { date: '2024-05', score: 0.195 },
  { date: '2024-06', score: 0.183 },
  { date: '2024-07', score: 0.191 },
  { date: '2024-08', score: 0.187 },
  { date: '2024-09', score: 0.179 },
  { date: '2024-10', score: 0.185 },
  { date: '2024-11', score: 0.182 },
  { date: '2024-12', score: 0.178 },
];

const expectedVsActual = [
  { outcome: 'Home Win', expected: 42.5, actual: 41.8 },
  { outcome: 'Draw', expected: 26.3, actual: 27.1 },
  { outcome: 'Away Win', expected: 31.2, actual: 31.1 },
];

const leagues = ['All Leagues', 'Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1'];
const timeWindows = ['Last 3 months', 'Last 6 months', 'Last 12 months', 'All time'];

export default function Calibration() {
  const [selectedLeague, setSelectedLeague] = useState('All Leagues');
  const [selectedTimeWindow, setSelectedTimeWindow] = useState('Last 12 months');

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Calibration & Validation</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Model performance and reliability metrics
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedLeague} onValueChange={setSelectedLeague}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select league" />
            </SelectTrigger>
            <SelectContent>
              {leagues.map(league => (
                <SelectItem key={league} value={league}>{league}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={selectedTimeWindow} onValueChange={setSelectedTimeWindow}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Time window" />
            </SelectTrigger>
            <SelectContent>
              {timeWindows.map(window => (
                <SelectItem key={window} value={window}>{window}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Calibration measures how well predicted probabilities match observed outcomes. 
          A well-calibrated model should have points close to the diagonal line.
        </AlertDescription>
      </Alert>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Reliability Curve */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Reliability Curve</CardTitle>
            <CardDescription>
              Predicted probability vs observed frequency
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={reliabilityCurve} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis 
                    dataKey="predictedProbability" 
                    tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                    className="text-xs"
                  />
                  <YAxis 
                    tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                    className="text-xs"
                  />
                  <Tooltip 
                    formatter={(value: number, name: string) => [
                      `${(value * 100).toFixed(1)}%`,
                      name === 'observedFrequency' ? 'Observed' : 'Predicted'
                    ]}
                    labelFormatter={(label) => `Predicted: ${(label * 100).toFixed(0)}%`}
                  />
                  <ReferenceLine 
                    segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} 
                    stroke="hsl(var(--muted-foreground))" 
                    strokeDasharray="5 5"
                    strokeOpacity={0.5}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="observedFrequency" 
                    stroke="hsl(var(--chart-1))" 
                    strokeWidth={2}
                    dot={{ fill: 'hsl(var(--chart-1))', strokeWidth: 0, r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="text-xs text-muted-foreground mt-4 text-center">
              Diagonal line represents perfect calibration. Sample sizes range from {Math.min(...reliabilityCurve.map(d => d.sampleSize))} to {Math.max(...reliabilityCurve.map(d => d.sampleSize))} observations per bucket.
            </p>
          </CardContent>
        </Card>

        {/* Brier Score Trend */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Brier Score Trend</CardTitle>
            <CardDescription>
              Rolling accuracy score over time (lower is better)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={brierScoreTrend} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis 
                    dataKey="date" 
                    className="text-xs"
                  />
                  <YAxis 
                    domain={[0.15, 0.25]}
                    tickFormatter={(v) => v.toFixed(2)}
                    className="text-xs"
                  />
                  <Tooltip 
                    formatter={(value: number) => [value.toFixed(3), 'Brier Score']}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="score" 
                    stroke="hsl(var(--chart-2))" 
                    strokeWidth={2}
                    dot={{ fill: 'hsl(var(--chart-2))', strokeWidth: 0, r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="text-xs text-muted-foreground mt-4 text-center">
              Brier Score measures overall probability accuracy. Values typically range from 0.18 to 0.22 for football predictions.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Expected vs Actual */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Expected vs Actual Outcomes</CardTitle>
          <CardDescription>
            Comparison of predicted and observed outcome frequencies
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={expectedVsActual} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="outcome" className="text-xs" />
                <YAxis tickFormatter={(v) => `${v}%`} className="text-xs" />
                <Tooltip formatter={(value: number) => [`${value.toFixed(1)}%`]} />
                <Legend />
                <Bar dataKey="expected" name="Expected %" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
                <Bar dataKey="actual" name="Actual %" fill="hsl(var(--chart-3))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
