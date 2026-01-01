import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, Upload, AlertTriangle, ArrowRight, Sparkles, Target, FileText, Loader2, Save, FolderOpen, X, Calendar, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Badge } from '@/components/ui/badge';
import { PDFJackpotImport, ParsedFixture } from '@/components/PDFJackpotImport';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/services/api';
import type { Fixture } from '@/types';

interface TeamValidation {
  isValid: boolean;
  isValidating: boolean;
  normalizedName?: string;
  suggestions?: string[];
  confidence?: number;
}

interface EditableFixture extends Omit<Fixture, 'id'> {
  id: string;
  tempId: string;
  homeTeamValidation?: TeamValidation;
  awayTeamValidation?: TeamValidation;
}

const createEmptyFixture = (): EditableFixture => ({
  id: '',
  tempId: crypto.randomUUID(),
  homeTeam: '',
  awayTeam: '',
  homeOdds: 0,
  drawOdds: 0,
  awayOdds: 0,
  validationWarnings: [],
  homeTeamValidation: undefined,
  awayTeamValidation: undefined,
});

export default function JackpotInput() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [fixtures, setFixtures] = useState<EditableFixture[]>([
    createEmptyFixture(),
  ]);
  const [bulkInput, setBulkInput] = useState('');
  const [isBulkDialogOpen, setIsBulkDialogOpen] = useState(false);
  const [isPDFDialogOpen, setIsPDFDialogOpen] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [savedTemplates, setSavedTemplates] = useState<any[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [isSaveDialogOpen, setIsSaveDialogOpen] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [saveDescription, setSaveDescription] = useState('');
  const validationTimersRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  // Debounced team validation
  const validateTeam = useCallback(async (tempId: string, teamType: 'home' | 'away', teamName: string) => {
    // Clear existing timer for this team
    const timerKey = `${tempId}-${teamType}`;
    const existingTimer = validationTimersRef.current.get(timerKey);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }

    // Set validating state
    setFixtures(prev => prev.map(f => 
      f.tempId === tempId 
        ? { 
            ...f, 
            [teamType === 'home' ? 'homeTeamValidation' : 'awayTeamValidation']: { 
              isValid: false, 
              isValidating: true 
            } 
          }
        : f
    ));

    // Debounce validation (wait 500ms after user stops typing)
    const timer = setTimeout(async () => {
      if (!teamName || teamName.trim().length < 2) {
        setFixtures(prev => prev.map(f => 
          f.tempId === tempId 
            ? { 
                ...f, 
                [teamType === 'home' ? 'homeTeamValidation' : 'awayTeamValidation']: undefined 
              }
            : f
        ));
        return;
      }

      try {
        const response = await apiClient.validateTeamName(teamName.trim());
        if (response.success && response.data) {
          setFixtures(prev => prev.map(f => 
            f.tempId === tempId 
              ? { 
                  ...f, 
                  [teamType === 'home' ? 'homeTeamValidation' : 'awayTeamValidation']: {
                    isValid: response.data.isValid,
                    isValidating: false,
                    normalizedName: response.data.normalizedName,
                    suggestions: response.data.suggestions,
                    confidence: response.data.confidence
                  }
                }
              : f
          ));
        }
      } catch (error) {
        console.error('Error validating team:', error);
        setFixtures(prev => prev.map(f => 
          f.tempId === tempId 
            ? { 
                ...f, 
                [teamType === 'home' ? 'homeTeamValidation' : 'awayTeamValidation']: {
                  isValid: false,
                  isValidating: false
                }
              }
            : f
        ));
      }
    }, 500);

    validationTimersRef.current.set(timerKey, timer);
  }, []);

  // Validate all teams in fixtures
  const validateAllTeams = useCallback(async () => {
    for (const fixture of fixtures) {
      if (fixture.homeTeam.trim().length >= 2) {
        await validateTeam(fixture.tempId, 'home', fixture.homeTeam);
      }
      if (fixture.awayTeam.trim().length >= 2) {
        await validateTeam(fixture.tempId, 'away', fixture.awayTeam);
      }
    }
  }, [fixtures, validateTeam]);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      validationTimersRef.current.forEach(timer => clearTimeout(timer));
      validationTimersRef.current.clear();
    };
  }, []);

  const handlePDFImport = useCallback((parsedFixtures: ParsedFixture[]) => {
    const newFixtures: EditableFixture[] = parsedFixtures.map(f => ({
      id: f.id,
      tempId: crypto.randomUUID(),
      homeTeam: f.homeTeam,
      awayTeam: f.awayTeam || 'Away Team',
      homeOdds: f.homeOdds,
      drawOdds: f.drawOdds,
      awayOdds: f.awayOdds,
      validationWarnings: [],
      homeTeamValidation: undefined,
      awayTeamValidation: undefined,
    }));
    setFixtures(newFixtures);
    // Validate teams after import
    setTimeout(() => {
      newFixtures.forEach(fixture => {
        if (fixture.homeTeam.trim().length >= 2) {
          validateTeam(fixture.tempId, 'home', fixture.homeTeam);
        }
        if (fixture.awayTeam.trim().length >= 2) {
          validateTeam(fixture.tempId, 'away', fixture.awayTeam);
        }
      });
    }, 100);
  }, [validateTeam]);
  const addFixture = useCallback(() => {
    setFixtures((prev) => [...prev, createEmptyFixture()]);
  }, []);

  const removeFixture = useCallback((tempId: string) => {
    setFixtures((prev) => prev.filter((f) => f.tempId !== tempId));
  }, []);

  const updateFixture = useCallback(
    (tempId: string, field: keyof EditableFixture, value: string | number) => {
      setFixtures((prev) =>
        prev.map((f) =>
          f.tempId === tempId ? { ...f, [field]: value } : f
        )
      );
      
      // Validate team name when it changes
      if (field === 'homeTeam' && typeof value === 'string') {
        validateTeam(tempId, 'home', value);
      } else if (field === 'awayTeam' && typeof value === 'string') {
        validateTeam(tempId, 'away', value);
      }
    },
    [validateTeam]
  );

  const parseOdds = (value: string): number => {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? 0 : parsed;
  };

  const validateFixtures = useCallback((): boolean => {
    const errors: string[] = [];
    
    fixtures.forEach((fixture, index) => {
      if (!fixture.homeTeam.trim()) {
        errors.push(`Row ${index + 1}: Home team is required`);
      }
      if (!fixture.awayTeam.trim()) {
        errors.push(`Row ${index + 1}: Away team is required`);
      }
      if (fixture.homeOdds <= 1) {
        errors.push(`Row ${index + 1}: Home odds must be greater than 1.00`);
      }
      if (fixture.drawOdds <= 1) {
        errors.push(`Row ${index + 1}: Draw odds must be greater than 1.00`);
      }
      if (fixture.awayOdds <= 1) {
        errors.push(`Row ${index + 1}: Away odds must be greater than 1.00`);
      }
    });

    setValidationErrors(errors);
    return errors.length === 0;
  }, [fixtures]);

  const handleBulkImport = useCallback(() => {
    const lines = bulkInput.trim().split('\n');
    const newFixtures: EditableFixture[] = [];

    lines.forEach((line) => {
      const parts = line.split(/[,\t]/);
      if (parts.length >= 5) {
        newFixtures.push({
          id: '',
          tempId: crypto.randomUUID(),
          homeTeam: parts[0].trim(),
          awayTeam: parts[1].trim(),
          homeOdds: parseOdds(parts[2]),
          drawOdds: parseOdds(parts[3]),
          awayOdds: parseOdds(parts[4]),
          validationWarnings: [],
          homeTeamValidation: undefined,
          awayTeamValidation: undefined,
        });
      }
    });

    if (newFixtures.length > 0) {
      setFixtures(newFixtures);
      setBulkInput('');
      setIsBulkDialogOpen(false);
      // Validate teams after bulk import
      setTimeout(() => {
        newFixtures.forEach(fixture => {
          if (fixture.homeTeam.trim().length >= 2) {
            validateTeam(fixture.tempId, 'home', fixture.homeTeam);
          }
          if (fixture.awayTeam.trim().length >= 2) {
            validateTeam(fixture.tempId, 'away', fixture.awayTeam);
          }
        });
      }, 100);
    }
  }, [bulkInput, validateTeam]);

  const handleSubmit = useCallback(async () => {
    if (!validateFixtures()) {
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      // Convert fixtures to API format
      const apiFixtures = fixtures.map(f => ({
        id: f.tempId,
        homeTeam: f.homeTeam.trim(),
        awayTeam: f.awayTeam.trim(),
        odds: {
          home: f.homeOdds,
          draw: f.drawOdds,
          away: f.awayOdds,
        },
        matchDate: null,
        league: null,
      }));
      
      // Create jackpot
      const response = await apiClient.createJackpot(apiFixtures);
      
      if (response.success && response.data) {
        const jackpotId = response.data.id;
        
        toast({
          title: "Jackpot created",
          description: "Calculating probabilities...",
        });
        
        // Navigate to probability output page with jackpot ID
        navigate(`/probability-output?jackpotId=${jackpotId}`);
      } else {
        throw new Error(response.message || "Failed to create jackpot");
      }
    } catch (error: any) {
      console.error("Error creating jackpot:", error);
      toast({
        title: "Error",
        description: error.message || "Failed to create jackpot. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [fixtures, validateFixtures, navigate, toast]);

  // Load saved templates
  const loadTemplates = useCallback(async () => {
    try {
      setLoadingTemplates(true);
      const response = await apiClient.getTemplates(50);
      if (response.success && response.data) {
        setSavedTemplates(response.data.templates || []);
      }
    } catch (error: any) {
      console.error('Error loading templates:', error);
      toast({
        title: 'Error',
        description: 'Failed to load saved lists',
        variant: 'destructive',
      });
    } finally {
      setLoadingTemplates(false);
    }
  }, [toast]);

  // Load templates on mount
  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  // Save current list as template
  const handleSaveTemplate = useCallback(async () => {
    if (!validateFixtures() || !saveName.trim()) {
      toast({
        title: 'Error',
        description: 'Please provide a name for the list',
        variant: 'destructive',
      });
      return;
    }

    try {
      const apiFixtures = fixtures.map(f => ({
        id: f.tempId,
        homeTeam: f.homeTeam.trim(),
        awayTeam: f.awayTeam.trim(),
        odds: {
          home: f.homeOdds,
          draw: f.drawOdds,
          away: f.awayOdds,
        },
        matchDate: null,
        league: null,
      }));

      const response = await apiClient.saveTemplate(
        saveName.trim(),
        saveDescription.trim() || null,
        apiFixtures
      );

      if (response.success) {
        toast({
          title: 'Success',
          description: 'List saved successfully',
        });
        setIsSaveDialogOpen(false);
        setSaveName('');
        setSaveDescription('');
        loadTemplates();
      }
    } catch (error: any) {
      console.error('Error saving template:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to save list',
        variant: 'destructive',
      });
    }
  }, [fixtures, saveName, saveDescription, validateFixtures, toast, loadTemplates]);

  // Load template into input form
  const handleLoadTemplate = useCallback(async (templateId: number) => {
    try {
      const response = await apiClient.getTemplate(templateId);
      if (response.success && response.data) {
        const loadedFixtures: EditableFixture[] = response.data.fixtures.map((f: any, idx: number) => ({
          id: f.id || '',
          tempId: crypto.randomUUID(),
          homeTeam: f.homeTeam || '',
          awayTeam: f.awayTeam || '',
          homeOdds: f.odds?.home || 2.0,
          drawOdds: f.odds?.draw || 3.0,
          awayOdds: f.odds?.away || 2.5,
          validationWarnings: [],
          homeTeamValidation: undefined,
          awayTeamValidation: undefined,
        }));
        setFixtures(loadedFixtures);
        toast({
          title: 'Success',
          description: 'List loaded successfully. Validating teams...',
        });
        // Validate teams after loading
        setTimeout(() => {
          loadedFixtures.forEach(fixture => {
            if (fixture.homeTeam.trim().length >= 2) {
              validateTeam(fixture.tempId, 'home', fixture.homeTeam);
            }
            if (fixture.awayTeam.trim().length >= 2) {
              validateTeam(fixture.tempId, 'away', fixture.awayTeam);
            }
          });
        }, 100);
      }
    } catch (error: any) {
      console.error('Error loading template:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to load list',
        variant: 'destructive',
      });
    }
  }, [toast, validateTeam]);

  // Calculate probabilities from template
  const handleCalculateFromTemplate = useCallback(async (templateId: number) => {
    try {
      setIsSubmitting(true);
      const response = await apiClient.calculateFromTemplate(templateId);
      if (response.success && response.data) {
        const jackpotId = response.data.id;
        navigate(`/probability-output?jackpotId=${jackpotId}`);
      }
    } catch (error: any) {
      console.error('Error calculating from template:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to calculate probabilities',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [navigate, toast]);

  // Delete template
  const handleDeleteTemplate = useCallback(async (templateId: number) => {
    if (!confirm('Are you sure you want to delete this saved list?')) {
      return;
    }

    try {
      const response = await apiClient.deleteTemplate(templateId);
      if (response.success) {
        toast({
          title: 'Success',
          description: 'List deleted successfully',
        });
        loadTemplates();
      }
    } catch (error: any) {
      console.error('Error deleting template:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to delete list',
        variant: 'destructive',
      });
    }
  }, [toast, loadTemplates]);

  // Calculate validation summary
  const validationSummary = useMemo(() => {
    let validTeams = 0;
    let invalidTeams = 0;
    let validatingTeams = 0;
    let unvalidatedTeams = 0;

    fixtures.forEach(f => {
      if (f.homeTeam.trim().length >= 2) {
        if (f.homeTeamValidation?.isValidating) {
          validatingTeams++;
        } else if (f.homeTeamValidation?.isValid === true) {
          validTeams++;
        } else if (f.homeTeamValidation?.isValid === false) {
          invalidTeams++;
        } else {
          unvalidatedTeams++;
        }
      }
      if (f.awayTeam.trim().length >= 2) {
        if (f.awayTeamValidation?.isValidating) {
          validatingTeams++;
        } else if (f.awayTeamValidation?.isValid === true) {
          validTeams++;
        } else if (f.awayTeamValidation?.isValid === false) {
          invalidTeams++;
        } else {
          unvalidatedTeams++;
        }
      }
    });

    return { validTeams, invalidTeams, validatingTeams, unvalidatedTeams };
  }, [fixtures]);

  const isValid = fixtures.length > 0 && 
    fixtures.every(f => 
      f.homeTeam.trim() && 
      f.awayTeam.trim() && 
      f.homeOdds > 1 && 
      f.drawOdds > 1 && 
      f.awayOdds > 1
    );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 glow-primary">
            <Target className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold gradient-text">Jackpot Input</h1>
            <p className="text-sm text-muted-foreground">
              Enter fixtures and their corresponding decimal odds
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 animate-slide-in-right">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => setIsPDFDialogOpen(true)}
            className="glass-card border-accent/30 hover:bg-accent/10"
          >
            <FileText className="h-4 w-4 mr-2" />
            Import PDF
          </Button>
          <Dialog open={isBulkDialogOpen} onOpenChange={setIsBulkDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" className="glass-card border-primary/30 hover:bg-primary/10">
                <Upload className="h-4 w-4 mr-2" />
                Bulk Import
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl glass-card-elevated">
              <DialogHeader>
                <DialogTitle className="gradient-text">Bulk Import Fixtures</DialogTitle>
                <DialogDescription>
                  Paste fixtures in CSV or tab-separated format: HomeTeam, AwayTeam, HomeOdds, DrawOdds, AwayOdds
                </DialogDescription>
              </DialogHeader>
              <Textarea
                placeholder="Arsenal, Chelsea, 2.10, 3.40, 3.20
Liverpool, Man City, 2.80, 3.30, 2.45"
                value={bulkInput}
                onChange={(e) => setBulkInput(e.target.value)}
                className="min-h-[200px] font-mono text-sm bg-background/50"
              />
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsBulkDialogOpen(false)} className="glass-card">
                  Cancel
                </Button>
                <Button onClick={handleBulkImport} disabled={!bulkInput.trim()} className="btn-glow bg-primary text-primary-foreground">
                  Import
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Button onClick={addFixture} size="sm" className="btn-glow bg-primary text-primary-foreground">
            <Plus className="h-4 w-4 mr-2" />
            Add Fixture
          </Button>
        </div>
      </div>

      {validationErrors.length > 0 && (
        <Alert variant="destructive" className="animate-fade-in border-destructive/50 bg-destructive/10">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <ul className="list-disc list-inside space-y-1">
              {validationErrors.map((error, i) => (
                <li key={i}>{error}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Team Validation Summary */}
      {(validationSummary.validTeams > 0 || validationSummary.invalidTeams > 0 || validationSummary.validatingTeams > 0) && (
        <Alert className="animate-fade-in border-primary/20 bg-primary/5">
          <Target className="h-4 w-4 text-primary" />
          <AlertDescription className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-4 flex-wrap">
              {validationSummary.validTeams > 0 && (
                <div className="flex items-center gap-1">
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  <span className="text-sm">{validationSummary.validTeams} team{validationSummary.validTeams !== 1 ? 's' : ''} validated</span>
                </div>
              )}
              {validationSummary.invalidTeams > 0 && (
                <div className="flex items-center gap-1">
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                  <span className="text-sm">{validationSummary.invalidTeams} team{validationSummary.invalidTeams !== 1 ? 's' : ''} not found</span>
                </div>
              )}
              {validationSummary.validatingTeams > 0 && (
                <div className="flex items-center gap-1">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <span className="text-sm">Validating {validationSummary.validatingTeams} team{validationSummary.validatingTeams !== 1 ? 's' : ''}...</span>
                </div>
              )}
            </div>
            {(validationSummary.invalidTeams > 0 || validationSummary.unvalidatedTeams > 0) && (
              <Button
                variant="outline"
                size="sm"
                onClick={validateAllTeams}
                className="ml-auto"
              >
                <Target className="h-4 w-4 mr-2" />
                Validate All Teams
              </Button>
            )}
          </AlertDescription>
        </Alert>
      )}

      <Card className="glass-card animate-fade-in-up">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-accent" />
            Fixtures
          </CardTitle>
          <CardDescription>
            Enter team names and decimal odds for each fixture
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-border/50">
                  <TableHead className="w-[40px] text-muted-foreground">#</TableHead>
                  <TableHead className="text-muted-foreground">Home Team</TableHead>
                  <TableHead className="text-muted-foreground">Away Team</TableHead>
                  <TableHead className="w-[100px] text-right text-muted-foreground">Home</TableHead>
                  <TableHead className="w-[100px] text-right text-muted-foreground">Draw</TableHead>
                  <TableHead className="w-[100px] text-right text-muted-foreground">Away</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {fixtures.map((fixture, index) => (
                  <TableRow 
                    key={fixture.tempId} 
                    className="border-border/30 hover:bg-primary/5 transition-colors animate-fade-in"
                    style={{ animationDelay: `${0.05 * index}s` }}
                  >
                    <TableCell className="text-muted-foreground tabular-nums font-medium">
                      {index + 1}
                    </TableCell>
                    <TableCell>
                      <div className="relative">
                        <Input
                          value={fixture.homeTeam}
                          onChange={(e) => updateFixture(fixture.tempId, 'homeTeam', e.target.value)}
                          placeholder="Home team"
                          className={`h-9 bg-background/50 border-border/50 focus:border-primary pr-8 ${
                            fixture.homeTeamValidation?.isValid === true 
                              ? 'border-green-500/50' 
                              : fixture.homeTeamValidation?.isValid === false 
                              ? 'border-red-500/50' 
                              : ''
                          }`}
                        />
                        {fixture.homeTeamValidation?.isValidating && (
                          <Loader2 className="absolute right-2 top-2.5 h-4 w-4 animate-spin text-muted-foreground" />
                        )}
                        {fixture.homeTeamValidation?.isValid === true && !fixture.homeTeamValidation.isValidating && (
                          <CheckCircle2 className="absolute right-2 top-2.5 h-4 w-4 text-green-500" />
                        )}
                        {fixture.homeTeamValidation?.isValid === false && !fixture.homeTeamValidation.isValidating && (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <AlertTriangle className="absolute right-2 top-2.5 h-4 w-4 text-red-500 cursor-help" />
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                              <div className="space-y-1">
                                <p className="font-medium">Team not found in database</p>
                                {fixture.homeTeamValidation.suggestions && fixture.homeTeamValidation.suggestions.length > 0 && (
                                  <div>
                                    <p className="text-xs mb-1">Suggestions:</p>
                                    <ul className="text-xs list-disc list-inside">
                                      {fixture.homeTeamValidation.suggestions.slice(0, 3).map((suggestion, idx) => (
                                        <li key={idx}>{suggestion}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                <p className="text-xs text-muted-foreground mt-1">
                                  Using default team strengths (1.0, 1.0) - probabilities may be less accurate
                                </p>
                              </div>
                            </TooltipContent>
                          </Tooltip>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="relative">
                        <Input
                          value={fixture.awayTeam}
                          onChange={(e) => updateFixture(fixture.tempId, 'awayTeam', e.target.value)}
                          placeholder="Away team"
                          className={`h-9 bg-background/50 border-border/50 focus:border-primary pr-8 ${
                            fixture.awayTeamValidation?.isValid === true 
                              ? 'border-green-500/50' 
                              : fixture.awayTeamValidation?.isValid === false 
                              ? 'border-red-500/50' 
                              : ''
                          }`}
                        />
                        {fixture.awayTeamValidation?.isValidating && (
                          <Loader2 className="absolute right-2 top-2.5 h-4 w-4 animate-spin text-muted-foreground" />
                        )}
                        {fixture.awayTeamValidation?.isValid === true && !fixture.awayTeamValidation.isValidating && (
                          <CheckCircle2 className="absolute right-2 top-2.5 h-4 w-4 text-green-500" />
                        )}
                        {fixture.awayTeamValidation?.isValid === false && !fixture.awayTeamValidation.isValidating && (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <AlertTriangle className="absolute right-2 top-2.5 h-4 w-4 text-red-500 cursor-help" />
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                              <div className="space-y-1">
                                <p className="font-medium">Team not found in database</p>
                                {fixture.awayTeamValidation.suggestions && fixture.awayTeamValidation.suggestions.length > 0 && (
                                  <div>
                                    <p className="text-xs mb-1">Suggestions:</p>
                                    <ul className="text-xs list-disc list-inside">
                                      {fixture.awayTeamValidation.suggestions.slice(0, 3).map((suggestion, idx) => (
                                        <li key={idx}>{suggestion}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                <p className="text-xs text-muted-foreground mt-1">
                                  Using default team strengths (1.0, 1.0) - probabilities may be less accurate
                                </p>
                              </div>
                            </TooltipContent>
                          </Tooltip>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        step="0.01"
                        min="1.01"
                        value={fixture.homeOdds || ''}
                        onChange={(e) => updateFixture(fixture.tempId, 'homeOdds', parseOdds(e.target.value))}
                        placeholder="1.00"
                        className="h-9 text-right tabular-nums bg-background/50 border-border/50 focus:border-primary"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        step="0.01"
                        min="1.01"
                        value={fixture.drawOdds || ''}
                        onChange={(e) => updateFixture(fixture.tempId, 'drawOdds', parseOdds(e.target.value))}
                        placeholder="1.00"
                        className="h-9 text-right tabular-nums bg-background/50 border-border/50 focus:border-primary"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        step="0.01"
                        min="1.01"
                        value={fixture.awayOdds || ''}
                        onChange={(e) => updateFixture(fixture.tempId, 'awayOdds', parseOdds(e.target.value))}
                        placeholder="1.00"
                        className="h-9 text-right tabular-nums bg-background/50 border-border/50 focus:border-primary"
                      />
                    </TableCell>
                    <TableCell>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => removeFixture(fixture.tempId)}
                            disabled={fixtures.length === 1}
                            className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Remove fixture</TooltipContent>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-between items-center animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
        <Button
          onClick={() => setIsSaveDialogOpen(true)}
          disabled={!isValid}
          variant="outline"
          size="lg"
          className="glass-card border-primary/30 hover:bg-primary/10"
        >
          <Save className="mr-2 h-5 w-5" />
          Save List
        </Button>
        <Button 
          onClick={handleSubmit} 
          disabled={!isValid || isSubmitting} 
          size="lg" 
          className="btn-glow bg-primary text-primary-foreground"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Creating Jackpot...
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-5 w-5" />
              Calculate Probabilities
              <ArrowRight className="ml-2 h-5 w-5" />
            </>
          )}
        </Button>
      </div>

      {/* Saved Lists Section */}
      <Card className="glass-card border-primary/20 animate-fade-in-up" style={{ animationDelay: '0.4s' }}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FolderOpen className="h-5 w-5 text-primary" />
            Saved Lists
          </CardTitle>
          <CardDescription>
            Your saved fixture lists. Load them to edit or calculate probabilities directly.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loadingTemplates ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : savedTemplates.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FolderOpen className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No saved lists yet.</p>
              <p className="text-sm mt-2">Save your current list to reuse it later.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {savedTemplates.map((template) => (
                <Card key={template.id} className="glass-card border-border/50 hover:border-primary/30 transition-colors">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-semibold text-foreground">{template.name}</h3>
                          <Badge variant="outline" className="text-xs">
                            {template.fixtureCount} fixtures
                          </Badge>
                        </div>
                        {template.description && (
                          <p className="text-sm text-muted-foreground mb-2">{template.description}</p>
                        )}
                        <p className="text-xs text-muted-foreground">
                          Created: {new Date(template.createdAt).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        <Button
                          onClick={() => handleLoadTemplate(template.id)}
                          variant="outline"
                          size="sm"
                          className="glass-card"
                        >
                          <FolderOpen className="h-4 w-4 mr-2" />
                          Load
                        </Button>
                        <Button
                          onClick={() => handleCalculateFromTemplate(template.id)}
                          variant="default"
                          size="sm"
                          disabled={isSubmitting}
                          className="btn-glow"
                        >
                          <Sparkles className="h-4 w-4 mr-2" />
                          Calculate
                        </Button>
                        <Button
                          onClick={() => handleDeleteTemplate(template.id)}
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Save Dialog */}
      <Dialog open={isSaveDialogOpen} onOpenChange={setIsSaveDialogOpen}>
        <DialogContent className="glass-card-elevated max-w-md">
          <DialogHeader>
            <DialogTitle>Save Fixture List</DialogTitle>
            <DialogDescription>
              Save your current fixture list with a name and description for later use.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Name *</label>
              <Input
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                placeholder="e.g., Weekend Premier League Matches"
                className="bg-background/50"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Description (optional)</label>
              <Textarea
                value={saveDescription}
                onChange={(e) => setSaveDescription(e.target.value)}
                placeholder="Add a description for this list..."
                rows={3}
                className="bg-background/50"
              />
            </div>
            <div className="text-xs text-muted-foreground">
              {fixtures.length} fixture{fixtures.length !== 1 ? 's' : ''} will be saved
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsSaveDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveTemplate} disabled={!saveName.trim() || !isValid}>
              <Save className="h-4 w-4 mr-2" />
              Save List
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* PDF Import Dialog */}
      <PDFJackpotImport 
        open={isPDFDialogOpen} 
        onOpenChange={setIsPDFDialogOpen}
        onImport={handlePDFImport}
      />
    </div>
  );
}
