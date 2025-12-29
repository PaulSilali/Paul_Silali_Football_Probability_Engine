import { ResponsibleGambling } from '@/components/ResponsibleGambling';

export default function ResponsibleGamblingPage() {
  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-foreground text-glow">Responsible Gambling</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Tools and resources for maintaining healthy gambling habits
        </p>
      </div>
      
      <ResponsibleGambling />
    </div>
  );
}
