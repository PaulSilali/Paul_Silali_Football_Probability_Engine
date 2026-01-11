import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageLayout } from '@/components/layouts/PageLayout';
import { Badge } from '@/components/ui/badge';
import { 
  Brain, 
  Target, 
  Shield, 
  TrendingUp, 
  BarChart3, 
  Zap,
  CheckCircle,
  AlertTriangle,
  Info,
  Calculator,
  Activity,
  X
} from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

export default function About() {
  return (
    <PageLayout
      title="Decision Intelligence System"
      description="EV-weighted scoring, structural validation, and automatic threshold learning"
    >
      <div className="space-y-6">
        {/* Executive Summary */}
        <Alert>
          <Info className="h-4 w-4" />
          <AlertTitle>What is Decision Intelligence?</AlertTitle>
          <AlertDescription>
            This system is not a "prediction app". It is a decision-intelligence system that conditions execution,
            preserves probability mass, learns from outcomes, and can be defended, sold, and improved.
          </AlertDescription>
        </Alert>

        {/* Core Principles */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              Core Principles
            </CardTitle>
            <CardDescription>
              The Decision Intelligence system is built on three foundational principles
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Target className="h-4 w-4 text-blue-500" />
                  <h3 className="font-semibold">Economically Grounded</h3>
                </div>
                <p className="text-sm text-muted-foreground">
                  All decisions are based on Expected Value (EV) calculations, not heuristics or intuition.
                  Every pick is evaluated for its economic merit.
                </p>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-green-500" />
                  <h3 className="font-semibold">Structurally Safe</h3>
                </div>
                <p className="text-sm text-muted-foreground">
                  Hard constraints prevent structural contradictions. Draw picks with strong favorites,
                  away picks with high odds and home favorites are automatically rejected.
                </p>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-purple-500" />
                  <h3 className="font-semibold">Self-Learning</h3>
                </div>
                <p className="text-sm text-muted-foreground">
                  Thresholds automatically tune from historical outcomes. The system learns optimal
                  EV thresholds and contradiction limits from actual performance data.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Unified Decision Score */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calculator className="h-5 w-5" />
              Unified Decision Score (UDS)
            </CardTitle>
            <CardDescription>
              A single scalar that encodes expected value, structural validity, confidence, and entropy control
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <h3 className="font-semibold">Pick-Level Decision Value (PDV)</h3>
              <div className="bg-muted p-4 rounded-lg font-mono text-sm space-y-2">
                <div>EV = p × (o - 1) - (1 - p)</div>
                <div>DEV = EV / (1 + o)</div>
                <div>CEV = DEV × c</div>
                <div>SDV = CEV - s</div>
                <div className="text-red-500">PDV = -∞ if hard_contradiction else SDV</div>
              </div>
              <p className="text-sm text-muted-foreground">
                Where <code className="text-xs bg-muted px-1 py-0.5 rounded">p</code> is model probability,
                <code className="text-xs bg-muted px-1 py-0.5 rounded">o</code> is market odds,
                <code className="text-xs bg-muted px-1 py-0.5 rounded">c</code> is confidence factor,
                and <code className="text-xs bg-muted px-1 py-0.5 rounded">s</code> is structural penalty.
              </p>
            </div>

            <div className="space-y-3">
              <h3 className="font-semibold">Ticket-Level Score</h3>
              <div className="bg-muted p-4 rounded-lg font-mono text-sm">
                UDS = Σ(w_L × PDV) - λ × Contradictions - μ × Entropy
              </div>
              <p className="text-sm text-muted-foreground">
                Where <code className="text-xs bg-muted px-1 py-0.5 rounded">w_L</code> is league reliability weight,
                <code className="text-xs bg-muted px-1 py-0.5 rounded">λ</code> is contradiction penalty (10.0),
                and <code className="text-xs bg-muted px-1 py-0.5 rounded">μ</code> is entropy penalty (0.05).
              </p>
            </div>

            <div className="space-y-2">
              <h3 className="font-semibold">Acceptance Rule</h3>
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span className="text-sm">ACCEPT if UDS ≥ θ AND Contradictions ≤ K</span>
              </div>
              <p className="text-sm text-muted-foreground pl-6">
                Where θ (theta) is the learned EV threshold and K is the maximum allowed contradictions (typically 0 or 1).
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Components */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              System Components
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-3">
                <h3 className="font-semibold flex items-center gap-2">
                  <Zap className="h-4 w-4" />
                  Confidence Factor
                </h3>
                <p className="text-sm text-muted-foreground">
                  Based on xG variance: <code className="text-xs bg-muted px-1 py-0.5 rounded">c = 1 / (1 + |xg_home - xg_away|)</code>
                </p>
                <p className="text-sm text-muted-foreground">
                  Lower variance (closer xG values) = higher confidence. This reflects match uncertainty.
                </p>
              </div>

              <div className="space-y-3">
                <h3 className="font-semibold flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  Structural Penalties
                </h3>
                <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                  <li>+0.15 if draw odds &gt; 3.4</li>
                  <li>+0.20 if draw pick with xG difference &gt; 0.45</li>
                  <li>+0.10 if away odds &gt; 3.2</li>
                </ul>
              </div>

              <div className="space-y-3">
                <h3 className="font-semibold flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  Hard Contradictions
                </h3>
                <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                  <li>Draw pick when market_prob_home &gt; 0.55</li>
                  <li>Draw pick when xG difference &gt; 0.45</li>
                  <li>Away pick when away_odds &gt; 3.2 AND market_prob_home &gt; 0.50</li>
                </ul>
                <p className="text-sm text-muted-foreground mt-2">
                  Hard contradictions cause immediate ticket rejection (PDV = -∞).
                </p>
              </div>

              <div className="space-y-3">
                <h3 className="font-semibold flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  League Weights
                </h3>
                <p className="text-sm text-muted-foreground">
                  League-specific reliability weights (w_L) adjust for league quality and predictability.
                  Defaults: EPL (1.00), La Liga (0.97), Bundesliga (0.95), Serie A (1.02).
                </p>
                <p className="text-sm text-muted-foreground">
                  Weights are learned from historical performance data.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Threshold Learning */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Automatic Threshold Learning
            </CardTitle>
            <CardDescription>
              The system learns optimal thresholds from historical ticket outcomes
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <h3 className="font-semibold">How It Works</h3>
              <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                <li>Tickets are evaluated and saved with their UDS scores</li>
                <li>After matches complete, outcomes are recorded (hit rate, correct picks)</li>
                <li>The system groups tickets by EV score buckets (e.g., 0.10, 0.11, 0.12)</li>
                <li>For each bucket with sufficient samples (≥100), average hit rate is calculated</li>
                <li>The threshold that maximizes conditional accuracy is selected</li>
                <li>Thresholds are updated periodically (monthly/quarterly)</li>
              </ol>
            </div>

            <Alert>
              <Info className="h-4 w-4" />
              <AlertTitle>Default Thresholds</AlertTitle>
              <AlertDescription>
                Initial thresholds are conservative defaults. As more ticket outcomes are recorded,
                the system automatically learns optimal values. This ensures the system improves over time
                without manual intervention.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        {/* What This Is NOT */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              What This System Is NOT
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <X className="h-5 w-5 text-red-500 mt-0.5" />
                <div>
                  <h3 className="font-semibold">Not a Prediction App</h3>
                  <p className="text-sm text-muted-foreground">
                    This system does not provide "best picks" or "guaranteed wins". It provides
                    economically-grounded decision intelligence with structural safety gates.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <X className="h-5 w-5 text-red-500 mt-0.5" />
                <div>
                  <h3 className="font-semibold">Not a Black Box</h3>
                  <p className="text-sm text-muted-foreground">
                    All calculations are transparent and auditable. Every decision can be traced
                    back to its components: EV, confidence, penalties, contradictions.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <X className="h-5 w-5 text-red-500 mt-0.5" />
                <div>
                  <h3 className="font-semibold">Not Overfitted</h3>
                  <p className="text-sm text-muted-foreground">
                    The system uses structural constraints and economic principles, not pattern matching
                    on historical data. Thresholds learn from outcomes, but the core logic is principled.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <X className="h-5 w-5 text-red-500 mt-0.5" />
                <div>
                  <h3 className="font-semibold">Not a Guarantee</h3>
                  <p className="text-sm text-muted-foreground">
                    Tickets that pass structural validation are not guaranteed to win. They are
                    economically sound decisions based on model probabilities and market odds.
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Disclaimer */}
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Important Disclaimer</AlertTitle>
          <AlertDescription>
            This system provides decision intelligence based on statistical models and market data.
            It does not guarantee outcomes. All decisions should be made responsibly and within
            your means. Past performance does not guarantee future results.
          </AlertDescription>
        </Alert>
      </div>
    </PageLayout>
  );
}

