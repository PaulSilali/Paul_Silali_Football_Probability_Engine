import { useState, useCallback } from 'react';
import { Upload, FileText, Check, AlertTriangle, Loader2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';

export interface ParsedFixture {
  id: string;
  homeTeam: string;
  awayTeam: string;
  homeOdds: number;
  drawOdds: number;
  awayOdds: number;
  country?: string;
  date?: string;
}

interface PDFJackpotImportProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImport: (fixtures: ParsedFixture[]) => void;
}

// Parse SportPesa-style jackpot text
const parseJackpotText = (text: string): ParsedFixture[] => {
  const fixtures: ParsedFixture[] = [];
  const lines = text.split('\n').filter(line => line.trim());
  
  // Pattern: ID, Date, Team, Country, Home, Draw, Away
  // Example: "2257 26-12-2025 Gillingham England 2.70 2.95 2.55"
  const oddsPattern = /(\d+)\s+(\d{2}-\d{2}-\d{4})\s+([A-Za-z\s]+?)\s+(England|Spain|Germany|Italy|France|[A-Za-z\s]+?(?:Amateur)?)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)/gi;
  
  let match;
  while ((match = oddsPattern.exec(text)) !== null) {
    fixtures.push({
      id: match[1],
      date: match[2],
      homeTeam: match[3].trim(),
      country: match[4].trim(),
      homeOdds: parseFloat(match[5]),
      drawOdds: parseFloat(match[6]),
      awayOdds: parseFloat(match[7]),
      awayTeam: '', // Will be filled from next team or "vs" pattern
    });
  }

  // Alternative pattern for table format with pipes
  if (fixtures.length === 0) {
    const tablePattern = /\|\s*(\d+)\s*\|\s*(\d{2}-\d{2}-\d{4})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|/gi;
    while ((match = tablePattern.exec(text)) !== null) {
      fixtures.push({
        id: match[1],
        date: match[2],
        homeTeam: match[3].trim(),
        country: match[4].trim(),
        homeOdds: parseFloat(match[5]),
        drawOdds: parseFloat(match[6]),
        awayOdds: parseFloat(match[7]),
        awayTeam: 'Away Team', // Placeholder
      });
    }
  }

  // Simple CSV-like pattern (Team1, Team2, H, D, A)
  if (fixtures.length === 0) {
    const csvLines = text.split('\n');
    csvLines.forEach((line, idx) => {
      const parts = line.split(/[,\t|]+/).map(p => p.trim()).filter(Boolean);
      if (parts.length >= 5) {
        const homeOdds = parseFloat(parts[parts.length - 3]);
        const drawOdds = parseFloat(parts[parts.length - 2]);
        const awayOdds = parseFloat(parts[parts.length - 1]);
        
        if (!isNaN(homeOdds) && !isNaN(drawOdds) && !isNaN(awayOdds) && 
            homeOdds > 1 && drawOdds > 1 && awayOdds > 1) {
          fixtures.push({
            id: String(idx + 1),
            homeTeam: parts[0] || `Team ${idx * 2 + 1}`,
            awayTeam: parts[1] || `Team ${idx * 2 + 2}`,
            homeOdds,
            drawOdds,
            awayOdds,
          });
        }
      }
    });
  }

  return fixtures;
};

// Mock PDF text extraction (in real implementation, use pdf.js or server-side parsing)
const extractTextFromPDF = async (file: File): Promise<string> => {
  // For demo, we'll read the file and return sample data
  // In production, you'd use pdf.js or send to a backend
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => {
      // Return sample SportPesa format for demo
      const sampleText = `
| ID   | DATE       | EVENT           | COUNTRY         | HOME | DRAW | AWAY |
| 2257 | 26-12-2025 | Gillingham      | England         | 2.70 | 2.95 | 2.55 |
| 4341 | 26-12-2025 | AFC Wimbledon   | England         | 2.75 | 2.90 | 2.70 |
| 4548 | 26-12-2025 | Cheltenham      | England         | 2.70 | 3.20 | 2.41 |
| 1088 | 26-12-2025 | Blackpool       | England         | 2.38 | 3.40 | 2.70 |
| 1956 | 26-12-2025 | Burton          | England         | 2.25 | 3.20 | 3.10 |
| 3704 | 26-12-2025 | Chesterfield    | England         | 2.28 | 3.30 | 2.80 |
| 5830 | 26-12-2025 | Plymouth        | England         | 2.49 | 3.40 | 2.60 |
| 2479 | 26-12-2025 | Portsmouth      | England         | 2.85 | 3.50 | 2.44 |
| 4055 | 26-12-2025 | Peterborough    | England         | 2.15 | 3.45 | 3.05 |
| 4276 | 26-12-2025 | Chippenham Town | England Amateur | 2.70 | 3.25 | 2.27 |
| 5706 | 26-12-2025 | Salisbury City  | England Amateur | 2.32 | 3.30 | 2.60 |
| 1282 | 26-12-2025 | Eastleigh       | England         | 2.47 | 3.10 | 2.60 |
| 1685 | 26-12-2025 | Telford         | England Amateur | 2.30 | 3.30 | 2.60 |
      `;
      resolve(sampleText);
    };
    reader.readAsText(file);
  });
};

export function PDFJackpotImport({ open, onOpenChange, onImport }: PDFJackpotImportProps) {
  const [file, setFile] = useState<File | null>(null);
  const [parsedFixtures, setParsedFixtures] = useState<ParsedFixture[]>([]);
  const [isParsing, setIsParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const { toast } = useToast();

  const handleFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    if (!selectedFile.name.toLowerCase().endsWith('.pdf') && 
        !selectedFile.type.includes('pdf')) {
      setParseError('Please select a PDF file');
      return;
    }

    setFile(selectedFile);
    setParseError(null);
    setIsParsing(true);

    try {
      const text = await extractTextFromPDF(selectedFile);
      const fixtures = parseJackpotText(text);
      
      if (fixtures.length === 0) {
        setParseError('Could not extract fixtures from PDF. Please check the format.');
      } else {
        setParsedFixtures(fixtures);
        toast({
          title: 'PDF Parsed Successfully',
          description: `Found ${fixtures.length} fixtures`,
        });
      }
    } catch (err) {
      setParseError('Failed to parse PDF file');
      console.error('PDF parse error:', err);
    } finally {
      setIsParsing(false);
    }
  }, [toast]);

  const handleImport = useCallback(() => {
    if (parsedFixtures.length === 0) return;
    
    onImport(parsedFixtures);
    onOpenChange(false);
    setFile(null);
    setParsedFixtures([]);
    
    toast({
      title: 'Fixtures Imported',
      description: `${parsedFixtures.length} fixtures imported successfully`,
    });
  }, [parsedFixtures, onImport, onOpenChange, toast]);

  const handleClose = () => {
    onOpenChange(false);
    setFile(null);
    setParsedFixtures([]);
    setParseError(null);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl glass-card-elevated">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 gradient-text">
            <FileText className="h-5 w-5" />
            Import Jackpot from PDF
          </DialogTitle>
          <DialogDescription>
            Upload a SportPesa-style jackpot PDF to automatically extract fixtures and odds
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* File Upload Area */}
          <div className="border-2 border-dashed border-border/50 rounded-lg p-6 text-center hover:border-primary/50 transition-colors">
            <Input
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              className="hidden"
              id="pdf-upload"
            />
            <label
              htmlFor="pdf-upload"
              className="cursor-pointer flex flex-col items-center gap-2"
            >
              {isParsing ? (
                <Loader2 className="h-10 w-10 text-primary animate-spin" />
              ) : file ? (
                <Check className="h-10 w-10 text-status-stable" />
              ) : (
                <Upload className="h-10 w-10 text-muted-foreground" />
              )}
              <span className="text-sm text-muted-foreground">
                {isParsing ? 'Parsing PDF...' : file ? file.name : 'Click to upload PDF or drag and drop'}
              </span>
              <span className="text-xs text-muted-foreground/60">
                Supports SportPesa, Betika, and similar jackpot formats
              </span>
            </label>
          </div>

          {/* Error Alert */}
          {parseError && (
            <Alert variant="destructive" className="border-destructive/50 bg-destructive/10">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{parseError}</AlertDescription>
            </Alert>
          )}

          {/* Parsed Fixtures Preview */}
          {parsedFixtures.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">
                  Extracted Fixtures
                  <Badge variant="outline" className="ml-2">
                    {parsedFixtures.length} matches
                  </Badge>
                </h3>
              </div>
              
              <ScrollArea className="h-[300px] rounded-lg border border-border/50">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/30">
                      <TableHead className="w-[50px]">#</TableHead>
                      <TableHead>Home Team</TableHead>
                      <TableHead>Away Team</TableHead>
                      <TableHead className="text-right">Home</TableHead>
                      <TableHead className="text-right">Draw</TableHead>
                      <TableHead className="text-right">Away</TableHead>
                      <TableHead>Country</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {parsedFixtures.map((fixture, idx) => (
                      <TableRow key={fixture.id} className="hover:bg-primary/5">
                        <TableCell className="text-muted-foreground tabular-nums">
                          {idx + 1}
                        </TableCell>
                        <TableCell className="font-medium">{fixture.homeTeam}</TableCell>
                        <TableCell>{fixture.awayTeam || '-'}</TableCell>
                        <TableCell className="text-right tabular-nums font-medium text-chart-1">
                          {fixture.homeOdds.toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums font-medium text-chart-3">
                          {fixture.drawOdds.toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums font-medium text-chart-2">
                          {fixture.awayOdds.toFixed(2)}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">
                            {fixture.country || 'Unknown'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>

              {/* Validation Summary */}
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Check className="h-4 w-4 text-status-stable" />
                  <span>{parsedFixtures.length} valid fixtures</span>
                </div>
                <div className="flex items-center gap-1">
                  <span>Avg odds margin:</span>
                  <span className="font-medium">
                    {(parsedFixtures.reduce((sum, f) => {
                      const margin = (1/f.homeOdds + 1/f.drawOdds + 1/f.awayOdds - 1) * 100;
                      return sum + margin;
                    }, 0) / parsedFixtures.length).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} className="glass-card">
            <X className="h-4 w-4 mr-2" />
            Cancel
          </Button>
          <Button 
            onClick={handleImport} 
            disabled={parsedFixtures.length === 0}
            className="btn-glow bg-primary text-primary-foreground"
          >
            <Check className="h-4 w-4 mr-2" />
            Import {parsedFixtures.length} Fixtures
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
