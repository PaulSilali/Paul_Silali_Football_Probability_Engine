/**
 * Main Application Component
 * 
 * Professional dashboard layout with top-level navigation
 * and section-based content display.
 */

import React, { useEffect } from 'react';
import { Activity, BarChart3, Database, FileText, GitBranch, Home, Settings } from 'lucide-react';
import { useAppStore } from './store';
import { getModelVersion, getModelHealth } from './api';
import type { NavigationSection } from './types';

// Section Components
import { JackpotInput } from './components/sections/JackpotInput';
import { ProbabilityOutput } from './components/sections/ProbabilityOutput';
import { ProbabilitySetsComparison } from './components/sections/ProbabilitySetsComparison';
import { CalibrationDashboard } from './components/sections/CalibrationDashboard';
import { ModelExplainability } from './components/sections/ModelExplainability';
import { ModelHealth } from './components/sections/ModelHealth';
import { SystemManagement } from './components/sections/SystemManagement';

import { Badge, LoadingSpinner } from './components/ui';

interface NavigationItem {
  id: NavigationSection;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
}

const NAVIGATION: NavigationItem[] = [
  {
    id: 'input',
    label: 'Jackpot Input',
    icon: Home,
    description: 'Define fixtures and odds',
  },
  {
    id: 'output',
    label: 'Probability Output',
    icon: FileText,
    description: 'View calibrated probabilities',
  },
  {
    id: 'comparison',
    label: 'Set Comparison',
    icon: GitBranch,
    description: 'Compare probability sets',
  },
  {
    id: 'calibration',
    label: 'Calibration',
    icon: BarChart3,
    description: 'Model validation metrics',
  },
  {
    id: 'explainability',
    label: 'Explainability',
    icon: Activity,
    description: 'Feature contributions',
  },
  {
    id: 'health',
    label: 'Model Health',
    icon: Activity,
    description: 'System monitoring',
  },
  {
    id: 'management',
    label: 'System',
    icon: Settings,
    description: 'Data & model management',
  },
];

export function App() {
  const {
    activeSection,
    setActiveSection,
    currentModelVersion,
    modelHealth,
    setModelVersion,
    setModelHealth,
    isLoading,
    error,
    setError,
  } = useAppStore();
  
  // ============================================================================
  // INITIALIZATION
  // ============================================================================
  
  useEffect(() => {
    // Load initial model status and health on mount
    const loadInitialData = async () => {
      try {
        const [version, health] = await Promise.all([
          getModelVersion(),
          getModelHealth(),
        ]);
        
        setModelVersion(version);
        setModelHealth(health);
      } catch (err) {
        console.error('Failed to load initial data:', err);
      }
    };
    
    loadInitialData();
  }, [setModelVersion, setModelHealth]);
  
  // ============================================================================
  // RENDER ACTIVE SECTION
  // ============================================================================
  
  const renderSection = () => {
    switch (activeSection) {
      case 'input':
        return <JackpotInput />;
      case 'output':
        return <ProbabilityOutput />;
      case 'comparison':
        return <ProbabilitySetsComparison />;
      case 'calibration':
        return <CalibrationDashboard />;
      case 'explainability':
        return <ModelExplainability />;
      case 'health':
        return <ModelHealth />;
      case 'management':
        return <SystemManagement />;
      default:
        return <JackpotInput />;
    }
  };
  
  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <Database className="h-8 w-8 text-slate-700" />
              <div className="ml-3">
                <h1 className="text-xl font-semibold text-slate-900">
                  Jackpot Probability Engine
                </h1>
                <p className="text-xs text-slate-600">
                  Statistical Analysis & Calibrated Probability Estimation
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {currentModelVersion && (
                <div className="text-right text-sm">
                  <p className="text-slate-600">Model: {currentModelVersion.version}</p>
                  <p className="text-xs text-slate-500">
                    Brier: {currentModelVersion.validationMetrics.brierScore.toFixed(3)}
                  </p>
                </div>
              )}
              
              {modelHealth && (
                <Badge
                  variant={
                    modelHealth.status === 'healthy' ? 'success' :
                    modelHealth.status === 'watch' ? 'warning' :
                    'error'
                  }
                >
                  {modelHealth.status}
                </Badge>
              )}
            </div>
          </div>
        </div>
      </header>
      
      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-12 gap-6">
          {/* Sidebar Navigation */}
          <aside className="col-span-3">
            <nav className="space-y-1 sticky top-24">
              {NAVIGATION.map((item) => {
                const Icon = item.icon;
                const isActive = activeSection === item.id;
                
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveSection(item.id)}
                    className={`w-full flex items-start gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                      isActive
                        ? 'bg-slate-700 text-white'
                        : 'text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    <Icon className="h-5 w-5 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="font-medium text-sm">{item.label}</div>
                      <div className={`text-xs mt-0.5 ${
                        isActive ? 'text-slate-300' : 'text-slate-500'
                      }`}>
                        {item.description}
                      </div>
                    </div>
                  </button>
                );
              })}
            </nav>
          </aside>
          
          {/* Main Content Area */}
          <main className="col-span-9">
            {/* Global Error Banner */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium text-red-900">Error</h4>
                    <p className="text-sm text-red-700 mt-1">{error}</p>
                  </div>
                  <button
                    onClick={() => setError(null)}
                    className="text-red-500 hover:text-red-700"
                  >
                    ✕
                  </button>
                </div>
              </div>
            )}
            
            {/* Loading Overlay */}
            {isLoading && (
              <div className="mb-6 flex items-center justify-center p-8 bg-white border border-slate-200 rounded-lg">
                <LoadingSpinner size="lg" />
                <span className="ml-4 text-slate-600">Processing...</span>
              </div>
            )}
            
            {/* Active Section Content */}
            {renderSection()}
          </main>
        </div>
      </div>
      
      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between text-sm text-slate-600">
            <p>
              This system provides probability estimates, not betting advice.
              All outputs represent model-implied likelihoods.
            </p>
            <p>
              Version 1.0.0 | {new Date().getFullYear()}
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
