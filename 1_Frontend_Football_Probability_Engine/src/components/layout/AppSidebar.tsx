import { 
  ClipboardList, 
  BarChart3, 
  Layers, 
  Target, 
  Lightbulb, 
  Activity, 
  Settings,
  LogOut,
  LayoutDashboard,
  Database,
  Download,
  Brain,
  CheckSquare,
  Shield,
  Sparkles,
  ChevronDown,
  Ticket,
  History,
  FileText,
  Info
} from 'lucide-react';
import { NavLink } from '@/components/NavLink';
import { useAuth } from '@/contexts/AuthContext';
import { useState } from 'react';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from '@/components/ui/sidebar';
import { Button } from '@/components/ui/button';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';

const mlTrainingItems = [
  {
    title: 'Data Ingestion',
    url: '/data-ingestion',
    icon: Download,
    description: 'Import historical data',
  },
  {
    title: 'Data Cleaning & ETL',
    url: '/data-cleaning',
    icon: Sparkles,
    description: 'Feature engineering & ETL',
  },
  {
    title: 'Data Contract',
    url: '/training-data-contract',
    icon: FileText,
    description: 'Required vs optional fields',
  },
  {
    title: 'Model Training',
    url: '/ml-training',
    icon: Brain,
    description: 'Train prediction models',
  },
];

const navigationItems = [
  {
    title: 'Dashboard',
    url: '/dashboard',
    icon: LayoutDashboard,
    description: 'System health overview',
  },
  {
    title: 'Jackpot Input',
    url: '/jackpot-input',
    icon: ClipboardList,
    description: 'Enter fixtures and odds',
  },
  {
    title: 'Probability Output',
    url: '/probability-output',
    icon: BarChart3,
    description: 'View calculated probabilities',
  },
  {
    title: 'Sets Comparison',
    url: '/sets-comparison',
    icon: Layers,
    description: 'Compare probability sets',
  },
  {
    title: 'Ticket Construction',
    url: '/ticket-construction',
    icon: Ticket,
    description: 'Generate jackpot tickets',
  },
  {
    title: 'Sure Bet',
    url: '/sure-bet',
    icon: Target,
    description: 'Find high-confidence sure bets',
  },
  {
    title: 'Jackpot Validation',
    url: '/jackpot-validation',
    icon: CheckSquare,
    description: 'Compare predictions vs results',
  },
  {
    title: 'Backtesting',
    url: '/backtesting',
    icon: History,
    description: 'Test against historical results',
  },
  {
    title: 'Feature Store',
    url: '/feature-store',
    icon: Database,
    description: 'Team features & data quality',
  },
  {
    title: 'Calibration',
    url: '/calibration',
    icon: Target,
    description: 'Validation metrics',
  },
  {
    title: 'Calibration Management',
    url: '/calibration-management',
    icon: Settings,
    description: 'Fit and manage calibration versions',
  },
  {
    title: 'Explainability',
    url: '/explainability',
    icon: Lightbulb,
    description: 'Model contributions',
  },
  {
    title: 'Model Health',
    url: '/model-health',
    icon: Activity,
    description: 'Stability monitoring',
  },
  {
    title: 'Responsible Gambling',
    url: '/responsible-gambling',
    icon: Shield,
    description: 'Limits & resources',
  },
  {
    title: 'About',
    url: '/about',
    icon: Info,
    description: 'Decision Intelligence system',
  },
  {
    title: 'System',
    url: '/system',
    icon: Settings,
    description: 'Data & model management',
  },
];

export function AppSidebar() {
  const { user, logout } = useAuth();
  const [mlOpen, setMlOpen] = useState(true);

  return (
    <Sidebar className="border-r border-border/50 bg-background dark:bg-background/95 backdrop-blur-xl shadow-lg">
      <SidebarHeader className="p-4 border-b border-border/40 bg-gradient-to-r from-primary/5 via-primary/3 to-transparent">
        <div className="flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary/20 via-primary/10 to-primary/5 border border-primary/20 shadow-lg shadow-primary/10">
            <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-primary/30 to-transparent opacity-50 blur-sm" />
            <BarChart3 className="h-5 w-5 text-primary relative z-10" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold text-foreground tracking-tight bg-gradient-to-r from-foreground to-foreground/80 bg-clip-text">
              Probability Engine
            </span>
            <span className="text-xs text-muted-foreground/80 font-medium">
              Football Jackpot
            </span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarSeparator className="bg-border/50 dark:bg-border/30" />

      <SidebarContent className="bg-transparent">
        <SidebarGroup>
          <SidebarGroupLabel className="text-muted-foreground/70 uppercase text-[10px] tracking-[0.15em] font-bold mb-3 px-3">
            <span className="bg-gradient-to-r from-primary/60 via-primary/40 to-transparent bg-clip-text text-transparent">
            Analysis
            </span>
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="space-y-1">
              {/* Dashboard */}
              <SidebarMenuItem>
                <SidebarMenuButton asChild tooltip="System health overview">
                  <NavLink
                    to="/dashboard"
                    className="group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-foreground/70 transition-all duration-200 hover:bg-gradient-to-r hover:from-primary/10 hover:via-primary/5 hover:to-transparent hover:text-foreground hover:shadow-sm hover:shadow-primary/5 hover:scale-[1.02]"
                    activeClassName="bg-gradient-to-r from-primary/15 via-primary/10 to-primary/5 text-foreground font-semibold shadow-md shadow-primary/10 border border-primary/20 scale-[1.02]"
                  >
                    <div className="relative">
                      <div className="absolute inset-0 rounded-lg bg-primary/20 blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
                      <LayoutDashboard className="h-4 w-4 shrink-0 relative z-10" />
                    </div>
                    <span className="truncate font-medium">Dashboard</span>
                  </NavLink>
                </SidebarMenuButton>
              </SidebarMenuItem>

              {/* ML Training Collapsible Group */}
              <Collapsible open={mlOpen} onOpenChange={setMlOpen}>
                <CollapsibleTrigger asChild>
                  <SidebarMenuButton className="group relative flex items-center justify-between gap-3 rounded-xl px-3 py-2.5 text-foreground/70 transition-all duration-200 hover:bg-gradient-to-r hover:from-primary/10 hover:via-primary/5 hover:to-transparent hover:text-foreground hover:shadow-sm hover:shadow-primary/5 hover:scale-[1.02] w-full">
                    <div className="flex items-center gap-3">
                      <div className="relative">
                        <div className="absolute inset-0 rounded-lg bg-primary/20 blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
                        <Brain className="h-4 w-4 shrink-0 relative z-10" />
                      </div>
                      <span className="truncate font-medium">ML Training</span>
                    </div>
                    <ChevronDown className={`h-4 w-4 transition-all duration-200 ${mlOpen ? 'rotate-180 text-primary' : ''}`} />
                  </SidebarMenuButton>
                </CollapsibleTrigger>
                <CollapsibleContent className="overflow-hidden data-[state=open]:animate-in data-[state=closed]:animate-out">
                  <div className="ml-6 border-l-2 border-gradient-to-b from-primary/30 via-primary/20 to-transparent pl-3 mt-2 space-y-1.5">
                    {mlTrainingItems.map((item) => (
                      <SidebarMenuItem key={item.title}>
                        <SidebarMenuButton asChild tooltip={item.description}>
                          <NavLink
                            to={item.url}
                            className="group relative flex items-center gap-3 rounded-lg px-3 py-2 text-foreground/60 transition-all duration-200 hover:bg-gradient-to-r hover:from-primary/8 hover:via-primary/4 hover:to-transparent hover:text-foreground hover:translate-x-1 text-sm"
                            activeClassName="bg-gradient-to-r from-primary/12 via-primary/8 to-primary/4 text-foreground font-semibold border-l-2 border-primary shadow-sm shadow-primary/5 translate-x-1"
                          >
                            <div className="relative">
                              <div className="absolute inset-0 rounded-md bg-primary/15 blur-sm opacity-0 group-hover:opacity-100 transition-opacity" />
                              <item.icon className="h-3.5 w-3.5 shrink-0 relative z-10" />
                            </div>
                            <span className="truncate">{item.title}</span>
                          </NavLink>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    ))}
                  </div>
                </CollapsibleContent>
              </Collapsible>

              {/* Other navigation items */}
              {navigationItems.slice(1).map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild tooltip={item.description}>
                    <NavLink
                      to={item.url}
                      className="group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-foreground/70 transition-all duration-200 hover:bg-gradient-to-r hover:from-primary/10 hover:via-primary/5 hover:to-transparent hover:text-foreground hover:shadow-sm hover:shadow-primary/5 hover:scale-[1.02]"
                      activeClassName="bg-gradient-to-r from-primary/15 via-primary/10 to-primary/5 text-foreground font-semibold shadow-md shadow-primary/10 border border-primary/20 scale-[1.02]"
                    >
                      <div className="relative">
                        <div className="absolute inset-0 rounded-lg bg-primary/20 blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
                        <item.icon className="h-4 w-4 shrink-0 relative z-10" />
                      </div>
                      <span className="truncate font-medium">{item.title}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-4 border-t border-border/50 dark:border-border/30 bg-background/50 dark:bg-background/80">
        <SidebarSeparator className="mb-4 bg-border/50 dark:bg-border/30" />
        <div className="flex items-center justify-between gap-3 p-2 rounded-xl bg-gradient-to-r from-muted/30 via-muted/20 to-transparent border border-border/30">
          <div className="flex flex-col min-w-0 flex-1">
            <span className="text-sm font-semibold text-foreground truncate">
              {user?.name || 'User'}
            </span>
            <span className="text-xs text-muted-foreground/70 truncate">
              {user?.email || ''}
            </span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={logout}
            className="h-9 w-9 shrink-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all duration-200 hover:scale-110 rounded-lg border border-transparent hover:border-destructive/20"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
