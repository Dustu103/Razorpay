'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { simulateWebhook } from '@/app/actions';
import { Play, Loader2, Code, Zap, CheckCircle2, AlertCircle } from 'lucide-react';
import MockCheckoutModal from './MockCheckoutModal';

interface Scenario {
  name: string;
  desc: string;
  payload: Record<string, any>;
  isCompliance?: boolean;
}

const SCENARIOS: Scenario[] = [
  {
    name: "Layer 1 · RBI Compliance",
    desc: "Pre-debit notification missing <24h before debit",
    isCompliance: true,
    payload: {
      event: "payment.failed",
      payload: {
        payment: {
          entity: {
            id: "pay_test_L1_rbi",
            amount: 150000,
            status_code: "COMPLIANCE_HOLD",
            bank: "HDFC",
            mandate_notification_sent_at: null
          }
        }
      }
    }
  },
  {
    name: "Layer 2 · Soft Decline (ML)",
    desc: "Insufficient funds mapped via Random Forest",
    payload: {
      event: "payment.failed",
      payload: {
        payment: {
          entity: {
            id: "pay_test_L2_soft",
            amount: 450000,
            status_code: "BAD_REQUEST_ERROR",
            bank_response_code: "51",
            bank: "ICIC",
            retry_count: 1
          }
        }
      }
    }
  },
  {
    name: "Layer 3 · Gateway Fault",
    desc: "Bank network timeout evaluated by LLM / Heuristics",
    payload: {
      event: "payment.failed",
      payload: {
        payment: {
          entity: {
            id: "pay_test_L3_gateway",
            amount: 750000,
            status_code: "TIMEOUT",
            bank_response_code: "91",
            bank: "SBIN"
          }
        }
      }
    }
  },
  {
    name: "Layer 4 · Fraud Block",
    desc: "Suspected fraud code triggering arbitration",
    payload: {
      event: "payment.failed",
      payload: {
        payment: {
          entity: {
            id: "pay_test_L4_fraud",
            amount: 2500000,
            status_code: "BAD_REQUEST_ERROR",
            bank_response_code: "59",
            bank: "KKBK"
          }
        }
      }
    }
  },
  {
    name: "Layer 0 · NACH SIP Guard",
    desc: "Recurring SIP failure #2 pre-emptive AMC escalation",
    payload: {
      event: "payment.failed",
      payload: {
        payment: {
          entity: {
            id: "pay_test_L0_sip",
            amount: 820000,
            status_code: "BAD_REQUEST_ERROR",
            bank_response_code: "51",
            payment_rail: "nach",
            product_type: "sip",
            consecutive_failure_count: 2
          }
        }
      }
    }
  },
  {
    name: "Layer 0 · NACH EMI Bureau",
    desc: "Loan EMI 29 days past due (Bureau Guard)",
    payload: {
      event: "payment.failed",
      payload: {
        payment: {
          entity: {
            id: "pay_test_L0_emi",
            amount: 1450000,
            status_code: "BAD_REQUEST_ERROR",
            bank_response_code: "51",
            payment_rail: "nach",
            product_type: "loan_emi",
            days_since_due_date: 29
          }
        }
      }
    }
  }
];

export default function SimulatorPanel() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showCheckoutDemo, setShowCheckoutDemo] = useState(false);
  
  const [customJson, setCustomJson] = useState(JSON.stringify(SCENARIOS[0].payload, null, 2));
  const [mode, setMode] = useState<'presets' | 'custom'>('presets');

  const handleSend = async (scenario: Scenario | Record<string, any>, isRawJson = false) => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    // Deep clone payload and ensure unique transaction ID on EVERY click so duplicate rejection never happens
    const rawPayload = isRawJson ? scenario : (scenario as Scenario).payload;
    const payload = JSON.parse(JSON.stringify(rawPayload));
    const uniqueId = `pay_sim_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    
    if (payload?.payload?.payment?.entity) {
      payload.payload.payment.entity.id = uniqueId;
      // If compliance test, set debit_scheduled_at to future time so rule triggers
      if (!isRawJson && (scenario as Scenario).isCompliance) {
        payload.payload.payment.entity.debit_scheduled_at = new Date(Date.now() + 6 * 3600 * 1000).toISOString();
      }
    }
    
    const res = await simulateWebhook(payload);
    
    if (res.success) {
      const name = isRawJson ? "Custom payload" : (scenario as Scenario).name;
      setSuccess(`✅ ${name} processed successfully! (ID: ${res.transactionId || uniqueId}) Updating dashboard...`);
      // Trigger Next.js App Router cache invalidation on the client
      router.refresh();
    } else {
      setError(res.error || 'Failed to simulate transaction');
    }
    setLoading(false);
  };

  const handleCustomSend = () => {
    try {
      const parsed = JSON.parse(customJson);
      handleSend(parsed, true);
    } catch (e: any) {
      setError('Invalid JSON format: ' + e.message);
    }
  };

  return (
    <div className="card" style={{ marginBottom: '2rem', padding: '1.25rem 1.5rem' }}>
      <div className="card-title" style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
          <Play size={16} color="var(--green)" />
          Test Simulator
        </span>
        
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button 
            onClick={() => setMode('presets')} 
            style={{ 
              background: mode === 'presets' ? 'var(--bg-card-hover)' : 'transparent', 
              border: '1px solid var(--border)', 
              color: mode === 'presets' ? 'var(--text-primary)' : 'var(--text-muted)', 
              padding: '0.35rem 0.75rem', 
              borderRadius: '6px', 
              fontSize: '0.75rem', 
              cursor: 'pointer', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.3rem' 
            }}
          >
            <Zap size={13} /> Presets
          </button>
          <button 
            onClick={() => setMode('custom')} 
            style={{ 
              background: mode === 'custom' ? 'var(--bg-card-hover)' : 'transparent', 
              border: '1px solid var(--border)', 
              color: mode === 'custom' ? 'var(--text-primary)' : 'var(--text-muted)', 
              padding: '0.35rem 0.75rem', 
              borderRadius: '6px', 
              fontSize: '0.75rem', 
              cursor: 'pointer', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.3rem' 
            }}
          >
            <Code size={13} /> JSON Payload
          </button>
        </div>
      </div>

      {mode === 'presets' ? (
        <div style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap' }}>
          {SCENARIOS.map((s, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(s)}
              disabled={loading}
              title={s.desc}
              style={{
                background: 'rgba(79,142,255,0.08)',
                border: '1px solid rgba(79,142,255,0.3)',
                color: 'var(--blue)',
                padding: '0.55rem 0.9rem',
                borderRadius: '8px',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '0.8rem',
                fontWeight: 600,
                opacity: loading ? 0.6 : 1,
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                transition: 'all 0.15s ease'
              }}
            >
              {loading ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
              {s.name}
            </button>
          ))}
          <button
            onClick={() => setShowCheckoutDemo(true)}
            style={{
              background: 'linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%)',
              border: 'none',
              color: 'white',
              padding: '0.55rem 0.9rem',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              boxShadow: '0 4px 12px rgba(255, 107, 107, 0.3)'
            }}
          >
            <Zap size={13} color="white" />
            Launch Mock Checkout
          </button>
        </div>
      ) : (
        <div>
          <textarea 
            value={customJson}
            onChange={(e) => setCustomJson(e.target.value)}
            style={{ 
              width: '100%', 
              height: '150px', 
              background: 'var(--bg-2)', 
              border: '1px solid var(--border)', 
              color: 'var(--text-primary)', 
              fontFamily: 'var(--mono)', 
              fontSize: '0.8rem', 
              padding: '0.75rem', 
              borderRadius: '8px', 
              marginBottom: '0.75rem', 
              resize: 'vertical' 
            }}
            spellCheck={false}
          />
          <button
            onClick={handleCustomSend}
            disabled={loading}
            style={{
              background: 'var(--green-dim)',
              border: '1px solid rgba(52,211,153,0.3)',
              color: 'var(--green)',
              padding: '0.5rem 1.25rem',
              borderRadius: '8px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '0.82rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem'
            }}
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : 'Send JSON Payload'}
          </button>
        </div>
      )}

      {error && (
        <div style={{ marginTop: '1rem', color: 'var(--red)', fontSize: '0.82rem', background: 'var(--red-dim)', padding: '0.6rem 0.85rem', borderRadius: '6px', border: '1px solid rgba(248,113,113,0.25)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div style={{ marginTop: '1rem', color: 'var(--green)', fontSize: '0.82rem', background: 'var(--green-dim)', padding: '0.6rem 0.85rem', borderRadius: '6px', border: '1px solid rgba(52,211,153,0.25)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <CheckCircle2 size={15} />
          <span>{success}</span>
        </div>
      )}

      {showCheckoutDemo && (
        <MockCheckoutModal 
          onClose={() => setShowCheckoutDemo(false)} 
          onEventFired={(evt) => console.log('Checkout event fired:', evt)}
        />
      )}
    </div>
  );
}
