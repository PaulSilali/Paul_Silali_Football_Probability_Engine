import { useState } from 'react';
import { Globe, ClipboardPaste, X, Check, AlertCircle, Loader2, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import type { ParsedResult } from '@/components/PDFResultsImport';

interface WebScrapingImportProps {
  onResultsImported: (results: ParsedResult[]) => void;
}

type SourceType = 'betika' | 'sportpesa';

// Parse Betika HTML content
function parseBetikaHTML(html: string): ParsedResult[] {
  const results: ParsedResult[] = [];
  
  // Pattern for Betika results: looks for match data in their HTML structure
  // Common patterns: team names, scores in format "X - Y" or "X:Y"
  const matchPatterns = [
    // Pattern: "Team1 X - Y Team2" or similar
    /([A-Za-z\s\.\-]+)\s+(\d+)\s*[-–:]\s*(\d+)\s+([A-Za-z\s\.\-]+)/g,
    // Pattern for table rows with team and score data
    /<td[^>]*>([^<]+)<\/td>\s*<td[^>]*>(\d+)\s*[-–:]\s*(\d+)<\/td>\s*<td[^>]*>([^<]+)<\/td>/gi,
  ];

  let matchId = 1;
  
  // Try to extract text content first
  const textContent = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  
  // Look for score patterns
  const scoreRegex = /([A-Za-z][A-Za-z\s\.\-']+?)\s+(\d+)\s*[-–:]\s*(\d+)\s+([A-Za-z][A-Za-z\s\.\-']+)/g;
  let match;
  
  while ((match = scoreRegex.exec(textContent)) !== null) {
    const homeTeam = match[1].trim();
    const homeScore = parseInt(match[2]);
    const awayScore = parseInt(match[3]);
    const awayTeam = match[4].trim();
    
    // Skip if team names are too short or look like numbers
    if (homeTeam.length < 3 || awayTeam.length < 3) continue;
    if (/^\d+$/.test(homeTeam) || /^\d+$/.test(awayTeam)) continue;
    
    let result: 'H' | 'D' | 'A';
    if (homeScore > awayScore) result = 'H';
    else if (homeScore < awayScore) result = 'A';
    else result = 'D';
    
    results.push({
      id: String(matchId++),
      homeTeam,
      awayTeam,
      homeScore,
      awayScore,
      result,
    });
  }
  
  return results;
}

// Parse SportPesa HTML content
function parseSportPesaHTML(html: string): ParsedResult[] {
  const results: ParsedResult[] = [];
  
  // Extract text content
  const textContent = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  
  let matchId = 1;
  
  // SportPesa often has patterns like "1. Team1 vs Team2 1-0" or "Team1 1 - 0 Team2"
  const patterns = [
    /(\d+)\.\s*([A-Za-z][A-Za-z\s\.\-']+?)\s+(?:vs\.?\s+)?([A-Za-z][A-Za-z\s\.\-']+?)\s+(\d+)\s*[-–:]\s*(\d+)/gi,
    /([A-Za-z][A-Za-z\s\.\-']+?)\s+(\d+)\s*[-–:]\s*(\d+)\s+([A-Za-z][A-Za-z\s\.\-']+)/g,
  ];
  
  for (const pattern of patterns) {
    let match;
    const regex = new RegExp(pattern.source, pattern.flags);
    
    while ((match = regex.exec(textContent)) !== null) {
      let homeTeam: string, awayTeam: string, homeScore: number, awayScore: number;
      
      if (match.length === 6) {
        // Pattern with match number
        homeTeam = match[2].trim();
        awayTeam = match[3].trim();
        homeScore = parseInt(match[4]);
        awayScore = parseInt(match[5]);
      } else {
        // Pattern without match number
        homeTeam = match[1].trim();
        homeScore = parseInt(match[2]);
        awayScore = parseInt(match[3]);
        awayTeam = match[4].trim();
      }
      
      // Skip if team names are too short
      if (homeTeam.length < 3 || awayTeam.length < 3) continue;
      if (/^\d+$/.test(homeTeam) || /^\d+$/.test(awayTeam)) continue;
      
      // Check for duplicates
      const isDuplicate = results.some(
        r => r.homeTeam === homeTeam && r.awayTeam === awayTeam
      );
      if (isDuplicate) continue;
      
      let result: 'H' | 'D' | 'A';
      if (homeScore > awayScore) result = 'H';
      else if (homeScore < awayScore) result = 'A';
      else result = 'D';
      
      results.push({
        id: String(matchId++),
        homeTeam,
        awayTeam,
        homeScore,
        awayScore,
        result,
      });
    }
    
    if (results.length > 0) break; // Use first pattern that works
  }
  
  return results;
}

export function WebScrapingImport({ onResultsImported }: WebScrapingImportProps) {
  const [sourceType, setSourceType] = useState<SourceType>('betika');
  const [htmlContent, setHtmlContent] = useState('');
  const [isParsing, setIsParsing] = useState(false);
  const [parsedResults, setParsedResults] = useState<ParsedResult[]>([]);

  const handleParse = async () => {
    if (!htmlContent.trim()) {
      toast.error('Please paste the page source first');
      return;
    }
    
    setIsParsing(true);
    
    // Small delay for UX
    await new Promise(resolve => setTimeout(resolve, 500));
    
    try {
      const results = sourceType === 'betika' 
        ? parseBetikaHTML(htmlContent)
        : parseSportPesaHTML(htmlContent);
      
      if (results.length === 0) {
        toast.warning('No match results found. Make sure you copied the full page source.');
        setParsedResults([]);
      } else {
        toast.success(`Found ${results.length} match results`);
        setParsedResults(results);
      }
    } catch (error) {
      toast.error('Failed to parse HTML content');
      setParsedResults([]);
    } finally {
      setIsParsing(false);
    }
  };

  const handleConfirmImport = () => {
    if (parsedResults.length > 0) {
      onResultsImported(parsedResults);
      toast.success(`Imported ${parsedResults.length} match results for backtesting`);
    }
  };

  const clearAll = () => {
    setHtmlContent('');
    setParsedResults([]);
  };

  const getResultBadge = (result: 'H' | 'D' | 'A') => {
    switch (result) {
      case 'H':
        return <Badge className="bg-green-500/10 text-green-600 border-green-500/20">Home</Badge>;
      case 'D':
        return <Badge className="bg-yellow-500/10 text-yellow-600 border-yellow-500/20">Draw</Badge>;
      case 'A':
        return <Badge className="bg-blue-500/10 text-blue-600 border-blue-500/20">Away</Badge>;
    }
  };

  const sourceUrls = {
    betika: 'https://www.betika.com/lite/en-ke/jackpots/result',
    sportpesa: 'https://www.ke.sportpesa.com/en/mega-jackpot-pro/results',
  };

  return (
    <Card className="glass-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Globe className="h-5 w-5 text-primary" />
          Web Import (Paste HTML)
        </CardTitle>
        <CardDescription>
          Copy page source from Betika or SportPesa results page and paste below
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Source Selection */}
        <Tabs value={sourceType} onValueChange={(v) => setSourceType(v as SourceType)}>
          <TabsList className="w-full">
            <TabsTrigger value="betika" className="flex-1">Betika</TabsTrigger>
            <TabsTrigger value="sportpesa" className="flex-1">SportPesa</TabsTrigger>
          </TabsList>
        </Tabs>

        {/* Instructions */}
        <div className="p-3 rounded-lg bg-muted/30 border border-border space-y-2">
          <p className="text-sm font-medium">How to get page source:</p>
          <ol className="text-xs text-muted-foreground list-decimal list-inside space-y-1">
            <li>
              Open the results page:{' '}
              <a 
                href={sourceUrls[sourceType]} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-primary hover:underline inline-flex items-center gap-1"
              >
                {sourceType === 'betika' ? 'Betika Jackpot Results' : 'SportPesa Mega Jackpot Results'}
                <ExternalLink className="h-3 w-3" />
              </a>
            </li>
            <li>Right-click anywhere on the page and select "View Page Source" (or press Ctrl+U)</li>
            <li>Select all (Ctrl+A) and copy (Ctrl+C)</li>
            <li>Paste the HTML below</li>
          </ol>
        </div>

        {/* HTML Input */}
        {parsedResults.length === 0 && (
          <div className="space-y-3">
            <Textarea
              placeholder="Paste the page source HTML here..."
              value={htmlContent}
              onChange={(e) => setHtmlContent(e.target.value)}
              className="min-h-[200px] font-mono text-xs"
            />
            
            <div className="flex gap-2">
              <Button 
                onClick={handleParse}
                disabled={!htmlContent.trim() || isParsing}
                className="flex-1"
              >
                {isParsing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Parsing...
                  </>
                ) : (
                  <>
                    <ClipboardPaste className="h-4 w-4 mr-2" />
                    Parse Results
                  </>
                )}
              </Button>
              {htmlContent && (
                <Button variant="outline" onClick={clearAll}>
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        )}

        {/* Parsed Results Preview */}
        {parsedResults.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Check className="h-4 w-4 text-green-500" />
                <span className="text-sm font-medium">
                  {parsedResults.length} matches found from {sourceType === 'betika' ? 'Betika' : 'SportPesa'}
                </span>
              </div>
              <Button variant="ghost" size="sm" onClick={clearAll}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            
            <ScrollArea className="h-[250px] rounded-lg border border-border">
              <div className="p-3 space-y-2">
                {parsedResults.map((result, idx) => (
                  <div 
                    key={result.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-muted-foreground w-6">{idx + 1}</span>
                      <div>
                        <p className="text-sm font-medium">
                          {result.homeTeam} vs {result.awayTeam}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Score: {result.homeScore} - {result.awayScore}
                        </p>
                      </div>
                    </div>
                    {getResultBadge(result.result)}
                  </div>
                ))}
              </div>
            </ScrollArea>

            <Button 
              onClick={handleConfirmImport} 
              className="w-full btn-glow"
            >
              <Check className="h-4 w-4 mr-2" />
              Use for Backtesting
            </Button>
          </div>
        )}

        {/* Info Box */}
        <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 border border-border">
          <AlertCircle className="h-4 w-4 text-muted-foreground mt-0.5" />
          <div className="text-xs text-muted-foreground">
            <p className="font-medium mb-1">Note:</p>
            <p>This method parses the raw HTML from the results page. The parsing may not capture all data depending on the page structure. If results aren't found, try the PDF import or manual entry options.</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
