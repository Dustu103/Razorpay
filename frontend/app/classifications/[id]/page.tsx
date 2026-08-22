import Link from 'next/link';
import type { Metadata } from 'next';
import { fetchClassification, formatAmount, formatDate } from '@/lib/api';
import type { Cause } from '@/types/classification';
import { notFound } from 'next/navigation';

interface Props { params: Promise<{ id: string }> }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  return { title: `Classification ${id} — Classifier Inspector` };
}

export default async function ClassificationDetailPage({ params }: Props) {
  const { id } = await params;
  let data;
  try {
    data = await fetchClassification(id);
  } catch {
    notFound();
  }

  const isLayer1 = data.layer === 1;
  const pct = Math.round(data.confidence * 100);
  const confCls = pct >= 80 ? 'high' : pct >= 50 ? 'medium' : 'low';

  const causeLabels: Record<Cause, string> = {
    notification_compliance_block: '🟡 Notification Compliance Block',
    soft_decline:                  '🔵 Soft Decline',
    hard_decline:                  '🔴 Hard Decline',
    gateway_fault:                 '🟠 Gateway Fault',
    fraud_filter_block:            '🟣 Fraud Filter Block',
  };

  return (
    <>
      <Link href="/" className="back-link">
        ← Back to list
      </Link>

      <div className="detail-header">
        <div>
          <div className="detail-eyebrow">Classification Detail</div>
          <h1 className="detail-title">{causeLabels[data.cause] ?? data.cause}</h1>
          <div className="detail-txnid">Gateway ID: {data.gateway_transaction_id}</div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', alignItems: 'flex-end' }}>
          {isLayer1
            ? <span className="badge badge-layer1 large">⚡ Layer 1 · Deterministic Rule</span>
            : <span className="badge badge-layer2 large">🤖 Layer 2 · {data.model_version ?? 'Model'}</span>
          }
          <span className={`cause-badge cause-${data.cause} large`}>{data.cause.replace(/_/g, ' ')}</span>
        </div>
      </div>

      {/* Summary */}
      <div className="card">
        <div className="card-title">Summary</div>
        <div className="summary-grid">
          <div className="summary-item">
            <div className="s-label">Confidence</div>
            <div className="s-value">
              {data.confidence === 0 ? (
                <span className="conf-review" style={{ fontSize: '0.82rem', padding: '0.3rem 0.7rem' }}>⚠️ Manual Review Required</span>
              ) : (
                <div className="conf-wrap" style={{ justifyContent: 'flex-start' }}>
                  <div className="conf-bar" style={{ minWidth: 100 }}>
                    <div className={`conf-fill ${confCls}`} style={{ width: `${pct}%` }} />
                  </div>
                  <span className="conf-pct" style={{ fontSize: '0.9rem', fontWeight: 700 }}>{pct}%</span>
                </div>
              )}
            </div>
          </div>
          <div className="summary-item">
            <div className="s-label">Recommended Action</div>
            <div className="s-value">
              <span className="action-code" style={{ fontSize: '0.82rem', padding: '0.3rem 0.7rem' }}>
                {data.recommended_action}
              </span>
            </div>
          </div>
          <div className="summary-item">
            <div className="s-label">Amount</div>
            <div className="s-value" style={{ fontSize: '1.1rem', letterSpacing: '-0.02em' }}>
              {formatAmount(data.amount)}
            </div>
          </div>
          <div className="summary-item">
            <div className="s-label">Bank</div>
            <div className="s-value">{data.customer_bank ?? <span style={{ color: 'var(--text-dim)', fontWeight: 400 }}>—</span>}</div>
          </div>
          <div className="summary-item">
            <div className="s-label">Retries</div>
            <div className="s-value">{data.retry_count_so_far}</div>
          </div>
          <div className="summary-item">
            <div className="s-label">Classification Layer</div>
            <div className="s-value">
              {isLayer1
                ? <span className="badge badge-layer1">⚡ Layer 1 · Rule</span>
                : <span className="badge badge-layer2">🤖 Layer 2 · Model</span>
              }
            </div>
          </div>
        </div>

        <div className="meta-row">
          <span className="meta-item">🕐 {formatDate(data.created_at)}</span>
          {data.model_version && <span className="meta-item">🔖 {data.model_version}</span>}
          <span className="meta-item">🆔 {data.id.slice(0, 8)}…</span>
        </div>
      </div>

      {/* Reasoning */}
      <div className="card">
        <div className="card-title">Reasoning</div>
        <div className="reasoning-wrap">
          <p className="reasoning-text">{data.reasoning}</p>
        </div>
      </div>

      {/* Input payload */}
      <div className="card">
        <div className="card-title">Classifier Input Payload</div>
        <div className="payload-grid">
          <PayloadRow label="status_code"                  value={data.status_code} />
          <PayloadRow label="npci_response_code"           value={data.npci_response_code} />
          <PayloadRow label="bank_response_code"           value={data.bank_response_code} />
          <PayloadRow label="amount"                       value={formatAmount(data.amount)} />
          <PayloadRow label="customer_bank"                value={data.customer_bank} />
          <PayloadRow label="retry_count_so_far"           value={String(data.retry_count_so_far)} />
          <PayloadRow label="mandate_notification_sent_at" value={null} />
          <PayloadRow label="debit_scheduled_at"           value={null} />
        </div>
        <hr className="divider" style={{ marginTop: '1rem' }} />
        <p style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '0.75rem' }}>
          🔒 PII excluded — customer name, account number, and card PAN are never sent to the classifier.
        </p>
      </div>
    </>
  );
}

function PayloadRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <>
      <span className="payload-key">{label}</span>
      <span className={`payload-value ${value == null ? 'payload-null' : ''}`}>
        {value ?? 'null'}
      </span>
    </>
  );
}
