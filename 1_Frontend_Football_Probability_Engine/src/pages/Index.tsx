import { useNavigate } from 'react-router-dom';
import { 
  ArrowRight, 
  BarChart3, 
  Brain, 
  Database, 
  Target, 
  Zap,
  TrendingUp,
  Shield,
  Activity
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import heroBg from '@/assets/hero-bg.jpg';

const features = [
  {
    icon: Brain,
    title: 'Poisson/Dixon-Coles',
    description: 'Advanced goal expectation modeling with time-decay and home advantage factors',
  },
  {
    icon: BarChart3,
    title: 'Market Blending',
    description: 'Intelligent fusion of model predictions with bookmaker odds for optimal accuracy',
  },
  {
    icon: Target,
    title: 'Calibration Layer',
    description: 'Isotonic regression ensures probabilities are statistically reliable',
  },
  {
    icon: Database,
    title: 'Feature Store',
    description: 'Rolling team metrics, league statistics, and real-time data freshness monitoring',
  },
];

const stats = [
  { value: '67.3%', label: 'Weekly Accuracy', icon: TrendingUp },
  { value: '0.142', label: 'Brier Score', icon: Target },
  { value: '45K+', label: 'Matches Analyzed', icon: Activity },
  { value: '12', label: 'Leagues Covered', icon: Shield },
];

export default function Index() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background overflow-hidden">
      {/* Hero Section */}
      <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden">
        {/* Background Image with Overlay */}
        <div className="absolute inset-0">
          <img 
            src={heroBg} 
            alt="Analytics Control Room" 
            className="w-full h-full object-cover opacity-40"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-background/60 via-background/80 to-background" />
          <div className="absolute inset-0 grid-pattern opacity-30" />
        </div>

        {/* Animated Glow Orbs */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[128px] animate-glow-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-accent/20 rounded-full blur-[128px] animate-glow-pulse" style={{ animationDelay: '1s' }} />

        {/* Hero Content */}
        <div className="relative z-10 max-w-6xl mx-auto px-6 text-center">
          <div className="mb-6 inline-flex items-center gap-2 px-4 py-2 glass-card text-sm animate-fade-in">
            <Zap className="h-4 w-4 text-primary" />
            <span className="text-muted-foreground">Probability Engine v2.4.1</span>
            <span className="px-2 py-0.5 bg-primary/20 text-primary text-xs rounded-full">Stable</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-bold mb-6 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
            <span className="gradient-text text-glow">Jackpot Probability</span>
            <br />
            <span className="text-foreground">Prediction Engine</span>
          </h1>

          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-8 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
            Advanced ML-powered system for calibrated football outcome probabilities. 
            Poisson modeling, market blending, and real-time validation.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
            <Button 
              size="lg" 
              className="btn-glow bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={() => navigate('/jackpot-input')}
            >
              Start Prediction
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            <Button 
              size="lg" 
              variant="outline" 
              className="glass-card border-primary/30 hover:bg-primary/10"
              onClick={() => navigate('/dashboard')}
            >
              View Dashboard
            </Button>
          </div>
        </div>

        {/* Scroll Indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-float">
          <div className="w-6 h-10 rounded-full border-2 border-primary/30 flex items-start justify-center p-2">
            <div className="w-1 h-2 bg-primary rounded-full animate-glow-pulse" />
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="relative py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {stats.map((stat, index) => (
              <div 
                key={stat.label}
                className="glass-card p-6 text-center animate-fade-in-up"
                style={{ animationDelay: `${0.1 * index}s` }}
              >
                <stat.icon className="h-8 w-8 text-primary mx-auto mb-3" />
                <div className="text-3xl md:text-4xl font-bold gradient-text mb-1">{stat.value}</div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              <span className="gradient-text">Four-Layer</span> Architecture
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              A production-grade system designed for stability, accuracy, and calibrated probability outputs.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {features.map((feature, index) => (
              <div 
                key={feature.title}
                className="glass-card-elevated p-8 group hover:border-primary/30 transition-all duration-300 animate-fade-in-up"
                style={{ animationDelay: `${0.1 * index}s` }}
              >
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-xl bg-primary/10 text-primary group-hover:glow-primary transition-all duration-300">
                    <feature.icon className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold mb-2 group-hover:text-primary transition-colors">
                      {feature.title}
                    </h3>
                    <p className="text-muted-foreground">{feature.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="glass-card-elevated p-12 relative overflow-hidden">
            {/* Background glow */}
            <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-accent/5 to-primary/5" />
            
            <div className="relative z-10">
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                Ready to <span className="gradient-text">Analyze?</span>
              </h2>
              <p className="text-muted-foreground mb-8 max-w-xl mx-auto">
                Input your jackpot fixtures and get calibrated probability estimates across multiple model configurations.
              </p>
              <div className="flex flex-wrap items-center justify-center gap-4">
                <Button 
                  size="lg" 
                  className="btn-glow bg-primary text-primary-foreground hover:bg-primary/90"
                  onClick={() => navigate('/jackpot-input')}
                >
                  Enter Fixtures
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
                <Button 
                  size="lg" 
                  variant="ghost" 
                  className="hover:bg-primary/10"
                  onClick={() => navigate('/ml-training')}
                >
                  Explore Models
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/50 py-8 px-6">
        <div className="max-w-6xl mx-auto text-center">
          <p className="text-sm text-muted-foreground">
            This system estimates probabilities. It does not provide betting advice.
          </p>
        </div>
      </footer>
    </div>
  );
}
