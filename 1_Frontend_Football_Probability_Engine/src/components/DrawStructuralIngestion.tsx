import { useState, useEffect } from 'react';
import {
  CloudRain,
  Users,
  TrendingUp,
  Wind,
  Clock,
  DollarSign,
  BarChart3,
  Loader2,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  Play,
  Info,
  Globe,
  Target,
  Database,
  FileSpreadsheet,
  CheckSquare,
  Square,
  RefreshCw,
  Download,
  Upload,
  Zap
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/services/api';
import { allLeagues } from '@/data/allLeagues';

interface IngestionResult {
  success: boolean;
  message?: string;
  error?: string;
  data?: any;
}

// Generate list of seasons (current season going back)
function generateSeasons(count: number = 10): string[] {
  const currentDate = new Date();
  const currentYear = currentDate.getFullYear();
  const currentMonth = currentDate.getMonth() + 1; // 1-12
  
  // Determine current season (assumes season starts in August)
  let currentSeasonStart: number;
  if (currentMonth >= 8) {
    currentSeasonStart = currentYear;
  } else {
    currentSeasonStart = currentYear - 1;
  }
  
  const seasons: string[] = [];
  for (let i = 0; i < count; i++) {
    const yearStart = currentSeasonStart - i;
    const yearEnd = yearStart + 1;
    const season = `${yearStart}-${String(yearEnd).slice(-2)}`;
    seasons.push(season);
  }
  
  return seasons;
}

export function DrawStructuralIngestion() {
  const { toast } = useToast();
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [results, setResults] = useState<Record<string, IngestionResult>>({});
  
  // Shared league and season selection (applies to all tabs)
  const [selectedLeagues, setSelectedLeagues] = useState<string[]>([]);
  const [selectedSeason, setSelectedSeason] = useState<string>('2024-25');
  const seasonsList = generateSeasons(10);
  
  // Summary states for all data types
  const [priorsSummary, setPriorsSummary] = useState<{
    total_priors: number;
    leagues_with_priors: number;
    total_leagues: number;
    unique_seasons: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  } | null>(null);
  const [h2hSummary, setH2hSummary] = useState<{
    total_records: number;
    leagues_with_stats: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  } | null>(null);
  const [eloSummary, setEloSummary] = useState<{
    total_records: number;
    leagues_with_elo: number;
    total_leagues: number;
    unique_dates: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  } | null>(null);
  const [weatherSummary, setWeatherSummary] = useState<{
    total_records: number;
    leagues_with_weather: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  } | null>(null);
  const [refereeSummary, setRefereeSummary] = useState<{
    total_records: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  } | null>(null);
  const [restDaysSummary, setRestDaysSummary] = useState<{
    total_records: number;
    leagues_with_rest_days: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  } | null>(null);
  const [leagueStructureSummary, setLeagueStructureSummary] = useState<{
    total_records: number;
    leagues_with_structure: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  } | null>(null);
  
  // Individual League Structure ingestion state
  const [selectedLeagueCode, setSelectedLeagueCode] = useState<string>('');
  const [selectedLeagueSeason, setSelectedLeagueSeason] = useState<string>('2024-25');
  const [totalTeams, setTotalTeams] = useState<string>('');
  const [relegationZones, setRelegationZones] = useState<string>('');
  const [promotionZones, setPromotionZones] = useState<string>('');
  const [playoffZones, setPlayoffZones] = useState<string>('');
  const [oddsMovementSummary, setOddsMovementSummary] = useState<{
    total_records: number;
    leagues_with_odds: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  } | null>(null);
  const [xgDataSummary, setXgDataSummary] = useState<{
    total_records: number;
    leagues_with_xg: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  } | null>(null);
  const [teamFormSummary, setTeamFormSummary] = useState<{
    total_records: number;
    fixture_records: number;
    historical_records: number;
    leagues_with_form: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  } | null>(null);
  const [teamInjuriesSummary, setTeamInjuriesSummary] = useState<{
    total_records: number;
    leagues_with_injuries: number;
    total_leagues: number;
    last_updated: string | null;
    by_league: Array<{ code: string; name: string; count: number }>;
  } | null>(null);
  
  const [loadingSummary, setLoadingSummary] = useState<Record<string, boolean>>({});
  const [importingAll, setImportingAll] = useState(false);
  const [importAllResult, setImportAllResult] = useState<{
    success: boolean;
    message: string;
    data?: {
      results: Record<string, any>;
      summary: {
        total_successful: number;
        total_failed: number;
        all_completed: boolean;
      };
    };
  } | null>(null);

  const setLoadingState = (key: string, value: boolean) => {
    setLoading(prev => ({ ...prev, [key]: value }));
  };

  const setResult = (key: string, result: IngestionResult) => {
    setResults(prev => ({ ...prev, [key]: result }));
  };

  // League selection helpers
  const toggleLeague = (leagueCode: string) => {
    setSelectedLeagues(prev =>
      prev.includes(leagueCode) ? prev.filter(c => c !== leagueCode) : [...prev, leagueCode]
    );
  };

  const selectAllLeagues = () => {
    if (selectedLeagues.length === allLeagues.length) {
      setSelectedLeagues([]);
    } else {
      setSelectedLeagues(allLeagues.map(l => l.code));
    }
  };

  // Fetch summary functions for all data types
  const fetchPriorsSummary = async () => {
    setLoadingSummary(prev => ({ ...prev, 'priors': true }));
    try {
      const response = await apiClient.getLeaguePriorsSummary();
      if (response.success && response.data) {
        setPriorsSummary(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch league priors summary:', error);
    } finally {
      setLoadingSummary(prev => ({ ...prev, 'priors': false }));
    }
  };

  const fetchH2HSummary = async () => {
    setLoadingSummary(prev => ({ ...prev, 'h2h': true }));
    try {
      const response = await apiClient.getH2HStatsSummary();
      if (response.success && response.data) {
        setH2hSummary(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch H2H stats summary:', error);
    } finally {
      setLoadingSummary(prev => ({ ...prev, 'h2h': false }));
    }
  };

  const fetchEloSummary = async () => {
    setLoadingSummary(prev => ({ ...prev, 'elo': true }));
    try {
      const response = await apiClient.getEloRatingsSummary();
      if (response.success && response.data) {
        setEloSummary(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch Elo ratings summary:', error);
    } finally {
      setLoadingSummary(prev => ({ ...prev, 'elo': false }));
    }
  };

  const fetchWeatherSummary = async () => {
    setLoadingSummary(prev => ({ ...prev, 'weather': true }));
    try {
      const response = await apiClient.getWeatherSummary();
      if (response.success && response.data) {
        setWeatherSummary(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch weather summary:', error);
    } finally {
      setLoadingSummary(prev => ({ ...prev, 'weather': false }));
    }
  };

  const fetchRefereeSummary = async () => {
    setLoadingSummary(prev => ({ ...prev, 'referee': true }));
    try {
      const response = await apiClient.getRefereeSummary();
      if (response.success && response.data) {
        setRefereeSummary(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch referee summary:', error);
    } finally {
      setLoadingSummary(prev => ({ ...prev, 'referee': false }));
    }
  };

  const fetchRestDaysSummary = async () => {
    setLoadingSummary(prev => ({ ...prev, 'rest-days': true }));
    try {
      const response = await apiClient.getRestDaysSummary();
      if (response.success && response.data) {
        setRestDaysSummary(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch rest days summary:', error);
    } finally {
      setLoadingSummary(prev => ({ ...prev, 'rest-days': false }));
    }
  };

  const fetchOddsMovementSummary = async () => {
    setLoadingSummary(prev => ({ ...prev, 'odds-movement': true }));
    try {
      const response = await apiClient.getOddsMovementSummary();
      if (response.success && response.data) {
        setOddsMovementSummary(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch odds movement summary:', error);
    } finally {
      setLoadingSummary(prev => ({ ...prev, 'odds-movement': false }));
    }
  };

  const fetchLeagueStructureSummary = async () => {
    setLoadingSummary(prev => ({ ...prev, 'league-structure': true }));
    try {
      const response = await apiClient.getLeagueStructureSummary();
      if (response.success && response.data) {
        setLeagueStructureSummary(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch league structure summary:', error);
    } finally {
      setLoadingSummary(prev => ({ ...prev, 'league-structure': false }));
    }
  };

  const fetchXGDataSummary = async () => {
    setLoadingSummary(prev => ({ ...prev, 'xg-data': true }));
    try {
      const response = await apiClient.getXGDataSummary();
      if (response.success && response.data) {
        setXgDataSummary(response.data);
      }
    } catch (error: any) {
      console.error('Failed to fetch xG data summary:', error);
    } finally {
      setLoadingSummary(prev => ({ ...prev, 'xg-data': false }));
    }
  };

  const fetchTeamFormSummary = async () => {
    setLoadingSummary(prev => ({ ...prev, 'team-form': true }));
    try {
      const response = await apiClient.getTeamFormSummary();
      if (response.success && response.data) {
        setTeamFormSummary(response.data);
      }
    } catch (error: any) {
      console.error('Failed to fetch team form summary:', error);
    } finally {
      setLoadingSummary(prev => ({ ...prev, 'team-form': false }));
    }
  };

  const fetchTeamInjuriesSummary = async () => {
    setLoadingSummary(prev => ({ ...prev, 'team-injuries': true }));
    try {
      const response = await apiClient.getTeamInjuriesSummary();
      if (response.success && response.data) {
        setTeamInjuriesSummary(response.data);
      }
    } catch (error: any) {
      console.error('Failed to fetch team injuries summary:', error);
    } finally {
      setLoadingSummary(prev => ({ ...prev, 'team-injuries': false }));
    }
  };

  // Fetch all summaries on mount
  useEffect(() => {
    fetchPriorsSummary();
    fetchH2HSummary();
    fetchEloSummary();
    fetchWeatherSummary();
    fetchRefereeSummary();
    fetchRestDaysSummary();
    fetchOddsMovementSummary();
    fetchLeagueStructureSummary();
    fetchXGDataSummary();
    fetchTeamFormSummary();
    fetchTeamInjuriesSummary();
  }, []);

  // Refresh summaries after successful ingestion
  useEffect(() => {
    if (results['league-priors']?.success) fetchPriorsSummary();
    if (results['h2h-batch']?.success) fetchH2HSummary();
    if (results['elo-batch']?.success) fetchEloSummary();
    if (results['weather-batch']?.success) fetchWeatherSummary();
    if (results['referee-batch']?.success) fetchRefereeSummary();
    if (results['rest-days-batch']?.success) fetchRestDaysSummary();
    if (results['odds-movement-batch']?.success) fetchOddsMovementSummary();
    if (results['league-structure-batch']?.success) fetchLeagueStructureSummary();
    if (results['xg-data-batch']?.success) fetchXGDataSummary();
    if (results['team-form-batch']?.success) fetchTeamFormSummary();
    if (results['team-injuries-batch']?.success) fetchTeamInjuriesSummary();
  }, [
    results['league-priors']?.success,
    results['h2h-batch']?.success,
    results['elo-batch']?.success,
    results['weather-batch']?.success,
    results['referee-batch']?.success,
    results['rest-days-batch']?.success,
    results['odds-movement-batch']?.success,
    results['league-structure-batch']?.success,
    results['team-form-batch']?.success,
    results['team-injuries-batch']?.success,
  ]);

  // League Draw Priors
  const handleIngestLeaguePriors = async () => {
    if (selectedLeagues.length === 0) {
      toast({
        title: 'Error',
        description: 'Please select at least one league',
        variant: 'destructive'
      });
      return;
    }

    setLoadingState('league-priors', true);
    try {
      // Use batch endpoint if:
      // 1. "ALL" seasons selected
      // 2. "last7" or "last10" selected (multiple seasons)
      // 3. All leagues are selected (more efficient to batch)
      const useBatchEndpoint = 
        selectedSeason === 'ALL' || 
        selectedSeason === 'last7' || 
        selectedSeason === 'last10' ||
        selectedLeagues.length === allLeagues.length;

      if (useBatchEndpoint) {
        // Use batch endpoint
        const useAllLeagues = selectedLeagues.length === allLeagues.length;
        const useAllSeasons = selectedSeason === 'ALL' || selectedSeason === 'last7' || selectedSeason === 'last10';
        const maxYears = selectedSeason === 'last7' ? 7 : selectedSeason === 'last10' ? 10 : undefined;

        const response = await apiClient.batchIngestLeagueDrawPriors({
          leagueCodes: useAllLeagues ? undefined : selectedLeagues,
          season: useAllSeasons ? undefined : selectedSeason,
          useAllLeagues: useAllLeagues,
          useAllSeasons: useAllSeasons,
          maxYears: maxYears,
        });

        if (response.success && response.data) {
          const data = response.data;
          setResult('league-priors', {
            success: data.success,
            data: {
              processed: data.processed || 0,
              successful: data.successful || 0,
              failed: data.failed || 0,
              skipped: data.skipped || 0,
              details: data.details || [],
            }
          });

          toast({
            title: 'Success',
            description: response.message || `Processed ${data.successful}/${data.processed} league/season combinations successfully`
          });
        } else {
          throw new Error(response.message || 'Batch ingestion failed');
        }
      } else {
        // Use individual endpoint for single league/season combinations
        const promises = selectedLeagues.map(leagueCode => 
          apiClient.ingestLeagueDrawPriors(leagueCode, selectedSeason)
        );
        const responses = await Promise.all(promises);
        
        const successCount = responses.filter(r => r.success).length;
        setResult('league-priors', { 
          success: successCount > 0, 
          data: { processed: selectedLeagues.length, successful: successCount }
        });
        
        toast({
          title: 'Success',
          description: `Processed ${successCount}/${selectedLeagues.length} leagues successfully`
        });
      }
    } catch (error: any) {
      setResult('league-priors', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to ingest league priors',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('league-priors', false);
    }
  };

  // H2H Stats
  const [homeTeamId, setHomeTeamId] = useState<string>('');
  const [awayTeamId, setAwayTeamId] = useState<string>('');
  const [useH2HApi, setUseH2HApi] = useState(false);

  const handleIngestH2H = async () => {
    if (!homeTeamId || !awayTeamId) {
      toast({
        title: 'Error',
        description: 'Please enter both team IDs',
        variant: 'destructive'
      });
      return;
    }

    setLoadingState('h2h', true);
    try {
      const response = await apiClient.ingestH2HStats(
        parseInt(homeTeamId),
        parseInt(awayTeamId),
        useH2HApi
      );
      setResult('h2h', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: 'H2H statistics ingested successfully'
      });
    } catch (error: any) {
      setResult('h2h', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to ingest H2H stats',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('h2h', false);
    }
  };

  const handleBatchIngestH2H = async () => {
    const useAllLeagues = selectedLeagues.length === allLeagues.length;
    const useAllSeasons = selectedSeason === 'ALL' || selectedSeason === 'last7' || selectedSeason === 'last10';
    const maxYears = selectedSeason === 'last7' ? 7 : selectedSeason === 'last10' ? 10 : undefined;

    setLoadingState('h2h-batch', true);
    try {
      const response = await apiClient.batchIngestH2HStats({
        leagueCodes: useAllLeagues ? undefined : selectedLeagues,
        season: useAllSeasons ? undefined : selectedSeason,
        useAllLeagues: useAllLeagues,
        useAllSeasons: useAllSeasons,
        maxYears: maxYears,
        saveCsv: true,
      });

      if (response.success && response.data) {
        const data = response.data;
        setResult('h2h-batch', {
          success: true,
          data: {
            successful: data.successful || 0,
            failed: data.failed || 0,
            total: data.total || 0,
            details: data.details || []
          }
        });
        toast({
          title: 'Success',
          description: `Batch H2H ingestion complete: ${data.successful || 0} successful, ${data.failed || 0} failed out of ${data.total || 0} processed`
        });
      } else {
        throw new Error(response.message || 'Batch ingestion failed');
      }
    } catch (error: any) {
      setResult('h2h-batch', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to batch ingest H2H stats',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('h2h-batch', false);
    }
  };

  // Elo Ratings Batch
  const handleBatchIngestElo = async () => {
    const useAllSeasons = selectedSeason === 'ALL' || selectedSeason === 'last7' || selectedSeason === 'last10';
    const maxYears = selectedSeason === 'last7' ? 7 : selectedSeason === 'last10' ? 10 : 10;
    
    setLoadingState('elo-batch', true);
    try {
      const response = await apiClient.batchIngestEloRatings({
        leagueCodes: selectedLeagues.length === allLeagues.length ? undefined : selectedLeagues,
        season: useAllSeasons ? undefined : selectedSeason,
        useAllLeagues: selectedLeagues.length === allLeagues.length,
        useAllSeasons: useAllSeasons,
        maxYears: maxYears,
        saveCsv: true
      });
      setResult('elo-batch', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: `Elo batch calculation complete: ${response.data?.successful || 0} successful, ${response.data?.failed || 0} failed`
      });
    } catch (error: any) {
      setResult('elo-batch', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to batch calculate Elo ratings',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('elo-batch', false);
    }
  };

  // Elo Ratings
  const [teamId, setTeamId] = useState<string>('');
  const [calculateEloFromMatches, setCalculateEloFromMatches] = useState(false);

  const handleIngestElo = async () => {
    if (!teamId && !calculateEloFromMatches) {
      toast({
        title: 'Error',
        description: 'Please enter team ID or enable calculation from matches',
        variant: 'destructive'
      });
      return;
    }

    setLoadingState('elo', true);
    try {
      const response = await apiClient.ingestEloRatings(
        teamId ? parseInt(teamId) : undefined,
        undefined,
        calculateEloFromMatches
      );
      setResult('elo', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: 'Elo ratings ingested successfully'
      });
    } catch (error: any) {
      setResult('elo', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to ingest Elo ratings',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('elo', false);
    }
  };

  // Weather
  const [fixtureId, setFixtureId] = useState<string>('');
  const [latitude, setLatitude] = useState<string>('');
  const [longitude, setLongitude] = useState<string>('');
  const [matchDatetime, setMatchDatetime] = useState<string>('');

  const handleIngestWeather = async () => {
    if (!fixtureId || !latitude || !longitude || !matchDatetime) {
      toast({
        title: 'Error',
        description: 'Please fill all weather fields',
        variant: 'destructive'
      });
      return;
    }

    setLoadingState('weather', true);
    try {
      const response = await apiClient.ingestWeather(
        parseInt(fixtureId),
        parseFloat(latitude),
        parseFloat(longitude),
        matchDatetime
      );
      setResult('weather', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: 'Weather data ingested successfully'
      });
    } catch (error: any) {
      setResult('weather', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to ingest weather',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('weather', false);
    }
  };

  // Referee Stats Batch
  const handleBatchIngestReferee = async () => {
    const useAllSeasons = selectedSeason === 'ALL' || selectedSeason === 'last7' || selectedSeason === 'last10';
    const maxYears = selectedSeason === 'last7' ? 7 : selectedSeason === 'last10' ? 10 : 10;
    
    setLoadingState('referee-batch', true);
    try {
      const response = await apiClient.batchIngestRefereeStats({
        leagueCodes: selectedLeagues.length === allLeagues.length ? undefined : selectedLeagues,
        season: useAllSeasons ? undefined : selectedSeason,
        useAllLeagues: selectedLeagues.length === allLeagues.length,
        useAllSeasons: useAllSeasons,
        maxYears: maxYears,
        saveCsv: true
      });
      setResult('referee-batch', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: `Referee batch ingestion complete: ${response.data?.successful || 0} successful, ${response.data?.failed || 0} failed`
      });
    } catch (error: any) {
      setResult('referee-batch', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to batch ingest referee stats',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('referee-batch', false);
    }
  };

  // Referee Stats
  const [refereeId, setRefereeId] = useState<string>('');
  const [refereeName, setRefereeName] = useState<string>('');

  const handleIngestReferee = async () => {
    if (!refereeId) {
      toast({
        title: 'Error',
        description: 'Please enter referee ID',
        variant: 'destructive'
      });
      return;
    }

    setLoadingState('referee', true);
    try {
      const response = await apiClient.ingestRefereeStats(
        parseInt(refereeId),
        refereeName || undefined
      );
      setResult('referee', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: 'Referee statistics ingested successfully'
      });
    } catch (error: any) {
      setResult('referee', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to ingest referee stats',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('referee', false);
    }
  };

  // Rest Days Batch
  const handleBatchIngestRestDays = async () => {
    const useAllSeasons = selectedSeason === 'ALL' || selectedSeason === 'last7' || selectedSeason === 'last10';
    const maxYears = selectedSeason === 'last7' ? 7 : selectedSeason === 'last10' ? 10 : 10;
    
    setLoadingState('rest-days-batch', true);
    try {
      const response = await apiClient.batchIngestRestDays({
        leagueCodes: selectedLeagues.length === allLeagues.length ? undefined : selectedLeagues,
        season: useAllSeasons ? undefined : selectedSeason,
        useAllLeagues: selectedLeagues.length === allLeagues.length,
        useAllSeasons: useAllSeasons,
        maxYears: maxYears,
        saveCsv: true
      });
      setResult('rest-days-batch', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: `Rest days batch calculation complete: ${response.data?.successful || 0} successful, ${response.data?.failed || 0} failed`
      });
    } catch (error: any) {
      setResult('rest-days-batch', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to batch calculate rest days',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('rest-days-batch', false);
    }
  };

  // Rest Days
  const [restDaysFixtureId, setRestDaysFixtureId] = useState<string>('');

  const handleIngestRestDays = async () => {
    if (!restDaysFixtureId) {
      toast({
        title: 'Error',
        description: 'Please enter fixture ID',
        variant: 'destructive'
      });
      return;
    }

    setLoadingState('rest-days', true);
    try {
      const response = await apiClient.ingestRestDays(parseInt(restDaysFixtureId));
      setResult('rest-days', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: 'Rest days calculated successfully'
      });
    } catch (error: any) {
      setResult('rest-days', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to calculate rest days',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('rest-days', false);
    }
  };

  // Odds Movement Batch
  const handleBatchIngestOddsMovement = async () => {
    const useAllSeasons = selectedSeason === 'ALL' || selectedSeason === 'last7' || selectedSeason === 'last10';
    const maxYears = selectedSeason === 'last7' ? 7 : selectedSeason === 'last10' ? 10 : 10;
    
    setLoadingState('odds-movement-batch', true);
    try {
      const response = await apiClient.batchIngestOddsMovement({
        leagueCodes: selectedLeagues.length === allLeagues.length ? undefined : selectedLeagues,
        season: useAllSeasons ? undefined : selectedSeason,
        useAllLeagues: selectedLeagues.length === allLeagues.length,
        useAllSeasons: useAllSeasons,
        maxYears: maxYears,
        saveCsv: true
      });
      setResult('odds-movement-batch', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: `Odds movement batch ingestion complete: ${response.data?.successful || 0} successful, ${response.data?.failed || 0} failed`
      });
    } catch (error: any) {
      setResult('odds-movement-batch', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to batch ingest odds movement',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('odds-movement-batch', false);
    }
  };

  // Weather Batch
  const handleBatchIngestWeather = async () => {
    const useAllSeasons = selectedSeason === 'ALL' || selectedSeason === 'last7' || selectedSeason === 'last10';
    const maxYears = selectedSeason === 'last7' ? 7 : selectedSeason === 'last10' ? 10 : 10;
    
    setLoadingState('weather-batch', true);
    try {
      const response = await apiClient.batchIngestWeather({
        leagueCodes: selectedLeagues.length === allLeagues.length ? undefined : selectedLeagues,
        season: useAllSeasons ? undefined : selectedSeason,
        useAllLeagues: selectedLeagues.length === allLeagues.length,
        useAllSeasons: useAllSeasons,
        maxYears: maxYears,
        saveCsv: true
      });
      setResult('weather-batch', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: `Weather batch ingestion complete: ${response.data?.successful || 0} successful, ${response.data?.failed || 0} failed`
      });
    } catch (error: any) {
      setResult('weather-batch', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to batch ingest weather',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('weather-batch', false);
    }
  };

  // Odds Movement
  const [oddsFixtureId, setOddsFixtureId] = useState<string>('');
  const [drawOdds, setDrawOdds] = useState<string>('');

  const handleIngestOddsMovement = async () => {
    if (!oddsFixtureId) {
      toast({
        title: 'Error',
        description: 'Please enter fixture ID',
        variant: 'destructive'
      });
      return;
    }

    setLoadingState('odds-movement', true);
    try {
      const response = await apiClient.ingestOddsMovement(
        parseInt(oddsFixtureId),
        drawOdds ? parseFloat(drawOdds) : undefined
      );
      setResult('odds-movement', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: 'Odds movement tracked successfully'
      });
    } catch (error: any) {
      setResult('odds-movement', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to track odds movement',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('odds-movement', false);
    }
  };

  // xG Data Individual
  const [xgFixtureId, setXgFixtureId] = useState<string>('');
  const [xgMatchId, setXgMatchId] = useState<string>('');
  const [xgHome, setXgHome] = useState<string>('');
  const [xgAway, setXgAway] = useState<string>('');

  const handleIngestXGData = async () => {
    if ((!xgFixtureId && !xgMatchId) || !xgHome || !xgAway) {
      toast({
        title: 'Error',
        description: 'Please provide either fixture_id or match_id, and both xG values',
        variant: 'destructive'
      });
      return;
    }

    setLoadingState('xg-data', true);
    try {
      const response = await apiClient.ingestXGData(
        xgFixtureId ? parseInt(xgFixtureId) : undefined,
        xgMatchId ? parseInt(xgMatchId) : undefined,
        parseFloat(xgHome),
        parseFloat(xgAway)
      );
      setResult('xg-data', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: 'xG data ingested successfully'
      });
      fetchXGDataSummary();
    } catch (error: any) {
      setResult('xg-data', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to ingest xG data',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('xg-data', false);
    }
  };

  // xG Data Batch
  const handleBatchIngestXGData = async () => {
    const useAllSeasons = selectedSeason === 'ALL' || selectedSeason === 'last7' || selectedSeason === 'last10';
    const maxYears = selectedSeason === 'last7' ? 7 : selectedSeason === 'last10' ? 10 : 10;
    
    setLoadingState('xg-data-batch', true);
    try {
      const response = await apiClient.batchIngestXGData({
        leagueCodes: selectedLeagues.length === allLeagues.length ? undefined : selectedLeagues,
        season: useAllSeasons ? undefined : selectedSeason,
        useAllLeagues: selectedLeagues.length === allLeagues.length,
        useAllSeasons: useAllSeasons,
        maxYears: useAllSeasons ? maxYears : undefined,
        saveCsv: true
      });
      setResult('xg-data-batch', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: `xG data batch ingestion complete: ${response.data?.successful || 0} successful, ${response.data?.failed || 0} failed`
      });
      fetchXGDataSummary();
    } catch (error: any) {
      setResult('xg-data-batch', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to batch ingest xG data',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('xg-data-batch', false);
    }
  };

  // Team Form Batch
  const [matchesCount, setMatchesCount] = useState<number>(5);

  const handleBatchIngestTeamForm = async () => {
    if (selectedLeagues.length === 0) {
      toast({
        title: 'Error',
        description: 'Please select at least one league',
        variant: 'destructive'
      });
      return;
    }

    const useAllSeasons = selectedSeason === 'ALL' || selectedSeason === 'last7' || selectedSeason === 'last10';
    const maxYears = selectedSeason === 'last7' ? 7 : selectedSeason === 'last10' ? 10 : 10;
    const useAllLeagues = selectedLeagues.length === allLeagues.length;
    
    setLoadingState('team-form-batch', true);
    setResult('team-form-batch', null);
    try {
      const response = await apiClient.batchIngestTeamForm({
        leagueCodes: useAllLeagues ? undefined : selectedLeagues,
        season: useAllSeasons ? 'ALL' : selectedSeason,
        useAllLeagues: useAllLeagues,
        useAllSeasons: useAllSeasons,
        maxYears: useAllSeasons ? maxYears : undefined,
        saveCsv: true,
        matchesCount: matchesCount
      });
      
      if (response.success) {
        setResult('team-form-batch', { success: true, data: response.data });
        toast({
          title: 'Success',
          description: response.message || `Team form batch ingestion complete: ${response.data?.successful || 0} successful, ${response.data?.failed || 0} failed`
        });
      } else {
        throw new Error(response.message || 'Batch ingestion failed');
      }
    } catch (error: any) {
      const errorMessage = error.message || error.response?.data?.detail || 'Failed to batch ingest team form';
      setResult('team-form-batch', { success: false, error: errorMessage });
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive'
      });
    } finally {
      setLoadingState('team-form-batch', false);
    }
  };

  // Team Injuries Download from API
  const handleDownloadTeamInjuries = async () => {
    if (selectedLeagues.length === 0) {
      toast({
        title: 'Error',
        description: 'Please select at least one league',
        variant: 'destructive'
      });
      return;
    }

    const useAllLeagues = selectedLeagues.length === allLeagues.length;
    
    setLoadingState('team-injuries-download', true);
    setResult('team-injuries-download', null);
    try {
      const response = await apiClient.downloadTeamInjuries({
        leagueCodes: useAllLeagues ? undefined : selectedLeagues,
        useAllLeagues: useAllLeagues,
        source: 'api-football'
      });
      
      if (response.success) {
        setResult('team-injuries-download', { success: true, data: response.data });
        toast({
          title: 'Success',
          description: response.message || `Injuries downloaded: ${response.data?.successful || 0} successful`
        });
        // Refresh summary after successful download
        fetchTeamInjuriesSummary();
      } else {
        throw new Error(response.message || 'Download failed');
      }
    } catch (error: any) {
      const errorMessage = error.message || error.response?.data?.detail || 'Failed to download team injuries';
      setResult('team-injuries-download', { success: false, error: errorMessage });
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive'
      });
    } finally {
      setLoadingState('team-injuries-download', false);
    }
  };

  // Team Injuries Import from CSV
  const handleImportTeamInjuriesFromCsv = async (file: File) => {
    setLoadingState('team-injuries-import', true);
    setResult('team-injuries-import', null);
    try {
      const response = await apiClient.importTeamInjuriesFromCsv(file);
      
      if (response.success) {
        setResult('team-injuries-import', { success: true, data: response.data });
        toast({
          title: 'Success',
          description: response.message || `Team injuries imported successfully: ${response.data?.inserted || 0} inserted, ${response.data?.updated || 0} updated`
        });
        // Refresh summary after successful import
        fetchTeamInjuriesSummary();
      } else {
        throw new Error(response.message || 'CSV import failed');
      }
    } catch (error: any) {
      const errorMessage = error.message || error.response?.data?.detail || 'Failed to import team injuries from CSV';
      setResult('team-injuries-import', { success: false, error: errorMessage });
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive'
      });
    } finally {
      setLoadingState('team-injuries-import', false);
    }
  };

  // Team Injuries Batch
  const handleBatchIngestTeamInjuries = async () => {
    if (selectedLeagues.length === 0) {
      toast({
        title: 'Error',
        description: 'Please select at least one league',
        variant: 'destructive'
      });
      return;
    }

    const useAllLeagues = selectedLeagues.length === allLeagues.length;
    
    setLoadingState('team-injuries-batch', true);
    setResult('team-injuries-batch', null);
    try {
      const response = await apiClient.batchIngestTeamInjuries({
        leagueCodes: useAllLeagues ? undefined : selectedLeagues,
        useAllLeagues: useAllLeagues,
        saveCsv: true
      });
      
      if (response.success) {
        setResult('team-injuries-batch', { success: true, data: response.data });
        toast({
          title: 'Success',
          description: response.message || `Team injuries batch export complete: ${response.data?.successful || 0} exported, ${response.data?.skipped || 0} skipped`
        });
      } else {
        throw new Error(response.message || 'Batch export failed');
      }
    } catch (error: any) {
      const errorMessage = error.message || error.response?.data?.detail || 'Failed to batch export team injuries';
      setResult('team-injuries-batch', { success: false, error: errorMessage });
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive'
      });
    } finally {
      setLoadingState('team-injuries-batch', false);
    }
  };

  // League Structure Individual
  const handleIngestLeagueStructure = async () => {
    if (!selectedLeagueCode || !selectedLeagueSeason) {
      toast({
        title: 'Error',
        description: 'Please select a league and season',
        variant: 'destructive',
      });
      return;
    }

    setLoadingState('league-structure', true);
    setResult('league-structure', null);

    try {
      const options: {
        totalTeams?: number;
        relegationZones?: number;
        promotionZones?: number;
        playoffZones?: number;
        saveCsv?: boolean;
      } = {
        saveCsv: true,
      };

      if (totalTeams) options.totalTeams = parseInt(totalTeams);
      if (relegationZones) options.relegationZones = parseInt(relegationZones);
      if (promotionZones) options.promotionZones = parseInt(promotionZones);
      if (playoffZones) options.playoffZones = parseInt(playoffZones);

      const response = await apiClient.ingestLeagueStructure(
        selectedLeagueCode,
        selectedLeagueSeason,
        options
      );

      setResult('league-structure', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: `League structure ingested successfully for ${selectedLeagueCode} (${selectedLeagueSeason})`,
      });

      // Refresh summary after successful ingestion
      if (response.success) fetchLeagueStructureSummary();
    } catch (error: any) {
      setResult('league-structure', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to ingest league structure',
        variant: 'destructive',
      });
    } finally {
      setLoadingState('league-structure', false);
    }
  };

  // League Structure Batch
  const handleBatchIngestLeagueStructure = async () => {
    const useAllSeasons = selectedSeason === 'ALL' || selectedSeason === 'last7' || selectedSeason === 'last10';
    const maxYears = selectedSeason === 'last7' ? 7 : selectedSeason === 'last10' ? 10 : 10;
    
    setLoadingState('league-structure-batch', true);
    try {
      const response = await apiClient.batchIngestLeagueStructure({
        leagueCodes: selectedLeagues.length === allLeagues.length ? undefined : selectedLeagues,
        season: useAllSeasons ? undefined : selectedSeason,
        useAllLeagues: selectedLeagues.length === allLeagues.length,
        useAllSeasons: useAllSeasons,
        maxYears: maxYears,
        saveCsv: true
      });
      setResult('league-structure-batch', { success: true, data: response.data });
      toast({
        title: 'Success',
        description: `League structure batch ingestion complete: ${response.data?.successful || 0} successful, ${response.data?.failed || 0} failed`
      });
    } catch (error: any) {
      setResult('league-structure-batch', { success: false, error: error.message });
      toast({
        title: 'Error',
        description: error.message || 'Failed to batch ingest league structure',
        variant: 'destructive'
      });
    } finally {
      setLoadingState('league-structure-batch', false);
    }
  };

  // Import all draw structural data
  const handleImportAll = async () => {
    setImportAllResult(null);
    setImportingAll(true);
    try {
      const response = await apiClient.importAllDrawStructuralData({
        useAllLeagues: true,
        useAllSeasons: true,
        maxYears: 10,
        useHybridImport: true,  // Use CSV-first hybrid approach
      });
      
      if (response.success) {
        setImportAllResult({
          success: true,
          message: response.message || 'Import completed successfully',
          data: response.data,
        });
        toast({
          title: 'Import Successful',
          description: response.message || 'All draw structural data imported successfully',
          variant: 'default',
        });
        
        // Refresh all summaries after import
        fetchPriorsSummary();
        fetchH2HSummary();
        fetchEloSummary();
        fetchWeatherSummary();
        fetchRefereeSummary();
        fetchRestDaysSummary();
        fetchLeagueStructureSummary();
        fetchOddsMovementSummary();
        fetchXGDataSummary();
      } else {
        setImportAllResult({
          success: false,
          message: response.message || 'Import failed',
          data: response.data,
        });
        toast({
          title: 'Import Failed',
          description: response.message || 'Failed to import draw structural data',
          variant: 'destructive',
        });
      }
    } catch (error: any) {
      const errorMessage = error?.message || 'An error occurred during import';
      setImportAllResult({
        success: false,
        message: errorMessage,
      });
      toast({
        title: 'Import Error',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setImportingAll(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Import All Button Card */}
      <Card className="border-2 border-primary/20 bg-gradient-to-r from-primary/5 to-primary/10">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-primary" />
                One-Click Import All Draw Structural Data
              </CardTitle>
              <CardDescription className="mt-2">
                Import all 11 data types in the correct order (Weather last). Includes: League Priors, League Structure, Elo Ratings, H2H Stats, Odds Movement, Referee Stats, Rest Days, xG Data, Team Form, Team Injuries, and Weather. 
                Data will be saved to both <code className="text-xs">data/1_data_ingestion/Draw_structural/</code> and <code className="text-xs">data/2_Cleaned_data/Draw_structural/</code>
              </CardDescription>
            </div>
            <Button
              onClick={handleImportAll}
              disabled={importingAll}
              size="lg"
              className="gap-2"
            >
              {importingAll ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Importing...
                </>
              ) : (
                <>
                  <Download className="h-5 w-5" />
                  Import All
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        {importAllResult && (
          <CardContent>
            <Alert variant={importAllResult.success ? 'default' : 'destructive'}>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-2">
                  <p className="font-semibold">{importAllResult.message}</p>
                  {importAllResult.data && (
                    <div className="space-y-2 text-sm">
                      <div className="grid grid-cols-3 gap-4 mt-2">
                        <div>
                          <p className="text-muted-foreground">Total Successful</p>
                          <p className="text-lg font-bold text-green-600">
                            {importAllResult.data.summary.total_successful}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Total Failed</p>
                          <p className="text-lg font-bold text-red-600">
                            {importAllResult.data.summary.total_failed}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">All Completed</p>
                          <p className="text-lg font-bold">
                            {importAllResult.data.summary.all_completed ? (
                              <CheckCircle className="h-5 w-5 text-green-600 inline" />
                            ) : (
                              <AlertCircle className="h-5 w-5 text-yellow-600 inline" />
                            )}
                          </p>
                        </div>
                      </div>
                      <div className="mt-4 space-y-1">
                        <p className="font-medium text-xs">Import Results by Data Type:</p>
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          {Object.entries(importAllResult.data.results).map(([key, result]: [string, any]) => (
                            <div key={key} className="flex items-center justify-between p-2 border rounded">
                              <span className="capitalize">{key.replace('_', ' ')}</span>
                              <Badge variant={result.success ? 'default' : 'destructive'}>
                                {result.success ? '✓' : '✗'}
                              </Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </AlertDescription>
            </Alert>
          </CardContent>
        )}
      </Card>

      <Tabs defaultValue="match-odds" className="space-y-4">
        <div className="w-full border-b border-border/40">
        <TabsList className="w-full h-auto justify-start gap-1 bg-transparent p-0 flex-wrap">
          <TabsTrigger value="match-odds" className="h-10 px-4 text-sm">
            <Globe className="h-4 w-4 mr-2" />
            Match & Odds
          </TabsTrigger>
          <TabsTrigger value="league-priors" className="h-10 px-4 text-sm">
            <BarChart3 className="h-4 w-4 mr-2" />
            League Priors
          </TabsTrigger>
          <TabsTrigger value="h2h" className="h-10 px-4 text-sm">
            <Users className="h-4 w-4 mr-2" />
            H2H Stats
          </TabsTrigger>
          <TabsTrigger value="elo" className="h-10 px-4 text-sm">
            <TrendingUp className="h-4 w-4 mr-2" />
            Elo Ratings
          </TabsTrigger>
          <TabsTrigger value="xg" className="h-10 px-4 text-sm">
            <Target className="h-4 w-4 mr-2" />
            xG Data
          </TabsTrigger>
          <TabsTrigger value="weather" className="h-10 px-4 text-sm">
            <CloudRain className="h-4 w-4 mr-2" />
            Weather
          </TabsTrigger>
          <TabsTrigger value="referee" className="h-10 px-4 text-sm">
            <Users className="h-4 w-4 mr-2" />
            Referee
          </TabsTrigger>
          <TabsTrigger value="rest-days" className="h-10 px-4 text-sm">
            <Clock className="h-4 w-4 mr-2" />
            Rest Days
          </TabsTrigger>
          <TabsTrigger value="league-structure" className="h-10 px-4 text-sm">
            <Database className="h-4 w-4 mr-2" />
            League Structure
          </TabsTrigger>
          <TabsTrigger value="odds-movement" className="h-10 px-4 text-sm">
            <DollarSign className="h-4 w-4 mr-2" />
            Odds Movement
          </TabsTrigger>
          <TabsTrigger value="team-form" className="h-10 px-4 text-sm">
            <TrendingUp className="h-4 w-4 mr-2" />
            Team Form
          </TabsTrigger>
          <TabsTrigger value="team-injuries" className="h-10 px-4 text-sm">
            <AlertTriangle className="h-4 w-4 mr-2" />
            Team Injuries
          </TabsTrigger>
        </TabsList>
      </div>

      {/* Match-Level Outcome & Odds */}
      <TabsContent value="match-odds" className="space-y-4">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-semibold">Source: Football-Data.org (FREE tier) - Core Backbone</p>
              <div>
                <p className="font-medium mb-1">What You Get:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Fixtures (past & upcoming)</li>
                  <li>Final scores, 1X2 odds (multiple bookmakers)</li>
                  <li>Match status, kickoff time</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Why It Helps:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Primary training labels</li>
                  <li>Odds = market prior (not oracle)</li>
                  <li>Enables odds blending + calibration</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Draw Relevance:</p>
                <p className="text-sm ml-2">
                  <strong>Market draw odds are often better calibrated than model raw outputs</strong>. Crucial for draw probability correction.
                </p>
              </div>
            </div>
          </AlertDescription>
        </Alert>
        <Card>
          <CardHeader>
            <CardTitle>Match-Level Outcome & Odds Data</CardTitle>
            <CardDescription>
              Core backbone data source for fixtures and market odds
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                This data is typically ingested through the main Football-Data.co.uk ingestion pipeline.
                Use the "Football-Data.co.uk" tab for bulk historical data ingestion.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </TabsContent>

      {/* League Draw Priors */}
      <TabsContent value="league-priors" className="space-y-4">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-semibold">Source: Football-Data.co.uk (FREE CSV)</p>
              <div>
                <p className="font-medium mb-1">What You Get:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>20+ years of league results</li>
                  <li>Goals, halftime/fulltime scores</li>
                  <li>Closing odds (1X2) from multiple bookmakers</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Why It Helps:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Long-horizon stability for model training</li>
                  <li>Low variance draw frequency estimation</li>
                  <li>League-specific draw baselines</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Draw Relevance:</p>
                <p className="text-sm ml-2">
                  Draw rate is <strong>league-structural, not seasonal noise</strong>. Enables league draw priors (mandatory for jackpot pools).
                </p>
              </div>
            </div>
          </AlertDescription>
        </Alert>

        <Card>
          <CardHeader>
            <CardTitle>Data Format</CardTitle>
            <CardDescription>
              CSV format from Football-Data.co.uk
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium mb-2">Required CSV Columns:</p>
              <div className="bg-muted p-3 rounded-md font-mono text-xs space-y-1">
                <div><span className="text-primary">FTHG</span> - Full Time Home Goals (integer)</div>
                <div><span className="text-primary">FTAG</span> - Full Time Away Goals (integer)</div>
                <div className="text-muted-foreground mt-2">Optional: <span className="text-foreground">FTR</span> - Full Time Result (H/A/D)</div>
              </div>
            </div>
            
            <div>
              <p className="text-sm font-medium mb-2">Example CSV Row:</p>
              <div className="bg-muted p-3 rounded-md font-mono text-xs overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b">
                      <th className="px-2">Date</th>
                      <th className="px-2">Div</th>
                      <th className="px-2">HomeTeam</th>
                      <th className="px-2">AwayTeam</th>
                      <th className="px-2 text-primary">FTHG</th>
                      <th className="px-2 text-primary">FTAG</th>
                      <th className="px-2">FTR</th>
                      <th className="px-2">B365H</th>
                      <th className="px-2">B365D</th>
                      <th className="px-2">B365A</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="px-2">15/01/2024</td>
                      <td className="px-2">E0</td>
                      <td className="px-2">Arsenal</td>
                      <td className="px-2">Chelsea</td>
                      <td className="px-2 text-primary font-bold">2</td>
                      <td className="px-2 text-primary font-bold">2</td>
                      <td className="px-2">D</td>
                      <td className="px-2">1.85</td>
                      <td className="px-2">3.40</td>
                      <td className="px-2">4.20</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div>
              <p className="text-sm font-medium mb-2">Processing Logic:</p>
              <div className="bg-muted p-3 rounded-md text-sm space-y-2">
                <div className="flex items-start gap-2">
                  <span className="font-bold text-primary">1.</span>
                  <span>Read CSV file and identify matches where <code className="bg-background px-1 rounded">FTHG == FTAG</code> (draw)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-bold text-primary">2.</span>
                  <span>Calculate draw rate: <code className="bg-background px-1 rounded">draw_rate = draws / total_matches</code></span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-bold text-primary">3.</span>
                  <span>Store in <code className="bg-background px-1 rounded">league_draw_priors</code> table with:</span>
                </div>
                <div className="ml-6 space-y-1 text-xs font-mono">
                  <div>• <span className="text-primary">league_id</span> - League identifier</div>
                  <div>• <span className="text-primary">season</span> - Season (e.g., "2023-24" or "ALL")</div>
                  <div>• <span className="text-primary">draw_rate</span> - Calculated rate (0.0 - 1.0)</div>
                  <div>• <span className="text-primary">sample_size</span> - Number of matches analyzed</div>
                </div>
              </div>
            </div>

            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription className="text-xs">
                <strong>Note:</strong> The system can also calculate draw priors from the existing <code>matches</code> table 
                if CSV files are not available. Select a league and season, then click "Ingest League Priors".
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>League Draw Priors</CardTitle>
            <CardDescription>
              Ingest historical draw rates per league/season from matches table
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* League Selection */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label>Select Leagues</Label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={selectAllLeagues}
                  className="h-8 text-xs"
                >
                  {selectedLeagues.length === allLeagues.length ? (
                    <>
                      <Square className="h-3 w-3 mr-1" />
                      Deselect All
                    </>
                  ) : (
                    <>
                      <CheckSquare className="h-3 w-3 mr-1" />
                      Select All
                    </>
                  )}
                </Button>
              </div>
              <div className="border rounded-md p-3 max-h-48 overflow-y-auto">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {allLeagues.map(league => (
                    <div key={league.code} className="flex items-center space-x-2">
                      <Checkbox
                        id={`league-${league.code}`}
                        checked={selectedLeagues.includes(league.code)}
                        onCheckedChange={() => toggleLeague(league.code)}
                      />
                      <Label
                        htmlFor={`league-${league.code}`}
                        className="text-sm font-normal cursor-pointer"
                      >
                        {league.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
              {selectedLeagues.length > 0 && (
                <p className="text-xs text-muted-foreground mt-2">
                  {selectedLeagues.length} league{selectedLeagues.length !== 1 ? 's' : ''} selected
                </p>
              )}
            </div>

            {/* Season Selection */}
            <div>
              <Label>Season</Label>
              <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {seasonsList.map((season) => (
                    <SelectItem key={season} value={season}>
                      {season}
                    </SelectItem>
                  ))}
                  <SelectItem value="last7">Last 7 Seasons (Ideal)</SelectItem>
                  <SelectItem value="last10">Last 10 Seasons (Diminishing Returns)</SelectItem>
                  <SelectItem value="ALL">All Seasons</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              onClick={handleIngestLeaguePriors}
              disabled={loading['league-priors'] || selectedLeagues.length === 0}
              className="w-full"
            >
              {loading['league-priors'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Ingesting...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Ingest League Priors ({selectedLeagues.length} league{selectedLeagues.length !== 1 ? 's' : ''})
                </>
              )}
            </Button>
            {results['league-priors'] && (
              <Alert>
                {results['league-priors'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['league-priors'].success ? (
                    <div className="space-y-1">
                      <div>
                        Processed {results['league-priors'].data?.successful || 0}/{results['league-priors'].data?.processed || 0} league/season combinations successfully
                      </div>
                      {results['league-priors'].data?.failed > 0 && (
                        <div className="text-yellow-600 text-sm">
                          {results['league-priors'].data?.failed} failed, {results['league-priors'].data?.skipped || 0} skipped
                        </div>
                      )}
                    </div>
                  ) : (
                    results['league-priors'].error
                  )}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* League Priors Summary */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Ingestion Summary</CardTitle>
                <CardDescription>
                  Overview of league draw priors in the database
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchPriorsSummary}
                disabled={loadingSummary['priors']}
              >
                {loadingSummary['priors'] ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loadingSummary['priors'] ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : priorsSummary ? (
              <div className="space-y-4">
                {/* Overall Statistics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Total Priors</p>
                    <p className="text-2xl font-bold">{priorsSummary.total_priors.toLocaleString()}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Leagues with Priors</p>
                    <p className="text-2xl font-bold">
                      {priorsSummary.leagues_with_priors}/{priorsSummary.total_leagues}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Unique Seasons</p>
                    <p className="text-2xl font-bold">{priorsSummary.unique_seasons}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Last Updated</p>
                    <p className="text-sm font-medium">
                      {priorsSummary.last_updated
                        ? new Date(priorsSummary.last_updated).toLocaleString()
                        : 'Never'}
                    </p>
                  </div>
                </div>

                {/* League Breakdown */}
                {priorsSummary.by_league.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold mb-3">Priors by League</h4>
                    <div className="border rounded-md">
                      <div className="max-h-64 overflow-y-auto">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 p-3">
                          {priorsSummary.by_league.map((league) => (
                            <div
                              key={league.code}
                              className="flex items-center justify-between p-2 rounded-md bg-muted/50 hover:bg-muted transition-colors"
                            >
                              <div>
                                <p className="text-sm font-medium">{league.name}</p>
                                <p className="text-xs text-muted-foreground">{league.code}</p>
                              </div>
                              <div className="text-right">
                                <p className="text-sm font-bold">{league.count}</p>
                                <p className="text-xs text-muted-foreground">prior{league.count !== 1 ? 's' : ''}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No summary data available</p>
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      {/* H2H Stats */}
      <TabsContent value="h2h" className="space-y-4">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-semibold">Source: API-Football (FREE tier)</p>
              <div>
                <p className="font-medium mb-1">What You Get:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Historical meetings between two teams</li>
                  <li>Goals scored, wins/draws/losses</li>
                  <li>Venue-specific H2H statistics</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Why It Helps:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Captures stylistic stalemates</li>
                  <li>Rivalry effects and tactical deadlocks</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Draw Relevance:</p>
                <p className="text-sm ml-2">
                  <strong>Repeated low-goal H2H → draw inflation factor</strong>. Especially powerful when Poisson home ≈ away.
                </p>
              </div>
            </div>
          </AlertDescription>
        </Alert>

        <Card>
          <CardHeader>
            <CardTitle>Data Format</CardTitle>
            <CardDescription>
              API response format from API-Football
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium mb-2">API Endpoint:</p>
              <div className="bg-muted p-3 rounded-md font-mono text-xs">
                <div>GET https://v3.football.api-sports.io/fixtures/headtohead</div>
                <div className="text-muted-foreground mt-1">{'Query: h2h={team_home_id}-{team_away_id}'}</div>
              </div>
            </div>
            
            <div>
              <p className="text-sm font-medium mb-2">Response Structure:</p>
              <div className="bg-muted p-3 rounded-md font-mono text-xs space-y-1">
                <div>{'{'}</div>
                <div className="ml-2">"response": [</div>
                <div className="ml-4">{'{'}</div>
                <div className="ml-6">"goals": {'{'}"home": 2, "away": 2{'}'},</div>
                <div className="ml-6">"fixture": {'{'}"id": 12345{'}'}</div>
                <div className="ml-4">{'}'}</div>
                <div className="ml-2">]</div>
                <div>{'}'}</div>
              </div>
            </div>

            <div>
              <p className="text-sm font-medium mb-2">Processing Logic:</p>
              <div className="bg-muted p-3 rounded-md text-sm space-y-2">
                <div className="flex items-start gap-2">
                  <span className="font-bold text-primary">1.</span>
                  <span>Fetch historical matches between two teams via API</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-bold text-primary">2.</span>
                  <span>Count draws: <code className="bg-background px-1 rounded">goals.home == goals.away</code></span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-bold text-primary">3.</span>
                  <span>Calculate draw rate: <code className="bg-background px-1 rounded">draw_count / matches_played</code></span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-bold text-primary">4.</span>
                  <span>Store in <code className="bg-background px-1 rounded">h2h_stats</code> table</span>
                </div>
              </div>
            </div>

            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription className="text-xs">
                <strong>Storage:</strong> Data saved to <code>data/1_data_ingestion/Draw_structural/h2h_stats/</code> folder structure.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Head-to-Head Statistics</CardTitle>
            <CardDescription>
              Ingest H2H draw statistics between two teams
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Home Team ID</Label>
                <Input
                  value={homeTeamId}
                  onChange={(e) => setHomeTeamId(e.target.value)}
                  placeholder="Team ID"
                  type="number"
                />
              </div>
              <div>
                <Label>Away Team ID</Label>
                <Input
                  value={awayTeamId}
                  onChange={(e) => setAwayTeamId(e.target.value)}
                  placeholder="Team ID"
                  type="number"
                />
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="use-h2h-api"
                checked={useH2HApi}
                onChange={(e) => setUseH2HApi(e.target.checked)}
                className="rounded"
              />
              <Label htmlFor="use-h2h-api">Use API-Football (requires API key)</Label>
            </div>
            <Button
              onClick={handleIngestH2H}
              disabled={loading['h2h'] || !homeTeamId || !awayTeamId}
              className="w-full"
            >
              {loading['h2h'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Ingesting...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Ingest H2H Stats
                </>
              )}
            </Button>
            {results['h2h'] && (
              <Alert>
                {results['h2h'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['h2h'].success
                    ? `Matches: ${results['h2h'].data?.matches_played}, Draws: ${results['h2h'].data?.draw_count}`
                    : results['h2h'].error}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Batch H2H Statistics</CardTitle>
            <CardDescription>
              Calculate H2H statistics for all team pairs in selected leagues and seasons
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Select Season</Label>
              <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                <SelectTrigger>
                  <SelectValue placeholder="Select season" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Seasons</SelectItem>
                  <SelectItem value="last7">Last 7 Seasons</SelectItem>
                  <SelectItem value="last10">Last 10 Seasons</SelectItem>
                  {seasonsList.map((season) => (
                    <SelectItem key={season} value={season}>
                      {season}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground mt-1">
                {selectedSeason === 'ALL' && 'Will process all historical matches between teams'}
                {selectedSeason === 'last7' && 'Will process matches from the last 7 seasons'}
                {selectedSeason === 'last10' && 'Will process matches from the last 10 seasons'}
                {selectedSeason !== 'ALL' && selectedSeason !== 'last7' && selectedSeason !== 'last10' && `Will process matches from ${selectedSeason} season`}
              </p>
            </div>
            <div>
              <Label>Select Leagues</Label>
              <div className="mt-2 space-y-2 max-h-48 overflow-y-auto border rounded-md p-3">
                <div className="flex items-center space-x-2 mb-2">
                  <input
                    type="checkbox"
                    id="select-all-h2h"
                    checked={selectedLeagues.length === allLeagues.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedLeagues(allLeagues.map(l => l.code));
                      } else {
                        setSelectedLeagues([]);
                      }
                    }}
                    className="rounded"
                  />
                  <Label htmlFor="select-all-h2h" className="font-semibold cursor-pointer">
                    Select All ({allLeagues.length} leagues)
                  </Label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {allLeagues.map((league) => (
                    <div key={league.code} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id={`league-h2h-${league.code}`}
                        checked={selectedLeagues.includes(league.code)}
                        onChange={() => toggleLeague(league.code)}
                        className="rounded"
                      />
                      <Label htmlFor={`league-h2h-${league.code}`} className="text-sm cursor-pointer">
                        {league.code} - {league.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Selected: {selectedLeagues.length} league{selectedLeagues.length !== 1 ? 's' : ''}
              </p>
            </div>
            <Button
              onClick={handleBatchIngestH2H}
              disabled={loading['h2h-batch'] || selectedLeagues.length === 0}
              className="w-full"
            >
              {loading['h2h-batch'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Database className="h-4 w-4 mr-2" />
                  Batch Ingest H2H Stats ({selectedLeagues.length === allLeagues.length ? 'All Leagues' : `${selectedLeagues.length} Leagues`})
                </>
              )}
            </Button>
            {results['h2h-batch'] && (
              <Alert>
                {results['h2h-batch'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['h2h-batch'].success ? (
                    <div className="space-y-1">
                      <div>Total Processed: {results['h2h-batch'].data?.total || 0}</div>
                      <div>Successful: {results['h2h-batch'].data?.successful || 0}</div>
                      <div>Failed: {results['h2h-batch'].data?.failed || 0}</div>
                    </div>
                  ) : (
                    results['h2h-batch'].error
                  )}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* H2H Stats Summary */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Ingestion Summary</CardTitle>
                <CardDescription>
                  Overview of H2H stats in the database
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchH2HSummary}
                disabled={loadingSummary['h2h']}
              >
                {loadingSummary['h2h'] ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loadingSummary['h2h'] ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : h2hSummary ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Total Records</p>
                    <p className="text-2xl font-bold">{h2hSummary.total_records.toLocaleString()}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Leagues with Stats</p>
                    <p className="text-2xl font-bold">
                      {h2hSummary.leagues_with_stats}/{h2hSummary.total_leagues}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Last Updated</p>
                    <p className="text-sm font-medium">
                      {h2hSummary.last_updated
                        ? new Date(h2hSummary.last_updated).toLocaleString()
                        : 'Never'}
                    </p>
                  </div>
                </div>
                {h2hSummary.by_league.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold mb-3">Stats by League</h4>
                    <div className="border rounded-md">
                      <div className="max-h-64 overflow-y-auto">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 p-3">
                          {h2hSummary.by_league.map((league) => (
                            <div
                              key={league.code}
                              className="flex items-center justify-between p-2 rounded-md bg-muted/50 hover:bg-muted transition-colors"
                            >
                              <div>
                                <p className="text-sm font-medium">{league.name}</p>
                                <p className="text-xs text-muted-foreground">{league.code}</p>
                              </div>
                              <div className="text-right">
                                <p className="text-sm font-bold">{league.count}</p>
                                <p className="text-xs text-muted-foreground">records</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No summary data available</p>
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      {/* Elo Ratings */}
      <TabsContent value="elo" className="space-y-4">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-semibold">Source: ClubElo (FREE CSV)</p>
              <div>
                <p className="font-medium mb-1">What You Get:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Daily Elo ratings per team</li>
                  <li>Attack/defense adjusted strength</li>
                  <li>Smooth, stable strength estimates</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Why It Helps:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Replaces subjective "form"</li>
                  <li>Provides smooth, stable strength estimates</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Draw Relevance:</p>
                <p className="text-sm ml-2">
                  <strong>Elo difference ≈ 0 → draw probability ↑</strong>. Strong empirical draw signal across leagues.
                </p>
              </div>
            </div>
          </AlertDescription>
        </Alert>

        <Card>
          <CardHeader>
            <CardTitle>Data Format</CardTitle>
            <CardDescription>
              CSV format from ClubElo or calculated from match history
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium mb-2">CSV Format (ClubElo):</p>
              <div className="bg-muted p-3 rounded-md font-mono text-xs space-y-1">
                <div><span className="text-primary">ClubID</span> - Team identifier</div>
                <div><span className="text-primary">From</span> - Date (YYYY-MM-DD)</div>
                <div><span className="text-primary">Elo</span> - Elo rating (float, typically 1000-2000)</div>
              </div>
            </div>
            
            <div>
              <p className="text-sm font-medium mb-2">Example CSV Row:</p>
              <div className="bg-muted p-3 rounded-md font-mono text-xs overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b">
                      <th className="px-2">ClubID</th>
                      <th className="px-2">From</th>
                      <th className="px-2 text-primary">Elo</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="px-2">1</td>
                      <td className="px-2">2024-01-15</td>
                      <td className="px-2 text-primary font-bold">1650.5</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div>
              <p className="text-sm font-medium mb-2">Processing Logic:</p>
              <div className="bg-muted p-3 rounded-md text-sm space-y-2">
                <div className="flex items-start gap-2">
                  <span className="font-bold text-primary">1.</span>
                  <span>Read Elo CSV or calculate from match results using Elo formula</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-bold text-primary">2.</span>
                  <span>Store daily ratings in <code className="bg-background px-1 rounded">team_elo</code> table</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-bold text-primary">3.</span>
                  <span>Calculate symmetry: <code className="bg-background px-1 rounded">exp(-abs(home_elo - away_elo) / 160)</code></span>
                </div>
              </div>
            </div>

            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription className="text-xs">
                <strong>Storage:</strong> Data saved to <code>data/Draw_structural/batch_{'{N}'}_Elo_Ratings/</code> folder structure.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Elo Ratings</CardTitle>
            <CardDescription>
              Calculate or ingest Elo ratings for teams
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Team ID (optional if calculating from matches)</Label>
              <Input
                value={teamId}
                onChange={(e) => setTeamId(e.target.value)}
                placeholder="Team ID"
                type="number"
              />
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="calculate-elo"
                checked={calculateEloFromMatches}
                onChange={(e) => setCalculateEloFromMatches(e.target.checked)}
                className="rounded"
              />
              <Label htmlFor="calculate-elo">Calculate from match history</Label>
            </div>
            <Button
              onClick={handleIngestElo}
              disabled={loading['elo'] || (!teamId && !calculateEloFromMatches)}
              className="w-full"
            >
              {loading['elo'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Ingest/Calculate Elo
                </>
              )}
            </Button>
            {results['elo'] && (
              <Alert>
                {results['elo'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['elo'].success
                    ? `Inserted: ${results['elo'].data?.inserted}, Updated: ${results['elo'].data?.updated}`
                    : results['elo'].error}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Batch Elo Ratings</CardTitle>
            <CardDescription>
              Calculate Elo ratings for all teams in selected leagues and seasons
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Select Season</Label>
              <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                <SelectTrigger>
                  <SelectValue placeholder="Select season" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Seasons</SelectItem>
                  <SelectItem value="last7">Last 7 Seasons</SelectItem>
                  <SelectItem value="last10">Last 10 Seasons</SelectItem>
                  {seasonsList.map((season) => (
                    <SelectItem key={season} value={season}>
                      {season}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Select Leagues</Label>
              <div className="mt-2 space-y-2 max-h-48 overflow-y-auto border rounded-md p-3">
                <div className="flex items-center space-x-2 mb-2">
                  <input
                    type="checkbox"
                    id="select-all-elo"
                    checked={selectedLeagues.length === allLeagues.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedLeagues(allLeagues.map(l => l.code));
                      } else {
                        setSelectedLeagues([]);
                      }
                    }}
                    className="rounded"
                  />
                  <Label htmlFor="select-all-elo" className="font-semibold cursor-pointer">
                    Select All ({allLeagues.length} leagues)
                  </Label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {allLeagues.map((league) => (
                    <div key={league.code} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id={`league-elo-${league.code}`}
                        checked={selectedLeagues.includes(league.code)}
                        onChange={() => toggleLeague(league.code)}
                        className="rounded"
                      />
                      <Label htmlFor={`league-elo-${league.code}`} className="text-sm cursor-pointer">
                        {league.code} - {league.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <Button
              onClick={handleBatchIngestElo}
              disabled={loading['elo-batch'] || selectedLeagues.length === 0}
              className="w-full"
            >
              {loading['elo-batch'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Database className="h-4 w-4 mr-2" />
                  Batch Calculate Elo Ratings ({selectedLeagues.length === allLeagues.length ? 'All Leagues' : `${selectedLeagues.length} Leagues`})
                </>
              )}
            </Button>
            {results['elo-batch'] && (
              <Alert>
                {results['elo-batch'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['elo-batch'].success ? (
                    <div className="space-y-1">
                      <div>Total Processed: {results['elo-batch'].data?.total || 0}</div>
                      <div>Successful: {results['elo-batch'].data?.successful || 0}</div>
                      <div>Failed: {results['elo-batch'].data?.failed || 0}</div>
                      <p className="text-xs text-muted-foreground mt-2">
                        CSV files saved to: <code>data/1_data_ingestion/Draw_structural/Elo_Rating/</code>
                      </p>
                    </div>
                  ) : (
                    results['elo-batch'].error
                  )}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Elo Ratings Summary */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Ingestion Summary</CardTitle>
                <CardDescription>
                  Overview of Elo ratings in the database
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchEloSummary}
                disabled={loadingSummary['elo']}
              >
                {loadingSummary['elo'] ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loadingSummary['elo'] ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : eloSummary ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Total Records</p>
                    <p className="text-2xl font-bold">{eloSummary.total_records.toLocaleString()}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Leagues with Elo</p>
                    <p className="text-2xl font-bold">
                      {eloSummary.leagues_with_elo}/{eloSummary.total_leagues}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Unique Dates</p>
                    <p className="text-2xl font-bold">{eloSummary.unique_dates}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Last Updated</p>
                    <p className="text-sm font-medium">
                      {eloSummary.last_updated
                        ? new Date(eloSummary.last_updated).toLocaleString()
                        : 'Never'}
                    </p>
                  </div>
                </div>
                {eloSummary.by_league.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold mb-3">Ratings by League</h4>
                    <div className="border rounded-md">
                      <div className="max-h-64 overflow-y-auto">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 p-3">
                          {eloSummary.by_league.map((league) => (
                            <div
                              key={league.code}
                              className="flex items-center justify-between p-2 rounded-md bg-muted/50 hover:bg-muted transition-colors"
                            >
                              <div>
                                <p className="text-sm font-medium">{league.name}</p>
                                <p className="text-xs text-muted-foreground">{league.code}</p>
                              </div>
                              <div className="text-right">
                                <p className="text-sm font-bold">{league.count}</p>
                                <p className="text-xs text-muted-foreground">records</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No summary data available</p>
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      {/* xG Data */}
      <TabsContent value="xg" className="space-y-4">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-semibold">Source: Manual Input or External APIs (Understat, FBref, Opta)</p>
              <div>
                <p className="font-medium mb-1">What You Get:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Expected goals (xG) for home and away teams</li>
                  <li>Total xG per match</li>
                  <li>Draw probability adjustment factor based on xG</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Why It Helps:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Separates dominance from finishing luck</li>
                  <li>Low xG matches (defensive) → higher draw probability</li>
                  <li>High xG matches (attacking) → lower draw probability</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Draw Relevance:</p>
                <p className="text-sm ml-2">
                  <strong>Low combined xG + symmetry → draw likelihood</strong>. Prevents overconfidence in 1-goal games.
                </p>
              </div>
              <div>
                <p className="font-medium mb-1">Storage:</p>
                <p className="text-sm ml-2">
                  Data saved to <code>data/1_data_ingestion/Draw_structural/xG_Data/</code> folder structure.
                </p>
              </div>
            </div>
          </AlertDescription>
        </Alert>

        <Card>
          <CardHeader>
            <CardTitle>xG Data</CardTitle>
            <CardDescription>
              Ingest Expected Goals (xG) data for individual fixtures or matches
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Fixture ID (for jackpot fixtures)</Label>
                <Input
                  type="number"
                  value={xgFixtureId}
                  onChange={(e) => setXgFixtureId(e.target.value)}
                  placeholder="Fixture ID (optional)"
                />
              </div>
              <div className="space-y-2">
                <Label>Match ID (for historical matches)</Label>
                <Input
                  type="number"
                  value={xgMatchId}
                  onChange={(e) => setXgMatchId(e.target.value)}
                  placeholder="Match ID (optional)"
                />
              </div>
              <div className="space-y-2">
                <Label>xG Home</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={xgHome}
                  onChange={(e) => setXgHome(e.target.value)}
                  placeholder="Expected goals for home team"
                />
              </div>
              <div className="space-y-2">
                <Label>xG Away</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={xgAway}
                  onChange={(e) => setXgAway(e.target.value)}
                  placeholder="Expected goals for away team"
                />
              </div>
            </div>
            <Button
              onClick={handleIngestXGData}
              disabled={loading['xg-data']}
              className="w-full"
            >
              {loading['xg-data'] ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Ingesting...
                </>
              ) : (
                <>
                  <Database className="mr-2 h-4 w-4" />
                  Ingest xG Data
                </>
              )}
            </Button>
            {results['xg-data'] && (
              <Alert variant={results['xg-data'].success ? 'default' : 'destructive'}>
                {results['xg-data'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['xg-data'].success ? (
                    <div>xG data ingested successfully</div>
                  ) : (
                    <div>{results['xg-data'].error}</div>
                  )}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Batch xG Data</CardTitle>
            <CardDescription>
              Batch ingest xG data for multiple leagues and seasons
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="xg-all-leagues"
                  checked={selectedLeagues.length === allLeagues.length}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedLeagues(allLeagues.map(l => l.code));
                    } else {
                      setSelectedLeagues([]);
                    }
                  }}
                />
                <Label htmlFor="xg-all-leagues" className="cursor-pointer">
                  Select All Leagues ({allLeagues.length} leagues)
                </Label>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Season</Label>
                  <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select season" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">All Seasons</SelectItem>
                      <SelectItem value="last7">Last 7 Seasons</SelectItem>
                      <SelectItem value="last10">Last 10 Seasons</SelectItem>
                      {seasonsList.map((season) => (
                        <SelectItem key={season} value={season}>
                          {season}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="max-h-40 overflow-y-auto border rounded p-2">
                <div className="grid grid-cols-2 gap-2">
                  {allLeagues.map((league) => (
                    <div key={league.code} className="flex items-center space-x-2">
                      <Checkbox
                        id={`xg-league-${league.code}`}
                        checked={selectedLeagues.includes(league.code)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setSelectedLeagues([...selectedLeagues, league.code]);
                          } else {
                            setSelectedLeagues(selectedLeagues.filter(l => l !== league.code));
                          }
                        }}
                      />
                      <Label htmlFor={`xg-league-${league.code}`} className="cursor-pointer text-sm">
                        {league.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <Button
              onClick={handleBatchIngestXGData}
              disabled={loading['xg-data-batch'] || selectedLeagues.length === 0}
              className="w-full"
            >
              {loading['xg-data-batch'] ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Database className="mr-2 h-4 w-4" />
                  Batch Ingest xG Data ({selectedLeagues.length === allLeagues.length ? 'All Leagues' : `${selectedLeagues.length} Leagues`})
                </>
              )}
            </Button>
            {results['xg-data-batch'] && (
              <Alert variant={results['xg-data-batch'].success ? 'default' : 'destructive'}>
                {results['xg-data-batch'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['xg-data-batch'].success ? (
                    <div>
                      <div>Batch ingestion complete: {results['xg-data-batch'].data?.successful || 0} successful, {results['xg-data-batch'].data?.failed || 0} failed</div>
                      <div className="mt-2 text-xs text-muted-foreground">
                        CSV files saved to: <code>data/1_data_ingestion/Draw_structural/xG_Data/</code>
                      </div>
                    </div>
                  ) : (
                    <div>{results['xg-data-batch'].error}</div>
                  )}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* xG Data Summary */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Ingestion Summary</CardTitle>
                <CardDescription>
                  Overview of xG data in the database
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchXGDataSummary}
                disabled={loadingSummary['xg-data']}
              >
                {loadingSummary['xg-data'] ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {xgDataSummary ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-2xl font-bold">{xgDataSummary.total_records.toLocaleString()}</p>
                    <p className="text-sm text-muted-foreground">Total Records</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{xgDataSummary.leagues_with_xg}</p>
                    <p className="text-sm text-muted-foreground">Leagues with xG</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{xgDataSummary.total_leagues}</p>
                    <p className="text-sm text-muted-foreground">Total Leagues</p>
                  </div>
                  <div>
                    <p className="text-sm font-semibold">
                      {xgDataSummary.last_updated
                        ? new Date(xgDataSummary.last_updated).toLocaleDateString()
                        : 'Never'}
                    </p>
                    <p className="text-sm text-muted-foreground">Last Updated</p>
                  </div>
                </div>
                {xgDataSummary.by_league && xgDataSummary.by_league.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold mb-3">xG Data by League</h4>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {xgDataSummary.by_league.map((league) => (
                        <div key={league.code} className="flex items-center justify-between p-2 border rounded">
                          <div>
                            <p className="font-medium">{league.name}</p>
                            <p className="text-xs text-muted-foreground">{league.code}</p>
                          </div>
                          <Badge variant="secondary">{league.count.toLocaleString()}</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No xG data summary available. Click refresh to load.</p>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      {/* Weather */}
      <TabsContent value="weather" className="space-y-4">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-semibold">Source: Open-Meteo (FREE API)</p>
              <div>
                <p className="font-medium mb-1">What You Get:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Temperature, rain/precipitation, wind speed</li>
                  <li>Weather conditions at match time</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Why It Helps:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Match tempo adjustment</li>
                  <li>Shot quality degradation modeling</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Draw Relevance:</p>
                <p className="text-sm ml-2">
                  <strong>Rain + wind → fewer goals → draw inflation</strong>. Particularly relevant in lower leagues.
                </p>
              </div>
            </div>
          </AlertDescription>
        </Alert>

        <Card>
          <CardHeader>
            <CardTitle>Data Format</CardTitle>
            <CardDescription>
              API response format from Open-Meteo
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium mb-2">API Endpoint:</p>
              <div className="bg-muted p-3 rounded-md font-mono text-xs">
                <div>GET https://api.open-meteo.com/v1/forecast</div>
                <div className="text-muted-foreground mt-1">Params: latitude, longitude, hourly=temperature_2m,rain,wind_speed_10m</div>
              </div>
            </div>
            
            <div>
              <p className="text-sm font-medium mb-2">Response Structure:</p>
              <div className="bg-muted p-3 rounded-md font-mono text-xs space-y-1">
                <div>{'{'}</div>
                <div className="ml-2">"hourly": {'{'}</div>
                <div className="ml-4">"temperature_2m": [15.2],</div>
                <div className="ml-4">"rain": [2.5],</div>
                <div className="ml-4">"wind_speed_10m": [12.3]</div>
                <div className="ml-2">{'}'}</div>
                <div>{'}'}</div>
              </div>
            </div>

            <div>
              <p className="text-sm font-medium mb-2">Processing Logic:</p>
              <div className="bg-muted p-3 rounded-md text-sm space-y-2">
                <div className="flex items-start gap-2">
                  <span className="font-bold text-primary">1.</span>
                  <span>Fetch weather data for match location and time</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-bold text-primary">2.</span>
                  <span>Calculate draw index: <code className="bg-background px-1 rounded">0.3 * rain + 0.2 * wind_speed</code></span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-bold text-primary">3.</span>
                  <span>Store in <code className="bg-background px-1 rounded">match_weather</code> table</span>
                </div>
              </div>
            </div>

            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription className="text-xs">
                <strong>Storage:</strong> Data saved to <code>data/Draw_structural/batch_{'{N}'}_Weather/</code> folder structure.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Weather Data</CardTitle>
            <CardDescription>
              Ingest weather conditions from Open-Meteo API
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Fixture ID</Label>
                <Input
                  value={fixtureId}
                  onChange={(e) => setFixtureId(e.target.value)}
                  placeholder="Fixture ID"
                  type="number"
                />
              </div>
              <div>
                <Label>Match Date/Time (ISO format)</Label>
                <Input
                  value={matchDatetime}
                  onChange={(e) => setMatchDatetime(e.target.value)}
                  placeholder="2024-01-15T15:00:00"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Latitude</Label>
                <Input
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  placeholder="51.5074"
                  type="number"
                  step="0.0001"
                />
              </div>
              <div>
                <Label>Longitude</Label>
                <Input
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  placeholder="-0.1278"
                  type="number"
                  step="0.0001"
                />
              </div>
            </div>
            <Button
              onClick={handleIngestWeather}
              disabled={loading['weather'] || !fixtureId || !latitude || !longitude || !matchDatetime}
              className="w-full"
            >
              {loading['weather'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Fetching...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Ingest Weather
                </>
              )}
            </Button>
            {results['weather'] && (
              <Alert>
                {results['weather'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['weather'].success
                    ? `Temp: ${results['weather'].data?.temperature}°C, Rain: ${results['weather'].data?.rainfall}mm, Wind: ${results['weather'].data?.wind_speed}km/h`
                    : results['weather'].error}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Batch Weather Data</CardTitle>
            <CardDescription>
              Ingest weather data for matches in selected leagues and seasons
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Select Season</Label>
              <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                <SelectTrigger>
                  <SelectValue placeholder="Select season" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Seasons</SelectItem>
                  <SelectItem value="last7">Last 7 Seasons</SelectItem>
                  <SelectItem value="last10">Last 10 Seasons</SelectItem>
                  {seasonsList.map((season) => (
                    <SelectItem key={season} value={season}>
                      {season}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Select Leagues</Label>
              <div className="mt-2 space-y-2 max-h-48 overflow-y-auto border rounded-md p-3">
                <div className="flex items-center space-x-2 mb-2">
                  <input
                    type="checkbox"
                    id="select-all-weather"
                    checked={selectedLeagues.length === allLeagues.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedLeagues(allLeagues.map(l => l.code));
                      } else {
                        setSelectedLeagues([]);
                      }
                    }}
                    className="rounded"
                  />
                  <Label htmlFor="select-all-weather" className="font-semibold cursor-pointer">
                    Select All ({allLeagues.length} leagues)
                  </Label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {allLeagues.map((league) => (
                    <div key={league.code} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id={`league-weather-${league.code}`}
                        checked={selectedLeagues.includes(league.code)}
                        onChange={() => toggleLeague(league.code)}
                        className="rounded"
                      />
                      <Label htmlFor={`league-weather-${league.code}`} className="text-sm cursor-pointer">
                        {league.code} - {league.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <Button
              onClick={handleBatchIngestWeather}
              disabled={loading['weather-batch'] || selectedLeagues.length === 0}
              className="w-full"
            >
              {loading['weather-batch'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Database className="h-4 w-4 mr-2" />
                  Batch Ingest Weather ({selectedLeagues.length === allLeagues.length ? 'All Leagues' : `${selectedLeagues.length} Leagues`})
                </>
              )}
            </Button>
            {results['weather-batch'] && (
              <Alert>
                {results['weather-batch'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['weather-batch'].success ? (
                    <div className="space-y-1">
                      <div>Total Processed: {results['weather-batch'].data?.total || 0}</div>
                      <div>Successful: {results['weather-batch'].data?.successful || 0}</div>
                      <div>Failed: {results['weather-batch'].data?.failed || 0}</div>
                      <p className="text-xs text-muted-foreground mt-2">
                        CSV files saved to: <code>data/1_data_ingestion/Draw_structural/Weather/</code>
                      </p>
                    </div>
                  ) : (
                    results['weather-batch'].error
                  )}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Weather Summary */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Ingestion Summary</CardTitle>
                <CardDescription>
                  Overview of weather data in the database
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchWeatherSummary}
                disabled={loadingSummary['weather']}
              >
                {loadingSummary['weather'] ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loadingSummary['weather'] ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : weatherSummary ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Total Records</p>
                    <p className="text-2xl font-bold">{weatherSummary.total_records.toLocaleString()}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Leagues with Weather</p>
                    <p className="text-2xl font-bold">
                      {weatherSummary.leagues_with_weather}/{weatherSummary.total_leagues}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Last Updated</p>
                    <p className="text-sm font-medium">
                      {weatherSummary.last_updated
                        ? new Date(weatherSummary.last_updated).toLocaleString()
                        : 'Never'}
                    </p>
                  </div>
                </div>
                {weatherSummary.by_league.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold mb-3">Weather Data by League</h4>
                    <div className="border rounded-md">
                      <div className="max-h-64 overflow-y-auto">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 p-3">
                          {weatherSummary.by_league.map((league) => (
                            <div
                              key={league.code}
                              className="flex items-center justify-between p-2 rounded-md bg-muted/50 hover:bg-muted transition-colors"
                            >
                              <div>
                                <p className="text-sm font-medium">{league.name}</p>
                                <p className="text-xs text-muted-foreground">{league.code}</p>
                              </div>
                              <div className="text-right">
                                <p className="text-sm font-bold">{league.count}</p>
                                <p className="text-xs text-muted-foreground">records</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No summary data available</p>
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      {/* Referee Stats */}
      <TabsContent value="referee" className="space-y-4">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-semibold">Source: WorldFootball.net (FREE scrape)</p>
              <div>
                <p className="font-medium mb-1">What You Get:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Referee match history</li>
                  <li>Cards per game, penalties awarded</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Why It Helps:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Game disruption modeling</li>
                  <li>Variance control</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Draw Relevance:</p>
                <p className="text-sm ml-2">
                  <strong>Low-penalty, low-card referees → more stalemates</strong>. High-intervention refs reduce draw probability.
                </p>
              </div>
            </div>
          </AlertDescription>
        </Alert>
        <Card>
          <CardHeader>
            <CardTitle>Referee Statistics</CardTitle>
            <CardDescription>
              Calculate referee statistics from match history
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Referee ID</Label>
                <Input
                  value={refereeId}
                  onChange={(e) => setRefereeId(e.target.value)}
                  placeholder="Referee ID"
                  type="number"
                />
              </div>
              <div>
                <Label>Referee Name (optional)</Label>
                <Input
                  value={refereeName}
                  onChange={(e) => setRefereeName(e.target.value)}
                  placeholder="Referee name"
                />
              </div>
            </div>
            <Button
              onClick={handleIngestReferee}
              disabled={loading['referee'] || !refereeId}
              className="w-full"
            >
              {loading['referee'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Calculating...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Calculate Referee Stats
                </>
              )}
            </Button>
            {results['referee'] && (
              <Alert>
                {results['referee'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['referee'].success
                    ? `Matches: ${results['referee'].data?.matches}, Draw Rate: ${(results['referee'].data?.draw_rate * 100).toFixed(1)}%`
                    : results['referee'].error}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Batch Referee Statistics</CardTitle>
            <CardDescription>
              Calculate referee statistics for all referees in selected leagues and seasons
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Select Season</Label>
              <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                <SelectTrigger>
                  <SelectValue placeholder="Select season" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Seasons</SelectItem>
                  <SelectItem value="last7">Last 7 Seasons</SelectItem>
                  <SelectItem value="last10">Last 10 Seasons</SelectItem>
                  {seasonsList.map((season) => (
                    <SelectItem key={season} value={season}>
                      {season}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Select Leagues</Label>
              <div className="mt-2 space-y-2 max-h-48 overflow-y-auto border rounded-md p-3">
                <div className="flex items-center space-x-2 mb-2">
                  <input
                    type="checkbox"
                    id="select-all-referee"
                    checked={selectedLeagues.length === allLeagues.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedLeagues(allLeagues.map(l => l.code));
                      } else {
                        setSelectedLeagues([]);
                      }
                    }}
                    className="rounded"
                  />
                  <Label htmlFor="select-all-referee" className="font-semibold cursor-pointer">
                    Select All ({allLeagues.length} leagues)
                  </Label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {allLeagues.map((league) => (
                    <div key={league.code} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id={`league-referee-${league.code}`}
                        checked={selectedLeagues.includes(league.code)}
                        onChange={() => toggleLeague(league.code)}
                        className="rounded"
                      />
                      <Label htmlFor={`league-referee-${league.code}`} className="text-sm cursor-pointer">
                        {league.code} - {league.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <Button
              onClick={handleBatchIngestReferee}
              disabled={loading['referee-batch'] || selectedLeagues.length === 0}
              className="w-full"
            >
              {loading['referee-batch'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Database className="h-4 w-4 mr-2" />
                  Batch Calculate Referee Stats ({selectedLeagues.length === allLeagues.length ? 'All Leagues' : `${selectedLeagues.length} Leagues`})
                </>
              )}
            </Button>
            {results['referee-batch'] && (
              <Alert>
                {results['referee-batch'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['referee-batch'].success ? (
                    <div className="space-y-1">
                      <div>Total Processed: {results['referee-batch'].data?.total || 0}</div>
                      <div>Successful: {results['referee-batch'].data?.successful || 0}</div>
                      <div>Failed: {results['referee-batch'].data?.failed || 0}</div>
                      <p className="text-xs text-muted-foreground mt-2">
                        CSV files saved to: <code>data/1_data_ingestion/Draw_structural/Referee/</code>
                      </p>
                    </div>
                  ) : (
                    results['referee-batch'].error
                  )}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Referee Summary */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Ingestion Summary</CardTitle>
                <CardDescription>
                  Overview of referee stats in the database
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchRefereeSummary}
                disabled={loadingSummary['referee']}
              >
                {loadingSummary['referee'] ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loadingSummary['referee'] ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : refereeSummary ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Total Records</p>
                    <p className="text-2xl font-bold">{refereeSummary.total_records.toLocaleString()}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Last Updated</p>
                    <p className="text-sm font-medium">
                      {refereeSummary.last_updated
                        ? new Date(refereeSummary.last_updated).toLocaleString()
                        : 'Never'}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No summary data available</p>
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      {/* Rest Days */}
      <TabsContent value="rest-days" className="space-y-4">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-semibold">Source: Football-Data.org API (Scheduling & Fatigue)</p>
              <div>
                <p className="font-medium mb-1">What You Get:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Match congestion data</li>
                  <li>Days of rest between matches</li>
                  <li>Home/away sequences</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Why It Helps:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Fatigue reduces pressing & finishing</li>
                  <li>Increases conservative tactics</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Draw Relevance:</p>
                <p className="text-sm ml-2">
                  <strong>Short rest + away team → draw bias</strong>. Midweek matches inflate draws.
                </p>
              </div>
            </div>
          </AlertDescription>
        </Alert>
        <Card>
          <CardHeader>
            <CardTitle>Rest Days & Congestion</CardTitle>
            <CardDescription>
              Calculate rest days for teams before fixtures
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Fixture ID</Label>
              <Input
                value={restDaysFixtureId}
                onChange={(e) => setRestDaysFixtureId(e.target.value)}
                placeholder="Fixture ID"
                type="number"
              />
            </div>
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                Rest days are calculated automatically from match history.
                Team IDs will be fetched from the fixture.
              </AlertDescription>
            </Alert>
            <Button
              onClick={handleIngestRestDays}
              disabled={loading['rest-days'] || !restDaysFixtureId}
              className="w-full"
            >
              {loading['rest-days'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Calculating...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Calculate Rest Days
                </>
              )}
            </Button>
            {results['rest-days'] && (
              <Alert>
                {results['rest-days'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['rest-days'].success
                    ? `Home: ${results['rest-days'].data?.home_rest_days} days, Away: ${results['rest-days'].data?.away_rest_days} days`
                    : results['rest-days'].error}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Batch Rest Days</CardTitle>
            <CardDescription>
              Calculate rest days for all matches in selected leagues and seasons
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Select Season</Label>
              <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                <SelectTrigger>
                  <SelectValue placeholder="Select season" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Seasons</SelectItem>
                  <SelectItem value="last7">Last 7 Seasons</SelectItem>
                  <SelectItem value="last10">Last 10 Seasons</SelectItem>
                  {seasonsList.map((season) => (
                    <SelectItem key={season} value={season}>
                      {season}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Select Leagues</Label>
              <div className="mt-2 space-y-2 max-h-48 overflow-y-auto border rounded-md p-3">
                <div className="flex items-center space-x-2 mb-2">
                  <input
                    type="checkbox"
                    id="select-all-rest-days"
                    checked={selectedLeagues.length === allLeagues.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedLeagues(allLeagues.map(l => l.code));
                      } else {
                        setSelectedLeagues([]);
                      }
                    }}
                    className="rounded"
                  />
                  <Label htmlFor="select-all-rest-days" className="font-semibold cursor-pointer">
                    Select All ({allLeagues.length} leagues)
                  </Label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {allLeagues.map((league) => (
                    <div key={league.code} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id={`league-rest-days-${league.code}`}
                        checked={selectedLeagues.includes(league.code)}
                        onChange={() => toggleLeague(league.code)}
                        className="rounded"
                      />
                      <Label htmlFor={`league-rest-days-${league.code}`} className="text-sm cursor-pointer">
                        {league.code} - {league.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <Button
              onClick={handleBatchIngestRestDays}
              disabled={loading['rest-days-batch'] || selectedLeagues.length === 0}
              className="w-full"
            >
              {loading['rest-days-batch'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Database className="h-4 w-4 mr-2" />
                  Batch Calculate Rest Days ({selectedLeagues.length === allLeagues.length ? 'All Leagues' : `${selectedLeagues.length} Leagues`})
                </>
              )}
            </Button>
            {results['rest-days-batch'] && (
              <Alert>
                {results['rest-days-batch'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['rest-days-batch'].success ? (
                    <div className="space-y-1">
                      <div>Total Processed: {results['rest-days-batch'].data?.total || 0}</div>
                      <div>Successful: {results['rest-days-batch'].data?.successful || 0}</div>
                      <div>Failed: {results['rest-days-batch'].data?.failed || 0}</div>
                      <p className="text-xs text-muted-foreground mt-2">
                        CSV files saved to: <code>data/1_data_ingestion/Draw_structural/Rest_Days/</code>
                      </p>
                    </div>
                  ) : (
                    results['rest-days-batch'].error
                  )}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Rest Days Summary */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Ingestion Summary</CardTitle>
                <CardDescription>
                  Overview of rest days data in the database
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchRestDaysSummary}
                disabled={loadingSummary['rest-days']}
              >
                {loadingSummary['rest-days'] ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loadingSummary['rest-days'] ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : restDaysSummary ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Total Records</p>
                    <p className="text-2xl font-bold">{restDaysSummary.total_records.toLocaleString()}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Leagues with Rest Days</p>
                    <p className="text-2xl font-bold">
                      {restDaysSummary.leagues_with_rest_days}/{restDaysSummary.total_leagues}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Last Updated</p>
                    <p className="text-sm font-medium">
                      {restDaysSummary.last_updated
                        ? new Date(restDaysSummary.last_updated).toLocaleString()
                        : 'Never'}
                    </p>
                  </div>
                </div>
                {restDaysSummary.by_league.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold mb-3">Rest Days Data by League</h4>
                    <div className="border rounded-md">
                      <div className="max-h-64 overflow-y-auto">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 p-3">
                          {restDaysSummary.by_league.map((league) => (
                            <div
                              key={league.code}
                              className="flex items-center justify-between p-2 rounded-md bg-muted/50 hover:bg-muted transition-colors"
                            >
                              <div>
                                <p className="text-sm font-medium">{league.name}</p>
                                <p className="text-xs text-muted-foreground">{league.code}</p>
                              </div>
                              <div className="text-right">
                                <p className="text-sm font-bold">{league.count}</p>
                                <p className="text-xs text-muted-foreground">records</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No summary data available</p>
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      {/* League Structure */}
      <TabsContent value="league-structure" className="space-y-4">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-semibold">Source: Default League Structure (Configurable)</p>
              <div>
                <p className="font-medium mb-1">What You Get:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>League size and structure</li>
                  <li>Relegation pressure zones</li>
                  <li>Promotion zones</li>
                  <li>Playoff zones</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Why It Helps:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Late-season incentive modeling</li>
                  <li>Tactical conservatism detection</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Draw Relevance:</p>
                <p className="text-sm ml-2">
                  <strong>Relegation six-pointers → high draw rate</strong>. End-season mid-table matches → draw spikes.
                </p>
              </div>
            </div>
          </AlertDescription>
        </Alert>

        <Card>
          <CardHeader>
            <CardTitle>League Structure</CardTitle>
            <CardDescription>
              Ingest league structure metadata for a specific league and season
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>League</Label>
                <Select value={selectedLeagueCode} onValueChange={setSelectedLeagueCode}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select league" />
                  </SelectTrigger>
                  <SelectContent>
                    {allLeagues.map((league) => (
                      <SelectItem key={league.code} value={league.code}>
                        {league.code} - {league.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Season</Label>
                <Select value={selectedLeagueSeason} onValueChange={setSelectedLeagueSeason}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select season" />
                  </SelectTrigger>
                  <SelectContent>
                    {seasonsList.map((season) => (
                      <SelectItem key={season} value={season}>
                        {season}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Total Teams (Optional)</Label>
                <Input
                  value={totalTeams}
                  onChange={(e) => setTotalTeams(e.target.value)}
                  placeholder="e.g., 20"
                  type="number"
                />
              </div>
              <div>
                <Label>Relegation Zones (Optional)</Label>
                <Input
                  value={relegationZones}
                  onChange={(e) => setRelegationZones(e.target.value)}
                  placeholder="e.g., 3"
                  type="number"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Promotion Zones (Optional)</Label>
                <Input
                  value={promotionZones}
                  onChange={(e) => setPromotionZones(e.target.value)}
                  placeholder="e.g., 3"
                  type="number"
                />
              </div>
              <div>
                <Label>Playoff Zones (Optional)</Label>
                <Input
                  value={playoffZones}
                  onChange={(e) => setPlayoffZones(e.target.value)}
                  placeholder="e.g., 1"
                  type="number"
                />
              </div>
            </div>
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription className="text-xs">
                <strong>Note:</strong> If optional fields are left empty, default values from the league structure mapping will be used.
              </AlertDescription>
            </Alert>
            <Button
              onClick={handleIngestLeagueStructure}
              disabled={loading['league-structure'] || !selectedLeagueCode || !selectedLeagueSeason}
              className="w-full"
            >
              {loading['league-structure'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Ingesting...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Ingest League Structure
                </>
              )}
            </Button>
            {results['league-structure'] && (
              <Alert>
                {results['league-structure'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['league-structure'].success ? (
                    <div className="space-y-1">
                      <div>League Structure ingested successfully</div>
                      <p className="text-xs text-muted-foreground mt-2">
                        CSV file saved to: <code>data/1_data_ingestion/Draw_structural/League_structure/</code>
                      </p>
                    </div>
                  ) : (
                    results['league-structure'].error
                  )}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Batch League Structure</CardTitle>
            <CardDescription>
              Ingest league structure metadata for selected leagues and seasons
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Select Season</Label>
              <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                <SelectTrigger>
                  <SelectValue placeholder="Select season" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Seasons</SelectItem>
                  <SelectItem value="last7">Last 7 Seasons</SelectItem>
                  <SelectItem value="last10">Last 10 Seasons</SelectItem>
                  {seasonsList.map((season) => (
                    <SelectItem key={season} value={season}>
                      {season}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Select Leagues</Label>
              <div className="mt-2 space-y-2 max-h-48 overflow-y-auto border rounded-md p-3">
                <div className="flex items-center space-x-2 mb-2">
                  <input
                    type="checkbox"
                    id="select-all-league-structure"
                    checked={selectedLeagues.length === allLeagues.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedLeagues(allLeagues.map(l => l.code));
                      } else {
                        setSelectedLeagues([]);
                      }
                    }}
                    className="rounded"
                  />
                  <Label htmlFor="select-all-league-structure" className="font-semibold cursor-pointer">
                    Select All ({allLeagues.length} leagues)
                  </Label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {allLeagues.map((league) => (
                    <div key={league.code} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id={`league-structure-${league.code}`}
                        checked={selectedLeagues.includes(league.code)}
                        onChange={() => toggleLeague(league.code)}
                        className="rounded"
                      />
                      <Label htmlFor={`league-structure-${league.code}`} className="text-sm cursor-pointer">
                        {league.code} - {league.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <Button
              onClick={handleBatchIngestLeagueStructure}
              disabled={loading['league-structure-batch'] || selectedLeagues.length === 0}
              className="w-full"
            >
              {loading['league-structure-batch'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Database className="h-4 w-4 mr-2" />
                  Batch Ingest League Structure ({selectedLeagues.length === allLeagues.length ? 'All Leagues' : `${selectedLeagues.length} Leagues`})
                </>
              )}
            </Button>
            {results['league-structure-batch'] && (
              <Alert>
                {results['league-structure-batch'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['league-structure-batch'].success ? (
                    <div className="space-y-1">
                      <div>Total Processed: {results['league-structure-batch'].data?.total || 0}</div>
                      <div>Successful: {results['league-structure-batch'].data?.successful || 0}</div>
                      <div>Failed: {results['league-structure-batch'].data?.failed || 0}</div>
                      <p className="text-xs text-muted-foreground mt-2">
                        CSV files saved to: <code>data/1_data_ingestion/Draw_structural/League_structure/</code>
                      </p>
                    </div>
                  ) : (
                    results['league-structure-batch'].error
                  )}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* League Structure Summary */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Ingestion Summary</CardTitle>
                <CardDescription>
                  Overview of league structure data in the database
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchLeagueStructureSummary}
                disabled={loadingSummary['league-structure']}
              >
                {loadingSummary['league-structure'] ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loadingSummary['league-structure'] ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : leagueStructureSummary ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Total Records</p>
                    <p className="text-2xl font-bold">{leagueStructureSummary.total_records.toLocaleString()}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Leagues with Structure</p>
                    <p className="text-2xl font-bold">{leagueStructureSummary.leagues_with_structure} / {leagueStructureSummary.total_leagues}</p>
                  </div>
                </div>
                {leagueStructureSummary.last_updated && (
                  <div className="text-sm text-muted-foreground">
                    Last Updated: {new Date(leagueStructureSummary.last_updated).toLocaleString()}
                  </div>
                )}
                {leagueStructureSummary.by_league && leagueStructureSummary.by_league.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium">By League:</p>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {leagueStructureSummary.by_league.map((league) => (
                        <div key={league.code} className="flex items-center justify-between p-2 border rounded-md">
                          <div>
                            <p className="text-sm font-medium">{league.name}</p>
                            <p className="text-xs text-muted-foreground">{league.code}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-bold">{league.count}</p>
                            <p className="text-xs text-muted-foreground">records</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No summary data available</p>
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      {/* Odds Movement */}
      <TabsContent value="odds-movement" className="space-y-4">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-semibold">Source: Football-Data.org (Market Movement)</p>
              <div>
                <p className="font-medium mb-1">What You Get:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Opening vs closing odds</li>
                  <li>Line movement direction</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Why It Helps:</p>
                <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                  <li>Market uncertainty detection</li>
                  <li>Late information proxy</li>
                </ul>
              </div>
              <div>
                <p className="font-medium mb-1">Draw Relevance:</p>
                <p className="text-sm ml-2">
                  <strong>Narrowing draw odds = rising stalemate expectation</strong>. Strong signal when models disagree.
                </p>
              </div>
            </div>
          </AlertDescription>
        </Alert>
        <Card>
          <CardHeader>
            <CardTitle>Odds Movement</CardTitle>
            <CardDescription>
              Track draw odds movement over time
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Fixture ID</Label>
                <Input
                  value={oddsFixtureId}
                  onChange={(e) => setOddsFixtureId(e.target.value)}
                  placeholder="Fixture ID"
                  type="number"
                />
              </div>
              <div>
                <Label>Current Draw Odds (optional)</Label>
                <Input
                  value={drawOdds}
                  onChange={(e) => setDrawOdds(e.target.value)}
                  placeholder="3.50"
                  type="number"
                  step="0.01"
                />
              </div>
            </div>
            <Button
              onClick={handleIngestOddsMovement}
              disabled={loading['odds-movement'] || !oddsFixtureId}
              className="w-full"
            >
              {loading['odds-movement'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Tracking...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Track Odds Movement
                </>
              )}
            </Button>
            {results['odds-movement'] && (
              <Alert>
                {results['odds-movement'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['odds-movement'].success
                    ? `Delta: ${results['odds-movement'].data?.draw_delta?.toFixed(3)}`
                    : results['odds-movement'].error}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Batch Odds Movement</CardTitle>
            <CardDescription>
              Track odds movement for all matches in selected leagues and seasons
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Select Season</Label>
              <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                <SelectTrigger>
                  <SelectValue placeholder="Select season" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Seasons</SelectItem>
                  <SelectItem value="last7">Last 7 Seasons</SelectItem>
                  <SelectItem value="last10">Last 10 Seasons</SelectItem>
                  {seasonsList.map((season) => (
                    <SelectItem key={season} value={season}>
                      {season}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Select Leagues</Label>
              <div className="mt-2 space-y-2 max-h-48 overflow-y-auto border rounded-md p-3">
                <div className="flex items-center space-x-2 mb-2">
                  <input
                    type="checkbox"
                    id="select-all-odds"
                    checked={selectedLeagues.length === allLeagues.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedLeagues(allLeagues.map(l => l.code));
                      } else {
                        setSelectedLeagues([]);
                      }
                    }}
                    className="rounded"
                  />
                  <Label htmlFor="select-all-odds" className="font-semibold cursor-pointer">
                    Select All ({allLeagues.length} leagues)
                  </Label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {allLeagues.map((league) => (
                    <div key={league.code} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id={`league-odds-${league.code}`}
                        checked={selectedLeagues.includes(league.code)}
                        onChange={() => toggleLeague(league.code)}
                        className="rounded"
                      />
                      <Label htmlFor={`league-odds-${league.code}`} className="text-sm cursor-pointer">
                        {league.code} - {league.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <Button
              onClick={handleBatchIngestOddsMovement}
              disabled={loading['odds-movement-batch'] || selectedLeagues.length === 0}
              className="w-full"
            >
              {loading['odds-movement-batch'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Database className="h-4 w-4 mr-2" />
                  Batch Track Odds Movement ({selectedLeagues.length === allLeagues.length ? 'All Leagues' : `${selectedLeagues.length} Leagues`})
                </>
              )}
            </Button>
            {results['odds-movement-batch'] && (
              <Alert>
                {results['odds-movement-batch'].success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {results['odds-movement-batch'].success ? (
                    <div className="space-y-1">
                      <div>Total Processed: {results['odds-movement-batch'].data?.total || 0}</div>
                      <div>Successful: {results['odds-movement-batch'].data?.successful || 0}</div>
                      <div>Failed: {results['odds-movement-batch'].data?.failed || 0}</div>
                      <p className="text-xs text-muted-foreground mt-2">
                        CSV files saved to: <code>data/1_data_ingestion/Draw_structural/Odds_Movement/</code>
                      </p>
                    </div>
                  ) : (
                    results['odds-movement-batch'].error
                  )}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Odds Movement Summary */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Ingestion Summary</CardTitle>
                <CardDescription>
                  Overview of odds movement data in the database
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchOddsMovementSummary}
                disabled={loadingSummary['odds-movement']}
              >
                {loadingSummary['odds-movement'] ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loadingSummary['odds-movement'] ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : oddsMovementSummary ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Total Records</p>
                    <p className="text-2xl font-bold">{oddsMovementSummary.total_records.toLocaleString()}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Leagues with Odds</p>
                    <p className="text-2xl font-bold">
                      {oddsMovementSummary.leagues_with_odds}/{oddsMovementSummary.total_leagues}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Last Updated</p>
                    <p className="text-sm font-medium">
                      {oddsMovementSummary.last_updated
                        ? new Date(oddsMovementSummary.last_updated).toLocaleString()
                        : 'Never'}
                    </p>
                  </div>
                </div>
                {oddsMovementSummary.by_league.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold mb-3">Odds Movement by League</h4>
                    <div className="border rounded-md">
                      <div className="max-h-64 overflow-y-auto">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 p-3">
                          {oddsMovementSummary.by_league.map((league) => (
                            <div
                              key={league.code}
                              className="flex items-center justify-between p-2 rounded-md bg-muted/50 hover:bg-muted transition-colors"
                            >
                              <div>
                                <p className="text-sm font-medium">{league.name}</p>
                                <p className="text-xs text-muted-foreground">{league.code}</p>
                              </div>
                              <div className="text-right">
                                <p className="text-sm font-bold">{league.count}</p>
                                <p className="text-xs text-muted-foreground">records</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No summary data available</p>
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      {/* Team Form */}
      <TabsContent value="team-form" className="space-y-4">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            Calculate and ingest team form metrics (last N matches) for fixtures. Form is calculated from historical match results.
          </AlertDescription>
        </Alert>

        <Card>
          <CardHeader>
            <CardTitle>Batch Ingest Team Form</CardTitle>
            <CardDescription>
              Calculate team form for matches in selected leagues and seasons
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Select Season</Label>
              <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                <SelectTrigger>
                  <SelectValue placeholder="Select season" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Seasons</SelectItem>
                  <SelectItem value="last7">Last 7 Seasons</SelectItem>
                  <SelectItem value="last10">Last 10 Seasons</SelectItem>
                  {seasonsList.map((season) => (
                    <SelectItem key={season} value={season}>
                      {season}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground mt-1">
                {selectedSeason === 'ALL' && 'Will process all historical matches'}
                {selectedSeason === 'last7' && 'Will process matches from the last 7 seasons'}
                {selectedSeason === 'last10' && 'Will process matches from the last 10 seasons'}
                {selectedSeason !== 'ALL' && selectedSeason !== 'last7' && selectedSeason !== 'last10' && `Will process matches from ${selectedSeason} season`}
              </p>
            </div>

            <div>
              <Label>Select Leagues</Label>
              <div className="mt-2 space-y-2 max-h-48 overflow-y-auto border rounded-md p-3">
                <div className="flex items-center space-x-2 mb-2">
                  <input
                    type="checkbox"
                    id="select-all-team-form"
                    checked={selectedLeagues.length === allLeagues.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedLeagues(allLeagues.map(l => l.code));
                      } else {
                        setSelectedLeagues([]);
                      }
                    }}
                    className="rounded"
                  />
                  <Label htmlFor="select-all-team-form" className="font-semibold cursor-pointer">
                    Select All ({allLeagues.length} leagues)
                  </Label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {allLeagues.map((league) => (
                    <div key={league.code} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id={`league-team-form-${league.code}`}
                        checked={selectedLeagues.includes(league.code)}
                        onChange={() => toggleLeague(league.code)}
                        className="rounded"
                      />
                      <Label htmlFor={`league-team-form-${league.code}`} className="text-sm cursor-pointer">
                        {league.code} - {league.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Selected: {selectedLeagues.length} league{selectedLeagues.length !== 1 ? 's' : ''}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>Matches Count</Label>
                <Input
                  type="number"
                  min="3"
                  max="10"
                  value={matchesCount}
                  onChange={(e) => setMatchesCount(parseInt(e.target.value) || 5)}
                  placeholder="5"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Number of recent matches to consider for form calculation (default: 5)
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="save-csv-team-form"
                checked={true}
                disabled
              />
              <Label htmlFor="save-csv-team-form" className="text-sm text-muted-foreground">
                Save CSV files (always enabled)
              </Label>
            </div>

            <Button
              onClick={handleBatchIngestTeamForm}
              disabled={loading['team-form-batch'] || selectedLeagues.length === 0}
              className="w-full"
            >
              {loading['team-form-batch'] ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Ingesting Team Form...
                </>
              ) : (
                <>
                  <TrendingUp className="h-4 w-4 mr-2" />
                  Batch Ingest Team Form ({selectedLeagues.length === allLeagues.length ? 'All Leagues' : `${selectedLeagues.length} Leagues`})
                </>
              )}
            </Button>

            {results['team-form-batch'] && (
              <Alert>
                {results['team-form-batch'].success ? (
                  <>
                    <CheckCircle className="h-4 w-4" />
                    <AlertDescription>
                      {results['team-form-batch'].data?.message || 
                       `Processed ${results['team-form-batch'].data?.total || 0} matches. ${results['team-form-batch'].data?.successful || 0} form records calculated.`}
                    </AlertDescription>
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      {results['team-form-batch'].error || 'Failed to ingest team form'}
                    </AlertDescription>
                  </>
                )}
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Ingestion Summary</CardTitle>
                <CardDescription>
                  Overview of team form data in the database
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchTeamFormSummary}
                disabled={loadingSummary['team-form']}
              >
                {loadingSummary['team-form'] ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loadingSummary['team-form'] ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : teamFormSummary ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Total Records</p>
                    <p className="text-2xl font-bold">{teamFormSummary.total_records.toLocaleString()}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Fixture Records</p>
                    <p className="text-2xl font-bold">{teamFormSummary.fixture_records.toLocaleString()}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Historical Records</p>
                    <p className="text-2xl font-bold">{teamFormSummary.historical_records.toLocaleString()}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Leagues with Form</p>
                    <p className="text-2xl font-bold">
                      {teamFormSummary.leagues_with_form}/{teamFormSummary.total_leagues}
                    </p>
                  </div>
                </div>
                {teamFormSummary.last_updated && (
                  <div className="pt-2 border-t">
                    <p className="text-sm text-muted-foreground">Last Updated</p>
                    <p className="text-sm font-medium">
                      {new Date(teamFormSummary.last_updated).toLocaleString()}
                    </p>
                  </div>
                )}
                {teamFormSummary.by_league.length > 0 && (
                  <div className="pt-2 border-t">
                    <p className="text-sm font-semibold mb-2">By League (Top 10)</p>
                    <div className="space-y-1 max-h-48 overflow-y-auto">
                      {teamFormSummary.by_league.slice(0, 10).map((league) => (
                        <div key={league.code} className="flex justify-between text-sm">
                          <span>{league.code} - {league.name}</span>
                          <span className="font-medium">{league.count.toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                No team form data available. Click Refresh to load summary.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              <strong>What is Team Form?</strong> Team form metrics calculated from recent match results including:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>Matches played, wins, draws, losses</li>
              <li>Goals scored and conceded</li>
              <li>Points earned (3*wins + draws)</li>
              <li>Form rating (normalized 0.0-1.0)</li>
              <li>Attack form (goals scored per match)</li>
              <li>Defense form (goals conceded per match, inverted)</li>
            </ul>
            <p className="mt-2">
              <strong>Note:</strong> Team form is automatically calculated during prediction if missing. This batch ingestion is useful for pre-populating form data for historical analysis.
            </p>
          </CardContent>
        </Card>
      </TabsContent>

      {/* Team Injuries */}
      <TabsContent value="team-injuries" className="space-y-4">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            Import team injuries from CSV, download from external APIs (API-Football), or export existing injury data to CSV format. You can also use the manual entry feature in the Probability Output page.
          </AlertDescription>
        </Alert>

        <Card>
          <CardHeader>
            <CardTitle>Import Team Injuries from CSV</CardTitle>
            <CardDescription>
              Upload a CSV file to import team injury data. CSV format: league_code, season, match_date, home_team, away_team, home_key_players_missing, home_injury_severity, away_key_players_missing, away_injury_severity, etc.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-4">
              <input
                type="file"
                id="team-injuries-csv-upload"
                accept=".csv"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    handleImportTeamInjuriesFromCsv(file);
                  }
                }}
                className="hidden"
                disabled={loading['team-injuries-import']}
              />
              <Label htmlFor="team-injuries-csv-upload" className="cursor-pointer">
                <Button
                  type="button"
                  variant="outline"
                  disabled={loading['team-injuries-import']}
                  onClick={() => document.getElementById('team-injuries-csv-upload')?.click()}
                >
                  {loading['team-injuries-import'] ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Importing...
                    </>
                  ) : (
                    <>
                      <Upload className="h-4 w-4 mr-2" />
                      Choose CSV File
                    </>
                  )}
                </Button>
              </Label>
              {results['team-injuries-import'] && (
                <Alert className="flex-1">
                  {results['team-injuries-import'].success ? (
                    <>
                      <CheckCircle className="h-4 w-4" />
                      <AlertDescription>
                        {results['team-injuries-import'].data?.message || 
                         `Imported ${results['team-injuries-import'].data?.inserted || 0} records, updated ${results['team-injuries-import'].data?.updated || 0} records. ${results['team-injuries-import'].data?.errors || 0} errors.`}
                      </AlertDescription>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        {results['team-injuries-import'].error || 'Failed to import team injuries'}
                      </AlertDescription>
                    </>
                  )}
                </Alert>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Team Injuries</CardTitle>
            <CardDescription>
              Download injury data from external APIs or export existing injury data to CSV files
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Select Leagues</Label>
              <div className="mt-2 space-y-2 max-h-48 overflow-y-auto border rounded-md p-3">
                <div className="flex items-center space-x-2 mb-2">
                  <input
                    type="checkbox"
                    id="select-all-team-injuries"
                    checked={selectedLeagues.length === allLeagues.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedLeagues(allLeagues.map(l => l.code));
                      } else {
                        setSelectedLeagues([]);
                      }
                    }}
                    className="rounded"
                  />
                  <Label htmlFor="select-all-team-injuries" className="font-semibold cursor-pointer">
                    Select All ({allLeagues.length} leagues)
                  </Label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {allLeagues.map((league) => (
                    <div key={league.code} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id={`league-team-injuries-${league.code}`}
                        checked={selectedLeagues.includes(league.code)}
                        onChange={() => toggleLeague(league.code)}
                        className="rounded"
                      />
                      <Label htmlFor={`league-team-injuries-${league.code}`} className="text-sm cursor-pointer">
                        {league.code} - {league.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Selected: {selectedLeagues.length} league{selectedLeagues.length !== 1 ? 's' : ''}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Button
                onClick={handleDownloadTeamInjuries}
                disabled={loading['team-injuries-download'] || selectedLeagues.length === 0}
                variant="outline"
                className="w-full"
              >
                {loading['team-injuries-download'] ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Downloading...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4 mr-2" />
                    Download from API
                  </>
                )}
              </Button>

              <Button
                onClick={handleBatchIngestTeamInjuries}
                disabled={loading['team-injuries-batch'] || selectedLeagues.length === 0}
                variant="outline"
                className="w-full"
              >
                {loading['team-injuries-batch'] ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Exporting...
                  </>
                ) : (
                  <>
                    <FileSpreadsheet className="h-4 w-4 mr-2" />
                    Export to CSV
                  </>
                )}
              </Button>
            </div>

            {results['team-injuries-download'] && (
              <Alert>
                {results['team-injuries-download'].success ? (
                  <>
                    <CheckCircle className="h-4 w-4" />
                    <AlertDescription>
                      {results['team-injuries-download'].data?.message || 
                       `Downloaded ${results['team-injuries-download'].data?.successful || 0} injuries. ${results['team-injuries-download'].data?.failed || 0} failed.`}
                    </AlertDescription>
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      {results['team-injuries-download'].error || 'Failed to download injuries'}
                    </AlertDescription>
                  </>
                )}
              </Alert>
            )}

            {results['team-injuries-batch'] && (
              <Alert>
                {results['team-injuries-batch'].success ? (
                  <>
                    <CheckCircle className="h-4 w-4" />
                    <AlertDescription>
                      {results['team-injuries-batch'].data?.message || 
                       `Exported ${results['team-injuries-batch'].data?.successful || 0} injury records. ${results['team-injuries-batch'].data?.skipped || 0} fixtures skipped (no injuries).`}
                    </AlertDescription>
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      {results['team-injuries-batch'].error || 'Failed to export team injuries'}
                    </AlertDescription>
                  </>
                )}
              </Alert>
            )}

            <Alert variant="default">
              <Info className="h-4 w-4" />
              <AlertDescription className="text-sm">
                <strong>Download from API:</strong> Requires API-Football API key configured in backend. The system automatically maps fixtures and downloads injuries. 
                Rate limited to ~10 requests/minute (free tier). See <code className="text-xs bg-muted px-1 py-0.5 rounded">TEAM_INJURIES_DATA_SOURCES.md</code> for setup instructions.
                <br /><br />
                <strong>Export to CSV:</strong> Exports existing injury data from the database to CSV files for backup or analysis.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Ingestion Summary</CardTitle>
                <CardDescription>
                  Overview of team injuries data in the database
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchTeamInjuriesSummary}
                disabled={loadingSummary['team-injuries']}
              >
                {loadingSummary['team-injuries'] ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loadingSummary['team-injuries'] ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : teamInjuriesSummary ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Total Records</p>
                    <p className="text-2xl font-bold">{teamInjuriesSummary.total_records.toLocaleString()}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Leagues with Injuries</p>
                    <p className="text-2xl font-bold">
                      {teamInjuriesSummary.leagues_with_injuries}/{teamInjuriesSummary.total_leagues}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Last Updated</p>
                    <p className="text-sm font-medium">
                      {teamInjuriesSummary.last_updated
                        ? new Date(teamInjuriesSummary.last_updated).toLocaleString()
                        : 'Never'}
                    </p>
                  </div>
                </div>
                {teamInjuriesSummary.by_league.length > 0 && (
                  <div className="pt-2 border-t">
                    <p className="text-sm font-semibold mb-2">By League (Top 10)</p>
                    <div className="space-y-1 max-h-48 overflow-y-auto">
                      {teamInjuriesSummary.by_league.slice(0, 10).map((league) => (
                        <div key={league.code} className="flex justify-between text-sm">
                          <span>{league.code} - {league.name}</span>
                          <span className="font-medium">{league.count.toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                No team injuries data available. Click Refresh to load summary.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              <strong>What is Team Injuries?</strong> Injury data for teams including:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>Key players missing</li>
              <li>Injury severity (0.0-1.0)</li>
              <li>Players missing by position (attackers, midfielders, defenders, goalkeepers)</li>
              <li>Injury notes</li>
            </ul>
            <p className="mt-2">
              <strong>How to Add Injuries:</strong>
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>Go to Probability Output page</li>
              <li>Click the injury icon next to a team name</li>
              <li>Enter injury details manually</li>
              <li>Or import from CSV using the batch import endpoint</li>
            </ul>
            <p className="mt-2">
              <strong>Note:</strong> This export function helps you backup existing injury data or prepare CSV files for external analysis. To populate injuries from external sources, consider integrating with API-Football or Transfermarkt scrapers.
            </p>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
    </div>
  );
}

