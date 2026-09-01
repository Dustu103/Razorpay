'use client';

import { useState } from 'react';
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  FileText,
  Mail,
  BadgeIndianRupee,
  Building2,
  CalendarClock
} from 'lucide-react';

type Approval = {
  id: string;
  invoice_id: string;
  customer_name: string;
  is_msme: boolean;
  days_late: number;
  tax_rule_triggered: string;
  draft_email_body: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
};

// Simulated data — in production this comes from the DB via a server action
const MOCK_APPROVALS: Approval[] = [
  {
    id: 'a1b2c3d4-0001-0000-0000-000000000001',
    invoice_id: 'INV-102',
    customer_name: 'MSME Suppliers Pvt Ltd',
    is_msme: true,
    days_late: 46,
    tax_rule_triggered: 'Sec 43B(h) Penalty',
    draft_email_body: `Dear Finance Team,

This is a formal notice regarding Invoice INV-102 for ₹7,50,000 which has been outstanding for 46 days, exceeding the statutory 45-day payment threshold mandated under Section 43B(h) of the Income Tax Act, 1961.

Under this provision, if your organization fails to settle dues owed to an MSME-registered vendor within 45 days from the date of acceptance, you will be DISALLOWED from claiming the corresponding expenditure as a tax deduction in the current financial year. This disallowance will materially increase your taxable income.

We request immediate settlement of the outstanding amount to avoid this adverse tax consequence. Kindly confirm the payment timeline at your earliest convenience.

Regards,
Accounts Receivable Team`,
    status: 'pending',
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'a1b2c3d4-0002-0000-0000-000000000002',
    invoice_id: 'INV-104',
    customer_name: 'Global Traders Pvt Ltd',
    is_msme: false,
    days_late: 181,
    tax_rule_triggered: 'CGST Rule 37 – ITC Reversal',
    draft_email_body: `Dear Finance Team,

This notice pertains to Invoice INV-104 for ₹1,20,000 which has been unpaid for 181 days, triggering mandatory obligations under Rule 37 of the CGST Rules, 2017.

Under Rule 37, your organization is legally required to REVERSE the Input Tax Credit (ITC) claimed on this invoice since payment was not made within 180 days from the invoice date. Failure to reverse this ITC in your GSTR-3B filing will constitute a tax compliance violation, attracting interest under Section 50 and potential penalties under Section 122 of the CGST Act, 2017.

We strongly urge immediate payment to allow you to legitimately retain the ITC already claimed. Please arrange for settlement today.

Regards,
Accounts Receivable Team`,
    status: 'pending',
    created_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'a1b2c3d4-0003-0000-0000-000000000003',
    invoice_id: 'INV-089',
    customer_name: 'Apex Manufacturing Ltd',
    is_msme: true,
    days_late: 52,
    tax_rule_triggered: 'Sec 43B(h) Penalty',
    draft_email_body: `Dear Finance Team,\n\nPlease be advised that Invoice INV-089 for ₹3,20,000 is now 52 days overdue, well past the 45-day threshold under Section 43B(h) of the Income Tax Act.\n\nThis delay now constitutes a statutory disallowance of the expense for the current Assessment Year. We advise immediate payment.\n\nRegards,\nAccounts Receivable Team`,
    status: 'approved',
    created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
  },
];

const statusConfig = {
  pending: { color: 'var(--amber)', bg: 'var(--amber-dim)', border: 'rgba(251, 191, 36, 0.3)', icon: Clock, label: 'Awaiting Approval' },
  approved: { color: 'var(--green)', bg: 'var(--green-dim)', border: 'rgba(52, 211, 153, 0.3)', icon: CheckCircle2, label: 'Approved & Sent' },
  rejected: { color: 'var(--red)', bg: 'var(--red-dim)', border: 'rgba(248, 113, 113, 0.3)', icon: XCircle, label: 'Rejected' },
};

const ruleConfig: Record<string, { color: string; bg: string; border: string }> = {
  'Sec 43B(h) Penalty': { color: 'var(--purple)', bg: 'var(--purple-dim)', border: 'rgba(192, 132, 252, 0.3)' },
  'CGST Rule 37 – ITC Reversal': { color: 'var(--amber)', bg: 'var(--amber-dim)', border: 'rgba(251, 191, 36, 0.3)' },
};

export default function TaxApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>(MOCK_APPROVALS);
  const [selected, setSelected] = useState<Approval | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const pendingCount = approvals.filter(a => a.status === 'pending').length;
  const approvedCount = approvals.filter(a => a.status === 'approved').length;
  const totalRecovered = approvals
    .filter(a => a.status === 'approved')
    .reduce((sum, a) => sum + a.days_late * 1500, 0); // ₹1500/day est. cost of capital

  const handleAction = async (id: string, action: 'approved' | 'rejected') => {
    setActionLoading(id);
    // Simulate API call
    await new Promise(r => setTimeout(r, 800));
    setApprovals(prev =>
      prev.map(a => a.id === id ? { ...a, status: action } : a)
    );
    if (selected?.id === id) {
      setSelected(prev => prev ? { ...prev, status: action } : null);
    }
    setActionLoading(null);
  };

  const handleRefresh = async () => {
    setLoading(true);
    await new Promise(r => setTimeout(r, 1000));
    setLoading(false);
  };

  const getRuleStyle = (rule: string) =>
    ruleConfig[rule] ?? { color: 'var(--text-primary)', bg: 'var(--bg-card)', border: 'var(--border)' };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '1rem 2rem' }}>

      {/* PAGE HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2.5rem' }}>
        <div>
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <ShieldCheck size={32} style={{ color: 'var(--indigo)' }} />
            B2B Tax Lever — Approvals
          </h1>
          <p className="page-sub" style={{ marginTop: '0.5rem', maxWidth: '650px' }}>
            Human-in-the-loop review for AI-generated legal notices. Review LLM-drafted emails citing
            <strong style={{ color: 'var(--purple)', fontWeight: 600, margin: '0 4px' }}>Sec 43B(h)</strong> and 
            <strong style={{ color: 'var(--amber)', fontWeight: 600, margin: '0 4px' }}>CGST Rule 37</strong> 
            before they are dispatched to buyers.
          </p>
        </div>
        <button
          className="btn"
          onClick={handleRefresh}
          disabled={loading}
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          {loading ? <Loader2 size={16} className="spin" /> : <RefreshCw size={16} />}
          Refresh Queue
        </button>
      </div>

      {/* STATS BAR */}
      <div className="stats-row">
        {[
          { label: 'Pending Review', value: pendingCount, icon: Clock, accent: 'var(--amber)' },
          { label: 'Approved & Sent', value: approvedCount, icon: CheckCircle2, accent: 'var(--green)' },
          { label: 'Total Monitored', value: approvals.length, icon: FileText, accent: 'var(--blue)' },
          { label: 'Potential Recovery', value: `₹${(totalRecovered).toLocaleString('en-IN')}`, icon: BadgeIndianRupee, accent: 'var(--indigo)' },
        ].map(({ label, value, icon: Icon, accent }) => (
          <div key={label} className="stat-card" style={{ '--accent-color': accent } as any}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <p className="stat-label">{label}</p>
                <p className="stat-value" style={{ marginTop: '0.4rem' }}>{value}</p>
              </div>
              <Icon size={24} style={{ color: accent }} />
            </div>
          </div>
        ))}
      </div>

      {/* MAIN SPLIT VIEW */}
      <div style={{ display: 'grid', gridTemplateColumns: '420px 1fr', gap: '1.5rem', alignItems: 'start' }}>

        {/* LEFT: APPROVAL QUEUE */}
        <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
          <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Clock size={18} style={{ color: 'var(--indigo)' }} />
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Approval Queue ({pendingCount} pending)</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {approvals.map((a, idx) => {
              const sc = statusConfig[a.status];
              const StatusIcon = sc.icon;
              const ruleStyle = getRuleStyle(a.tax_rule_triggered);
              const isSelected = selected?.id === a.id;
              
              return (
                <div
                  key={a.id}
                  onClick={() => setSelected(a)}
                  style={{
                    padding: '1.25rem 1.5rem',
                    borderTop: idx > 0 ? '1px solid var(--border)' : 'none',
                    cursor: 'pointer',
                    background: isSelected ? 'rgba(129, 140, 248, 0.08)' : 'transparent',
                    borderLeft: isSelected ? '3px solid var(--indigo)' : '3px solid transparent',
                    transition: 'all 0.2s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) e.currentTarget.style.background = 'var(--bg-card-hover)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Building2 size={14} style={{ color: 'var(--text-muted)' }} />
                      <span style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-primary)' }}>{a.customer_name}</span>
                    </div>
                    <span style={{ fontSize: '0.7rem', fontWeight: 700, color: sc.color, backgroundColor: sc.bg, border: `1px solid ${sc.border}`, borderRadius: '12px', padding: '2px 8px', display: 'flex', alignItems: 'center', gap: '4px', whiteSpace: 'nowrap', textTransform: 'uppercase' }}>
                      <StatusIcon size={12} /> {sc.label}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, backgroundColor: ruleStyle.bg, color: ruleStyle.color, border: `1px solid ${ruleStyle.border}`, borderRadius: '6px', padding: '2px 8px' }}>
                      {a.tax_rule_triggered}
                    </span>
                    <span className="action-code">
                      {a.invoice_id}
                    </span>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, backgroundColor: a.days_late >= 180 ? 'var(--red-dim)' : 'var(--amber-dim)', color: a.days_late >= 180 ? 'var(--red)' : 'var(--amber)', border: `1px solid ${a.days_late >= 180 ? 'rgba(248,113,113,0.3)' : 'rgba(251,191,36,0.3)'}`, borderRadius: '6px', padding: '2px 8px' }}>
                      {a.days_late}d overdue
                    </span>
                    {a.is_msme && (
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, backgroundColor: 'var(--indigo-dim)', color: 'var(--indigo)', border: '1px solid rgba(129, 140, 248, 0.3)', borderRadius: '6px', padding: '2px 8px' }}>
                        MSME
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* RIGHT: DETAIL PANEL */}
        {!selected ? (
          <div className="empty-state" style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', backgroundColor: 'var(--bg-card)' }}>
            <Mail size={48} className="empty-icon" />
            <h3 className="empty-title">Select a Case to Review</h3>
            <p className="empty-sub">
              Click on a pending item from the queue to review the AI-drafted legal notice before it is dispatched to the buyer.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

            {/* Invoice metadata */}
            <div className="card" style={{ marginBottom: 0 }}>
              <div className="card-title">
                <FileText size={16} style={{ color: 'var(--indigo)' }} />
                Case Details — {selected.invoice_id}
              </div>
              <div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
                  {[
                    { label: 'Customer', value: selected.customer_name, icon: Building2 },
                    { label: 'Days Overdue', value: `${selected.days_late} days`, icon: CalendarClock },
                    { label: 'MSME Registered', value: selected.is_msme ? 'Yes' : 'No', icon: ShieldCheck },
                  ].map(({ label, value, icon: Icon }) => (
                    <div key={label} style={{ backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: '10px', padding: '1rem' }}>
                      <p style={{ margin: 0, fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</p>
                      <p style={{ margin: '0.4rem 0 0', fontWeight: 700, color: 'var(--text-primary)', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <Icon size={16} style={{ color: 'var(--indigo)' }} /> {value}
                      </p>
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: '1.25rem', padding: '1rem 1.25rem', backgroundColor: getRuleStyle(selected.tax_rule_triggered).bg, border: `1px solid ${getRuleStyle(selected.tax_rule_triggered).border}`, borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <AlertTriangle size={20} style={{ color: getRuleStyle(selected.tax_rule_triggered).color, flexShrink: 0 }} />
                  <div>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: getRuleStyle(selected.tax_rule_triggered).color, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Statutory Rule Triggered</span>
                    <p style={{ margin: '0.2rem 0 0', fontWeight: 700, fontSize: '1.05rem', color: getRuleStyle(selected.tax_rule_triggered).color }}>{selected.tax_rule_triggered}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Draft Email */}
            <div className="card" style={{ marginBottom: 0 }}>
              <div className="card-title" style={{ justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <Mail size={16} style={{ color: 'var(--indigo)' }} />
                  AI-Drafted Legal Notice
                </div>
                <span style={{ fontSize: '0.75rem', backgroundColor: 'var(--indigo-dim)', color: 'var(--indigo)', border: '1px solid rgba(129, 140, 248, 0.3)', borderRadius: '12px', padding: '2px 10px', fontWeight: 700 }}>
                  Groq / Llama 3 70B
                </span>
              </div>
              <div>
                <div style={{
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'var(--mono)',
                  fontSize: '0.88rem',
                  backgroundColor: 'rgba(0,0,0,0.2)',
                  padding: '1.5rem',
                  borderRadius: '12px',
                  border: '1px solid var(--border)',
                  lineHeight: 1.8,
                  maxHeight: '350px',
                  overflowY: 'auto',
                  color: 'var(--text-primary)'
                }}>
                  {selected.draft_email_body}
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            {selected.status === 'pending' && (
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                <button
                  className="btn"
                  disabled={actionLoading === selected.id}
                  onClick={() => handleAction(selected.id, 'rejected')}
                  style={{ border: '1px solid rgba(248, 113, 113, 0.3)', color: 'var(--red)', backgroundColor: 'var(--red-dim)', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 1.5rem' }}
                >
                  {actionLoading === selected.id ? <Loader2 size={16} className="spin" /> : <XCircle size={16} />}
                  Reject Draft
                </button>
                <button
                  className="btn primary"
                  disabled={actionLoading === selected.id}
                  onClick={() => handleAction(selected.id, 'approved')}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 1.5rem' }}
                >
                  {actionLoading === selected.id ? <Loader2 size={16} className="spin" /> : <CheckCircle2 size={16} />}
                  Approve & Dispatch Notice
                </button>
              </div>
            )}

            {selected.status !== 'pending' && (
              <div style={{
                padding: '1.25rem 1.5rem',
                backgroundColor: statusConfig[selected.status].bg,
                border: `1px solid ${statusConfig[selected.status].border}`,
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                color: statusConfig[selected.status].color,
                fontWeight: 600,
                marginTop: '0.5rem'
              }}>
                {selected.status === 'approved' ? <CheckCircle2 size={24} /> : <XCircle size={24} />}
                This notice has been {selected.status}. No further action is needed.
              </div>
            )}

          </div>
        )}
      </div>
    </div>
  );
}
