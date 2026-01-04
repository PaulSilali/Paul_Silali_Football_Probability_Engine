import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { PageLayout } from '@/components/layouts/PageLayout';
import { ModernCard } from '@/components/ui/modern-card';
import { 
  CheckCircle2, 
  XCircle, 
  Database, 
  Globe,
  FileText,
  ArrowRight,
  Info,
  Zap,
  Target,
  TrendingUp
} from 'lucide-react';

export default function TrainingDataContract() {
  const requiredData = [
    {
      field: 'Match Date',
      rawColumn: 'Date',
      type: 'date',
      description: 'Date of the match',
      example: '2024-01-15',
    },
    {
      field: 'League / Competition',
      rawColumn: 'Div',
      type: 'string',
      description: 'Competition code (e.g., E0 = Premier League)',
      example: 'E0',
    },
    {
      field: 'Home Team',
      rawColumn: 'HomeTeam',
      type: 'string',
      description: 'Name of the home team',
      example: 'Arsenal',
    },
    {
      field: 'Away Team',
      rawColumn: 'AwayTeam',
      type: 'string',
      description: 'Name of the away team',
      example: 'Chelsea',
    },
    {
      field: 'Full-time Home Goals',
      rawColumn: 'FTHG',
      type: 'integer',
      description: 'Goals scored by home team',
      example: '2',
    },
    {
      field: 'Full-time Away Goals',
      rawColumn: 'FTAG',
      type: 'integer',
      description: 'Goals scored by away team',
      example: '1',
    },
    {
      field: 'Home Odds',
      rawColumn: 'B365H',
      type: 'float',
      description: 'Bookmaker odds for home win',
      example: '1.85',
    },
    {
      field: 'Draw Odds',
      rawColumn: 'B365D',
      type: 'float',
      description: 'Bookmaker odds for draw',
      example: '3.40',
    },
    {
      field: 'Away Odds',
      rawColumn: 'B365A',
      type: 'float',
      description: 'Bookmaker odds for away win',
      example: '4.20',
    },
  ];

  const optionalData = [
    { field: 'Half-time Goals', description: 'Not used in training' },
    { field: 'Shots / Shots on Target', description: 'Redundant - goals are outcome' },
    { field: 'Corners / Fouls', description: 'Low predictive signal' },
    { field: 'Yellow/Red Cards', description: 'Not relevant to outcome prediction' },
  ];

  const notRequiredData = [
    { field: 'Player Statistics', reason: 'Team strength is learned implicitly' },
    { field: 'Injury Reports', reason: 'Already priced into bookmaker odds' },
    { field: 'Lineups', reason: 'Unavailable consistently, high noise' },
    { field: 'Possession / xG', reason: 'Post-match stats, not predictive' },
    { field: 'Live / In-play Data', reason: 'System operates pre-match only' },
    { field: 'Social Media / News', reason: 'High noise, low stability' },
    { field: 'Current Form Tables', reason: 'Implicitly learned via historical data' },
  ];

  const dataFlow = [
    { step: 'INPUT', items: ['Jackpot fixtures (teams, league, date)', 'Market odds (H/D/A)'] },
    { step: 'MODELS', items: ['Poisson / Dixon-Coles (goal expectations)', 'Analytical probability aggregation', 'Odds–model blending', 'Calibration'] },
    { step: 'OUTPUT', items: ['P(Home), P(Draw), P(Away)', 'Multiple probability sets (A/B/C/…)'] },
  ];

  return (
    <PageLayout
      title="Training Data Contract"
      description="Formal specification of data requirements for the Football Jackpot Probability Engine"
      icon={<FileText className="h-6 w-6" />}
    >

      {/* Quick Summary */}
      <Card className="border-primary/30 bg-primary/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Info className="h-5 w-5 text-primary" />
            System Data Requirements
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm">
            This system is intentionally designed to be <strong>minimal, robust, and scalable</strong>. 
            For full model training, you only need two core data classes:
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex items-start gap-3 p-4 rounded-lg bg-background border">
              <Database className="h-5 w-5 text-primary mt-0.5" />
              <div>
                <h4 className="font-medium">Historical Match Results</h4>
                <p className="text-sm text-muted-foreground">Date, teams, goals — core model learning</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 rounded-lg bg-background border">
              <TrendingUp className="h-5 w-5 text-primary mt-0.5" />
              <div>
                <h4 className="font-medium">Historical Odds</h4>
                <p className="text-sm text-muted-foreground">H/D/A odds — market signal for blending</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Required Data */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-500" />
            Required Data Fields
          </CardTitle>
          <CardDescription>
            These fields are mandatory for model training
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="text-left py-3 px-4 font-medium">Field</th>
                  <th className="text-left py-3 px-4 font-medium">Raw Column</th>
                  <th className="text-left py-3 px-4 font-medium">Type</th>
                  <th className="text-left py-3 px-4 font-medium hidden md:table-cell">Description</th>
                  <th className="text-left py-3 px-4 font-medium hidden lg:table-cell">Example</th>
                </tr>
              </thead>
              <tbody>
                {requiredData.map((item, index) => (
                  <tr key={item.field} className={index % 2 === 0 ? 'bg-background' : 'bg-muted/20'}>
                    <td className="py-3 px-4 font-medium">{item.field}</td>
                    <td className="py-3 px-4 font-mono text-xs">{item.rawColumn}</td>
                    <td className="py-3 px-4">
                      <Badge variant="outline" className={
                        item.type === 'date' ? 'bg-purple-500/10 text-purple-500 border-purple-500/30' :
                        item.type === 'string' ? 'bg-blue-500/10 text-blue-500 border-blue-500/30' :
                        item.type === 'integer' ? 'bg-green-500/10 text-green-500 border-green-500/30' :
                        'bg-amber-500/10 text-amber-500 border-amber-500/30'
                      }>{item.type}</Badge>
                    </td>
                    <td className="py-3 px-4 text-muted-foreground hidden md:table-cell">{item.description}</td>
                    <td className="py-3 px-4 font-mono text-xs hidden lg:table-cell">{item.example}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Not Required */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <XCircle className="h-5 w-5 text-destructive" />
            NOT Required for Training
          </CardTitle>
          <CardDescription>
            These data sources are not needed — the system is intentionally minimal
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2">
            {notRequiredData.map((item) => (
              <div key={item.field} className="flex items-start gap-3 p-3 rounded-lg bg-destructive/5 border border-destructive/20">
                <XCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
                <div>
                  <span className="font-medium">{item.field}</span>
                  <p className="text-sm text-muted-foreground">{item.reason}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Why This Works */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            Why This Works (Architectural Reasoning)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <div className="p-4 rounded-lg border bg-muted/30">
              <h4 className="font-medium mb-2">1. Team "Form" Is Already Embedded</h4>
              <p className="text-sm text-muted-foreground">
                Models do not rely on human-defined "last 5 games form". Form is implicitly learned via:
                rolling historical goal data, time-decayed team strength, home/away asymmetry, and league-level dynamics.
              </p>
            </div>
            <div className="p-4 rounded-lg border bg-muted/30">
              <h4 className="font-medium mb-2">2. Injuries & Lineups Are Indirectly Reflected by Odds</h4>
              <p className="text-sm text-muted-foreground">
                Bookmaker odds already price in injuries, suspensions, squad depth, managerial changes, and market sentiment.
                By blending model probabilities with odds, injury information is implicitly absorbed.
              </p>
            </div>
            <div className="p-4 rounded-lg border bg-muted/30">
              <h4 className="font-medium mb-2">3. Jackpot Constraints Favor Stability Over Reactivity</h4>
              <p className="text-sm text-muted-foreground">
                Jackpot betting has fixed kickoff windows, no in-play updates, long-tail outcome risk, and many matches per slip.
                Adding volatile data often reduces calibration quality across 13–17 matches.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Data Flow Diagram */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5 text-primary" />
            System Data Flow
          </CardTitle>
          <CardDescription>
            Conceptual flow from input to output
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row items-stretch gap-4">
            {dataFlow.map((stage, index) => (
              <div key={stage.step} className="flex-1 flex items-center gap-4">
                <div className="flex-1 p-4 rounded-lg border bg-muted/30 space-y-2">
                  <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30">
                    {stage.step}
                  </Badge>
                  <ul className="text-sm space-y-1">
                    {stage.items.map((item) => (
                      <li key={item} className="flex items-start gap-2">
                        <span className="text-primary mt-1">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                {index < dataFlow.length - 1 && (
                  <ArrowRight className="h-5 w-5 text-muted-foreground hidden md:block" />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Data Source */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5 text-primary" />
            Recommended Data Source
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-start gap-4 p-4 rounded-lg border bg-green-500/5 border-green-500/20">
            <FileText className="h-8 w-8 text-green-500 shrink-0" />
            <div className="space-y-2">
              <h4 className="font-semibold text-lg">Football-Data.co.uk</h4>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/30">Free</Badge>
                <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/30">CSV Download</Badge>
                <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/30">Results + Odds</Badge>
                <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/30">10+ Years</Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                One free source covers everything needed for training. No API key required.
                Historical results and closing betting odds available in CSV format.
              </p>
              <Separator className="my-3" />
              <div className="text-sm">
                <p className="font-medium mb-1">Download URLs:</p>
                <code className="text-xs bg-muted px-2 py-1 rounded block">
                  https://www.football-data.co.uk/data.php
                </code>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </PageLayout>
  );
}
