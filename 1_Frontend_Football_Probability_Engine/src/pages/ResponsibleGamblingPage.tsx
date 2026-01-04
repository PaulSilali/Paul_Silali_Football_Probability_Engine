import { ResponsibleGambling } from '@/components/ResponsibleGambling';
import { PageLayout } from '@/components/layouts/PageLayout';
import { Shield } from 'lucide-react';

export default function ResponsibleGamblingPage() {
  return (
    <PageLayout
      title="Responsible Gambling"
      description="Tools and resources for maintaining healthy gambling habits"
      icon={<Shield className="h-6 w-6" />}
    >
      <ResponsibleGambling />
    </PageLayout>
  );
}
