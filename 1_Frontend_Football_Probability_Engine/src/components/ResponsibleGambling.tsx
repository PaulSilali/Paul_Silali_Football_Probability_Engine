import { useState } from 'react';
import { Shield, Clock, AlertCircle, ExternalLink, HelpCircle, Settings, Phone } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { toast } from '@/hooks/use-toast';

export function ResponsibleGambling() {
  const [weeklyLimit, setWeeklyLimit] = useState<number | ''>('');
  const [cooldownEnabled, setCooldownEnabled] = useState(false);
  const [cooldownMinutes, setCooldownMinutes] = useState(5);
  const [lossAlertEnabled, setLossAlertEnabled] = useState(true);
  const [consecutiveLossLimit, setConsecutiveLossLimit] = useState(3);

  const handleSaveLimits = () => {
    toast({
      title: "Limits Updated",
      description: "Your responsible gambling settings have been saved.",
    });
  };

  return (
    <div className="space-y-6">
      {/* Main Disclaimer */}
      <Alert className="border-status-watch/50 bg-status-watch/10">
        <Shield className="h-5 w-5 text-status-watch" />
        <AlertTitle className="text-status-watch">Important Information</AlertTitle>
        <AlertDescription className="mt-2 space-y-2">
          <p>
            This system provides <strong>probability estimates</strong>, not predictions or guarantees. 
            Past performance does not predict future results.
          </p>
          <p className="text-sm text-muted-foreground">
            Please gamble responsibly. If gambling is affecting your life, seek help.
          </p>
        </AlertDescription>
      </Alert>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                <Clock className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Session Time</p>
                <p className="text-2xl font-bold">0:45:32</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-full bg-status-watch/10 flex items-center justify-center">
                <AlertCircle className="h-6 w-6 text-status-watch" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Predictions Made</p>
                <p className="text-2xl font-bold">12 <span className="text-sm font-normal">today</span></p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-full bg-status-stable/10 flex items-center justify-center">
                <Shield className="h-6 w-6 text-status-stable" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Weekly Limit Status</p>
                <p className="text-2xl font-bold text-status-stable">Active</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Limit Settings */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Self-Limit Settings
          </CardTitle>
          <CardDescription>
            Set personal limits to maintain healthy gambling habits
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Weekly Stake Limit */}
            <div className="space-y-2">
              <Label htmlFor="weekly-limit">Weekly Stake Limit (£)</Label>
              <Input
                id="weekly-limit"
                type="number"
                min={0}
                placeholder="e.g., 50"
                value={weeklyLimit}
                onChange={(e) => setWeeklyLimit(e.target.value ? Number(e.target.value) : '')}
              />
              <p className="text-xs text-muted-foreground">
                Leave empty for no limit. System will alert when approaching limit.
              </p>
            </div>

            {/* Consecutive Loss Alert */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Loss Alert After</Label>
                  <p className="text-xs text-muted-foreground">
                    Get notified after consecutive losses
                  </p>
                </div>
                <Switch
                  checked={lossAlertEnabled}
                  onCheckedChange={setLossAlertEnabled}
                />
              </div>
              {lossAlertEnabled && (
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    min={1}
                    max={10}
                    value={consecutiveLossLimit}
                    onChange={(e) => setConsecutiveLossLimit(Number(e.target.value))}
                    className="w-20"
                  />
                  <span className="text-sm text-muted-foreground">consecutive losses</span>
                </div>
              )}
            </div>

            {/* Cooldown Period */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Cooldown Period</Label>
                  <p className="text-xs text-muted-foreground">
                    Mandatory wait between predictions
                  </p>
                </div>
                <Switch
                  checked={cooldownEnabled}
                  onCheckedChange={setCooldownEnabled}
                />
              </div>
              {cooldownEnabled && (
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    min={1}
                    max={60}
                    value={cooldownMinutes}
                    onChange={(e) => setCooldownMinutes(Number(e.target.value))}
                    className="w-20"
                  />
                  <span className="text-sm text-muted-foreground">minutes between bets</span>
                </div>
              )}
            </div>
          </div>

          <Separator />

          <Button onClick={handleSaveLimits} className="btn-glow">
            Save Limit Settings
          </Button>
        </CardContent>
      </Card>

      {/* Educational Content */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <HelpCircle className="h-5 w-5" />
            Understanding Probabilities
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="probability-meaning">
              <AccordionTrigger>What does a 52% probability really mean?</AccordionTrigger>
              <AccordionContent className="space-y-2 text-muted-foreground">
                <p>
                  A 52% probability means that if you placed this exact bet 100 times under identical conditions, 
                  you would expect to win approximately 52 times and lose 48 times.
                </p>
                <p>
                  <strong>It does NOT mean:</strong>
                </p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  <li>A guaranteed win</li>
                  <li>That the next bet will definitely win</li>
                  <li>That losses mean the system is wrong</li>
                </ul>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="accumulator-trap">
              <AccordionTrigger>The Accumulator Trap (Combinatorial Explosion)</AccordionTrigger>
              <AccordionContent className="space-y-2 text-muted-foreground">
                <p>
                  When you combine multiple bets, probabilities multiply:
                </p>
                <div className="p-4 bg-background/50 rounded-lg font-mono text-sm space-y-1">
                  <p>1 match @ 60% = <Badge variant="outline">60%</Badge> chance</p>
                  <p>5 matches @ 60% = <Badge variant="outline">7.8%</Badge> chance (0.6⁵)</p>
                  <p>10 matches @ 60% = <Badge variant="outline">0.6%</Badge> chance (0.6¹⁰)</p>
                  <p>13 matches @ 60% = <Badge variant="outline">0.13%</Badge> chance (0.6¹³)</p>
                </div>
                <p className="text-status-watch">
                  Even with "good" 60% individual probabilities, a 13-match jackpot has only about 1 in 769 chance of winning!
                </p>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="expected-value">
              <AccordionTrigger>What is Expected Value (EV)?</AccordionTrigger>
              <AccordionContent className="space-y-2 text-muted-foreground">
                <p>
                  Expected Value tells you the average profit/loss per bet over the long term:
                </p>
                <div className="p-4 bg-background/50 rounded-lg font-mono text-sm">
                  EV = (Win Probability × Potential Win) - (Loss Probability × Stake)
                </div>
                <p>
                  <strong>Positive EV:</strong> Profitable in the long run (rare in gambling)
                </p>
                <p>
                  <strong>Negative EV:</strong> Expected to lose money over time (most bets)
                </p>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="consensus-wrong">
              <AccordionTrigger>Can model and market both be wrong?</AccordionTrigger>
              <AccordionContent className="space-y-2 text-muted-foreground">
                <p>
                  <strong>Yes!</strong> Agreement between model and market does NOT guarantee correctness.
                </p>
                <p>
                  Historical examples: Leicester City winning the Premier League 2015-16 (5000/1 odds), 
                  Greece winning Euro 2004, etc.
                </p>
                <p className="text-status-watch">
                  Black swan events happen. No model can predict manager sackings, injuries, 
                  or other unexpected factors.
                </p>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
      </Card>

      {/* Help Resources */}
      <Card className="glass-card border-primary/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5 text-primary" />
            Get Help
          </CardTitle>
          <CardDescription>
            If gambling is affecting your life, please reach out
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <a 
              href="https://www.gamcare.org.uk" 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-4 rounded-lg bg-background/50 hover:bg-primary/10 transition-colors"
            >
              <ExternalLink className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">GamCare</p>
                <p className="text-xs text-muted-foreground">Free advice & support</p>
              </div>
            </a>

            <a 
              href="https://www.begambleaware.org" 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-4 rounded-lg bg-background/50 hover:bg-primary/10 transition-colors"
            >
              <ExternalLink className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">BeGambleAware</p>
                <p className="text-xs text-muted-foreground">Freephone: 0808 8020 133</p>
              </div>
            </a>

            <a 
              href="https://www.gamblingtherapy.org" 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-4 rounded-lg bg-background/50 hover:bg-primary/10 transition-colors"
            >
              <ExternalLink className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">Gambling Therapy</p>
                <p className="text-xs text-muted-foreground">Online support 24/7</p>
              </div>
            </a>
          </div>

          <Separator className="my-6" />

          <div className="text-center space-y-2">
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="destructive" className="w-full sm:w-auto">
                  Self-Exclude from System
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Self-Exclusion</DialogTitle>
                  <DialogDescription className="space-y-4 pt-4">
                    <p>
                      Self-exclusion will prevent you from accessing this prediction system 
                      for a period of your choosing.
                    </p>
                    <p className="text-status-watch">
                      This action cannot be undone during the exclusion period.
                    </p>
                    <div className="flex gap-2 pt-4">
                      <Button variant="outline" className="flex-1">7 Days</Button>
                      <Button variant="outline" className="flex-1">30 Days</Button>
                      <Button variant="outline" className="flex-1">6 Months</Button>
                    </div>
                  </DialogDescription>
                </DialogHeader>
              </DialogContent>
            </Dialog>
            <p className="text-xs text-muted-foreground">
              Must be 18+ to use this system. Gambling can be addictive.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
