import { Info, AlertCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageLayout } from '@/components/layouts/PageLayout';
import { ModernCard } from '@/components/ui/modern-card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useState, useEffect } from 'react';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/services/api';
import type { FeatureContribution } from '@/types';

function ContributionBar({ value, maxValue }: { value: number; maxValue: number }) {
  const percentage = Math.abs(value) / maxValue * 100;
  const isPositive = value > 0;
  
  return (
    <div className="flex items-center gap-3 h-6">
      <div className="w-24 text-right tabular-nums text-sm">
        <span className={isPositive ? 'text-chart-1' : 'text-chart-3'}>
          {isPositive ? '+' : ''}{value.toFixed(1)}
        </span>
      </div>
      <div className="flex-1 flex items-center h-full">
        <div className="w-full h-2 bg-muted rounded-full overflow-hidden flex">
          <div className="w-1/2 flex justify-end">
            {!isPositive && (
              <div 
                className="h-full bg-chart-3 rounded-l-full transition-all"
                style={{ width: `${percentage}%` }}
              />
            )}
          </div>
          <div className="w-px bg-border" />
          <div className="w-1/2">
            {isPositive && (
              <div 
                className="h-full bg-chart-1 rounded-r-full transition-all"
                style={{ width: `${percentage}%` }}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Explainability() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [jackpotId, setJackpotId] = useState<string>('');
  const [availableJackpots, setAvailableJackpots] = useState<Array<{ id: string; label: string }>>([]);
  const [fixtureContributions, setFixtureContributions] = useState<Array<FeatureContribution & { homeTeam: string; awayTeam: string }>>([]);
  const [selectedFixture, setSelectedFixture] = useState<string>('');

  // Load available jackpots
  useEffect(() => {
    const loadJackpots = async () => {
      try {
        const response = await apiClient.getAllSavedResults(100);
        if (response.success && response.data) {
          const jackpots = response.data.map((result: any) => ({
            id: result.jackpotId,
            label: `${result.jackpotId} - ${new Date(result.createdAt).toLocaleDateString()}`
          }));
          setAvailableJackpots(jackpots);
          if (jackpots.length > 0 && !jackpotId) {
            setJackpotId(jackpots[0].id);
          }
        }
      } catch (error: any) {
        console.error('Error loading jackpots:', error);
      }
    };
    loadJackpots();
  }, []);

  // Load feature contributions when jackpot is selected
  useEffect(() => {
    if (!jackpotId) return;
    
    const loadContributions = async () => {
      setLoading(true);
      try {
        const response = await apiClient.getFeatureContributions(jackpotId);
        if (response.success && response.data) {
          const contributions = response.data.map((item: any) => ({
            fixtureId: item.fixtureId,
            homeTeam: item.homeTeam,
            awayTeam: item.awayTeam,
            contributions: item.contributions.map((c: any) => ({
              feature: c.feature,
              value: c.value * 100, // Convert to percentage points
              description: c.description
            }))
          }));
          setFixtureContributions(contributions);
          if (contributions.length > 0 && !selectedFixture) {
            setSelectedFixture(contributions[0].fixtureId);
          }
        } else {
          toast({
            title: 'No data available',
            description: 'No feature contributions found for this jackpot. Calculate probabilities first.',
            variant: 'default'
          });
        }
      } catch (error: any) {
        toast({
          title: 'Error',
          description: error.message || 'Failed to load feature contributions',
          variant: 'destructive'
        });
      } finally {
        setLoading(false);
      }
    };
    
    loadContributions();
  }, [jackpotId, toast]);

  const currentFixture = fixtureContributions.find(f => f.fixtureId === selectedFixture);
  const maxContribution = currentFixture 
    ? Math.max(...currentFixture.contributions.map(c => Math.abs(c.value)))
    : 1;

  return (
    <PageLayout
      title="Model Explainability"
      description="Feature contributions to probability estimates"
      icon={<Info className="h-6 w-6" />}
    >
      <div className="space-y-4">
        {/* Jackpot Selection */}
        <div className="flex items-center gap-4">
          <Select value={jackpotId} onValueChange={setJackpotId}>
            <SelectTrigger className="w-[300px]">
              <SelectValue placeholder="Select jackpot" />
            </SelectTrigger>
            <SelectContent>
              {availableJackpots.map(j => (
                <SelectItem key={j.id} value={j.id}>
                  {j.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          {loading && (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          )}
        </div>

        {/* Fixture Selection */}
        {fixtureContributions.length > 0 && (
          <Select value={selectedFixture} onValueChange={setSelectedFixture}>
            <SelectTrigger className="w-[300px]">
              <SelectValue placeholder="Select fixture" />
            </SelectTrigger>
            <SelectContent>
              {fixtureContributions.map(f => (
                <SelectItem key={f.fixtureId} value={f.fixtureId}>
                  {f.homeTeam} vs {f.awayTeam}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      <Alert variant="default" className="border-muted bg-muted/30">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Important Disclaimer</AlertTitle>
        <AlertDescription>
          These values describe contribution to probability, not causation. 
          Feature contributions show how different factors affect the model's estimate, 
          but should not be interpreted as causal explanations for match outcomes.
        </AlertDescription>
      </Alert>

      {loading ? (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="ml-3 text-muted-foreground">Loading feature contributions...</p>
            </div>
          </CardContent>
        </Card>
      ) : currentFixture ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              {currentFixture.homeTeam} vs {currentFixture.awayTeam}
            </CardTitle>
            <CardDescription>
              Contribution of each feature to the home win probability estimate
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {currentFixture.contributions.map((contribution, index) => (
              <div key={index} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{contribution.feature}</span>
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Info className="h-3 w-3" />
                    {contribution.description}
                  </span>
                </div>
                <ContributionBar value={contribution.value} maxValue={maxContribution} />
              </div>
            ))}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="pt-6">
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>No Data Available</AlertTitle>
              <AlertDescription>
                {jackpotId 
                  ? 'No feature contributions found for this jackpot. Please calculate probabilities first.'
                  : 'Please select a jackpot to view feature contributions.'}
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-muted/30">
          <CardContent className="pt-6">
            <h4 className="font-medium text-sm mb-2">Reading the Chart</h4>
            <p className="text-xs text-muted-foreground">
              Positive values (blue, right) increase home win probability. 
              Negative values (gray, left) decrease it. 
              Bar length indicates relative impact magnitude.
            </p>
          </CardContent>
        </Card>
        <Card className="bg-muted/30">
          <CardContent className="pt-6">
            <h4 className="font-medium text-sm mb-2">Feature Independence</h4>
            <p className="text-xs text-muted-foreground">
              Contributions are calculated independently and may have interactions 
              not fully captured by this linear decomposition.
            </p>
          </CardContent>
        </Card>
        <Card className="bg-muted/30">
          <CardContent className="pt-6">
            <h4 className="font-medium text-sm mb-2">Base Probability</h4>
            <p className="text-xs text-muted-foreground">
              Contributions are relative to a baseline probability. 
              The sum of all contributions plus baseline equals the final estimate.
            </p>
          </CardContent>
        </Card>
      </div>
    </PageLayout>
  );
}
