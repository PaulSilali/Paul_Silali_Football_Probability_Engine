import { useState, useMemo } from 'react';
import { Calculator, TrendingDown, AlertTriangle, Info, Percent } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface FixtureSelection {
  id: string;
  homeTeam: string;
  awayTeam: string;
  selection: '1' | 'X' | '2';
  probability: number;
  odds: number;
}

interface AccumulatorCalculatorProps {
  fixtures: FixtureSelection[];
}

export function AccumulatorCalculator({ fixtures }: AccumulatorCalculatorProps) {
  const [stake, setStake] = useState(50); // Default 50 KSH
  const [currency, setCurrency] = useState<'KSH' | 'USD' | 'GBP'>('KSH');
  const [jackpotType, setJackpotType] = useState<'15' | '17'>('15'); // 15 or 17 games

  const calculations = useMemo(() => {
    if (fixtures.length === 0) {
      return {
        overallProbability: 0,
        combinedOdds: 1,
        potentialReturn: 0,
        expectedValue: 0,
        oneInX: 0,
        edgePercentage: 0,
      };
    }

    // Overall jackpot probability: multiply all individual probabilities
    const overallProbability = fixtures.reduce(
      (acc, f) => acc * (f.probability / 100),
      1
    );

    // Combined odds: multiply all odds
    const combinedOdds = fixtures.reduce((acc, f) => acc * f.odds, 1);

    // Potential return
    const potentialReturn = stake * combinedOdds;
    
    // Kenyan jackpot prize structure
    // 15 games: 15M KSH (if all correct), partial prizes for 13/15, 14/15
    // 17 games: 200M KSH (if all correct), partial prizes for 15/17, 16/17
    const getJackpotPrize = (correctCount: number, totalCount: number): number => {
      if (totalCount === 15) {
        if (correctCount === 15) return 15000000; // 15M KSH
        if (correctCount === 14) return 500000;   // 500K KSH
        if (correctCount === 13) return 50000;     // 50K KSH
        return 0;
      } else if (totalCount === 17) {
        if (correctCount === 17) return 200000000; // 200M KSH
        if (correctCount === 16) return 5000000;    // 5M KSH
        if (correctCount === 15) return 500000;     // 500K KSH
        return 0;
      }
      return 0;
    };
    
    // Calculate expected jackpot prize (simplified - assumes uniform distribution)
    // This is a rough estimate based on probability of getting N correct
    const expectedJackpotPrize = 0; // Would require more complex calculation
    
    // Convert currency
    const currencySymbol = currency === 'KSH' ? 'KSh' : currency === 'USD' ? '$' : '£';
    const currencyMultiplier = currency === 'KSH' ? 1 : currency === 'USD' ? 0.007 : 0.0055; // Approximate rates

    // Expected value: (probability * return) - stake
    const expectedValue = overallProbability * potentialReturn - stake;

    // 1 in X chance
    const oneInX = overallProbability > 0 ? Math.round(1 / overallProbability) : 0;

    // Edge: (fair odds - market odds) / market odds * 100
    const fairOdds = overallProbability > 0 ? 1 / overallProbability : 0;
    const edgePercentage = fairOdds > 0 
      ? ((combinedOdds - fairOdds) / fairOdds) * 100 
      : 0;

    return {
      overallProbability,
      combinedOdds,
      potentialReturn,
      expectedValue,
      oneInX,
      edgePercentage,
    };
  }, [fixtures, stake]);

  const probabilityColor = useMemo(() => {
    const p = calculations.overallProbability * 100;
    if (p >= 1) return 'text-status-stable';
    if (p >= 0.1) return 'text-status-watch';
    return 'text-status-degraded';
  }, [calculations.overallProbability]);

  const evColor = useMemo(() => {
    if (calculations.expectedValue > 0) return 'text-status-stable';
    if (calculations.expectedValue > -stake * 0.1) return 'text-status-watch';
    return 'text-status-degraded';
  }, [calculations.expectedValue, stake]);

  return (
    <Card className="glass-card-elevated">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Calculator className="h-5 w-5 text-primary" />
          Accumulator Calculator
        </CardTitle>
        <CardDescription>
          Calculate overall jackpot probability and expected value
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {fixtures.length === 0 ? (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              Select fixtures above to calculate accumulator probability
            </AlertDescription>
          </Alert>
        ) : (
          <>
            {/* Stake Input and Settings */}
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="stake">Stake Amount</Label>
                  <Input
                    id="stake"
                    type="number"
                    min={1}
                    value={stake}
                    onChange={(e) => setStake(Math.max(1, Number(e.target.value)))}
                    className="w-full"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="currency">Currency</Label>
                  <select
                    id="currency"
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value as 'KSH' | 'USD' | 'GBP')}
                    className="w-full h-10 px-3 rounded-md border border-input bg-background"
                  >
                    <option value="KSH">KSH (Kenyan Shilling)</option>
                    <option value="USD">USD</option>
                    <option value="GBP">GBP</option>
                  </select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="jackpotType">Jackpot Type</Label>
                <select
                  id="jackpotType"
                  value={jackpotType}
                  onChange={(e) => setJackpotType(e.target.value as '15' | '17')}
                  className="w-full h-10 px-3 rounded-md border border-input bg-background"
                >
                  <option value="15">15 Games (15M KSH prize)</option>
                  <option value="17">17 Games (200M KSH prize)</option>
                </select>
                <p className="text-xs text-muted-foreground">
                  {jackpotType === '15' 
                    ? '15 games: 15M KSH (all correct), 500K (14/15), 50K (13/15)'
                    : '17 games: 200M KSH (all correct), 5M (16/17), 500K (15/17)'}
                </p>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {/* Overall Probability */}
              <div className="p-4 rounded-lg bg-background/50 space-y-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Percent className="h-4 w-4" />
                  Overall Win Probability
                </div>
                <div className={`text-2xl font-bold tabular-nums ${probabilityColor}`}>
                  {(calculations.overallProbability * 100).toFixed(4)}%
                </div>
                <div className="text-xs text-muted-foreground">
                  1 in {calculations.oneInX.toLocaleString()} chance
                </div>
              </div>

              {/* Combined Odds */}
              <div className="p-4 rounded-lg bg-background/50 space-y-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <TrendingDown className="h-4 w-4" />
                  Combined Odds
                </div>
                <div className="text-2xl font-bold tabular-nums text-foreground">
                  {calculations.combinedOdds.toFixed(2)}
                </div>
                <div className="text-xs text-muted-foreground">
                  Return: {currency === 'KSH' ? 'KSh' : currency === 'USD' ? '$' : '£'}
                  {(calculations.potentialReturn * (currency === 'KSH' ? 1 : currency === 'USD' ? 0.007 : 0.0055)).toFixed(2)}
                </div>
              </div>

              {/* Expected Value */}
              <div className="p-4 rounded-lg bg-background/50 space-y-2">
                <Tooltip>
                  <TooltipTrigger className="flex items-center gap-2 text-sm text-muted-foreground cursor-help">
                    <AlertTriangle className="h-4 w-4" />
                    Expected Value
                    <Info className="h-3 w-3" />
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs">
                    EV = (Win Probability × Potential Return) - Stake. 
                    Positive EV means profitable long-term.
                  </TooltipContent>
                </Tooltip>
                <div className={`text-2xl font-bold tabular-nums ${evColor}`}>
                  {calculations.expectedValue >= 0 ? '+' : ''}
                  {currency === 'KSH' ? 'KSh' : currency === 'USD' ? '$' : '£'}
                  {(calculations.expectedValue * (currency === 'KSH' ? 1 : currency === 'USD' ? 0.007 : 0.0055)).toFixed(2)}
                </div>
                <div className="text-xs text-muted-foreground">
                  Edge: {calculations.edgePercentage >= 0 ? '+' : ''}
                  {calculations.edgePercentage.toFixed(2)}%
                </div>
              </div>
            </div>

            {/* Probability Visualization */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Win Probability</span>
                <span className={`font-medium ${probabilityColor}`}>
                  {(calculations.overallProbability * 100).toFixed(4)}%
                </span>
              </div>
              <Progress 
                value={Math.min(calculations.overallProbability * 100 * 100, 100)} 
                className="h-2"
              />
              <p className="text-xs text-muted-foreground">
                Scaled for visibility (actual probability shown above)
              </p>
            </div>

            {/* Fixture Breakdown */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Selection Breakdown</h4>
              <div className="space-y-1">
                {fixtures.map((fixture) => (
                  <div 
                    key={fixture.id}
                    className="flex items-center justify-between text-sm p-2 rounded bg-background/30"
                  >
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs w-6 justify-center">
                        {fixture.selection}
                      </Badge>
                      <span className="text-muted-foreground">
                        {fixture.homeTeam} vs {fixture.awayTeam}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 tabular-nums">
                      <span className="text-muted-foreground">
                        {fixture.probability.toFixed(1)}%
                      </span>
                      <span className="font-medium">
                        @{fixture.odds.toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Kenyan Jackpot Prize Info */}
            {fixtures.length === parseInt(jackpotType) && (
              <Alert className="bg-primary/10 border-primary/30">
                <Info className="h-4 w-4 text-primary" />
                <AlertDescription className="text-sm">
                  <strong>Kenyan Jackpot Prize Structure ({jackpotType} games):</strong>
                  <ul className="list-disc list-inside mt-2 space-y-1">
                    {jackpotType === '15' ? (
                      <>
                        <li>15/15 correct: <strong>15,000,000 KSH</strong></li>
                        <li>14/15 correct: <strong>500,000 KSH</strong></li>
                        <li>13/15 correct: <strong>50,000 KSH</strong></li>
                      </>
                    ) : (
                      <>
                        <li>17/17 correct: <strong>200,000,000 KSH</strong></li>
                        <li>16/17 correct: <strong>5,000,000 KSH</strong></li>
                        <li>15/17 correct: <strong>500,000 KSH</strong></li>
                      </>
                    )}
                  </ul>
                  <p className="mt-2 text-xs">
                    <strong>Stake Amount:</strong> The amount you bet per jackpot entry. 
                    In Kenya, typical stakes range from 50 KSH to 1,000 KSH per entry.
                  </p>
                </AlertDescription>
              </Alert>
            )}
            
            {/* Educational Warning */}
            <Alert className="bg-status-watch/10 border-status-watch/30">
              <AlertTriangle className="h-4 w-4 text-status-watch" />
              <AlertDescription className="text-sm">
                <strong>Remember:</strong> A {(calculations.overallProbability * 100).toFixed(2)}% probability 
                means winning approximately {Math.round(calculations.overallProbability * 1000)} times 
                out of 1,000 attempts. If you bet {currency === 'KSH' ? 'KSh' : currency === 'USD' ? '$' : '£'}{stake} each time, you'd expect to 
                {calculations.expectedValue >= 0 ? ' profit ' : ' lose '}
                {currency === 'KSH' ? 'KSh' : currency === 'USD' ? '$' : '£'}{Math.abs(calculations.expectedValue * 1000 / stake).toFixed(0)} over 1,000 bets.
              </AlertDescription>
            </Alert>
          </>
        )}
      </CardContent>
    </Card>
  );
}
