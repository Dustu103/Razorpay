'use client';

import { useState } from 'react';
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
      case 'auto_submit': return { bg: '#e6f4ea', text: '#137333', border: '#34a853', label: 'Auto Submit' };
      case 'one_tap_approval': return { bg: '#e8f0fe', text: '#1a73e8', border: '#4285f4', label: 'One-Tap Approve' };
      case 'deflect_via_refund': return { bg: '#fce8e6', text: '#c5221f', border: '#ea4335', label: 'Deflect (Refund)' };
      default: return { bg: '#fef7e0', text: '#b06000', border: '#fbbc04', label: 'Human Review' };
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '1rem 2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Scale className="icon purple" style={{ width: '28px', height: '28px' }} />
            AI Chargeback Pre-emption Pipeline
          </h1>
          <p style={{ color: '#64748b', marginTop: '0.25rem' }}>
            Multi-layer automated dispute triage, VAMP ratio defense, and compliance-optimized representment generation.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <div className="header-badge" style={{ backgroundColor: '#f1f5f9', color: '#475569', border: '1px solid #e2e8f0' }}>
            VAMP Guard Active
          </div>
          <div className="header-badge" style={{ backgroundColor: '#ede9fe', color: '#6d28d9', border: '1px solid #ddd6fe' }}>
            5-Model Ensemble
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '400px 1fr', gap: '2rem', alignItems: 'start' }}>
        
        {/* LEFT COLUMN: SCENARIO PARAMETERS INPUT */}
        <div className="simulator-panel" style={{ height: 'auto' }}>
          <div className="panel-header">
            <Sparkles size={18} className="icon purple" />
            <h3 style={{ margin: 0 }}>Dispute Simulator</h3>
          </div>
          
          <div className="panel-content" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            
            {/* Network selection */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.5rem' }}>CARD NETWORK</label>
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
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.5rem' }}>REASON CODE & POLICY RULE</label>
              <select 
                value={reasonCode}
                onChange={(e) => setReasonCode(e.target.value)}
                style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.9rem', backgroundColor: '#fff' }}
              >
                {reasonCodeOptions[network].map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            {/* Continuous Parameters */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>AMOUNT (INR)</label>
                <div style={{ position: 'relative' }}>
                  <span style={{ position: 'absolute', left: '8px', top: '8px', color: '#94a3b8', fontSize: '0.85rem' }}>₹</span>
                  <input 
                    type="number" 
                    value={amount} 
                    onChange={(e) => setAmount(Number(e.target.value))}
                    style={{ width: '100%', padding: '7px 8px 7px 20px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.9rem' }} 
                  />
                </div>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>DISPUTE RATIO</label>
                <input 
                  type="number" 
                  step="0.001"
                  value={disputeRatio} 
                  onChange={(e) => setDisputeRatio(Number(e.target.value))}
                  style={{ width: '100%', padding: '7px 8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.9rem' }} 
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>DAYS REMAINING</label>
                <input 
                  type="number" 
                  value={daysRemaining} 
                  onChange={(e) => setDaysRemaining(Number(e.target.value))}
                  style={{ width: '100%', padding: '7px 8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.9rem' }} 
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>REPEAT DISPUTES</label>
                <input 
                  type="number" 
                  value={repeatDisputes} 
                  onChange={(e) => setRepeatDisputes(Number(e.target.value))}
                  style={{ width: '100%', padding: '7px 8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.9rem' }} 
                />
              </div>
            </div>

            {/* Categorical details */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>DAYS SINCE TX</label>
                <input 
                  type="number" 
                  value={daysSinceTx} 
                  onChange={(e) => setDaysSinceTx(Number(e.target.value))}
                  style={{ width: '100%', padding: '7px 8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.9rem' }} 
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>MERCHANT CAT</label>
                <select
                  value={merchantCategory}
                  onChange={(e) => setMerchantCategory(e.target.value)}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.9rem', backgroundColor: '#fff' }}
                >
                  <option value="saas">SaaS</option>
                  <option value="ecommerce">Ecommerce</option>
                  <option value="retail">Retail</option>
                  <option value="travel">Travel</option>
                  <option value="fintech">Fintech</option>
                </select>
              </div>
            </div>

            {/* Evidence Checklist Switches */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.5rem' }}>EVIDENCE PRESENT</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={has3ds} onChange={(e) => setHas3ds(e.target.checked)} />
                  3D Secure (3DS) Authentication
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={hasDelivery} onChange={(e) => setHasDelivery(e.target.checked)} />
                  Proof of Delivery / Fulfillment
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={hasAvsCvv} onChange={(e) => setHasAvsCvv(e.target.checked)} />
                  AVS & CVV Match Verified
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={hasIpDevice} onChange={(e) => setHasIpDevice(e.target.checked)} />
                  IP & Device Fingerprint Matching
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={hasPriorComms} onChange={(e) => setHasPriorComms(e.target.checked)} />
                  Customer Support Communication
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={hasSignedReceipt} onChange={(e) => setHasSignedReceipt(e.target.checked)} />
                  Signed Receipt / Contract
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={hasUsageLogs} onChange={(e) => setHasUsageLogs(e.target.checked)} />
                  Digital Usage Logs / Consumption
                </label>
              </div>
            </div>

            <button className="btn primary" onClick={triggerAnalyze} disabled={loading} style={{ marginTop: '0.5rem', width: '100%', justifyContent: 'center' }}>
              {loading ? <Loader2 className="spin" size={16} /> : <Sparkles size={16} />}
              {loading ? 'Analyzing Pipeline...' : 'Run Pipeline Analysis'}
            </button>
            
          </div>
        </div>

        {/* RIGHT COLUMN: ANALYTICS & NARRATIVE DRAFT */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          
          {error && (
            <div style={{ padding: '1rem', backgroundColor: '#fee2e2', color: '#b91c1c', border: '1px solid #fca5a5', borderRadius: '8px', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <AlertTriangle size={20} />
              <div><strong>System Error:</strong> {error}</div>
            </div>
          )}

          {!result && !loading && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '6rem 2rem', border: '2px dashed #cbd5e1', borderRadius: '12px', textAlign: 'center', backgroundColor: '#f8fafc' }}>
              <Scale size={48} style={{ color: '#94a3b8', marginBottom: '1rem' }} />
              <h3 style={{ margin: 0, color: '#334155' }}>No Active Dispute Simulation</h3>
              <p style={{ color: '#64748b', fontSize: '0.9rem', maxWidth: '400px', marginTop: '0.5rem' }}>
                Select a card network, reason code, and available transaction evidence, then run the pipeline to start the triage analysis.
              </p>
            </div>
          )}

          {loading && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '6rem 2rem', border: '1px solid #e2e8f0', borderRadius: '12px', backgroundColor: '#ffffff' }}>
              <Loader2 className="spin" size={40} style={{ color: 'var(--purple)', marginBottom: '1rem' }} />
              <h3 style={{ margin: 0 }}>Executing Pipeline Orchestration</h3>
              <p style={{ color: '#64748b', fontSize: '0.9rem', marginTop: '0.5rem' }}>
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
                  borderRadius: '10px'
                }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Recommended Action</span>
                  <h2 style={{ fontSize: '1.7rem', fontWeight: 800, margin: '0.25rem 0' }}>
                    {getActionColor(result.recommended_action).label}
                  </h2>
                  <p style={{ fontSize: '0.85rem', opacity: 0.9, margin: 0 }}>
                    {result.recommended_action === 'auto_submit' ? 'Ensemble predicts a high win probability. Auto-submitting to the bank.' :
                     result.recommended_action === 'deflect_via_refund' ? 'Dispute lacks necessary evidence. Deflecting via instant refund to protect VAMP metrics.' :
                     result.recommended_action === 'one_tap_approval' ? 'Ensemble predicts a moderate win probability. Approved with one-tap merchant review.' :
                     'Disagreement or high variance in models. Awaiting manual reviewer approval.'}
                  </p>
                </div>

                {/* Win Probability Card */}
                <div style={{ 
                  backgroundColor: '#ffffff', 
                  border: '1px solid #e2e8f0',
                  padding: '1.25rem',
                  borderRadius: '10px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center'
                }}>
                  <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Win Probability</span>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem', margin: '0.25rem 0' }}>
                    <span style={{ fontSize: '2rem', fontWeight: 800, color: '#0f172a' }}>
                      {(result.win_probability * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div style={{ width: '100%', height: '6px', backgroundColor: '#f1f5f9', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${result.win_probability * 100}%`, height: '100%', backgroundColor: result.win_probability >= 0.70 ? '#10b981' : result.win_probability >= 0.40 ? '#3b82f6' : '#ef4444' }} />
                  </div>
                </div>

                {/* Model Variance / Disagreement Card */}
                <div style={{ 
                  backgroundColor: '#ffffff', 
                  border: '1px solid #e2e8f0',
                  padding: '1.25rem',
                  borderRadius: '10px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center'
                }}>
                  <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Ensemble Variance</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: '0.25rem 0' }}>
                    <span style={{ fontSize: '2rem', fontWeight: 800, color: result.disagreement_flag ? '#ef4444' : '#0f172a' }}>
                      {result.variance.toFixed(4)}
                    </span>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: result.disagreement_flag ? '#ef4444' : '#10b981', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
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
                  backgroundColor: result.vamp_advisory.status === 'high_risk' ? '#fffbeb' : '#f0fdf4',
                  border: `1px solid ${result.vamp_advisory.status === 'high_risk' ? '#fde68a' : '#bbf7d0'}`,
                  borderRadius: '8px',
                  padding: '1rem',
                  display: 'flex',
                  gap: '0.75rem',
                  alignItems: 'start'
                }}>
                  {result.vamp_advisory.status === 'high_risk' ? (
                    <AlertTriangle style={{ color: '#d97706', flexShrink: 0, marginTop: '0.1rem' }} />
                  ) : (
                    <ShieldCheck style={{ color: '#16a34a', flexShrink: 0, marginTop: '0.1rem' }} />
                  )}
                  <div>
                    <h4 style={{ margin: 0, color: result.vamp_advisory.status === 'high_risk' ? '#92400e' : '#166534', fontSize: '0.9rem', fontWeight: 700 }}>
                      VAMP Compliance Advisory ({result.vamp_advisory.status.toUpperCase()})
                    </h4>
                    <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem', color: result.vamp_advisory.status === 'high_risk' ? '#b45309' : '#15803d' }}>
                      {result.vamp_advisory.message}
                    </p>
                  </div>
                </div>
              )}

              {/* DETAILED ML MODEL BREAKDOWN */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                
                {/* 5-Model Probabilities List */}
                <div style={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '1.25rem' }}>
                  <h4 style={{ margin: '0 0 1rem 0', fontSize: '0.9rem', color: '#334155', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Info size={16} /> 5-Model Ensemble Predictions
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {Object.entries(result.individual_predictions).map(([modelName, prob]: any) => (
                      <div key={modelName}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#475569', marginBottom: '0.25rem' }}>
                          <span>{modelName}</span>
                          <span style={{ fontWeight: 600 }}>{(prob * 100).toFixed(1)}%</span>
                        </div>
                        <div style={{ width: '100%', height: '4px', backgroundColor: '#f1f5f9', borderRadius: '2px', overflow: 'hidden' }}>
                          <div style={{ width: `${prob * 100}%`, height: '100%', backgroundColor: '#6d28d9' }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Top SHAP Features and Routing */}
                <div style={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div>
                    <h4 style={{ margin: '0 0 1rem 0', fontSize: '0.9rem', color: '#334155', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Sparkles size={16} /> Top Contributing Features (SHAP)
                    </h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                      {result.top_features.map((feat: string) => (
                        <span key={feat} className="badge" style={{ backgroundColor: '#ede9fe', color: '#6d28d9', fontSize: '0.75rem', padding: '4px 10px', borderRadius: '12px', border: '1px solid #ddd6fe' }}>
                          {feat.replace('has_', '').replace('_', ' ')}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '1rem', marginTop: '1rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#64748b' }}>COST-AWARE LLM ROUTING PATH</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.25rem' }}>
                      <strong style={{ fontSize: '0.9rem', color: '#0f172a' }}>{result.routing_path}</strong>
                      <span className="badge" style={{ fontSize: '0.75rem', backgroundColor: result.llm_confidence === 'high' ? '#e2f0d9' : '#fff2cc', color: result.llm_confidence === 'high' ? '#385723' : '#7f6000' }}>
                        {result.llm_confidence.toUpperCase()} CONFIDENCE
                      </span>
                    </div>
                  </div>
                </div>

              </div>

              {/* POST-GENERATION HALLUCINATION SCRUB REPORT */}
              {result.redacted_artifacts && result.redacted_artifacts.length > 0 && (
                <div style={{ backgroundColor: '#fff1f2', border: '1px solid #fecdd3', borderRadius: '8px', padding: '1rem' }}>
                  <h4 style={{ margin: '0 0 0.5rem 0', color: '#9f1239', fontSize: '0.85rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <ShieldAlert size={16} /> Layer 4 Guardrail: Redacted Compliance Hallucinations
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.8rem', color: '#be123c' }}>
                    {result.redacted_artifacts.map((red: string, idx: number) => (
                      <li key={idx}>{red}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* NARRATIVE EDITOR & ACTION CONTROLS */}
              <div className="simulator-panel" style={{ height: 'auto' }}>
                <div className="panel-header" style={{ justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FileText size={18} className="icon purple" />
                    <h3 style={{ margin: 0 }}>Representment Narrative Rebuttal</h3>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button 
                      className="btn text" 
                      onClick={() => setIsEditing(!isEditing)}
                      style={{ padding: '4px 8px', fontSize: '0.8rem' }}
                    >
                      <Edit3 size={14} />
                      {isEditing ? 'Cancel Edit' : 'Edit Narrative'}
                    </button>
                    <button 
                      className="btn text" 
                      onClick={copyToClipboard}
                      style={{ padding: '4px 8px', fontSize: '0.8rem' }}
                    >
                      {copied ? <Check size={14} style={{ color: '#10b981' }} /> : <Copy size={14} />}
                      {copied ? 'Copied!' : 'Copy to Clipboard'}
                    </button>
                  </div>
                </div>

                <div className="panel-content">
                  {isEditing ? (
                    <textarea 
                      className="json-textarea"
                      value={editedNarrative}
                      onChange={(e) => setEditedNarrative(e.target.value)}
                      rows={14}
                      style={{ fontFamily: 'monospace', fontSize: '0.9rem', width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                    />
                  ) : (
                    <div style={{ 
                      whiteSpace: 'pre-wrap', 
                      fontFamily: 'monospace', 
                      fontSize: '0.9rem', 
                      backgroundColor: '#f8fafc', 
                      padding: '1.25rem', 
                      borderRadius: '8px', 
                      border: '1px solid #e2e8f0',
                      maxHeight: '350px',
                      overflowY: 'auto'
                    }}>
                      {editedNarrative}
                    </div>
                  )}

                  {/* Assist-Not-Decide Merchant Approval Workflow */}
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1.5rem', borderTop: '1px solid #f1f5f9', paddingTop: '1.25rem' }}>
                    <button 
                      className="btn" 
                      onClick={() => {
                        setEditedNarrative(result.narrative);
                        setIsEditing(false);
                      }} 
                      style={{ border: '1px solid #cbd5e1' }}
                    >
                      <RotateCcw size={14} /> Reset Narrative
                    </button>
                    
                    <button 
                      className={`btn ${approved ? 'success' : 'primary'}`} 
                      disabled={approved}
                      onClick={() => setApproved(true)}
                      style={{
                        backgroundColor: approved ? '#10b981' : 'var(--purple)',
                        color: '#fff',
                        fontWeight: 600
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
