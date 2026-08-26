import { Circle } from 'lucide-react';
import type { Cause } from '@/types/classification';

interface Props {
  cause: Cause;
  large?: boolean;
}

export function CauseBadge({ cause, large = false }: Props) {
  const labels: Record<Cause, string> = {
    notification_compliance_block: large ? 'Notification Compliance Block' : 'Compliance',
    soft_decline:                  'Soft Decline',
    hard_decline:                  'Hard Decline',
    gateway_fault:                 'Gateway Fault',
    fraud_filter_block:            large ? 'Fraud Filter Block' : 'Fraud',
  };

  const className = `cause-badge cause-${cause} ${large ? 'large' : ''}`;

  return (
    <span className={className}>
      <Circle size={10} fill="currentColor" strokeWidth={0} />
      {labels[cause] ?? cause.replace(/_/g, ' ')}
    </span>
  );
}
