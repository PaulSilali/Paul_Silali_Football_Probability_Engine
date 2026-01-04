import { useState } from 'react';
import { 
  Database, 
  TrendingUp, 
  TrendingDown,
  Home,
  AlertTriangle,
  CheckCircle,
  Search,
  Filter,
  RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageLayout } from '@/components/layouts/PageLayout';
import { ModernCard } from '@/components/ui/modern-card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

// Mock team features data (rolling attack/defense strengths)
const teamFeatures = [
  { team: 'Arsenal', league: 'Premier League', attack: 1.42, defense: 0.78, homeAdv: 0.32, form5: 13, form10: 24, lastUpdated: '2024-12-27', dataQuality: 'complete' },
  { team: 'Man City', league: 'Premier League', attack: 1.58, defense: 0.65, homeAdv: 0.28, form5: 15, form10: 28, lastUpdated: '2024-12-27', dataQuality: 'complete' },
  { team: 'Liverpool', league: 'Premier League', attack: 1.51, defense: 0.72, homeAdv: 0.35, form5: 12, form10: 25, lastUpdated: '2024-12-27', dataQuality: 'complete' },
  { team: 'Chelsea', league: 'Premier League', attack: 1.18, defense: 0.95, homeAdv: 0.25, form5: 9, form10: 18, lastUpdated: '2024-12-27', dataQuality: 'complete' },
  { team: 'Real Madrid', league: 'La Liga', attack: 1.62, defense: 0.68, homeAdv: 0.38, form5: 13, form10: 26, lastUpdated: '2024-12-27', dataQuality: 'complete' },
  { team: 'Barcelona', league: 'La Liga', attack: 1.55, defense: 0.75, homeAdv: 0.30, form5: 11, form10: 23, lastUpdated: '2024-12-27', dataQuality: 'complete' },
  { team: 'Bayern Munich', league: 'Bundesliga', attack: 1.72, defense: 0.62, homeAdv: 0.42, form5: 14, form10: 27, lastUpdated: '2024-12-27', dataQuality: 'complete' },
  { team: 'Dortmund', league: 'Bundesliga', attack: 1.35, defense: 0.88, homeAdv: 0.33, form5: 10, form10: 20, lastUpdated: '2024-12-27', dataQuality: 'partial' },
  { team: 'Gillingham', league: 'League Two', attack: 0.92, defense: 1.15, homeAdv: 0.28, form5: 6, form10: 12, lastUpdated: '2024-12-26', dataQuality: 'complete' },
  { team: 'Cambridge', league: 'League Two', attack: 0.88, defense: 1.22, homeAdv: 0.22, form5: 5, form10: 11, lastUpdated: '2024-12-26', dataQuality: 'partial' },
];

// League-level statistics
const leagueStats = [
  { league: 'Premier League', avgGoals: 2.85, drawRate: 23.5, homeWinRate: 44.2, awayWinRate: 32.3, matches: 380 },
  { league: 'La Liga', avgGoals: 2.62, drawRate: 26.8, homeWinRate: 45.1, awayWinRate: 28.1, matches: 380 },
  { league: 'Bundesliga', avgGoals: 3.12, drawRate: 21.2, homeWinRate: 43.8, awayWinRate: 35.0, matches: 306 },
  { league: 'Serie A', avgGoals: 2.78, drawRate: 25.4, homeWinRate: 42.9, awayWinRate: 31.7, matches: 380 },
  { league: 'Ligue 1', avgGoals: 2.55, drawRate: 27.1, homeWinRate: 41.5, awayWinRate: 31.4, matches: 380 },
  { league: 'League One', avgGoals: 2.45, drawRate: 28.5, homeWinRate: 40.2, awayWinRate: 31.3, matches: 552 },
  { league: 'League Two', avgGoals: 2.38, drawRate: 29.2, homeWinRate: 39.8, awayWinRate: 31.0, matches: 552 },
];

// Missing data alerts
const dataAlerts = [
  { type: 'warning', team: 'Dortmund', issue: 'Missing 2 recent matches', league: 'Bundesliga' },
  { type: 'warning', team: 'Cambridge', issue: 'Incomplete odds data for 3 matches', league: 'League Two' },
  { type: 'info', team: 'Promoted Teams', issue: '3 newly promoted teams using league priors', league: 'Various' },
];

function getStrengthColor(value: number) {
  if (value >= 1.4) return 'text-green-600';
  if (value >= 1.1) return 'text-blue-600';
  if (value >= 0.9) return 'text-muted-foreground';
  return 'text-orange-600';
}

function getDefenseColor(value: number) {
  if (value <= 0.7) return 'text-green-600';
  if (value <= 0.9) return 'text-blue-600';
  if (value <= 1.1) return 'text-muted-foreground';
  return 'text-orange-600';
}

export default function FeatureStore() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLeague, setSelectedLeague] = useState('all');

  const filteredTeams = teamFeatures.filter(team => {
    const matchesSearch = team.team.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesLeague = selectedLeague === 'all' || team.league === selectedLeague;
    return matchesSearch && matchesLeague;
  });

  const uniqueLeagues = [...new Set(teamFeatures.map(t => t.league))];

  return (
    <PageLayout
      title="Feature Store"
      description="Team strength features, league statistics, and data quality monitoring"
      icon={<Database className="h-6 w-6" />}
      action={
        <Button variant="outline" size="sm" className="btn-glow">
          <RefreshCw className="h-4 w-4 mr-2" />
          Recompute Features
        </Button>
      }
    >

      {/* Data Alerts */}
      {dataAlerts.length > 0 && (
        <Alert variant="default" className="border-yellow-500/50 bg-yellow-500/5">
          <AlertTriangle className="h-4 w-4 text-yellow-600" />
          <AlertTitle>Data Quality Alerts</AlertTitle>
          <AlertDescription>
            <ul className="mt-2 space-y-1 text-sm">
              {dataAlerts.map((alert, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="font-medium">{alert.team}</span>
                  <span className="text-muted-foreground">—</span>
                  <span>{alert.issue}</span>
                  <Badge variant="outline" className="text-xs">{alert.league}</Badge>
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="teams">
        <TabsList>
          <TabsTrigger value="teams">Team Features</TabsTrigger>
          <TabsTrigger value="leagues">League Statistics</TabsTrigger>
        </TabsList>

        <TabsContent value="teams" className="space-y-4">
          {/* Filters */}
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search teams..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={selectedLeague} onValueChange={setSelectedLeague}>
              <SelectTrigger className="w-[200px]">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="All Leagues" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Leagues</SelectItem>
                {uniqueLeagues.map(league => (
                  <SelectItem key={league} value={league}>{league}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Team Features Table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Database className="h-5 w-5" />
                Team Rolling Features
              </CardTitle>
              <CardDescription>
                Attack/defense strengths computed from Poisson/Dixon-Coles model (time-decayed)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Team</TableHead>
                      <TableHead>League</TableHead>
                      <TableHead className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <TrendingUp className="h-3 w-3" />
                          Attack
                        </div>
                      </TableHead>
                      <TableHead className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <TrendingDown className="h-3 w-3" />
                          Defense
                        </div>
                      </TableHead>
                      <TableHead className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Home className="h-3 w-3" />
                          Home Adv
                        </div>
                      </TableHead>
                      <TableHead className="text-right">Form 5</TableHead>
                      <TableHead className="text-right">Form 10</TableHead>
                      <TableHead>Quality</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredTeams.map((team) => (
                      <TableRow key={team.team}>
                        <TableCell className="font-medium">{team.team}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">{team.league}</Badge>
                        </TableCell>
                        <TableCell className={`text-right tabular-nums font-medium ${getStrengthColor(team.attack)}`}>
                          {team.attack.toFixed(2)}
                        </TableCell>
                        <TableCell className={`text-right tabular-nums font-medium ${getDefenseColor(team.defense)}`}>
                          {team.defense.toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          +{team.homeAdv.toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-muted-foreground">
                          {team.form5} pts
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-muted-foreground">
                          {team.form10} pts
                        </TableCell>
                        <TableCell>
                          {team.dataQuality === 'complete' ? (
                            <Badge variant="secondary" className="bg-green-500/10 text-green-600 text-xs">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Complete
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="bg-yellow-500/10 text-yellow-600 text-xs">
                              <AlertTriangle className="h-3 w-3 mr-1" />
                              Partial
                            </Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Feature Explanation */}
          <Card className="bg-muted/30">
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="font-medium flex items-center gap-2 mb-1">
                    <TrendingUp className="h-4 w-4 text-green-600" />
                    Attack Strength
                  </div>
                  <p className="text-muted-foreground">
                    Goals scored relative to league average. &gt;1.0 = above average.
                  </p>
                </div>
                <div>
                  <div className="font-medium flex items-center gap-2 mb-1">
                    <TrendingDown className="h-4 w-4 text-blue-600" />
                    Defense Strength
                  </div>
                  <p className="text-muted-foreground">
                    Goals conceded relative to league average. &lt;1.0 = better defense.
                  </p>
                </div>
                <div>
                  <div className="font-medium flex items-center gap-2 mb-1">
                    <Home className="h-4 w-4 text-primary" />
                    Home Advantage
                  </div>
                  <p className="text-muted-foreground">
                    Additional expected goal boost when playing at home.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="leagues" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">League-Level Statistics</CardTitle>
              <CardDescription>
                Aggregate outcome distributions and goal rates by competition
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>League</TableHead>
                    <TableHead className="text-right">Avg Goals</TableHead>
                    <TableHead className="text-right">Draw Rate</TableHead>
                    <TableHead className="text-right">Home Win %</TableHead>
                    <TableHead className="text-right">Away Win %</TableHead>
                    <TableHead className="text-right">Matches</TableHead>
                    <TableHead>Distribution</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {leagueStats.map((league) => (
                    <TableRow key={league.league}>
                      <TableCell className="font-medium">{league.league}</TableCell>
                      <TableCell className="text-right tabular-nums">{league.avgGoals.toFixed(2)}</TableCell>
                      <TableCell className="text-right tabular-nums">{league.drawRate}%</TableCell>
                      <TableCell className="text-right tabular-nums">{league.homeWinRate}%</TableCell>
                      <TableCell className="text-right tabular-nums">{league.awayWinRate}%</TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">{league.matches}</TableCell>
                      <TableCell>
                        <div className="flex h-2 w-24 rounded-full overflow-hidden">
                          <div 
                            className="bg-green-500" 
                            style={{ width: `${league.homeWinRate}%` }} 
                          />
                          <div 
                            className="bg-gray-400" 
                            style={{ width: `${league.drawRate}%` }} 
                          />
                          <div 
                            className="bg-blue-500" 
                            style={{ width: `${league.awayWinRate}%` }} 
                          />
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Legend */}
          <Card className="bg-muted/30">
            <CardContent className="pt-6">
              <div className="flex items-center gap-6 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-green-500 rounded" />
                  <span>Home Win</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-gray-400 rounded" />
                  <span>Draw</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-blue-500 rounded" />
                  <span>Away Win</span>
                </div>
                <span className="text-muted-foreground ml-auto">
                  Draw-heavy leagues: higher draw rates indicate need for conservative probability sets
                </span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </PageLayout>
  );
}
