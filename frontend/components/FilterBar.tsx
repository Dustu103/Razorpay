'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { type Cause } from '@/types/classification';

const CAUSES: { value: Cause | ''; label: string }[] = [
  { value: '', label: 'All Causes' },
  { value: 'notification_compliance_block', label: '🟡 Compliance Block' },
  { value: 'soft_decline',                  label: '🔵 Soft Decline' },
  { value: 'hard_decline',                  label: '🔴 Hard Decline' },
  { value: 'gateway_fault',                 label: '🟠 Gateway Fault' },
  { value: 'fraud_filter_block',            label: '🟣 Fraud Block' },
];

interface Props {
  currentCause: string;
  currentLayer: string;
}

export default function FilterBar({ currentCause, currentLayer }: Props) {
  const router = useRouter();

  function update(cause: string, layer: string) {
    const params = new URLSearchParams();
    if (cause) params.set('cause', cause);
    if (layer) params.set('layer', layer);
    router.push(`/?${params.toString()}`);
  }

  const layers = [
    { value: '',  label: 'All' },
    { value: '1', label: '⚡ Layer 1', cls: 'active-green' },
    { value: '2', label: '🤖 Layer 2', cls: 'active' },
  ];

  return (
    <div className="filter-bar">
      <select
        className="filter-select"
        value={currentCause}
        onChange={(e) => update(e.target.value, currentLayer)}
        aria-label="Filter by cause"
      >
        {CAUSES.map((c) => (
          <option key={c.value} value={c.value}>{c.label}</option>
        ))}
      </select>

      <div className="layer-group" role="group" aria-label="Filter by layer">
        {layers.map((l) => (
          <button
            key={l.value}
            className={`layer-btn ${currentLayer === l.value ? (l.cls ?? 'active') : ''}`}
            onClick={() => update(currentCause, l.value)}
            aria-pressed={currentLayer === l.value}
          >
            {l.label}
          </button>
        ))}
      </div>
    </div>
  );
}
