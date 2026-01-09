/**
 * Section 2: Probability Output
 * 
 * Display raw calibrated probabilities clearly and honestly.
 * No "highlighted winners" or gambling language.
 */

import React from 'react';
import { AlertCircle, Info } from 'lucide-react';
import { useAppStore } from '../../store';
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
  Alert,
  Badge,
  Tooltip,
} from '../ui';
import {
  formatProbability,
  formatEntropy,
  PROBABILITY_SET_METADATA,
  calculateJackpotWinProbability,
} from '../../utils';

export function ProbabilityOutput() {
  const { activePrediction, selectedSets } = useAppStore();
  
  if (!activePrediction) {
    return (
      <Card>
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 text-slate-400 mx-auto mb-4" />
          <p className="text-slate-600">No active prediction. Generate predictions from fixture input.</p>
        </div>
      </Card>
    );
  }
  
  const { fixtures, probabilitySets, confidenceFlags, modelVersion, createdAt } = activePrediction;
  
  // Use the first selected set, or default to balanced
  const primarySetId = selectedSets[0] || 'B_balanced';
  const primaryProbabilities = probabilitySets[primarySetId];
  
  if (!primaryProbabilities) {
    return (
      <Card>
        <Alert variant="error">
          Selected probability set not available in prediction results.
        </Alert>
      </Card>
    );
  }
  
  const setMetadata = PROBABILITY_SET_METADATA[primarySetId];
  const overallWinProbability = calculateJackpotWinProbability(primaryProbabilities);
  
  return (
    <div className="space-y-6">
      {/* Header Card */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle>Probability Output</CardTitle>
              <CardDescription>
                Calibrated probabilities for {fixtures.length} fixtures using {setMetadata.name}
              </CardDescription>
            </div>
            <div className="text-right text-sm text-slate-600">
              <p>Model: {modelVersion}</p>
              <p>Generated: {new Date(createdAt).toLocaleString()}</p>
            </div>
          </div>
        </CardHeader>
        
        <Alert variant="info">
          <div className="flex items-start gap-2">
            <Info className="h-5 w-5 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium mb-1">Probability Interpretation</p>
              <p>
                Values represent model-implied likelihoods, not certainties.
                A 60% probability means the model estimates this outcome would occur
                approximately 6 times out of 10 in similar circumstances.
              </p>
            </div>
          </div>
        </Alert>
      </Card>
      
      {/* Overall Jackpot Statistics */}
      <Card>
        <h4 className="text-sm font-medium text-slate-900 mb-4">Jackpot Statistics</h4>
        <div className="grid grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-slate-600 mb-1">Overall Win Probability</p>
            <p className="text-2xl font-semibold text-slate-900">
              {formatProbability(overallWinProbability, 4)}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              (1 in {Math.round(1 / overallWinProbability).toLocaleString()})
            </p>
          </div>
          <div>
            <p className="text-sm text-slate-600 mb-1">Probability Set</p>
            <p className="text-lg font-medium text-slate-900">{setMetadata.shortName}</p>
            <Badge variant="default" className="mt-1">
              {setMetadata.riskProfile}
            </Badge>
          </div>
          <div>
            <p className="text-sm text-slate-600 mb-1">Fixtures</p>
            <p className="text-2xl font-semibold text-slate-900">{fixtures.length}</p>
          </div>
        </div>
      </Card>
      
      {/* Probabilities Table */}
      <Card padding={false}>
        <div className="p-6 pb-4">
          <h4 className="text-sm font-medium text-slate-700">Match-by-Match Probabilities</h4>
          <p className="text-sm text-slate-600 mt-1">
            All probabilities sum to 100% per fixture. No outcomes are highlighted or recommended.
          </p>
        </div>
        
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>#</TableHead>
              <TableHead>Fixture</TableHead>
              <TableHead className="text-center">Home Win</TableHead>
              <TableHead className="text-center">Draw</TableHead>
              <TableHead className="text-center">Away Win</TableHead>
              <TableHead className="text-center">Entropy</TableHead>
              <TableHead className="text-center">Confidence</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {fixtures.map((fixture, index) => {
              const probs = primaryProbabilities[index];
              const confidence = confidenceFlags?.[index] || 'medium';
              
              // Validation: Ensure probabilities sum to ~1.0
              const sum = probs.home + probs.draw + probs.away;
              const isValid = Math.abs(sum - 1.0) < 0.001;
              
              return (
                <TableRow key={fixture.id}>
                  <TableCell className="text-slate-500">{index + 1}</TableCell>
                  <TableCell>
                    <div className="font-medium text-slate-900">
                      {fixture.homeTeam} vs {fixture.awayTeam}
                    </div>
                    {fixture.odds && (
                      <div className="text-xs text-slate-500 mt-1">
                        Market: {fixture.odds.home.toFixed(2)} / {fixture.odds.draw.toFixed(2)} / {fixture.odds.away.toFixed(2)}
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="text-center">
                    <div className="font-mono text-sm">
                      {formatProbability(probs.home)}
                    </div>
                  </TableCell>
                  <TableCell className="text-center">
                    <div className="font-mono text-sm">
                      {formatProbability(probs.draw)}
                    </div>
                  </TableCell>
                  <TableCell className="text-center">
                    <div className="font-mono text-sm">
                      {formatProbability(probs.away)}
                    </div>
                  </TableCell>
                  <TableCell className="text-center">
                    <Tooltip content="Higher entropy indicates greater uncertainty">
                      <span className="font-mono text-sm text-slate-600">
                        {formatEntropy(probs.entropy)}
                      </span>
                    </Tooltip>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge
                      variant={
                        confidence === 'high' ? 'success' :
                        confidence === 'low' ? 'warning' :
                        'default'
                      }
                    >
                      {confidence}
                    </Badge>
                    {!isValid && (
                      <Tooltip content={`Sum: ${sum.toFixed(4)} (should be 1.0000)`}>
                        <AlertCircle className="h-4 w-4 text-red-500 inline ml-2" />
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        
        {/* Summary Row */}
        <div className="p-6 pt-4 border-t border-slate-200 bg-slate-50">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-4">
              <span className="text-slate-600">Average Entropy:</span>
              <span className="font-mono font-medium">
                {formatEntropy(
                  primaryProbabilities.reduce((sum, p) => sum + p.entropy, 0) / primaryProbabilities.length
                )}
              </span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-slate-600">Compound Win Probability:</span>
              <span className="font-mono font-semibold text-lg">
                {formatProbability(overallWinProbability, 4)}
              </span>
            </div>
          </div>
        </div>
      </Card>
      
      {/* Probability Distribution Visualization */}
      <Card>
        <CardTitle>Probability Distribution</CardTitle>
        <div className="mt-4 space-y-3">
          {fixtures.map((fixture, index) => {
            const probs = primaryProbabilities[index];
            
            return (
              <div key={fixture.id}>
                <div className="text-sm text-slate-700 mb-1.5">
                  {index + 1}. {fixture.homeTeam} vs {fixture.awayTeam}
                </div>
                <div className="flex h-8 rounded overflow-hidden border border-slate-200">
                  <Tooltip content={`Home: ${formatProbability(probs.home)}`}>
                    <div
                      className="bg-slate-400 flex items-center justify-center text-xs text-white font-medium"
                      style={{ width: `${probs.home * 100}%` }}
                    >
                      {probs.home > 0.15 && formatProbability(probs.home)}
                    </div>
                  </Tooltip>
                  <Tooltip content={`Draw: ${formatProbability(probs.draw)}`}>
                    <div
                      className="bg-slate-500 flex items-center justify-center text-xs text-white font-medium"
                      style={{ width: `${probs.draw * 100}%` }}
                    >
                      {probs.draw > 0.15 && formatProbability(probs.draw)}
                    </div>
                  </Tooltip>
                  <Tooltip content={`Away: ${formatProbability(probs.away)}`}>
                    <div
                      className="bg-slate-600 flex items-center justify-center text-xs text-white font-medium"
                      style={{ width: `${probs.away * 100}%` }}
                    >
                      {probs.away > 0.15 && formatProbability(probs.away)}
                    </div>
                  </Tooltip>
                </div>
              </div>
            );
          })}
        </div>
        <div className="mt-4 flex items-center gap-6 text-xs text-slate-600">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-slate-400 rounded" />
            <span>Home Win</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-slate-500 rounded" />
            <span>Draw</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-slate-600 rounded" />
            <span>Away Win</span>
          </div>
        </div>
      </Card>
      
      {/* Warnings */}
      {activePrediction.warnings && activePrediction.warnings.length > 0 && (
        <Card>
          <h4 className="text-sm font-medium text-slate-900 mb-3">Prediction Warnings</h4>
          <div className="space-y-2">
            {activePrediction.warnings.map((warning, idx) => (
              <Alert
                key={idx}
                variant={warning.severity === 'error' ? 'error' : 'warning'}
              >
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium">{warning.type.replace(/_/g, ' ')}</p>
                    <p className="text-sm mt-1">{warning.message}</p>
                  </div>
                </div>
              </Alert>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
