import Link from 'next/link';
import { fetchClassifications, formatAmount, formatDate } from '@/lib/api';
import type { ClassificationView, Cause } from '@/types/classification';
import FilterBar from '@/components/FilterBar';

interface Props {
  searchParams: Promise<{ cause?: string; layer?: string; limit?: string; offset?: string }>;
}

export default async function TransactionListPage({ searchParams }: Props) {
  const { cause = '', layer = '', limit = '50', offset = '0' } = await searchParams;

  let data: ClassificationView[] = [];
  let count = 0;
  let error = '';

  try {
    const res = await fetchClassifications({ cause, layer, limit: Number(limit), offset: Number(offset) });
    data = res.data;
    count = res.count;
  } catch (e: any) {
    error = e.message;
  }

  // Derive stats from the data
  const layer1Count  = data.filter(d => d.layer === 1).length;
  const layer2Count  = data.filter(d => d.layer === 2).length;
  const avgConf      = data.length ? (data.reduce((s, d) => s + d.confidence, 0) / data.length * 100).toFixed(0) : '—';
  const needsReview  = data.filter(d => d.confidence === 0).length;

  const causeStats: Record<Cause, number> = {
    notification_compliance_block: 0,
    soft_decline: 0, hard_decline: 0,
    gateway_fault: 0, fraud_filter_block: 0,
  };
  data.forEach(d => { if (d.cause in causeStats) causeStats[d.cause as Cause]++; });

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Transaction Classifications</h1>
        <p className="page-sub">
          Live audit trail for payment failure root-cause classification
          {cause && <><span className="page-sub-dot" /> Filtered: {cause}</>}
        </p>
      </div>

      {/* Stats row */}
      <div className="stats-row">
        <div className="stat-card" style={{ '--accent-color': 'var(--blue)' } as any}>
          <div className="stat-icon">📊</div>
          <div className="stat-value">{count}</div>
          <div className="stat-label">Total Classifications</div>
        </div>
        <div className="stat-card" style={{ '--accent-color': 'var(--green)' } as any}>
          <div className="stat-icon">⚡</div>
          <div className="stat-value">{layer1Count}</div>
          <div className="stat-label">Layer 1 · Rule</div>
        </div>
        <div className="stat-card" style={{ '--accent-color': 'var(--purple)' } as any}>
          <div className="stat-icon">🤖</div>
          <div className="stat-value">{layer2Count}</div>
          <div className="stat-label">Layer 2 · Model</div>
        </div>
        <div className="stat-card" style={{ '--accent-color': 'var(--amber)' } as any}>
          <div className="stat-icon">🎯</div>
          <div className="stat-value">{avgConf}{avgConf !== '—' ? '%' : ''}</div>
          <div className="stat-label">Avg. Confidence</div>
        </div>
        <div className="stat-card" style={{ '--accent-color': needsReview > 0 ? 'var(--red)' : 'var(--green)' } as any}>
          <div className="stat-icon">{needsReview > 0 ? '⚠️' : '✅'}</div>
          <div className="stat-value">{needsReview}</div>
          <div className="stat-label">Manual Review</div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="toolbar">
        <FilterBar currentCause={cause} currentLayer={layer} />
        <span className="result-count">{count} result{count !== 1 ? 's' : ''}</span>
      </div>

      {/* Table */}
      {error ? (
        <div className="table-wrap">
          <div className="empty-state error">
            <div className="empty-icon">⚠️</div>
            <div className="empty-title">Could not reach audit service</div>
            <div className="empty-sub">Make sure the backend is running:<br /><code style={{ fontFamily: 'var(--mono)', fontSize: '0.8rem', color: 'var(--blue)' }}>docker-compose up</code></div>
          </div>
        </div>
      ) : data.length === 0 ? (
        <div className="table-wrap">
          <div className="empty-state">
            <div className="empty-icon">📭</div>
            <div className="empty-title">No classifications yet</div>
            <div className="empty-sub">Send a <code style={{ fontFamily: 'var(--mono)', color: 'var(--blue)' }}>payment.failed</code> webhook to the ingestion service to see results here.</div>
          </div>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Gateway Txn ID</th>
                <th>Layer</th>
                <th>Cause</th>
                <th>Confidence</th>
                <th>Action</th>
                <th>Amount</th>
                <th>Classified</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.id}>
                  <td>
                    <Link href={`/classifications/${row.id}`} className="txn-id">
                      {row.gateway_transaction_id}
                    </Link>
                  </td>
                  <td><LayerBadge layer={row.layer} /></td>
                  <td><CauseBadge cause={row.cause} /></td>
                  <td><ConfidenceBar confidence={row.confidence} /></td>
                  <td><span className="action-code">{row.recommended_action}</span></td>
                  <td style={{ fontWeight: 600 }}>{formatAmount(row.amount)}</td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>{formatDate(row.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/* ── Server-side components ─────────────────────────────────────────── */

function LayerBadge({ layer }: { layer: 1 | 2 }) {
  return layer === 1
    ? <span className="badge badge-layer1">⚡ Layer 1</span>
    : <span className="badge badge-layer2">🤖 Layer 2</span>;
}

function CauseBadge({ cause }: { cause: Cause }) {
  const labels: Record<Cause, string> = {
    notification_compliance_block: '🟡 Compliance',
    soft_decline:                  '🔵 Soft',
    hard_decline:                  '🔴 Hard',
    gateway_fault:                 '🟠 Gateway',
    fraud_filter_block:            '🟣 Fraud',
  };
  return <span className={`cause-badge cause-${cause}`}>{labels[cause] ?? cause}</span>;
}

function ConfidenceBar({ confidence }: { confidence: number }) {
  if (confidence === 0) {
    return <span className="conf-review">⚠️ Review</span>;
  }
  const pct = Math.round(confidence * 100);
  const cls = pct >= 80 ? 'high' : pct >= 50 ? 'medium' : 'low';
  return (
    <div className="conf-wrap">
      <div className="conf-bar">
        <div className={`conf-fill ${cls}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="conf-pct">{pct}%</span>
    </div>
  );
}
