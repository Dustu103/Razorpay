'use client';

import Link from 'next/link';
import { 
  BrainCircuit, 
  ShieldCheck, 
  TrendingDown, 
  RotateCcw, 
  CreditCard, 
  Scale, 
  FileCheck, 
  ShieldAlert, 
  Cpu,
  ArrowRight,
  Sparkles,
  CheckCircle2
} from 'lucide-react';

const PILLARS = [
  {
    id: 1,
    title: 'Root-Cause MoE & ML Model Gateway',
    subtitle: 'Pillar 1 · Diagnostics & Model Registry',
    description: '8 ML Models in memory (Causal S-Learner, Dispute 5-Ensemble, False Decline, BNPL Edge, Smart Retry) with live inference at :8000.',
    metric: '8 Models Live',
    metricLabel: 'Sub-10ms localized inference',
    service: 'inference-service',
    port: ':8000',
    badgeColor: 'var(--indigo)',
    icon: BrainCircuit,
    href: '/models',
    ctaText: 'Open ML Models Hub'
  },
  {
    id: 2,
    title: 'NACH Mandate Shield',
    subtitle: 'Pillar 2 · Recurring Debit Defense',
    description: 'Layer 0 Governor enforces AMC 3-attempt SIP cap, EMI Day 28 credit bureau guard, and stops wasted bank bounce fees.',
    metric: '+51.3% Revenue Lift',
    metricLabel: '114 wasted bank attempts eliminated',
    service: 'nach-recovery-service',
    port: ':3007',
    badgeColor: 'var(--green)',
    icon: ShieldCheck,
    href: '/nach',
    ctaText: 'Open Mandate Shield'
  },
  {
    id: 3,
    title: 'Causal Drop-Off Recovery',
    subtitle: 'Pillar 3 · Margin-Protected Cart Rescue',
    description: 'Dual Causal S-Learner & RTO risk engine evaluates Net-EV (ΔΠ_a). Suppresses discounts if user would convert organically.',
    metric: '88% Oracle Net Profit',
    metricLabel: 'Suppresses cannibalizing discounts',
    service: 'dropoff-service',
    port: ':3002',
    badgeColor: 'var(--amber)',
    icon: TrendingDown,
    href: '/dropoff',
    ctaText: 'View Causal Console'
  },
  {
    id: 4,
    title: 'False-Decline Reversal',
    subtitle: 'Pillar 4 · Big-Ticket Shopper Rescue',
    description: 'High-value customer rescue using IP risk, device trust, and velocity heuristics to reverse overly aggressive fraud filter blocks.',
    metric: '97.35% Model Precision',
    metricLabel: 'Zero-friction reverify & rescue',
    service: 'inference-service',
    port: ':8000',
    badgeColor: 'var(--pink)',
    icon: RotateCcw,
    href: '/?cause=fraud_filter_block#classifications-table',
    ctaText: 'Filter Reversals'
  },
  {
    id: 5,
    title: 'BNPL Edge Checkout Rescue',
    subtitle: 'Pillar 5 · Hard Decline Salvation',
    description: 'Ultra-low latency edge proxy that intercepts insufficient-fund declines within 50ms to present instant split-pay EMI offers.',
    metric: '< 50ms Edge SLA',
    metricLabel: 'Prevents checkout bounce at edge',
    service: 'bnpl-edge-service',
    port: ':8003',
    badgeColor: 'var(--purple)',
    icon: CreditCard,
    href: '/edge-rescue',
    ctaText: 'Simulate Edge Fallback'
  },
  {
    id: 6,
    title: 'Dispute Pre-emption & Defense',
    subtitle: 'Pillar 6 · Autonomous Chargeback Defense',
    description: 'VAMP dispute engine predicts win probability with LightGBM and synthesizes telemetry into compliant LLM evidence packets.',
    metric: '84.93% Win Predictor',
    metricLabel: 'Automated rebuttal drafting',
    service: 'chargeback-service',
    port: ':3005',
    badgeColor: 'var(--blue)',
    icon: Scale,
    href: '/chargeback',
    ctaText: 'Manage Chargebacks'
  },
  {
    id: 7,
    title: 'B2B Tax Lever Agent',
    subtitle: 'Pillar 7 · Working Capital Recovery',
    description: 'Scheduled daemon identifying 30+ day unpaid invoices. Cites MSME Sec 43B(h) and CGST Rule 37 ITC reversal to accelerate payment.',
    metric: 'Statutory Tax Statutes',
    metricLabel: 'MSME 45-day & GST 180-day leverage',
    service: 'b2b-recovery-service',
    port: ':3006',
    badgeColor: 'var(--orange)',
    icon: FileCheck,
    href: '/tax-approvals',
    ctaText: 'Review Tax Notices'
  },
  {
    id: 8,
    title: 'RBI UX Mandate Scanner',
    subtitle: 'Pillar 8 · Regulatory Integrity Guard',
    description: 'Proactive scanner auditing recurring mandate checkout UI schemas against RBI circulars for pre-debit alerts and dark patterns.',
    metric: '100% RBI Compliance',
    metricLabel: 'Pre-production schema validation',
    service: 'compliance-service',
    port: ':3004',
    badgeColor: 'var(--red)',
    icon: ShieldAlert,
    href: '/compliance',
    ctaText: 'Run Schema Audit'
  },
  {
    id: 9,
    title: 'NPCI Retry & Invariant Governor',
    subtitle: 'Pillar 9 · Clearing Cap Enforcer',
    description: 'Deterministic systemic backstop enforcing NPCI attempt caps (max 4 retries/24h) to eliminate merchant debit penalties.',
    metric: 'Max 4 Retries / 24h',
    metricLabel: 'Systemic banking clearing compliance',
    service: 'system-governor',
    port: 'Embedded',
    badgeColor: 'var(--indigo)',
    icon: Cpu,
    href: '/npci-governor',
    ctaText: 'Inspect Invariants'
  },
];

export default function PillarGrid() {
  return (
    <section style={{ marginBottom: '2.5rem' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '1.25rem'
      }}>
        <div>
          <h2 style={{
            fontSize: '1.35rem',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem',
            letterSpacing: '-0.02em',
            color: 'var(--text-primary)'
          }}>
            <Sparkles size={20} style={{ color: 'var(--indigo)' }} />
            9-Pillar Autonomous Revenue Recovery Engine
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            Comprehensive microservice ecosystem addressing payment failure modes across checkouts, recurring debits, disputes, and corporate billing.
          </p>
        </div>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.78rem',
          color: 'var(--text-dim)',
          background: 'rgba(255,255,255,0.02)',
          padding: '4px 12px',
          borderRadius: '999px',
          border: '1px solid var(--border)'
        }}>
          <CheckCircle2 size={13} style={{ color: 'var(--green)' }} />
          <span>9 Autonomous Pillars Operating Concurrently</span>
        </div>
      </div>

      {/* Grid of 9 pillars */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
        gap: '1.1rem'
      }}>
        {PILLARS.map((p) => {
          const Icon = p.icon;
          return (
            <div
              key={p.id}
              style={{
                background: 'rgba(10, 10, 20, 0.65)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                borderRadius: '16px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                position: 'relative',
                overflow: 'hidden',
                backdropFilter: 'blur(16px)',
                transition: 'all 0.25s ease',
                boxShadow: '0 4px 20px rgba(0,0,0,0.25)'
              }}
              className="pillar-card"
            >
              {/* Top ambient color glow */}
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                height: '3px',
                background: `linear-gradient(90deg, transparent, ${p.badgeColor}, transparent)`
              }} />

              {/* Card Header */}
              <div>
                <div style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  marginBottom: '0.75rem'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                    <div style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '10px',
                      background: `rgba(255, 255, 255, 0.03)`,
                      border: `1px solid rgba(255, 255, 255, 0.08)`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <Icon size={18} style={{ color: p.badgeColor }} />
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: p.badgeColor, fontWeight: 700 }}>
                        {p.subtitle}
                      </div>
                      <h3 style={{ fontSize: '1.02rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '1px' }}>
                        {p.title}
                      </h3>
                    </div>
                  </div>

                  <span style={{
                    fontSize: '0.68rem',
                    fontFamily: 'var(--mono)',
                    padding: '2px 8px',
                    borderRadius: '6px',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.06)',
                    color: 'var(--text-dim)'
                  }}>
                    {p.port}
                  </span>
                </div>

                <p style={{
                  fontSize: '0.82rem',
                  color: 'var(--text-muted)',
                  lineHeight: '1.45',
                  marginBottom: '1rem'
                }}>
                  {p.description}
                </p>
              </div>

              {/* Bottom Metric & CTA */}
              <div>
                <div style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.04)',
                  borderRadius: '10px',
                  padding: '0.6rem 0.85rem',
                  marginBottom: '0.9rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 700, color: p.badgeColor, fontFamily: 'var(--mono)' }}>
                      {p.metric}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      {p.metricLabel}
                    </div>
                  </div>
                  <span style={{
                    fontSize: '0.68rem',
                    color: 'var(--text-dim)',
                    background: 'rgba(255,255,255,0.02)',
                    padding: '2px 6px',
                    borderRadius: '4px'
                  }}>
                    {p.service}
                  </span>
                </div>

                <Link
                  href={p.href}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.4rem',
                    width: '100%',
                    padding: '0.55rem',
                    borderRadius: '8px',
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    textDecoration: 'none',
                    transition: 'all 0.2s ease'
                  }}
                  className="pillar-cta-btn"
                >
                  <span>{p.ctaText}</span>
                  <ArrowRight size={13} />
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
