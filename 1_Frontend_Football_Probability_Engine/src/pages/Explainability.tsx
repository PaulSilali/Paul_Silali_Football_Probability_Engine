import { Info, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useState } from 'react';
import type { FeatureContribution } from '@/types';

// Mock data
const fixtureContributions: (FeatureContribution & { homeTeam: string; awayTeam: string })[] = [
  {
    fixtureId: '1',
    homeTeam: 'Arsenal',
    awayTeam: 'Chelsea',
    contributions: [
      { feature: 'Team Strength Differential', value: 8.5, description: 'Arsenal rated higher by ELO and form metrics' },
      { feature: 'Home Advantage', value: 4.2, description: 'Standard home advantage adjustment' },
      { feature: 'Market Odds Correction', value: -2.1, description: 'Model slightly above market consensus' },
      { feature: 'Draw Inflation', value: 0.0, description: 'No adjustment applied' },
      { feature: 'Recent Form', value: 3.8, description: 'Arsenal in better recent form' },
    ],
  },
  {
    fixtureId: '2',
    homeTeam: 'Liverpool',
    awayTeam: 'Man City',
    contributions: [
      { feature: 'Team Strength Differential', value: -5.2, description: 'Man City rated higher overall' },
      { feature: 'Home Advantage', value: 4.8, description: 'Liverpool strong at Anfield' },
      { feature: 'Market Odds Correction', value: 1.4, description: 'Model slightly below market consensus' },
      { feature: 'Draw Inflation', value: 2.3, description: 'Close match adjustment' },
      { feature: 'Recent Form', value: -1.8, description: 'Man City in better recent form' },
    ],
  },
  {
    fixtureId: '3',
    homeTeam: 'Man United',
    awayTeam: 'Tottenham',
    contributions: [
      { feature: 'Team Strength Differential', value: 3.2, description: 'Man United rated slightly higher' },
      { feature: 'Home Advantage', value: 3.9, description: 'Standard home advantage adjustment' },
      { feature: 'Market Odds Correction', value: -0.8, description: 'Model close to market consensus' },
      { feature: 'Draw Inflation', value: 1.5, description: 'Moderate draw inflation' },
      { feature: 'Recent Form', value: 1.2, description: 'Slightly better recent form for home team' },
    ],
  },
];

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
  const [selectedFixture, setSelectedFixture] = useState(fixtureContributions[0].fixtureId);
  
  const currentFixture = fixtureContributions.find(f => f.fixtureId === selectedFixture) || fixtureContributions[0];
  const maxContribution = Math.max(...currentFixture.contributions.map(c => Math.abs(c.value)));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Model Explainability</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Feature contributions to probability estimates
          </p>
        </div>
        <Select value={selectedFixture} onValueChange={setSelectedFixture}>
          <SelectTrigger className="w-[250px]">
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
    </div>
  );
}
