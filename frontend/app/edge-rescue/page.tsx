'use client';

import { useState } from 'react';
import { 
  CreditCard, 
  Zap, 
  Clock, 
  TrendingUp, 
  CheckCircle2, 
  XCircle, 
  ShieldCheck, 
  Send, 
  Sparkles,
  ArrowRight,
  Split
} from 'lucide-react';
import { evaluateEdgeRescue } from '@/app/actions';
import MockCheckoutModal from '@/components/MockCheckoutModal';

export default function EdgeRescuePage() {
  const [amount, setAmount] = useState(6499);
  const [declineReason, setDeclineReason] = useState(1); // 1 = Insufficient balance
  const [tenureMonths, setTenureMonths] = useState(3);
  const [evaluating, setEvaluating] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [showCheckoutModal, setShowCheckoutModal] = useState(false);

  const handleTestEdge = async (e: React.FormEvent) => {
    e.preventDefault();
    setEvaluating(true);
    const start = performance.now();
    try {
      const res = await evaluateEdgeRescue({
        amount,
        decline_reason_encoded: declineReason,
        tenure_months: tenureMonths,
      });
      const end = performance.now();
      setLatencyMs(Math.round(end - start));
      if (res.success && res.data) {
        setResult(res.data);
      }
    } catch (err) {
      console.error('Edge evaluation failed:', err);
    } finally {
      setEvaluating(false);
    }
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  };

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '1rem 0 3rem' }}>
      {/* Header */}
      <div className="page-header" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                background: 'rgba(192, 132, 252, 0.15)',
                border: '1px solid rgba(192, 132, 252, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <CreditCard size={20} style={{ color: 'var(--purple)' }} />
              </div>
              <h1 className="page-title" style={{ margin: 0 }}>BNPL Edge Checkout Rescue</h1>
              <span style={{
                fontSize: '0.72rem',
                fontFamily: 'var(--mono)',
                padding: '3px 8px',
                borderRadius: '6px',
                background: 'rgba(192, 132, 252, 0.12)',
                color: 'var(--purple)',
                border: '1px solid rgba(192, 132, 252, 0.25)',
                fontWeight: 600
              }}>
                Pillar 5 · Go Edge Service (:8003)
              </span>
            </div>
            <p className="page-sub" style={{ marginTop: '0.35rem' }}>
              When a customer's debit card or UPI transaction suffers a hard decline (insufficient funds), backend retries are futile. The BNPL Edge proxy intercepts the decline in &lt;50ms and dynamically injects a split-payment EMI offer on-screen before the customer bounces.
            </p>
          </div>

          <button
            onClick={() => setShowCheckoutModal(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '8px 18px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, var(--purple), var(--indigo))',
              color: '#FFF',
              fontWeight: 600,
              fontSize: '0.85rem',
              border: 'none',
              cursor: 'pointer',
              boxShadow: '0 4px 16px rgba(192, 132, 252, 0.3)'
            }}
          >
            <span>Launch Live Razorpay Checkout Demo</span>
            <ArrowRight size={15} />
          </button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="stats-row" style={{ marginBottom: '2.5rem' }}>
        <div className="stat-card" style={{ '--accent-color': 'var(--purple)' } as any}>
          <div className="stat-icon"><Clock size={24} /></div>
          <div className="stat-value">&lt; 50ms</div>
          <div className="stat-label">Edge Latency SLA</div>
        </div>

        <div className="stat-card" style={{ '--accent-color': 'var(--green)' } as any}>
          <div className="stat-icon"><TrendingUp size={24} /></div>
          <div className="stat-value">+32.4%</div>
          <div className="stat-label">Hard-Decline Conversion Lift</div>
        </div>

        <div className="stat-card" style={{ '--accent-color': 'var(--indigo)' } as any}>
          <div className="stat-icon"><Zap size={24} /></div>
          <div className="stat-value">Sub-Second</div>
          <div className="stat-label">Instant EMI Decisioning</div>
        </div>

        <div className="stat-card" style={{ '--accent-color': 'var(--amber)' } as any}>
          <div className="stat-icon"><ShieldCheck size={24} /></div>
          <div className="stat-value">0 Cart Drops</div>
          <div className="stat-label">Synchronous Edge Fallback</div>
        </div>
      </div>

      {/* Edge Tester & Live Architecture */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1.2fr 1fr',
        gap: '1.75rem',
        marginBottom: '2.5rem'
      }}>
        {/* Interactive Edge Tester */}
        <div style={{
          background: 'rgba(10, 10, 20, 0.7)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '16px',
          padding: '1.75rem',
          backdropFilter: 'blur(20px)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <Zap size={18} style={{ color: 'var(--purple)' }} />
              Live Edge Fallback Simulator
            </h2>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>
              POST /v1/checkout/fallback-offer
            </span>
          </div>

          <form onSubmit={handleTestEdge} style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
            {/* Cart Amount */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Cart Value: <span style={{ color: 'var(--purple)', fontWeight: 600 }}>{formatCurrency(amount)}</span>
              </label>
              <input
                type="range"
                min={500}
                max={25000}
                step={250}
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--purple)' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                <span>₹500 (Low Ticket)</span>
                <span>₹1,500 (BNPL Eligible Threshold)</span>
                <span>₹25,000</span>
              </div>
            </div>

            {/* Decline Reason */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Decline Scenario
                </label>
                <select
                  value={declineReason}
                  onChange={(e) => setDeclineReason(Number(e.target.value))}
                  style={{
                    width: '100%',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    padding: '0.6rem 0.75rem',
                    color: '#FFF',
                    fontSize: '0.85rem'
                  }}
                >
                  <option value={1} style={{ background: '#0A0A14' }}>Insufficient Account Balance (Hard Decline)</option>
                  <option value={2} style={{ background: '#0A0A14' }}>Daily Transaction Limit Exceeded</option>
                  <option value={3} style={{ background: '#0A0A14' }}>Issuer Risk Rejection</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Preferred BNPL Split Tenure
                </label>
                <select
                  value={tenureMonths}
                  onChange={(e) => setTenureMonths(Number(e.target.value))}
                  style={{
                    width: '100%',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    padding: '0.6rem 0.75rem',
                    color: '#FFF',
                    fontSize: '0.85rem'
                  }}
                >
                  <option value={3} style={{ background: '#0A0A14' }}>3 Months Split (₹{Math.round(amount / 3)}/mo)</option>
                  <option value={6} style={{ background: '#0A0A14' }}>6 Months Split (₹{Math.round(amount / 6)}/mo)</option>
                  <option value={12} style={{ background: '#0A0A14' }}>12 Months Split (₹{Math.round(amount / 12)}/mo)</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={evaluating}
              style={{
                marginTop: '0.5rem',
                background: 'linear-gradient(135deg, var(--purple), var(--indigo))',
                border: 'none',
                borderRadius: '8px',
                padding: '0.75rem',
                color: '#FFF',
                fontWeight: 600,
                fontSize: '0.9rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                boxShadow: '0 4px 16px rgba(192, 132, 252, 0.25)'
              }}
            >
              {evaluating ? 'Calling BNPL Edge Gateway...' : 'Execute Sub-50ms Edge Fallback Call'}
              <Send size={15} />
            </button>
          </form>

          {/* Result Card */}
          {result && (
            <div style={{
              marginTop: '1.5rem',
              padding: '1.25rem',
              borderRadius: '12px',
              background: result.show_bnpl_offer ? 'rgba(52, 211, 153, 0.08)' : 'rgba(239, 68, 68, 0.08)',
              border: result.show_bnpl_offer ? '1px solid rgba(52, 211, 153, 0.25)' : '1px solid rgba(239, 68, 68, 0.25)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {result.show_bnpl_offer ? (
                    <CheckCircle2 size={18} style={{ color: 'var(--green)' }} />
                  ) : (
                    <XCircle size={18} style={{ color: 'var(--red)' }} />
                  )}
                  <span style={{ fontWeight: 700, fontSize: '0.95rem', color: result.show_bnpl_offer ? 'var(--green)' : 'var(--red)' }}>
                    {result.show_bnpl_offer ? 'BNPL FALLBACK PRESENTED TO SHOPPER' : 'OFFER SUPPRESSED (Below Threshold)'}
                  </span>
                </div>

                {latencyMs !== null && (
                  <span style={{
                    fontSize: '0.72rem',
                    fontFamily: 'var(--mono)',
                    padding: '2px 8px',
                    borderRadius: '999px',
                    background: latencyMs < 50 ? 'rgba(52, 211, 153, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                    color: latencyMs < 50 ? 'var(--green)' : 'var(--amber)',
                    fontWeight: 600
                  }}>
                    ⏱️ {latencyMs}ms latency
                  </span>
                )}
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '0.5rem',
                fontSize: '0.78rem',
                marginTop: '0.75rem',
                paddingTop: '0.75rem',
                borderTop: '1px solid rgba(255,255,255,0.06)'
              }}>
                <div>
                  <span style={{ color: 'var(--text-dim)', display: 'block' }}>Conversion Likelihood</span>
                  <span style={{ color: 'var(--green)', fontWeight: 700, fontSize: '1rem' }}>
                    {(result.conversion_probability * 100).toFixed(0)}%
                  </span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-dim)', display: 'block' }}>Monthly EMI Split</span>
                  <span style={{ color: 'var(--purple)', fontWeight: 700, fontSize: '1rem' }}>
                    ₹{Math.round(amount / tenureMonths)}/mo
                  </span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-dim)', display: 'block' }}>Checkout Action</span>
                  <span style={{ color: 'var(--indigo)', fontWeight: 600 }}>
                    Instant Modal Switch
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Why BNPL Edge Architecture Card */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '1.25rem'
        }}>
          <div style={{
            background: 'rgba(10, 10, 20, 0.7)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '16px',
            padding: '1.5rem',
            backdropFilter: 'blur(20px)'
          }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-primary)' }}>
              <Zap size={18} style={{ color: 'var(--purple)' }} />
              The Sub-50ms Edge Advantage
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              <p>
                When a payment gateway throws an <strong>INSUFFICIENT_FUNDS</strong> error, the customer is seconds away from abandoning the site.
              </p>
              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <strong style={{ color: '#FFF' }}>1. Millisecond Interception:</strong> The Go Edge proxy receives the failure callback, checks ML inference in memory, and returns eligibility in &lt;50ms.
              </div>
              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <strong style={{ color: '#FFF' }}>2. Dynamic EMI Restructuring:</strong> Instead of asking for ₹6,500 upfront, the UI automatically offers 3 interest-free payments of ₹2,166.
              </div>
              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <strong style={{ color: '#FFF' }}>3. Zero Brand Churn:</strong> Recovers high-intent buyers without frustrating them with repeated failed bank OTP prompts.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Mock Checkout Modal when requested */}
      {showCheckoutModal && (
        <MockCheckoutModal
          onClose={() => setShowCheckoutModal(false)}
          onEventFired={() => {}}
        />
      )}
    </div>
  );
}
