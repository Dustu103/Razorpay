import { AlertTriangle } from 'lucide-react';

interface Props {
  confidence: number;
}

export function ConfidenceBar({ confidence }: Props) {
  if (confidence === 0) {
    return (
      <span className="conf-review" style={{ fontSize: '0.82rem', padding: '0.3rem 0.7rem' }}>
        <AlertTriangle size={14} /> Manual Review Required
      </span>
    );
  }
  
  const pct = Math.round(confidence * 100);
  const cls = pct >= 80 ? 'high' : pct >= 50 ? 'medium' : 'low';
  
  return (
    <div className="conf-wrap" style={{ justifyContent: 'flex-start' }}>
      <div className="conf-bar" style={{ minWidth: 100 }}>
        <div className={`conf-fill ${cls}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="conf-pct" style={{ fontSize: '0.9rem', fontWeight: 700 }}>{pct}%</span>
    </div>
  );
}
