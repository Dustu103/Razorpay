'use client';
import { useEffect, useState } from 'react';
import { Activity, MessageSquare, TrendingUp, Filter, ShieldAlert, Sparkles, Clock, CheckCircle2, XCircle } from 'lucide-react';

interface InterventionItem {
  session_id: string;
  diagnosis: string;
  action: string;
  timestamp: string;
  message?: string;
  risk_score?: number;
  recovery_prob?: number;
  expected_profit?: number;
}

interface Metrics {
  active_sessions: number;
  interventions_sent: number;
  revenue_recovered: string;
  recent_interventions?: (string | InterventionItem)[];
}

const DIAGNOSIS_LABELS: Record<string, { title: string; color: string; bg: string }> = {
  price_shock: { title: "Price Shock (Cart Breakdown Abandonment)", color: "#F59E0B", bg: "rgba(245, 158, 11, 0.12)" },
  vpa_validation_abort: { title: "UPI VPA Validation Failure", color: "#EF4444", bg: "rgba(239, 68, 68, 0.12)" },
  app_switch_failure: { title: "UPI App-Switch Timeout", color: "#3B82F6", bg: "rgba(59, 130, 246, 0.12)" },
  otp_delivery_delay: { title: "Issuer OTP Delivery Delay", color: "#8B5CF6", bg: "rgba(139, 92, 246, 0.12)" },
  genuine_abandonment: { title: "Standard Cart Abandonment", color: "#6B7280", bg: "rgba(107, 114, 128, 0.12)" }
};

const ACTION_LABELS: Record<string, { label: string; icon: string }> = {
  whatsapp_discount: { label: "Dispatched WhatsApp Recovery", icon: "💬" },
  whatsapp: { label: "Dispatched WhatsApp Recovery", icon: "💬" },
  vpa_retry_nudge: { label: "Triggered In-App VPA Suggestion", icon: "⚡" },
  sms_checkout_link: { label: "Sent SMS Checkout URL", icon: "📱" },
  sms: { label: "Sent SMS Checkout URL", icon: "📱" },
  suppressed: { label: "Intervention Suppressed (High Risk)", icon: "🛑" },
  NO_ACTION: { label: "Intervention Suppressed (High Risk)", icon: "🛑" },
  default: { label: "Dispatched Recovery Nudge", icon: "✨" }
};

const ProgressBar = ({ label, percentage, color }: { label: string, percentage: number, color: string }) => {
  return (
    <div style={{ marginBottom: '6px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '2px', color: 'var(--text-muted)' }}>
        <span>{label}</span>
        <span style={{ fontFamily: 'var(--mono)' }}>{Math.round(percentage * 100)}%</span>
      </div>
      <div style={{ height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${Math.min(100, Math.max(0, percentage * 100))}%`, background: color, transition: 'width 0.5s ease' }} />
      </div>
    </div>
  );
};

export default function DropOffFunnel() {
  const [metrics, setMetrics] = useState<Metrics>({
    active_sessions: 42,
    interventions_sent: 156,
    revenue_recovered: '117000.00',
    recent_interventions: []
  });

  const fetchMetrics = () => {
    fetch('http://localhost:3002/api/v1/dropoff-metrics')
      .then(res => res.json())
      .then(data => {
        if (data && typeof data.active_sessions === 'number') {
          setMetrics(data);
        }
      })
      .catch(e => console.log('Dropoff metrics fetch failed, using demo data', e));
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 3000);
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (val: string | number) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(num);
  };

  // Parse interventions if they arrive as JSON strings
  const parsedInterventions: InterventionItem[] = (metrics.recent_interventions || []).map(item => {
    if (typeof item === 'string') {
      try { return JSON.parse(item); } catch (e) { return null; }
    }
    return item;
  }).filter(Boolean) as InterventionItem[];

  return (
    <div className="funnel-container" style={{ marginBottom: '2.5rem', padding: '1.5rem', background: 'var(--surface)', borderRadius: '12px', border: '1px solid var(--border)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--text)' }}>
          <Filter size={20} color="var(--indigo)" />
          Two-Stage ML Recovery Engine
        </h2>
        <span style={{ fontSize: '0.85rem', color: 'var(--green)', background: 'rgba(16, 185, 129, 0.1)', padding: '6px 12px', borderRadius: '12px', fontWeight: 500, letterSpacing: '0.5px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--green)', animation: 'pulse 2s infinite' }}></span>
          LIVE DUAL-MODEL PIPELINE
        </span>
      </div>

      {/* Aggregate Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '1.75rem' }}>
        <div style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.02)', borderRadius: '10px', borderLeft: '4px solid var(--indigo)' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 500 }}>
            <Activity size={18} /> Active Sessions
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text)' }}>{metrics.active_sessions}</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>Tracking uncommitted checkouts</div>
        </div>

        <div style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.02)', borderRadius: '10px', borderLeft: '4px solid var(--amber)' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 500 }}>
            <MessageSquare size={18} /> Interventions Sent
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text)' }}>{metrics.interventions_sent}</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>EV-Optimized & Risk-Gated</div>
        </div>

        <div style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.02)', borderRadius: '10px', borderLeft: '4px solid var(--green)' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 500 }}>
            <TrendingUp size={18} /> Est. Incremental Profit
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--green)' }}>
            {formatCurrency(metrics.revenue_recovered)}
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>Net profit after channel costs</div>
        </div>
      </div>

      {/* Live AI Detection & Action Table */}
      <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '10px', padding: '1.25rem', border: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={16} color="#F59E0B" />
            Live Dual-Model Inference Log
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Auto-refreshing every 3s</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {parsedInterventions.length === 0 ? (
            <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              No recent drop-off interventions recorded yet. Launch the Mock Checkout below to test!
            </div>
          ) : (
            parsedInterventions.slice(0, 5).map((item, idx) => {
              const diag = DIAGNOSIS_LABELS[item.diagnosis] || DIAGNOSIS_LABELS.genuine_abandonment;
              const act = ACTION_LABELS[item.action] || ACTION_LABELS.default;
              const isSuppressed = item.action === "NO_ACTION" || item.action === "suppressed";

              return (
                <div 
                  key={idx} 
                  style={{ 
                    display: 'flex', 
                    flexDirection: 'column',
                    padding: '1rem', 
                    background: 'var(--surface)', 
                    borderRadius: '8px', 
                    border: '1px solid var(--border)',
                    borderLeft: `4px solid ${isSuppressed ? '#EF4444' : '#10B981'}`,
                    gap: '1rem'
                  }}
                >
                  {/* Top Row: Session, Diagnosis, Expected Profit */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Clock size={14} color="var(--text-muted)" />
                        <span style={{ fontFamily: 'var(--mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          Session {item.session_id.substring(0, 10)}
                        </span>
                      </div>
                      <span style={{ 
                        padding: '4px 10px', borderRadius: '6px', 
                        background: diag.bg, color: diag.color, 
                        fontWeight: 600, fontSize: '0.75rem',
                        display: 'inline-flex', alignItems: 'center', gap: '5px', width: 'fit-content'
                      }}>
                        <ShieldAlert size={12} />
                        {diag.title}
                      </span>
                    </div>

                    {/* Dual Model Progress Bars */}
                    <div style={{ flex: 1, minWidth: '200px', maxWidth: '300px' }}>
                      <ProgressBar label="Recovery Propensity (XGBoost)" percentage={item.recovery_prob || 0} color="var(--indigo)" />
                      <ProgressBar label="Behavioral Risk (Isolation Forest)" percentage={item.risk_score || 0} color="#EF4444" />
                    </div>

                    <div style={{ textAlign: 'right', minWidth: '120px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Expected Profit</div>
                      <div style={{ fontSize: '1.25rem', fontWeight: 700, color: item.expected_profit && item.expected_profit > 0 ? 'var(--green)' : 'var(--text-muted)' }}>
                        {item.expected_profit ? formatCurrency(item.expected_profit) : '₹0.00'}
                      </div>
                    </div>

                  </div>

                  {/* Bottom Row: Action Taken */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                    {isSuppressed ? <XCircle size={18} color="#EF4444" /> : <CheckCircle2 size={18} color="var(--green)" />}
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '0.9rem', fontWeight: 600, color: isSuppressed ? '#EF4444' : 'var(--text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span>{act.icon}</span> {isSuppressed ? "SUPPRESSED" : "DECISION: " + act.label}
                      </div>
                      {item.message && !isSuppressed && (
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontStyle: 'italic', marginTop: '4px' }}>
                          "{item.message}"
                        </div>
                      )}
                    </div>
                  </div>

                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
