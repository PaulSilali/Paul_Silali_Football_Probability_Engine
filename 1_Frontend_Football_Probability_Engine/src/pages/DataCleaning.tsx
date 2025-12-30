import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  CheckCircle2, 
  AlertTriangle, 
  Play, 
  RefreshCw,
  Filter,
  GitMerge,
  Zap,
  Columns,
  Type,
  Users,
  Plus,
  Trash2,
  ArrowRight,
  ChevronRight,
  Upload,
  Download,
  FileText,
  X,
  Save,
  RotateCcw,
  Files,
  Calendar,
  HardDrive,
  Copy,
  TrendingUp,
  BarChart3,
  Database
} from 'lucide-react';
import { useState, useRef, useCallback, useMemo, useEffect, DragEvent } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { toast } from 'sonner';
import { exportToCSV } from '@/lib/export';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend, LineChart, Line } from 'recharts';
import apiClient from '@/services/api';

// localStorage keys
const STORAGE_KEYS = {
  COLUMNS: 'etl-column-config',
  TEAM_MAPPINGS: 'etl-team-mappings',
  UPLOAD_HISTORY: 'etl-upload-history',
};

interface ETLStep {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  progress: number;
  icon: React.ElementType;
  rowsProcessed?: number;
  rowsDropped?: number;
}

interface ColumnConfig {
  raw: string;
  canonical: string;
  type: 'date' | 'string' | 'integer' | 'float';
  required: boolean;
  selected: boolean;
}

interface TeamMapping {
  raw: string;
  canonical: string;
}

interface UploadedFile {
  name: string;
  rows: number;
  validRows: number;
  size: number;
  season: string;
  league: string;
  uploadedAt: string;
}

interface UploadHistoryEntry {
  date: string;
  filesCount: number;
  totalRows: number;
  validRows: number;
  duplicatesRemoved: number;
  dataQuality: number;
}

// Raw columns from Football-Data.co.uk
const defaultColumns: ColumnConfig[] = [
  { raw: 'Date', canonical: 'date', type: 'date', required: true, selected: true },
  { raw: 'Div', canonical: 'league', type: 'string', required: true, selected: true },
  { raw: 'HomeTeam', canonical: 'home', type: 'string', required: true, selected: true },
  { raw: 'AwayTeam', canonical: 'away', type: 'string', required: true, selected: true },
  { raw: 'FTHG', canonical: 'home_goals', type: 'integer', required: true, selected: true },
  { raw: 'FTAG', canonical: 'away_goals', type: 'integer', required: true, selected: true },
  { raw: 'FTR', canonical: 'result', type: 'string', required: false, selected: false },
  { raw: 'HTHG', canonical: 'ht_home_goals', type: 'integer', required: false, selected: false },
  { raw: 'HTAG', canonical: 'ht_away_goals', type: 'integer', required: false, selected: false },
  { raw: 'HTR', canonical: 'ht_result', type: 'string', required: false, selected: false },
  { raw: 'B365H', canonical: 'odds_h', type: 'float', required: true, selected: true },
  { raw: 'B365D', canonical: 'odds_d', type: 'float', required: true, selected: true },
  { raw: 'B365A', canonical: 'odds_a', type: 'float', required: true, selected: true },
  { raw: 'BWH', canonical: 'bw_odds_h', type: 'float', required: false, selected: false },
  { raw: 'BWD', canonical: 'bw_odds_d', type: 'float', required: false, selected: false },
  { raw: 'BWA', canonical: 'bw_odds_a', type: 'float', required: false, selected: false },
  { raw: 'HS', canonical: 'home_shots', type: 'integer', required: false, selected: false },
  { raw: 'AS', canonical: 'away_shots', type: 'integer', required: false, selected: false },
  { raw: 'HST', canonical: 'home_shots_target', type: 'integer', required: false, selected: false },
  { raw: 'AST', canonical: 'away_shots_target', type: 'integer', required: false, selected: false },
  { raw: 'HC', canonical: 'home_corners', type: 'integer', required: false, selected: false },
  { raw: 'AC', canonical: 'away_corners', type: 'integer', required: false, selected: false },
];

const defaultTeamMappings: TeamMapping[] = [
  { raw: 'Man United', canonical: 'Manchester United' },
  { raw: 'Man City', canonical: 'Manchester City' },
  { raw: 'QPR', canonical: 'Queens Park Rangers' },
  { raw: 'Spurs', canonical: 'Tottenham' },
  { raw: 'West Ham', canonical: 'West Ham United' },
  { raw: 'Sheffield Utd', canonical: 'Sheffield United' },
  { raw: 'Newcastle', canonical: 'Newcastle United' },
  { raw: 'Nott\'m Forest', canonical: 'Nottingham Forest' },
  { raw: 'Wolves', canonical: 'Wolverhampton' },
  { raw: 'Brighton', canonical: 'Brighton & Hove Albion' },
];

interface ValidationRow {
  date: string;
  league: string;
  home: string;
  away: string;
  home_goals: number | null;
  away_goals: number | null;
  odds_h: number | null;
  odds_d: number | null;
  odds_a: number | null;
  sourceFile?: string;
}

const defaultSampleData: ValidationRow[] = [
  { date: '26/12/2023', league: 'E0', home: 'Arsenal', away: 'West Ham', home_goals: 2, away_goals: 0, odds_h: 1.45, odds_d: 4.50, odds_a: 6.00 },
  { date: '26/12/2023', league: 'E0', home: 'Liverpool', away: 'Burnley', home_goals: 3, away_goals: 1, odds_h: 1.25, odds_d: 5.75, odds_a: 11.00 },
  { date: '2023-12-26', league: 'E0', home: 'Man City', away: 'Everton', home_goals: 2, away_goals: null, odds_h: 1.18, odds_d: 7.00, odds_a: 15.00 },
  { date: '27/12/2023', league: 'E0', home: 'Chelsea', away: 'Crystal Palace', home_goals: 2, away_goals: 1, odds_h: 1.55, odds_d: 4.20, odds_a: 5.50 },
  { date: 'invalid', league: 'E0', home: 'Spurs', away: 'Brighton', home_goals: 1, away_goals: 1, odds_h: 1.80, odds_d: 3.60, odds_a: 4.00 },
  { date: '27/12/2023', league: 'E0', home: 'Aston Villa', away: 'Sheffield Utd', home_goals: null, away_goals: null, odds_h: 1.35, odds_d: 5.00, odds_a: 8.50 },
  { date: '28/12/2023', league: 'E0', home: 'Newcastle', away: 'Nottingham Forest', home_goals: 3, away_goals: 1, odds_h: 1.50, odds_d: 4.20, odds_a: 6.00 },
  { date: '28/12/2023', league: 'E0', home: 'Wolves', away: 'Brentford', home_goals: 1, away_goals: 0, odds_h: 1.01, odds_d: 3.50, odds_a: 4.75 },
  { date: '29/12/2023', league: 'E0', home: 'Fulham', away: 'Luton', home_goals: 2, away_goals: 2, odds_h: 1.65, odds_d: 3.80, odds_a: 5.00 },
  { date: '', league: 'E0', home: 'Bournemouth', away: 'Man United', home_goals: 0, away_goals: 3, odds_h: 4.00, odds_d: 3.50, odds_a: 1.00 },
];

type ValidationIssue = 'date' | 'home_goals' | 'away_goals' | 'odds_h' | 'odds_d' | 'odds_a';

const isValidDate = (dateStr: string): boolean => {
  if (!dateStr || dateStr.trim() === '') return false;
  const ddmmyyyy = /^\d{2}\/\d{2}\/\d{4}$/;
  if (ddmmyyyy.test(dateStr)) return true;
  return false;
};

const validateRow = (row: ValidationRow): ValidationIssue[] => {
  const issues: ValidationIssue[] = [];
  if (!isValidDate(row.date)) issues.push('date');
  if (row.home_goals === null || row.home_goals === undefined) issues.push('home_goals');
  if (row.away_goals === null || row.away_goals === undefined) issues.push('away_goals');
  if (row.odds_h === null || row.odds_h <= 1.01) issues.push('odds_h');
  if (row.odds_d === null || row.odds_d <= 1.01) issues.push('odds_d');
  if (row.odds_a === null || row.odds_a <= 1.01) issues.push('odds_a');
  return issues;
};

const getIssueBadgeClass = (issue: ValidationIssue): string => {
  switch (issue) {
    case 'date': return 'bg-purple-500/10 text-purple-500 border-purple-500/30';
    case 'home_goals':
    case 'away_goals': return 'bg-destructive/10 text-destructive border-destructive/30';
    case 'odds_h':
    case 'odds_d':
    case 'odds_a': return 'bg-amber-500/10 text-amber-500 border-amber-500/30';
    default: return '';
  }
};

const getIssueLabel = (issue: ValidationIssue): string => {
  switch (issue) {
    case 'date': return 'Bad Date';
    case 'home_goals': return 'Null HG';
    case 'away_goals': return 'Null AG';
    case 'odds_h': return 'Bad H Odds';
    case 'odds_d': return 'Bad D Odds';
    case 'odds_a': return 'Bad A Odds';
    default: return issue;
  }
};

// Detect season from filename or dates
const detectSeason = (fileName: string, rows: ValidationRow[]): string => {
  // Try filename pattern like "E0_2324.csv" or "2023-24.csv"
  const fileMatch = fileName.match(/(\d{2})(\d{2})\.csv$/i) || fileName.match(/(\d{4})-?(\d{2,4})/);
  if (fileMatch) {
    const start = fileMatch[1].length === 2 ? `20${fileMatch[1]}` : fileMatch[1];
    const end = fileMatch[2].length === 2 ? fileMatch[2] : fileMatch[2].slice(-2);
    return `${start}/${end}`;
  }
  
  // Fallback: detect from dates in data
  const validDates = rows
    .map(r => r.date)
    .filter(d => isValidDate(d))
    .map(d => {
      const parts = d.split('/');
      const year = parseInt(parts[2]);
      const month = parseInt(parts[1]);
      return { year, month };
    });
  
  if (validDates.length > 0) {
    const years = [...new Set(validDates.map(d => d.year))].sort();
    if (years.length >= 2) {
      return `${years[0]}/${years[1].toString().slice(-2)}`;
    } else if (years.length === 1) {
      const months = validDates.filter(d => d.year === years[0]).map(d => d.month);
      const hasSecondHalf = months.some(m => m >= 1 && m <= 6);
      const hasFirstHalf = months.some(m => m >= 7 && m <= 12);
      if (hasSecondHalf && !hasFirstHalf) {
        return `${years[0] - 1}/${years[0].toString().slice(-2)}`;
      }
      return `${years[0]}/${(years[0] + 1).toString().slice(-2)}`;
    }
  }
  
  return 'Unknown';
};

// Detect league from data
const detectLeague = (rows: ValidationRow[]): string => {
  const leagues = rows.map(r => r.league).filter(Boolean);
  if (leagues.length === 0) return 'Unknown';
  
  const leagueCounts = leagues.reduce((acc, l) => {
    acc[l] = (acc[l] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  const mostCommon = Object.entries(leagueCounts).sort((a, b) => b[1] - a[1])[0];
  
  const leagueNames: Record<string, string> = {
    'E0': 'Premier League',
    'E1': 'Championship',
    'E2': 'League One',
    'E3': 'League Two',
    'SP1': 'La Liga',
    'D1': 'Bundesliga',
    'I1': 'Serie A',
    'F1': 'Ligue 1',
  };
  
  return leagueNames[mostCommon?.[0]] || mostCommon?.[0] || 'Unknown';
};

// Format file size
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

// Create match key for deduplication
const getMatchKey = (row: ValidationRow): string => {
  return `${row.date}|${row.home}|${row.away}|${row.league}`.toLowerCase();
};

// Parse CSV content
const parseCSV = (content: string, fileName?: string): ValidationRow[] => {
  const lines = content.trim().split('\n');
  if (lines.length < 2) return [];
  
  const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
  const rows: ValidationRow[] = [];
  
  const dateIdx = headers.findIndex(h => h === 'Date');
  const divIdx = headers.findIndex(h => h === 'Div');
  const homeIdx = headers.findIndex(h => h === 'HomeTeam');
  const awayIdx = headers.findIndex(h => h === 'AwayTeam');
  const fthgIdx = headers.findIndex(h => h === 'FTHG');
  const ftagIdx = headers.findIndex(h => h === 'FTAG');
  const b365hIdx = headers.findIndex(h => h === 'B365H');
  const b365dIdx = headers.findIndex(h => h === 'B365D');
  const b365aIdx = headers.findIndex(h => h === 'B365A');
  
  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',').map(v => v.trim().replace(/"/g, ''));
    if (values.length < 5) continue;
    
    const parseNumber = (idx: number): number | null => {
      if (idx === -1) return null;
      const val = values[idx];
      if (!val || val === '') return null;
      const num = parseFloat(val);
      return isNaN(num) ? null : num;
    };
    
    rows.push({
      date: dateIdx !== -1 ? values[dateIdx] || '' : '',
      league: divIdx !== -1 ? values[divIdx] || '' : '',
      home: homeIdx !== -1 ? values[homeIdx] || '' : '',
      away: awayIdx !== -1 ? values[awayIdx] || '' : '',
      home_goals: parseNumber(fthgIdx),
      away_goals: parseNumber(ftagIdx),
      odds_h: parseNumber(b365hIdx),
      odds_d: parseNumber(b365dIdx),
      odds_a: parseNumber(b365aIdx),
      sourceFile: fileName,
    });
  }
  
  return rows;
};

const loadFromStorage = <T,>(key: string, fallback: T): T => {
  try {
    const stored = localStorage.getItem(key);
    if (stored) return JSON.parse(stored) as T;
  } catch (e) {
    console.error(`Error loading ${key} from localStorage:`, e);
  }
  return fallback;
};

const saveToStorage = <T,>(key: string, value: T): void => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    console.error(`Error saving ${key} to localStorage:`, e);
  }
};

const CHART_COLORS = ['hsl(var(--primary))', 'hsl(142, 76%, 36%)', 'hsl(38, 92%, 50%)', 'hsl(0, 84%, 60%)'];

export default function DataCleaning() {
  const [isRunning, setIsRunning] = useState(false);
  const [columns, setColumns] = useState<ColumnConfig[]>(() => loadFromStorage(STORAGE_KEYS.COLUMNS, defaultColumns));
  const [teamMappings, setTeamMappings] = useState<TeamMapping[]>(() => loadFromStorage(STORAGE_KEYS.TEAM_MAPPINGS, defaultTeamMappings));
  const [newMapping, setNewMapping] = useState<TeamMapping>({ raw: '', canonical: '' });
  const [uploadedData, setUploadedData] = useState<ValidationRow[]>([]);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [duplicatesRemoved, setDuplicatesRemoved] = useState(0);
  const [uploadHistory, setUploadHistory] = useState<UploadHistoryEntry[]>(() => loadFromStorage(STORAGE_KEYS.UPLOAD_HISTORY, []));
  const [liveStats, setLiveStats] = useState({ totalRows: 0, processedRows: 0, validRows: 0, droppedRows: 0, currentStep: '' });
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Backend integration states
  const [allTeams, setAllTeams] = useState<Array<{id: number; name: string; canonicalName: string; leagueId: number; leagueName: string | null}>>([]);
  const [isLoadingTeams, setIsLoadingTeams] = useState(false);
  const [teamSearchQuery, setTeamSearchQuery] = useState('');
  const [teamSearchResults, setTeamSearchResults] = useState<Array<{id: number; name: string; canonicalName: string; leagueId: number; similarity: number}>>([]);
  
  const [steps, setSteps] = useState<ETLStep[]>([
    { id: 'column', name: 'Column Selection', description: 'Select and rename columns from raw data', status: 'pending', progress: 0, icon: Columns },
    { id: 'type', name: 'Type Normalization', description: 'Convert dates, integers, and floats', status: 'pending', progress: 0, icon: Type },
    { id: 'team', name: 'Team Name Standardization', description: 'Apply team name mappings across seasons', status: 'pending', progress: 0, icon: Users },
    { id: 'validate', name: 'Data Validation', description: 'Drop invalid rows (null goals, bad odds)', status: 'pending', progress: 0, icon: Filter },
    { id: 'feature', name: 'Feature Derivation', description: 'Calculate market probabilities from odds', status: 'pending', progress: 0, icon: GitMerge },
    { id: 'load', name: 'Load to Training Store', description: 'Store processed data for model training', status: 'pending', progress: 0, icon: Zap },
  ]);

  const displayData = uploadedData.length > 0 ? uploadedData : defaultSampleData;

  const validationStats = useMemo(() => {
    const results = displayData.map(row => validateRow(row));
    return {
      validRows: results.filter(issues => issues.length === 0).length,
      nullGoalsCount: results.filter(issues => issues.includes('home_goals') || issues.includes('away_goals')).length,
      invalidOddsCount: results.filter(issues => issues.includes('odds_h') || issues.includes('odds_d') || issues.includes('odds_a')).length,
      malformedDateCount: results.filter(issues => issues.includes('date')).length,
      totalRows: displayData.length,
    };
  }, [displayData]);

  // Season distribution for charts
  const seasonDistribution = useMemo(() => {
    const seasons = uploadedFiles.reduce((acc, f) => {
      acc[f.season] = (acc[f.season] || 0) + f.rows;
      return acc;
    }, {} as Record<string, number>);
    return Object.entries(seasons).map(([season, rows]) => ({ season, rows })).sort((a, b) => a.season.localeCompare(b.season));
  }, [uploadedFiles]);

  // Quality distribution for pie chart
  const qualityDistribution = useMemo(() => [
    { name: 'Valid', value: validationStats.validRows, color: CHART_COLORS[1] },
    { name: 'Null Goals', value: validationStats.nullGoalsCount, color: CHART_COLORS[3] },
    { name: 'Invalid Odds', value: validationStats.invalidOddsCount, color: CHART_COLORS[2] },
    { name: 'Bad Dates', value: validationStats.malformedDateCount, color: CHART_COLORS[0] },
  ].filter(d => d.value > 0), [validationStats]);

  const saveConfig = useCallback(() => {
    saveToStorage(STORAGE_KEYS.COLUMNS, columns);
    saveToStorage(STORAGE_KEYS.TEAM_MAPPINGS, teamMappings);
    toast.success('Configuration saved to browser storage');
  }, [columns, teamMappings]);

  const resetConfig = useCallback(() => {
    setColumns(defaultColumns);
    setTeamMappings(defaultTeamMappings);
    localStorage.removeItem(STORAGE_KEYS.COLUMNS);
    localStorage.removeItem(STORAGE_KEYS.TEAM_MAPPINGS);
    toast.info('Configuration reset to defaults');
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => {
      saveToStorage(STORAGE_KEYS.COLUMNS, columns);
      saveToStorage(STORAGE_KEYS.TEAM_MAPPINGS, teamMappings);
    }, 1000);
    return () => clearTimeout(timeout);
  }, [columns, teamMappings]);

  // Load all teams from backend for team mapping
  useEffect(() => {
    const loadAllTeams = async () => {
      try {
        setIsLoadingTeams(true);
        const response = await apiClient.getAllTeams();
        if (response.success && response.data) {
          setAllTeams(response.data);
          // Auto-populate team mappings from database teams
          const dbMappings: TeamMapping[] = response.data.map(team => ({
            raw: team.name,
            canonical: team.canonicalName
          }));
          // Merge with existing mappings, avoiding duplicates
          setTeamMappings(prev => {
            const existing = new Set(prev.map(m => m.raw));
            const newMappings = dbMappings.filter(m => !existing.has(m.raw));
            return [...prev, ...newMappings];
          });
        }
      } catch (error) {
        console.error('Failed to load teams:', error);
        toast.error('Failed to load teams from database');
      } finally {
        setIsLoadingTeams(false);
      }
    };
    loadAllTeams();
  }, []);

  // Search teams when typing in canonical name field
  useEffect(() => {
    if (newMapping.canonical.length >= 2) {
      const searchTeams = async () => {
        try {
          const response = await apiClient.searchTeams({
            q: newMapping.canonical,
            limit: 5
          });
          if (response.success && response.data) {
            setTeamSearchResults(response.data);
          }
        } catch (error) {
          console.error('Failed to search teams:', error);
        }
      };
      const debounce = setTimeout(searchTeams, 300);
      return () => clearTimeout(debounce);
    } else {
      setTeamSearchResults([]);
    }
  }, [newMapping.canonical]);

  const toggleColumn = (rawName: string) => {
    setColumns(prev => prev.map(col => col.raw === rawName && !col.required ? { ...col, selected: !col.selected } : col));
  };

  const addTeamMapping = () => {
    if (newMapping.raw && newMapping.canonical) {
      setTeamMappings(prev => [...prev, newMapping]);
      setNewMapping({ raw: '', canonical: '' });
      toast.success(`Added mapping: ${newMapping.raw} → ${newMapping.canonical}`);
    }
  };

  const removeTeamMapping = (rawName: string) => {
    setTeamMappings(prev => prev.filter(m => m.raw !== rawName));
  };

  // Deduplicate rows
  const deduplicateRows = useCallback((rows: ValidationRow[]): { deduplicated: ValidationRow[]; removed: number } => {
    const seen = new Set<string>();
    const deduplicated: ValidationRow[] = [];
    let removed = 0;
    
    for (const row of rows) {
      const key = getMatchKey(row);
      if (!seen.has(key)) {
        seen.add(key);
        deduplicated.push(row);
      } else {
        removed++;
      }
    }
    
    return { deduplicated, removed };
  }, []);

  const processFiles = useCallback((files: FileList | File[]) => {
    const fileArray = Array.from(files).filter(f => f.name.endsWith('.csv'));
    if (fileArray.length === 0) {
      toast.error('Please upload CSV files');
      return;
    }

    let totalParsed = 0;
    const newFiles: UploadedFile[] = [];
    let allRows: ValidationRow[] = [...uploadedData];

    const processNextFile = (index: number) => {
      if (index >= fileArray.length) {
        // Deduplicate all rows
        const { deduplicated, removed } = deduplicateRows(allRows);
        setUploadedData(deduplicated);
        setUploadedFiles(prev => [...prev, ...newFiles]);
        setDuplicatesRemoved(prev => prev + removed);
        
        // Add to upload history
        const historyEntry: UploadHistoryEntry = {
          date: new Date().toISOString().split('T')[0],
          filesCount: fileArray.length,
          totalRows: totalParsed,
          validRows: deduplicated.filter(r => validateRow(r).length === 0).length,
          duplicatesRemoved: removed,
          dataQuality: totalParsed > 0 ? (deduplicated.filter(r => validateRow(r).length === 0).length / deduplicated.length) * 100 : 0,
        };
        setUploadHistory(prev => {
          const updated = [...prev, historyEntry].slice(-30); // Keep last 30 entries
          saveToStorage(STORAGE_KEYS.UPLOAD_HISTORY, updated);
          return updated;
        });
        
        const dupeMsg = removed > 0 ? ` (${removed} duplicates removed)` : '';
        toast.success(`Loaded ${totalParsed} rows from ${fileArray.length} file(s)${dupeMsg}`);
        return;
      }

      const file = fileArray[index];
      const reader = new FileReader();
      
      reader.onload = (e) => {
        const content = e.target?.result as string;
        const parsed = parseCSV(content, file.name);
        
        if (parsed.length > 0) {
          const validCount = parsed.filter(row => validateRow(row).length === 0).length;
          const season = detectSeason(file.name, parsed);
          const league = detectLeague(parsed);
          
          allRows.push(...parsed);
          newFiles.push({
            name: file.name,
            rows: parsed.length,
            validRows: validCount,
            size: file.size,
            season,
            league,
            uploadedAt: new Date().toISOString(),
          });
          totalParsed += parsed.length;
        }
        
        processNextFile(index + 1);
      };
      
      reader.readAsText(file);
    };

    processNextFile(0);
  }, [uploadedData, deduplicateRows]);

  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) processFiles(files);
  }, [processFiles]);

  const handleDragEnter = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files) processFiles(files);
  }, [processFiles]);

  const removeFile = useCallback((fileName: string) => {
    setUploadedData(prev => prev.filter(row => row.sourceFile !== fileName));
    setUploadedFiles(prev => prev.filter(f => f.name !== fileName));
    toast.info(`Removed ${fileName}`);
  }, []);

  const clearAllFiles = useCallback(() => {
    setUploadedData([]);
    setUploadedFiles([]);
    setDuplicatesRemoved(0);
    if (fileInputRef.current) fileInputRef.current.value = '';
    toast.info('Cleared all uploaded data');
  }, []);

  const handleExportCleanedData = useCallback(() => {
    const cleanedData = displayData
      .filter(row => validateRow(row).length === 0)
      .map(row => ({
        date: row.date, league: row.league, home: row.home, away: row.away,
        home_goals: row.home_goals, away_goals: row.away_goals,
        odds_h: row.odds_h, odds_d: row.odds_d, odds_a: row.odds_a,
      }));
    
    if (cleanedData.length === 0) {
      toast.error('No valid rows to export');
      return;
    }
    
    exportToCSV({
      filename: `cleaned-data-${new Date().toISOString().split('T')[0]}`,
      columns: [
        { header: 'date', accessor: 'date' }, { header: 'league', accessor: 'league' },
        { header: 'home', accessor: 'home' }, { header: 'away', accessor: 'away' },
        { header: 'home_goals', accessor: 'home_goals' }, { header: 'away_goals', accessor: 'away_goals' },
        { header: 'odds_h', accessor: 'odds_h' }, { header: 'odds_d', accessor: 'odds_d' }, { header: 'odds_a', accessor: 'odds_a' },
      ],
      data: cleanedData as unknown as Record<string, unknown>[],
    });
    toast.success(`Exported ${cleanedData.length} cleaned rows`);
  }, [displayData]);

  const handleRunPipeline = async () => {
    setIsRunning(true);
    
    // Reset steps
    setSteps(prev => prev.map(step => ({ ...step, status: 'pending', progress: 0, rowsProcessed: 0, rowsDropped: 0 })));
    setLiveStats({ totalRows: 0, processedRows: 0, validRows: 0, droppedRows: 0, currentStep: 'Starting...' });
    
    try {
      // Step 1: Column Selection
      setSteps(prev => prev.map((step, idx) => idx === 0 ? { ...step, status: 'running', progress: 0 } : step));
      setLiveStats(prev => ({ ...prev, currentStep: 'Column Selection' }));
      await new Promise(resolve => setTimeout(resolve, 500));
      setSteps(prev => prev.map((step, idx) => idx === 0 ? { ...step, status: 'completed', progress: 100 } : step));
      
      // Step 2: Type Normalization
      setSteps(prev => prev.map((step, idx) => idx === 1 ? { ...step, status: 'running', progress: 0 } : step));
      setLiveStats(prev => ({ ...prev, currentStep: 'Type Normalization' }));
      await new Promise(resolve => setTimeout(resolve, 500));
      setSteps(prev => prev.map((step, idx) => idx === 1 ? { ...step, status: 'completed', progress: 100 } : step));
      
      // Step 3: Team Standardization
      setSteps(prev => prev.map((step, idx) => idx === 2 ? { ...step, status: 'running', progress: 0 } : step));
      setLiveStats(prev => ({ ...prev, currentStep: 'Team Standardization' }));
      await new Promise(resolve => setTimeout(resolve, 500));
      setSteps(prev => prev.map((step, idx) => idx === 2 ? { ...step, status: 'completed', progress: 100 } : step));
      
      // Step 4: Data Validation
      setSteps(prev => prev.map((step, idx) => idx === 3 ? { ...step, status: 'running', progress: 0 } : step));
      setLiveStats(prev => ({ ...prev, currentStep: 'Data Validation' }));
      await new Promise(resolve => setTimeout(resolve, 500));
      setSteps(prev => prev.map((step, idx) => idx === 3 ? { ...step, status: 'completed', progress: 100 } : step));
      
      // Step 5: Feature Derivation
      setSteps(prev => prev.map((step, idx) => idx === 4 ? { ...step, status: 'running', progress: 0 } : step));
      setLiveStats(prev => ({ ...prev, currentStep: 'Feature Derivation' }));
      await new Promise(resolve => setTimeout(resolve, 500));
      setSteps(prev => prev.map((step, idx) => idx === 4 ? { ...step, status: 'completed', progress: 100 } : step));
      
      // Step 6: Load to Training Store (ACTUAL BACKEND CALL)
      setSteps(prev => prev.map((step, idx) => idx === 5 ? { ...step, status: 'running', progress: 0 } : step));
      setLiveStats(prev => ({ ...prev, currentStep: 'Preparing Training Data Files...' }));
      
      console.log('Calling backend API to prepare training data...');
      
      const response = await apiClient.prepareTrainingData({
        format: "both", // CSV + Parquet
        // league_codes: undefined means all leagues
      });
      
      if (response.success && response.data) {
        const data = response.data;
        const totalMatches = data.total_matches || 0;
        const successfulLeagues = data.successful || 0;
        const failedLeagues = data.failed || 0;
        
        setLiveStats(prev => ({ 
          ...prev, 
          currentStep: 'Complete', 
          totalRows: totalMatches,
          processedRows: totalMatches,
          validRows: totalMatches
        }));
        
        setSteps(prev => prev.map((step, idx) => idx === 5 ? { 
          ...step, 
          status: 'completed', 
          progress: 100,
          rowsProcessed: totalMatches
        } : step));
        
        toast.success(
          `Training data prepared successfully! ${successfulLeagues} leagues processed, ${totalMatches} matches total. Files saved to: ${data.output_directory || 'data/2_Cleaned_data'}`
        );
        
        console.log('Training data preparation complete:', data);
        } else {
        throw new Error('Failed to prepare training data');
      }
      
    } catch (error: any) {
      console.error('Error running pipeline:', error);
      
      // Mark current step as error
      setSteps(prev => prev.map(step => 
        step.status === 'running' ? { ...step, status: 'error', progress: 0 } : step
      ));
      
      setLiveStats(prev => ({ ...prev, currentStep: 'Error' }));
      
      toast.error(
        error?.message || 'Failed to prepare training data. Check console for details.'
      );
    } finally {
      setIsRunning(false);
    }
  };

  const getStatusIcon = (status: ETLStep['status']) => {
    switch (status) {
      case 'completed': return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'running': return <RefreshCw className="h-5 w-5 text-primary animate-spin" />;
      case 'error': return <AlertTriangle className="h-5 w-5 text-destructive" />;
      default: return <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/30" />;
    }
  };

  const getStatusBadge = (status: ETLStep['status']) => {
    switch (status) {
      case 'completed': return <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/30">Completed</Badge>;
      case 'running': return <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30">Running</Badge>;
      case 'error': return <Badge variant="destructive">Error</Badge>;
      default: return <Badge variant="secondary">Pending</Badge>;
    }
  };

  const getTypeBadge = (type: ColumnConfig['type']) => {
    const colors: Record<string, string> = {
      date: 'bg-purple-500/10 text-purple-500 border-purple-500/30',
      string: 'bg-blue-500/10 text-blue-500 border-blue-500/30',
      integer: 'bg-green-500/10 text-green-500 border-green-500/30',
      float: 'bg-amber-500/10 text-amber-500 border-amber-500/30',
    };
    return <Badge variant="outline" className={colors[type]}>{type}</Badge>;
  };

  const completedSteps = steps.filter(s => s.status === 'completed').length;
  const overallProgress = (completedSteps / steps.length) * 100;
  const selectedColumns = columns.filter(c => c.selected).length;
  const requiredColumns = columns.filter(c => c.required).length;
  const dataQuality = validationStats.totalRows > 0 ? ((validationStats.validRows / validationStats.totalRows) * 100).toFixed(1) : '0.0';
  const totalFileSize = uploadedFiles.reduce((acc, f) => acc + f.size, 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold tracking-tight">Data Cleaning & ETL</h1>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={resetConfig} className="gap-2">
              <RotateCcw className="h-4 w-4" />Reset Config
            </Button>
            <Button variant="outline" size="sm" onClick={saveConfig} className="gap-2">
              <Save className="h-4 w-4" />Save Config
            </Button>
          </div>
        </div>
        <p className="text-muted-foreground">Configure column selection, type normalization, and team name standardization</p>
      </div>

      <Tabs defaultValue="pipeline" className="space-y-6">
        <div className="w-full border-b border-border/40 bg-gradient-to-r from-background via-background/95 to-background">
          <TabsList className="w-full h-14 justify-start gap-1 bg-transparent p-0">
            <TabsTrigger 
              value="pipeline" 
              className="h-12 px-6 text-sm font-medium data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none border-b-2 border-transparent transition-all hover:bg-muted/50"
            >
              <Zap className="h-4 w-4 mr-2" />
              Pipeline
            </TabsTrigger>
            <TabsTrigger 
              value="upload"
              className="h-12 px-6 text-sm font-medium data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none border-b-2 border-transparent transition-all hover:bg-muted/50 relative"
            >
              <Upload className="h-4 w-4 mr-2" />
            Upload Data
              {uploadedFiles.length > 0 && (
                <Badge variant="secondary" className="ml-2 h-5 px-1.5 text-xs bg-primary/20 text-primary border-primary/30">
                  {uploadedFiles.length}
                </Badge>
              )}
          </TabsTrigger>
            <TabsTrigger 
              value="analytics"
              className="h-12 px-6 text-sm font-medium data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none border-b-2 border-transparent transition-all hover:bg-muted/50"
            >
              <BarChart3 className="h-4 w-4 mr-2" />
              Analytics
          </TabsTrigger>
            <TabsTrigger 
              value="columns"
              className="h-12 px-6 text-sm font-medium data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none border-b-2 border-transparent transition-all hover:bg-muted/50"
            >
              <Columns className="h-4 w-4 mr-2" />
              Columns
            </TabsTrigger>
            <TabsTrigger 
              value="teams"
              className="h-12 px-6 text-sm font-medium data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none border-b-2 border-transparent transition-all hover:bg-muted/50 relative"
            >
              <Users className="h-4 w-4 mr-2" />
              Team Mapping
              {teamMappings.length > 0 && (
                <Badge variant="secondary" className="ml-2 h-5 px-1.5 text-xs bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/30">
                  {teamMappings.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger 
              value="validation"
              className="h-12 px-6 text-sm font-medium data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none border-b-2 border-transparent transition-all hover:bg-muted/50"
            >
              <Filter className="h-4 w-4 mr-2" />
              Validation
              {validationStats.totalRows > 0 && (
                <Badge 
                  variant="secondary" 
                  className={`ml-2 h-5 px-1.5 text-xs ${
                    parseFloat(dataQuality) >= 80 
                      ? 'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/30'
                      : parseFloat(dataQuality) >= 50
                      ? 'bg-amber-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30'
                      : 'bg-destructive/20 text-destructive border-destructive/30'
                  }`}
                >
                  {dataQuality}%
                </Badge>
              )}
            </TabsTrigger>
        </TabsList>
        </div>

        {/* Pipeline Tab */}
        <TabsContent value="pipeline" className="space-y-6">
          <Card className="border-2 border-primary/20 bg-gradient-to-br from-background to-background/50 shadow-xl">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl flex items-center gap-2">
                    <Zap className="h-6 w-6 text-primary" />
                    ETL Pipeline
                  </CardTitle>
                  <CardDescription className="mt-1 text-base">
                    Process raw Football-Data.co.uk CSV into training-ready dataset
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    onClick={handleExportCleanedData} 
                    disabled={isRunning || validationStats.validRows === 0} 
                    className="gap-2 border-border/50 hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all"
                  >
                    <Download className="h-4 w-4" />Export Cleaned
                  </Button>
                  <Button 
                    onClick={handleRunPipeline} 
                    disabled={isRunning} 
                    className="gap-2 bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary shadow-lg hover:shadow-xl transition-all"
                  >
                    {isRunning ? (
                      <>
                        <RefreshCw className="h-4 w-4 animate-spin" />Running...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4" />Run Pipeline
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 p-4 rounded-lg bg-muted/30 border border-border/50">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-medium">Overall Progress</span>
                  <span className="font-bold text-primary">{completedSteps}/{steps.length} steps</span>
                </div>
                <Progress value={overallProgress} className="h-3 bg-muted" />
              </div>
            </CardContent>
          </Card>

          {isRunning && (
            <Card className="border-primary/50 bg-primary/5">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2"><RefreshCw className="h-4 w-4 animate-spin" />Live Pipeline Stats</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-5">
                  <div><div className="text-2xl font-bold">{liveStats.currentStep}</div><p className="text-xs text-muted-foreground">Current Step</p></div>
                  <div><div className="text-2xl font-bold">{liveStats.totalRows}</div><p className="text-xs text-muted-foreground">Total Rows</p></div>
                  <div><div className="text-2xl font-bold">{liveStats.processedRows}</div><p className="text-xs text-muted-foreground">Processed</p></div>
                  <div><div className="text-2xl font-bold text-green-500">{liveStats.validRows}</div><p className="text-xs text-muted-foreground">Valid</p></div>
                  <div><div className="text-2xl font-bold text-destructive">{liveStats.droppedRows}</div><p className="text-xs text-muted-foreground">Dropped</p></div>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="space-y-3">
            {steps.map((step, index) => (
              <Card key={step.id} className={step.status === 'running' ? 'ring-2 ring-primary/50' : ''}>
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    <div className="flex flex-col items-center gap-2">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted"><step.icon className="h-5 w-5 text-muted-foreground" /></div>
                      {index < steps.length - 1 && <div className={`w-0.5 h-6 ${step.status === 'completed' ? 'bg-green-500' : 'bg-muted'}`} />}
                    </div>
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {getStatusIcon(step.status)}
                          <div><h3 className="font-medium">{step.name}</h3><p className="text-sm text-muted-foreground">{step.description}</p></div>
                        </div>
                        <div className="flex items-center gap-2">
                          {step.rowsProcessed !== undefined && step.rowsProcessed > 0 && <span className="text-xs text-muted-foreground">{step.rowsProcessed} rows</span>}
                          {getStatusBadge(step.status)}
                        </div>
                      </div>
                      {step.status === 'running' && <Progress value={step.progress} className="h-1.5" />}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid gap-4 md:grid-cols-5">
            <Card><CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Columns</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{selectedColumns}</div><p className="text-xs text-muted-foreground">{requiredColumns} required</p></CardContent></Card>
            <Card><CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Team Mappings</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{teamMappings.length}</div><p className="text-xs text-muted-foreground">Standardization rules</p></CardContent></Card>
            <Card><CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Data Quality</CardTitle></CardHeader><CardContent><div className={`text-2xl font-bold ${parseFloat(dataQuality) >= 80 ? 'text-green-500' : parseFloat(dataQuality) >= 50 ? 'text-amber-500' : 'text-destructive'}`}>{dataQuality}%</div><p className="text-xs text-muted-foreground">After validation</p></CardContent></Card>
            <Card><CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Records Ready</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{validationStats.validRows.toLocaleString()}</div><p className="text-xs text-muted-foreground">For training</p></CardContent></Card>
            <Card><CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Duplicates Removed</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-amber-500">{duplicatesRemoved}</div><p className="text-xs text-muted-foreground">This session</p></CardContent></Card>
          </div>
        </TabsContent>

        {/* Upload Data Tab */}
        <TabsContent value="upload" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Upload className="h-5 w-5" />Upload CSV Data</CardTitle>
              <CardDescription>Upload multiple Football-Data.co.uk CSV files from different seasons. Duplicates are automatically detected and removed.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div 
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/30 hover:border-primary/50'}`}
                onDragEnter={handleDragEnter} onDragLeave={handleDragLeave} onDragOver={handleDragOver} onDrop={handleDrop}
              >
                <input ref={fileInputRef} type="file" accept=".csv" multiple onChange={handleFileUpload} className="hidden" id="csv-upload" />
                <Files className={`h-12 w-12 mx-auto mb-4 ${isDragging ? 'text-primary' : 'text-muted-foreground'}`} />
                <h3 className="font-medium mb-2">{isDragging ? 'Drop files here' : 'Drag & drop CSV files here'}</h3>
                <p className="text-sm text-muted-foreground mb-4">Supports batch upload with automatic season detection & deduplication</p>
                <Button asChild><label htmlFor="csv-upload" className="cursor-pointer gap-2"><Upload className="h-4 w-4" />Choose Files</label></Button>
              </div>

              {uploadedFiles.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium">Uploaded Files ({uploadedFiles.length})</h4>
                      <p className="text-sm text-muted-foreground">Total size: {formatFileSize(totalFileSize)}</p>
                    </div>
                    <Button variant="ghost" size="sm" onClick={clearAllFiles} className="text-destructive hover:text-destructive"><Trash2 className="h-4 w-4 mr-2" />Clear All</Button>
                  </div>
                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {uploadedFiles.map((file) => (
                      <div key={file.name} className="flex items-center justify-between p-3 rounded-lg bg-muted/50 border">
                        <div className="flex items-center gap-3">
                          <FileText className="h-5 w-5 text-primary" />
                          <div>
                            <p className="font-medium text-sm">{file.name}</p>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              <span className="flex items-center gap-1"><HardDrive className="h-3 w-3" />{formatFileSize(file.size)}</span>
                              <span className="flex items-center gap-1"><Calendar className="h-3 w-3" />{file.season}</span>
                              <span>{file.league}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/30">{file.validRows} valid</Badge>
                          <Badge variant="outline" className="bg-destructive/10 text-destructive border-destructive/30">{file.rows - file.validRows} invalid</Badge>
                          <Button variant="ghost" size="icon" onClick={() => removeFile(file.name)} className="h-8 w-8"><X className="h-4 w-4" /></Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {duplicatesRemoved > 0 && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
                  <Copy className="h-5 w-5 text-amber-500" />
                  <div>
                    <p className="font-medium text-amber-600 dark:text-amber-400">{duplicatesRemoved} duplicates detected and removed</p>
                    <p className="text-sm text-muted-foreground">Matches with same date, teams, and league are deduplicated automatically</p>
                  </div>
                </div>
              )}

              {uploadedData.length > 0 && (
                <div className="grid gap-4 md:grid-cols-4">
                  <div className="rounded-lg border p-3"><div className="text-2xl font-bold">{validationStats.totalRows}</div><p className="text-sm text-muted-foreground">Total Rows</p></div>
                  <div className="rounded-lg border p-3"><div className="text-2xl font-bold text-green-500">{validationStats.validRows}</div><p className="text-sm text-muted-foreground">Valid Rows</p></div>
                  <div className="rounded-lg border p-3"><div className="text-2xl font-bold text-destructive">{validationStats.nullGoalsCount}</div><p className="text-sm text-muted-foreground">Null Goals</p></div>
                  <div className="rounded-lg border p-3"><div className="text-2xl font-bold text-amber-500">{validationStats.invalidOddsCount}</div><p className="text-sm text-muted-foreground">Invalid Odds</p></div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Download className="h-5 w-5" />Export Cleaned Data</CardTitle>
              <CardDescription>Download validated data as CSV for model training</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50 border">
                <div><p className="font-medium">Cleaned Dataset</p><p className="text-sm text-muted-foreground">{validationStats.validRows} valid rows ready for export</p></div>
                <Button onClick={handleExportCleanedData} disabled={validationStats.validRows === 0} className="gap-2"><Download className="h-4 w-4" />Export CSV</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Season Distribution */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Calendar className="h-5 w-5" />Season Distribution</CardTitle>
                <CardDescription>Matches loaded per season</CardDescription>
              </CardHeader>
              <CardContent>
                {seasonDistribution.length > 0 ? (
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={seasonDistribution}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="season" className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                      <YAxis className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                      <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }} />
                      <Bar dataKey="rows" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[250px] flex items-center justify-center text-muted-foreground">Upload CSV files to see season distribution</div>
                )}
              </CardContent>
            </Card>

            {/* Data Quality Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><TrendingUp className="h-5 w-5" />Data Quality Breakdown</CardTitle>
                <CardDescription>Distribution of valid vs invalid records</CardDescription>
              </CardHeader>
              <CardContent>
                {qualityDistribution.length > 0 ? (
                  <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie data={qualityDistribution} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={2} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                        {qualityDistribution.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[250px] flex items-center justify-center text-muted-foreground">Upload CSV files to see quality breakdown</div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Historical Quality Trend */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><BarChart3 className="h-5 w-5" />Upload History & Quality Trend</CardTitle>
              <CardDescription>Historical data quality across upload sessions</CardDescription>
            </CardHeader>
            <CardContent>
              {uploadHistory.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={uploadHistory}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="date" className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                    <YAxis yAxisId="left" className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                    <YAxis yAxisId="right" orientation="right" className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} domain={[0, 100]} />
                    <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }} />
                    <Legend />
                    <Line yAxisId="left" type="monotone" dataKey="totalRows" stroke="hsl(var(--primary))" name="Total Rows" strokeWidth={2} />
                    <Line yAxisId="left" type="monotone" dataKey="validRows" stroke="hsl(142, 76%, 36%)" name="Valid Rows" strokeWidth={2} />
                    <Line yAxisId="right" type="monotone" dataKey="dataQuality" stroke="hsl(38, 92%, 50%)" name="Quality %" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground">Upload history will appear here after processing files</div>
              )}
            </CardContent>
          </Card>

          {/* Summary Stats */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card><CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Total Files Uploaded</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{uploadedFiles.length}</div><p className="text-xs text-muted-foreground">This session</p></CardContent></Card>
            <Card><CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Total Data Size</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{formatFileSize(totalFileSize)}</div><p className="text-xs text-muted-foreground">Uploaded CSV files</p></CardContent></Card>
            <Card><CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Unique Seasons</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{new Set(uploadedFiles.map(f => f.season)).size}</div><p className="text-xs text-muted-foreground">Detected from data</p></CardContent></Card>
            <Card><CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Avg. Quality</CardTitle></CardHeader><CardContent><div className={`text-2xl font-bold ${parseFloat(dataQuality) >= 80 ? 'text-green-500' : parseFloat(dataQuality) >= 50 ? 'text-amber-500' : 'text-destructive'}`}>{dataQuality}%</div><p className="text-xs text-muted-foreground">Valid rows ratio</p></CardContent></Card>
          </div>
        </TabsContent>

        {/* Column Selection Tab */}
        <TabsContent value="columns" className="space-y-6">
          <Card className="border-2 border-primary/20 bg-gradient-to-br from-background to-background/50 shadow-xl">
            <CardHeader className="pb-4">
              <CardTitle className="text-2xl flex items-center gap-2">
                <Columns className="h-6 w-6 text-primary" />
                Column Selection & Type Mapping
              </CardTitle>
              <CardDescription className="mt-1 text-base">
                Select columns from raw Football-Data.co.uk CSV and define type conversions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg overflow-hidden bg-background/50">
                <div className="max-h-[600px] overflow-y-auto">
              <Table>
                    <TableHeader className="sticky top-0 bg-muted/50 backdrop-blur-sm z-10">
                  <TableRow>
                        <TableHead className="w-12 font-semibold">Select</TableHead>
                        <TableHead className="font-semibold">Raw Column</TableHead>
                    <TableHead className="w-8"></TableHead>
                        <TableHead className="font-semibold">Canonical Name</TableHead>
                        <TableHead className="font-semibold">Type</TableHead>
                        <TableHead className="font-semibold">Required</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {columns.map((col) => (
                        <TableRow 
                          key={col.raw} 
                          className={`transition-colors ${col.selected ? 'bg-background hover:bg-muted/50' : 'opacity-50 hover:bg-muted/30'}`}
                        >
                          <TableCell>
                            <Checkbox 
                              checked={col.selected} 
                              onCheckedChange={() => toggleColumn(col.raw)} 
                              disabled={col.required}
                              className="border-border/50"
                            />
                          </TableCell>
                          <TableCell className="font-mono text-sm font-medium">{col.raw}</TableCell>
                          <TableCell><ChevronRight className="h-4 w-4 text-primary" /></TableCell>
                          <TableCell className="font-mono text-sm text-primary font-semibold">{col.canonical}</TableCell>
                      <TableCell>{getTypeBadge(col.type)}</TableCell>
                          <TableCell>
                            {col.required ? (
                              <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/30">
                                Required
                              </Badge>
                            ) : (
                              <Badge variant="secondary" className="bg-muted text-muted-foreground">
                                Optional
                              </Badge>
                            )}
                          </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-2 border-primary/10 bg-gradient-to-br from-background to-background/50">
            <CardHeader>
              <CardTitle className="text-xl flex items-center gap-2">
                <Type className="h-5 w-5 text-primary" />
                Type Conversion Rules
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border-2 border-purple-500/20 bg-gradient-to-br from-purple-500/5 to-transparent p-4 space-y-2 hover:border-purple-500/40 transition-colors">
                  <div className="flex items-center gap-2">
                    {getTypeBadge('date')}
                    <span className="font-semibold">Date Conversion</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Convert <code className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono">DD/MM/YYYY</code> → ISO format
                  </p>
                </div>
                <div className="rounded-lg border-2 border-green-500/20 bg-gradient-to-br from-green-500/5 to-transparent p-4 space-y-2 hover:border-green-500/40 transition-colors">
                  <div className="flex items-center gap-2">
                    {getTypeBadge('integer')}
                    <span className="font-semibold">Integer Conversion</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Goals must be integers. Drop rows with null goals.
                  </p>
                </div>
                <div className="rounded-lg border-2 border-amber-500/20 bg-gradient-to-br from-amber-500/5 to-transparent p-4 space-y-2 hover:border-amber-500/40 transition-colors">
                  <div className="flex items-center gap-2">
                    {getTypeBadge('float')}
                    <span className="font-semibold">Float Conversion</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Odds as floats. Drop rows with odds ≤ 1.01.
                  </p>
                </div>
                <div className="rounded-lg border-2 border-blue-500/20 bg-gradient-to-br from-blue-500/5 to-transparent p-4 space-y-2 hover:border-blue-500/40 transition-colors">
                  <div className="flex items-center gap-2">
                    {getTypeBadge('string')}
                    <span className="font-semibold">String Normalization</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Trim whitespace, apply team name mappings.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Team Mapping Tab */}
        <TabsContent value="teams" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-3">
            <Card className="md:col-span-2 border-2 border-primary/20 bg-gradient-to-br from-background to-background/50">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2 text-xl">
                      <Users className="h-5 w-5 text-primary" />
                      Team Name Standardization
                    </CardTitle>
                    <CardDescription className="mt-1">
                      Map variant team names to canonical names across seasons. All teams from database are automatically loaded.
                    </CardDescription>
                  </div>
                  <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30">
                    {teamMappings.length} Mappings
                  </Badge>
                </div>
            </CardHeader>
            <CardContent className="space-y-6">
                <div className="flex gap-4 items-end p-4 rounded-lg bg-muted/30 border border-border/50">
                  <div className="flex-1 space-y-2">
                    <Label htmlFor="raw" className="text-sm font-medium">Raw Name (as in CSV)</Label>
                    <Input 
                      id="raw" 
                      placeholder="e.g., Man United" 
                      value={newMapping.raw} 
                      onChange={(e) => setNewMapping(prev => ({ ...prev, raw: e.target.value }))}
                      className="bg-background"
                    />
              </div>
                  <ArrowRight className="h-5 w-5 text-primary mb-3" />
                  <div className="flex-1 space-y-2 relative">
                    <Label htmlFor="canonical" className="text-sm font-medium">Canonical Name</Label>
                    <Input 
                      id="canonical" 
                      placeholder="e.g., Manchester United" 
                      value={newMapping.canonical} 
                      onChange={(e) => setNewMapping(prev => ({ ...prev, canonical: e.target.value }))}
                      className="bg-background"
                    />
                    {teamSearchResults.length > 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-popover border border-border rounded-md shadow-lg max-h-48 overflow-y-auto">
                        {teamSearchResults.map((team) => (
                          <div
                            key={team.id}
                            className="p-2 hover:bg-muted cursor-pointer text-sm"
                            onClick={() => {
                              setNewMapping(prev => ({ ...prev, canonical: team.canonicalName }));
                              setTeamSearchResults([]);
                            }}
                          >
                            <div className="font-medium">{team.canonicalName}</div>
                            <div className="text-xs text-muted-foreground">
                              {team.name} • Similarity: {(team.similarity * 100).toFixed(0)}%
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <Button 
                    onClick={addTeamMapping} 
                    className="gap-2 bg-primary hover:bg-primary/90"
                    disabled={!newMapping.raw || !newMapping.canonical}
                  >
                    <Plus className="h-4 w-4" />Add
                  </Button>
                </div>
                
                <div className="border rounded-lg overflow-hidden bg-background/50">
                  <div className="max-h-[500px] overflow-y-auto">
              <Table>
                      <TableHeader className="sticky top-0 bg-muted/50 backdrop-blur-sm z-10">
                        <TableRow>
                          <TableHead className="font-semibold">Raw Name</TableHead>
                          <TableHead className="w-8"></TableHead>
                          <TableHead className="font-semibold">Canonical Name</TableHead>
                          <TableHead className="font-semibold">League</TableHead>
                          <TableHead className="w-20 text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                <TableBody>
                        {teamMappings.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                              {isLoadingTeams ? 'Loading teams from database...' : 'No team mappings yet. Add your first mapping above.'}
                            </TableCell>
                    </TableRow>
                        ) : (
                          teamMappings.map((mapping, index) => {
                            const teamInfo = allTeams.find(t => t.canonicalName === mapping.canonical || t.name === mapping.raw);
                            // Use unique key: combination of raw name, canonical name, and index to handle duplicates
                            const uniqueKey = `${mapping.raw}-${mapping.canonical}-${index}-${teamInfo?.id || 'no-id'}`;
                            return (
                              <TableRow key={uniqueKey} className="hover:bg-muted/50 transition-colors">
                                <TableCell className="font-mono text-sm font-medium">{mapping.raw}</TableCell>
                                <TableCell><ArrowRight className="h-4 w-4 text-primary" /></TableCell>
                                <TableCell className="font-mono text-sm text-primary font-semibold">{mapping.canonical}</TableCell>
                                <TableCell>
                                  {teamInfo?.leagueName ? (
                                    <Badge variant="outline" className="text-xs">
                                      {teamInfo.leagueName}
                                    </Badge>
                                  ) : (
                                    <span className="text-xs text-muted-foreground">-</span>
                                  )}
                                </TableCell>
                                <TableCell className="text-right">
                                  <Button 
                                    variant="ghost" 
                                    size="icon" 
                                    onClick={() => removeTeamMapping(mapping.raw)} 
                                    className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </TableCell>
                              </TableRow>
                            );
                          })
                        )}
                </TableBody>
              </Table>
                  </div>
                </div>
            </CardContent>
          </Card>
            
            <Card className="border-2 border-primary/10 bg-gradient-to-br from-background to-background/50">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Database className="h-5 w-5 text-primary" />
                  Database Teams
                </CardTitle>
                <CardDescription>Teams loaded from database</CardDescription>
              </CardHeader>
              <CardContent>
                {isLoadingTeams ? (
                  <div className="flex items-center justify-center py-8">
                    <RefreshCw className="h-6 w-6 animate-spin text-primary" />
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="text-3xl font-bold text-primary">{allTeams.length}</div>
                    <p className="text-sm text-muted-foreground">Total teams in database</p>
                    <div className="mt-4 space-y-2 max-h-[300px] overflow-y-auto">
                      {allTeams.slice(0, 20).map((team) => (
                        <div key={team.id} className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border/50 text-sm">
                          <div>
                            <div className="font-medium">{team.canonicalName}</div>
                            <div className="text-xs text-muted-foreground">{team.name}</div>
                          </div>
                          {team.leagueName && (
                            <Badge variant="outline" className="text-xs">
                              {team.leagueName}
                            </Badge>
                          )}
                        </div>
                      ))}
                      {allTeams.length > 20 && (
                        <p className="text-xs text-muted-foreground text-center pt-2">
                          +{allTeams.length - 20} more teams
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Validation Preview Tab */}
        <TabsContent value="validation" className="space-y-6">
          <Card className="border-2 border-primary/20 bg-gradient-to-br from-background to-background/50 shadow-xl">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl flex items-center gap-2">
                    <Filter className="h-6 w-6 text-primary" />
                    Data Validation Preview
                  </CardTitle>
                  <CardDescription className="mt-1 text-base">
                    Preview data with validation rules applied. Invalid rows are highlighted.
                    {uploadedFiles.length > 0 && (
                      <span className="ml-2 text-primary font-medium">({uploadedFiles.length} files loaded)</span>
                    )}
                  </CardDescription>
                </div>
                <Button 
                  variant="outline" 
                  onClick={handleExportCleanedData} 
                  disabled={validationStats.validRows === 0} 
                  className="gap-2 border-border/50 hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all"
                >
                  <Download className="h-4 w-4" />Export Valid Rows
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Legend */}
              <div className="flex gap-6 mb-4 flex-wrap p-4 rounded-lg bg-muted/30 border border-border/50">
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 rounded bg-destructive/20 border-2 border-destructive/50" />
                  <span className="text-sm font-medium">Null Goals</span>
              </div>
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 rounded bg-amber-500/20 border-2 border-amber-500/50" />
                  <span className="text-sm font-medium">Invalid Odds (≤1.01)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 rounded bg-purple-500/20 border-2 border-purple-500/50" />
                  <span className="text-sm font-medium">Malformed Date</span>
                </div>
              </div>
              
              {/* Validation Table */}
              <div className="border-2 border-border/50 rounded-lg overflow-hidden bg-background/50">
                <div className="max-h-[500px] overflow-y-auto">
                <Table>
                    <TableHeader className="sticky top-0 bg-muted/80 backdrop-blur-sm z-10 border-b-2 border-border/50">
                    <TableRow>
                        <TableHead className="w-12 font-semibold">#</TableHead>
                        <TableHead className="font-semibold">Date</TableHead>
                        <TableHead className="font-semibold">League</TableHead>
                        <TableHead className="font-semibold">Home</TableHead>
                        <TableHead className="font-semibold">Away</TableHead>
                        <TableHead className="text-center font-semibold">HG</TableHead>
                        <TableHead className="text-center font-semibold">AG</TableHead>
                        <TableHead className="text-right font-semibold">H</TableHead>
                        <TableHead className="text-right font-semibold">D</TableHead>
                        <TableHead className="text-right font-semibold">A</TableHead>
                        <TableHead className="font-semibold">Issues</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {displayData.slice(0, 100).map((row, idx) => {
                      const issues = validateRow(row);
                      const hasIssues = issues.length > 0;
                      return (
                          <TableRow 
                            key={idx} 
                            className={`transition-colors ${hasIssues ? 'bg-destructive/5 hover:bg-destructive/10' : 'hover:bg-muted/30'}`}
                          >
                            <TableCell className="text-muted-foreground font-medium">{idx + 1}</TableCell>
                            <TableCell className={`font-mono text-sm font-medium ${issues.includes('date') ? 'bg-purple-500/20 text-purple-600 dark:text-purple-400 rounded px-2 py-1' : ''}`}>
                              {row.date}
                            </TableCell>
                            <TableCell className="font-medium">{row.league}</TableCell>
                            <TableCell className="font-medium">{row.home}</TableCell>
                            <TableCell className="font-medium">{row.away}</TableCell>
                            <TableCell className={`text-center font-mono font-bold ${issues.includes('home_goals') ? 'bg-destructive/20 text-destructive rounded px-2 py-1' : ''}`}>
                              {row.home_goals ?? <span className="text-destructive">NULL</span>}
                            </TableCell>
                            <TableCell className={`text-center font-mono font-bold ${issues.includes('away_goals') ? 'bg-destructive/20 text-destructive rounded px-2 py-1' : ''}`}>
                              {row.away_goals ?? <span className="text-destructive">NULL</span>}
                            </TableCell>
                            <TableCell className={`text-right font-mono ${issues.includes('odds_h') ? 'bg-amber-500/20 text-amber-600 dark:text-amber-400 rounded px-2 py-1' : ''}`}>
                              {row.odds_h?.toFixed(2) ?? '-'}
                            </TableCell>
                            <TableCell className={`text-right font-mono ${issues.includes('odds_d') ? 'bg-amber-500/20 text-amber-600 dark:text-amber-400 rounded px-2 py-1' : ''}`}>
                              {row.odds_d?.toFixed(2) ?? '-'}
                            </TableCell>
                            <TableCell className={`text-right font-mono ${issues.includes('odds_a') ? 'bg-amber-500/20 text-amber-600 dark:text-amber-400 rounded px-2 py-1' : ''}`}>
                              {row.odds_a?.toFixed(2) ?? '-'}
                            </TableCell>
                          <TableCell>
                            {hasIssues ? (
                                <div className="flex gap-1 flex-wrap">
                                  {issues.map((issue) => (
                                    <Badge 
                                      key={issue} 
                                      variant="outline" 
                                      className={getIssueBadgeClass(issue)}
                                    >
                                      {getIssueLabel(issue)}
                                    </Badge>
                                  ))}
                                </div>
                            ) : (
                                <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/30">
                                  Valid
                                </Badge>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
              </div>
              {displayData.length > 100 && (
                <p className="text-sm text-muted-foreground text-center">
                  Showing first 100 of {displayData.length} rows
                </p>
              )}

              {/* Validation Stats */}
              <div className="grid gap-4 md:grid-cols-4">
                <Card className="border-2 border-green-500/20 bg-gradient-to-br from-green-500/5 to-transparent">
                  <CardContent className="p-4">
                    <div className="text-3xl font-bold text-green-500">{validationStats.validRows}</div>
                    <p className="text-sm text-muted-foreground mt-1">Valid Rows</p>
                  </CardContent>
                </Card>
                <Card className="border-2 border-destructive/20 bg-gradient-to-br from-destructive/5 to-transparent">
                  <CardContent className="p-4">
                    <div className="text-3xl font-bold text-destructive">{validationStats.nullGoalsCount}</div>
                    <p className="text-sm text-muted-foreground mt-1">Null Goals</p>
                  </CardContent>
                </Card>
                <Card className="border-2 border-amber-500/20 bg-gradient-to-br from-amber-500/5 to-transparent">
                  <CardContent className="p-4">
                    <div className="text-3xl font-bold text-amber-500">{validationStats.invalidOddsCount}</div>
                    <p className="text-sm text-muted-foreground mt-1">Invalid Odds</p>
                  </CardContent>
                </Card>
                <Card className="border-2 border-purple-500/20 bg-gradient-to-br from-purple-500/5 to-transparent">
                  <CardContent className="p-4">
                    <div className="text-3xl font-bold text-purple-500">{validationStats.malformedDateCount}</div>
                    <p className="text-sm text-muted-foreground mt-1">Malformed Dates</p>
                  </CardContent>
                </Card>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
