/**
 * Section 3: Probability Sets Comparison
 * 
 * Enable multiple bets per jackpot using different probability philosophies.
 * Side-by-side comparison with clear methodology explanations.
 */

import React, { useState } from 'react';
import { Info, Eye, EyeOff } from 'lucide-react';
import { useAppStore } from '../../store';
import type { ProbabilitySetId, MatchProbabilities } from '../../types';
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
  Tooltip,
} from '../ui';
import {
  formatProbability,
  formatEntropy,
  PROBABILITY_SET_METADATA,
  calculateDivergence,
} from '../../utils';

export function ProbabilitySetsComparison() {
  const {
    activePrediction,
    selectedSets,
    toggleProbabilitySet,
    selectAllSets,
    selectDefaultSets,
  } = useAppStore();
  
  const [showDifferences, setShowDifferences] = useState(false);
  const [referenceSet, setReferenceSet] = useState<ProbabilitySetId>('B_balanced');
  
  if (!activePrediction) {
    return (
      <Card>
        <div className="text-center py-12 text-slate-600">
          No active prediction available.
        </div>
      </Card>
    );
  }
  
  const { fixtures, probabilitySets } = activePrediction;
  const availableSets = Object.keys(probabilitySets) as ProbabilitySetId[];
  
  // ============================================================================
  // HELPERS
  // ============================================================================
  
  const calculateDifference = (
    value: number,
    reference: number,
    asPercentage: boolean = false
  ): string => {
    const diff = value - reference;
    const sign = diff > 0 ? '+' : '';
    return asPercentage
      ? `${sign}${formatProbability(diff)}`
      : `${sign}${(diff * 100).toFixed(2)}pp`;
  };
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <CardTitle>Probability Sets Comparison</CardTitle>
          <CardDescription>
            Compare multiple probability perspectives to inform different betting strategies.
            Each set represents a distinct methodological approach with different risk profiles.
          </CardDescription>
        </CardHeader>
        
        <Alert variant="info">
          <div className="flex items-start gap-2">
            <Info className="h-5 w-5 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium mb-1">Multiple Perspectives, Not Multiple Truths</p>
              <p>
                Different probability sets reflect different modeling assumptions and market integration levels.
                None is definitively "correct" — choose based on your risk tolerance and beliefs about market efficiency.
              </p>
            </div>
          </div>
        </Alert>
      </Card>
      
      {/* Set Selection Controls */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-sm font-medium text-slate-700">Active Probability Sets</h4>
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" onClick={selectDefaultSets}>
              Default (A, B, C)
            </Button>
            <Button size="sm" variant="ghost" onClick={selectAllSets}>
              Show All
            </Button>
          </div>
        </div>
        
        <div className="flex flex-wrap gap-2">
          {availableSets.map((setId) => {
            const metadata = PROBABILITY_SET_METADATA[setId];
            const isSelected = selectedSets.includes(setId);
            
            return (
              <button
                key={setId}
                onClick={() => toggleProbabilitySet(setId)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  isSelected
                    ? 'bg-slate-700 text-white'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                <div className="flex items-center gap-2">
                  {isSelected ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                  {metadata.shortName}
                </div>
              </button>
            );
          })}
        </div>
      </Card>
      
      {/* Set Methodology Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {selectedSets.map((setId) => {
          const metadata = PROBABILITY_SET_METADATA[setId];
          
          return (
            <Card key={setId} className="border-l-4" style={{ borderLeftColor: metadata.color }}>
              <div className="flex items-start justify-between mb-3">
                <h4 className="text-sm font-semibold text-slate-900">{metadata.name}</h4>
                <Badge variant="default">{metadata.riskProfile}</Badge>
              </div>
              <p className="text-sm text-slate-600 mb-3">{metadata.description}</p>
              <div className="pt-3 border-t border-slate-200">
                <p className="text-xs text-slate-500 mb-1">Methodology:</p>
                <p className="text-xs text-slate-700">{metadata.methodology}</p>
              </div>
              <div className="pt-2">
                <p className="text-xs text-slate-500 mb-1">Use Case:</p>
                <p className="text-xs text-slate-700">{metadata.useCase}</p>
              </div>
            </Card>
          );
        })}
      </div>
      
      {/* Comparison Controls */}
      <Card>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={showDifferences}
                onChange={(e) => setShowDifferences(e.target.checked)}
                className="rounded border-slate-300 text-slate-700 focus:ring-slate-500"
              />
              <span className="text-sm text-slate-700">Show differences vs reference</span>
            </label>
            
            {showDifferences && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-600">Reference:</span>
                <select
                  value={referenceSet}
                  onChange={(e) => setReferenceSet(e.target.value as ProbabilitySetId)}
                  className="text-sm border-slate-300 rounded px-2 py-1"
                >
                  {selectedSets.map((setId) => (
                    <option key={setId} value={setId}>
                      {PROBABILITY_SET_METADATA[setId].shortName}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>
      </Card>
      
      {/* Comparison Table */}
      {selectedSets.length > 0 ? (
        <div className="space-y-6">
          {fixtures.map((fixture, fixtureIndex) => {
            const referenceProbabilities = probabilitySets[referenceSet]?.[fixtureIndex];
            
            return (
              <Card key={fixture.id} padding={false}>
                <div className="p-4 bg-slate-50 border-b border-slate-200">
                  <h4 className="font-medium text-slate-900">
                    {fixtureIndex + 1}. {fixture.homeTeam} vs {fixture.awayTeam}
                  </h4>
                  {fixture.odds && (
                    <p className="text-sm text-slate-600 mt-1">
                      Market Odds: {fixture.odds.home.toFixed(2)} / {fixture.odds.draw.toFixed(2)} / {fixture.odds.away.toFixed(2)}
                    </p>
                  )}
                </div>
                
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Set</TableHead>
                      <TableHead className="text-center">Home Win</TableHead>
                      <TableHead className="text-center">Draw</TableHead>
                      <TableHead className="text-center">Away Win</TableHead>
                      <TableHead className="text-center">Entropy</TableHead>
                      {showDifferences && (
                        <TableHead className="text-center">Divergence</TableHead>
                      )}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {selectedSets.map((setId) => {
                      const probs = probabilitySets[setId]?.[fixtureIndex];
                      if (!probs) return null;
                      
                      const metadata = PROBABILITY_SET_METADATA[setId];
                      const divergence = referenceProbabilities
                        ? calculateDivergence(probs, referenceProbabilities)
                        : 0;
                      
                      return (
                        <TableRow key={setId}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <div
                                className="w-3 h-3 rounded"
                                style={{ backgroundColor: metadata.color }}
                              />
                              <span className="font-medium">{metadata.shortName}</span>
                            </div>
                          </TableCell>
                          <TableCell className="text-center">
                            <div className="font-mono text-sm">
                              {formatProbability(probs.home)}
                            </div>
                            {showDifferences && referenceProbabilities && (
                              <div className="text-xs text-slate-500 mt-1">
                                {calculateDifference(probs.home, referenceProbabilities.home)}
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="text-center">
                            <div className="font-mono text-sm">
                              {formatProbability(probs.draw)}
                            </div>
                            {showDifferences && referenceProbabilities && (
                              <div className="text-xs text-slate-500 mt-1">
                                {calculateDifference(probs.draw, referenceProbabilities.draw)}
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="text-center">
                            <div className="font-mono text-sm">
                              {formatProbability(probs.away)}
                            </div>
                            {showDifferences && referenceProbabilities && (
                              <div className="text-xs text-slate-500 mt-1">
                                {calculateDifference(probs.away, referenceProbabilities.away)}
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="text-center">
                            <span className="font-mono text-sm text-slate-600">
                              {formatEntropy(probs.entropy)}
                            </span>
                          </TableCell>
                          {showDifferences && (
                            <TableCell className="text-center">
                              <Tooltip content="Jensen-Shannon divergence from reference set">
                                <span className="font-mono text-sm text-slate-600">
                                  {divergence.toFixed(3)}
                                </span>
                              </Tooltip>
                            </TableCell>
                          )}
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <div className="text-center py-8 text-slate-600">
            No probability sets selected. Choose at least one set to view comparisons.
          </div>
        </Card>
      )}
      
      {/* Guidance */}
      <Card>
        <CardTitle>Set Selection Guidance</CardTitle>
        <div className="mt-4 space-y-3">
          <div className="p-4 bg-slate-50 rounded-md">
            <p className="font-medium text-sm text-slate-900 mb-2">New to jackpot betting?</p>
            <p className="text-sm text-slate-700">
              Start with Set B (Market-Aware Balanced). It provides a well-calibrated blend of
              statistical modeling and market intelligence.
            </p>
          </div>
          
          <div className="p-4 bg-slate-50 rounded-md">
            <p className="font-medium text-sm text-slate-900 mb-2">Looking for contrarian value?</p>
            <p className="text-sm text-slate-700">
              Try Set A (Pure Model). It disregards market odds entirely and relies on the statistical
              model's assessment of team strengths.
            </p>
          </div>
          
          <div className="p-4 bg-slate-50 rounded-md">
            <p className="font-medium text-sm text-slate-900 mb-2">Want conservative, market-aligned picks?</p>
            <p className="text-sm text-slate-700">
              Use Set C (Market-Dominant). It leans heavily on market consensus with minor model adjustments.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
