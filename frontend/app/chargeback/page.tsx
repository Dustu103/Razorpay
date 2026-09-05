'use client';

import { useState, useEffect } from 'react';
import { 
  Loader2, 
  ShieldCheck, 
  ShieldAlert, 
  Scale, 
  ChevronRight, 
  Edit3, 
  Copy, 
  Check, 
  AlertTriangle,
  RotateCcw,
  Sparkles,
  Info,
  DollarSign,
  FileText
} from 'lucide-react';

export default function ChargebackPreemptionPage() {
  // Input form state
  const [network, setNetwork] = useState('visa');
  const [reasonCode, setReasonCode] = useState('visa_10.4');
  const [has3ds, setHas3ds] = useState(true);
  const [hasDelivery, setHasDelivery] = useState(true);
  const [hasAvsCvv, setHasAvsCvv] = useState(true);
  const [hasIpDevice, setHasIpDevice] = useState(true);
  const [hasPriorComms, setHasPriorComms] = useState(false);
  const [hasSignedReceipt, setHasSignedReceipt] = useState(false);
  const [hasUsageLogs, setHasUsageLogs] = useState(false);
  const [daysRemaining, setDaysRemaining] = useState(12);
  const [daysSinceTx, setDaysSinceTx] = useState(15);
  const [repeatDisputes, setRepeatDisputes] = useState(0);
  const [amount, setAmount] = useState(4500.0);
  const [merchantCategory, setMerchantCategory] = useState('saas');
  const [disputeRatio, setDisputeRatio] = useState(0.008); // 0.8%

  // Output response state
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  
  // UI helpers
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedNarrative, setEditedNarrative] = useState('');
  const [approved, setApproved] = useState(false);

  // Track 03 — Batch summary state (Gap 1)
  const [batchSummary, setBatchSummary] = useState<any>(null);
  useEffect(() => {
    fetch('http://localhost:3005/api/v1/batch-summary')
      .then(r => r.json())
      .then(setBatchSummary)
      .catch(() => {});
  }, []);

  // Network reason codes mapping for UI selection
  const reasonCodeOptions: Record<string, { value: string; label: string }[]> = {
    visa: [
      { value: 'visa_10.4', label: '10.4 - Other Fraud (Card Absent)' },
      { value: 'visa_13.1', label: '13.1 - Merchandise/Services Not Received' },
      { value: 'visa_13.3', label: '13.3 - Not as Described or Defective' }
    ],
    mastercard: [
      { value: 'mc_4837', label: '4837 - No Cardholder Authorization' },
      { value: 'mc_4853', label: '4853 - Cardholder Dispute (Not Provided)' },
      { value: 'mc_4808', label: '4808 - Authorization-Related Chargeback' }
    ],
    rupay: [
      { value: 'rupay_ru01', label: 'RU01 - Unauthorized Transaction' },
      { value: 'rupay_ru02', label: 'RU02 - Goods/Services Not Received' },
      { value: 'rupay_ru03', label: 'RU03 - Duplicate Transaction' },
      { value: 'rupay_1062', label: '1062 - Goods/Services Not as Described' },
      { value: 'rupay_1064', label: '1064 - Goods/Services Not Provided' },
      { value: 'rupay_1065', label: '1065 - Account Debited, Confirmation Not Recv' },
      { value: 'rupay_1085', label: '1085 - Charged More Than Transaction Amt' }
    ]
  };

  const handleNetworkChange = (net: string) => {
    setNetwork(net);
    setReasonCode(reasonCodeOptions[net][0].value);
  };

  const triggerAnalyze = async () => {
    setLoading(true);
    setError('');
    setResult(null);
    setApproved(false);
    setIsEditing(false);

    const payload = {
      reason_code: reasonCode,
      network: network,
      has_3ds_auth: has3ds ? 1 : 0,
      has_delivery_proof: hasDelivery ? 1 : 0,
      has_avs_cvv_match: hasAvsCvv ? 1 : 0,
      has_ip_device_fingerprint: hasIpDevice ? 1 : 0,
      has_prior_comms: hasPriorComms ? 1 : 0,
      has_signed_receipt: hasSignedReceipt ? 1 : 0,
      has_usage_logs: hasUsageLogs ? 1 : 0,
      days_remaining: Number(daysRemaining),
      days_since_transaction: Number(daysSinceTx),
      repeat_dispute_count: Number(repeatDisputes),
      transaction_amount_inr: Number(amount),
      merchant_category: merchantCategory,
      merchant_current_dispute_ratio: Number(disputeRatio)
    };

    try {
      const res = await fetch('http://localhost:3005/api/v1/analyze-dispute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error(`API returned ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();
      setResult(data);
      setEditedNarrative(data.narrative);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to the chargeback service');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(editedNarrative);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'auto_submit':          return { bg: 'var(--green-dim)',  text: 'var(--green)',  border: 'rgba(52, 211, 153, 0.3)',  label: 'Auto Submit' };
      case 'one_tap_approval':     return { bg: 'var(--indigo-dim)', text: 'var(--indigo)', border: 'rgba(129, 140, 248, 0.3)', label: 'One-Tap Approve' };
      case 'deflect_via_refund':   return { bg: 'var(--red-dim)',    text: 'var(--red)',    border: 'rgba(248, 113, 113, 0.3)', label: 'Deflect (Refund)' };
      case 'instant_deflect':      return { bg: 'var(--red-dim)',    text: 'var(--red)',    border: 'rgba(248, 113, 113, 0.3)', label: 'Instant Deflect' };
      case 'escalate_to_specialist': return { bg: 'var(--amber-dim)', text: 'var(--amber)', border: 'rgba(251, 191, 36, 0.3)',   label: 'Escalate to Specialist' };
      default: return { bg: 'var(--amber-dim)', text: 'var(--amber)', border: 'rgba(251, 191, 36, 0.3)', label: 'Human Review' };
    }
  };

  // Reusable input styling for dark mode
  const inputStyle = {
    width: '100%',
    padding: '8px 12px',
    borderRadius: '8px',
    border: '1px solid var(--border)',
    fontSize: '0.9rem',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font)'
  };
  const labelStyle = { display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.4rem', textTransform: 'uppercase' as const, letterSpacing: '0.05em' };

  return (
    <div style={{ maxWidth: '1320px', margin: '0 auto', padding: '1rem 2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2.5rem' }}>
        <div>
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Scale size={32} style={{ color: 'var(--purple)' }} />
            AI Chargeback Pre-emption Pipeline
          </h1>
          <p className="page-sub" style={{ marginTop: '0.5rem', maxWidth: '650px' }}>
            Multi-layer automated dispute triage, VAMP ratio defense, and compliance-optimized representment generation.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <div className="badge" style={{ backgroundColor: 'var(--green-dim)', color: 'var(--green)', border: '1px solid rgba(52, 211, 153, 0.3)' }}>
            VAMP Guard Active
          </div>
          <div className="badge" style={{ backgroundColor: 'var(--purple-dim)', color: 'var(--purple)', border: '1px solid rgba(192, 132, 252, 0.3)' }}>
            5-Model Ensemble
          </div>
        </div>
      </div>

      {/* Track 03 — Batch Recovery Stats Banner */}
      {batchSummary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', marginBottom: '2rem', padding: '1.25rem', background: 'linear-gradient(135deg, rgba(139,92,246,0.08) 0%, rgba(16,185,129,0.06) 100%)', borderRadius: '12px', border: '1px solid rgba(139,92,246,0.2)' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, marginBottom: '4px' }}>50-Dispute Batch Processed</div>
            <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--text)' }}>{batchSummary.total_disputes}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Visa · MC · RuPay</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, marginBottom: '4px' }}>Est. Revenue Recovered</div>
            <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--green)' }}>₹{(batchSummary.estimated_recovered_inr/1000).toFixed(0)}K</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>of ₹{(batchSummary.total_dispute_value_inr/1000).toFixed(0)}K at risk</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, marginBottom: '4px' }}>Our Recovery Rate</div>
            <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--indigo)' }}>{batchSummary.your_recovery_rate}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>vs 6.7% national avg</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, marginBottom: '4px' }}>Arbitration Fees Saved</div>
            <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--amber)' }}>₹{(batchSummary.estimated_arbitration_fees_saved_inr/1000).toFixed(1)}K</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>by smart deflection</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, marginBottom: '4px' }}>Escalated to Specialist</div>
            <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--purple)' }}>{batchSummary.escalated_to_specialist}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>High-value / repeat abuse</div>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '400px 1fr', gap: '2rem', alignItems: 'start' }}>
        
        {/* LEFT COLUMN: SCENARIO PARAMETERS INPUT */}
        <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
          <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Sparkles size={18} style={{ color: 'var(--purple)' }} />
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Dispute Simulator</h3>
          </div>
          
          <div style={{ padding: '1.25rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            
            {/* Network selection */}
            <div>
              <label style={labelStyle}>CARD NETWORK</label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
                {['visa', 'mastercard', 'rupay'].map(net => (
                  <button 
                    key={net} 
                    className={`btn ${network === net ? 'primary' : ''}`} 
                    style={{ fontSize: '0.8rem', padding: '6px', textTransform: 'capitalize' }}
                    onClick={() => handleNetworkChange(net)}
                  >
                    {net}
                  </button>
                ))}
              </div>
            </div>

            {/* Reason code selection */}
            <div>
              <label style={labelStyle}>REASON CODE & POLICY RULE</label>
              <select 
                value={reasonCode}
                onChange={(e) => setReasonCode(e.target.value)}
                style={inputStyle}
              >
                {reasonCodeOptions[network].map(opt => (
                  <option key={opt.value} value={opt.value} style={{ background: 'var(--bg-2)' }}>{opt.label}</option>
                ))}
              </select>
            </div>

            {/* Continuous Parameters */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label style={labelStyle}>AMOUNT (INR)</label>
                <div style={{ position: 'relative' }}>
                  <span style={{ position: 'absolute', left: '10px', top: '9px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>₹</span>
                  <input 
                    type="number" 
                    value={amount} 
                    onChange={(e) => setAmount(Number(e.target.value))}
                    style={{ ...inputStyle, paddingLeft: '24px' }} 
                  />
                </div>
              </div>
              <div>
                <label style={labelStyle}>DISPUTE RATIO</label>
                <input 
                  type="number" 
                  step="0.001"
                  value={disputeRatio} 
                  onChange={(e) => setDisputeRatio(Number(e.target.value))}
                  style={inputStyle} 
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label style={labelStyle}>DAYS REMAINING</label>
                <input 
                  type="number" 
                  value={daysRemaining} 
                  onChange={(e) => setDaysRemaining(Number(e.target.value))}
                  style={inputStyle} 
                />
              </div>
              <div>
                <label style={labelStyle}>REPEAT DISPUTES</label>
                <input 
                  type="number" 
                  value={repeatDisputes} 
                  onChange={(e) => setRepeatDisputes(Number(e.target.value))}
                  style={inputStyle} 
                />
              </div>
            </div>

            {/* Categorical details */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label style={labelStyle}>DAYS SINCE TX</label>
                <input 
                  type="number" 
                  value={daysSinceTx} 
                  onChange={(e) => setDaysSinceTx(Number(e.target.value))}
                  style={inputStyle} 
                />
              </div>
              <div>
                <label style={labelStyle}>MERCHANT CAT</label>
                <select
                  value={merchantCategory}
                  onChange={(e) => setMerchantCategory(e.target.value)}
                  style={inputStyle}
                >
                  <option value="saas" style={{ background: 'var(--bg-2)' }}>SaaS</option>
                  <option value="ecommerce" style={{ background: 'var(--bg-2)' }}>Ecommerce</option>
                  <option value="retail" style={{ background: 'var(--bg-2)' }}>Retail</option>
                  <option value="travel" style={{ background: 'var(--bg-2)' }}>Travel</option>
                  <option value="fintech" style={{ background: 'var(--bg-2)' }}>Fintech</option>
                </select>
              </div>
            </div>

            {/* Evidence Checklist Switches */}
            <div>
              <label style={labelStyle}>EVIDENCE PRESENT</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.85rem', cursor: 'pointer', color: 'var(--text-primary)' }}>
                  <input type="checkbox" checked={has3ds} onChange={(e) => setHas3ds(e.target.checked)} style={{ accentColor: 'var(--purple)' }} />
                  3D Secure (3DS) Authentication
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.85rem', cursor: 'pointer', color: 'var(--text-primary)' }}>
                  <input type="checkbox" checked={hasDelivery} onChange={(e) => setHasDelivery(e.target.checked)} style={{ accentColor: 'var(--purple)' }} />
                  Proof of Delivery / Fulfillment
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.85rem', cursor: 'pointer', color: 'var(--text-primary)' }}>
                  <input type="checkbox" checked={hasAvsCvv} onChange={(e) => setHasAvsCvv(e.target.checked)} style={{ accentColor: 'var(--purple)' }} />
                  AVS & CVV Match Verified
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.85rem', cursor: 'pointer', color: 'var(--text-primary)' }}>
                  <input type="checkbox" checked={hasIpDevice} onChange={(e) => setHasIpDevice(e.target.checked)} style={{ accentColor: 'var(--purple)' }} />
                  IP & Device Fingerprint Matching
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.85rem', cursor: 'pointer', color: 'var(--text-primary)' }}>
                  <input type="checkbox" checked={hasPriorComms} onChange={(e) => setHasPriorComms(e.target.checked)} style={{ accentColor: 'var(--purple)' }} />
                  Customer Support Communication
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.85rem', cursor: 'pointer', color: 'var(--text-primary)' }}>
                  <input type="checkbox" checked={hasSignedReceipt} onChange={(e) => setHasSignedReceipt(e.target.checked)} style={{ accentColor: 'var(--purple)' }} />
                  Signed Receipt / Contract
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.85rem', cursor: 'pointer', color: 'var(--text-primary)' }}>
                  <input type="checkbox" checked={hasUsageLogs} onChange={(e) => setHasUsageLogs(e.target.checked)} style={{ accentColor: 'var(--purple)' }} />
                  Digital Usage Logs / Consumption
                </label>
              </div>
            </div>

            <button className="btn primary" onClick={triggerAnalyze} disabled={loading} style={{ marginTop: '0.5rem', width: '100%', justifyContent: 'center', padding: '0.75rem', backgroundColor: 'var(--purple)' }}>
              {loading ? <Loader2 className="spin" size={16} /> : <Sparkles size={16} />}
              {loading ? 'Analyzing Pipeline...' : 'Run Pipeline Analysis'}
            </button>
            
          </div>
        </div>

        {/* RIGHT COLUMN: ANALYTICS & NARRATIVE DRAFT */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {error && (
            <div style={{ padding: '1rem', backgroundColor: 'var(--red-dim)', color: 'var(--red)', border: '1px solid rgba(248, 113, 113, 0.3)', borderRadius: '10px', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
              <AlertTriangle size={20} />
              <div><strong>System Error:</strong> {error}</div>
            </div>
          )}

          {!result && !loading && (
            <div className="empty-state" style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', backgroundColor: 'var(--bg-card)' }}>
              <Scale size={48} className="empty-icon" style={{ color: 'var(--purple)' }} />
              <h3 className="empty-title">No Active Dispute Simulation</h3>
              <p className="empty-sub">
                Select a card network, reason code, and available transaction evidence, then run the pipeline to start the triage analysis.
              </p>
            </div>
          )}

          {loading && (
            <div className="empty-state" style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', backgroundColor: 'var(--bg-card)' }}>
              <Loader2 className="spin" size={40} style={{ color: 'var(--purple)', marginBottom: '1rem' }} />
              <h3 className="empty-title">Executing Pipeline Orchestration</h3>
              <p className="empty-sub">
                Layer 1: Deterministic rules checking • Layer 2: 5-model ensemble evaluation • Layer 3: Context bridge & LLM routing
              </p>
            </div>
          )}

          {result && !loading && (
            <>
              {/* TOP SUMMARY CARDS */}
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '1rem' }}>
                
                {/* Recommended Action Card */}
                <div style={{ 
                  backgroundColor: getActionColor(result.recommended_action).bg, 
                  color: getActionColor(result.recommended_action).text, 
                  border: `1px solid ${getActionColor(result.recommended_action).border}`,
                  padding: '1.25rem',
                  borderRadius: '12px'
                }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Recommended Action</span>
                  <h2 style={{ fontSize: '1.7rem', fontWeight: 800, margin: '0.25rem 0' }}>
                    {getActionColor(result.recommended_action).label}
                  </h2>
                  <p style={{ fontSize: '0.85rem', opacity: 0.9, margin: 0, color: 'var(--text-primary)' }}>
                    {result.recommended_action === 'auto_submit' ? 'Ensemble predicts a high win probability. Auto-submitting to the bank.' :
                     result.recommended_action === 'deflect_via_refund' ? 'Dispute lacks necessary evidence. Deflecting via instant refund to protect VAMP metrics.' :
                     result.recommended_action === 'one_tap_approval' ? 'Ensemble predicts a moderate win probability. Approved with one-tap merchant review.' :
                     'Disagreement or high variance in models. Awaiting manual reviewer approval.'}
                  </p>
                </div>

                {/* Win Probability Card */}
                <div className="card" style={{ marginBottom: 0, padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Win Probability</span>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem', margin: '0.25rem 0' }}>
                    <span style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                      {(result.win_probability * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div style={{ width: '100%', height: '6px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${result.win_probability * 100}%`, height: '100%', backgroundColor: result.win_probability >= 0.70 ? 'var(--green)' : result.win_probability >= 0.40 ? 'var(--blue)' : 'var(--red)' }} />
                  </div>
                </div>

                {/* Model Variance / Disagreement Card */}
                <div className="card" style={{ marginBottom: 0, padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Ensemble Variance</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: '0.25rem 0' }}>
                    <span style={{ fontSize: '2rem', fontWeight: 800, color: result.disagreement_flag ? 'var(--red)' : 'var(--text-primary)' }}>
                      {result.variance.toFixed(4)}
                    </span>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: result.disagreement_flag ? 'var(--red)' : 'var(--green)', display: 'flex', alignItems: 'center', gap: '0.25rem', fontWeight: 600 }}>
                    {result.disagreement_flag ? (
                      <><AlertTriangle size={12} /> Disagreement Flagged</>
                    ) : (
                      <><ShieldCheck size={12} /> Consensus Acquired</>
                    )}
                  </span>
                </div>

              </div>

              {/* VAMP RATIO RISK WARNING */}
              {result.vamp_advisory && (
                <div style={{ 
                  backgroundColor: result.vamp_advisory.status === 'high_risk' ? 'var(--amber-dim)' : 'var(--green-dim)',
                  border: `1px solid ${result.vamp_advisory.status === 'high_risk' ? 'rgba(251, 191, 36, 0.3)' : 'rgba(52, 211, 153, 0.3)'}`,
                  borderRadius: '10px',
                  padding: '1.25rem',
                  display: 'flex',
                  gap: '1rem',
                  alignItems: 'start'
                }}>
                  {result.vamp_advisory.status === 'high_risk' ? (
                    <AlertTriangle style={{ color: 'var(--amber)', flexShrink: 0, marginTop: '0.1rem' }} />
                  ) : (
                    <ShieldCheck style={{ color: 'var(--green)', flexShrink: 0, marginTop: '0.1rem' }} />
                  )}
                  <div>
                    <h4 style={{ margin: 0, color: result.vamp_advisory.status === 'high_risk' ? 'var(--amber)' : 'var(--green)', fontSize: '0.9rem', fontWeight: 700 }}>
                      VAMP Compliance Advisory ({result.vamp_advisory.status.toUpperCase()})
                    </h4>
                    <p style={{ margin: '0.4rem 0 0 0', fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                      {result.vamp_advisory.message}
                    </p>
                  </div>
                </div>
              )}

              {/* DETAILED ML MODEL BREAKDOWN */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                
                {/* 5-Model Probabilities List */}
                <div className="card" style={{ marginBottom: 0, padding: '1.5rem' }}>
                  <h4 style={{ margin: '0 0 1.25rem 0', fontSize: '0.9rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <Info size={16} style={{ color: 'var(--purple)' }} /> 5-Model Ensemble Predictions
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {Object.entries(result.individual_predictions).map(([modelName, prob]: any) => (
                      <div key={modelName}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
                          <span>{modelName}</span>
                          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{(prob * 100).toFixed(1)}%</span>
                        </div>
                        <div style={{ width: '100%', height: '6px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ width: `${prob * 100}%`, height: '100%', backgroundColor: 'var(--purple)' }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Top SHAP Features and Routing */}
                <div className="card" style={{ marginBottom: 0, padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div>
                    <h4 style={{ margin: '0 0 1.25rem 0', fontSize: '0.9rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <Sparkles size={16} style={{ color: 'var(--purple)' }} /> Top Contributing Features (SHAP)
                    </h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                      {result.top_features.map((feat: string) => (
                        <span key={feat} className="badge" style={{ backgroundColor: 'var(--purple-dim)', color: 'var(--purple)', fontSize: '0.75rem', padding: '4px 10px', borderRadius: '12px', border: '1px solid rgba(192, 132, 252, 0.3)' }}>
                          {feat.replace('has_', '').replace('_', ' ')}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1.25rem', marginTop: '1.25rem' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>COST-AWARE LLM ROUTING PATH</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
                      <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>{result.routing_path}</strong>
                      <span className="badge" style={{ fontSize: '0.75rem', backgroundColor: result.llm_confidence === 'high' ? 'var(--green-dim)' : 'var(--amber-dim)', color: result.llm_confidence === 'high' ? 'var(--green)' : 'var(--amber)', border: `1px solid ${result.llm_confidence === 'high' ? 'rgba(52, 211, 153, 0.3)' : 'rgba(251, 191, 36, 0.3)'}` }}>
                        {result.llm_confidence.toUpperCase()} CONFIDENCE
                      </span>
                    </div>
                  </div>
                </div>

              </div>

              {/* POST-GENERATION HALLUCINATION SCRUB REPORT */}
              {result.redacted_artifacts && result.redacted_artifacts.length > 0 && (
                <div style={{ backgroundColor: 'var(--red-dim)', border: '1px solid rgba(248, 113, 113, 0.3)', borderRadius: '10px', padding: '1.25rem' }}>
                  <h4 style={{ margin: '0 0 0.75rem 0', color: 'var(--red)', fontSize: '0.9rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <ShieldAlert size={16} /> Layer 4 Guardrail: Redacted Compliance Hallucinations
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--red)' }}>
                    {result.redacted_artifacts.map((red: string, idx: number) => (
                      <li key={idx} style={{ marginBottom: '0.25rem' }}>{red}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* NARRATIVE EDITOR & ACTION CONTROLS */}
              <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <FileText size={18} style={{ color: 'var(--purple)' }} />
                    <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Representment Narrative Rebuttal</h3>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button 
                      className="btn" 
                      onClick={() => setIsEditing(!isEditing)}
                      style={{ padding: '6px 12px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                    >
                      <Edit3 size={14} />
                      {isEditing ? 'Cancel Edit' : 'Edit Narrative'}
                    </button>
                    <button 
                      className="btn" 
                      onClick={copyToClipboard}
                      style={{ padding: '6px 12px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                    >
                      {copied ? <Check size={14} style={{ color: 'var(--green)' }} /> : <Copy size={14} />}
                      {copied ? 'Copied!' : 'Copy to Clipboard'}
                    </button>
                  </div>
                </div>

                <div style={{ padding: '1.5rem' }}>
                  {isEditing ? (
                    <textarea 
                      value={editedNarrative}
                      onChange={(e) => setEditedNarrative(e.target.value)}
                      rows={14}
                      style={{ fontFamily: 'var(--mono)', fontSize: '0.9rem', width: '100%', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border)', backgroundColor: 'rgba(0,0,0,0.2)', color: 'var(--text-primary)', outline: 'none' }}
                    />
                  ) : (
                    <div style={{ 
                      whiteSpace: 'pre-wrap', 
                      fontFamily: 'var(--mono)', 
                      fontSize: '0.9rem', 
                      backgroundColor: 'rgba(0,0,0,0.2)', 
                      padding: '1.5rem', 
                      borderRadius: '12px', 
                      border: '1px solid var(--border)',
                      maxHeight: '350px',
                      overflowY: 'auto',
                      color: 'var(--text-primary)',
                      lineHeight: 1.8
                    }}>
                      {editedNarrative}
                    </div>
                  )}

                  {/* Assist-Not-Decide Merchant Approval Workflow */}
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1.5rem', borderTop: '1px solid var(--border)', paddingTop: '1.5rem' }}>
                    <button 
                      className="btn" 
                      onClick={() => {
                        setEditedNarrative(result.narrative);
                        setIsEditing(false);
                      }} 
                      style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                    >
                      <RotateCcw size={14} /> Reset Narrative
                    </button>
                    
                    <button 
                      className={`btn primary`} 
                      disabled={approved}
                      onClick={() => setApproved(true)}
                      style={{
                        backgroundColor: approved ? 'var(--green)' : 'var(--purple)',
                        borderColor: 'transparent',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem'
                      }}
                    >
                      <ShieldCheck size={16} />
                      {approved ? 'Representment Approved & Submitted!' : 'Approve & Submit Representment'}
                    </button>
                  </div>

                </div>
              </div>

            </>
          )}

        </div>

      </div>
    </div>
  );
}
