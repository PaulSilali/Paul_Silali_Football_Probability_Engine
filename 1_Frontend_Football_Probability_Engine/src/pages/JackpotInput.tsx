import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, Upload, AlertTriangle, ArrowRight, Sparkles, Target, FileText, Loader2, Save, FolderOpen, X, Calendar, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageLayout } from '@/components/layouts/PageLayout';
import { ModernCard } from '@/components/ui/modern-card';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
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
  teamId?: number;
  isTrained?: boolean;
  strengthSource?: 'model' | 'database' | 'default';
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
  
  // Pipeline state
  const [pipelineDialogOpen, setPipelineDialogOpen] = useState(false);
  const [pipelineStatus, setPipelineStatus] = useState<'idle' | 'checking' | 'running' | 'completed' | 'failed'>('idle');
  const [pipelineProgress, setPipelineProgress] = useState(0);
  const [pipelinePhase, setPipelinePhase] = useState('');
  const [pipelineSteps, setPipelineSteps] = useState<Record<string, any>>({});
  const [pipelineTaskId, setPipelineTaskId] = useState<string | null>(null);
  const [baseModelWindowYears, setBaseModelWindowYears] = useState<number>(4);  // Recent data focus: 2, 3, or 4 years

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
        const response = await apiClient.validateTeamName(teamName.trim(), undefined, true); // Check training status
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
                    confidence: response.data.confidence,
                    teamId: response.data.teamId,
                    isTrained: response.data.isTrained,
                    strengthSource: response.data.strengthSource
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

  // Poll pipeline status
  const pollPipelineStatus = useCallback((taskId: string): Promise<void> => {
    return new Promise((resolve) => {
      let pollInterval: NodeJS.Timeout | null = null;
      
      const poll = async () => {
        try {
          const response = await apiClient.getPipelineStatus(taskId);
          if (response.success && response.data) {
            const status = response.data.status;
            const progress = response.data.progress || 0;
            const phase = response.data.phase || '';
            const steps = response.data.steps || {};
            
            // Update state - React will re-render
            setPipelineStatus(status as 'idle' | 'checking' | 'running' | 'completed' | 'failed');
            setPipelineProgress(progress);
            setPipelinePhase(phase);
            setPipelineSteps(steps);
            
            if (status === 'completed' || status === 'failed') {
              if (pollInterval) {
                clearInterval(pollInterval);
                pollInterval = null;
              }
              
              // Ensure final state is set
              if (status === 'completed') {
                setPipelineStatus('completed');
                setPipelineProgress(100);
                setPipelinePhase('Pipeline completed successfully!');
              } else {
                setPipelineStatus('failed');
                toast({
                  title: 'Pipeline Failed',
                  description: response.data.error || 'Pipeline execution failed',
                  variant: 'destructive',
                });
              }
              
              // Wait a bit to show final state before resolving
              setTimeout(() => {
                resolve();
              }, 500);
            }
          }
        } catch (error) {
          console.error('Error polling pipeline status:', error);
          if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
          }
          resolve();
        }
      };
      
      // Start polling immediately, then every 2 seconds
      poll();
      pollInterval = setInterval(poll, 2000);
      
      // Timeout after 5 minutes
      setTimeout(() => {
        if (pollInterval) {
          clearInterval(pollInterval);
          pollInterval = null;
        }
        resolve();
      }, 300000);
    });
  }, [toast]);

  const handleSubmit = useCallback(async () => {
    if (!validateFixtures()) {
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      // Step 1: Check team status
      const allTeamNames = fixtures.flatMap(f => [
        f.homeTeam.trim(),
        f.awayTeam.trim()
      ]).filter(name => name.length >= 2);
      
      setPipelineDialogOpen(true);
      setPipelineStatus('checking');
      setPipelineProgress(0);
      setPipelinePhase('Checking team validation and training status...');
      
      const statusResponse = await apiClient.checkTeamsStatus(allTeamNames);
      
      // Step 2: Create jackpot FIRST (so we have jackpot_id for pipeline metadata)
      setPipelinePhase('Creating jackpot...');
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
      
      const response = await apiClient.createJackpot(apiFixtures);
      
      if (!response.success || !response.data) {
        throw new Error(response.message || "Failed to create jackpot");
      }
      
      const jackpotId = response.data.id;
      
      if (statusResponse.success && statusResponse.data) {
        const status = statusResponse.data;
        const needsPipeline = status.missing_teams.length > 0 || status.untrained_teams.length > 0;
        
        if (needsPipeline) {
          // Step 3: Run pipeline WITH jackpot_id (so metadata can be saved)
          setPipelineStatus('running');
          setPipelineProgress(20);
          setPipelinePhase('Running automated pipeline...');
          
          const pipelineResponse = await apiClient.runPipeline({
            team_names: allTeamNames,
            league_id: status.team_details[Object.keys(status.team_details)[0]]?.league_id,
            auto_download: true,
            auto_train: true,
            auto_recompute: false,
            jackpot_id: jackpotId, // Pass jackpot_id so metadata can be saved
            max_seasons: 7,
            base_model_window_years: baseModelWindowYears  // Recent data focus configuration
          });
          
          if (pipelineResponse.success && pipelineResponse.data) {
            const taskId = pipelineResponse.data.taskId;
            setPipelineTaskId(taskId);
            
            // Poll for status and wait for completion
            await pollPipelineStatus(taskId);
            
            // Get final status and steps after polling completes
            const finalStatusResponse = await apiClient.getPipelineStatus(taskId);
            if (finalStatusResponse.success && finalStatusResponse.data) {
              const finalStatus = finalStatusResponse.data.status;
              const finalProgress = finalStatusResponse.data.progress || 100;
              const finalPhase = finalStatusResponse.data.phase || 'Complete';
              const finalSteps = finalStatusResponse.data.steps || {};
              
              // Update to final state
              setPipelineStatus(finalStatus as 'idle' | 'checking' | 'running' | 'completed' | 'failed');
              setPipelineProgress(finalProgress);
              setPipelinePhase(finalPhase);
              setPipelineSteps(finalSteps);
              
              if (finalStatus === 'failed') {
                const continueAnyway = confirm(
                  'Pipeline encountered errors. Do you want to continue with probability calculation anyway?'
                );
                if (!continueAnyway) {
                  setIsSubmitting(false);
                  return;
                }
              }
            }
          }
        } else {
          setPipelineProgress(100);
          setPipelinePhase('All teams validated and trained!');
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
      
      // Update final state
      setPipelineStatus('completed');
      setPipelineProgress(100);
      setPipelinePhase('Jackpot created successfully!');
      
      // Wait a moment to show completed state before navigating
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      toast({
        title: "Jackpot created",
        description: "Calculating probabilities...",
      });
      
      // Close dialog and navigate
      setPipelineDialogOpen(false);
      navigate(`/probability-output?jackpotId=${jackpotId}`);
    } catch (error: any) {
      console.error("Error creating jackpot:", error);
      setPipelineStatus('failed');
      toast({
        title: "Error",
        description: error.message || "Failed to create jackpot. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [fixtures, validateFixtures, navigate, toast, pollPipelineStatus, pipelineStatus]);

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
    let trainedTeams = 0;
    let untrainedTeams = 0;

    fixtures.forEach(f => {
      if (f.homeTeam.trim().length >= 2) {
        if (f.homeTeamValidation?.isValidating) {
          validatingTeams++;
        } else if (f.homeTeamValidation?.isValid === true) {
          validTeams++;
          if (f.homeTeamValidation.isTrained === true) {
            trainedTeams++;
          } else if (f.homeTeamValidation.isTrained === false) {
            untrainedTeams++;
          }
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
          if (f.awayTeamValidation.isTrained === true) {
            trainedTeams++;
          } else if (f.awayTeamValidation.isTrained === false) {
            untrainedTeams++;
          }
        } else if (f.awayTeamValidation?.isValid === false) {
          invalidTeams++;
        } else {
          unvalidatedTeams++;
        }
      }
    });

    return { validTeams, invalidTeams, validatingTeams, unvalidatedTeams, trainedTeams, untrainedTeams };
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
    <PageLayout
      title="Jackpot Input"
      description="Enter fixtures and their corresponding decimal odds"
      icon={<Target className="h-6 w-6" />}
      action={
        <div className="flex items-center gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => setIsPDFDialogOpen(true)}
            className="btn-glow"
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
      }
    >

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
      {(validationSummary.validTeams > 0 || validationSummary.invalidTeams > 0 || validationSummary.validatingTeams > 0 || validationSummary.untrainedTeams > 0) && (
        <Alert className="animate-fade-in border-primary/20 bg-primary/5">
          <Target className="h-4 w-4 text-primary" />
          <AlertDescription className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-4 flex-wrap">
              {validationSummary.validTeams > 0 && (
                <div className="flex items-center gap-1">
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  <span className="text-sm font-medium">{validationSummary.validTeams} validated</span>
                </div>
              )}
              {validationSummary.trainedTeams > 0 && (
                <div className="flex items-center gap-1">
                  <Sparkles className="h-4 w-4 text-blue-500" />
                  <span className="text-sm font-medium">{validationSummary.trainedTeams} trained</span>
                </div>
              )}
              {validationSummary.untrainedTeams > 0 && (
                <div className="flex items-center gap-1">
                  <AlertTriangle className="h-4 w-4 text-yellow-500" />
                  <span className="text-sm font-medium">{validationSummary.untrainedTeams} need training</span>
                </div>
              )}
              {validationSummary.invalidTeams > 0 && (
                <div className="flex items-center gap-1">
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                  <span className="text-sm font-medium">{validationSummary.invalidTeams} not found</span>
                </div>
              )}
              {validationSummary.validatingTeams > 0 && (
                <div className="flex items-center gap-1">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span className="text-sm font-medium">{validationSummary.validatingTeams} validating...</span>
                </div>
              )}
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Pipeline Status Dialog */}
      {pipelineDialogOpen && (
        <Dialog open={pipelineDialogOpen} onOpenChange={setPipelineDialogOpen}>
          <DialogContent className="max-w-2xl glass-card-elevated">
            <DialogHeader>
              <DialogTitle className="gradient-text">Preparing Data Pipeline</DialogTitle>
              <DialogDescription>
                {pipelineStatus === 'running' 
                  ? 'Downloading missing data and retraining model...'
                  : pipelineStatus === 'completed'
                  ? 'Pipeline completed successfully!'
                  : 'Checking team status...'}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Progress</span>
                  <span className="font-medium">{pipelineProgress}%</span>
                </div>
                <div className="h-2 bg-background/50 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${pipelineProgress}%` }}
                  />
                </div>
              </div>
              <div className="text-sm text-muted-foreground">
                <p className="font-medium mb-2">Current Step:</p>
                <p>{pipelinePhase}</p>
              </div>
              {pipelineSteps && Object.keys(pipelineSteps).length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Pipeline Steps:</p>
                  <div className="space-y-1 text-xs">
                    {Object.entries(pipelineSteps).map(([step, data]: [string, any]) => (
                      <div key={step} className="flex items-center gap-2">
                        {data.success !== undefined ? (
                          data.success ? (
                            <CheckCircle2 className="h-3 w-3 text-green-500" />
                          ) : (
                            <AlertTriangle className="h-3 w-3 text-red-500" />
                          )
                        ) : data.skipped ? (
                          <X className="h-3 w-3 text-gray-500" />
                        ) : (
                          <Loader2 className="h-3 w-3 animate-spin text-primary" />
                        )}
                        <span className="capitalize">{step.replace(/_/g, ' ')}</span>
                        {data.error && (
                          <span className="text-red-500 text-xs">({data.error})</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            {pipelineStatus === 'completed' && pipelineSteps && (
              <div className="space-y-3 border-t pt-4">
                <p className="text-sm font-semibold">Pipeline Summary:</p>
                <div className="space-y-2 text-xs">
                  {pipelineSteps.create_teams?.created?.length > 0 && (
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-3 w-3 text-green-500" />
                      <span><strong>{pipelineSteps.create_teams.created.length}</strong> teams created</span>
                    </div>
                  )}
                  {pipelineSteps.download_data && !pipelineSteps.download_data.skipped && (
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-3 w-3 text-green-500" />
                      <span>
                        <strong>Data downloaded:</strong> {pipelineSteps.download_data.total_matches || 0} matches
                        {pipelineSteps.download_data.leagues_downloaded?.length > 0 && (
                          <span className="text-muted-foreground ml-1">
                            ({pipelineSteps.download_data.leagues_downloaded.map((l: any) => l.league_code).join(', ')})
                          </span>
                        )}
                      </span>
                    </div>
                  )}
                  {pipelineSteps.train_model?.success && (
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-3 w-3 text-green-500" />
                      <span>
                        <strong>Model trained:</strong> Version {pipelineSteps.train_model.version || 'N/A'}
                      </span>
                    </div>
                  )}
                  {pipelineSteps.train_model?.success && (
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-3 w-3 text-blue-500" />
                      <span className="text-green-600 font-medium">
                        ✓ Probabilities calculated using newly trained model data
                      </span>
                    </div>
                  )}
                  {pipelineSteps.download_data?.errors?.length > 0 && (
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="h-3 w-3 text-yellow-500 mt-0.5" />
                      <div>
                        <span className="text-yellow-600 font-medium">Download warnings:</span>
                        <ul className="list-disc list-inside ml-2 text-muted-foreground">
                          {pipelineSteps.download_data.errors.slice(0, 3).map((err: string, idx: number) => (
                            <li key={idx}>{err}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            <DialogFooter>
              {pipelineStatus === 'completed' && (
                <Button 
                  onClick={() => {
                    setPipelineDialogOpen(false);
                    // Navigation will happen automatically after delay
                  }} 
                  className="btn-glow"
                  disabled={isSubmitting}
                >
                  Continue
                </Button>
              )}
              {pipelineStatus === 'failed' && (
                <Button 
                  onClick={() => {
                    setPipelineDialogOpen(false);
                    setIsSubmitting(false);
                  }} 
                  variant="destructive"
                >
                  Close
                </Button>
              )}
              {(pipelineStatus === 'checking' || pipelineStatus === 'running') && (
                <div className="text-sm text-muted-foreground">
                  Please wait...
                </div>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>
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

      {/* Model Training Configuration */}
      <Card className="glass-card border-primary/20 animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Target className="h-5 w-5 text-primary" />
            Model Training Configuration
          </CardTitle>
          <CardDescription>
            Configure how the model uses historical data for training
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex-1 min-w-[250px]">
              <Label htmlFor="recent-data-window" className="text-sm font-medium mb-2 block">
                Recent Data Focus
              </Label>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-2">
                    <Select
                      value={baseModelWindowYears.toString()}
                      onValueChange={(value) => setBaseModelWindowYears(parseFloat(value))}
                    >
                      <SelectTrigger id="recent-data-window" className="w-full bg-background/50">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="2">
                          2 Years (Most Recent)
                        </SelectItem>
                        <SelectItem value="3">
                          3 Years (Recent Focus)
                        </SelectItem>
                        <SelectItem value="4">
                          4 Years (Default - Balanced)
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p className="font-semibold mb-1">Recent Data Focus</p>
                  <p className="text-xs">
                    Controls how many years of historical data the model uses for training.
                    <br /><br />
                    <strong>2 Years:</strong> Most recent data only (+3-5% accuracy, faster training)
                    <br />
                    <strong>3 Years:</strong> Recent focus (+2-4% accuracy)
                    <br />
                    <strong>4 Years:</strong> Default balanced approach (most stable)
                  </p>
                </TooltipContent>
              </Tooltip>
              <p className="text-xs text-muted-foreground mt-2">
                Model will train on last {baseModelWindowYears} {baseModelWindowYears === 1 ? 'year' : 'years'} of data
                {baseModelWindowYears < 4 && ' (recent data focus enabled)'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-between items-center animate-fade-in-up" style={{ animationDelay: '0.35s' }}>
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
    </PageLayout>
  );
}
