import { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  Users,
  CloudRain,
  Clock,
  DollarSign,
  Wind,
  Info,
  Loader2
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/services/api';

interface DrawComponents {
  league_prior: number;
  elo_symmetry: number;
  h2h: number;
  weather: number;
  fatigue: number;
  referee: number;
  odds_drift: number;
  total_multiplier: number;
}

export function DrawComponentsDisplay() {
  const { toast } = useToast();
  const [fixtureId, setFixtureId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [components, setComponents] = useState<DrawComponents | null>(null);

  const loadComponents = async () => {
    if (!fixtureId) {
      toast({
        title: 'Error',
        description: 'Please enter a fixture ID',
        variant: 'destructive'
      });
      return;
    }

    setLoading(true);
    try {
      const response = await apiClient.getDrawComponents(parseInt(fixtureId));
      setComponents(response.data);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to load components',
        variant: 'destructive'
      });
      setComponents(null);
    } finally {
      setLoading(false);
    }
  };

  const componentConfig = [
    {
      key: 'league_prior' as keyof DrawComponents,
      label: 'League Prior',
      icon: BarChart3,
      description: 'Historical draw rate for this league',
      color: 'bg-blue-500'
    },
    {
      key: 'elo_symmetry' as keyof DrawComponents,
      label: 'Elo Symmetry',
      icon: TrendingUp,
      description: 'Team strength similarity (closer = higher draw)',
      color: 'bg-purple-500'
    },
    {
      key: 'h2h' as keyof DrawComponents,
      label: 'Head-to-Head',
      icon: Users,
      description: 'Historical draw rate between these teams',
      color: 'bg-green-500'
    },
    {
      key: 'weather' as keyof DrawComponents,
      label: 'Weather',
      icon: CloudRain,
      description: 'Weather conditions impact',
      color: 'bg-cyan-500'
    },
    {
      key: 'fatigue' as keyof DrawComponents,
      label: 'Fatigue',
      icon: Clock,
      description: 'Rest days and congestion',
      color: 'bg-orange-500'
    },
    {
      key: 'referee' as keyof DrawComponents,
      label: 'Referee',
      icon: Users,
      description: 'Referee control level',
      color: 'bg-red-500'
    },
    {
      key: 'odds_drift' as keyof DrawComponents,
      label: 'Odds Movement',
      icon: DollarSign,
      description: 'Market draw odds drift',
      color: 'bg-yellow-500'
    }
  ];

  const getMultiplierColor = (value: number) => {
    if (value > 1.1) return 'text-green-600';
    if (value < 0.9) return 'text-red-600';
    return 'text-blue-600';
  };

  const getMultiplierLabel = (value: number) => {
    if (value > 1.1) return 'Strong Increase';
    if (value > 1.05) return 'Moderate Increase';
    if (value < 0.9) return 'Strong Decrease';
    if (value < 0.95) return 'Moderate Decrease';
    return 'Neutral';
  };

  return (
    <div className="space-y-6">
      {/* Input */}
      <Card>
        <CardHeader>
          <CardTitle>View Draw Components</CardTitle>
          <CardDescription>
            Enter a fixture ID to view its draw structural adjustment components
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <div className="flex-1">
              <Label>Fixture ID</Label>
              <Input
                value={fixtureId}
                onChange={(e) => setFixtureId(e.target.value)}
                placeholder="Enter fixture ID"
                type="number"
              />
            </div>
            <div className="flex items-end">
              <Button
                onClick={loadComponents}
                disabled={loading || !fixtureId}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  'Load Components'
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Components Display */}
      {components && (
        <>
          {/* Total Multiplier */}
          <Card className="border-primary/50 bg-primary/5">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Total Draw Multiplier</span>
                <Badge
                  variant="outline"
                  className={`text-lg font-bold ${getMultiplierColor(components.total_multiplier)}`}
                >
                  {components.total_multiplier.toFixed(4)}x
                </Badge>
              </CardTitle>
              <CardDescription>
                {getMultiplierLabel(components.total_multiplier)} in draw probability
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Progress
                value={((components.total_multiplier - 0.75) / (1.35 - 0.75)) * 100}
                className="h-3"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-2">
                <span>0.75x (Min)</span>
                <span>1.35x (Max)</span>
              </div>
            </CardContent>
          </Card>

          {/* Individual Components */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {componentConfig.map((config) => {
              const Icon = config.icon;
              const value = components[config.key];
              const isNeutral = Math.abs(value - 1.0) < 0.01;

              return (
                <Card key={config.key}>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Icon className={`h-5 w-5 ${config.color.replace('bg-', 'text-')}`} />
                        <CardTitle className="text-sm">{config.label}</CardTitle>
                      </div>
                      <Badge
                        variant={isNeutral ? 'secondary' : value > 1.0 ? 'default' : 'destructive'}
                        className="font-mono"
                      >
                        {value.toFixed(3)}x
                      </Badge>
                    </div>
                    <CardDescription className="text-xs mt-1">
                      {config.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Progress
                      value={isNeutral ? 50 : value > 1.0 ? 50 + ((value - 1.0) / 0.35) * 50 : (value / 1.0) * 50}
                      className="h-2"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground mt-2">
                      <span>Decrease</span>
                      <span className="font-medium">1.0x (Neutral)</span>
                      <span>Increase</span>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Explanation */}
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              <strong>How it works:</strong> Each component multiplies the base draw probability.
              Values above 1.0 increase draw probability, below 1.0 decrease it. The total multiplier
              is the product of all components (bounded between 0.75x and 1.35x). Only the draw
              probability is adjusted; home/away probabilities are renormalized proportionally.
            </AlertDescription>
          </Alert>
        </>
      )}

      {!components && !loading && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Enter a fixture ID and click "Load Components" to view draw structural adjustments</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

