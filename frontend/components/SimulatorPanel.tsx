'use client';

import { useState } from 'next/startTransition';
import { simulateWebhook } from '@/app/actions';
import { Play, Loader2, Code, Zap } from 'lucide-react';
import React from 'react';

const SCENARIOS = [
  {
    name: "Gateway Fault (Layer 1)",
    payload: {
      event: "payment.failed",
      payload: {
        payment: {
          entity: {
            id: "pay_test_L1_gateway",
            amount: 50000,
            status: "failed",
            error_code: "BAD_REQUEST_ERROR",
            error_description: "Payment failed",
            error_reason: "payment_failed",
            error_step: "payment_authentication",
            error_source: "bank"
          }
        }
      }
    }
  },
  {
    name: "Fraud Risk (Layer 4)",
    payload: {
      event: "payment.failed",
      payload: {
        payment: {
          entity: {
            id: "pay_test_L4_fraud",
            amount: 250000,
            status: "failed",
            error_code: "BAD_REQUEST_ERROR",
            error_description: "Suspicious transaction detected",
            error_reason: "fraud_suspected",
            error_step: "payment_authorization",
            error_source: "issuer"
          }
        }
      }
    }
  },
  {
    name: "Compliance (Layer 4)",
    payload: {
      event: "payment.failed",
      payload: {
        payment: {
          entity: {
            id: "pay_test_L4_comp",
            amount: 15000,
            status: "failed",
            error_code: "BAD_REQUEST_ERROR",
            error_description: "Card missing required 3DS authentication",
            error_reason: "authentication_failed",
            error_step: "payment_authentication",
            error_source: "customer"
          }
        }
      }
    }
  }
];

export default function SimulatorPanel() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [customJson, setCustomJson] = useState(JSON.stringify(SCENARIOS[0].payload, null, 2));
  const [mode, setMode] = useState<'presets' | 'custom'>('presets');

  const handleSend = async (payload: any) => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    const res = await simulateWebhook(payload);
    
    if (res.success) {
      setSuccess('Transaction ingested & classified!');
    } else {
      setError(res.error || 'Failed to simulate');
    }
    setLoading(false);
  };

  const handleCustomSend = () => {
    try {
      const parsed = JSON.parse(customJson);
      handleSend(parsed);
    } catch (e: any) {
      setError('Invalid JSON format: ' + e.message);
    }
  };

  return (
    <div className="card" style={{ marginBottom: '2rem', padding: '1.25rem 1.5rem' }}>
      <div className="card-title" style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Play size={16} color="var(--green)" />
          Test Simulator
        </span>
        
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button 
            onClick={() => setMode('presets')} 
            style={{ background: mode === 'presets' ? 'var(--bg-card-hover)' : 'transparent', border: '1px solid var(--border)', color: mode === 'presets' ? 'var(--text-primary)' : 'var(--text-muted)', padding: '0.3rem 0.6rem', borderRadius: '6px', fontSize: '0.7rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
          >
            <Zap size={12} /> Presets
          </button>
          <button 
            onClick={() => setMode('custom')} 
            style={{ background: mode === 'custom' ? 'var(--bg-card-hover)' : 'transparent', border: '1px solid var(--border)', color: mode === 'custom' ? 'var(--text-primary)' : 'var(--text-muted)', padding: '0.3rem 0.6rem', borderRadius: '6px', fontSize: '0.7rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
          >
            <Code size={12} /> JSON Payload
          </button>
        </div>
      </div>

      {mode === 'presets' ? (
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {SCENARIOS.map((s, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(s.payload)}
              disabled={loading}
              style={{
                background: 'rgba(79,142,255,0.08)',
                border: '1px solid rgba(79,142,255,0.3)',
                color: 'var(--blue)',
                padding: '0.5rem 1rem',
                borderRadius: '8px',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '0.82rem',
                fontWeight: 600,
                opacity: loading ? 0.6 : 1,
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem'
              }}
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
              {s.name}
            </button>
          ))}
        </div>
      ) : (
        <div>
          <textarea 
            value={customJson}
            onChange={(e) => setCustomJson(e.target.value)}
            style={{ width: '100%', height: '150px', background: 'var(--bg-2)', border: '1px solid var(--border)', color: 'var(--text-primary)', fontFamily: 'var(--mono)', fontSize: '0.8rem', padding: '0.75rem', borderRadius: '8px', marginBottom: '0.75rem', resize: 'vertical' }}
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

      {error && <div style={{ marginTop: '1rem', color: 'var(--red)', fontSize: '0.8rem', background: 'var(--red-dim)', padding: '0.5rem 0.75rem', borderRadius: '6px', border: '1px solid rgba(248,113,113,0.25)' }}>{error}</div>}
      {success && <div style={{ marginTop: '1rem', color: 'var(--green)', fontSize: '0.8rem', background: 'var(--green-dim)', padding: '0.5rem 0.75rem', borderRadius: '6px', border: '1px solid rgba(52,211,153,0.25)' }}>{success}</div>}
    </div>
  );
}
