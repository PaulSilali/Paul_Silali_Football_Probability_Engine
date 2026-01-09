/**
 * Section 1: Jackpot Input
 * 
 * Professional interface for defining jackpot fixtures
 * without narrative data or gambling language.
 */

import React, { useState } from 'react';
import { Plus, Trash2, Upload, Download } from 'lucide-react';
import { useAppStore } from '../../store';
import { generatePrediction } from '../../api';
import type { Fixture, MarketOdds } from '../../types';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  Button,
  Input,
  Alert,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '../ui';
import { validateOdds, validateTeamName, isFixtureComplete } from '../../utils';

export function JackpotInput() {
  const {
    currentJackpot,
    addFixture,
    removeFixture,
    updateFixture,
    clearJackpot,
    setPrediction,
    setLoading,
    setError,
    isLoading,
  } = useAppStore();
  
  const [bulkInput, setBulkInput] = useState('');
  const [showBulkInput, setShowBulkInput] = useState(false);
  
  const fixtures = currentJackpot?.fixtures || [];
  
  // ============================================================================
  // HANDLERS
  // ============================================================================
  
  const handleAddFixture = () => {
    const newFixture: Fixture = {
      id: `fixture-${Date.now()}-${Math.random()}`,
      homeTeam: '',
      awayTeam: '',
      odds: null,
    };
    addFixture(newFixture);
  };
  
  const handleUpdateTeams = (
    fixtureId: string,
    field: 'homeTeam' | 'awayTeam',
    value: string
  ) => {
    updateFixture(fixtureId, { [field]: value });
  };
  
  const handleUpdateOdds = (
    fixtureId: string,
    field: keyof MarketOdds,
    value: string
  ) => {
    const fixture = fixtures.find(f => f.id === fixtureId);
    if (!fixture) return;
    
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return;
    
    const updatedOdds: MarketOdds = {
      home: fixture.odds?.home || 2.0,
      draw: fixture.odds?.draw || 3.0,
      away: fixture.odds?.away || 3.5,
      ...(fixture.odds || {}),
      [field]: numValue,
    };
    
    updateFixture(fixtureId, { odds: updatedOdds });
  };
  
  const handleRemoveFixture = (fixtureId: string) => {
    removeFixture(fixtureId);
  };
  
  const handleBulkPaste = () => {
    const lines = bulkInput.trim().split('\n');
    const newFixtures: Fixture[] = [];
    
    for (const line of lines) {
      const parts = line.split(/\t|,/).map(p => p.trim());
      if (parts.length < 5) continue;
      
      const [homeTeam, awayTeam, homeOdds, drawOdds, awayOdds] = parts;
      const parsedOdds = {
        home: parseFloat(homeOdds),
        draw: parseFloat(drawOdds),
        away: parseFloat(awayOdds),
      };
      
      if (
        validateTeamName(homeTeam) &&
        validateTeamName(awayTeam) &&
        validateOdds(parsedOdds.home) &&
        validateOdds(parsedOdds.draw) &&
        validateOdds(parsedOdds.away)
      ) {
        newFixtures.push({
          id: `fixture-${Date.now()}-${Math.random()}`,
          homeTeam,
          awayTeam,
          odds: parsedOdds,
        });
      }
    }
    
    newFixtures.forEach(f => addFixture(f));
    setBulkInput('');
    setShowBulkInput(false);
  };
  
  const handleGeneratePredictions = async () => {
    if (!currentJackpot) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const prediction = await generatePrediction(currentJackpot);
      setPrediction(prediction);
      
      // Switch to output section
      useAppStore.getState().setActiveSection('output');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate predictions');
    } finally {
      setLoading(false);
    }
  };
  
  const handleExportCSV = () => {
    const csv = [
      'Home Team,Away Team,Home Odds,Draw Odds,Away Odds',
      ...fixtures.map(f =>
        `${f.homeTeam},${f.awayTeam},${f.odds?.home || ''},${f.odds?.draw || ''},${f.odds?.away || ''}`
      ),
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `jackpot-fixtures-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };
  
  // ============================================================================
  // VALIDATION
  // ============================================================================
  
  const incompleteFixtures = fixtures.filter(f => !isFixtureComplete(f));
  const canGenerate = fixtures.length > 0 && incompleteFixtures.length === 0 && !isLoading;
  
  return (
    <div className="space-y-6">
      {/* Header Card with Disclaimer */}
      <Card>
        <CardHeader>
          <CardTitle>Jackpot Fixture Input</CardTitle>
          <CardDescription>
            Define fixtures and market odds. This system estimates probabilities based on statistical models and market data.
          </CardDescription>
        </CardHeader>
        
        <Alert variant="info">
          This system estimates probabilities. It does not provide betting advice.
          All outputs represent model-implied likelihoods, not certainties.
        </Alert>
      </Card>
      
      {/* Input Method Selection */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-sm font-medium text-slate-700">Input Method</h4>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowBulkInput(!showBulkInput)}
            >
              <Upload className="h-4 w-4 mr-2" />
              Bulk Paste
            </Button>
            {fixtures.length > 0 && (
              <>
                <Button variant="ghost" size="sm" onClick={handleExportCSV}>
                  <Download className="h-4 w-4 mr-2" />
                  Export CSV
                </Button>
                <Button variant="ghost" size="sm" onClick={clearJackpot}>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Clear All
                </Button>
              </>
            )}
          </div>
        </div>
        
        {/* Bulk Input Panel */}
        {showBulkInput && (
          <div className="mb-4 p-4 bg-slate-50 rounded-md">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Paste fixtures (one per line: Home Team, Away Team, Home Odds, Draw Odds, Away Odds)
            </label>
            <textarea
              className="w-full h-32 px-3 py-2 border border-slate-300 rounded-md text-sm font-mono"
              placeholder="Arsenal, Chelsea, 2.10, 3.40, 3.20&#10;Liverpool, Man United, 1.85, 3.60, 4.20"
              value={bulkInput}
              onChange={(e) => setBulkInput(e.target.value)}
            />
            <div className="mt-2 flex gap-2">
              <Button size="sm" onClick={handleBulkPaste}>
                Import Fixtures
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setBulkInput('');
                  setShowBulkInput(false);
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </Card>
      
      {/* Fixtures Table */}
      <Card padding={false}>
        <div className="p-6 pb-0">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-sm font-medium text-slate-700">
              Fixtures ({fixtures.length})
            </h4>
            <Button size="sm" onClick={handleAddFixture}>
              <Plus className="h-4 w-4 mr-2" />
              Add Fixture
            </Button>
          </div>
        </div>
        
        {fixtures.length === 0 ? (
          <div className="p-6 text-center text-slate-500">
            No fixtures added yet. Click "Add Fixture" to begin.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Home Team</TableHead>
                <TableHead>Away Team</TableHead>
                <TableHead>Home Odds</TableHead>
                <TableHead>Draw Odds</TableHead>
                <TableHead>Away Odds</TableHead>
                <TableHead>Status</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {fixtures.map((fixture, index) => {
                const isComplete = isFixtureComplete(fixture);
                
                return (
                  <TableRow key={fixture.id}>
                    <TableCell className="text-slate-500">
                      {index + 1}
                    </TableCell>
                    <TableCell>
                      <Input
                        type="text"
                        placeholder="Home team"
                        value={fixture.homeTeam}
                        onChange={(e) => handleUpdateTeams(fixture.id, 'homeTeam', e.target.value)}
                        className="min-w-[150px]"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="text"
                        placeholder="Away team"
                        value={fixture.awayTeam}
                        onChange={(e) => handleUpdateTeams(fixture.id, 'awayTeam', e.target.value)}
                        className="min-w-[150px]"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        step="0.01"
                        min="1.01"
                        placeholder="2.00"
                        value={fixture.odds?.home || ''}
                        onChange={(e) => handleUpdateOdds(fixture.id, 'home', e.target.value)}
                        className="w-20"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        step="0.01"
                        min="1.01"
                        placeholder="3.00"
                        value={fixture.odds?.draw || ''}
                        onChange={(e) => handleUpdateOdds(fixture.id, 'draw', e.target.value)}
                        className="w-20"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        step="0.01"
                        min="1.01"
                        placeholder="3.50"
                        value={fixture.odds?.away || ''}
                        onChange={(e) => handleUpdateOdds(fixture.id, 'away', e.target.value)}
                        className="w-20"
                      />
                    </TableCell>
                    <TableCell>
                      {isComplete ? (
                        <span className="text-xs text-emerald-600">✓ Complete</span>
                      ) : (
                        <span className="text-xs text-amber-600">Incomplete</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveFixture(fixture.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </Card>
      
      {/* Validation Warnings */}
      {incompleteFixtures.length > 0 && (
        <Alert variant="warning">
          {incompleteFixtures.length} fixture{incompleteFixtures.length > 1 ? 's' : ''} incomplete.
          Ensure all teams and odds are entered.
        </Alert>
      )}
      
      {/* Generate Button */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-900">
              Ready to generate probabilities
            </p>
            <p className="text-sm text-slate-600">
              {fixtures.length} fixture{fixtures.length !== 1 ? 's' : ''} defined
            </p>
          </div>
          <Button
            onClick={handleGeneratePredictions}
            disabled={!canGenerate}
            size="lg"
          >
            Generate Predictions →
          </Button>
        </div>
      </Card>
    </div>
  );
}
