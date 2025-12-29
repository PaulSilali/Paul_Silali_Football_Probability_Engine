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
  FileText
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
    <Sidebar className="border-r-0">
      <SidebarHeader className="p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-sidebar-accent">
            <BarChart3 className="h-5 w-5 text-sidebar-accent-foreground" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-sidebar-foreground">
              Probability Engine
            </span>
            <span className="text-xs text-sidebar-foreground/60">
              Football Jackpot
            </span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarSeparator />

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="text-sidebar-foreground/50 uppercase text-xs tracking-wider">
            Analysis
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {/* Dashboard */}
              <SidebarMenuItem>
                <SidebarMenuButton asChild tooltip="System health overview">
                  <NavLink
                    to="/dashboard"
                    className="flex items-center gap-3 rounded-lg px-3 py-2 text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                    activeClassName="bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                  >
                    <LayoutDashboard className="h-4 w-4 shrink-0" />
                    <span className="truncate">Dashboard</span>
                  </NavLink>
                </SidebarMenuButton>
              </SidebarMenuItem>

              {/* ML Training Collapsible Group */}
              <Collapsible open={mlOpen} onOpenChange={setMlOpen}>
                <CollapsibleTrigger asChild>
                  <SidebarMenuButton className="flex items-center justify-between gap-3 rounded-lg px-3 py-2 text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground w-full">
                    <div className="flex items-center gap-3">
                      <Brain className="h-4 w-4 shrink-0" />
                      <span className="truncate">ML Training</span>
                    </div>
                    <ChevronDown className={`h-4 w-4 transition-transform ${mlOpen ? 'rotate-180' : ''}`} />
                  </SidebarMenuButton>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="ml-4 border-l border-sidebar-border pl-2 mt-1 space-y-1">
                    {mlTrainingItems.map((item) => (
                      <SidebarMenuItem key={item.title}>
                        <SidebarMenuButton asChild tooltip={item.description}>
                          <NavLink
                            to={item.url}
                            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground text-sm"
                            activeClassName="bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                          >
                            <item.icon className="h-4 w-4 shrink-0" />
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
                      className="flex items-center gap-3 rounded-lg px-3 py-2 text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                      activeClassName="bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                    >
                      <item.icon className="h-4 w-4 shrink-0" />
                      <span className="truncate">{item.title}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-4">
        <SidebarSeparator className="mb-4" />
        <div className="flex items-center justify-between">
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-medium text-sidebar-foreground truncate">
              {user?.name || 'User'}
            </span>
            <span className="text-xs text-sidebar-foreground/60 truncate">
              {user?.email || ''}
            </span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={logout}
            className="h-8 w-8 shrink-0 text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
