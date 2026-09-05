'use client';

import { useState } from 'react';
import { 
  TrendingDown, 
  Sparkles, 
  ShieldAlert, 
  Calculator, 
  Percent, 
  BadgeIndianRupee, 
  CheckCircle2, 
  XCircle, 
  Send,
  Zap,
  Filter,
  Brain,
  Cpu,
  ArrowRight,
  RefreshCw
} from 'lucide-react';
import Link from 'next/link';
import DropOffFunnel from '@/components/DropOffFunnel';
import { executeLiveCausalIntervention } from '@/app/actions';

export default function DropoffPage() {
  // Causal Net-EV Calculator state
  const [baseConversion, setBaseConversion] = useState(0.14); // P0 = 14%
  const [liftConversion, setLiftConversion] = useState(0.24); // Pa = 24%
  const [contributionMargin, setContributionMargin] = useState(1500); // CM = Rs 1500
  const [discountAmount, setDiscountAmount] = useState(250); // Da = Rs 250
  const [rtoRate, setRtoRate] = useState(0.18); // ra = 18%
  const [rtoPenalty, setRtoPenalty] = useState(250); // K_RTO = Rs 250
  const [dispatchCost, setDispatchCost] = useState(1.5); // Ka = Rs 1.50 (WhatsApp API)

  // Real Model Inference State (FastAPI :8000)
  const [mlLoading, setMlLoading] = useState(false);
  const [liveMlResult, setLiveMlResult] = useState<any>(null);

  const handleTestLiveModel = async () => {
    setMlLoading(true);
    try {
      const res = await executeLiveCausalIntervention({
        session_id: `ses_live_${Date.now().toString(36)}`,
        diagnosis: 'price_shock',
        cart_value: contributionMargin * 4, // 25% margin implies cart = 4x CM
        duration_sec: 140,
        payment_method: 'upi',
        device: 'mobile_android',
        merchant_margin: 0.25,
        incentive_amount: discountAmount,
        rto_cost_estimate: rtoPenalty
      });
      setLiveMlResult(res);
    } catch (e: any) {
      console.error(e);
    } finally {
      setMlLoading(false);
    }
  };

  // Net-EV calculation:
  // EV_treat = Pa * [ (1 - ra)*(CM - Da) - ra * K_RTO ] - Ka
  // EV_ctrl  = P0 * [ (1 - r0)*CM - r0 * K_RTO ] (assuming base r0 = rtoRate * 0.8)
  const baseRto = rtoRate * 0.8;
  const evTreat = liftConversion * ((1 - rtoRate) * (contributionMargin - discountAmount) - rtoRate * rtoPenalty) - dispatchCost;
  const evCtrl = baseConversion * ((1 - baseRto) * contributionMargin - baseRto * rtoPenalty);
  const deltaNetEV = evTreat - evCtrl;
  const shouldIntervene = deltaNetEV > 0;

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
                background: 'rgba(251, 191, 36, 0.15)',
                border: '1px solid rgba(251, 191, 36, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <TrendingDown size={20} style={{ color: 'var(--amber)' }} />
              </div>
              <h1 className="page-title" style={{ margin: 0 }}>Causal Checkout Drop-Off Recovery</h1>
              <span style={{
                fontSize: '0.72rem',
                fontFamily: 'var(--mono)',
                padding: '3px 8px',
                borderRadius: '6px',
                background: 'rgba(251, 191, 36, 0.12)',
                color: 'var(--amber)',
                border: '1px solid rgba(251, 191, 36, 0.25)',
                fontWeight: 600
              }}>
                Pillar 3 · Causal Revenue Engine (:3002)
              </span>
            </div>
            <p className="page-sub" style={{ marginTop: '0.35rem' }}>
              Real-time Redis ZSET session tracker combined with a Causal S-Learner & RTO risk model. Unlike naive abandoned-cart blast tools, it rigorously suppresses intervention when net economic value (ΔΠ_a) is negative.
            </p>
          </div>
        </div>
      </div>

      {/* Live Two-Stage ML Recovery Engine Funnel */}
      <DropOffFunnel />

      {/* Causal Net-EV Interactive Simulator */}
      <div style={{
        background: 'rgba(10, 10, 20, 0.7)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '16px',
        padding: '1.75rem',
        marginBottom: '2.5rem',
        backdropFilter: 'blur(20px)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <Calculator size={20} style={{ color: 'var(--amber)' }} />
              Causal Net-EV Maximizer Playground
            </h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Mathematical proof of why Razorpay Causal Engine captures ~88% of maximum Oracle profit while eliminating margin cannibalization.
            </p>
          </div>

          {/* Decision Pill */}
          <div style={{
            padding: '8px 16px',
            borderRadius: '999px',
            background: shouldIntervene ? 'rgba(52, 211, 153, 0.12)' : 'rgba(239, 68, 68, 0.12)',
            border: shouldIntervene ? '1px solid rgba(52, 211, 153, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontWeight: 700,
            fontSize: '0.85rem',
            color: shouldIntervene ? 'var(--green)' : 'var(--red)'
          }}>
            {shouldIntervene ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
            <span>{shouldIntervene ? 'DISPATCH RECOVERY (Net-EV Positive)' : 'SUPPRESS INTERVENTION (Protects Profit)'}</span>
          </div>
        </div>

        {/* Sliders Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '1.5rem',
          marginBottom: '1.75rem'
        }}>
          {/* Contribution Margin */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Contribution Margin (CM)</span>
              <span style={{ fontWeight: 600, fontFamily: 'var(--mono)', color: 'var(--indigo)' }}>₹{contributionMargin}</span>
            </div>
            <input
              type="range"
              min={500}
              max={5000}
              step={50}
              value={contributionMargin}
              onChange={(e) => setContributionMargin(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--indigo)' }}
            />
          </div>

          {/* WhatsApp Discount */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Discount Given (D_a)</span>
              <span style={{ fontWeight: 600, fontFamily: 'var(--mono)', color: 'var(--amber)' }}>₹{discountAmount}</span>
            </div>
            <input
              type="range"
              min={0}
              max={1000}
              step={25}
              value={discountAmount}
              onChange={(e) => setDiscountAmount(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--amber)' }}
            />
          </div>

          {/* Lift Conversion Probability */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Treated Conversion (P_a)</span>
              <span style={{ fontWeight: 600, fontFamily: 'var(--mono)', color: 'var(--green)' }}>{(liftConversion * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min={0.05}
              max={0.6}
              step={0.01}
              value={liftConversion}
              onChange={(e) => setLiftConversion(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--green)' }}
            />
          </div>

          {/* Organic Conversion Probability */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Organic Conversion (P_0)</span>
              <span style={{ fontWeight: 600, fontFamily: 'var(--mono)', color: 'var(--purple)' }}>{(baseConversion * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min={0.02}
              max={0.4}
              step={0.01}
              value={baseConversion}
              onChange={(e) => setBaseConversion(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--purple)' }}
            />
          </div>

          {/* RTO Risk Rate */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Return-to-Origin Risk (r_a)</span>
              <span style={{ fontWeight: 600, fontFamily: 'var(--mono)', color: 'var(--red)' }}>{(rtoRate * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min={0.05}
              max={0.6}
              step={0.01}
              value={rtoRate}
              onChange={(e) => setRtoRate(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--red)' }}
            />
          </div>

          {/* RTO Penalty Cost */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>RTO Reverse Logistics (K_RTO)</span>
              <span style={{ fontWeight: 600, fontFamily: 'var(--mono)', color: 'var(--text-primary)' }}>₹{rtoPenalty}</span>
            </div>
            <input
              type="range"
              min={100}
              max={600}
              step={25}
              value={rtoPenalty}
              onChange={(e) => setRtoPenalty(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--text-muted)' }}
            />
          </div>
        </div>

        {/* Calculation Result Breakdown */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '1rem',
          padding: '1.25rem',
          background: 'rgba(255,255,255,0.02)',
          borderRadius: '12px',
          border: '1px solid rgba(255,255,255,0.05)'
        }}>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Intervention Expected Value (EV_treat)</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--indigo)', marginTop: '2px' }}>
              ₹{evTreat.toFixed(2)}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              P_a[(1-r_a)(CM - D_a) - r_a K_RTO] - K_a
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Organic Baseline Value (EV_ctrl)</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--purple)', marginTop: '2px' }}>
              ₹{evCtrl.toFixed(2)}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              P_0[(1-r_0)CM - r_0 K_RTO]
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Net Economic Value (ΔΠ_a)</div>
            <div style={{
              fontSize: '1.2rem',
              fontWeight: 700,
              fontFamily: 'var(--mono)',
              color: deltaNetEV > 0 ? 'var(--green)' : 'var(--red)',
              marginTop: '2px'
            }}>
              {deltaNetEV > 0 ? '+' : ''}₹{deltaNetEV.toFixed(2)}
            </div>
            <div style={{ fontSize: '0.7rem', color: deltaNetEV > 0 ? 'var(--green)' : 'var(--red)', marginTop: '2px' }}>
              {deltaNetEV > 0 ? 'Positive ROI — Safe to Disptach Nudge' : 'Negative ROI — Discount Burns Margin!'}
            </div>
          </div>
        </div>
      </div>

      {/* Direct Underlying Machine Learning Model Execution Card */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(30, 27, 75, 0.4), rgba(15, 23, 42, 0.6))',
        border: '1px solid rgba(139, 92, 246, 0.25)',
        borderRadius: '16px',
        padding: '1.75rem',
        backdropFilter: 'blur(20px)',
        marginBottom: '2rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Brain size={20} style={{ color: 'var(--indigo)' }} />
              <h3 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0 }}>
                Underlying ML Model: LightGBM Causal S-Learner & RTO Engine
              </h3>
              <span style={{
                fontSize: '0.7rem',
                fontFamily: 'var(--mono)',
                padding: '2px 8px',
                borderRadius: '6px',
                background: 'rgba(52, 211, 153, 0.12)',
                color: 'var(--green)',
                border: '1px solid rgba(52, 211, 153, 0.25)'
              }}>
                models/ml/causal_s_learner.pkl
              </span>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
              Instead of synthetic formulas, test the real trained LightGBM meta-learner running inside <code style={{ color: 'var(--cyan)' }}>razorpay-inference:8000</code>.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <Link
              href="/models"
              style={{
                fontSize: '0.8rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                color: 'var(--indigo)',
                textDecoration: 'none',
                padding: '6px 12px',
                borderRadius: '8px',
                background: 'rgba(99, 102, 241, 0.1)',
                border: '1px solid rgba(99, 102, 241, 0.25)'
              }}
            >
              <span>Explore All 8 Models</span>
              <ArrowRight size={14} />
            </Link>

            <button
              onClick={handleTestLiveModel}
              disabled={mlLoading}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '8px 16px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, var(--indigo), #8B5CF6)',
                border: 'none',
                color: '#fff',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: mlLoading ? 'not-allowed' : 'pointer',
                boxShadow: '0 2px 10px rgba(99, 102, 241, 0.3)'
              }}
            >
              {mlLoading ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  <span>Querying Model...</span>
                </>
              ) : (
                <>
                  <Zap size={14} />
                  <span>Run Live Model Inference (:8000)</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Live Model Output Display */}
        {liveMlResult && (
          <div style={{
            background: 'rgba(0, 0, 0, 0.4)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '10px',
            padding: '1rem',
            animation: 'fadeIn 0.3s ease'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
                Live Model Prediction & Telemetry
              </span>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{
                  fontSize: '0.72rem',
                  fontFamily: 'var(--mono)',
                  color: 'var(--cyan)',
                  background: 'rgba(6, 182, 212, 0.1)',
                  padding: '2px 6px',
                  borderRadius: '4px'
                }}>
                  {liveMlResult.latencyMs} ms
                </span>
                <span style={{
                  fontSize: '0.7rem',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  background: liveMlResult.isLive ? 'rgba(52, 211, 153, 0.15)' : 'rgba(251, 191, 36, 0.15)',
                  color: liveMlResult.isLive ? 'var(--green)' : 'var(--amber)'
                }}>
                  {liveMlResult.isLive ? 'Live FastAPI Gateway :8000' : 'Emulated Fallback'}
                </span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '0.75rem' }}>
              <div style={{ padding: '8px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Action Decision</div>
                <div style={{
                  fontSize: '1rem',
                  fontWeight: 700,
                  fontFamily: 'var(--mono)',
                  color: liveMlResult.data.action === 'NO_ACTION' ? 'var(--red)' : 'var(--green)',
                  marginTop: '2px'
                }}>
                  {liveMlResult.data.action}
                </div>
              </div>

              <div style={{ padding: '8px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Causal Recovery Prob (P_a)</div>
                <div style={{ fontSize: '1rem', fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--green)', marginTop: '2px' }}>
                  {((liveMlResult.data.recovery_prob || 0) * 100).toFixed(1)}%
                </div>
              </div>

              <div style={{ padding: '8px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Estimated RTO Risk (r_a)</div>
                <div style={{ fontSize: '1rem', fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--amber)', marginTop: '2px' }}>
                  {((liveMlResult.data.risk_score || 0) * 100).toFixed(1)}%
                </div>
              </div>

              <div style={{ padding: '8px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Net-EV Gain (ΔΠ)</div>
                <div style={{
                  fontSize: '1rem',
                  fontWeight: 700,
                  fontFamily: 'var(--mono)',
                  color: liveMlResult.data.expected_profit >= 0 ? 'var(--green)' : 'var(--red)',
                  marginTop: '2px'
                }}>
                  ₹{liveMlResult.data.expected_profit}
                </div>
              </div>
            </div>

            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--mono)', background: 'rgba(0,0,0,0.3)', padding: '6px 10px', borderRadius: '4px' }}>
              Model Reason: {liveMlResult.data.reasoning}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
