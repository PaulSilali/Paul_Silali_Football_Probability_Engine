import React, { useState, useEffect } from 'react';
import { AlertTriangle, Save, X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Slider } from '@/components/ui/slider';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/services/api';

interface InjuryInputProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  fixtureId: number;
  teamId: number;
  teamName: string;
  isHome: boolean;
  onSuccess?: () => void;
}

export function InjuryInput({
  open,
  onOpenChange,
  fixtureId,
  teamId,
  teamName,
  isHome,
  onSuccess
}: InjuryInputProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [loadingExisting, setLoadingExisting] = useState(false);
  
  // Form state
  const [keyPlayersMissing, setKeyPlayersMissing] = useState<number>(0);
  const [injurySeverity, setInjurySeverity] = useState<number[]>([0.5]);
  const [attackersMissing, setAttackersMissing] = useState<number>(0);
  const [midfieldersMissing, setMidfieldersMissing] = useState<number>(0);
  const [defendersMissing, setDefendersMissing] = useState<number>(0);
  const [goalkeepersMissing, setGoalkeepersMissing] = useState<number>(0);
  const [notes, setNotes] = useState<string>('');

  // Load existing injury data when dialog opens
  useEffect(() => {
    if (open && fixtureId && teamId) {
      loadExistingInjuries();
    }
  }, [open, fixtureId, teamId]);

  const loadExistingInjuries = async () => {
    setLoadingExisting(true);
    try {
      const response = await apiClient.getInjuries(fixtureId, teamId);
      if (response.success && response.data) {
        const data = response.data;
        setKeyPlayersMissing(data.key_players_missing || 0);
        setInjurySeverity([data.injury_severity || 0.5]);
        setAttackersMissing(data.attackers_missing || 0);
        setMidfieldersMissing(data.midfielders_missing || 0);
        setDefendersMissing(data.defenders_missing || 0);
        setGoalkeepersMissing(data.goalkeepers_missing || 0);
        setNotes(data.notes || '');
      }
    } catch (error: any) {
      // No existing injuries is fine - start with empty form
      console.debug('No existing injuries found:', error);
    } finally {
      setLoadingExisting(false);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const response = await apiClient.recordInjuries({
        team_id: teamId,
        fixture_id: fixtureId,
        key_players_missing: keyPlayersMissing > 0 ? keyPlayersMissing : undefined,
        injury_severity: injurySeverity[0] > 0 ? injurySeverity[0] : undefined,
        attackers_missing: attackersMissing > 0 ? attackersMissing : undefined,
        midfielders_missing: midfieldersMissing > 0 ? midfieldersMissing : undefined,
        defenders_missing: defendersMissing > 0 ? defendersMissing : undefined,
        goalkeepers_missing: goalkeepersMissing > 0 ? goalkeepersMissing : undefined,
        notes: notes.trim() || undefined,
      });

      if (response.success) {
        toast({
          title: "Injuries recorded",
          description: `Injury data saved for ${teamName}`,
        });
        onSuccess?.();
        onOpenChange(false);
      } else {
        throw new Error(response.message || 'Failed to record injuries');
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || 'Failed to record injuries',
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const calculateSeverityFromPositions = () => {
    // Auto-calculate severity if positions are filled but severity not set
    if (injurySeverity[0] === 0.5 && (attackersMissing > 0 || midfieldersMissing > 0 || defendersMissing > 0 || goalkeepersMissing > 0)) {
      const totalImpact = 
        goalkeepersMissing * 1.0 +
        keyPlayersMissing * 0.8 +
        attackersMissing * 0.3 +
        midfieldersMissing * 0.4 +
        defendersMissing * 0.3;
      const calculatedSeverity = Math.min(1.0, totalImpact / 5.0);
      setInjurySeverity([calculatedSeverity]);
    }
  };

  useEffect(() => {
    calculateSeverityFromPositions();
  }, [attackersMissing, midfieldersMissing, defendersMissing, goalkeepersMissing, keyPlayersMissing]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl glass-card-elevated max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-500" />
            Record Injuries: {teamName}
          </DialogTitle>
          <DialogDescription>
            Record injury data for {isHome ? 'home' : 'away'} team. This will adjust team strength calculations.
          </DialogDescription>
        </DialogHeader>

        {loadingExisting ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <span className="ml-2">Loading existing injury data...</span>
          </div>
        ) : (
          <div className="space-y-6 py-4">
            <Alert className="border-blue-200 bg-blue-50">
              <AlertTriangle className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-sm text-blue-900">
                Injury data adjusts team strength calculations. Leave fields empty if no injuries.
              </AlertDescription>
            </Alert>

            {/* Quick Input: Key Players Missing */}
            <div className="space-y-2">
              <Label htmlFor="key-players">Key Players Missing</Label>
              <Input
                id="key-players"
                type="number"
                min="0"
                max="10"
                value={keyPlayersMissing || ''}
                onChange={(e) => setKeyPlayersMissing(parseInt(e.target.value) || 0)}
                placeholder="e.g., 2"
                className="bg-background/50"
              />
              <p className="text-xs text-muted-foreground">
                Number of key/star players missing due to injury
              </p>
            </div>

            {/* Injury Severity Slider */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="severity">Injury Severity</Label>
                <span className="text-sm font-medium text-primary">
                  {(injurySeverity[0] * 100).toFixed(0)}%
                </span>
              </div>
              <Slider
                id="severity"
                min={0}
                max={1}
                step={0.01}
                value={injurySeverity}
                onValueChange={setInjurySeverity}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>None (0%)</span>
                <span>Moderate (50%)</span>
                <span>Critical (100%)</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Overall impact of injuries on team strength (0.0 = no impact, 1.0 = critical)
              </p>
            </div>

            {/* Position-Specific Injuries */}
            <div className="space-y-4">
              <Label className="text-base font-semibold">Position-Specific Injuries (Optional)</Label>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="attackers">Attackers Missing</Label>
                  <Input
                    id="attackers"
                    type="number"
                    min="0"
                    max="5"
                    value={attackersMissing || ''}
                    onChange={(e) => setAttackersMissing(parseInt(e.target.value) || 0)}
                    placeholder="0"
                    className="bg-background/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="midfielders">Midfielders Missing</Label>
                  <Input
                    id="midfielders"
                    type="number"
                    min="0"
                    max="5"
                    value={midfieldersMissing || ''}
                    onChange={(e) => setMidfieldersMissing(parseInt(e.target.value) || 0)}
                    placeholder="0"
                    className="bg-background/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="defenders">Defenders Missing</Label>
                  <Input
                    id="defenders"
                    type="number"
                    min="0"
                    max="5"
                    value={defendersMissing || ''}
                    onChange={(e) => setDefendersMissing(parseInt(e.target.value) || 0)}
                    placeholder="0"
                    className="bg-background/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="goalkeepers">Goalkeepers Missing</Label>
                  <Input
                    id="goalkeepers"
                    type="number"
                    min="0"
                    max="2"
                    value={goalkeepersMissing || ''}
                    onChange={(e) => setGoalkeepersMissing(parseInt(e.target.value) || 0)}
                    placeholder="0"
                    className="bg-background/50"
                  />
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Position-specific injuries help calculate overall severity more accurately
              </p>
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label htmlFor="notes">Notes (Optional)</Label>
              <Textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g., Star striker injured, expected return in 2 weeks..."
                rows={3}
                className="bg-background/50"
              />
            </div>

            {/* Impact Preview */}
            {(keyPlayersMissing > 0 || injurySeverity[0] > 0 || attackersMissing > 0 || midfieldersMissing > 0 || defendersMissing > 0 || goalkeepersMissing > 0) && (
              <Alert className="border-orange-200 bg-orange-50">
                <AlertTriangle className="h-4 w-4 text-orange-600" />
                <AlertDescription className="text-sm text-orange-900">
                  <strong>Impact:</strong> Team strength will be reduced by approximately{' '}
                  <strong>{((injurySeverity[0] || 0) * 15).toFixed(1)}%</strong> due to injuries.
                  {injurySeverity[0] > 0.7 && (
                    <span className="block mt-1 font-semibold">
                      ⚠️ Critical injuries detected - significant impact expected
                    </span>
                  )}
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            <X className="h-4 w-4 mr-2" />
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={loading}
            className="btn-glow"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Injuries
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

