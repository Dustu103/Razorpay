'use client';

import { useState } from 'react';
import { Loader2, ShieldCheck, ShieldAlert, Code } from 'lucide-react';

export default function ComplianceScanner() {
  const [jsonInput, setJsonInput] = useState(`{
  "flow": [
    {
      "screen_name": "checkout_step_1",
      "elements": [
        { "id": "btn_pay", "type": "button", "text": "Pay Now (Hurry, 5 mins left!)" },
        { "id": "chk_subscribe", "type": "checkbox", "state": "pre-checked", "text": "Subscribe to premium" }
      ]
    },
    {
      "screen_name": "cancellation_settings",
      "elements": [
        { "id": "btn_cancel", "type": "button", "state": "hidden", "text": "Cancel Subscription" }
      ]
    }
  ]
}`);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleScan = async () => {
    setLoading(true);
    setError('');
    setResult(null);

    try {
      // Validate JSON first
      const payload = JSON.parse(jsonInput);
      
      const res = await fetch('http://localhost:3004/api/v1/scan-compliance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error(`API Error: ${res.statusText}`);
      }

      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Failed to scan compliance');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <ShieldCheck size={20} style={{ color: 'var(--purple)' }} />
        <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Mandate Compliance Scanner (Feature 2)</h2>
      </div>

      <div style={{ padding: '1.5rem' }}>
        <p style={{ marginBottom: '1.25rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Validate a business's UX flow against the Feb 2026 RBI Guidelines for recurring mandates.
        </p>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600 }}>
            <Code size={14} style={{ color: 'var(--indigo)' }} />
            <span>Screen JSON Definition</span>
          </div>
          <textarea 
            value={jsonInput}
            onChange={(e) => setJsonInput(e.target.value)}
            spellCheck="false"
            rows={15}
            style={{ width: '100%', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border)', backgroundColor: 'rgba(0,0,0,0.2)', color: 'var(--text-primary)', fontFamily: 'var(--mono)', fontSize: '0.85rem', outline: 'none', resize: 'vertical' }}
          />
        </div>

        <div style={{ marginTop: '1.25rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <button className="btn primary" onClick={handleScan} disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 1.5rem' }}>
            {loading ? <Loader2 className="spin" size={16} /> : <ShieldCheck size={16} />}
            {loading ? 'Scanning...' : 'Scan Flow for RBI Violations'}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: '1.5rem', padding: '1rem', backgroundColor: 'var(--red-dim)', color: 'var(--red)', border: '1px solid rgba(248, 113, 113, 0.3)', borderRadius: '8px' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {result && (
          <div style={{ marginTop: '2.5rem', borderTop: '1px solid var(--border)', paddingTop: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
              {result.is_compliant ? (
                <><ShieldCheck size={28} style={{ color: 'var(--green)' }} /> <h3 style={{ color: 'var(--green)', margin: 0, fontSize: '1.25rem' }}>Fully Compliant</h3></>
              ) : (
                <><ShieldAlert size={28} style={{ color: 'var(--red)' }} /> <h3 style={{ color: 'var(--red)', margin: 0, fontSize: '1.25rem' }}>Compliance Violations Detected</h3></>
              )}
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
              <span className="badge" style={{ background: 'var(--bg-2)', color: 'var(--text-primary)', border: '1px solid var(--border)', fontSize: '0.8rem', padding: '4px 10px', borderRadius: '16px' }}>
                Layer 1 (Deterministic): {result.layer1_violations || 0}
              </span>
              <span className="badge" style={{ background: 'var(--purple-dim)', color: 'var(--purple)', border: '1px solid rgba(192, 132, 252, 0.3)', fontSize: '0.8rem', padding: '4px 10px', borderRadius: '16px' }}>
                Layer 2 (LLM): {result.layer2_violations || 0}
              </span>
            </div>

            {result.violations && result.violations.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {result.violations.map((v: any, idx: number) => (
                  <div key={idx} style={{
                    padding: '1.25rem', 
                    borderRadius: '10px', 
                    borderLeft: `4px solid ${v.severity === 'High' ? 'var(--red)' : v.severity === 'Medium' ? 'var(--amber)' : 'var(--blue)'}`,
                    backgroundColor: 'rgba(255,255,255,0.03)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <strong style={{ fontSize: '0.95rem', color: 'var(--text-primary)' }}>Screen: {v.screen_name}</strong>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <span className="badge" style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '12px', background: v.detected_by === 'layer1_deterministic' ? 'var(--bg-2)' : 'var(--purple-dim)', color: v.detected_by === 'layer1_deterministic' ? 'var(--text-muted)' : 'var(--purple)', border: `1px solid ${v.detected_by === 'layer1_deterministic' ? 'var(--border)' : 'rgba(192, 132, 252, 0.3)'}` }}>
                          {v.detected_by === 'layer1_deterministic' ? 'Layer 1' : 
                           v.detected_by === 'layer2_llm_ensemble_consensus' ? 'Layer 2 (Groq + Gemini Consensus)' :
                           v.detected_by === 'layer2_llm_groq' ? 'Layer 2 (Groq Only)' :
                           v.detected_by === 'layer2_llm_gemini' ? 'Layer 2 (Gemini Only)' : 'Layer 2 (LLM)'}
                        </span>
                        <span className="badge" style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '12px', background: v.severity === 'High' ? 'var(--red-dim)' : v.severity === 'Medium' ? 'var(--amber-dim)' : 'var(--blue-dim)', color: v.severity === 'High' ? 'var(--red)' : v.severity === 'Medium' ? 'var(--amber)' : 'var(--blue)', border: `1px solid ${v.severity === 'High' ? 'rgba(248, 113, 113, 0.3)' : v.severity === 'Medium' ? 'rgba(251, 191, 36, 0.3)' : 'rgba(96, 165, 250, 0.3)'}` }}>
                          {v.severity} Severity
                        </span>
                      </div>
                    </div>
                    <div style={{ marginBottom: '0.5rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}><strong style={{ color: 'var(--text-primary)' }}>Rule Broken:</strong> {v.rule_broken}</div>
                    <div style={{ color: 'var(--green)', fontSize: '0.9rem', padding: '0.5rem 0.75rem', backgroundColor: 'var(--green-dim)', borderRadius: '6px', border: '1px solid rgba(52, 211, 153, 0.2)' }}><strong style={{ color: 'var(--green)' }}>Suggested Fix:</strong> {v.fix_suggestion}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
